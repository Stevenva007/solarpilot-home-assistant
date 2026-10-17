"""Presentation snapshots share work without granting fresh control evidence."""
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS

import pytest

from test_runtime import build
from test_sensor_recorder59 import sensor
from test_cloud_energy_period91 import setup_source, PROVIDER
from custom_components.solar_pilot.cloud_energy_period import cloud_energy_periods


def test_panasonic_values_attributes_and_status_share_snapshot_and_refresh(monkeypatch):
    runtime, hass = build()
    calls = []
    observation = {"status": "old", "power_w": 100, "source_reported_at": 123}

    def overview():
        calls.append(dict(observation))
        return dict(observation)

    monkeypatch.setattr(runtime.panasonic, "overview", overview)
    entities = [sensor(runtime, suffix) for suffix in (
        "panasonic_status", "panasonic_power", "dhw_status", "dhw_temperature", "dhw_target")]
    for entity in entities:
        entity.native_value
        assert entity.extra_state_attributes["source_reported_at"] == 123
    assert len(calls) == 1
    observation.update(status="new", power_w=200)
    assert entities[1].native_value == 100
    assert runtime.panasonic.overview()["power_w"] == 200  # live control read
    frames = []
    runtime.subscribe(lambda: frames.append((entities[0].native_value, entities[1].native_value,
                                             entities[0].extra_state_attributes["source_reported_at"])))
    runtime.publish()
    assert frames == [("new", 200, 123)]  # no synthetic freshness
    assert len(calls) == 3
    assert not hass.services.calls


@pytest.mark.parametrize("modern", [True, False])
def test_hub_is_registered_before_consumer_and_legacy_remains_supported(monkeypatch, modern):
    import homeassistant.helpers as helpers
    runtime, hass = build()
    runtime.configs = {"consumer": {"name": "Synthetic consumer"}}
    calls = []
    registry = NS(async_get_or_create=lambda **kw: (calls.append(kw), NS(id="hub-id"))[1])
    if modern:
        registry.async_get_device_by_identifier = lambda identifier, entry: None
    dr = ModuleType("homeassistant.helpers.device_registry")
    dr.async_get = lambda _: registry
    monkeypatch.setitem(sys.modules, dr.__name__, dr)
    monkeypatch.setattr(helpers, "device_registry", dr, raising=False)
    em = ModuleType("homeassistant.helpers.entity")
    em.Entity, em.DeviceInfo = type("Entity", (), {}), dict
    monkeypatch.setitem(sys.modules, em.__name__, em)
    path = Path(__file__).parents[1] / "custom_components/solar_pilot/entity.py"
    spec = importlib.util.spec_from_file_location("custom_components.solar_pilot._entity96", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    added = []
    runtime.platforms.register("sensor", added.extend,
        lambda: [module.SolarEntity(runtime, "state", "State", "consumer")])
    info = added[0]._attr_device_info
    if modern:
        assert len(calls) == 1
        assert calls[0]["config_entry_id"] == runtime.entry.entry_id
        assert info["via_device_id"] == "hub-id" and "via_device" not in info
        runtime.platforms.prepare_hub()
        assert len(calls) == 1
    else:
        assert not calls and "via_device" in info and "via_device_id" not in info


@pytest.mark.asyncio
@pytest.mark.parametrize("modern", [True, False])
async def test_device_rename_uses_own_entry_and_never_touches_source_devices(monkeypatch, modern):
    import homeassistant.helpers as helpers
    from custom_components.solar_pilot.const import DOMAIN
    runtime, hass = build()
    runtime.configs = {"consumer": {"name": "Synthetic consumer"}}
    identifier = (DOMAIN, f"{runtime.entry.entry_id}_consumer")
    reads, writes = [], []

    def scoped_lookup(actual, entry):
        reads.append((actual, entry))
        assert actual == identifier and entry == runtime.entry.entry_id
        return NS(id="owned-virtual-device")

    def legacy_lookup(*, identifiers):
        assert not modern, "Modern Core must not use the unscoped lookup"
        reads.append(identifiers)
        assert identifiers == {identifier}
        return NS(id="owned-virtual-device")

    registry = NS(async_get_device=legacy_lookup,
        async_update_device=lambda device_id, **fields: writes.append((device_id, fields)))
    if modern:
        registry.async_get_device_by_identifier = scoped_lookup
    dr = ModuleType("homeassistant.helpers.device_registry")
    dr.async_get = lambda _: registry
    monkeypatch.setitem(sys.modules, dr.__name__, dr)
    monkeypatch.setattr(helpers, "device_registry", dr, raising=False)
    await runtime.platforms.refresh()

    assert len(reads) == 1
    assert writes == [("owned-virtual-device", {"name": "Synthetic consumer"})]
    assert not hass.services.calls


def test_aquarea_160_interval_delta_is_not_relabelled_as_daily_energy(monkeypatch):
    # Upstream 1.6.0 replaces the old daily sensors with interval deltas, removes
    # ENERGY and period_being_processed; monthly accumulated sensors stay intact.
    env = setup_source(monkeypatch)
    env.state.attributes.pop("device_class")
    env.state.attributes["state_class"] = "measurement"
    del env.entity.period_being_processed
    assert cloud_energy_periods(env.hass, [env.eid], {**PROVIDER, "integration_version": "1.6.0"},
                                captured_at=env.captured) == {}
