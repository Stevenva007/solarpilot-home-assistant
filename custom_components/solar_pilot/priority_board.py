"""One explicit allocation order, without rewriting device bindings or rights.

Absent a saved board, the beta.34 controllers are untouched. Saving is an admin
operation under the existing runtime lock. Safety/comfort is NOT a sortable load.
The optional DHW buffer stays behind EV and the protected dishwasher preference;
it can be placed among other lower loads without borrowing EV watts.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import time

from homeassistant.exceptions import HomeAssistantError

from .consumer_wallbox import follows_wallbox
from .dishwasher_priority import enabled as dishwasher_priority_enabled
from .wallbox_policy import reclaim_permission

GROUP = "priority_board"
SCHEMA = 2
WALLBOX = "wallbox"
EXTRA = "dhw_extra"


def device_key(device_id):
    return "device:" + device_id


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class PriorityBoard:
    def __init__(self, runtime):
        self.r = runtime

    @property
    def saved(self):
        value = self.r.entry.options.get(GROUP, {})
        return value if isinstance(value, dict) else {}

    @property
    def active(self):
        s = self.saved
        order = s.get("order")
        return (s.get("schema") in (1, SCHEMA) and isinstance(order, list)
                and all(isinstance(x, str) for x in order)
                and len(set(order)) == len(order) and WALLBOX in order and EXTRA in order
                and order.index(WALLBOX) < order.index(EXTRA))

    def legacy_order(self):
        r = self.r
        ids = sorted(r.configs, key=lambda i: (
            0 if dishwasher_priority_enabled(r.configs[i]) else 1,
            r.priorities.get(i, r.configs[i].get("priority", 50)), i))
        first = [device_key(i) for i in ids if not follows_wallbox(r.configs[i], r.others_first)]
        last = [device_key(i) for i in ids if follows_wallbox(r.configs[i], r.others_first)]
        return first + [WALLBOX] + last + [EXTRA]

    def order(self):
        if not self.active:
            return self.legacy_order()
        known = {device_key(i) for i in self.r.configs} | {WALLBOX, EXTRA}
        result = [x for x in self.saved["order"] if x in known]
        # A new identity is never granted the predecessor's control permissions.
        # Ordinary additions go at the bottom; a new preferred dishwasher stays
        # above the Wallbox, but still starts with Auto excluded.
        for i in sorted(self.r.configs):
            key = device_key(i)
            if key not in result:
                if dishwasher_priority_enabled(self.r.configs[i]):
                    result.insert(result.index(WALLBOX), key)
                else:
                    # A newly added flexible device gets no implicit priority over
                    # existing choices. It starts at the bottom until the user
                    # deliberately moves it in the central priority screen.
                    result.append(key)
        return result

    def ranks(self):
        return {key: n + 1 for n, key in enumerate(self.order())}

    def constraints(self):
        rows = [{"before": WALLBOX, "after": EXTRA,
                 "reason": "Extra boilerwarmte blijft na de Wallbox en gebruikt geen laadvermogen van de auto."}]
        rows += [{"before": device_key(i), "after": EXTRA,
                  "reason": c["name"] + " houdt de afgesproken voorrang op extra boilerwarmte."}
                 for i, c in self.r.configs.items() if dishwasher_priority_enabled(c)]
        return rows

    @staticmethod
    def original_permission(c):
        if c.get("kind") == "dishwasher":
            return bool(c.get("dishwasher_ev_solar_priority", True))
        if c.get("wallbox_power_policy", "priority") == "legacy":
            return bool(c.get("allow_wallbox_reclaim", False))
        return c.get("wallbox_power_policy", "priority") != "never"

    def permissions(self):
        saved = self.saved.get("wallbox_power", {}) if self.active else {}
        if not isinstance(saved, dict):
            saved = {}
        return {device_key(i): saved.get(device_key(i), self.original_permission(c)) is True
                for i, c in self.r.configs.items()}

    def effective_config(self, device_id, config=None):
        c = self.r.configs[device_id] if config is None else config
        if not self.active:
            return c
        ranks = self.ranks()
        before = ranks[device_key(device_id)] < ranks[WALLBOX]
        permission = self.permissions()[device_key(device_id)]
        return {**c, "priority": ranks[device_key(device_id)],
                "_priority_board_before_wallbox": before,
                "_priority_board_wallbox_power": permission,
                "_priority_board_rank": ranks[device_key(device_id)],
                "wallbox_precedence": "consumer_first" if before else "wallbox_first",
                "wallbox_power_policy": ("legacy" if c.get("wallbox_power_policy") == "legacy" else "priority") if permission else "never",
                "allow_wallbox_reclaim": permission and c.get("kind") != "dishwasher",
                "dishwasher_ev_solar_priority": permission and before}

    def configs(self):
        return {i: self.effective_config(i, c) for i, c in self.r.configs.items()}

    def revision(self):
        # No live measurements/timestamps: a normal five-second tick is NOT a
        # concurrent edit. Device additions, legacy priority edits and proposals
        # do invalidate an open editor, so it cannot overwrite another choice.
        data = {"board": self.saved, "devices": self.r.configs,
                "overrides": self.r.priorities, "others_first": self.r.others_first,
                "wallbox": self.r.entry.options.get("wallbox", {}),
                "dhw": self.r.entry.options.get("dhw", {}),
                "pending": self.r.entry.options.get("_live_pending", {})}
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()[:24]

    def validate(self, revision, order, permissions, confirm):
        if confirm is not True:
            raise HomeAssistantError("Bevestig eerst dat je deze voorrang wilt toepassen.")
        if revision != self.revision():
            raise HomeAssistantError("De instellingen zijn intussen gewijzigd. Vernieuw de lijst en controleer je keuze opnieuw.")
        expected = self.order()
        if (not isinstance(order, list) or not all(isinstance(x, str) for x in order)
                or len(order) != len(expected) or len(set(order)) != len(order)
                or set(order) != set(expected)):
            raise HomeAssistantError("De lijst moet elk huidig toestel en elke regeling precies één keer bevatten.")
        if (not isinstance(permissions, dict) or set(permissions) != set(self.permissions())
                or any(type(v) is not bool for v in permissions.values())):
            raise HomeAssistantError("Controleer de toestemming per toestel; een ontbrekende of ongeldige keuze wordt niet ingevuld.")
        for rule in self.constraints():
            if order.index(rule["before"]) >= order.index(rule["after"]):
                raise HomeAssistantError(rule["reason"])

    async def save(self, revision, order, permissions, confirm):
        """Caller holds SolarRuntime._lock. This method never ticks or sends a command."""
        self.validate(revision, order, permissions, confirm)
        if order == self.order() and permissions == self.permissions():
            return {**self.overview(), "message": "Geen wijziging: de bestaande regeling blijft ongewijzigd."}
        if self.r.handover or self.r.pending:
            raise HomeAssistantError("Er wordt nog op een toestel of Wallbox-overdracht gewacht. De huidige opdracht wordt eerst afgerond; probeer daarna opnieuw.")
        base = deepcopy(dict(self.r.entry.options))
        desired = deepcopy(base)
        desired[GROUP] = {"schema": SCHEMA, "order": list(order), "wallbox_power": dict(permissions),
                          "source": "central_beta36"}
        await self.r.live_options.submit(base, desired)
        return {**self.overview(), "message": "Voorrang opgeslagen. De volgende regelcontrole gebruikt de nieuwe volgorde; lopende bescherming blijft gelden."}

    async def migrate_beta36(self):
        """Activate one central board while preserving beta.35 effective order exactly."""
        saved = self.saved
        order = self.order()
        permissions = self.permissions()
        if (saved.get("schema") == SCHEMA and saved.get("order") == order
                and saved.get("wallbox_power") == permissions):
            return False
        options = deepcopy(dict(self.r.entry.options))
        options[GROUP] = {
            "schema": SCHEMA,
            "order": list(order),
            "wallbox_power": dict(permissions),
            "source": "migrated_beta35" if saved.get("schema") != SCHEMA else saved.get("source", "central_beta36"),
        }
        updater = getattr(getattr(self.r.hass, "config_entries", None), "async_update_entry", None)
        if updater is not None:
            updater(self.r.entry, options=options)
        else:
            self.r.entry.options = options
        return True

    def protected_rows(self):
        r = self.r
        return [
            {"id": "safety", "name": "Veiligheid en Panasonic-beveiliging", "active": True,
             "power_label": "Wallbox-vermogen: niet van toepassing",
             "reason": "Elektrische grenzen, Panasonic-beveiliging en de wekelijkse sterilisatie blijven altijd beschermd."},
            {"id": "space_comfort", "name": "Verwarming en koeling van de woning", "active": bool(r.smart_climate.settings.get("enabled")),
             "power_label": "Wallbox-vermogen: ja, comfort gaat voor",
             "reason": "Als de woning echt warmte of koeling nodig heeft, blijft de warmtepomp voorrang houden. Panasonic kiest zelf HEAT of COOL."},
            {"id": "dhw_comfort", "name": "Normaal warm water en noodzakelijke ochtendvoorraad", "active": r.dhw.configured,
             "power_label": "Wallbox-vermogen: ja, comfort gaat voor",
             "reason": "Het gewone 50 °C-doel, de 46 °C-bewaking en noodzakelijke voorraad blijven beschermd. De extra 60 °C-buffer staat apart in de verplaatsbare lijst."},
            {"id": "dhw_evening", "name": f"Avondvoorraad warm water (maximaal {r.dhw.settings.get('evening_cap_c', 55):g} °C)",
             "active": bool(r.dhw.configured and r.dhw.auto_enabled and r.dhw.settings.get("evening_enabled")),
             "power_label": "Wallbox-vermogen: ja, bij bevestigd zonneladen",
             "reason": "De avondvoorraad mag indien nodig zonnestroom gebruiken waarmee de auto nu laadt. De Wallbox vermindert het laden zelf; SolarPilot geeft geen laadcommando. Temperatuurlimiet, koeling, woningcomfort, sterilisatie en kwartierpiekbewaking blijven gelden."},
        ]

    def overview(self):
        r, ranks = self.r, self.ranks()
        permissions = self.permissions()
        rows = []
        for key in self.order():
            if key == WALLBOX:
                rows.append({"id": key, "name": "Auto laden (Wallbox)", "kind": "wallbox",
                    "active": bool(r.wallbox_settings.get("enabled")), "position": ranks[key],
                    "power_label": "Wallbox-vermogen: dit ís de Wallbox",
                    "reason": "De Wallbox regelt zelf. SolarPilot verstuurt geen laadcommando vanuit deze lijst."})
            elif key == EXTRA:
                target = r.dhw.settings.get("surplus_c", 60)
                rows.append({"id": key, "name": f"Extra warm water tot {target:g} °C", "kind": "dhw_extra",
                    "active": r.dhw.configured and r.dhw.auto_enabled, "position": ranks[key],
                    "power_label": "Wallbox-vermogen: nee · alleen echt vrij overschot",
                    "reason": "Dit is alleen extra zonne-opslag in warm water. Het mag nooit normaal comfort, de afwasmachine of de auto verdringen."})
            else:
                i = key[len("device:"):]
                c = self.effective_config(i)
                before = not follows_wallbox(c, r.others_first)
                if c.get("kind") == "dishwasher":
                    may = before and permissions[key] and dishwasher_priority_enabled(c) and i not in r.dishwasher_priority.ev_blocks
                    why = ("Beschermde afwasroute: alleen met actuele, bevestigde zonnelaadsessie; lopende beurt wordt nooit afgebroken."
                           if may else "Geen laadvermogen beschikbaar via de beschermde afwasroute; alleen toegestane andere energie.")
                else:
                    may, _, why = reclaim_permission(c, before_wallbox=before,
                        dedicated_meter=r._reclaim_meter(i), blocked=i in r.reclaim_blocks)
                status = "Auto" if r.device_modes.get(i, "disabled") == "auto" else "Uitgesloten"
                rows.append({"id": key, "device_id": i, "name": c["name"], "kind": c.get("kind", "switch"),
                    "position": ranks[key], "active": status == "Auto", "status": status,
                    "before_wallbox": before, "wallbox_power": permissions[key],
                    "effective_permission": may,
                    "power_label": "Ja, onder voorwaarden" if may else "Nee in de huidige instelling",
                    "reason": why, "non_interruptible": bool(c.get("non_interruptible"))})
        return {"active": self.active, "revision": self.revision(), "order": self.order(),
                "wallbox_power": permissions, "rows": rows, "protected": self.protected_rows(),
                "constraints": self.constraints(),
                "note": ("Dit is de enige volgorde voor flexibele zonne-energie. Wat hoger staat krijgt eerst de kans, maar lopende programma’s, minimumlooptijden en veiligheid blijven altijd beschermd."
                         if self.active else "De bestaande effectieve volgorde wordt ongewijzigd in deze centrale lijst vastgelegd."),
                "legacy_note": "Eerder opgeslagen toestelkeuzes blijven behouden; deze centrale lijst is leidend."}

    def guard_extra(self, reading, now):
        """Do not let optional heat take a *fitting* higher claimant's free watts.

        Running measured loads already live in P1; do not double-reserve them.
        Dishwasher reservations continue to use their existing separate route.
        This cannot start, stop or override an ordinary comfort target.
        """
        if not self.active or not reading.luxury_allowed or self.r.mode != "solar":
            return
        r = self.r
        if not finite(r.grid_w) or not finite(r.filtered):
            return
        free = max(0.0, -max(r.grid_w, r.filtered) - r.settings["reserve_w"] - max(0, reading.battery_discharge_w or 0)
                   - max(0.0, getattr(r, "isolated_reserve_w", 0)))
        ranks = self.ranks()
        for d in sorted(r.devices(), key=lambda x: (x.priority, x.id)):
            s = r.states[d.id]
            if (d.id in getattr(r, "source_isolated_devices", {})
                    or ranks[device_key(d.id)] >= ranks[EXTRA] or s.on or not s.enabled or not s.available
                    or not s.demand or not s.interlock or not s.cycle_armed or s.fault
                    or s.manual_until > now or now - s.last_off < d.min_off_s
                    or (s.planner_hold and not s.deadline_force) or d.kind == "dishwasher"):
                continue
            if free >= d.minimum + d.start_margin_w:
                reading.luxury_allowed = False
                reading.luxury_reason = f"{d.name} staat vóór extra boilerwarmte en past in het beschikbare zonneoverschot"
                return

    def extra_start_blocks(self, now):
        """Reserve a qualifying optional heat window against NEW lower starts.

        Existing cycles are never stopped for a new optional heat target. The
        heat policy itself supplies its stable-sun and cooling/comfort verdict;
        no second, weaker temperature controller is introduced here.
        """
        r = self.r
        if (not self.active or r.mode != "solar" or not r.dhw.configured or not r.dhw.auto_enabled
                or r.dhw.needs_review or r.dhw.manual_hold or r.dhw.fault
                or not r.dhw.settings.get("safety_confirmed")):
            return {}
        decision = r.dhw.policy.result
        # Only a real surplus-stage evaluation reserves an upcoming command.
        # A temperature already at its extra target creates no perpetual claim.
        temp = r.dhw.reading.temperature_c
        threshold = r.dhw.settings["surplus_c"] + r.dhw.settings["tank_differential_c"]
        target = r.hass.states.get(r.dhw.settings.get("target_entity")) if r.dhw.settings.get("target_entity") else None
        heating = bool(target and target.attributes.get("hvac_action") == "heating")
        # Above the native restart threshold an idle tank does not claim a
        # heating window merely because the high setpoint is still selected.
        if (not finite(temp) or temp >= r.dhw.settings["surplus_c"]
                or (temp > threshold and not heating) or decision.capacity_block
                or decision.stage != "surplus"):
            return {}
        ranks = self.ranks()
        return {i: "Extra boilerwarmte krijgt eerst het passende zonnevenster; bestaande looptijden blijven behouden"
                for i, s in r.states.items() if ranks[device_key(i)] > ranks[EXTRA] and not s.on
                and not s.manual_forced and s.boost_until <= now and not s.deadline_force and not s.planner_grid_force}
