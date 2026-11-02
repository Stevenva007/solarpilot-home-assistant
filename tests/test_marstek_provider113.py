"""Read-only taurgis v1.12 field provenance, using fictional provider doubles.

No provider module, transport, credentials or private diagnostic is loaded.
"""
from copy import deepcopy
from datetime import datetime, timezone
from types import ModuleType, SimpleNamespace
import sys
import time

import pytest
from homeassistant.helpers import entity_registry as er

from test_marstek_runtime113 import marstek


@pytest.fixture
def provider(monkeypatch):
    runtime, hass = marstek(power=800, soc=52)
    clock = SimpleNamespace(wall=time.time(), mono=5000.0)
    monkeypatch.setattr(sys.modules["custom_components.solar_pilot.battery_runtime"].time,
                        "time", lambda: clock.wall)
    host, port = "192.0.2.10", 30000
    coordinator_type = type("MarstekDataUpdateCoordinator", (), {
        "__module__": "custom_components.marstek.coordinator",
    })
    coordinator = coordinator_type()
    coordinator.device_ip, coordinator.device_port = host, port
    coordinator.data = {"ongrid_power": 800, "battery_soc": 52,
        "es_status_fresh": True, "has_fresh_data": True, "last_update": clock.mono}
    coordinator.last_update_success = True
    coordinator.consecutive_failures = 0
    stats = {"ES.GetStatus": {"last_success": True, "last_updated": clock.wall-14}}
    coordinator.last_update_success_time = datetime.fromtimestamp(clock.wall-13, timezone.utc)
    cache = {(host, 1): {"response": {"id": 1, "result": {
        "id": 0, "ongrid_power": 800, "bat_soc": 52}},
        "addr": (host, port), "timestamp": clock.mono-14}}
    reads = []

    def command_stats(ip):
        reads.append(ip)
        return deepcopy(stats)

    client = SimpleNamespace(_router=SimpleNamespace(cache=cache),
        get_command_stats_for_ip=command_stats, loop_time=lambda: clock.mono)
    coordinator.udp_client = client
    entry = SimpleNamespace(entry_id="fictional-native-entry", domain="marstek",
        runtime_data=SimpleNamespace(coordinator=coordinator))
    rows, entities = {}, {}
    for eid, key in (("sensor.fictional_storage_ac", "ongrid_power"),
                     ("sensor.fictional_storage_soc", "battery_soc")):
        uid = "020000000002_"+key
        rows[eid] = SimpleNamespace(entity_id=eid, platform="marstek",
            device_id="fictional-native-device", config_entry_id=entry.entry_id,
            unique_id=uid, disabled_by=None)
        entities[eid] = SimpleNamespace(entity_id=eid, unique_id=uid,
            coordinator=coordinator, entity_description=SimpleNamespace(key=key))
    monkeypatch.setattr(er, "async_get", lambda _hass: SimpleNamespace(async_get=rows.get))
    hass.config_entries = SimpleNamespace(async_get_entry=lambda eid:
        entry if eid == entry.entry_id else None)
    # Current HA stores loaded platforms under entity_component.DATA_INSTANCES,
    # not hass.data["sensor"]. Keep the public unit-double convention used by
    # the existing native cloud-source tests, and leave the old key absent.
    component_module = ModuleType("homeassistant.helpers.entity_component")
    component_module.DATA_INSTANCES = "entity_components"
    monkeypatch.setitem(sys.modules, component_module.__name__, component_module)
    hass.data[component_module.DATA_INSTANCES] = {
        "sensor": SimpleNamespace(get_entity=entities.get),
    }
    manager = runtime.battery_fleet

    def stamp(role="power"):
        key, eid = (("ongrid_power", "sensor.fictional_storage_ac") if role == "power"
                    else ("battery_soc", "sensor.fictional_storage_soc"))
        return manager._monitor_source_stamp(eid, role, clock.wall, coordinator.data[key])

    def advance(seconds):
        clock.wall += seconds
        clock.mono += seconds

    def fresh_reply(result, *, request_id=2):
        cache[(host, request_id)] = {"response": {"id": request_id, "result": result},
            "addr": (host, port), "timestamp": clock.mono}
        stats["ES.GetStatus"].update(last_success=True, last_updated=clock.wall)
        # The coordinator finishes after the UDP receipt; avoid an artificial
        # equality rounding difference between epoch floats and datetime.
        coordinator.last_update_success_time = datetime.fromtimestamp(clock.wall+.001, timezone.utc)
        coordinator.data["last_update"] = clock.mono

    return SimpleNamespace(runtime=runtime, hass=hass, manager=manager, clock=clock,
        host=host, port=port, coordinator=coordinator, entry=entry, rows=rows,
        entities=entities, cache=cache, stats=stats, reads=reads, stamp=stamp,
        advance=advance, fresh_reply=fresh_reply)


def test_fresh_native_fields_keep_actual_received_time(provider):
    for role in ("power", "soc"):
        assert provider.stamp(role) == pytest.approx(provider.clock.wall-14)
    reading = provider.manager.read()[0]
    assert reading.valid and reading.power_w == 800 and reading.soc_pct == 52
    assert reading.power_stamp == pytest.approx(provider.clock.wall-14)
    assert not provider.hass.services.calls


def test_fresh_ha_reports_do_not_renew_old_native_evidence(provider):
    original = provider.stamp()
    provider.advance(30)
    assert provider.stamp() == original
    provider.advance(100)
    assert provider.stamp() is None


def test_cache_eviction_keeps_only_bounded_original_proof(provider):
    original = provider.stamp()
    provider.cache.clear()
    provider.advance(30)
    assert provider.stamp() == original
    provider.advance(100)
    assert provider.stamp() is None


def test_successful_partial_reply_does_not_refresh_missing_ac_field(provider):
    original = provider.stamp()
    provider.advance(30)
    provider.cache.clear()
    provider.fresh_reply({"bat_soc": 52})
    assert provider.stamp("soc") == pytest.approx(provider.clock.wall)
    assert provider.stamp() == original
    provider.advance(100)
    provider.fresh_reply({"bat_soc": 52}, request_id=3)
    assert provider.stamp() is None


def test_fresh_equal_ac_field_is_new_evidence_without_a_state_change(provider):
    original = provider.stamp()
    provider.advance(30)
    provider.fresh_reply({"ongrid_power": 800, "bat_soc": 52})
    assert provider.stamp() == pytest.approx(provider.clock.wall)
    assert provider.stamp() > original


@pytest.mark.parametrize("role,missing", [("power", "ongrid_power"), ("soc", "bat_soc")])
def test_first_read_requires_actual_field_presence_not_success_flags(provider, role, missing):
    next(iter(provider.cache.values()))["response"]["result"].pop(missing)
    assert provider.stamp(role) is None


@pytest.mark.parametrize("corruption", [
    "wrong_host", "wrong_port", "raw_mismatch", "error_reply", "future_reply", "nan_field",
])
def test_unrelated_or_invalid_raw_payload_cannot_prove_current_ac(provider, corruption):
    item = next(iter(provider.cache.values()))
    if corruption == "wrong_host":
        item["addr"] = ("192.0.2.11", provider.port)
    elif corruption == "wrong_port":
        item["addr"] = (provider.host, provider.port+1)
    elif corruption == "raw_mismatch":
        item["response"]["result"]["ongrid_power"] = 799
    elif corruption == "error_reply":
        item["response"]["error"] = {"code": -1}
    elif corruption == "future_reply":
        item["timestamp"] = provider.clock.mono+30
    else:
        item["response"]["result"]["ongrid_power"] = float("nan")
    assert provider.stamp() is None


@pytest.mark.parametrize("mutation", ["registry_device", "registry_unique", "coordinator"])
def test_old_proof_does_not_survive_rebinding(provider, mutation):
    assert provider.stamp() is not None
    provider.cache.clear()
    if mutation == "registry_device":
        provider.rows["sensor.fictional_storage_ac"].device_id = "replacement-device"
    elif mutation == "registry_unique":
        provider.rows["sensor.fictional_storage_ac"].unique_id = "replacement_ongrid_power"
        provider.entities["sensor.fictional_storage_ac"].unique_id = "replacement_ongrid_power"
    else:
        replacement = type(provider.coordinator)()
        replacement.__dict__.update(provider.coordinator.__dict__)
        provider.entry.runtime_data.coordinator = replacement
        for entity in provider.entities.values():
            entity.coordinator = replacement
    assert provider.stamp() is None


@pytest.mark.parametrize("key", ["battery_power", "em_total_power", "pv_power"])
def test_native_sensor_scope_cannot_be_relabelled_as_battery_ac(provider, key):
    provider.entities["sensor.fictional_storage_ac"].entity_description.key = key
    assert provider.stamp() is None


@pytest.mark.parametrize("failure", ["es_timeout", "coordinator_failure", "cached_poll"])
def test_provider_failure_flags_do_not_become_fresh_success(provider, failure):
    if failure == "es_timeout":
        provider.stats["ES.GetStatus"]["last_success"] = False
    elif failure == "coordinator_failure":
        provider.coordinator.last_update_success = False
    else:
        provider.coordinator.data["es_status_fresh"] = False
    assert provider.stamp() is None


def test_ac_proof_does_not_supply_missing_soc_proof(provider):
    next(iter(provider.cache.values()))["response"]["result"].pop("bat_soc")
    reading = provider.manager.read()[0]
    assert reading.valid and reading.power_valid and reading.power_w == 800
    assert not reading.soc_valid and reading.soc_pct is None


def test_new_manager_does_not_restore_unproved_native_fields(provider):
    from custom_components.solar_pilot.battery_runtime import BatteryFleetManager
    assert provider.stamp() is not None
    provider.cache.clear()
    replacement = BatteryFleetManager(provider.runtime)
    reading = replacement.read()[0]
    assert not reading.valid and not reading.power_valid
    assert reading.power_w is None and not provider.hass.services.calls


def test_fresh_ac_packet_does_not_refresh_carried_forward_soc(provider):
    assert provider.stamp("soc") is not None
    provider.advance(120)
    provider.cache.clear()
    provider.fresh_reply({"ongrid_power": 800})
    for entity_id in provider.rows:
        # New HA publication can carry old SoC; only received fields count.
        provider.hass.states.get(entity_id).last_reported = datetime.fromtimestamp(
            provider.clock.wall, timezone.utc)
    reading = provider.manager.read()[0]
    assert reading.valid and reading.power_w == 800
    assert reading.power_stamp == pytest.approx(provider.clock.wall)
    assert reading.soc_pct is None and not reading.soc_valid


def test_known_native_ac_sign_cannot_be_reversed_by_profile_option(provider):
    provider.manager.configs["storage"]["power_sign"] = "charge_positive"
    reading = provider.manager.read()[0]
    assert not reading.power_valid and reading.power_w is None
    assert reading.soc_valid and reading.soc_pct == 52


def test_a_new_value_cannot_reuse_a_previous_packet_time(provider):
    assert provider.stamp() is not None
    provider.coordinator.data["ongrid_power"] = 900
    next(iter(provider.cache.values()))["response"]["result"]["ongrid_power"] = 900
    assert provider.stamp() is None


def test_backward_native_clock_cannot_extend_a_proof(provider):
    assert provider.stamp() is not None
    provider.clock.mono -= 100
    assert provider.stamp() is None
