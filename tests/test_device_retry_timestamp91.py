"""Report timestamps rounded to HA datetime resolution cannot confirm a call."""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from test_device_retry_audit90 import install_clock, reports, fresh, physical
from test_runtime import build


@pytest.mark.asyncio
@pytest.mark.parametrize("issued", [1800000000.1234567, 1800000000.0000007, 1800000000.9999998])
async def test_rounded_up_precommand_report_cannot_release_unknown_outcome(monkeypatch, issued):
    clock = install_clock(monkeypatch)
    clock.wall = issued
    runtime, hass = build(device={"nominal_w": 1000})
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    reports(hass, clock)
    old_state = hass.states.get("switch.load")
    # HA datetimes round to microseconds; time.time() retains sub-microseconds.
    assert 0 < old_state.last_reported.timestamp()-issued < 1e-6
    hass.services.fail = True
    await runtime.tick()
    hass.services.fail = False
    assert runtime.device_retry.waiting("a")
    clock.advance(300)
    fresh(hass, "sensor.grid", -2500, clock, {"unit_of_measurement": "W"})
    hass.states.data["switch.load"] = old_state
    await runtime.tick()
    assert runtime.device_retry.waiting("a")
    assert len(physical(hass)) == 1
    assert runtime.states["a"].owned
    # A real later report is still accepted at the following scheduled check.
    clock.advance(300)
    reports(hass, clock, active="on")
    await runtime.tick()
    assert not runtime.device_retry.waiting("a")
    assert runtime.states["a"].owned and runtime.states["a"].on
    assert len(physical(hass)) == 1


@pytest.mark.parametrize("kind", ["switch", "number", "script", "dishwasher"])
def test_postcommand_proof_requires_new_time_beyond_datetime_resolution(monkeypatch, kind):
    issued = 1800000000.1234567
    rounded = datetime.fromtimestamp(issued, timezone.utc).timestamp()
    runtime, hass = build()
    cfg = {**runtime.configs["a"], "kind": kind}
    if kind == "dishwasher":
        runtime.dishwasher.readings["a"] = SimpleNamespace(stamp=rounded, active=True, finished=False)
    else:
        key = "active_entity" if kind == "script" else "control_entity"
        for entity in (cfg[key], cfg.get("number_entity")):
            obj = hass.states.get(entity)
            obj.last_reported = obj.last_updated = datetime.fromtimestamp(issued, timezone.utc)
    # Keep the runtime validator on this fixture's date as well.
    clock = install_clock(monkeypatch)
    clock.wall = issued+1
    assert not runtime.device_retry._post_command_report(cfg, issued)
    newer = issued+0.001
    if kind == "dishwasher":
        runtime.dishwasher.readings["a"].stamp = newer
    else:
        for entity in (cfg[key], cfg.get("number_entity")):
            obj = hass.states.get(entity)
            obj.last_reported = obj.last_updated = datetime.fromtimestamp(newer, timezone.utc)
    assert runtime.device_retry._post_command_report(cfg, issued)
