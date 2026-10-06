"""One explicit allocation order, without rewriting device bindings or rights.

Absent a saved board, the beta.34 controllers are untouched. Saving is an admin
operation under the existing runtime lock. Safety/comfort is NOT a sortable load.
The optional DHW buffer stays behind EV and the protected dishwasher preference;
it can be placed among other lower loads without borrowing EV watts.
"""
from __future__ import annotations

from copy import copy, deepcopy
import hashlib
import json
import math
import time

from homeassistant.exceptions import HomeAssistantError

from .consumer_wallbox import follows_wallbox
from .dishwasher_priority import enabled as dishwasher_priority_enabled
from .wallbox_policy import reclaim_permission
from .engine import Action
from .heatpump_budget import heatpump_power, shared_commitment
from .dishwasher import read as read_dishwasher

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
        # one safe OFF; normal DHW feedback/P1/stability still authorise 60 °C.
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
                 "reason": "Extra boilerwarmte blijft na de Wallbox en gebruikt geen laadvermogen van de auto."}]
        rows += [{"before": device_key(i), "after": EXTRA,
                  "reason": c["name"] + " houdt de afgesproken voorrang op extra boilerwarmte."}
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

    async def migrate_beta57(self):
        """Give the newly authorised solar buffer first ordinary-load priority once.

        Wallbox consumption and every dishwasher remain ahead of extra DHW.
        Saved Wallbox rights are retained, although a lower position makes them
        ineffective. Future deliberate central edits are never reset.
        """
        if not self.r.dhw.configured or self.saved.get(EXTRA_MIGRATION) == 57:
            return False
        old = self.order()
        protected = {WALLBOX} | {device_key(i) for i, c in self.r.configs.items()
                                if c.get("kind") == "dishwasher"}
        order = [key for key in old if key in protected] + [EXTRA]
        order += [key for key in old if key not in protected and key != EXTRA]
        options = deepcopy(dict(self.r.entry.options))
        options[GROUP] = {**self.saved, "schema": SCHEMA, "order": order,
                          "wallbox_power": self.permissions(),
                          "source": "migrated_beta57", EXTRA_MIGRATION: 57}
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
                    "reason": "Extra zonne-opslag mag lager geplaatste, veilig onderbreekbare verbruikers pauzeren. Ruimteklimaat, afwasmachine en auto blijven beschermd."})
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
                    or (s.planner_hold and not s.deadline_force)):
                continue
            if d.kind == "dishwasher":
                cfg = r.configs[d.id]
                permitted, _ = r.dishwasher.permitted(cfg, read_dishwasher(r.hass, cfg), time.time())
                if not permitted:
                    continue
            if free >= d.minimum + d.start_margin_w or d.kind == "dishwasher" and s.deadline_force:
                reading.luxury_allowed = False
                reading.luxury_reason = f"{d.name} staat vóór extra boilerwarmte en past in het beschikbare zonneoverschot"
                return

    def _clear_extra_reclaim(self, reason=""):
        self._extra_since = self._extra_sample = self._extra_last = self._extra_key = None
        self.extra_reclaim = {"state": "idle", "reason": reason}

    def extra_reclaim_sent(self, action, now):
        """Retain a bounded start reservation, never the requested OFF watts."""
        if action.watts == 0 and action.reason.startswith("Zonnestroom vrijmaken voor extra warm water"):
            self._extra_lease_until = now + max(60.0, float(self.r.dhw.settings["rise_delay_s"])) + max(
                30.0, float(self.r.settings["stale_s"]))

    def _extra_claim_needed(self, manager=None):
        manager = manager or self.r.dhw
        temp = manager.reading.temperature_c
        threshold = manager.settings["surplus_c"] + manager.settings["tank_differential_c"]
        target_id = manager.settings.get("target_entity")
        target = self.r.hass.states.get(target_id) if target_id else None
        heating = bool(target and target.attributes.get("hvac_action") in ("heating", "preheating"))
        return (finite(temp) and temp < manager.settings["surplus_c"]
                and (temp <= threshold or heating))

    def _extra_candidates(self, now):
        """Only real, controlled, safely interruptible watts can become a proposal."""
        r, ranks = self.r, self.ranks()
        devices = {d.id: d for d in r.devices()}
        climate_ids = set(getattr(r.smart_climate, "settings", {}).get("zone_entities", []))
        candidates = []
        for i, state in r.states.items():
            cfg, d = r.configs[i], devices[i]
            if (ranks[device_key(i)] <= ranks[EXTRA] or not state.owned or not state.on
                    or not state.available or not state.enabled or state.fault
                    or cfg.get("kind") == "dishwasher" or d.non_interruptible
                    or cfg.get("control_entity") in climate_ids
                    or state.manual_until > now or state.manual_forced
                    or state.boost_until > now or state.deadline_force or state.deadline_urgent
                    or state.planner_grid_force or now - state.last_on < d.min_on_s
                    or i in getattr(r, "source_isolated_devices", {})
                    or i in r.faults or not r._reclaim_meter(i)):
                continue
            # Re-read both the control status and a dedicated physical meter.
            # Planner nominal watts, stale feedback and estimated meters cannot
            # prove how much solar power the requested OFF would release.
            watts, _ = r._power(cfg.get("power_entity"))
            if r._restart_active(cfg) is not True or not finite(watts) or watts <= 0:
                continue
            candidates.append((i, float(watts)))
        return sorted(candidates, key=lambda item: (ranks[device_key(item[0])], item[0]), reverse=True)

    def _prospective_extra(self, now, local_now, grid, discharge, pv, candidates):
        """Run every DHW policy/runtime gate on an isolated counterfactual copy.

        No real reading, learned sample, stability timer, target ownership or
        dishwasher state is modified. The freed power is a planning hypothesis,
        never permission to issue a DHW target before the normal fresh P1 path.
        """
        r = self.r
        trial_runtime = copy(r)
        trial_runtime.states = deepcopy(r.states)
        freed = sum(watts for _, watts in candidates)
        trial_runtime.grid_w = grid - freed
        trial_runtime.filtered = grid - freed
        trial_runtime.pv_w = pv
        for i, _ in candidates:
            state = trial_runtime.states[i]
            state.on = state.owned = False
            state.target_w = state.measured_w = 0.0
        hp = heatpump_power(r)
        incremental = shared_commitment(float(r.dhw.settings["estimated_heat_power_w"]), 0,
                                        hp["watts"] if hp["valid"] else None)
        unconsumed = sum(max(0.0, state.target_w - state.measured_w)
                         for i, state in trial_runtime.states.items() if state.owned and state.on
                         and i not in getattr(r, "source_isolated_devices", {}))
        projected = grid - freed + incremental + max(0.0, float(r.isolated_reserve_w)) + unconsumed
        if projected > r.settings["max_import_w"]:
            return False, "Extra warm water wacht op ruimte binnen de netgrens"
        if r.capacity_settings.get("enabled"):
            if not r.capacity.valid:
                return False, "Extra warm water wacht op betrouwbare kwartierpiekmeting"
            limit = r.capacity.allowed_grid_w
            if limit is None:
                limit = max(0.0, r.capacity.effective_target_w - r.capacity_settings["margin_w"])
            if not finite(limit) or projected > limit:
                return False, "Extra warm water wacht op voldoende kwartierpiekruimte"
        if (r.phase_settings.get("enabled") and r.phase_settings.get("control_starts")
                and (not r.phase.valid or r.phase.block_increase or not finite(r.phase.headroom_w)
                     or r.phase.headroom_w < incremental + max(0.0, float(r.isolated_reserve_w)) + unconsumed)):
            # The OFF meter has no verified phase allocation. Its prospective
            # watts must never inflate a per-phase safety headroom.
            return False, "Extra warm water wacht op veilige ruimte op de elektrische fasen"
        trial = copy(r.dhw)
        trial.runtime = trial_runtime
        trial.settings = {**r.dhw.settings, "estimated_heat_power_w": incremental}
        trial.policy = deepcopy(r.dhw.policy)
        trial.policy.settings = {**r.dhw.settings, "rise_delay_s": 0,
                                 "sample_gap_s": max(30, r.settings["interval_s"] * 2)}
        trial.comfort = deepcopy(r.dhw.comfort)
        trial.reading = deepcopy(r.dhw.reading)
        trial._comfort_slots = deepcopy(r.dhw._comfort_slots)
        trial._luxury_allocation = None
        # An unexecuted counterfactual never owns high-target hysteresis.
        trial.owned_target = None
        trial._execution_now, trial._execution_local_now = now, local_now
        trial_runtime.dhw = trial
        trial_runtime.priority_board = PriorityBoard(trial_runtime)
        reading = trial.read(grid - freed, True, discharge, local_now)
        capacity_guard = (bool(getattr(r.capacity, "enabled", False))
                          and r.capacity_settings.get("respect_optional_dhw", True))
        if capacity_guard:
            if (not getattr(r.capacity, "valid", False)
                    or not finite(reading.optional_import_headroom_w)):
                return False, "Extra warm water wacht op betrouwbare kwartierpiekruimte"
            reading.optional_import_headroom_w += freed
            if reading.optional_import_headroom_w < incremental:
                return False, "Extra warm water wacht op voldoende kwartierpiekruimte"
        trial._prepare_comfort(local_now, reading)
        decision = trial.policy.update(now, local_now, reading, False)
        gates = trial._execution_gates()
        failed = [g for g in gates if not g["passed"]]
        if failed:
            return False, failed[0]["reason"]
        if (decision.stage != "surplus" or decision.remaining_s
                or decision.capacity_block or decision.target_c != trial.settings["surplus_c"]):
            return False, decision.reason
        return True, decision.reason

    def extra_reclaim_action(self, now, local_now):
        """Propose one serial OFF only after a complete, stable solar-buffer proof.

        The caller must use the normal OFF dispatch/ack path, then a new P1
        sample and ordinary DHW stability. This method never sends a command.
        """
        r = self.r
        if (not self.active or r.mode != "solar" or not r.dhw.configured or not r.dhw.auto_enabled
                or r.dhw.needs_review or r.dhw.restart_recovery or r.dhw.manual_hold or r.dhw.fault
                or not r.dhw.settings.get("safety_confirmed") or r.dhw.pending
                or r.pending or r.handover or r.restart_blocking or r.faults
                or not self._extra_claim_needed()):
            self._clear_extra_reclaim()
            return None
        grid, valid, discharge, ready, stamp = r._site_data()
        pv, _ = r._power(r.settings.get("pv_entity"))
        if (not valid or not ready or not finite(grid) or not finite(r.filtered)
                or not finite(pv) or pv < 0 or not finite(stamp)):
            self._clear_extra_reclaim("Extra warm water wacht op betrouwbare actuele energiemetingen")
            return None
        grid = max(grid, r.filtered)
        # If actual free watts already fit, pausing any ordinary load would be
        # unnecessary. Keep its normal stability/dispatch controller in charge.
        already_fits, _ = self._prospective_extra(now, local_now, grid, discharge, pv, [])
        if already_fits:
            self._clear_extra_reclaim()
            return None
        pool = self._extra_candidates(now)
        selected = []
        why = "Geen veilig onderbreekbare verbruiker kan voldoende zonnevermogen vrijmaken"
        fits = False
        for candidate in pool:
            selected.append(candidate)
            fits, why = self._prospective_extra(now, local_now, grid, discharge, pv, selected)
            if fits:
                break
        if not fits:
            self._clear_extra_reclaim(why)
            return None
        key = (tuple(i for i, _ in selected), self.revision())
        gap = max(30, r.settings["interval_s"] * 2)
        if (key != self._extra_key or self._extra_last is None
                or now < self._extra_last or now - self._extra_last > gap):
            self._extra_key, self._extra_since, self._extra_sample = key, now, stamp
        self._extra_last = now
        delay = max(0.0, float(r.dhw.settings["rise_delay_s"]))
        remaining = max(0, math.ceil(delay - (now - self._extra_since)))
        fresh = stamp > self._extra_sample
        first = selected[0][0]
        reason = (f"Zonnestroom vrijmaken voor extra warm water: {r.configs[first]['name']} veilig pauzeren; "
                  "afwasmachine en ruimteklimaat blijven beschermd")
        self.extra_reclaim = {"state": "ready" if not remaining and fresh else "stability",
                              "reason": reason, "device_ids": [i for i, _ in selected],
                              "prospective_freed_w": round(sum(w for _, w in selected), 1),
                              "remaining_s": remaining, "new_grid_sample": fresh}
        if remaining or not fresh:
            return None
        return Action(first, 0.0, reason)

    def extra_start_blocks(self, now):
        """Reserve a qualifying optional heat window against NEW lower starts.

        Reclaim only pauses eligible owned interruptible loads; protected
        programs and minimum runtimes remain intact. The same DHW policy gives
        the prospective and actual solar/cooling/comfort verdicts.
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
        prospective = (self.extra_reclaim.get("state") in ("stability", "ready")
                       and self._extra_last is not None and 0 <= now - self._extra_last <= max(30, r.settings["interval_s"] * 2))
        if (not prospective and now < self._extra_lease_until and not r.pending
                and finite(r.grid_w) and finite(r.pv_w)):
            # After a confirmed OFF, the smoothing filter can lag behind real
            # P1. Reserve the now genuine raw solar window while the ordinary
            # filtered DHW timer catches up. No old or requested watts are added.
            _, valid, discharge, ready, _ = r._site_data()
            if valid and ready:
                local_now = getattr(r.dhw, "_execution_local_now", None)
                if local_now is not None:
                    prospective, _ = self._prospective_extra(now, local_now, r.grid_w, discharge, r.pv_w, [])
        if (not finite(temp) or temp >= r.dhw.settings["surplus_c"]
                or (temp > threshold and not heating) or decision.capacity_block
                or not prospective and decision.stage != "surplus"):
            return {}
        ranks = self.ranks()
        return {i: "Extra boilerwarmte krijgt eerst het passende zonnevenster; bestaande looptijden blijven behouden"
                for i, s in r.states.items() if ranks[device_key(i)] > ranks[EXTRA] and not s.on
                and r.configs[i].get("kind") != "dishwasher" and not s.manual_forced
                and s.manual_until <= now and s.boost_until <= now
                and not s.deadline_force and not s.deadline_urgent and not s.planner_grid_force}
