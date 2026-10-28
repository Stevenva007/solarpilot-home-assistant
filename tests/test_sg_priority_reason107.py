"""Live SG explanations follow effective priority without granting power."""
from copy import deepcopy
import asyncio

import pytest

from test_priority106 import solar_wallbox
from test_sg_transport62 import native, writes

from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from custom_components.solar_pilot.sg_transport import ShellyLeaseError


@pytest.mark.parametrize("sg_first", [True, False])
def test_zero_ev_does_not_veto_independent_electrical_room(sg_first):
    runtime, hass = solar_wallbox()
    runtime.entry.options["priority_board"]["order"] = (
        ["dhw_extra", "device:a", "wallbox"] if sg_first else
        ["wallbox", "dhw_extra", "device:a"])
    hass.states.set("sensor.public_ev_power", 0, {"unit_of_measurement": "W"})
    options = deepcopy(runtime.entry.options)
    assert runtime.heat_pump_increase_allowed()[0]
    assert not runtime.sg_dispatch_allowed(automatic=True)
    assert runtime._sg_dispatch_rejection["code"] == "solar_threshold"
    assert runtime.entry.options == options and not hass.services.calls


@pytest.mark.parametrize("sg_first", [True, False])
def test_wallbox_summary_describes_central_order_without_an_invented_tank_goal(sg_first):
    runtime, hass = solar_wallbox()
    runtime.entry.options["priority_board"]["order"] = (
        ["dhw_extra", "device:a", "wallbox"] if sg_first else
        ["wallbox", "dhw_extra", "device:a"])
    options = deepcopy(runtime.entry.options)
    summary = runtime.wallbox_overview()["comfort_priority"]
    assert "Panasonic" in summary
    assert "SG heeft altijd voorrang op autonome Wallbox-zonnestroom" in summary
    assert "60" not in summary
    assert runtime.entry.options == options and not hass.services.calls


@pytest.mark.asyncio
async def test_priority_summary_follows_temporary_override_then_saved_order_again():
    runtime, hass = solar_wallbox()
    runtime.data_loaded = True
    runtime.entry.runtime_data = runtime
    runtime.publish = lambda: None
    saved_order = list(runtime.priority_board.base_order())
    assert "SG heeft altijd voorrang" in runtime.wallbox_overview()["comfort_priority"]
    await runtime.async_set_wallbox_priority("global", "until_auto")
    assert "SG heeft altijd voorrang" in runtime.wallbox_overview()["comfort_priority"]
    await runtime.async_set_wallbox_priority("global", "auto")
    assert "SG heeft altijd voorrang" in runtime.wallbox_overview()["comfort_priority"]
    assert runtime.priority_board.base_order() == saved_order
    assert not hass.services.calls


@pytest.mark.parametrize("sign", ["import_positive", "export_positive", "separate"])
def test_ev_site_coherence_uses_normalized_signed_p1_for_each_source_contract(sign):
    runtime, hass = solar_wallbox()
    runtime.settings["grid_sign"] = sign
    hass.states.set("sensor.public_pv", 5000, {"unit_of_measurement": "W"})
    if sign == "separate":
        runtime.settings["export_entity"] = "sensor.fixture_export"
        hass.states.set("sensor.grid", 200, {"unit_of_measurement": "W"})
        hass.states.set("sensor.fixture_export", 1200, {"unit_of_measurement": "W"})
    else:
        hass.states.set("sensor.grid", 1000 if sign == "export_positive" else -1000,
                        {"unit_of_measurement": "W"})
    hass.states.set("sensor.public_ev_power", 4250, {"unit_of_measurement": "W"})
    accepted = sg_solar_budget(runtime)
    assert accepted["grid_w"] == -1000 and accepted["available_w"] == 850
    assert accepted["ev_solar_w"] == 4250
    hass.states.set("sensor.public_ev_power", 4251, {"unit_of_measurement": "W"})
    rejected = sg_solar_budget(runtime)
    assert rejected["ev_solar_w"] == 0 and rejected["eligible_w"] == 850
    assert not hass.services.calls


@pytest.mark.parametrize("sign,value", [("discharge_positive", 300), ("charge_positive", -300)])
def test_battery_energy_cannot_authorize_sg_even_when_it_explains_ev_site_load(sign, value):
    runtime, hass = solar_wallbox()
    runtime.settings.update(battery_power_entity="sensor.fixture_battery", battery_sign=sign)
    hass.states.set("sensor.public_pv", 5000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.grid", -1000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.fixture_battery", value, {"unit_of_measurement": "W"})
    hass.states.set("sensor.public_ev_power", 4550, {"unit_of_measurement": "W"})
    budget = sg_solar_budget(runtime)
    assert budget["valid"] and budget["discharge_w"] == 300
    assert budget["ev_solar_w"] == 4550
    assert budget["eligible_w"] == 4850 and budget["available_w"] == 550
    assert not runtime.sg_dispatch_allowed(automatic=True)
    assert runtime._sg_dispatch_rejection["code"] == "battery_discharge"
    assert not hass.services.calls


@pytest.mark.parametrize("invalid", ["unknown", "stale", "restored"])
def test_unusable_battery_evidence_cannot_complete_ev_solar_coherence(invalid):
    runtime, hass = solar_wallbox()
    runtime.settings.update(battery_power_entity="sensor.fixture_battery", battery_sign="discharge_positive")
    attrs = {"unit_of_measurement": "W"}
    if invalid == "restored":
        attrs["restored"] = True
    hass.states.set("sensor.fixture_battery", "unavailable" if invalid == "unknown" else 0,
                    attrs, age=121 if invalid == "stale" else 0)
    assert not sg_solar_budget(runtime)["valid"]
    assert not runtime.sg_dispatch_allowed(automatic=True)
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_async_shelly_preflight_cannot_spend_ev_credit_contradicted_by_new_p1(native):
    runtime, hass = solar_wallbox()
    hass.states.set("sensor.public_pv", 5000, {"unit_of_measurement": "W"})
    original_ev = hass.states.get("sensor.public_ev_power")
    assert runtime.sg_dispatch_allowed(automatic=True)
    native.adapter.before_on = lambda: runtime.sg_dispatch_allowed(automatic=True)
    native.device.pause_read = asyncio.Event()
    native.device.release_read = asyncio.Event()
    pending = asyncio.create_task(native.adapter.set_on(300))
    await asyncio.wait_for(native.device.pause_read.wait(), timeout=2)
    # The EV poll has not changed. A newer P1 proves whole-site consumption
    # fell below that poll; residual export alone cannot start the SG request.
    hass.states.set("sensor.grid", -2000, {"unit_of_measurement": "W"})
    native.device.release_read.set()
    with pytest.raises(ShellyLeaseError) as caught:
        await pending
    assert caught.value.code == "dispatch_changed" and not caught.value.command_attempted
    assert runtime._sg_dispatch_rejection["code"] == "solar_threshold"
    assert hass.states.get("sensor.public_ev_power") is original_ev
    assert writes(native) == [] and not hass.services.calls
