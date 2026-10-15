"""Read-only recovery of temporary consumer unavailability and uncertain calls.

No saved command is replayed. After a five-minute check has reconciled current
feedback, the ordinary planner and final dispatch guards decide any next action.
"""
from __future__ import annotations

from copy import deepcopy
import math
import time

from homeassistant.exceptions import HomeAssistantError

INTERVAL_S = 300.0
LEGACY_TRANSPORT_FAULTS = frozenset({
    "Opdrachtfout: HomeAssistantError; controleer het toestel",
    "Opdrachtfout: TimeoutError; controleer het toestel",
    "Geen opdrachtbevestiging: handmatige controle nodig",
})


class DeviceUnavailable(HomeAssistantError):
    """A native service is temporarily absent before any call is dispatched."""


def ambiguous_transport(error):
    """An external service failure is uncertain, not proof that nothing ran."""
    if not isinstance(error, (HomeAssistantError, TimeoutError, ConnectionError)):
        return False
    actionable = {"ServiceValidationError", "ServiceNotFound", "Unauthorized",
                  "ConfigEntryAuthFailed", "HomeAssistantAuthError"}
    pending, seen = [error], set()
    while pending and len(seen) < 16:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if any(cls.__name__ in actionable for cls in type(current).__mro__):
            return False
        pending.extend(cause for cause in (current.__cause__, current.__context__)
                       if isinstance(cause, BaseException) and id(cause) not in seen)
    return True


def _finite(value, default=None):
    if isinstance(value, bool):
        return default
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return default
    return number if math.isfinite(number) else default


class DeviceRetry:
    """A per-device waiting journal; unrelated trustworthy loads may continue."""

    def __init__(self, runtime):
        self.r = runtime
        self.records = {}
        # Observation evidence is deliberately not restored as a new recovery.
        # Each captured telemetry row preserves the actual collecting moment.
        self.recovered = {}

    def mark_recovered(self, device_id, now, reason):
        """Record reconciliation, never a physical start or permission to act."""
        self.recovered[device_id] = {"at_wall": time.time(), "at_monotonic": now,
                                     "reason": reason}

    def recovery_overview(self, device_id, now=None, wall=None):
        now = time.monotonic() if now is None else now
        wall = time.time() if wall is None else wall
        st, cfg = self.r.states[device_id], self.r.configs[device_id]
        last_on = _finite(st.last_on)
        duration = max(0.0, _finite(cfg.get("min_on_s"), 0.0))
        running = bool(st.owned and st.on and last_on is not None and 0 <= last_on <= now)
        elapsed = max(0.0, now - last_on) if running else None
        remaining = max(0.0, duration - elapsed) if elapsed is not None else 0.0
        item = self.recovered.get(device_id, {})
        reference_wall = (item.get("at_wall") if running and item.get("at_monotonic") == last_on
                          else wall - elapsed if elapsed is not None else None)
        return {
            "reconciled_at_wall": item.get("at_wall"),
            "reconciliation_reason": item.get("reason"),
            "minimum_run": {
                "configured_s": duration,
                "active": bool(running and st.available and remaining > 0),
                "status_confirmed": bool(st.available),
                "reference_at_wall": reference_wall,
                "until_wall": reference_wall + duration if reference_wall is not None else None,
                "remaining_s": math.ceil(remaining),
                "physical_start_confirmed": False,
            },
        }

    def waiting(self, device_id):
        return device_id in self.records

    def command_waiting(self, device_id):
        return self.records.get(device_id, {}).get("state") == "command_wait"

    def snapshot(self):
        return {"schema": 1, "records": deepcopy(self.records)}

    def restore(self, data):
        self.records = {}
        self.recovered = {}
        if not isinstance(data, dict) or data.get("schema") != 1:
            return
        records = data.get("records", {})
        if not isinstance(records, dict):
            return
        wall = time.time()
        for device_id, item in records.items():
            if device_id not in self.r.configs or not isinstance(item, dict):
                continue
            state = item.get("state")
            issued = _finite(item.get("issued_wall"))
            due = _finite(item.get("next_check_wall"))
            target = _finite(item.get("requested_w"))
            previous = _finite(item.get("previous_w"), 0.0)
            if (state not in ("source_wait", "command_wait") or issued is None
                    or issued < 0 or due is None or target is None or target < 0
                    or previous < 0):
                continue
            if issued > wall + 5:
                issued = wall  # A clock jump still requires a new current report.
            self.records[device_id] = {
                "state": state, "issued_wall": issued,
                "next_check_wall": min(due, wall + INTERVAL_S),
                "requested_w": target, "previous_w": previous,
                "max_runtime": item.get("max_runtime") is True,
                "retry_dispatch": item.get("retry_dispatch") is True,
                "reason": str(item.get("reason", ""))[:240],
            }

    def migrate_legacy(self, leases):
        """Only exact old ordinary transport messages become read-only waits.

        Old stores lack a reliable failure time. Require a new native report
        after this upgrade before releasing their unknown-outcome quarantine.
        Appliance START tickets and actual configuration faults are untouched.
        """
        wall = time.time()
        for device_id, reason in tuple(self.r.faults.items()):
            cfg = self.r.configs[device_id]
            ordinary = reason in LEGACY_TRANSPORT_FAULTS and cfg.get("kind") in ("switch", "number")
            appliance = (cfg.get("kind") == "dishwasher"
                         and reason.startswith("START-uitkomst onzeker na herstart;")
                         and self.r.dishwasher.tickets.get(device_id, {}).get("attempted"))
            if (not (ordinary or appliance) or self.configuration_fault(device_id)
                    or (device_id in self.r._restart_faults and not appliance)):
                continue
            lease = leases.get(device_id)
            target = _finite(lease.get("watts")) if isinstance(lease, dict) else None
            owned_evidence = target is not None and target >= 0
            if not owned_evidence and not appliance:
                # An old message alone is not permission to take over an ON
                # appliance. Normal observation keeps any current ON external.
                self.records[device_id] = self._record(
                    "source_wait", wall, 0.0, 0.0,
                    "Wacht op betrouwbare toestelgegevens; geen beheer overgenomen")
            else:
                target = target if owned_evidence else float(cfg["nominal_w"])
                self.records[device_id] = self._record(
                    "command_wait", wall, max(0.0, target), max(0.0, target),
                    "Wacht op een nieuwe toestelterugmelding; controle elke 5 minuten")
            self.r.faults.pop(device_id, None)
            if appliance:
                self.r._restart_faults.pop(device_id, None)

    @staticmethod
    def _record(state, wall, target, previous, reason, max_runtime=False):
        return {"state": state, "issued_wall": wall,
                "next_check_wall": wall + INTERVAL_S, "requested_w": target,
                "previous_w": previous, "max_runtime": bool(max_runtime),
                "reason": reason}

    def configuration_fault(self, device_id):
        r, cfg = self.r, self.r.configs[device_id]
        authority = r._profile_authority_error(cfg)
        if authority:
            return authority
        if cfg.get("power_entity"):
            if not r._dedicated_meter(device_id):
                return "Vermogensmeter is niet exclusief voor dit toestel"
            power_obj = r.hass.states.get(cfg["power_entity"])
            value = r._number(cfg["power_entity"])
            if power_obj is not None and value is not None:
                if power_obj.attributes.get("unit_of_measurement") not in ("W", "kW"):
                    return "Eenheid van vermogensmeter is onjuist"
                if value < -1:
                    return "Vermogensmeting onbetrouwbaar"
        if cfg.get("kind") != "number":
            return ""
        obj = r.hass.states.get(cfg.get("number_entity", ""))
        value = r._number(cfg.get("number_entity"))
        if obj is None or obj.attributes.get("restored") or value is None:
            return ""
        if cfg.get("control_unit") and obj.attributes.get("unit_of_measurement") != cfg["control_unit"]:
            return "Eenheid van vermogensregelaar is gewijzigd"
        try:
            valid = (float(obj.attributes["min"]) <= cfg["min_units"]
                     <= cfg["max_units"] <= float(obj.attributes["max"]))
        except (KeyError, TypeError, ValueError):
            valid = False
        return "" if valid else "Bereik van vermogensregelaar is gewijzigd"

    def source_reason(self, device_id):
        r, cfg = self.r, self.r.configs[device_id]
        if r._restart_active(cfg) is None:
            return "Toestelgegevens tijdelijk niet beschikbaar; controle elke 5 minuten"
        if cfg.get("power_entity"):
            watts, _ = r._power(cfg["power_entity"])
            if watts is None:
                return "Vermogensmeting tijdelijk niet beschikbaar; controle elke 5 minuten"
        return ""

    def begin(self, device_id, watts, issued_wall, previous_w=0.0, *, max_runtime=False):
        wall = time.time()
        record = self._record("command_wait", wall, max(0.0, float(watts)),
                              max(0.0, float(previous_w)),
                              "Wacht op toestelterugmelding; controle elke 5 minuten",
                              max_runtime)
        issued = _finite(issued_wall)
        record["issued_wall"] = issued if issued is not None else wall
        self.records[device_id] = record
        st = self.r.states[device_id]
        st.available = False
        st.start_since = None
        if self.r.pending and self.r.pending.get("id") == device_id:
            self.r.pending = None
        return record

    async def hold(self, device_id, watts, issued_wall, previous_w=0.0, *, max_runtime=False):
        record = self.begin(device_id, watts, issued_wall, previous_w, max_runtime=max_runtime)
        self.r.consumer_history.event(device_id, record["reason"])
        self.r.note(self.r.configs[device_id]["name"] + ": " + record["reason"] + ".")
        await self.r.store.async_save(self.r._snapshot())

    async def defer_unsent(self, device_id):
        wall = time.time()
        record = self._record("source_wait", wall, 0.0, 0.0,
                              "Toestelactie tijdelijk niet beschikbaar; controle elke 5 minuten")
        record["retry_dispatch"] = True
        self.records[device_id] = record
        st = self.r.states[device_id]
        st.available = False
        st.start_since = None
        self.r.consumer_history.event(device_id, record["reason"])
        await self.r.store.async_save(self.r._snapshot())

    def observe(self):
        """Describe passive source waits; an actual new report may resolve early."""
        r, wall = self.r, time.time()
        changed = False
        for device_id in tuple(self.records):
            if device_id not in r.configs or device_id not in r.states:
                self.records.pop(device_id, None)
                changed = True
        for device_id, st in r.states.items():
            if self.command_waiting(device_id):
                continue
            if device_id in r.faults or self.configuration_fault(device_id):
                if self.records.pop(device_id, None) is not None:
                    changed = True
                continue
            item = self.records.get(device_id)
            if item and item.get("retry_dispatch") and wall < item["next_check_wall"]:
                st.available = False
                st.start_since = None
                continue
            reason = self.source_reason(device_id)
            if not reason:
                if self.records.pop(device_id, None) is not None:
                    changed = True
                continue
            item = self.records.get(device_id)
            if item is None:
                self.records[device_id] = self._record(
                    "source_wait", wall, max(0.0, st.target_w),
                    max(0.0, st.target_w), reason)
                changed = True
            elif wall >= item["next_check_wall"]:
                item["next_check_wall"] = wall + INTERVAL_S
                changed = True
            # A missing report is not a device fault or a measured zero.
            if st.fault in ("", "Vermogensmeting onbetrouwbaar"):
                st.fault = ""
                st.available = False
        if changed:
            r.store.async_delay_save(r._snapshot, 1)

    def _post_command_report(self, cfg, issued_wall):
        r = self.r
        if cfg.get("kind") == "dishwasher":
            reading = r.dishwasher.readings.get(cfg["id"])
            return bool(reading and reading.stamp > issued_wall
                        and (reading.active is True or reading.finished))
        key = "active_entity" if cfg.get("kind") == "script" else "control_entity"
        obj = r.hass.states.get(cfg.get(key, ""))
        stamp = r._reported_wall(obj)
        if stamp is None or stamp <= issued_wall:
            return False
        if cfg.get("kind") == "number":
            number_obj = r.hass.states.get(cfg.get("number_entity", ""))
            number_stamp = r._reported_wall(number_obj)
            if number_stamp is None or number_stamp <= issued_wall:
                return False
        return True

    async def tick(self, now):
        r, wall = self.r, time.time()
        changed = False
        for device_id, item in tuple(self.records.items()):
            if device_id not in r.configs or device_id not in r.states:
                self.records.pop(device_id, None)
                changed = True
                continue
            if item["state"] != "command_wait" or wall < item["next_check_wall"]:
                continue
            item["next_check_wall"] = wall + INTERVAL_S
            changed = True
            fault = self.configuration_fault(device_id)
            if fault:
                r.faults[device_id] = fault
                self.records.pop(device_id, None)
                continue
            cfg, st = r.configs[device_id], r.states[device_id]
            if self.source_reason(device_id):
                continue
            active = r._restart_active(cfg)
            if active is None or not self._post_command_report(cfg, item["issued_wall"]):
                continue
            if cfg.get("kind") == "dishwasher":
                reading = r.dishwasher.readings[device_id]
                # An attempted one-shot START is never made available again.
                if active is True:
                    r.dishwasher.confirmed(device_id)
                    r.dishwasher_app.event(cfg, cfg.get("dishwasher_state_entity"), reading.raw, wall)
                    r.dishwasher_app.cancel(cfg, "APP-aanvraag verbruikt door bevestigde cyclus")
                elif reading.finished:
                    r.dishwasher.review(device_id)
                    r.dishwasher_app.cancel(cfg, "APP-aanvraag verbruikt door bevestigde cyclus")
                else:
                    continue
            if active:
                target = item["requested_w"] or item["previous_w"] or float(cfg["nominal_w"])
                if cfg.get("kind") == "number" and not r._target_matches(cfg, target):
                    st.owned = False
                    st.target_w = 0.0
                    st.manual_until = now + cfg["manual_hold_s"]
                    st.manual_forced = st.manual_stop_requested = False
                else:
                    st.owned = True
                    st.target_w = target
                # A missing interval can contain a restart: protect a full run.
                st.on, st.last_on = True, now
                if cfg["non_interruptible"]:
                    st.cycle_armed = False
            else:
                st.owned, st.on, st.target_w = False, False, 0.0
                st.last_off = now
                st.manual_forced = st.manual_stop_requested = False
                if item.get("max_runtime"):
                    r.faults[device_id] = "Maximale looptijd bereikt: controleer en wis de melding"
            st.available, st.observed_once = True, True
            st.start_since = st.stop_since = None
            st.fault = r.faults.get(device_id, "")
            self.records.pop(device_id, None)
            r.recovery.pop(device_id, None)
            self.mark_recovered(device_id, now, "command_feedback")
            r.consumer_history.event(device_id, "Toestelterugmelding hersteld; actuele voorwaarden opnieuw beoordelen")
            r.note(cfg["name"] + ": terugmelding hersteld; actuele voorwaarden worden opnieuw beoordeeld.")
        if changed:
            await r.store.async_save(r._snapshot())

    def overview(self, device_id):
        item = self.records.get(device_id)
        if (item is None or device_id in self.r.faults
                or self.configuration_fault(device_id) or self.r.states[device_id].fault):
            return {"active": False}
        wall = time.time()
        return {"active": True, "state": item["state"], "interval_s": int(INTERVAL_S),
                "next_check_wall": item["next_check_wall"],
                "remaining_s": math.ceil(max(0.0, min(INTERVAL_S, item["next_check_wall"] - wall))),
                "observed_wall": wall, "reason": item["reason"]}
