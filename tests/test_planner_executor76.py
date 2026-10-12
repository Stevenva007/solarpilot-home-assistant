"""Isolated planner jobs cannot overwrite live telemetry or stale permissions.

These explicit HA doubles exercise the executor boundary, not a real HA Core.
"""
import asyncio
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import threading
import time

import pytest

from custom_components.solar_pilot.engine import Plan
from custom_components.solar_pilot.battery_fleet import BatteryReading
import custom_components.solar_pilot.runtime as runtime_module
from custom_components.solar_pilot.unified_planner import UnifiedPlanner
from test_runtime import build


NOW = datetime(2026, 10, 12, 10, tzinfo=timezone.utc)


def configured():
    runtime, hass = build(device={
        "forecast_deferrable": True,
        "daily_energy_goal_kwh": 1.0,
        "cheap_grid_allowed": True,
        "deadline_grid_allowed": True,
    })
    runtime.planner_settings.update(horizon_h=6, slot_min=60, early_grid_enabled=True)
    runtime.unified_planner.settings.update(runtime.planner_settings)
    runtime.device_modes["a"] = "auto"
    runtime._observe(time.monotonic(), NOW)
    runtime._planner_pv_hourly = lambda now: [0.0] * 6
    runtime._planner_prices = lambda n, now: ([.30] * n, [.03] * n)
    runtime.learning_hub.observe = lambda *args: {
        "valid": False, "watts": None, "context": "unknown",
    }
    return runtime, hass


def configured_battery(runtime, *, charge=1250, discharge=8000, soc=50,
                       minimum=20, reserve=20, maximum=95):
    runtime.battery_fleet.settings["enabled"] = True
    runtime.battery_fleet.last = [BatteryReading(
        id="battery", name="Battery", valid=True, soc_pct=soc, power_w=0,
        capacity_kwh=10, min_soc_pct=minimum, reserve_soc_pct=reserve,
        max_soc_pct=maximum, max_charge_w=charge, max_discharge_w=discharge,
    )]
    runtime.battery_fleet.overview = lambda: {"aggregate": {
        "valid": True, "count": 1, "valid_count": 1,
        "capacity_kwh": 10, "soc_pct": soc,
        "charge_available_w": charge, "discharge_available_w": discharge,
    }}


class DeferredExecutor:
    def __init__(self, *, fail=False):
        self.entered = asyncio.Event()
        self.release = asyncio.Event()
        self.jobs = []
        self.fail = fail

    async def __call__(self, job):
        self.jobs.append(job)
        self.entered.set()
        await self.release.wait()
        if self.fail:
            raise RuntimeError("deliberate abandoned worker failure")
        return job()


@pytest.mark.asyncio
async def test_real_executor_runs_isolated_planner_off_event_loop(monkeypatch):
    runtime, hass = configured()
    loop_thread = threading.get_ident()
    live_planner = runtime.unified_planner
    live_base = live_planner.base_load
    observed = []
    original = UnifiedPlanner.build

    def tracked_build(worker, **inputs):
        observed.append((threading.get_ident(), worker, inputs))
        return original(worker, **inputs)

    monkeypatch.setattr(UnifiedPlanner, "build", tracked_build)
    calls = []

    async def executor(job):
        calls.append(job)
        return await asyncio.to_thread(job)

    hass.async_add_executor_job = executor
    await runtime._update_planner(NOW, time.monotonic())

    assert len(calls) == len(observed) == 1
    thread, worker, inputs = observed[0]
    assert thread != loop_thread
    assert worker is not live_planner and worker.base_load is not live_base
    assert worker.settings is not runtime.planner_settings
    assert inputs["devices"][0] is not runtime.configs["a"]
    assert runtime.unified_plan is live_planner.plan
    assert runtime.unified_plan is not None
    assert live_planner.plan_runs == 1
    assert runtime.planner_job_status["status"] == "ready"
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_pending_job_yields_and_duplicate_call_cannot_start_another():
    runtime, hass = configured()
    executor = hass.async_add_executor_job = DeferredExecutor()
    task = asyncio.create_task(runtime._update_planner(NOW, time.monotonic()))
    await asyncio.wait_for(executor.entered.wait(), 1)
    try:
        heartbeat = []
        asyncio.get_running_loop().call_soon(heartbeat.append, True)
        await asyncio.sleep(0)
        assert heartbeat == [True]
        assert runtime._planner_busy
        await runtime._update_planner(NOW, time.monotonic())
        assert len(executor.jobs) == 1
    finally:
        executor.release.set()
        await task
    assert not runtime._planner_busy
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("worker_fails", [False, True])
async def test_cancelled_tick_keeps_worker_busy_until_real_completion(worker_fails):
    runtime, hass = configured()
    executor = hass.async_add_executor_job = DeferredExecutor(fail=worker_fails)
    task = asyncio.create_task(runtime._update_planner(NOW, time.monotonic()))
    await asyncio.wait_for(executor.entered.wait(), 1)
    worker_future = runtime._planner_future
    completed = asyncio.Event()
    try:
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert runtime._planner_busy
        assert worker_future is not None and not worker_future.cancelled()
        await runtime._update_planner(NOW, time.monotonic())
        assert len(executor.jobs) == 1
        assert runtime.unified_plan is None
    finally:
        # The runtime installs its cleanup callback while handling cancellation;
        # our later callback signals that this cleanup has already run.
        worker_future.add_done_callback(lambda _: completed.set())
        executor.release.set()
        await asyncio.wait_for(completed.wait(), 1)
    assert not runtime._planner_busy
    assert runtime._planner_future is None
    assert runtime.unified_plan is None and runtime.unified_planner.plan is None
    assert runtime.unified_planner.plan_runs == 0
    if worker_fails:
        # Do not call .exception() here: the assertion verifies that runtime
        # cleanup already retrieved it, avoiding an unhandled-task warning.
        assert not worker_future._log_traceback
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_tick_refreshes_site_and_demand_after_executor_await(monkeypatch):
    runtime, hass = configured()
    runtime.configs["a"]["condition_entity"] = "input_boolean.ready"
    executor = hass.async_add_executor_job = DeferredExecutor()
    observed = []

    def record_site(site, devices, states):
        observed.append((site.grid_w, site.now, states["a"].demand))
        return Plan()

    monkeypatch.setattr(runtime_module, "plan", record_site)
    task = asyncio.create_task(runtime._tick())
    await asyncio.wait_for(executor.entered.wait(), 1)
    try:
        after_snapshot = time.monotonic()
        hass.states.set("sensor.grid", 5000, {"unit_of_measurement": "W"})
        hass.states.set("input_boolean.ready", "off")
    finally:
        executor.release.set()
        await task
    assert observed
    grid, timestamp, demand = observed[0]
    assert grid == 5000
    assert timestamp >= after_snapshot
    assert demand is False
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["disabled", "generation", "config", "device_mode", "closed"])
async def test_result_is_rejected_after_permissions_or_identity_change(change):
    runtime, hass = configured()
    executor = hass.async_add_executor_job = DeferredExecutor()
    task = asyncio.create_task(runtime._update_planner(NOW, time.monotonic()))
    await asyncio.wait_for(executor.entered.wait(), 1)
    try:
        if change == "disabled":
            await runtime.async_set_planner_setting("enabled", False)
        elif change == "generation":
            await runtime.async_set_planner_setting("enabled", False)
            await runtime.async_set_planner_setting("enabled", True)
        elif change == "config":
            runtime.configs["a"]["daily_energy_goal_kwh"] = 2
        elif change == "device_mode":
            runtime.device_modes["a"] = "disabled"
        else:
            runtime._closed = True
    finally:
        executor.release.set()
        await task
    assert runtime.unified_plan is None
    assert runtime.unified_planner.plan is None
    assert runtime.unified_planner.plan_runs == 0
    assert runtime.planner_job_status["status"] == "discarded"
    assert not runtime.states["a"].planner_grid_force
    if change == "disabled":
        assert not runtime.states["a"].planner_hold
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_live_learning_and_quality_objects_survive_adoption():
    runtime, hass = configured()
    planner = runtime.unified_planner
    base, quality, replay = planner.base_load, planner.quality, planner.replay
    base.accepted = 7
    executor = hass.async_add_executor_job = DeferredExecutor()
    task = asyncio.create_task(runtime._update_planner(NOW, time.monotonic()))
    await asyncio.wait_for(executor.entered.wait(), 1)
    try:
        worker = executor.jobs[0].func.__self__
        assert worker.base_load.accepted == 7
        base.accepted = 8
        replay.observe(local_now=NOW, pv_w=1000, base_w=500, grid_w=-500,
                       import_price=.30, export_price=.03, capacity_target_w=3500)
        before_replay = deepcopy(replay.snapshot())
        before_quality = deepcopy(quality.snapshot())
    finally:
        executor.release.set()
        await task
    assert runtime.unified_planner is planner
    assert planner.base_load is base and base.accepted == 8
    assert planner.quality is quality and quality.snapshot() == before_quality
    assert planner.replay is replay and replay.snapshot() == before_replay
    assert runtime.unified_plan is not None


@pytest.mark.asyncio
async def test_executor_error_keeps_mode_existing_plan_and_suppresses_immediate_retry():
    runtime, hass = configured()
    runtime.mode = "solar"
    previous = runtime.unified_planner.build(
        local_now=NOW, pv_hourly_w=[0] * 6,
        import_prices=[.30] * 6, export_prices=[.03] * 6, devices=[])
    runtime.unified_plan = previous
    runtime.unified_planner.last_plan_wall = 0
    runs = runtime.unified_planner.plan_runs
    calls = []

    async def broken_executor(job):
        calls.append(job)
        raise RuntimeError("deliberate executor failure")

    hass.async_add_executor_job = broken_executor
    await runtime._update_planner(NOW, time.monotonic())
    await runtime._update_planner(NOW, time.monotonic())
    assert len(calls) == 1
    assert runtime.mode == "solar"
    assert runtime.unified_plan is runtime.unified_planner.plan is previous
    assert runtime.unified_planner.plan_runs == runs
    assert runtime.planner_job_status["status"] == "fallback"
    assert runtime.planner_job_status["error_type"] == "RuntimeError"
    assert not runtime._planner_busy
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_zero_battery_headroom_does_not_invent_charge_or_discharge_power():
    runtime, hass = configured()
    configured_battery(runtime, charge=0, discharge=0)
    runtime._planner_pv_hourly = lambda now: [5000.0] * 3 + [0.0] * 3
    captured = []

    async def executor(job):
        captured.append(job.keywords["battery"])
        return job()

    hass.async_add_executor_job = executor
    await runtime._update_planner(NOW, time.monotonic())
    assert captured[0]["charge_power_w"] == 0
    assert captured[0]["discharge_power_w"] == 0
    assert all(slot.battery_w == 0 for slot in runtime.unified_plan.slots)
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("efficiency", [.80, .72])
async def test_battery_uses_real_available_limits_and_configured_loss(efficiency):
    runtime, hass = configured()
    configured_battery(runtime)
    runtime.battery_analysis_settings["roundtrip_efficiency"] = efficiency
    captured = []

    async def executor(job):
        captured.append(job.keywords["battery"])
        return job()

    hass.async_add_executor_job = executor
    await runtime._update_planner(NOW, time.monotonic())
    assert captured == [{
        "available_kwh": 10, "soc_pct": 50,
        "charge_power_w": 1250, "discharge_power_w": 5000,
        "min_soc_pct": 20, "max_soc_pct": 95,
        "round_trip_efficiency": efficiency,
        "aggregate_count": 1,
    }]
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_battery_advice_uses_configured_reserve_and_maximum_soc():
    runtime, hass = configured()
    configured_battery(runtime, soc=60, minimum=10, reserve=50, maximum=80)
    runtime._planner_pv_hourly = lambda now: [5000.0] * 3 + [0.0] * 3
    captured = []

    async def executor(job):
        captured.append(job.keywords["battery"])
        return job()

    hass.async_add_executor_job = executor
    await runtime._update_planner(NOW, time.monotonic())
    assert captured[0]["min_soc_pct"] == 50
    assert captured[0]["max_soc_pct"] == 80
    advice = runtime.unified_plan.battery_advice
    assert advice["status"] == "planned"
    assert all(50 - 1e-9 <= row["soc_end_pct"] <= 80 + 1e-9
               for row in advice["soc_trajectory"])
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("incomplete", ["missing_readings", "missing_capacity", "invalid_member"])
async def test_battery_advice_withheld_without_complete_matching_readings(incomplete):
    runtime, hass = configured()
    configured_battery(runtime)
    aggregate = dict(runtime.battery_fleet.overview()["aggregate"])
    if incomplete == "missing_readings":
        runtime.battery_fleet.last = []
        runtime.battery_fleet.read = lambda: []
    elif incomplete == "missing_capacity":
        aggregate["capacity_kwh"] = 20
    else:
        runtime.battery_fleet.last.append(replace(
            runtime.battery_fleet.last[0], id="unavailable", valid=False))
        aggregate.update(count=2, valid_count=1)
    runtime.battery_fleet.overview = lambda: {"aggregate": aggregate}
    captured = []

    async def executor(job):
        captured.append(job.keywords["battery"])
        return job()

    hass.async_add_executor_job = executor
    await runtime._update_planner(NOW, time.monotonic())
    assert captured == [None]
    assert runtime.unified_plan.battery_advice["status"] == "unavailable"
    assert all(slot.battery_w == 0 for slot in runtime.unified_plan.slots)
    assert not hass.services.calls
