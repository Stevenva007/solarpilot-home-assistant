"""Separate import release policy without rewriting commissioned SG options."""
from copy import deepcopy
from types import MappingProxyType, SimpleNamespace

import pytest

from custom_components.solar_pilot.heatpump_history_runtime import history_binding
from custom_components.solar_pilot.panasonic_migration import migrate_panasonic
from custom_components.solar_pilot.sg_config import SG_DEFAULTS, normalize_config, validate_config
from test_sg_config62 import flow, live_sg_runtime
from test_sg_migration62 import legacy


@pytest.mark.parametrize("saved,expected", [
    ({}, (600, 300)),
    ({"entity_id": "switch.sg_contact"}, (600, 300)),
    ({"hysteresis_w": 300, "stop_delay_s": 60}, (600, 300)),
    ({"hysteresis_w": "300", "stop_delay_s": "60"}, (600, 300)),
    ({"hysteresis_w": 450, "stop_delay_s": 60}, (450, 60)),
    ({"hysteresis_w": 300, "stop_delay_s": 90}, (300, 90)),
    ({"hysteresis_w": 450, "stop_delay_s": 90}, (450, 90)),
    ({"hysteresis_w": 0, "stop_delay_s": 60}, (0, 60)),
    ({"hysteresis_w": 450}, (450, 60)),
    ({"hysteresis_w": 300}, (600, 300)),
    ({"stop_delay_s": 60}, (600, 300)),
    ({"stop_delay_s": 90}, (300, 90)),
    ({"import_threshold_w": 300, "hysteresis_w": 300, "stop_delay_s": 60}, (300, 60)),
    ({"import_threshold_w": 0, "hysteresis_w": 300, "stop_delay_s": 60}, (0, 60)),
])
def test_legacy_effective_defaults_upgrade_once_and_custom_policy_remains(saved, expected):
    before = deepcopy(saved)
    effective = normalize_config(saved)
    assert (effective["import_threshold_w"], effective["stop_delay_s"]) == expected
    assert effective["hysteresis_w"] == saved.get("hysteresis_w", 300)
    assert normalize_config(effective) == effective
    assert saved == before
    assert not validate_config(effective)


def test_defaults_keep_twenty_minute_minimum_and_independent_solar_reset():
    assert normalize_config() == SG_DEFAULTS
    assert (SG_DEFAULTS["import_threshold_w"], SG_DEFAULTS["stop_delay_s"]) == (600, 300)
    assert SG_DEFAULTS["hysteresis_w"] == 300
    assert (SG_DEFAULTS["min_session_s"], SG_DEFAULTS["max_session_s"]) == (1200, 3600)


def test_read_only_mapping_keeps_bindings_confirmations_and_other_settings_detached():
    saved = normalize_config({"entity_id": "switch.sg_contact", "enabled": True,
        "commissioning_confirmed": True, "watchdog_confirmed": True,
        "profile": "general", "profile_confirmed": True, "cooling_protection_confirmed": True,
        "threshold_w": 2500, "expected_power_w": 4200, "max_session_s": 300,
        "min_session_s": 0, "rest_s": 1200, "lease_s": 240, "renew_s": 30,
        "tank_temperature_entity": "sensor.tank", "zone_entities": ["climate.zone_a"],
        "power_entity": "sensor.hp_total", "power_scope": "total"})
    saved.pop("import_threshold_w")
    saved["stop_delay_s"] = 60
    before = deepcopy(saved)
    effective = normalize_config(MappingProxyType(saved))
    for key in saved:
        if key != "stop_delay_s":
            assert effective[key] == saved[key]
    assert effective["import_threshold_w"] == 600 and effective["stop_delay_s"] == 300
    assert saved == before and not validate_config(effective)
    effective["zone_entities"].append("climate.zone_b")
    assert saved["zone_entities"] == ["climate.zone_a"]


@pytest.mark.parametrize("value", [-1, 20001, True, None, "invalid", float("nan"), float("inf")])
def test_explicit_invalid_import_limit_is_visible_and_never_triggers_migration(value):
    effective = normalize_config({"import_threshold_w": value, "hysteresis_w": 300, "stop_delay_s": 60})
    assert effective["stop_delay_s"] == 60 and effective["hysteresis_w"] == 300
    assert validate_config(effective) == {"import_threshold_w": "range"}


@pytest.mark.parametrize("value", [None, True, "invalid"])
def test_invalid_legacy_import_policy_is_not_silently_replaced(value):
    effective = normalize_config({"hysteresis_w": value, "stop_delay_s": 60})
    assert effective["import_threshold_w"] == value
    assert effective["hysteresis_w"] == value and effective["stop_delay_s"] == 60
    assert validate_config(effective) == {"hysteresis_w": "range", "import_threshold_w": "range"}


@pytest.mark.parametrize("value", [None, True, "invalid"])
def test_invalid_legacy_delay_is_visible_and_does_not_upgrade_the_old_threshold(value):
    effective = normalize_config({"hysteresis_w": 300, "stop_delay_s": value})
    assert effective["import_threshold_w"] == 300 and effective["stop_delay_s"] == value
    assert validate_config(effective) == {"stop_delay_s": "range"}


def test_import_limit_is_independent_of_start_threshold_but_solar_reset_stays_below_it():
    config = normalize_config({"threshold_w": 500, "hysteresis_w": 300, "import_threshold_w": 600})
    assert not validate_config(config)
    assert not validate_config({**config, "import_threshold_w": 20000})
    assert validate_config({**config, "hysteresis_w": 500}) == {"hysteresis_w": "range"}


def test_completed_panasonic_archive_and_saved_options_are_not_rewritten_for_policy_upgrade():
    options, stored = legacy()
    options, stored, _ = migrate_panasonic(options, stored)
    options["sg_boost"].update(entity_id="switch.sg_contact", enabled=True,
        commissioning_confirmed=True, watchdog_confirmed=True, max_session_s=300,
        hysteresis_w=300, stop_delay_s=60)
    options["sg_boost"].pop("import_threshold_w")
    before = deepcopy((options, stored))
    upgraded, journal, report = migrate_panasonic(options, stored)
    assert (upgraded, journal) == before and report["changed"] is False
    effective = normalize_config(upgraded["sg_boost"])
    assert (effective["import_threshold_w"], effective["stop_delay_s"]) == (600, 300)
    assert (effective["min_session_s"], effective["max_session_s"]) == (1200, 300)
    assert effective["enabled"] is True and not validate_config(effective)


@pytest.mark.asyncio
async def test_native_form_shows_separate_policy_fields_without_saving_legacy_options(flow):
    flow.options["sg_boost"].pop("import_threshold_w")
    flow.options["sg_boost"]["stop_delay_s"] = 60
    before = deepcopy(flow.options)
    form = await flow.async_step_sg_advanced()
    assert form["data_schema"]["import_threshold_w"] == (0, 20000, 50)
    assert form["data_schema"]["hysteresis_w"] == (0, 5000, 50)
    assert form["data_schema"]["stop_delay_s"] == (5, 600, 5)
    assert (flow._sg_values()["import_threshold_w"], flow._sg_values()["stop_delay_s"]) == (600, 300)
    assert flow.options == before and flow.saved is None and not flow.hass.services.calls


@pytest.mark.asyncio
async def test_explicit_form_save_marks_policy_as_current_and_preserves_other_settings(flow):
    flow.options["sg_boost"].update(max_session_s=300, min_session_s=0)
    before = deepcopy(flow.options["sg_boost"])
    result = await flow.async_step_sg_advanced({"import_threshold_w": 300, "stop_delay_s": 60})
    saved = result["saved"]["sg_boost"]
    assert normalize_config(saved) == saved
    assert (saved["import_threshold_w"], saved["stop_delay_s"], saved["hysteresis_w"]) == (300, 60, 300)
    assert all(saved[key] == value for key, value in before.items()
               if key not in {"import_threshold_w", "stop_delay_s"})
    assert not flow.hass.services.calls


@pytest.mark.asyncio
async def test_invalid_form_import_limit_does_not_save_or_actuate(flow):
    before = deepcopy(flow.options)
    result = await flow.async_step_sg_advanced({"import_threshold_w": 20001})
    assert result["errors"] == {"import_threshold_w": "range"}
    assert flow.options == before and flow.saved is None and not flow.hass.services.calls


@pytest.mark.asyncio
async def test_open_form_cannot_overwrite_concurrent_import_policy_edit(flow):
    flow.config_entry = SimpleNamespace(options=deepcopy(flow.options))
    await flow.async_step_sg_advanced()
    flow.config_entry.options["sg_boost"]["import_threshold_w"] = 900
    result = await flow.async_step_sg_advanced({"stop_delay_s": 420})
    assert result["errors"] == {"base": "sg_reopen"}
    assert flow._sg_values()["import_threshold_w"] == 900
    assert flow.saved is None and not flow.hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("key,value", [("import_threshold_w", 900), ("stop_delay_s", 420), ("hysteresis_w", 200)])
async def test_live_policy_edits_wait_for_owned_lease_release(key, value):
    runtime, hass = live_sg_runtime()
    runtime.sg_boost.owned = runtime.sg_boost.relay_on = True
    runtime.sg_boost._lease_deadline = runtime.sg_boost._clock() + 60
    base = deepcopy(runtime.entry.options)
    desired = deepcopy(base)
    desired["sg_boost"][key] = value
    await runtime.live_options.submit(base, desired)
    assert runtime.sg_boost.settings[key] == base["sg_boost"][key]
    assert runtime.entry.options["sg_boost"][key] == base["sg_boost"][key]
    assert "group:sg_boost" in runtime.entry.options["_live_pending"]
    assert not hass.services.calls
    runtime.sg_boost.owned = runtime.sg_boost.relay_on = False
    await runtime.live_options.process_pending()
    assert runtime.sg_boost.settings[key] == value
    assert runtime.entry.options["sg_boost"][key] == value
    assert not runtime.entry.options["_live_pending"] and not hass.services.calls


def test_policy_edit_does_not_invalidate_physical_heatpump_history_binding():
    runtime, _ = live_sg_runtime()
    before = history_binding(runtime, {}, {})
    config = {**runtime.sg_boost.settings, "import_threshold_w": 900, "stop_delay_s": 420, "hysteresis_w": 200}
    runtime.sg_boost.update_config(config)
    runtime.panasonic.update_config(config)
    assert history_binding(runtime, {}, {}) == before
