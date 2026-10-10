"""One explicit allocation order, without rewriting device bindings or rights.

Absent a saved board, the beta.34 controllers are untouched. Saving is an admin
operation under the existing runtime lock. Safety/comfort is NOT a sortable load.
The optional SG request stays behind EV and the protected dishwasher preference;
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
from .engine import Action
from .heatpump_budget import sg_solar_budget
from .dishwasher import read as read_dishwasher
from .sg_config import actuator_conflicts, validate_config

GROUP = "priority_board"
SCHEMA = 2
WALLBOX = "wallbox"
EXTRA = "dhw_extra"
EXTRA_MIGRATION = "dhw_extra_priority_migration"


def device_key(device_id):
    return "device:" + device_id


def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


class PriorityBoard:
    def __init__(self, runtime):
        self.r = runtime
        # Prospective allocation is never physical solar credit. It only permits
        # one safe OFF; fresh P1 and SG commissioning still authorise the relay.
        self._extra_since = None
        self._extra_sample = None
        self._extra_last = None
        self._extra_key = None
        self._extra_lease_until = 0.0
        self.extra_reclaim = {"state": "idle", "reason": ""}

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
                elif self.r.configs[i].get("kind") == "dishwasher":
                    # Protected programme power remains ahead of the optional
                    # tank buffer even when no EV preference was granted.
                    result.insert(result.index(EXTRA), key)
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
                 "reason": "SG-zonneboost blijft na de Wallbox en gebruikt geen laadvermogen van de auto."}]
        rows += [{"before": device_key(i), "after": EXTRA,
                  "reason": c["name"] + " houdt de afgesproken voorrang op SG-zonneboost."}
                 for i, c in self.r.configs.items() if c.get("kind") == "dishwasher"]
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
                "sg_boost": self.r.entry.options.get("sg_boost", {}),
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
        if self.saved.get(EXTRA_MIGRATION) == 57:
            desired[GROUP][EXTRA_MIGRATION] = 57
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
        options[GROUP] = {**saved,
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
        return [{"id": "safety", "name": "Veiligheid en Panasonic-regeling", "active": True,
                 "power_label": "Niet beschikbaar voor zonneboost",
                 "reason": "Panasonic regelt ruimtecomfort, normaal warm water en sterilisatie zelfstandig. SG verandert geen native instelling."}]

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
                rows.append({"id": key, "name": "Warmtepomp — SG-zonneboost", "kind": "sg_boost",
                    "active": r.sg_boost.configured and r.sg_boost.settings.get("enabled") is True,
                    "position": ranks[key], "power_label": "Alleen echt restoverschot; geen laadvermogen",
                    "reason": "Een extra SG-vraag mag alleen lager geplaatste, eigen onderbreekbare toestellen veilig laten wachten."})
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
                "extra_reclaim": dict(self.extra_reclaim),
                "wallbox_power": permissions, "rows": rows, "protected": self.protected_rows(),
                "constraints": self.constraints(),
                "note": ("Dit is de enige volgorde voor flexibele zonne-energie. Wat hoger staat krijgt eerst de kans, maar lopende programma’s, minimumlooptijden en veiligheid blijven altijd beschermd."
                         if self.active else "De bestaande effectieve volgorde wordt ongewijzigd in deze centrale lijst vastgelegd."),
                "legacy_note": "Eerder opgeslagen toestelkeuzes blijven behouden; deze centrale lijst is leidend."}

    def _clear_extra_reclaim(self, reason=""):
        self._extra_since = self._extra_sample = self._extra_last = self._extra_key = None
        self.extra_reclaim = {"state": "idle", "reason": reason}

    def _sg_ready(self):
        r, c = self.r, self.r.sg_boost.settings
        return (self.active and r.mode == "solar" and c.get("enabled") is True
                and c.get("commissioning_confirmed") is True and c.get("watchdog_confirmed") is True
                and bool(c.get("entity_id")) and not validate_config(c)
                and not actuator_conflicts(c, list(r.configs.values()))
                and not actuator_conflicts(c, list(r.battery_fleet.configs.values()))
                and not r.sg_boost.manual_hold and not r.sg_boost.completion_hold
                and not r.sg_boost.cooling_block_reason(live=True)
                and not r.battery_fleet.busy
                and not r.sg_boost.busy and not r.sg_boost.overview().get("action_required")
                and not r.pending and not r.handover and not r.restart_blocking and not r.faults)

    def sg_priority_allowed(self, now):
        """Higher fitting requests get the next actual solar window first."""
        r, ranks = self.r, self.ranks()
        guard = getattr(r.wallbox_guard, "result", None)
        if r.wallbox_settings.get("enabled") and getattr(guard, "block_increase", False):
            return False
        budget = sg_solar_budget(r)
        if not budget["valid"]:
            return False
        for d in r.devices():
            st, cfg = r.states[d.id], r.configs[d.id]
            if cfg.get("kind") == "dishwasher" and r.dishwasher_app.due(cfg, time.time()) and not st.on:
                return False
            if (ranks[device_key(d.id)] >= ranks[EXTRA] or st.on or not st.enabled
                    or not st.available or not st.demand or not st.interlock or not st.cycle_armed
                    or st.fault or st.manual_until > now or now-st.last_off < d.min_off_s
                    or st.planner_hold and not st.deadline_force):
                continue
            if cfg.get("kind") == "dishwasher" and not r.dishwasher.permitted(cfg, read_dishwasher(r.hass,cfg),time.time())[0]:
                continue
            if budget["available_w"] >= d.minimum+d.start_margin_w:
                return False
        return True

    def _extra_candidates(self, now):
        r, ranks = self.r, self.ranks()
        devices = {d.id:d for d in r.devices()}
        candidates = []
        for i, state in r.states.items():
            cfg, d = r.configs[i], devices[i]
            if (ranks[device_key(i)] <= ranks[EXTRA] or not state.owned or not state.on
                    or not state.available or not state.enabled or state.fault
                    or cfg.get("kind") == "dishwasher" or d.non_interruptible
                    or state.manual_until > now or state.manual_forced or state.boost_until > now
                    or state.deadline_force or state.deadline_urgent or state.planner_grid_force
                    or now-state.last_on < d.min_on_s or i in r.source_isolated_devices
                    or i in r.faults or not r._reclaim_meter(i)):
                continue
            watts, _ = r._power(cfg.get("power_entity"))
            if r._restart_active(cfg) is not True or not finite(watts) or watts <= 0:
                continue
            candidates.append((i, float(watts)))
        return sorted(candidates,key=lambda item:(ranks[device_key(item[0])],item[0]),reverse=True)

    def extra_reclaim_action(self, now, local_now):
        """One lower owned OFF proposal, not yet available watts or an SG lease."""
        if not self._sg_ready() or not self.sg_priority_allowed(now):
            self._clear_extra_reclaim()
            return None
        r, c = self.r, self.r.sg_boost.settings
        budget = sg_solar_budget(r)
        if not budget["valid"] or budget["available_w"] >= c["threshold_w"]:
            self._clear_extra_reclaim()
            return None
        if budget["discharge_w"] > r.settings.get("battery_discharge_tolerance_w", 50):
            self._clear_extra_reclaim("SG wacht: de batterij levert nog stroom")
            return None
        if max(0.0, budget["pv_w"]-budget["reserve_w"]) < c["threshold_w"]:
            self._clear_extra_reclaim("Ook na pauzeren is er nog onvoldoende werkelijke zonneproductie")
            return None
        unconsumed = sum(max(0.0, st.target_w-st.measured_w) for i,st in r.states.items()
                         if st.owned and st.on and i not in r.source_isolated_devices)
        envelope = c["expected_power_w"]+r.isolated_reserve_w+unconsumed
        limit = r.settings["max_import_w"]
        if r.capacity_settings.get("enabled"):
            if not r.capacity.valid:
                self._clear_extra_reclaim("SG wacht op betrouwbare kwartierpiekmeting")
                return None
            capacity_limit = r.capacity.allowed_grid_w
            if capacity_limit is None:
                capacity_limit = max(0.0, r.capacity.effective_target_w-r.capacity_settings["margin_w"])
            limit = min(limit, capacity_limit)
        # Never count prospective OFF watts towards phase safety. The caller's
        # normal meter/ACK and a newer actual P1 prove any eventual SG start.
        if r.phase_settings.get("enabled") and r.phase_settings.get("control_starts"):
            if (not r.phase.valid or r.phase.block_increase or r.phase.release_flexible
                    or r.phase.headroom_w is None or r.phase.headroom_w < envelope):
                self._clear_extra_reclaim("SG wacht op veilige faseruimte")
                return None
        pool, selected = self._extra_candidates(now), []
        for candidate in pool:
            selected.append(candidate)
            freed = sum(w for _,w in selected)
            if (budget["available_w"]+freed >= c["threshold_w"]
                    and budget["grid_w"]-freed+envelope <= limit):
                break
        if (not selected or budget["available_w"]+sum(w for _,w in selected) < c["threshold_w"]
                or budget["grid_w"]-sum(w for _,w in selected)+envelope > limit):
            self._clear_extra_reclaim("Geen veilig onderbreekbare lagere last kan voldoende zon vrijmaken")
            return None
        key = (tuple(i for i,_ in selected),self.revision())
        gap = max(30,r.settings["interval_s"]*2)
        if key != self._extra_key or self._extra_last is None or not 0 <= now-self._extra_last <= gap:
            self._extra_since,self._extra_sample,self._extra_key = now,budget["stamp"],key
        self._extra_last = now
        remaining = max(0,math.ceil(c["start_delay_s"]-(now-self._extra_since)))
        fresh = budget["stamp"] > self._extra_sample
        first = selected[0][0]
        reason = "Zonnestroom vrijmaken voor SG-zonneboost: " + r.configs[first]["name"] + " veilig pauzeren"
        self.extra_reclaim = {"state":"ready" if not remaining and fresh else "stability",
            "reason":reason,"device_ids":[i for i,_ in selected],
            "prospective_freed_w":round(sum(w for _,w in selected),1),"remaining_s":remaining,"new_grid_sample":fresh}
        return None if remaining or not fresh else Action(first,0.0,reason)

    def extra_reclaim_sent(self, action, now):
        if action.watts == 0 and action.reason.startswith("Zonnestroom vrijmaken voor SG-zonneboost"):
            self._extra_lease_until = now+self.r.sg_boost.settings["start_delay_s"]+self.r.settings["stale_s"]

    def extra_start_blocks(self, now):
        active_request = self.r.sg_boost.busy and self.r.sg_boost.desired_on
        if not active_request and not self._sg_ready():
            return {}
        budget = sg_solar_budget(self.r)
        prospective = self.extra_reclaim.get("state") in ("ready","stability")
        actual = budget["valid"] and budget["available_w"] >= self.r.sg_boost.settings["threshold_w"]
        if not active_request and not prospective and not actual:
            return {}
        ranks, r = self.ranks(),self.r
        return {i:"SG-zonneboost krijgt volgens de opgeslagen volgorde eerst dit zonnevenster"
            for i,st in r.states.items() if ranks[device_key(i)] > ranks[EXTRA] and not st.on
            and r.configs[i].get("kind") != "dishwasher" and not st.manual_forced
            and st.manual_until <= now and st.boost_until <= now and not st.deadline_force
            and not st.deadline_urgent and not st.planner_grid_force}
