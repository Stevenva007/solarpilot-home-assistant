"""Read-only Aquarea programme evidence; no cloud or actuator calls."""
from enum import IntEnum
import importlib
from types import SimpleNamespace as NS

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.solar_pilot.native_program import NativeClimateProgram

native_program = importlib.import_module("custom_components.solar_pilot.native_program")


ExtendedOperationMode = IntEnum(
    "ExtendedOperationMode", {"OFF": 0, "HEAT": 1, "COOL": 2,
                              "AUTO_HEAT": 3, "AUTO_COOL": 4},
    module="aioaquarea.data")


def device(device_id="pump", mode=ExtendedOperationMode.COOL):
    return NS(device_id=device_id, zones={1: NS(), 2: NS()}, mode=mode)


class Coordinator:
    def __init__(self, device_id="pump"):
        self.device = device(device_id)
        self.device_info = NS(device_id=device_id)
        self.last_update_success = True
        self.listeners = []
        self.api_calls = []

    def async_add_listener(self, listener):
        self.listeners.append(listener)
        return lambda: self.listeners.remove(listener)

    def poll(self, mode=ExtendedOperationMode.COOL, *, success=True, replace=True):
        if replace:
            self.device = device(self.device_info.device_id, mode)
        else:
            self.device.mode = mode
        self.last_update_success = success
        for listener in tuple(self.listeners):
            listener()


def setup(monkeypatch, *, stale_s=1800, platform="aquarea", domain="aquarea",
          unique_id="pump_climate_2", entry_id="native"):
    coordinator = Coordinator()
    entry = NS(domain=domain, runtime_data={"pump": coordinator})
    rows = {"climate.salon": NS(platform=platform, config_entry_id=entry_id,
                               unique_id=unique_id)}
    entries = {"native": entry}
    hass = NS(config_entries=NS(async_get_entry=lambda eid: entries.get(eid)))
    monkeypatch.setattr(er, "async_get", lambda _hass: NS(async_get=rows.get))
    wall = [1000.0]
    monkeypatch.setattr(native_program.time, "monotonic", lambda: wall[0])
    runtime = NS(hass=hass, smart_climate=NS(settings={"stale_s": stale_s}))
    return NativeClimateProgram(runtime), coordinator, rows, entries, wall


def test_initial_cached_device_is_not_proof_and_no_poll_is_requested(monkeypatch):
    helper, coordinator, _, _, _ = setup(monkeypatch)
    for _ in range(3):
        result = helper.read("climate.salon")
        assert result["program"] == "unknown" and not result["fresh"]
        assert result["source"] == "aquarea_poll"
    assert len(coordinator.listeners) == 1
    assert coordinator.api_calls == []


@pytest.mark.parametrize("mode,expected", [
    (ExtendedOperationMode.OFF, "off"),
    (ExtendedOperationMode.HEAT, "heating"),
    (ExtendedOperationMode.COOL, "cooling"),
    (ExtendedOperationMode.AUTO_HEAT, "heating"),
    (ExtendedOperationMode.AUTO_COOL, "cooling"),
])
def test_successful_poll_resolves_true_program_even_when_zone_is_off(monkeypatch, mode, expected):
    helper, coordinator, _, _, _ = setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll(mode)
    result = helper.read("climate.salon")
    assert result["program"] == expected and result["fresh"]
    assert result["raw_mode"] == mode.name and not result["reason"]


@pytest.mark.parametrize("platform,domain,unique_id,entry_id", [
    ("panasonic_cc", "aquarea", "pump_climate_2", "native"),
    ("aquarea", "unrelated", "pump_climate_2", "native"),
    ("aquarea", "aquarea", "other_climate_2", "native"),
    ("aquarea", "aquarea", "pump_climate_3", "native"),
    ("aquarea", "aquarea", "pump_climate_2", "missing"),
    ("aquarea", "aquarea", "pump_climate_2_suffix", "native"),
])
def test_binding_must_match_provider_entry_device_and_zone(monkeypatch, platform, domain, unique_id, entry_id):
    helper, coordinator, _, _, _ = setup(monkeypatch, platform=platform, domain=domain,
                                       unique_id=unique_id, entry_id=entry_id)
    coordinator.poll()
    result = helper.read("climate.salon")
    assert result["program"] == "unknown" and not result["fresh"]
    assert coordinator.listeners == []


@pytest.mark.parametrize("kind", ["mapping_key", "info_id", "device_id", "no_runtime_data"])
def test_invalid_coordinator_shape_is_unknown(monkeypatch, kind):
    helper, coordinator, _, entries, _ = setup(monkeypatch)
    if kind == "mapping_key":
        entries["native"].runtime_data = {"other": coordinator}
    elif kind == "info_id":
        coordinator.device_info.device_id = "other"
    elif kind == "device_id":
        coordinator.device.device_id = "other"
    else:
        entries["native"].runtime_data = None
    assert not helper.read("climate.salon")["fresh"]
    assert not coordinator.listeners


def test_off_does_not_invent_direction_from_current_water_task_or_info_mode(monkeypatch):
    helper, coordinator, _, _, _ = setup(monkeypatch)
    coordinator.device_info.mode = ExtendedOperationMode.HEAT
    helper.read("climate.salon")
    coordinator.poll(ExtendedOperationMode.OFF)
    coordinator.device.current_direction = "WATER"
    coordinator.device.current_action = "HEATING_WATER"
    assert helper.read("climate.salon")["program"] == "off"


@pytest.mark.parametrize("invalid", [1, "HEAT", NS(name="HEAT", value=1),
    IntEnum("OperationMode", {"HEAT": 1}, module="aioaquarea.data").HEAT,
    IntEnum("ExtendedOperationMode", {"HEAT": 8}, module="aioaquarea.data").HEAT,
    IntEnum("ExtendedOperationMode", {"HEAT": 1}, module="other.data").HEAT,
])
def test_unsupported_enums_and_raw_values_do_not_grant_permission(monkeypatch, invalid):
    helper, coordinator, _, _, _ = setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll(invalid)
    assert not helper.read("climate.salon")["fresh"]


@pytest.mark.parametrize("stale_s,valid_age,invalid_age", [(1800, 300, 300.001), (30, 30, 30.001)])
def test_successful_poll_has_bounded_real_age(monkeypatch, stale_s, valid_age, invalid_age):
    helper, coordinator, _, _, wall = setup(monkeypatch, stale_s=stale_s)
    helper.read("climate.salon")
    coordinator.poll()
    wall[0] = 1000 + valid_age
    assert helper.read("climate.salon")["fresh"]
    wall[0] = 1000 + invalid_age
    assert not helper.read("climate.salon")["fresh"]
    coordinator.poll()
    assert helper.read("climate.salon")["fresh"]


def test_repeated_same_object_notifications_cannot_renew_a_stale_poll(monkeypatch):
    helper, coordinator, _, _, wall = setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll()
    wall[0] += 301
    coordinator.poll(replace=False)
    assert not helper.read("climate.salon")["fresh"]


def test_failed_update_invalidates_old_success_until_new_poll(monkeypatch):
    helper, coordinator, _, _, _ = setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll()
    assert helper.read("climate.salon")["fresh"]
    coordinator.poll(success=False)
    assert not helper.read("climate.salon")["fresh"]
    coordinator.last_update_success = True
    assert not helper.read("climate.salon")["fresh"]
    coordinator.poll(ExtendedOperationMode.HEAT)
    assert helper.read("climate.salon")["program"] == "heating"


def test_changed_unpolled_device_or_mode_cannot_reuse_previous_evidence(monkeypatch):
    helper, coordinator, _, _, _ = setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll()
    coordinator.device.mode = ExtendedOperationMode.HEAT
    assert not helper.read("climate.salon")["fresh"]
    coordinator.device = device(mode=ExtendedOperationMode.COOL)
    assert not helper.read("climate.salon")["fresh"]
    coordinator.poll(ExtendedOperationMode.HEAT)
    assert helper.read("climate.salon")["program"] == "heating"


def test_direct_failure_flag_cannot_revive_old_proof_without_new_poll(monkeypatch):
    helper, coordinator, _, _, _ = setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll()
    coordinator.last_update_success = False
    assert not helper.read("climate.salon")["fresh"]
    coordinator.last_update_success = True
    assert not helper.read("climate.salon")["fresh"]
    coordinator.poll()
    assert helper.read("climate.salon")["fresh"]


def test_unpolled_mode_flip_cannot_revive_proof_when_value_flips_back(monkeypatch):
    helper, coordinator, _, _, _ = setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll()
    coordinator.device.mode = ExtendedOperationMode.HEAT
    assert not helper.read("climate.salon")["fresh"]
    coordinator.device.mode = ExtendedOperationMode.COOL
    assert not helper.read("climate.salon")["fresh"]
    coordinator.poll()
    assert helper.read("climate.salon")["fresh"]


def test_source_rebinding_requires_its_own_new_successful_poll(monkeypatch):
    helper, first, rows, entries, _ = setup(monkeypatch)
    helper.read("climate.salon")
    first.poll(ExtendedOperationMode.HEAT)
    first_row = helper.read("climate.salon")
    assert first_row["program"] == "heating"
    second = Coordinator("second")
    entries["second_entry"] = NS(domain="aquarea", runtime_data={"second": second})
    rows["climate.salon"].config_entry_id = "second_entry"
    rows["climate.salon"].unique_id = "second_climate_2"
    assert not helper.read("climate.salon")["fresh"]
    second.poll()
    second_row = helper.read("climate.salon")
    assert second_row["program"] == "cooling"
    assert first_row["binding_key"] != second_row["binding_key"]


def test_close_releases_subscriptions_and_forgets_poll_proof(monkeypatch):
    helper, coordinator, _, _, _ = setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll()
    helper.close()
    assert coordinator.listeners == []
    helper.close()
    assert not helper.read("climate.salon")["fresh"]
    assert len(coordinator.listeners) == 1


def test_two_zones_share_one_verified_device_subscription(monkeypatch):
    helper, coordinator, rows, _, _ = setup(monkeypatch)
    rows["climate.home"] = NS(platform="aquarea", config_entry_id="native", unique_id="pump_climate_1")
    helper.read("climate.salon")
    helper.read("climate.home")
    assert len(coordinator.listeners) == 1
    coordinator.poll(ExtendedOperationMode.AUTO_COOL)
    assert helper.read("climate.salon")["program"] == "cooling"
    assert helper.read("climate.home")["program"] == "cooling"


def test_binding_hash_is_stable_across_polls_and_distinct_for_each_zone(monkeypatch):
    helper, coordinator, rows, _, _ = setup(monkeypatch)
    rows["climate.home"] = NS(platform="aquarea", config_entry_id="native", unique_id="pump_climate_1")
    first = helper.read("climate.salon")["binding_key"]
    coordinator.poll()
    assert helper.read("climate.salon")["binding_key"] == first
    coordinator.poll(ExtendedOperationMode.HEAT)
    assert helper.read("climate.salon")["binding_key"] == first
    assert helper.read("climate.home")["binding_key"] != first
    assert "pump" not in first and "native" not in first


def test_native_entry_reload_releases_old_coordinator_and_waits_for_new_poll(monkeypatch):
    helper, old, _, entries, _ = setup(monkeypatch)
    helper.read("climate.salon")
    old.poll()
    key = helper.read("climate.salon")["binding_key"]
    for _ in range(5):
        new = Coordinator()
        entries["native"].runtime_data = {"pump": new}
        assert not helper.read("climate.salon")["fresh"]
        assert old.listeners == [] and len(helper._watches) == 1
        new.poll()
        assert helper.read("climate.salon")["binding_key"] == key
        assert helper.read("climate.salon")["fresh"]
        old = new


def test_native_entry_unload_releases_coordinator_watch(monkeypatch):
    helper, coordinator, _, entries, _ = setup(monkeypatch)
    helper.read("climate.salon")
    entries.pop("native")
    assert not helper.read("climate.salon")["fresh"]
    assert coordinator.listeners == []


@pytest.mark.parametrize("exception", [ImportError, AttributeError, RuntimeError])
def test_unavailable_registry_capability_returns_unknown(monkeypatch, exception):
    helper, coordinator, _, _, _ = setup(monkeypatch)
    def unavailable(_hass):
        raise exception("Not available")
    monkeypatch.setattr(er, "async_get", unavailable)
    assert not helper.read("climate.salon")["fresh"]
    assert not coordinator.listeners


def test_unavailable_listener_capability_returns_unknown(monkeypatch):
    helper, coordinator, _, _, _ = setup(monkeypatch)
    def unavailable(_listener):
        raise RuntimeError("Coordinator shutting down")
    coordinator.async_add_listener = unavailable
    assert not helper.read("climate.salon")["fresh"]
    assert not helper._watches
