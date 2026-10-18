"""A newer HA report cannot make cached native tank readings current."""
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot.panasonic_monitor import PanasonicMonitor
from test_aquarea_semantics98 import split_setup
from test_aquarea_display_snapshot86 import modern_setup

BASE = datetime(2026, 10, 11, 9, tzinfo=timezone.utc).timestamp()


def monitored(monkeypatch, *, legacy=False, sensor_temperature=False):
    env = modern_setup(monkeypatch) if legacy else split_setup(monkeypatch)
    env.clock[0] = BASE
    env.helper._display_metadata_checked = BASE
    runtime = env.helper.runtime
    runtime.settings = {}
    runtime.hass.config = SimpleNamespace(units=SimpleNamespace(temperature_unit="°C"))
    tank = env.sources["tank_entity"]
    temperature = tank
    if sensor_temperature:
        temperature = "sensor.fictional_native_temperature"
        env.rows[temperature] = SimpleNamespace(entity_id=temperature, platform="aquarea",
            config_entry_id="native", unique_id="pump_tank_temperature",
            device_id=env.rows[tank].device_id, disabled_by=None)
        env.state(temperature, "47", {"unit_of_measurement": "°C"}, stamp=BASE-7)
    env.state(tank, "idle", {"temperature_unit": "°C", "current_temperature": 52,
        "temperature": 50}, stamp=BASE-7)
    for eid in env.sources["zone_entities"]:
        env.state(eid, "heat", {"hvac_action": "heating", "temperature_unit": "°C",
            "current_temperature": 21, "temperature": 22}, stamp=BASE-7)
    monitor = PanasonicMonitor(runtime, {"tank_temperature_entity": temperature,
        "tank_target_entity": tank, "zone_entities": env.sources["zone_entities"], "stale_s": 120})
    runtime.panasonic = monitor
    monitor.native_program = env.helper
    return env, monitor


@pytest.mark.parametrize("quality", ["LIVE", "CACHED", None, True, False, 0, 1, "untyped_live"])
def test_original_bound_temperatures_require_actual_typed_live_quality(quality, monkeypatch):
    env, monitor = monitored(monkeypatch)
    value = getattr(env.quality, quality) if quality in ("LIVE", "CACHED") else "LIVE" if quality == "untyped_live" else quality
    env.poll(quality=value)
    snapshot = monitor.overview()
    good = quality == "LIVE"
    assert snapshot["temperature_c"] == (52 if good else None)
    assert snapshot["target_c"] == (50 if good else None)
    assert snapshot["temperature_stamp"] == (BASE-7 if good else None)
    assert snapshot["target_stamp"] == (BASE-7 if good else None)
    assert snapshot["display_tank"]["temperature_c"] == (52 if good else None)
    assert snapshot["display_tank"]["target_c"] == (50 if good else None)
    assert all(row["available"] is good for row in snapshot["zones"])
    if not good:
        assert snapshot["native_task"].get("function") is None
        assert snapshot["context_reliable"] is False and snapshot["cooling_possible"] is True
    assert not env.helper.runtime.hass.services.calls and env.coordinator.api_calls == []


def test_registered_native_temperature_sensor_obeys_the_same_cached_quality_veto(monkeypatch):
    env, monitor = monitored(monkeypatch, sensor_temperature=True)
    env.poll(quality=env.quality.CACHED)
    assert monitor.overview()["temperature_c"] is None
    env.poll(quality=env.quality.LIVE)
    assert monitor.overview()["temperature_c"] == 47


def test_legacy_status_without_data_mode_keeps_original_temperature_contract(monkeypatch):
    env, monitor = monitored(monkeypatch, legacy=True)
    assert not hasattr(env.coordinator.device._status, "data_mode")
    snapshot = monitor.overview()
    assert snapshot["temperature_c"] == snapshot["display_tank"]["temperature_c"] == 52
    assert snapshot["target_c"] == snapshot["display_tank"]["target_c"] == 50
    assert snapshot["temperature_stamp"] == snapshot["target_stamp"] == BASE-7


def test_generic_independent_temperature_is_not_blocked_by_a_cached_native_tank(monkeypatch):
    env, monitor = monitored(monkeypatch)
    external = "sensor.fictional_independent_temperature"
    env.rows[external] = SimpleNamespace(entity_id=external, platform="mqtt", config_entry_id="external",
        unique_id="external-temperature", device_id="external-device", disabled_by=None)
    env.state(external, "43", {"unit_of_measurement": "°C"}, stamp=BASE-3)
    monitor.update_config({**monitor.settings, "tank_temperature_entity": external})
    env.poll(quality=env.quality.CACHED)
    snapshot = monitor.overview()
    assert snapshot["temperature_c"] == 43 and snapshot["temperature_stamp"] == BASE-3
    assert snapshot["target_c"] is None and snapshot["display_tank"]["target_c"] is None


def test_rebound_aquarea_registry_source_cannot_borrow_another_devices_live_status(monkeypatch):
    env, monitor = monitored(monkeypatch)
    env.poll(quality=env.quality.LIVE)
    assert monitor.overview()["temperature_c"] == 52
    env.rows[env.sources["tank_entity"]].unique_id = "fictional-other-device_tank"
    snapshot = monitor.overview()
    assert snapshot["temperature_c"] is None and snapshot["target_c"] is None
    assert snapshot["display_tank"]["temperature_c"] is None


def test_rejected_cached_status_cannot_be_revived_by_an_in_place_quality_edit(monkeypatch):
    env, monitor = monitored(monkeypatch)
    env.poll(quality=env.quality.CACHED)
    assert monitor.overview()["temperature_c"] is None
    env.coordinator.device._status.data_mode = env.quality.LIVE
    edited = monitor.overview()
    assert edited["temperature_c"] is None and edited["target_c"] is None
    assert edited["native_task"].get("function") is None and edited["context_reliable"] is False
    env.poll(quality=env.quality.LIVE)
    current = monitor.overview()
    assert current["temperature_c"] == 52 and current["target_c"] == 50
    assert all(row["available"] for row in current["zones"])
