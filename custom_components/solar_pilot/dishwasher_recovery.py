"""Conservative beta.38 recovery for the legacy AEG dishwasher profile.

This is deliberately a *migration*, not a generic appliance auto-configurator.
Older SolarPilot/Home Assistant work used a dashboard helper for the dishwasher,
while beta.35 analysis can show that the matching SolarPilot ``devices`` row was
missing.  When that exact legacy marker is present, beta.38 may reconstruct the
start-only profile from Home Assistant's entity registry.

Safety properties:
- no AEG actuator/source entity_id or private HA device id is hard-coded;
- every required source must resolve to one and the same HA device;
- the START button must be the unique usable START command (never PAUSE/RESUME/
  STOPRESET);
- APP permission still has to transition to exact ``Enabled`` after startup;
- no START is sent by this migration itself;
- a running programme is never stopped or reset;
- an existing dishwasher profile is never overwritten.
"""
from __future__ import annotations

import asyncio
from collections import Counter
from copy import deepcopy
from datetime import timedelta
import hashlib
import re
import time
from typing import Any

from homeassistant.core import callback
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers import entity_registry as er

from .const import DEVICE_DEFAULTS
from .dishwasher import normalize_config

LEGACY_MARKERS = (
    "sensor.afwasmachine_dashboardstatus",
    "binary_sensor.afwasmachine_actief",
)
RECOVERY_KEY = "_beta38_dishwasher_recovery"
RECOVERED_AUTO_KEY = "_beta38_recovered_auto_devices"
REPAIR39_KEY = "_beta39_dishwasher_repair"
RECOVERY_SOURCE = "legacy_dashboard_same_device_registry"

REQUIRED_ROLES = (
    "start_button",
    "appliance_state",
    "connection_state",
    "remote_control",
    "door_state",
    "program",
)

# The startup-order workaround is intentionally temporary.  Ten minutes covers
# slow cloud/entity setup without turning this migration into a permanent
# appliance auto-discovery service.
RETRY_INTERVAL_S = 10
RETRY_WINDOW_S = 600


def _norm(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def _all_states(hass):
    states = getattr(hass, "states", None)
    if states is None:
        return []
    fn = getattr(states, "async_all", None)
    if callable(fn):
        return list(fn())
    data = getattr(states, "data", None)
    if isinstance(data, dict):
        out = []
        for entity_id, obj in data.items():
            if not getattr(obj, "entity_id", None):
                try:
                    obj.entity_id = entity_id
                except Exception:
                    pass
            out.append(obj)
        return out
    return []


REJECTION_REASONS = ("disabled", "restored", "not_loaded", "unavailable")


def _rejection(state, row, *, button=False) -> str:
    if getattr(row, "disabled_by", None) is not None:
        return "disabled"
    if state is None:
        return "not_loaded"
    if getattr(state, "attributes", {}).get("restored"):
        return "restored"
    raw = str(getattr(state, "state", "")).casefold()
    # A HA button that has never been pressed legitimately reports unknown.
    if button:
        return "" if raw not in {"unavailable", "none", ""} else "unavailable"
    return "" if raw not in {"unavailable", "unknown", "none", ""} else "unavailable"


def _registry_pairs(registry):
    entries = getattr(registry, "entities", None)
    if entries is not None:
        values = entries.values() if hasattr(entries, "values") else entries
        return [(str(getattr(row, "entity_id", "") or ""), row) for row in values]
    rows = getattr(registry, "rows", {})
    return list(rows.items()) if isinstance(rows, dict) else []


def _candidate_rows(hass):
    registry = er.async_get(hass)
    states = {str(getattr(state, "entity_id", "") or ""): state for state in _all_states(hass)}
    rows = {entity_id: row for entity_id, row in _registry_pairs(registry) if entity_id}
    # Registry entries often exist before their integration publishes states.
    # Conversely, explicit test/legacy states can precede a registry view.
    for entity_id in list(states):
        if entity_id and entity_id not in rows:
            row = registry.async_get(entity_id)
            if row is not None:
                rows[entity_id] = row
    groups: dict[str, list[tuple[str, Any, Any, str]]] = {}
    for entity_id, row in rows.items():
        if "." not in entity_id:
            continue
        device_id = getattr(row, "device_id", None) if row else None
        if not device_id:
            continue
        state = states.get(entity_id)
        friendly = getattr(state, "attributes", {}).get("friendly_name", "")
        original = getattr(row, "original_name", "") or ""
        tag = _norm(" ".join((entity_id, friendly, original)))
        # Only consider an appliance whose own entities clearly identify it as a
        # dishwasher.  AEG/Electrolux is intentionally a preference, not a sole
        # criterion, so renamed Dutch/English entities remain discoverable.
        if not any(x in tag for x in ("afwasmachine", "vaatwas", "dishwasher")):
            continue
        groups.setdefault(str(device_id), []).append((entity_id, state, row, tag))
    return groups


def _pick(rows, domains, predicates, *, button=False):
    """Return one role plus privacy-safe cardinality diagnostics."""
    domains = {domains} if isinstance(domains, str) else set(domains)
    matches = []
    for entity_id, state, row, tag in rows:
        if entity_id.split(".", 1)[0] not in domains:
            continue
        if not all(p(tag, entity_id, state, row) for p in predicates):
            continue
        matches.append((entity_id, state, row))
    rejected = Counter()
    usable = []
    for entity_id, state, row in matches:
        reason = _rejection(state, row, button=button)
        if reason:
            rejected[reason] += 1
        else:
            usable.append(entity_id)
    diagnostics = {
        "status": "selected" if len(usable) == 1 else "ambiguous" if len(usable) > 1 else "missing",
        "candidate_count": len(matches),
        "usable_count": len(usable),
        "rejected": {reason: rejected[reason] for reason in REJECTION_REASONS},
    }
    # One role may have an old restored/unavailable duplicate plus one current
    # entity. More than one live candidate is intentionally ambiguous; zero live
    # candidates never falls back to a restored/unavailable/disabled row.
    return (usable[0] if len(usable) == 1 else ""), diagnostics


def _contains(*needles):
    return lambda tag, *_: all(n in tag for n in needles)


def _start_pred(tag, *_):
    return "start" in tag and not any(x in tag for x in ("stopreset", "resume", "pause", "starttime"))


def _role_summary(per_device: list[dict[str, dict[str, Any]]]) -> dict[str, dict[str, Any]]:
    """Summarise candidate counts without leaking entity or HA device ids."""
    out = {}
    for role in REQUIRED_ROLES:
        rows = [item[role] for item in per_device]
        usable = sum(int(x.get("usable_count", 0)) for x in rows)
        count = sum(int(x.get("candidate_count", 0)) for x in rows)
        rejected = {reason: sum(int(x.get("rejected", {}).get(reason, 0)) for x in rows)
                    for reason in REJECTION_REASONS}
        status = "selected" if usable == 1 else "ambiguous" if usable > 1 else "missing"
        out[role] = {"status": status, "candidate_count": count,
                     "usable_count": usable, "rejected": rejected}
    return out


def discover_legacy_dishwasher(hass) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Return a complete profile only for one unambiguous same-device mapping."""
    candidates = []
    evaluated = []
    for device_id, rows in _candidate_rows(hass).items():
        start, start_info = _pick(rows, "button", [_start_pred], button=True)
        state, state_info = _pick(rows, "sensor", [_contains("appliancestate")])
        connection, connection_info = _pick(rows, "sensor", [_contains("connectivitystate")])
        remote, remote_info = _pick(rows, "sensor", [_contains("remotecontrol")])
        door, door_info = _pick(rows, "binary_sensor", [_contains("doorstate")])
        program, program_info = _pick(rows, ("select", "sensor"), [lambda tag, *_: "programuid" in tag or ("program" in tag and "endofcycle" not in tag)])
        role_info = {
            "start_button": start_info,
            "appliance_state": state_info,
            "connection_state": connection_info,
            "remote_control": remote_info,
            "door_state": door_info,
            "program": program_info,
        }
        evaluated.append((device_id, role_info))
        required = (start, state, connection, remote, door, program)
        if not all(required):
            continue
        phase, _ = _pick(rows, "sensor", [_contains("cyclephase")])
        alert, _ = _pick(rows, "sensor", [lambda tag, *_: "alerts" in tag or "alarm" in tag])
        delay, _ = _pick(rows, "number", [_contains("starttime")])
        digest = hashlib.sha256(str(device_id).encode("utf-8")).hexdigest()[:16]
        cfg = {
            **DEVICE_DEFAULTS,
            "id": f"dishwasher_{digest}",
            "name": "AEG/Electrolux afwasmachine",
            "kind": "dishwasher",
            "appliance_type": "dishwasher",
            "priority": 10,
            "nominal_w": 2000,
            "start_delay_s": 300,
            "ack_timeout_s": 300,
            "max_on_s": 21600,
            "wallbox_precedence": "consumer_first",
            "start_button": start,
            "dishwasher_state_entity": state,
            "dishwasher_connection_entity": connection,
            "dishwasher_remote_entity": remote,
            "dishwasher_door_entity": door,
            "cycle_program_entity": program,
            "dishwasher_phase_entity": phase,
            # Alert is optional and beta.38 proved that auto-binding a numeric aggregate
            # can create a permanent false block when no explicit DISH_ALARM flags exist.
            # Keep optional alarm unbound until the user verifies a usable alarm source.
            "dishwasher_alert_entity": "",
            "dishwasher_delay_entity": delay,
            "dishwasher_alert_mode": "state",
            "dishwasher_arming_mode": "app",
            "dishwasher_remote_states": "Enabled",
            "dishwasher_ready_states": "Ready To Start",
            "dishwasher_running_states": "Running;Washing;Prewash;Pre wash;Main wash;Rinsing;Drying;Ado Drying;Paused",
            "dishwasher_finished_states": "End Of Cycle",
            "dishwasher_connected_states": "Connected",
            "dishwasher_closed_states": "off;Closed",
            "dishwasher_mapping_confirmed": True,
            "dishwasher_start_deadline": "13:00:00",
            "dishwasher_after_deadline": "next_day",
            "dishwasher_deadline_grid_allowed": True,
            "dishwasher_deadline_grace_min": 120,
            "dishwasher_priority_enabled": True,
            "dishwasher_ev_solar_priority": True,
        }
        candidates.append((device_id, normalize_config(cfg)))

    # Prefer diagnostics for the uniquely complete same-device mapping. Without
    # one, report the best candidate device; tied devices are aggregated so
    # duplicate usable roles become explicit ambiguity without leaking ids.
    if len(candidates) == 1:
        selected_device = candidates[0][0]
        roles = next(info for device_id, info in evaluated if device_id == selected_device)
    else:
        scored = [(sum(value["status"] == "selected" for value in info.values()), info)
                  for _device_id, info in evaluated]
        best = max((score for score, _info in scored), default=0)
        role_rows = [info for score, info in scored if score == best and (score > 0 or len(scored) == 1)]
        roles = _role_summary(role_rows)

    marker_count = sum(
        getattr(hass, "states", None) is not None and hass.states.get(entity_id) is not None
        for entity_id in LEGACY_MARKERS
    )
    marker = {"status": "selected" if marker_count else "missing", "loaded_count": marker_count}
    if not marker_count:
        return None, {
            "status": "not_applicable",
            "reason": "geen oudere afwas-dashboardkoppeling gevonden",
            "legacy_marker": marker,
            "roles": roles,
        }
    if len(candidates) != 1:
        return None, {
            "status": "incomplete" if not candidates else "ambiguous",
            "reason": "vereiste AEG/Electrolux-koppelingen niet eenduidig op één Home Assistant-apparaat gevonden",
            "candidate_count": len(candidates),
            "legacy_marker": marker,
            "roles": roles,
        }
    device_id, cfg = candidates[0]
    return cfg, {
        "status": "discovered",
        "reason": "één volledige start-only afwasmachinekoppeling op hetzelfde Home Assistant-apparaat gevonden",
        "device_fingerprint": hashlib.sha256(str(device_id).encode("utf-8")).hexdigest()[:12],
        "legacy_marker": marker,
        "roles": roles,
    }


def _repair_beta38_profile(hass, options: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Repair only the exact profile that beta.38 reconstructed automatically.

    This does not touch manually-created dishwasher profiles. It restores the full
    running-state set from the earlier AEG logic and removes only an automatically
    selected alarm source that cannot expose explicit safety-relevant AEG flags.
    """
    out = deepcopy(options or {})
    meta = out.get(RECOVERY_KEY, {}) if isinstance(out.get(RECOVERY_KEY), dict) else {}
    device_id = meta.get("device_id") if meta.get("status") == "recovered" else None
    if not device_id:
        return out, {"status": "not_applicable", "changed": False}
    if isinstance(out.get(REPAIR39_KEY), dict) and out[REPAIR39_KEY].get("schema") == 1:
        return out, {"status": "already_repaired", "changed": False, "device_id": device_id}
    devices = [deepcopy(x) for x in out.get("devices", []) if isinstance(x, dict)]
    target = next((d for d in devices if d.get("id") == device_id and d.get("kind") == "dishwasher"), None)
    if target is None:
        return out, {"status": "missing_recovered_profile", "changed": False, "device_id": device_id}

    changes = []
    if target.get("dishwasher_running_states") == "Running;Paused":
        target["dishwasher_running_states"] = "Running;Washing;Prewash;Pre wash;Main wash;Rinsing;Drying;Ado Drying;Paused"
        changes.append("running_states")

    alert_eid = target.get("dishwasher_alert_entity", "")
    if alert_eid and target.get("dishwasher_alert_mode") == "aeg_attributes":
        alert = hass.states.get(alert_eid) if getattr(hass, "states", None) else None
        attrs = getattr(alert, "attributes", {}) if alert else {}
        flags = {k: v for k, v in attrs.items() if k.startswith("DISH_ALARM_") and k not in
                 ("DISH_ALARM_RINSE_AID_LOW", "DISH_ALARM_SALT_MISSING")}
        if not flags:
            target["dishwasher_alert_entity"] = ""
            target["dishwasher_alert_mode"] = "state"
            changes.append("unverified_auto_alarm")

    out["devices"] = devices
    out[REPAIR39_KEY] = {"schema": 1, "device_id": device_id, "changes": list(changes)}
    return out, {"status": "repaired" if changes else "checked", "changed": True,
                 "device_id": device_id, "changes": changes}


def recover_legacy_dishwasher(hass, options: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Add the missing legacy profile once; never overwrite configured devices."""
    out, repair = _repair_beta38_profile(hass, options or {})
    devices = [deepcopy(x) for x in out.get("devices", []) if isinstance(x, dict)]
    existing = [d for d in devices if d.get("kind") == "dishwasher"]
    if existing:
        repaired = repair.get("status") in ("repaired", "checked", "already_repaired")
        return out, {"status": repair.get("status") if repaired else "already_configured",
                     "changed": bool(repair.get("changed")) if repaired else False,
                     "device_id": existing[0].get("id"),
                     "repair_changes": repair.get("changes", []) if repaired else []}

    # The recovery marker is the durable one-shot boundary.  If its recovered
    # profile was later removed, do not silently recreate it or restore Auto.
    meta = out.get(RECOVERY_KEY, {}) if isinstance(out.get(RECOVERY_KEY), dict) else {}
    if meta.get("status") == "recovered":
        return out, {"status": "previously_recovered", "changed": False,
                     "reason": "eerder hersteld profiel is niet meer aanwezig; geen automatische heraanmaak"}

    cfg, info = discover_legacy_dishwasher(hass)
    if cfg is None:
        return out, {**info, "changed": False}

    # Never duplicate a source already owned by another configured consumer.
    refs = {cfg.get("start_button"), cfg.get("dishwasher_state_entity")}
    for row in devices:
        if refs & {row.get("start_button"), row.get("dishwasher_state_entity"), row.get("control_entity"), row.get("active_entity")} - {None, ""}:
            return out, {"status": "conflict", "changed": False, "reason": "bron is al aan een ander SolarPilot-profiel gekoppeld"}

    devices.append(cfg)
    out["devices"] = devices
    out[RECOVERY_KEY] = {
        "schema": 1,
        "status": "recovered",
        "device_id": cfg["id"],
        "source": RECOVERY_SOURCE,
    }
    auto = [x for x in out.get(RECOVERED_AUTO_KEY, []) if isinstance(x, str)]
    if cfg["id"] not in auto:
        auto.append(cfg["id"])
    out[RECOVERED_AUTO_KEY] = auto
    return out, {**info, "status": "recovered", "changed": True, "device_id": cfg["id"]}


def recovery_watch_entity_ids(hass) -> list[str]:
    """Return only legacy markers and registry rows visibly tied to a dishwasher."""
    ids = set(LEGACY_MARKERS)
    registry = er.async_get(hass)
    entries = getattr(registry, "entities", None)
    if entries is not None:
        values = entries.values() if hasattr(entries, "values") else entries
        pairs = ((getattr(row, "entity_id", ""), row) for row in values)
    else:
        # Small explicit test doubles commonly expose their registry as a dict.
        rows = getattr(registry, "rows", {})
        pairs = rows.items() if isinstance(rows, dict) else ()
    for entity_id, row in pairs:
        entity_id = str(entity_id or "")
        domain = entity_id.split(".", 1)[0]
        if domain not in {"button", "sensor", "binary_sensor", "select", "number"}:
            continue
        tag = _norm(" ".join((entity_id, str(getattr(row, "original_name", "") or ""))))
        if any(word in tag for word in ("afwasmachine", "vaatwas", "dishwasher")):
            ids.add(entity_id)
    return sorted(ids)


class LegacyDishwasherRecoveryRetry:
    """Bounded post-start retry for the beta.38 legacy recovery only.

    It never calls an actuator or ``tick``.  A recovered row is applied through
    ``LiveOptions`` so the APP listener and virtual platforms are refreshed in
    place.  The one recovered id alone receives its historical one-shot Auto
    mode; all ordinary live-added profiles remain Disabled.
    """

    def __init__(self, runtime):
        self.r = runtime
        self.started = time.monotonic()
        self.attempts = 0
        self._closed = False
        self._unsub_states = None
        self._unsub_timer = None
        self._watched = ()
        self._attempt_lock = asyncio.Lock()
        self._task = None

    async def start(self):
        if any(c.get("kind") == "dishwasher" for c in self.r.configs.values()):
            self.close()
            return False
        if await self.attempt():
            return True
        self._bind_state_listener()
        if not self._closed:
            self._unsub_timer = async_track_time_interval(
                self.r.hass, self._on_interval, timedelta(seconds=RETRY_INTERVAL_S)
            )
        return False

    def _bind_state_listener(self):
        ids = tuple(recovery_watch_entity_ids(self.r.hass))
        if ids == self._watched:
            return
        if self._unsub_states:
            self._unsub_states()
        self._watched = ids
        self._unsub_states = async_track_state_change_event(self.r.hass, ids, self._on_state)

    @callback
    def _on_state(self, _event):
        if self._closed or (self._task is not None and not self._task.done()):
            return
        self._task = self.r.hass.async_create_task(self.attempt())

    async def _on_interval(self, _now):
        await self.attempt()

    async def attempt(self):
        async with self._attempt_lock:
            if self._closed:
                return False
            if time.monotonic() - self.started >= RETRY_WINDOW_S:
                info = dict(getattr(self.r, "dishwasher_recovery_info", {}))
                self.r.dishwasher_recovery_info = {**info, "retry_active": False,
                                                   "retry_attempts": self.attempts}
                self.close()
                self.r.publish()
                return False
            self.attempts += 1
            # Serialize the read/merge/persist/apply sequence with ordinary live
            # option saves so a concurrent user edit cannot be overwritten.
            async with self.r._lock:
                # Unload can close the retry while it is waiting for an active
                # dispatch cycle. Never persist a migration after that boundary.
                if self._closed:
                    return False
                options, info = recover_legacy_dishwasher(self.r.hass, dict(self.r.entry.options))
                if info.get("changed"):
                    recovered_id = info.get("device_id")
                    was_known = recovered_id in self.r.configs or recovered_id in self.r.device_modes
                    updater = getattr(getattr(self.r.hass, "config_entries", None), "async_update_entry", None)
                    if updater is not None:
                        updater(self.r.entry, options=deepcopy(options))
                    else:  # Explicit test doubles only.
                        self.r.entry.options = deepcopy(options)
                    await self.r.live_options.accept(options)
                    exact_recovery = (
                        info.get("status") == "recovered"
                        and options.get(RECOVERY_KEY, {}).get("source") == RECOVERY_SOURCE
                        and options.get(RECOVERY_KEY, {}).get("device_id") == recovered_id
                        and recovered_id in options.get(RECOVERED_AUTO_KEY, [])
                    )
                    if exact_recovery and not was_known and recovered_id in self.r.configs:
                        self.r.device_modes[recovered_id] = "auto"
                        self.r.store.async_delay_save(self.r._snapshot, 1)
            terminal = info.get("status") in {"already_configured", "previously_recovered"}
            self.r.dishwasher_recovery_info = {
                **info,
                "retry_active": not info.get("changed") and not terminal,
                "retry_attempts": self.attempts,
            }
            if not info.get("changed"):
                if terminal:
                    self.close()
                else:
                    self._bind_state_listener()
                self.r.publish()
                return False

            recovered_id = info.get("device_id")
            self.r.dishwasher_recovery_info = {**info, "retry_active": False,
                                               "retry_attempts": self.attempts}
            self.r.note(f'{self.r.configs[recovered_id]["name"]}: ontbrekend beta.38-profiel na late Home Assistant-start hersteld; APP-vrijgave blijft verplicht.')
            self.close()
            self.r.publish()
            return True

    def close(self):
        self._closed = True
        for unsub in (self._unsub_states, self._unsub_timer):
            if unsub:
                unsub()
        self._unsub_states = None
        self._unsub_timer = None
