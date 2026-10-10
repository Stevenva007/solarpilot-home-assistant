"""Current migration preserves earlier activation choices without replaying them.

The retired beta.37 activation API is absent. Its non-Panasonic invariants remain
covered here: explicit phase/capacity/PV/AEG/Wallbox/learning choices survive, and
no migration grants a new physical start or SG commissioning right.
"""
from copy import deepcopy
import pytest
from custom_components.solar_pilot.panasonic_migration import migrate_panasonic


def configured_legacy(enabled):
    options = {
        "planner": {"enabled": enabled, "base_load_learning": enabled,
                    "replay_enabled": enabled, "forecast_deferral_enabled": enabled,
                    "adaptive_power_guard": enabled},
        "analysis": {"enabled": enabled, "retention_days": 12},
        "local_pv": {"enabled": enabled, "seed_enabled": enabled},
        "pv_forecast": {"enabled": enabled, "calibration_enabled": enabled,
                        "panel_peak_wp": 12000, "inverter_limit_w": 9000},
        "battery_analysis": {"enabled": enabled, "seed_enabled": enabled},
        "economy": {"enabled": enabled},
        "capacity": {"enabled": enabled, "average_demand_entity": "sensor.demand"},
        "phase": {"enabled": enabled, "learning_enabled": enabled,
                  "control_starts": enabled, "shed_on_overlimit": False,
                  "phase_1_entity": "sensor.phase_a", "phase_2_entity": "sensor.phase_b",
                  "phase_3_entity": "sensor.phase_c"},
        "wallbox": {"enabled": enabled, "power_entity": "sensor.wallbox"},
        "devices": [{"id": "washer", "kind": "dishwasher", "name": "Dishwasher",
                     "cycle_learning_enabled": enabled, "dishwasher_mapping_confirmed": False,
                     "start_button": "button.dishwasher_start", "priority": 35}],
        "dhw": {"enabled": True, "safety_confirmed": True,
                "target_entity": "water_heater.tank", "temperature_entity": "sensor.tank"},
        "smart_climate": {"enabled": True, "control_enabled": True,
                          "zone_entities": ["climate.zone"]},
    }
    stored = {"mode": "solar", "auto_resume_after_restart": False,
              "device_modes": {"washer": "disabled"},
              "learning": {"enabled": enabled, "profiles": {"washer": {"n": 8}}},
              "learning_hub": {"policy": {"adaptation": "automatic" if enabled else "assisted",
                                            "notifications": enabled}},
              "dishwasher_app": {"data": {"washer": {"cycle": {"status": "completed"}}}}}
    return options, stored


@pytest.mark.parametrize("enabled", [False, True])
def test_migration_preserves_explicit_model_and_other_device_choices(enabled):
    options, stored = configured_legacy(enabled)
    before = deepcopy((options, stored))
    new, data, _ = migrate_panasonic(options, stored)
    assert (options, stored) == before
    for group in ("planner", "analysis", "local_pv", "pv_forecast", "battery_analysis",
                  "economy", "capacity", "phase", "wallbox", "devices"):
        assert new[group] == options[group], group
    for key in ("mode", "auto_resume_after_restart", "device_modes", "learning", "learning_hub", "dishwasher_app"):
        assert data[key] == stored[key], key
    assert "_beta37_activation_profile" not in new
    assert "dhw" not in new and "smart_climate" not in new
    assert all(new["sg_boost"][key] is False for key in
               ("enabled", "commissioning_confirmed", "watchdog_confirmed"))


def test_old_activation_marker_and_later_user_choices_remain_exact():
    options, stored = configured_legacy(False)
    options["_beta37_activation_profile"] = 1
    options["planner"]["quality_retention_days"] = 19
    new, data, _ = migrate_panasonic(options, stored)
    assert new["_beta37_activation_profile"] == 1
    assert new["planner"] == options["planner"]
    assert data["learning_hub"]["policy"]["adaptation"] == "assisted"
    assert data["panasonic_archive"]["backup_options"] == options
    assert data["panasonic_archive"]["backup_store"] == stored


def test_missing_sources_or_experimental_sg_flags_never_create_new_rights():
    options, stored = configured_legacy(False)
    options["phase"].update(phase_2_entity="", phase_3_entity="")
    options["wallbox"]["power_entity"] = ""
    options["smart_climate"]["zone_entities"] = ["climate.missing"]
    options["sg_boost"] = {"entity_id": "switch.guessed", "enabled": True,
                           "commissioning_confirmed": True, "watchdog_confirmed": True}
    new, data, _ = migrate_panasonic(options, stored)
    assert new["phase"] == options["phase"] and new["wallbox"] == options["wallbox"]
    assert new["sg_boost"]["entity_id"] == ""
    assert all(new["sg_boost"][key] is False for key in
               ("enabled", "commissioning_confirmed", "watchdog_confirmed"))
    assert new["sg_boost"]["zone_entities"] == ["climate.missing"]
    assert data["device_modes"]["washer"] == "disabled"
    assert data["panasonic_archive"]["backup_options"]["sg_boost"] == options["sg_boost"]
