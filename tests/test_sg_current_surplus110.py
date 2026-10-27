"""Current P1 surplus and a total HP envelope, using fictional sources only."""
import asyncio
from dataclasses import replace
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot import heatpump_budget
from custom_components.solar_pilot.heatpump_budget import sg_expected_increment, sg_solar_budget
from custom_components.solar_pilot.sg_transport import ShellyLeaseError
from test_sg_budget_priority62 import configured
from test_sg_solar_credit69 import metered
from test_sg_transport62 import native, writes


@pytest.mark.parametrize("current,extra", [(0, 3000), (800, 2200), (3000, 0), (4000, 0)])
def test_total_estimate_counts_only_extra_draw_above_current_complete_hp(current, extra):
    runtime, hass = metered(hp=current, pv=6000)
    runtime.sg_boost.settings["expected_power_w"] = 3000
    budget = sg_solar_budget(runtime)
    assert budget["hp_power_complete"] is True
    assert sg_expected_increment(runtime, budget) == extra
    assert sg_expected_increment(runtime) == extra
    assert not hass.services.calls


@pytest.mark.parametrize("failure", ["missing", "stale", "future", "estimated", "restored",
                                     "unit", "partial", "unconfirmed", "overlap", "invalid", "boolean"])
def test_unproven_hp_measurement_never_reduces_total_estimate(failure):
    runtime, hass = metered(hp=800)
    runtime.sg_boost.settings["expected_power_w"] = 3000
    attrs, value, age = {"unit_of_measurement": "W"}, 800, 0
    if failure == "missing":
        hass.states.data.pop("sensor.public_hp")
    elif failure in ("partial", "unconfirmed"):
        runtime.panasonic.settings["power_scope"] = "supply1" if failure == "partial" else "unconfirmed"
    else:
        if failure in ("estimated", "restored"):
            attrs[failure] = True
        elif failure == "unit":
            attrs["unit_of_measurement"] = "kWh"
        elif failure == "overlap":
            attrs["source_entity"] = "sensor.grid"
        elif failure in ("stale", "future"):
            age = 121 if failure == "stale" else -6
        elif failure == "invalid":
            value = "unavailable"
        elif failure == "boolean":
            value = True
        hass.states.set("sensor.public_hp", value, attrs, age=age)
    assert sg_solar_budget(runtime)["hp_power_complete"] is False
    assert sg_expected_increment(runtime) == 3000
    assert not hass.services.calls


def test_reading_old_budget_never_refreshes_its_hp_source_time(monkeypatch):
    runtime, _ = metered(hp=800)
    runtime.sg_boost.settings["expected_power_w"] = 3000
    budget = sg_solar_budget(runtime)
    stamp = budget["hp_power_reported_at"]
    assert sg_expected_increment(runtime, budget) == 2200
    monkeypatch.setattr(heatpump_budget, "time", SimpleNamespace(time=lambda: stamp+121))
    assert sg_expected_increment(runtime, budget) == 3000
    assert budget["hp_power_reported_at"] == stamp


@pytest.mark.parametrize("reserve", [0, 2000, 100000, float("nan")])
def test_future_dishwasher_peak_does_not_deduct_actual_export(reserve):
    runtime, _ = metered(grid=-3500, pv=6000, hp=0, reserve=150)
    runtime._dishwasher_comfort_reserve = reserve
    budget = sg_solar_budget(runtime)
    assert budget["valid"] and budget["available_w"] == 3350
    assert budget["reserve_w"] == 150


def test_sg_start_and_overview_ignore_other_thermostat_future_watts():
    runtime, hass = metered(grid=-1000, pv=6000, hp=800, reserve=150)
    runtime.settings["max_import_w"] = 2000
    runtime.sg_boost.settings.update(expected_power_w=3000, threshold_w=1500)
    runtime.states["a"].target_w = 100000
    runtime.states["a"].measured_w = 0
    runtime._dishwasher_comfort_reserve = 2000
    assert runtime.heat_pump_increase_allowed()[0] is True
    assert runtime.sg_dispatch_allowed(automatic=True) is True
    overview = runtime.electrical_limits_overview()
    assert overview["committed_reserve_w"] == 0
    assert overview["sg_estimated_total_w"] == 3000
    assert overview["sg_estimated_extra_w"] == 2200
    assert overview["fixed_import_headroom_w"] == 3000
    assert not hass.services.calls


@pytest.mark.parametrize("gate", ["pending", "handover", "settle", "battery", "net", "phase", "quarter"])
def test_current_surplus_does_not_replace_independent_start_guards(gate):
    runtime, hass = metered(grid=-1000, pv=6000, hp=800, reserve=150)
    runtime.settings["max_import_w"] = 3500
    runtime.sg_boost.settings.update(expected_power_w=3000, threshold_w=1500)
    if gate == "pending":
        runtime.pending = {"id": "a"}
    elif gate == "handover":
        runtime.handover = SimpleNamespace()
    elif gate == "settle":
        runtime.last_issued_wall = hass.states.get("sensor.grid").last_reported.timestamp()
    elif gate == "battery":
        runtime.settings["battery_power_entity"] = "sensor.public_battery"
        hass.states.set("sensor.public_battery", 100, {"unit_of_measurement": "W"})
    elif gate == "net":
        hass.states.set("sensor.grid", 1400, {"unit_of_measurement": "W"})
    elif gate == "phase":
        runtime.phase_settings.update(enabled=True, control_starts=True)
        runtime.phase = replace(runtime.phase, enabled=True, valid=True,
                                block_increase=False, headroom_w=2199)
    elif gate == "quarter":
        runtime.capacity_settings.update(enabled=True)
        runtime.capacity = replace(runtime.capacity, valid=True, allowed_grid_w=1199)
    if gate == "battery":
        # The solar budget remains large; dispatch independently rejects storage energy.
        assert runtime.sg_dispatch_allowed(automatic=True) is False
        assert runtime._sg_dispatch_rejection["code"] == "battery_discharge"
    else:
        assert runtime.heat_pump_increase_allowed()[0] is False
    assert not hass.services.calls


@pytest.mark.parametrize("elapsed,allowed", [(None, True), (299, True), (300, False), (301, False)])
def test_higher_waiting_candidate_only_gets_next_start_after_its_real_delay(elapsed, allowed):
    runtime, _ = configured(device={"start_delay_s": 300})
    runtime.entry.options["priority_board"]["order"] = ["device:a", "dhw_extra", "wallbox"]
    state = runtime.states["a"]
    state.on = state.owned = False
    state.last_off = -10000
    state.start_since = None if elapsed is None else 1000-elapsed
    assert runtime.priority_board.sg_priority_allowed(1000) is allowed


def test_due_but_unready_dishwasher_cannot_reserve_the_solar_window():
    runtime, _ = configured(kind="dishwasher", device={"start_delay_s": 300})
    runtime.entry.options["priority_board"]["order"] = ["device:a", "dhw_extra", "wallbox"]
    runtime.states["a"].on = runtime.states["a"].owned = False
    runtime.dishwasher_app.due = lambda cfg, wall: True
    assert runtime.priority_board.sg_priority_allowed(1000) is True
    assert runtime._sg_start_priority_blocks_wait() is False


@pytest.mark.asyncio
async def test_async_preflight_rereads_hp_before_reducing_total_envelope(native):
    runtime, hass = metered(grid=-1000, pv=6000, hp=800, reserve=0)
    runtime.settings["max_import_w"] = 2000
    runtime.sg_boost.settings.update(expected_power_w=3000, threshold_w=1500)
    assert runtime.sg_dispatch_allowed(automatic=True)
    native.adapter.before_on = lambda: runtime.sg_dispatch_allowed(automatic=True)
    native.device.pause_read = asyncio.Event()
    native.device.release_read = asyncio.Event()
    pending = asyncio.create_task(native.adapter.set_on(300))
    await asyncio.wait_for(native.device.pause_read.wait(), timeout=2)
    # The full 3 kW envelope plus new site import no longer fits. No stale
    # HP deduction, earlier plan or device reserve grants a relay command.
    hass.states.set("sensor.public_hp", "unavailable", {"unit_of_measurement": "W"})
    hass.states.set("sensor.grid", 600, {"unit_of_measurement": "W"})
    native.device.release_read.set()
    with pytest.raises(ShellyLeaseError) as caught:
        await pending
    assert caught.value.code == "dispatch_changed" and not caught.value.command_attempted
    assert writes(native) == [] and not hass.services.calls
