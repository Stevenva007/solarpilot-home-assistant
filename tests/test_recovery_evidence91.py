"""Recovery must finish its protected run and keep feedback apart from planning."""
import math

import pytest

from custom_components.solar_pilot import analysis_export as ae
from test_device_retry_audit90 import install_clock, physical, reports
from test_runtime import build


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["restart_lease", "uncertain_command", "source_return"])
async def test_recovered_on_completes_full_minimum_then_stops_on_current_conditions(monkeypatch, path):
    clock = install_clock(monkeypatch)
    runtime, hass = build(power=True, device={"nominal_w": 1000, "min_on_s": 1800})
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    st = runtime.states["a"]
    st.owned, st.on, st.target_w = True, True, 1000
    st.last_on = clock.mono - 5000
    if path == "restart_lease":
        runtime.recovery["a"] = {"watts": 1000}
        st.available = False
    elif path == "uncertain_command":
        runtime.device_retry.begin("a", 0, clock.wall, 1000)
        clock.advance(300)
    else:
        st.available = False
    recovered_at = clock.mono
    reports(hass, clock, active="on", grid=500)
    await runtime.tick()
    assert st.owned and st.on and st.last_on == recovered_at
    assert not physical(hass)
    evidence = runtime.device_retry.recovery_overview("a", clock.mono, clock.wall)
    assert evidence["reconciled_at_wall"] == clock.wall
    assert evidence["minimum_run"]["remaining_s"] == 1800
    for step in (900, 899):
        clock.advance(step)
        reports(hass, clock, active="on", grid=500)
        await runtime.tick()
        assert not physical(hass)
        assert runtime.result.reasons["a"] == "Minimale looptijd"
    clock.advance(1)
    reports(hass, clock, active="on", grid=500)
    await runtime.tick()
    assert [call[:2] for call in physical(hass)] == [("switch", "turn_off")]
    evidence = runtime.device_retry.recovery_overview("a", clock.mono, clock.wall)
    assert evidence["minimum_run"]["remaining_s"] == 0
    assert not evidence["minimum_run"]["active"]
    clock.advance(5)
    reports(hass, clock, active="off", grid=500)
    await runtime.tick()
    assert not st.owned and not st.on
    assert len(physical(hass)) == 1


def test_original_on_meter_survive_zero_planning_values_in_export():
    runtime, hass = build(power=True)
    st = runtime.states["a"]
    st.on, st.owned, st.available = False, True, False
    st.measured_w = 0
    runtime.grid_w, runtime.pv_w = 10, 1200
    hass.states.set("switch.load", "on")
    hass.states.set("sensor.load", 280, {"unit_of_measurement": "W"})
    runtime.analysis.capture(1)
    fast = runtime.analysis.fast[-1]["devices"]["a"]
    assert fast["on"] is False and fast["power_w"] == 0
    assert fast["planning"]["on"] is False
    assert fast["planning"]["accounted_power_w"] == 0
    assert fast["observed"]["control"]["on"] is True
    assert fast["observed"]["power"]["watts"] == 280
    assert fast["observed"]["power"]["valid"]
    report = runtime.analysis.build(include_names=True)
    consumer = report["components"]["consumers"][0]
    assert consumer["observed"]["control"]["on"] is True
    assert consumer["observed"]["power"]["watts"] == 280
    assert consumer["planning"]["accounted_power_w"] == 0
    assert not physical(hass)


@pytest.mark.parametrize("source,attrs", [
    ("unavailable", {"unit_of_measurement": "W"}),
    ("0", {"unit_of_measurement": "W", "restored": True}),
    ("0", {"unit_of_measurement": "kWh"}),
])
def test_bad_meter_is_unknown_even_when_planning_is_zero(source, attrs):
    runtime, hass = build(power=True)
    hass.states.set("sensor.load", source, attrs)
    data = ae.consumer_evidence(runtime, "a")
    assert data["planning"]["accounted_power_w"] == 0
    assert data["observed"]["power"]["watts"] is None
    assert not data["observed"]["power"]["valid"]


def test_restored_control_and_shared_meter_never_become_physical_evidence():
    runtime, hass = build(power=True)
    hass.states.set("switch.load", "on", {"restored": True})
    runtime.configs["b"] = {**runtime.configs["a"], "id": "b", "control_entity": "switch.other"}
    data = ae.consumer_evidence(runtime, "a")
    assert data["observed"]["control"]["raw_state"] == "on"
    assert data["observed"]["control"]["on"] is None
    assert not data["observed"]["control"]["valid"]
    assert data["observed"]["power"]["watts"] is None
    assert not data["observed"]["power"]["valid"]


def test_source_release_coverage_does_not_bridge_versions_gaps_or_infer_old_freshness():
    def row(ts, release, value="100", stamp=None, policy=True):
        result = {"ts": ts, "release": release, "entities": {
            "sensor.fictional": [value, ts if stamp is None else stamp, ts]}}
        if policy:
            result["source_policy"] = {"stale_s": 60}
        return result
    windows = {"samples": [
        row(1000, "unknown", policy=False), row(1300, "unknown", policy=False),
        row(1600, "1.0.0-beta.90"), row(1900, "1.0.0-beta.90"),
        row(2200, "1.0.0-beta.91"), row(2500, "1.0.0-beta.91", stamp=2200),
        row(2800, "1.0.0-beta.91", value="unavailable"),
        row(4000, "1.0.0-beta.91"),
    ], "fast": [{"ts": 2200, "release": "1.0.0-beta.91"},
                 {"ts": 2205, "release": "1.0.0-beta.91"},
                 {"ts": 3000, "release": "1.0.0-beta.91"}], "events": []}
    data = ae.collecting_coverage(windows, 660)["by_release"]
    assert data["unknown"]["sample_interval_s"] == 300
    old = data["unknown"]["sources"]["sensor.fictional"]
    assert old["numeric_interval_s"] == 300
    assert old["fresh_report_interval_s"] == 0
    old = data["1.0.0-beta.90"]["sources"]["sensor.fictional"]
    assert old["numeric_interval_s"] == old["fresh_report_interval_s"] == 300
    new = data["1.0.0-beta.91"]
    assert new["sample_count"] == 4 and new["sample_interval_s"] == 600
    assert new["fast_interval_s"] == 5
    assert new["sources"]["sensor.fictional"]["numeric_interval_s"] == 300
    assert new["sources"]["sensor.fictional"]["fresh_report_interval_s"] == 0


@pytest.mark.parametrize("watts", [1380, "1380", 0, None, "bad", math.nan, math.inf,
                                   1379, 3681, True, False])
def test_number_restart_lease_uses_valid_original_target_and_safe_fallback(watts):
    runtime, hass = build(kind="number", device={"nominal_w": 2000})
    st = runtime.states["a"]
    hass.states.set("switch.load", "on")
    # A saved lower valid setting must not be replaced with the nominal watts.
    target = 1380 if watts in (1380, "1380") else 2000
    hass.states.set("number.amps", target / 230, {
        "min": 6, "max": 16, "step": 1, "unit_of_measurement": "A"})
    assert runtime._reconcile_restart_lease("a", {"watts": watts}, 100)
    assert st.owned and st.on and st.target_w == target
    assert not physical(hass)


@pytest.mark.parametrize("kind", ["switch", "script"])
def test_restart_fixed_load_lease_keeps_conservative_nominal_budget(kind):
    runtime, hass = build(kind=kind, device={"nominal_w": 2000})
    hass.states.set("switch.load", "on")
    hass.states.set("binary_sensor.running", "on")
    assert runtime._reconcile_restart_lease("a", {"watts": 1000}, 100)
    assert runtime.states["a"].owned and runtime.states["a"].on
    assert runtime.states["a"].target_w == 2000
    assert not physical(hass)


def test_recovery_observation_is_not_restored_as_current_evidence(monkeypatch):
    runtime, _ = build()
    runtime.device_retry.mark_recovered("a", 10, "source_return")
    assert runtime.device_retry.recovery_overview("a", 10)["reconciled_at_wall"] is not None
    saved = runtime.device_retry.snapshot()
    runtime.device_retry.restore(saved)
    assert runtime.device_retry.recovery_overview("a", 11)["reconciled_at_wall"] is None


def test_minimum_run_expiry_keeps_original_boundary_after_it_has_passed(monkeypatch):
    clock = install_clock(monkeypatch)
    runtime, _ = build(device={"min_on_s": 1800})
    st = runtime.states["a"]
    st.owned = st.on = st.available = True
    st.last_on = clock.mono
    runtime.device_retry.mark_recovered("a", clock.mono, "source_return")
    expires = clock.wall + 1800
    clock.advance(1900)
    evidence = runtime.device_retry.recovery_overview("a", clock.mono, clock.wall)
    assert evidence["minimum_run"]["until_wall"] == expires
    assert evidence["minimum_run"]["remaining_s"] == 0
    assert not evidence["minimum_run"]["active"]
