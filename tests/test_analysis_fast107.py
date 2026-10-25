"""Original electrical reports make delayed EV feedback visible without control."""
from datetime import datetime, timezone
from types import SimpleNamespace
import json
import time

import pytest

from custom_components.solar_pilot import analysis_export as ae
from test_wallbox_runtime import setup


def context():
    runtime, hass = setup(session_mode_entity="sensor.ev_session")
    runtime.settings["pv_entity"] = "sensor.pv"
    runtime.entry.data["pv_entity"] = "sensor.pv"
    hass.states.set("sensor.grid", 4200, {"unit_of_measurement": "W"}, reported_age=1)
    hass.states.set("sensor.pv", 7600, {"unit_of_measurement": "W"}, reported_age=25)
    hass.states.set("sensor.ev_power", 5.4, {"unit_of_measurement": "kW"}, reported_age=78)
    hass.states.set("sensor.ev_session", "Zonne-auto · laden", reported_age=55)
    runtime.wallbox_settings["session_solar_states"] = "Zonne-auto · laden"
    runtime.wallbox_guard.update(time.monotonic(), runtime._wallbox_reading(), 4200, 150)
    runtime.grid_w, runtime.pv_w = 4200, 7600
    return runtime, hass


def test_fast_capture_preserves_unequal_source_clocks_and_normalized_ev_watts(monkeypatch):
    runtime, hass = context()
    wall = time.time()
    monkeypatch.setattr(ae, "time", SimpleNamespace(time=lambda: wall, monotonic=lambda: 10))
    runtime.analysis.capture(1)
    wall += 5
    runtime.analysis.capture(1)
    first, latest = runtime.analysis.fast
    assert len(runtime.analysis.samples) == 1
    assert latest["grid_w"] == 4200 and latest["pv_w"] == 7600
    assert latest["electrical_sources"]["grid"]["watts"] == 4200
    assert latest["wallbox"]["power_w"] == 5400
    assert latest["wallbox"]["session_confirmed"] is True
    for role, entity in (("grid", "sensor.grid"), ("pv", "sensor.pv")):
        proof = latest["electrical_sources"][role]
        assert proof["reported_at_wall"] == hass.states.get(entity).last_reported.timestamp()
        assert proof["reported_at_wall"] == first["electrical_sources"][role]["reported_at_wall"]
    power = latest["wallbox"]["sources"]["power"]
    assert power["raw_state"] == "5.4" and power["unit_of_measurement"] == "kW"
    assert power["watts"] == 5400 and power["valid"] is True
    assert power["reported_at_wall"] == first["wallbox"]["power_reported_at"]
    assert power["report_age_s"] >= 83
    assert latest["wallbox"]["session_reported_at"] == hass.states.get("sensor.ev_session").last_reported.timestamp()
    assert hass.services.calls == []


@pytest.mark.parametrize("state,unit,age", [(5.4, "kW", 301), (-3, "W", 0), (5.4, "kWh", 0), ("unavailable", "W", 0)])
def test_invalid_ev_source_keeps_raw_report_without_usable_watts(state, unit, age):
    runtime, hass = context()
    hass.states.set("sensor.ev_power", state, {"unit_of_measurement": unit}, reported_age=age)
    runtime.wallbox_guard.update(time.monotonic(), runtime._wallbox_reading(), 4200, 150)
    runtime.analysis.capture(1)
    proof = runtime.analysis.fast[-1]["wallbox"]["sources"]["power"]
    assert proof["raw_state"] == str(state)
    assert proof["watts"] is None and proof["valid"] is False
    assert proof["reported_at_wall"] == hass.states.get("sensor.ev_power").last_reported.timestamp()
    assert runtime.analysis.fast[-1]["wallbox"]["power_w"] is None
    assert hass.services.calls == []


def test_sg_transition_retains_frozen_electrical_context_in_bounded_event_log(monkeypatch):
    runtime, hass = context()
    sg = {"desired_on": True, "relay_on": True, "relay_confirmed": True,
          "owner": "solarpilot", "state": "boost_requested"}
    monkeypatch.setattr(runtime.sg_boost, "overview", lambda: dict(sg))
    runtime.analysis.capture(1)
    sg.update(desired_on=False, relay_on=False, owner="none", state="blocked")
    runtime.analysis.capture(1)
    stop = [row for row in runtime.analysis.events if row["kind"] == "heatpump_change"][-1]
    context_at_stop = stop["data"]["electrical_context"]
    assert stop["data"]["state"]["sg"]["relay_on"] is False
    assert context_at_stop["grid_w"] == 4200
    assert context_at_stop["wallbox"]["sources"]["power"]["watts"] == 5400
    original_stamp = context_at_stop["wallbox"]["power_reported_at"]
    hass.states.set("sensor.ev_power", 0.65, {"unit_of_measurement": "kW"})
    runtime.wallbox_guard.update(time.monotonic(), runtime._wallbox_reading(), -314, 150)
    runtime.analysis.capture(1)
    assert context_at_stop["wallbox"]["power_reported_at"] == original_stamp
    assert context_at_stop["wallbox"]["sources"]["power"]["watts"] == 5400
    persisted = runtime.analysis.snapshot()
    assert "fast" not in persisted
    assert persisted["events"][-1]["kind"] != "electrical_context"  # No extra per-loop event stream.
    assert any("electrical_context" in row.get("data", {}) for row in persisted["events"])
    assert hass.services.calls == []


def test_new_diagnostic_sources_use_existing_private_export_aliases():
    runtime, hass = context()
    hass.states.get("sensor.ev_power").attributes.update(password="PRIVATE_PASSWORD", friendly_name="Private Charger")
    runtime.analysis.capture(1)
    report = runtime.analysis.build()
    content = json.dumps(report)
    assert "sensor.ev_power" not in content and "sensor.ev_session" not in content
    assert "PRIVATE_PASSWORD" not in content and "Private Charger" not in content
    latest = report["telemetry"]["fast"][-1]
    ev_alias = report["effective_configuration"]["wallbox"]["power_entity"]
    assert latest["wallbox"]["sources"]["power"]["entity_id"] == ev_alias
    grid_alias = report["configuration"]["site"]["grid_entity"]
    assert latest["electrical_sources"]["grid"]["entity_id"] == grid_alias
    sample = report["telemetry"]["samples"][-1]
    assert sample["wallbox"]["sources"]["power"]["entity_id"] == ev_alias
    assert hass.services.calls == []


def test_separate_grid_channels_keep_independent_report_times():
    runtime, hass = context()
    runtime.settings.update(grid_sign="separate", export_entity="sensor.grid_export")
    hass.states.set("sensor.grid_export", 0.2, {"unit_of_measurement": "kW"}, reported_age=30)
    runtime.analysis.capture(1)
    latest = runtime.analysis.fast[-1]
    assert latest["source_policy"]["grid_sign"] == "separate"
    sources = latest["electrical_sources"]
    assert sources["grid_export"]["watts"] == 200
    assert sources["grid_export"]["reported_at_wall"] < sources["grid"]["reported_at_wall"] - 20
    assert hass.services.calls == []


def test_new_source_during_dispatch_does_not_retimestamp_the_older_control_reading():
    runtime, hass = context()
    old_stamp = runtime.wallbox_guard.reading.stamp
    hass.states.set("sensor.ev_power", 0.65, {"unit_of_measurement": "kW"})
    hass.states.set("sensor.ev_session", "Manueel laden")
    runtime.analysis.capture(1)
    wallbox = runtime.analysis.fast[-1]["wallbox"]
    assert wallbox["power_w"] == 5400 and wallbox["power_reported_at"] == old_stamp
    assert wallbox["sources"]["power"]["watts"] == 650
    assert wallbox["sources"]["power"]["reported_at_wall"] > old_stamp
    assert wallbox["session_confirmed"] is True
    assert wallbox["session_source_matches_reading"] is False
    assert wallbox["session_value"] == "Zonne-auto · laden"
    assert wallbox["sources"]["session"]["raw_state"] == "Manueel laden"
    assert hass.services.calls == []


def test_missing_and_future_sources_remain_unknown_without_capture_time_replacement():
    runtime, hass = context()
    del hass.states.data["sensor.ev_power"]
    future = datetime.fromtimestamp(time.time()+3600, timezone.utc)
    hass.states.get("sensor.pv").last_reported = future
    runtime.analysis.capture(1)
    latest = runtime.analysis.fast[-1]
    for source in (latest["wallbox"]["sources"]["power"], latest["electrical_sources"]["pv"]):
        assert source["reported_at_wall"] is None
        assert source["report_age_s"] is None
        assert source["valid"] is False and source["watts"] is None
    assert hass.services.calls == []
