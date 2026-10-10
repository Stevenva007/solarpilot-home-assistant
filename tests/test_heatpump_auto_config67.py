"""Existing split meters acquire presentation defaults without new authority."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.sg_config import DISPLAY_ONLY_KEYS, normalize_config, validate_config
from custom_components.solar_pilot.panasonic_migration import migrate_panasonic
from test_sg_migration62 import legacy
from test_sg_config62 import live_sg_runtime
from test_sg_controller62 import fixture, tick


PAIR = {"power_supply1_entity": "sensor.generic_feed1", "power_supply2_entity": "sensor.generic_feed2"}


@pytest.mark.parametrize("roles", [{}, {"power_supply1_role": "unconfirmed", "power_supply2_role": "unconfirmed"}])
def test_existing_pair_defaults_to_panasonic_functions_without_new_settings(roles):
    raw = {**PAIR, **roles}
    before = deepcopy(raw)
    config = normalize_config(raw)
    assert config["power_supply_profile"] == "panasonic_standard"
    assert config["power_supply1_role"] == "main" and config["power_supply2_role"] == "heater"
    assert config["power_activity_threshold_w"] == 200
    assert config["split_power_confirmed"] is False
    assert config["enabled"] is False and config["commissioning_confirmed"] is False
    assert config["watchdog_confirmed"] is False and raw == before


def test_explicit_nonstandard_functions_remain_exact():
    config = normalize_config({**PAIR, "power_supply1_role": "heater", "power_supply2_role": "main"})
    assert config["power_supply1_role"] == "heater" and config["power_supply2_role"] == "main"


@pytest.mark.parametrize("meters", [{}, {"power_supply1_entity": "sensor.single"},
    {"power_supply1_entity": "sensor.same", "power_supply2_entity": "sensor.same"},
    {"power_entity": "sensor.single_total", "power_scope": "total"}])
def test_missing_duplicate_or_single_meter_never_acquires_the_two_supply_model(meters):
    config = normalize_config(meters)
    assert config["power_supply1_role"] == config["power_supply2_role"] == "unconfirmed"


def test_unconfirmed_profile_retains_neutral_roles_without_inferred_function():
    config = normalize_config({**PAIR, "power_supply_profile": "unconfirmed"})
    assert config["power_supply1_role"] == config["power_supply2_role"] == "unconfirmed"


@pytest.mark.parametrize("profile", [None, True, [], {}, "automatic", "PANASONIC"])
def test_invalid_profile_is_retained_for_visible_validation(profile):
    assert validate_config({**PAIR, "power_supply_profile": profile})["power_supply_profile"] == "range"


def test_completed_migration_keeps_user_options_archive_and_journal_unchanged():
    options, stored = legacy()
    current, journal, _ = migrate_panasonic(options, stored)
    current["sg_boost"].update(PAIR)
    current["sg_boost"].pop("power_supply_profile", None)
    current["sg_boost"]["power_supply1_role"] = current["sg_boost"]["power_supply2_role"] = "unconfirmed"
    before = deepcopy((current, journal))
    migrated, persisted, report = migrate_panasonic(current, journal)
    assert (migrated, persisted) == before and report["changed"] is False
    effective = normalize_config(migrated["sg_boost"])
    assert effective["power_supply1_role"] == "main" and effective["power_supply2_role"] == "heater"
    assert effective["enabled"] is False and effective["split_power_confirmed"] is False


@pytest.mark.asyncio
async def test_display_profile_edit_never_resets_accumulated_sg_start_delay():
    manager, adapter, clock, _ = fixture(power_supply_profile="unconfirmed", **PAIR)
    await tick(manager)
    clock.advance(119)
    manager.update_config({**manager.settings, "power_supply_profile": "panasonic_standard"})
    clock.advance(1)
    await tick(manager)
    assert "power_supply_profile" in DISPLAY_ONLY_KEYS
    assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_automatic_profile_can_update_display_while_dispatch_is_busy_without_a_call():
    runtime, hass = live_sg_runtime()
    runtime.sg_boost._in_flight = True
    before = deepcopy(dict(runtime.entry.options))
    before["sg_boost"].update(power_supply_profile="unconfirmed")
    runtime.entry.options = deepcopy(before)
    runtime.sg_boost.update_config(before["sg_boost"])
    desired = deepcopy(before)
    desired["sg_boost"]["power_supply_profile"] = "panasonic_standard"
    result = await runtime.live_options.submit(before, desired)
    assert result["sg_boost"]["power_supply_profile"] == "panasonic_standard"
    assert not result["_live_pending"] and not hass.services.calls
