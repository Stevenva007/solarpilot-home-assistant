"""SG always uses proven autonomous EV solar; stored device order is untouched."""
from copy import deepcopy
from dataclasses import replace
import time

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.heatpump_budget import sg_solar_budget, sg_expected_increment
from custom_components.solar_pilot.house_first import HouseFirstGuard
from custom_components.solar_pilot.wallbox import Reading
from test_priority106 import solar_wallbox
from test_sg_transfer_integration108 import environment, sources


@pytest.mark.parametrize("order", [
    ["dhw_extra", "device:a", "wallbox"],
    ["wallbox", "dhw_extra", "device:a"],
    ["wallbox", "device:a", "dhw_extra"],
    ["device:a", "wallbox", "dhw_extra"],
])
def test_sg_solar_permission_does_not_reorder_any_saved_device(order):
    runtime, hass = solar_wallbox()
    runtime.entry.options["priority_board"]["order"] = order
    runtime.sg_boost.settings["expected_power_w"] = 3000
    before = deepcopy(runtime.entry.options)
    budget = sg_solar_budget(runtime)
    assert budget["ev_solar_w"] == 4000
    assert budget["eligible_w"] == 3850
    assert budget["available_w"] == 0
    assert runtime.priority_board.sg_before_wallbox()
    assert runtime.sg_dispatch_allowed(automatic=True)
    assert isinstance(runtime.sg_wallbox_guard, HouseFirstGuard)
    assert runtime.priority_board.base_order() == order
    assert runtime.entry.options == before and not hass.services.calls


def test_ev_pool_is_not_capped_before_site_import_is_paid():
    runtime, hass = solar_wallbox()
    runtime.sg_boost.settings.update(expected_power_w=3000, threshold_w=2500)
    hass.states.set("sensor.grid", 600, {"unit_of_measurement": "W"})
    budget = sg_solar_budget(runtime)
    assert budget["ev_solar_w"] == 4000
    assert budget["available_w"] == 0
    assert budget["eligible_w"] == 3250
    assert budget["eligible_w"] <= budget["pv_w"]
    assert sg_expected_increment(runtime, budget) == 3000


@pytest.mark.parametrize("hp,ev,export,threshold,extra,eligible", [
    (3000, 0, 0, 2500, 0, 2850),
    (2200, 50, 1000, 3000, 800, 3100),
])
def test_sg_uses_its_own_solar_threshold_not_a_secondary_ev_start_cap(
        hp, ev, export, threshold, extra, eligible):
    runtime, hass = solar_wallbox()
    runtime.entry.options["priority_board"]["order"] = ["wallbox", "dhw_extra", "device:a"]
    runtime.sg_boost.settings.update(expected_power_w=3000, threshold_w=threshold)
    hass.states.set("sensor.public_hp", hp, {"unit_of_measurement": "W"})
    hass.states.set("sensor.public_ev_power", ev, {"unit_of_measurement": "W"})
    hass.states.set("sensor.grid", -export, {"unit_of_measurement": "W"})
    budget = sg_solar_budget(runtime)
    assert budget["eligible_w"] == eligible
    assert sg_expected_increment(runtime, budget) == extra
    assert runtime.heat_pump_increase_allowed()[0]
    assert runtime.sg_dispatch_allowed(automatic=True)
    assert runtime.electrical_limits_overview()["sg_protected_ev_headroom_w"] is None
    assert not hass.services.calls


@pytest.mark.parametrize("eligible", [False, True])
def test_higher_device_may_claim_only_its_own_ev_permission(eligible):
    runtime, hass = solar_wallbox()
    runtime.entry.options["priority_board"]["order"] = ["device:a", "wallbox", "dhw_extra"]
    runtime.entry.options["priority_board"]["wallbox_power"]["device:a"] = eligible
    runtime.states["a"].owned = runtime.states["a"].on = False
    runtime.states["a"].start_since = time.monotonic()-1000
    hass.states.set("sensor.grid", -100, {"unit_of_measurement": "W"})
    runtime.wallbox_guard.update(time.monotonic(), runtime._wallbox_reading(), -100, 150, 0)
    assert sg_solar_budget(runtime)["available_w"] == 0
    assert sg_solar_budget(runtime)["ev_solar_w"] == 4000
    assert runtime.priority_board.sg_priority_allowed(time.monotonic()) is (not eligible)
    assert not hass.services.calls


def test_higher_but_ev_ineligible_row_after_wallbox_cannot_deadlock_sg():
    runtime, hass = solar_wallbox()
    runtime.entry.options["priority_board"]["order"] = ["wallbox", "device:a", "dhw_extra"]
    runtime.entry.options["priority_board"]["wallbox_power"]["device:a"] = True
    runtime.states["a"].owned = runtime.states["a"].on = False
    hass.states.set("sensor.grid", -100, {"unit_of_measurement": "W"})
    runtime.wallbox_guard.update(time.monotonic(), runtime._wallbox_reading(), -100, 150, 0)
    assert not next(d for d in runtime.devices() if d.id == "a").allow_wallbox_reclaim
    assert runtime.priority_board.sg_priority_allowed(time.monotonic())
    assert not hass.services.calls


@pytest.mark.parametrize("withdraw", ["none", "permission", "ev_source"])
def test_dishwasher_cached_ev_allocation_needs_current_rights_and_current_ev_proof(withdraw):
    runtime, hass = solar_wallbox()
    runtime.configs["a"]["kind"] = "dishwasher"
    runtime.entry.options["priority_board"]["order"] = ["device:a", "wallbox", "dhw_extra"]
    runtime.entry.options["priority_board"]["wallbox_power"]["device:a"] = withdraw != "permission"
    runtime.states["a"].owned = runtime.states["a"].on = False
    # Isolate priority arithmetic after the native controller already granted
    # a legitimate start opportunity; no native or actuator right is granted.
    runtime.dishwasher.permitted = lambda *_args: (True, "")
    runtime.dishwasher_priority.view.ev_credit = {"a": 1500}
    hass.states.set("sensor.grid", -100, {"unit_of_measurement": "W"})
    if withdraw == "ev_source":
        hass.states.set("sensor.fixture_session", "Manueel laden")
    assert runtime.priority_board.sg_priority_allowed(time.monotonic()) is (withdraw != "none")
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_general_wallbox_choice_excludes_sg_and_keeps_ordinary_choices():
    runtime, hass = solar_wallbox()
    runtime.data_loaded = True
    runtime.entry.runtime_data = runtime
    runtime.publish = lambda: None
    before = deepcopy(runtime.entry.options)
    await runtime.async_set_wallbox_priority("global", "1h")
    assert runtime.wallbox_priority.active("device:a")
    assert not runtime.wallbox_priority.active("dhw_extra")
    assert runtime.wallbox_priority.overview()["sg_boost"] is None
    assert runtime.sg_dispatch_allowed(automatic=True)
    with pytest.raises(HomeAssistantError, match="ondersteunt geen"):
        await runtime.async_set_wallbox_priority("dhw_extra", "until_auto")
    assert runtime.entry.options == before and not hass.services.calls


@pytest.mark.asyncio
async def test_existing_stored_sg_preference_is_inert_and_removed_durably():
    runtime, _ = solar_wallbox()
    wall = time.time()
    stored = runtime.wallbox_priority.snapshot()
    stored["targets"]["dhw_extra"] = {"option": "until_auto", "created_at": wall,
        "expires_at": None, "binding": "old-sg-scope"}
    runtime.wallbox_priority.restore(stored)
    assert not runtime.wallbox_priority.active("dhw_extra")
    assert "dhw_extra" not in runtime.wallbox_priority.snapshot()["targets"]
    assert runtime.priority_board.sg_before_wallbox()


@pytest.mark.parametrize("kind", ["manual", "unknown", "stale", "missing", "incoherent"])
def test_bad_ev_proof_does_not_create_credit_but_gives_a_reason(kind):
    runtime, hass = solar_wallbox()
    if kind == "manual":
        hass.states.set("sensor.fixture_session", "Manueel laden")
    elif kind == "unknown":
        hass.states.set("sensor.fixture_session", "Unrecognised")
    elif kind == "stale":
        hass.states.set("sensor.public_ev_power", 4000, {"unit_of_measurement": "W"}, age=121)
    elif kind == "missing":
        hass.states.set("sensor.public_ev_power", "unavailable", {"unit_of_measurement": "W"})
    else:
        hass.states.set("sensor.public_ev_power", 20000, {"unit_of_measurement": "W"})
    budget = sg_solar_budget(runtime)
    assert budget["ev_solar_w"] == 0 and budget["ev_reported_at"] is None
    assert budget["ev_credit_reason"]
    assert budget["eligible_w"] == budget["available_w"] == 0
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_order_and_ordinary_preference_do_not_restart_transfer_identity(monkeypatch):
    runtime, hass, _manager, _adapter, clock = environment(monkeypatch)
    await runtime._observe_sg_wallbox_transfer()
    clock.advance(15)
    sources(runtime, hass, clock)
    await runtime._observe_sg_wallbox_transfer()
    identity = runtime._sg_transfer_inputs()[2]
    runtime.entry.options["priority_board"]["order"] = ["wallbox", "dhw_extra", "device:a"]
    assert runtime._sg_transfer_inputs()[2] == identity
    runtime.wallbox_settings["power_entity"] = "sensor.different_ev"
    assert runtime._sg_transfer_inputs()[2] != identity


@pytest.mark.asyncio
async def test_armed_off_sg_can_start_then_bridge_its_immediate_ev_spike(monkeypatch):
    runtime, hass, manager, adapter, clock = environment(monkeypatch, limit=3500)
    runtime.entry.options["priority_board"]["order"] = ["wallbox", "dhw_extra", "device:a"]
    manager.settings.update(expected_power_w=3000, threshold_w=2500)
    for delay in (0, 15):
        clock.advance(delay)
        sources(runtime, hass, clock, grid=0, ev=4000, hp=0)
        await runtime._observe_sg_wallbox_transfer()
    assert not manager.owned and runtime.sg_wallbox_transfer.snapshot()["armed"]
    clock.advance(5)
    sources(runtime, hass, clock, grid=600, ev=4000, hp=0)
    await runtime._observe_sg_wallbox_transfer()
    assert runtime.heat_pump_increase_allowed()[0]
    assert runtime.sg_dispatch_allowed(automatic=True)
    await runtime._tick()
    clock.advance(30)
    sources(runtime, hass, clock, grid=600, ev=4000, hp=0)
    await runtime._tick()
    assert manager.owned and adapter.on
    clock.advance(5)
    sources(runtime, hass, clock, grid=3600, ev=4000, hp=3000)
    await runtime._tick()
    view = runtime.sg_wallbox_transfer_overview()
    assert manager.owned and adapter.on and view["applicable"]
    assert view["remaining_s"] == 240
    assert runtime.grid_w == 3600 and manager._import_observation["watts"] == 3600
    assert not hass.services.calls
