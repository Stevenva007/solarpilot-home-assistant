"""Battery controller observations retain their original evidence in bounded logs."""
from dataclasses import replace
from types import SimpleNamespace
import json
import time

from custom_components.solar_pilot.battery_fleet import BatteryReading
from test_analysis_fast107 import context


def battery(runtime, hass):
    wall = time.time()
    reading = BatteryReading(id="storage", name="Private battery", valid=True,
        soc_pct=None, power_w=-400, capacity_kwh=5, min_soc_pct=10, reserve_soc_pct=15,
        max_soc_pct=95, max_charge_w=3000, max_discharge_w=3000,
        monitor_only=True, power_valid=True, soc_valid=False, power_stamp=wall-20,
        native_key="ongrid_power", expected_native_key="ongrid_power",
        source_evidence={"checked_at_wall": wall-1, "ha_reported_at_wall": wall-2,
            "es_reported_at_wall": wall-20, "coordinator_success_at_wall": wall-19,
            "field_reported_at_wall": wall-20, "accepted_reported_at_wall": wall-20,
            "detail_code": "completed_field_confirmed", "device_ip": "192.0.2.25"})
    manager = runtime.battery_fleet
    manager.settings["enabled"] = True
    manager.configs = {"storage": {"power_entity": "sensor.storage_ac", "profile": "marstek_venus_e3"}}
    manager.last = [reading]
    hass.states.set("sensor.storage_ac", -400, {"unit_of_measurement": "W", "token": "PRIVATE_TOKEN"}, reported_age=2)
    return manager, reading


def test_capture_does_not_reread_or_renew_adapter_clock(monkeypatch):
    runtime, hass = context()
    manager, reading = battery(runtime, hass)
    monkeypatch.setattr(manager, "read", lambda: (_ for _ in ()).throw(AssertionError("diagnostics read adapter")))
    runtime.analysis.capture(1)
    proof = runtime.analysis.fast[-1]["battery_sources"]["batteries"][0]
    assert proof["power_w"] == -400  # Signed AC charge is not forced to zero.
    assert proof["power_reported_at_wall"] == reading.power_stamp
    assert proof["ha_power"]["reported_at_wall"] > reading.power_stamp
    assert proof["ha_power"]["watts"] == -400
    content = json.dumps(proof)
    assert "192.0.2.25" not in content and "PRIVATE_TOKEN" not in content
    assert "Private battery" not in content and "device_ip" not in content
    assert not hass.services.calls


def test_only_discrete_quality_changes_make_events_and_sg_context_is_frozen():
    runtime, hass = context()
    manager, reading = battery(runtime, hass)
    runtime.analysis.capture(1)
    for i in range(5):
        manager.last = [replace(reading, power_stamp=reading.power_stamp+i,
            source_evidence={**reading.source_evidence, "checked_at_wall": reading.power_stamp+i})]
        runtime.analysis.capture(1)
    changes = [e for e in runtime.analysis.events if e["kind"] == "battery_source_change"]
    assert len(changes) == 1
    manager.last = [replace(reading, valid=False, power_valid=False, power_w=None,
        source_code="native_source_stale", source_evidence={"es_reported_at_wall": reading.power_stamp-200})]
    runtime.analysis.capture(1)
    changes = [e for e in runtime.analysis.events if e["kind"] == "battery_source_change"]
    assert len(changes) == 2
    assert changes[-1]["data"]["battery_sources"]["batteries"][0]["power_w"] is None
    original = changes[-1]["data"]["battery_sources"]["batteries"][0]["adapter_check"].copy()
    manager.last = [reading]
    runtime.analysis.capture(1)
    assert changes[-1]["data"]["battery_sources"]["batteries"][0]["adapter_check"] == original
    sg_event = next(e for e in runtime.analysis.events if e["kind"] == "heatpump_change")
    assert sg_event["data"]["electrical_context"]["battery_sources"]["batteries"][0]["power_w"] == -400
    assert not hass.services.calls
