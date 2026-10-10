"""Read-only power interpretation settings retain the independent SG boundary."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.sg_config import (
    DISPLAY_ONLY_KEYS, POWER_SUPPLY_ROLES, normalize_config, validate_config,
)
from test_sg_config62 import actual_flow_class, hass_with
from test_sg_controller62 import fixture, tick
from test_sg_interface64 import live_flow


def test_old_meter_coverage_and_names_do_not_assign_supply_functions():
    config = normalize_config({"power_supply1_entity": "sensor.main_heatpump",
        "power_supply2_entity": "sensor.electric_heater", "split_power_confirmed": True,
        "power_scope": "total"})
    assert config["power_activity_threshold_w"] == 200.0
    assert config["power_supply1_role"] == config["power_supply2_role"] == "unconfirmed"
    assert config["split_power_confirmed"] is True
    assert not config["enabled"]


@pytest.mark.parametrize("threshold", [10, 200, 2000])
def test_display_threshold_accepts_bounded_values(threshold):
    assert not validate_config({"power_activity_threshold_w": threshold})


@pytest.mark.parametrize("threshold", [9.99, 2000.01, True, None, "", float("nan"), float("inf")])
def test_invalid_display_threshold_is_visible_in_validation(threshold):
    assert validate_config({"power_activity_threshold_w": threshold})["power_activity_threshold_w"] == "range"


@pytest.mark.parametrize("key", ["power_supply1_role", "power_supply2_role"])
@pytest.mark.parametrize("role", sorted(POWER_SUPPLY_ROLES))
def test_only_explicit_supported_supply_functions_are_preserved(key, role):
    config = normalize_config({key: role})
    assert config[key] == role
    assert not validate_config(config)


@pytest.mark.parametrize("key", ["power_supply1_role", "power_supply2_role"])
@pytest.mark.parametrize("role", ["compressor", "auto", "MAIN", True, None, [], {}])
def test_unsupported_function_does_not_get_coerced_or_inferred(key, role):
    assert validate_config({key: role})[key] == "range"


@pytest.fixture
def display_flow():
    class Flow(actual_flow_class()):
        def _base_options(self):
            return self.options

        def _site(self):
            return {}

        def async_show_form(self, **kwargs):
            return kwargs

        async def _save(self, options):
            self.saved = options
            return {"saved": options}

    flow = Flow()
    flow.options = {"sg_boost": normalize_config({"entity_id": "switch.public_sg",
        "power_supply1_entity": "sensor.public_supply1", "power_supply2_entity": "sensor.public_supply2"})}
    flow.hass = hass_with(**{"switch.public_sg": {},
        "sensor.public_supply1": {"unit_of_measurement": "W"},
        "sensor.public_supply2": {"unit_of_measurement": "W"}})
    flow.saved = None
    return flow


@pytest.mark.asyncio
async def test_actual_sources_form_exposes_independent_display_controls(display_flow):
    form = await display_flow.async_step_sg_sources()
    fields = form["data_schema"]
    assert fields["power_activity_threshold_w"] == (10, 2000, 10)
    assert DISPLAY_ONLY_KEYS <= fields.keys()
    for key in ("power_supply1_role", "power_supply2_role"):
        assert {option["value"] for option in fields[key]["options"]} == POWER_SUPPLY_ROLES


@pytest.mark.asyncio
async def test_saving_interpretation_preserves_separate_meter_coverage_and_sg_proof(display_flow):
    before = deepcopy(display_flow.options["sg_boost"])
    result = await display_flow.async_step_sg_sources({
        "power_supply1_entity": before["power_supply1_entity"],
        "power_supply2_entity": before["power_supply2_entity"],
        "power_activity_threshold_w": 350, "power_supply1_role": "main", "power_supply2_role": "heater"})
    saved = result["saved"]["sg_boost"]
    assert saved["power_activity_threshold_w"] == 350
    assert saved["power_supply1_role"] == "main" and saved["power_supply2_role"] == "heater"
    assert saved["split_power_confirmed"] is False
    assert saved["threshold_w"] == before["threshold_w"]
    assert all(saved[key] is False for key in ("enabled", "commissioning_confirmed", "watchdog_confirmed"))
    assert not display_flow.hass.services.calls


@pytest.mark.asyncio
async def test_changed_meter_does_not_inherit_old_or_carried_over_role(display_flow):
    display_flow.options["sg_boost"].update(power_supply1_role="main", power_supply2_role="heater")
    display_flow.hass = hass_with(**{"switch.public_sg": {},
        "sensor.public_replacement": {"unit_of_measurement": "W"},
        "sensor.public_supply2": {"unit_of_measurement": "W"}})
    submission = {"power_supply1_entity": "sensor.public_replacement",
        "power_supply2_entity": "sensor.public_supply2",
        "power_supply1_role": "main", "power_supply2_role": "heater"}
    first = await display_flow.async_step_sg_sources(submission)
    assert first["errors"]["power_supply1_role"] == "sg_supply_role_review"
    assert display_flow.saved is None
    second = await display_flow.async_step_sg_sources(submission)
    saved = second["saved"]["sg_boost"]
    assert saved["power_supply1_role"] == "main" and saved["power_supply2_role"] == "heater"
    assert saved["split_power_confirmed"] is False
    assert display_flow._sg_local_confirmed_roles == (
        ("sensor.public_supply1", "sensor.public_supply2"),
        ("sensor.public_replacement", "sensor.public_supply2"))
    assert not display_flow.hass.services.calls


@pytest.mark.asyncio
async def test_unconfirmed_function_allows_meter_edit_without_extra_confirmation(display_flow):
    display_flow.hass = hass_with(**{"switch.public_sg": {},
        "sensor.public_replacement": {"unit_of_measurement": "W"},
        "sensor.public_supply2": {"unit_of_measurement": "W"}})
    result = await display_flow.async_step_sg_sources({"power_supply1_entity": "sensor.public_replacement",
        "power_supply2_entity": "sensor.public_supply2"})
    assert result["saved"]["sg_boost"]["power_supply1_role"] == "unconfirmed"
    assert not display_flow.hass.services.calls


@pytest.mark.asyncio
async def test_imported_changed_meter_cannot_reuse_old_function():
    current = {"sg_boost": normalize_config({"power_supply1_entity": "sensor.public_supply1",
        "power_supply2_entity": "sensor.public_supply2", "power_supply1_role": "main",
        "power_supply2_role": "heater", "split_power_confirmed": True})}
    desired = deepcopy(current)
    desired["sg_boost"]["power_supply1_entity"] = "sensor.public_replacement"
    saved = await live_flow(current)._live_save(desired)
    assert saved["sg_boost"]["power_supply1_role"] == "unconfirmed"
    assert saved["sg_boost"]["power_supply2_role"] == "heater"
    assert saved["sg_boost"]["split_power_confirmed"] is False
    assert desired["sg_boost"]["power_supply1_role"] == "main"


@pytest.mark.asyncio
async def test_local_reviewed_function_survives_save_without_total_coverage_confirmation():
    current = {"sg_boost": normalize_config({"power_supply1_entity": "sensor.public_supply1",
        "power_supply2_entity": "sensor.public_supply2", "power_supply1_role": "main",
        "power_supply2_role": "heater"})}
    desired = deepcopy(current)
    desired["sg_boost"]["power_supply1_entity"] = "sensor.public_replacement"
    flow = live_flow(current)
    flow._sg_local_confirmed_roles = (
        ("sensor.public_supply1", "sensor.public_supply2"),
        ("sensor.public_replacement", "sensor.public_supply2"))
    saved = await flow._live_save(desired)
    assert saved["sg_boost"]["power_supply1_role"] == "main"
    assert saved["sg_boost"]["split_power_confirmed"] is False
    assert flow._sg_local_confirmed_roles is None


@pytest.mark.asyncio
@pytest.mark.parametrize("threshold", [10, 200, 2000])
async def test_power_display_settings_never_replace_sg_solar_start_threshold(threshold):
    manager, adapter, clock, _ = fixture(power_activity_threshold_w=threshold,
        power_supply1_role="main", power_supply2_role="heater")
    await tick(manager, surplus=2999)
    clock.advance(500)
    await tick(manager, surplus=2999)
    assert not adapter.calls
    await tick(manager, surplus=4000)
    clock.advance(120)
    await tick(manager, surplus=4000)
    assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_confirmed_display_roles_do_not_grant_sg_commissioning():
    manager, adapter, clock, _ = fixture(commissioning_confirmed=False, watchdog_confirmed=False,
        power_activity_threshold_w=10, power_supply1_role="main", power_supply2_role="heater")
    await tick(manager)
    clock.advance(500)
    await tick(manager)
    assert not adapter.calls
