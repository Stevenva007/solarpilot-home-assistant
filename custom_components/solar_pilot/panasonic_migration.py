"""Versioned, private, read-only retirement of the old Panasonic writers.

Pure data migration: no Home Assistant imports, command adapters or callbacks.
The first pre-upgrade config and runtime payload are preserved for rollback in
the integration's existing private Store. They must never be restored as active
command authority by the current runtime.
"""
from __future__ import annotations

from copy import deepcopy
from collections.abc import Mapping
from .sg_config import SG_DEFAULTS, finite, normalize_config

MIGRATION_VERSION = 1
MARKER = "_panasonic_migration"
ARCHIVE_KEY = "panasonic_archive"
RETIRED_GROUPS = frozenset({"dhw", "smart_climate"})
KNOWN_DHW_FAULTS = frozenset({
    "Boileropdracht niet bevestigd; handmatige controle vereist",
    "Boileropdracht nog niet bevestigd; automatische controle loopt",
    "Onzekere boileropdracht; automatische controle loopt",
    *(f"Onzekere boileropdracht ({name}); {ending}" for name in
      ("HomeAssistantError", "TimeoutError", "ValueError") for ending in
      ("controle vereist", "automatische controle loopt")),
})


def _mapping(value):
    # HA ConfigEntry.options is an immutable mapping, while Store payloads are
    # ordinary dictionaries. Both represent the same JSON configuration data.
    return dict(value) if isinstance(value, Mapping) else {}


def _assessment(options, stored):
    dhw = _mapping(stored.get("dhw"))
    climate = _mapping(stored.get("smart_climate"))
    fault = dhw.get("fault", "")
    retired_fault = bool(isinstance(fault, str) and fault in KNOWN_DHW_FAULTS)
    unknown_fault = bool(fault and not retired_fault)
    raw_climate_faults = climate.get("command_faults")
    climate_faults = _mapping(raw_climate_faults)
    # A command journal supports only the exact known writer errors. Arbitrary
    # stored text cannot be transformed into permission to resume the site.
    known_climate_faults = bool(climate_faults) and all(
        isinstance(reason, str) and reason in {
            "Klimaatopdracht niet bevestigd; geen opdracht herhaald",
            "Opgeslagen klimaatopdracht ongeldig; geen opdracht herhaald",
        } for reason in climate_faults.values())
    unknown_climate = bool(raw_climate_faults and not known_climate_faults)
    battery = _mapping(stored.get("battery_fleet"))
    unrelated = bool(stored.get("faults") or stored.get("restart_faults")
                     or stored.get("reclaim_blocks") or battery.get("faults"))
    hold = bool(dhw.get("manual_hold") or climate.get("dashboard_overrides")
                or climate.get("manual_hold_until") or climate.get("zone_holds")
                or climate.get("manual_off"))
    removal = stored.get("removal_requested") is True or stored.get("pause_cause") == "removal"
    retired_only = (stored.get("mode") == "paused" and stored.get("pause_cause") == "command_fault"
                    and (retired_fault or known_climate_faults)
                    and not (unknown_fault or unknown_climate or unrelated or hold or removal))
    checks = []
    if any(dhw.get(k) for k in ("pending", "restart_recovery", "automatic_recovery", "needs_review")) or dhw.get("owned_target") is not None:
        checks.append("Controleer op Panasonic het gewenste normale tankdoel; oude opdrachten worden niet herhaald of teruggezet.")
    if any(climate.get(k) for k in ("pending_commands", "expected_mode", "program_leases", "solar_owned", "manual_off", "dashboard_overrides")):
        checks.append("Controleer op Panasonic de gewenste zonestanden en het native programma; SolarPilot herstelt geen AUTO/UIT-stand.")
    if unknown_fault or unknown_climate:
        checks.append("Onbekend oud foutbewijs blijft bewaard; controleer de betrokken bron of het apparaat vóór SG-ingebruikname.")
    return {"version": MIGRATION_VERSION, "changed": True,
            "retired_only_pause": retired_only, "manual_choice_preserved": hold,
            "unknown_fault_preserved": bool(unknown_fault or unknown_climate),
            "unrelated_faults_preserved": unrelated, "checks": checks,
            "reason": "Oude Panasonic-sturing is vervallen en als alleen-lezen bewijs gearchiveerd; dit bevestigt geen fysiek herstel."}


def migrate_panasonic(options, stored):
    """Return (options, Store payload, assessment) with one immutable backup.

    Existing SG settings are accepted only after a completed migration. A
    pre-migration foreign/experimental sg_boost block cannot enable a relay.
    User mode, identity, priority order, learning, retention and other command
    faults stay unchanged. The runtime decides its existing restart policy.
    """
    options = deepcopy(_mapping(options))
    stored = deepcopy(_mapping(stored))
    archive = _mapping(stored.get(ARCHIVE_KEY))
    valid_archive = (type(archive.get("version")) is int and archive["version"] == MIGRATION_VERSION
                     and archive.get("read_only") is True
                     and isinstance(archive.get("backup_options"), dict)
                     and isinstance(archive.get("backup_store"), dict))
    complete = (type(options.get(MARKER)) is int and options[MARKER] == MIGRATION_VERSION
                and valid_archive)
    if complete:
        report = deepcopy(_mapping(archive.get("assessment")))
        report["changed"] = False
        return options, stored, report

    # Store is committed before entry.options. A crash between those two saves
    # must retain the original backup and assessment rather than nest the
    # previous archive or replace it with an already-retired empty journal.
    old_options = deepcopy(archive["backup_options"] if valid_archive else options)
    old_store = deepcopy(archive["backup_store"] if valid_archive else stored)
    report = _assessment(old_options, old_store)
    dhw = _mapping(old_options.get("dhw"))
    legacy_runtime = _mapping(old_store.get("dhw"))
    # The older runtime tunables were the effective values. Archive them as
    # candidates, never re-run the old control-profile/rank migrations.
    effective = {**dhw, **_mapping(legacy_runtime.get("tunables"))}
    climate = _mapping(old_options.get("smart_climate"))
    sources = {
        "tank_temperature_entity": dhw.get("temperature_entity") or dhw.get("target_entity") or "",
        "tank_target_entity": dhw.get("target_entity") or "",
        "power_entity": dhw.get("power_entity") or "",
        "power_scope": "total" if dhw.get("power_meter_scope") == "heat_pump" else "unconfirmed",
        "activity_entity": dhw.get("space_activity_entity") or "",
        "zone_entities": deepcopy(climate.get("zone_entities") or dhw.get("cooling_entities") or []),
    }
    # A cooling binary sensor is not a zone thermostat; retain it in the backup.
    zone_values = sources["zone_entities"] if isinstance(sources["zone_entities"], list) else []
    sources["zone_entities"] = [x for x in zone_values
                               if isinstance(x, str) and x.startswith("climate.")]
    sg = normalize_config(sources)
    sg.update(enabled=False, commissioning_confirmed=False, watchdog_confirmed=False, entity_id="")
    candidates = {}
    for old_key, new_key in (("surplus_threshold_w", "threshold_w"),
                             ("estimated_heat_power_w", "expected_power_w")):
        value = finite(effective.get(old_key))
        if value is not None:
            candidates[new_key] = value
    report["legacy_candidates"] = candidates
    if candidates:
        report["checks"].append("Bevestig SG-startdrempel en vermogensraming afzonderlijk; de oude tankdoelregeling had een andere betekenis.")
    options["sg_boost"] = sg
    options[MARKER] = MIGRATION_VERSION
    for group in RETIRED_GROUPS:
        options.pop(group, None)
        stored.pop(group, None)
    # Deferred edits and old planner proposals must not revive removed writers.
    for container, key in ((options, "_live_pending"), (stored, "live_options")):
        raw = _mapping(container.get(key))
        if key == "_live_pending":
            container[key] = {k: deepcopy(v) for k, v in raw.items()
                              if not (isinstance(v, dict) and isinstance(v.get("group"), str)
                                      and v["group"] in RETIRED_GROUPS)}
        elif raw:
            container[key] = deepcopy(raw)
    plan = _mapping(stored.get("unified_planner"))
    if plan:
        # Baseline-load learning belongs to other devices; keep it. Only the
        # cached plan may contain thermal targets and is recalculated fresh.
        stored["unified_planner"] = {k: deepcopy(v) for k, v in plan.items()
                                     if k not in {"plan", "thermal_plan", "thermal_schedule"}}
    if valid_archive:
        stored[ARCHIVE_KEY] = deepcopy(archive)
    else:
        stored[ARCHIVE_KEY] = {"version": MIGRATION_VERSION, "read_only": True,
                              "backup_options": old_options, "backup_store": old_store,
                              "assessment": deepcopy(report)}
    return options, stored, report
