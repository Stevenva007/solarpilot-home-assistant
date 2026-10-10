"""Display interpretation cannot grant, revoke or delay an SG permission."""
from copy import deepcopy

import pytest

from test_sg_controller62 import boosted, fixture, tick
from test_sg_config62 import live_sg_runtime
from custom_components.solar_pilot.live_options import PENDING


@pytest.mark.asyncio
async def test_meter_display_edit_preserves_accumulated_start_delay():
    manager, adapter, clock, _runtime = fixture()
    await tick(manager)
    clock.advance(manager.settings["start_delay_s"] - 1)
    manager.update_config({**manager.settings, "power_activity_threshold_w": 500,
                           "power_supply1_role": "main", "power_supply2_role": "heater"})
    clock.advance(1)
    await tick(manager)
    assert manager.owned and manager.desired_on
    assert adapter.calls == [("on", manager.settings["lease_s"])]


@pytest.mark.asyncio
async def test_meter_display_edit_preserves_existing_lease_and_renewal():
    manager, adapter, clock, _runtime = await boosted()
    before = manager.snapshot()
    manager.update_config({**manager.settings, "power_activity_threshold_w": 500,
                           "power_supply1_role": "main", "power_supply2_role": "heater"})
    assert manager.snapshot() == before
    clock.advance(manager.settings["renew_s"])
    await tick(manager)
    assert manager.owned and manager.desired_on
    assert adapter.calls == [("on", manager.settings["lease_s"]),
                             ("on", manager.settings["lease_s"])]


@pytest.mark.asyncio
async def test_display_options_apply_during_busy_dispatch_without_device_calls():
    runtime, hass = live_sg_runtime()
    runtime.sg_boost._in_flight = True
    before = deepcopy(dict(runtime.entry.options))
    after = deepcopy(before)
    after["sg_boost"].update(power_activity_threshold_w=500,
                             power_supply1_role="main", power_supply2_role="heater")
    result = await runtime.live_options.submit(before, after)
    assert not result[PENDING]
    assert runtime.sg_boost.settings["power_activity_threshold_w"] == 500
    assert runtime.panasonic.settings["power_supply2_role"] == "heater"
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_display_edit_does_not_bypass_busy_control_change():
    runtime, hass = live_sg_runtime()
    runtime.sg_boost._in_flight = True
    before = deepcopy(dict(runtime.entry.options))
    after = deepcopy(before)
    after["sg_boost"].update(power_activity_threshold_w=500, threshold_w=4500)
    result = await runtime.live_options.submit(before, after)
    assert "group:sg_boost" in result[PENDING]
    assert runtime.sg_boost.settings["threshold_w"] == before["sg_boost"]["threshold_w"]
    assert not hass.services.calls
