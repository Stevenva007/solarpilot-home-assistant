"""Aquarea 2.0.1 entity migration compatibility.

The upstream migration keeps the native unique id and device ownership but
moves pump status from ``sensor`` to ``binary_sensor``.  Direction becomes a
lowercase enum state.  These fixtures exercise only SolarPilot's read-only
registry and current-state checks; they perform no cloud or device command.
"""
from types import SimpleNamespace as NS

import pytest

from custom_components.solar_pilot.cloud_energy_period import period_evidence
from test_aquarea_display_snapshot86 import modern_setup


def _migrate_pump_entity(env):
    old_id = env.sources["pump_status_entity"]
    row = env.rows.pop(old_id)
    new_id = old_id.replace("sensor.", "binary_sensor.", 1)
    env.rows[new_id] = NS(
        entity_id=new_id,
        unique_id=row.unique_id,
        platform=row.platform,
        config_entry_id=row.config_entry_id,
        device_id=row.device_id,
        disabled_by=None,
    )
    state = env.helper.runtime.hass.states.data.pop(old_id)
    env.helper.runtime.hass.states.data[new_id] = state
    return new_id


def test_201_binary_pump_and_lowercase_direction_keep_read_only_display(monkeypatch):
    env = modern_setup(monkeypatch, version="2.0.1")
    pump_id = _migrate_pump_entity(env)
    env.state(pump_id, "on")
    env.state(env.sources["direction_entity"], "pump")

    sources = env.helper.display_sources()
    assert sources["pump_status_entity"] == pump_id
    assert sources["direction_entity"] == env.sources["direction_entity"]
    assert env.helper.read_source_contract(sources)["status"] == "unknown"

    env.coordinator.poll()
    result = env.helper.read_source_contract(sources)
    assert result["status"] == "verified"
    assert result["pump"]["state"] == "on"
    assert result["direction"]["state"] == "PUMP"
    assert result["read_only"] is True
    assert env.coordinator.api_calls == []
    assert env.helper.runtime.hass.services.calls == []


def test_201_interrupted_migration_with_both_domains_fails_closed(monkeypatch):
    env = modern_setup(monkeypatch, version="2.0.1")
    binary_id = "binary_sensor.pump_pump_status"
    old = env.rows[env.sources["pump_status_entity"]]
    env.rows[binary_id] = NS(
        entity_id=binary_id,
        unique_id=old.unique_id,
        platform=old.platform,
        config_entry_id=old.config_entry_id,
        device_id=old.device_id,
        disabled_by=None,
    )
    env.state(binary_id, "on")

    sources = env.helper.display_sources()
    assert sources["pump_status_entity"] == ""
    env.coordinator.poll()
    result = env.helper.read_source_contract(sources)
    assert result["status"] == "unknown"
    assert result["reason_code"] == "native_source_mapping_unverified"


def test_legacy_sensor_pump_source_remains_supported(monkeypatch):
    env = modern_setup(monkeypatch, version="1.5.4")
    assert env.sources["pump_status_entity"].startswith("sensor.")
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"
    env.coordinator.poll()
    assert env.helper.read_source_contract(env.sources)["status"] == "verified"


@pytest.mark.parametrize(
    "key",
    [
        "today_energy_consumption",
        "heating_today_energy_consumption",
        "lifetime_energy_consumption",
        "heating_lifetime_energy_consumption",
    ],
)
def test_201_new_energy_types_are_not_relabelled_as_old_period_sources(key):
    assert period_evidence(
        {"integration_loaded": True, "integration_domain": "aquarea"},
        key,
        period_start=None,
        fetched_at=None,
        reported_at=None,
        captured_at=None,
    ) is None
