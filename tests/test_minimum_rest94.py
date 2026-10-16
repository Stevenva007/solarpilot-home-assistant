"""Original confirmed OFF deadlines survive reloads and changed uptime."""
from copy import deepcopy

import pytest

from test_device_retry_audit90 import install_clock, physical, reports
from test_runtime import build


def remaining(runtime, clock):
    return max(0, runtime.configs["a"]["min_off_s"]-(clock.mono-runtime.states["a"].last_off))


def checkpoint(monkeypatch, *, elapsed=1200, minimum=1800):
    clock = install_clock(monkeypatch)
    runtime, hass = build(power=True, device={"nominal_w": 350, "min_off_s": minimum})
    runtime.device_modes["a"] = "auto"
    reports(hass, clock, active="on", grid=500)
    runtime._observe(clock.mono, runtime._local_now())
    clock.advance(5)
    reports(hass, clock, active="off", grid=500)
    runtime._observe(clock.mono, runtime._local_now())
    original = clock.wall
    clock.advance(elapsed)
    reports(hass, clock, grid=-2500)
    runtime._observe(clock.mono, runtime._local_now())
    runtime.mode = "solar"
    saved = runtime._snapshot()
    assert saved["minimum_rest"]["devices"]["a"]["off_since_wall"] == original
    return clock, saved, original


async def restart(clock, saved, *, uptime=1000, minimum=1800, source="off"):
    clock.mono = float(uptime)
    runtime, hass = build(power=True, device={"nominal_w": 350, "min_off_s": minimum})
    reports(hass, clock, active=source, grid=-2500)
    runtime.store.data = deepcopy(saved)
    await runtime.start()
    assert not runtime.problem.startswith("Interne fout")
    return runtime, hass


@pytest.mark.asyncio
async def test_restart_counts_downtime_and_starts_only_at_the_original_off_deadline(monkeypatch):
    clock, saved, original = checkpoint(monkeypatch)
    clock.advance(120)
    runtime, hass = await restart(clock, saved)
    try:
        assert remaining(runtime, clock) == 480
        assert runtime._snapshot()["minimum_rest"]["devices"]["a"]["off_since_wall"] == original
        assert not physical(hass)
        clock.advance(479)
        reports(hass, clock, grid=-2500)
        await runtime.tick()
        assert remaining(runtime, clock) == 1 and not physical(hass)
        clock.advance(1)
        reports(hass, clock, grid=-2500)
        await runtime.tick()
        assert physical(hass) == [("switch", "turn_on", {"entity_id": "switch.load"})]
        assert "a" not in runtime._snapshot()["minimum_rest"]["devices"]
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_expired_rest_is_not_restarted_and_current_solar_guards_still_decide(monkeypatch):
    clock, saved, _original = checkpoint(monkeypatch, elapsed=1900)
    runtime, hass = await restart(clock, saved)
    try:
        assert remaining(runtime, clock) == 0
        assert physical(hass) == [("switch", "turn_on", {"entity_id": "switch.load"})]
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_repeated_restarts_preserve_the_same_original_off_time(monkeypatch):
    clock, saved, original = checkpoint(monkeypatch)
    for elapsed, uptime, expected in ((60, 1000, 540), (60, 500, 480), (120, 2000, 360)):
        clock.advance(elapsed)
        runtime, hass = await restart(clock, saved, uptime=uptime)
        try:
            assert remaining(runtime, clock) == expected
            saved = runtime._snapshot()
            assert saved["minimum_rest"]["devices"]["a"]["off_since_wall"] == original
            assert not physical(hass)
        finally:
            await runtime.close()


@pytest.mark.asyncio
async def test_missing_source_keeps_candidate_and_applies_remaining_only_after_actual_off(monkeypatch):
    clock, saved, original = checkpoint(monkeypatch)
    runtime, hass = await restart(clock, saved, source="unavailable")
    try:
        assert not runtime.states["a"].available and not physical(hass)
        assert runtime._snapshot()["minimum_rest"]["devices"]["a"]["off_since_wall"] == original
        clock.advance(120)
        reports(hass, clock, grid=-2500)
        await runtime.tick()
        assert remaining(runtime, clock) == 480
        assert runtime.states["a"].available and not physical(hass)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_a_real_new_on_to_off_transition_starts_a_new_full_rest(monkeypatch):
    clock, saved, original = checkpoint(monkeypatch)
    runtime, hass = await restart(clock, saved)
    try:
        clock.advance(60)
        reports(hass, clock, active="on", grid=500)
        await runtime.tick()
        assert "a" not in runtime._snapshot()["minimum_rest"]["devices"]
        assert not runtime.states["a"].owned
        clock.advance(60)
        reports(hass, clock, active="off", grid=500)
        await runtime.tick()
        assert remaining(runtime, clock) == 1800
        assert runtime._snapshot()["minimum_rest"]["devices"]["a"]["off_since_wall"] == clock.wall
        assert clock.wall != original and not physical(hass)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_current_minimum_setting_is_applied_to_the_original_stop(monkeypatch):
    clock, saved, original = checkpoint(monkeypatch, elapsed=600)
    runtime, hass = await restart(clock, saved, minimum=2400)
    try:
        assert remaining(runtime, clock) == 1800
        assert runtime._snapshot()["minimum_rest"]["devices"]["a"]["off_since_wall"] == original
        assert not physical(hass)
    finally:
        await runtime.close()


@pytest.mark.asyncio
async def test_first_off_proof_never_promotes_an_unobserved_startup_baseline(monkeypatch):
    clock = install_clock(monkeypatch)
    runtime, hass = build(power=True, device={"nominal_w": 350, "min_off_s": 1800})
    runtime.device_modes["a"] = "auto"
    reports(hass, clock, active="unavailable", grid=500)
    runtime._observe(clock.mono, runtime._local_now())
    assert not runtime._snapshot()["minimum_rest"]["devices"]
    clock.advance(1500)
    reports(hass, clock, grid=500)
    runtime._observe(clock.mono, runtime._local_now())
    original = clock.wall
    assert remaining(runtime, clock) == 300  # Existing live engine policy is unchanged.
    saved = runtime._snapshot()
    assert saved["minimum_rest"]["devices"]["a"]["off_since_wall"] == original
    clock.advance(60)
    restarted, new_hass = await restart(clock, saved)
    try:
        assert remaining(restarted, clock) == 1740
        assert not physical(new_hass)
    finally:
        await restarted.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("corrupt", ["legacy", "schema", "future_saved", "future_off", "negative_off", "nan_off", "infinite_off", "boolean_off", "text_off", "clock_backwards"])
async def test_missing_or_corrupt_timing_keeps_the_conservative_full_rest(monkeypatch, corrupt):
    clock, saved, _original = checkpoint(monkeypatch)
    data = saved["minimum_rest"]
    if corrupt == "legacy":
        saved.pop("minimum_rest")
    elif corrupt == "schema":
        data["schema"] = True
    elif corrupt == "future_saved":
        data["saved_at_wall"] = clock.wall+1
    elif corrupt == "clock_backwards":
        clock.wall -= 1
    else:
        data["devices"]["a"]["off_since_wall"] = {
            "future_off": clock.wall+1, "negative_off": -1,
            "nan_off": float("nan"), "infinite_off": float("inf"),
            "boolean_off": True, "text_off": "yesterday",
        }[corrupt]
    runtime, hass = await restart(clock, saved)
    try:
        assert remaining(runtime, clock) == 1800
        assert not physical(hass)
    finally:
        await runtime.close()
