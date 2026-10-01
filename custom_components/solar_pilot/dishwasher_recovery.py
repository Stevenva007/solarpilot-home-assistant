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

from copy import deepcopy
import hashlib
import re
from typing import Any

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


def _usable(state, *, button=False) -> bool:
    if state is None or getattr(state, "attributes", {}).get("restored"):
        return False
    raw = str(getattr(state, "state", "")).casefold()
    # A HA button that has never been pressed legitimately reports unknown.
    if button:
        return raw != "unavailable"
    return raw not in {"unavailable", "unknown", "none", ""}


def _candidate_rows(hass):
    registry = er.async_get(hass)
    groups: dict[str, list[tuple[str, Any, Any, str]]] = {}
    for state in _all_states(hass):
        entity_id = str(getattr(state, "entity_id", "") or "")
        if "." not in entity_id:
            continue
        row = registry.async_get(entity_id)
        device_id = getattr(row, "device_id", None) if row else None
        if not device_id:
            continue
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


def _pick(rows, domain: str, predicates, *, button=False):
    matches = []
    for entity_id, state, row, tag in rows:
        if entity_id.split(".", 1)[0] != domain:
            continue
        if not all(p(tag, entity_id, state, row) for p in predicates):
            continue
        matches.append((entity_id, state))
    if not matches:
        return ""
    usable = [x for x in matches if _usable(x[1], button=button)]
    chosen = usable if usable else matches
    # One role may have an old restored/unavailable duplicate plus one current
    # entity.  More than one equally usable candidate is intentionally ambiguous.
    if len(chosen) != 1:
        return ""
    return chosen[0][0]


def _contains(*needles):
    return lambda tag, *_: all(n in tag for n in needles)


def _start_pred(tag, *_):
    return "start" in tag and not any(x in tag for x in ("stopreset", "resume", "pause", "starttime"))


def discover_legacy_dishwasher(hass) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Return a complete profile only for one unambiguous same-device mapping."""
    if not any(getattr(hass, "states", None) and hass.states.get(eid) is not None for eid in LEGACY_MARKERS):
        return None, {"status": "not_applicable", "reason": "geen oudere afwas-dashboardkoppeling gevonden"}

    candidates = []
    for device_id, rows in _candidate_rows(hass).items():
        start = _pick(rows, "button", [_start_pred], button=True)
        state = _pick(rows, "sensor", [_contains("appliancestate")])
        connection = _pick(rows, "sensor", [_contains("connectivitystate")])
        remote = _pick(rows, "sensor", [_contains("remotecontrol")])
        door = _pick(rows, "binary_sensor", [_contains("doorstate")])
        program = _pick(rows, "select", [lambda tag, *_: "programuid" in tag or ("program" in tag and "endofcycle" not in tag)])
        required = (start, state, connection, remote, door, program)
        if not all(required):
            continue
        phase = _pick(rows, "sensor", [_contains("cyclephase")])
        alert = _pick(rows, "sensor", [lambda tag, *_: "alerts" in tag or "alarm" in tag])
        delay = _pick(rows, "number", [_contains("starttime")])
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

    if len(candidates) != 1:
        return None, {
            "status": "incomplete" if not candidates else "ambiguous",
            "reason": "vereiste AEG/Electrolux-koppelingen niet eenduidig op één Home Assistant-apparaat gevonden",
            "candidate_count": len(candidates),
        }
    device_id, cfg = candidates[0]
    return cfg, {
        "status": "discovered",
        "reason": "één volledige start-only afwasmachinekoppeling op hetzelfde Home Assistant-apparaat gevonden",
        "device_fingerprint": hashlib.sha256(str(device_id).encode("utf-8")).hexdigest()[:12],
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
        "source": "legacy_dashboard_same_device_registry",
    }
    auto = [x for x in out.get(RECOVERED_AUTO_KEY, []) if isinstance(x, str)]
    if cfg["id"] not in auto:
        auto.append(cfg["id"])
    out[RECOVERED_AUTO_KEY] = auto
    return out, {**info, "status": "recovered", "changed": True, "device_id": cfg["id"]}
