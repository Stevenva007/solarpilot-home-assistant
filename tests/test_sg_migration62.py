"""Pure migration contract: private backup, no command authority or replay."""
from copy import deepcopy
import pytest

from custom_components.solar_pilot.panasonic_migration import (
    migrate_panasonic, ARCHIVE_KEY, MARKER, KNOWN_DHW_FAULTS,
)


def legacy():
    options = {"devices": [{"id": "dryer", "name": "Dryer", "control_entity": "switch.dryer"}],
               "settings": {"reserve_w": 275}, "priority_board": {"schema": 2, "order": ["wallbox", "device:washer", "dhw_extra", "device:dryer"]},
               "dhw": {"target_entity": "water_heater.generic_tank", "temperature_entity": "sensor.generic_tank",
                       "power_entity": "sensor.generic_heatpump_power", "power_meter_scope": "heat_pump",
                       "surplus_threshold_w": 3700, "estimated_heat_power_w": 4100, "enabled": True},
               "smart_climate": {"zone_entities": ["climate.zone_a", "climate.zone_b"], "control_enabled": True}}
    stored = {"mode": "solar", "auto_resume_after_restart": False, "device_modes": {"dryer": "auto"},
              "energy_kwh": {"dryer": 37.25}, "heatpump_learning": {"samples": [1, 2, 3]},
              "dhw": {"pending": {"target": 60}, "owned_target": 60, "automatic_recovery": {"schema": 1}, "recovery_budget": {"failure_streak": 3}},
              "smart_climate": {"profiles": {"climate.zone_a": {"samples": 125}}, "expected_mode": {"climate.zone_a": "off"}},
              "unified_planner": {"plan": {"thermal_target": 60}, "base_load": {"days": ["2026-01-01"]}}}
    return options, stored


def test_full_first_backup_exact_and_new_binding_never_guessed():
    options, stored = legacy(); before = deepcopy((options, stored))
    new, data, report = migrate_panasonic(options, stored)
    assert (options, stored) == before
    assert data[ARCHIVE_KEY]["backup_options"] == options
    assert data[ARCHIVE_KEY]["backup_store"] == stored
    assert data[ARCHIVE_KEY]["read_only"] is True
    assert "dhw" not in new and "smart_climate" not in new
    assert "dhw" not in data and "smart_climate" not in data
    assert new["sg_boost"]["entity_id"] == ""
    assert all(new["sg_boost"][key] is False for key in ("enabled", "commissioning_confirmed", "watchdog_confirmed"))
    assert new["priority_board"] == options["priority_board"]
    assert data["mode"] == "solar" and data["auto_resume_after_restart"] is False
    assert data["heatpump_learning"] == stored["heatpump_learning"]
    assert data["energy_kwh"] == stored["energy_kwh"]
    assert data["unified_planner"]["base_load"] == stored["unified_planner"]["base_load"]
    assert "plan" not in data["unified_planner"]
    assert report["legacy_candidates"] == {"threshold_w": 3700.0, "expected_power_w": 4100.0}
    assert new["sg_boost"]["threshold_w"] == 3000 and new["sg_boost"]["expected_power_w"] == 3200


def test_idempotent_and_later_sg_permissions_preserved():
    options, stored = legacy(); new, data, report = migrate_panasonic(options, stored)
    new["sg_boost"].update(entity_id="switch.sg_contact", enabled=True, commissioning_confirmed=True, watchdog_confirmed=True)
    twice, second, report = migrate_panasonic(new, data)
    assert (twice, second) == (new, data)
    assert report["changed"] is False
    assert second[ARCHIVE_KEY] == data[ARCHIVE_KEY]


def test_crash_after_private_store_before_entry_options_keeps_original_backup():
    options, stored = legacy(); new, data, _ = migrate_panasonic(options, stored)
    retried, retried_data, _ = migrate_panasonic(options, data)
    assert retried == new
    assert retried_data[ARCHIVE_KEY] == data[ARCHIVE_KEY]
    assert ARCHIVE_KEY not in retried_data[ARCHIVE_KEY]["backup_store"]
    assert retried_data[ARCHIVE_KEY]["backup_store"]["dhw"]["pending"] == {"target": 60}


def test_partial_or_malformed_archive_never_counts_as_commissioning_authority():
    options, stored = legacy()
    options[MARKER] = 1
    options["sg_boost"] = {"entity_id": "switch.guessed", "enabled": True,
                           "commissioning_confirmed": True, "watchdog_confirmed": True}
    stored[ARCHIVE_KEY] = {"version": 1, "other_evidence": ["keep exactly"]}
    before = deepcopy(stored)
    new, data, _ = migrate_panasonic(options, stored)
    assert new["sg_boost"]["entity_id"] == "" and new["sg_boost"]["enabled"] is False
    assert data[ARCHIVE_KEY]["backup_store"] == before


@pytest.mark.parametrize("key,value", [("pending", {"target": 60}), ("owned_target", 60),
    ("restart_recovery", {"owned_target": 60}), ("failed_command", {"code": "feedback_timeout"}),
    ("automatic_recovery", {"state": "waiting_reports"}), ("recovery_budget", {"failure_streak": 2}),
    ("manual_hold", True)])
def test_every_old_journal_only_exists_in_archive(key, value):
    options, stored = legacy(); stored["dhw"] = {key: value}
    new, data, _ = migrate_panasonic(options, stored)
    assert data[ARCHIVE_KEY]["backup_store"]["dhw"][key] == value
    assert "dhw" not in data
    assert new["sg_boost"]["enabled"] is False


@pytest.mark.parametrize("fault", sorted(KNOWN_DHW_FAULTS))
def test_only_known_retired_fault_pause_is_identified_not_reset(fault):
    options, stored = legacy(); stored.update(mode="paused", pause_cause="command_fault")
    stored["dhw"] = {"fault": fault}
    new, data, report = migrate_panasonic(options, stored)
    assert report["retired_only_pause"] is True
    assert data["mode"] == "paused" and data["pause_cause"] == "command_fault"


@pytest.mark.parametrize("extra", [{"faults": {"dryer": "Unknown command"}},
    {"battery_fleet": {"faults": {"battery_a": "Battery error"}}},
    {"removal_requested": True}, {"pause_cause": "user"},
    {"pause_cause": "internal_fault"}, {"pause_cause": "legacy"}])
def test_mixed_unknown_user_or_removal_pause_never_classified_as_retired_only(extra):
    options, stored = legacy(); stored.update(mode="paused", pause_cause="command_fault")
    stored["dhw"] = {"fault": next(iter(KNOWN_DHW_FAULTS))}; stored.update(extra)
    _, data, report = migrate_panasonic(options, stored)
    assert report["retired_only_pause"] is False
    for k, v in extra.items(): assert data[k] == v


@pytest.mark.parametrize("key,value", [("manual_hold", True), ("unknown_fault", "Unknown device error")])
def test_manual_hold_or_unknown_fault_cannot_resume_legacy_pause(key, value):
    options, stored = legacy(); stored.update(mode="paused", pause_cause="command_fault")
    stored["dhw"] = {"fault": next(iter(KNOWN_DHW_FAULTS))}
    if key == "manual_hold": stored["dhw"][key] = value
    else: stored["dhw"]["fault"] = value
    _, data, report = migrate_panasonic(options, stored)
    assert not report["retired_only_pause"]
    assert data[ARCHIVE_KEY]["backup_store"]["dhw"] == stored["dhw"]


@pytest.mark.parametrize("fault", [[], ["bad"], {}, {"bad": True}, False, 123])
def test_damaged_fault_shapes_are_conservative_without_crashing(fault):
    options, stored = legacy(); stored["dhw"]["fault"] = fault
    _, data, report = migrate_panasonic(options, stored)
    assert not report["retired_only_pause"]
    assert data[ARCHIVE_KEY]["backup_store"]["dhw"]["fault"] == fault


@pytest.mark.parametrize("faults", [["unknown"], {"a": {"bad": True}}, "unknown"])
def test_damaged_climate_fault_journal_cannot_release_an_old_fault_pause(faults):
    options, stored = legacy(); stored.update(mode="paused", pause_cause="command_fault")
    stored["dhw"] = {"fault": next(iter(KNOWN_DHW_FAULTS))}
    stored["smart_climate"]["command_faults"] = faults
    _, data, report = migrate_panasonic(options, stored)
    assert report["retired_only_pause"] is False and report["unknown_fault_preserved"] is True
    assert data[ARCHIVE_KEY]["backup_store"]["smart_climate"]["command_faults"] == faults


def test_pending_legacy_option_changes_cannot_revive_writer():
    options, stored = legacy()
    options["_live_pending"] = {"group:dhw": {"kind": "group", "group": "dhw", "old": {}, "new": {"enabled": True}},
                                "group:wallbox": {"kind": "group", "group": "wallbox", "old": {}, "new": {"enabled": True}}}
    new, data, _ = migrate_panasonic(options, stored)
    assert "group:dhw" not in new["_live_pending"] and "group:wallbox" in new["_live_pending"]
    assert data[ARCHIVE_KEY]["backup_options"]["_live_pending"] == options["_live_pending"]


def test_malformed_pending_group_is_kept_as_evidence_without_crashing():
    options, stored = legacy()
    options["_live_pending"] = {"damaged": {"kind": "group", "group": {"bad": True}}}
    new, data, _ = migrate_panasonic(options, stored)
    assert new["_live_pending"] == options["_live_pending"]
    assert data[ARCHIVE_KEY]["backup_options"]["_live_pending"] == options["_live_pending"]


@pytest.mark.parametrize("scope,expected", [("heat_pump", "total"), ("tank", "unconfirmed"), (None, "unconfirmed")])
def test_meter_coverage_is_never_guessed_as_a_supply(scope, expected):
    options, stored = legacy(); options["dhw"]["power_meter_scope"] = scope
    new, _, _ = migrate_panasonic(options, stored)
    assert new["sg_boost"]["power_scope"] == expected
    assert new["sg_boost"]["power_entity"] == "sensor.generic_heatpump_power"


def test_retired_ignored_flags_are_not_defaults_but_original_values_stay_archived():
    from custom_components.solar_pilot.ems import CAPACITY_DEFAULTS
    from custom_components.solar_pilot.wallbox_policy import SESSION_DEFAULTS
    assert 'respect_optional_dhw' not in CAPACITY_DEFAULTS
    assert 'manual_suspend_extra_dhw' not in SESSION_DEFAULTS
    options,stored=legacy()
    options['capacity']={'respect_optional_dhw':False,'target_peak_w':4200}
    options['wallbox']={'manual_suspend_extra_dhw':False,'enabled':True}
    new,data,_=migrate_panasonic(options,stored)
    assert new['capacity']==options['capacity'] and new['wallbox']==options['wallbox']
    assert data[ARCHIVE_KEY]['backup_options']==options
