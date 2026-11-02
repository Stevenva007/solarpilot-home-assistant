"""Source explanations remain observations, using only fictional providers."""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
import json
import time

import pytest

from custom_components.solar_pilot.battery_runtime import monitor_source_identity
from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from custom_components.solar_pilot.learning_hub import measured_baseline
from test_battery_baseline114 import fleet_metered, monitor
from test_learning_hub30 import sample
from test_marstek_provider113 import provider
from test_marstek_runtime113 import marstek


@pytest.mark.asyncio
async def test_mutating_returned_diagnostics_cannot_confirm_or_control_the_monitor():
    runtime, hass = marstek(power=0, confirmed=False)
    manager = runtime.battery_fleet
    config_before = deepcopy(manager.configs)
    persisted_before = deepcopy(runtime.entry.options)
    status = manager.source_status()
    status.update(valid=True, code="", reason="", native_key="ongrid_power")
    overview = manager.overview()
    overview["batteries"][0].update(power_valid=True, power_w=0, source_code="")
    assert not manager.source_status()["valid"]
    assert not runtime._site_data()[1]
    assert not sg_solar_budget(runtime)["valid"]
    assert not await manager._send("storage", 0)
    assert manager.configs == config_before
    assert runtime.entry.options == persisted_before
    assert not hass.services.calls


def test_restoring_the_first_condition_cannot_hide_the_next_native_source_failure(provider):
    cfg = provider.manager.configs["storage"]
    entity = provider.entities["sensor.fictional_storage_ac"]
    entity.entity_description.key = "battery_power"
    cfg["ac_power_confirmed"] = False
    assert provider.manager.source_status()["code"] == "ac_unconfirmed"
    cfg["ac_power_confirmed"] = True
    assert provider.manager.source_status()["code"] == "native_source_scope"
    entity.entity_description.key = "ongrid_power"
    next(iter(provider.cache.values()))["response"]["result"].pop("ongrid_power")
    assert provider.manager.source_status()["code"] == "native_field_unverified"
    provider.fresh_reply({"ongrid_power": 800, "bat_soc": 52})
    assert provider.manager.source_status()["valid"]
    assert not provider.manager.source_problem()
    assert provider.manager.read()[0].power_valid
    assert not provider.hass.services.calls


def test_native_unknown_descriptor_is_not_exported_as_an_identity(provider):
    private_descriptor = "fictional_private_device_serial_0123456789"
    provider.entities["sensor.fictional_storage_ac"].entity_description.key = private_descriptor
    identity = monitor_source_identity(provider.hass, "sensor.fictional_storage_ac",
                                       power_sign="discharge_positive")
    assert identity["code"] == "native_source_scope"
    assert identity["native_key"] is None
    payload = json.dumps({"identity": identity, "status": provider.manager.source_status(),
                          "overview": provider.manager.overview()})
    assert private_descriptor not in payload
    assert provider.host not in payload
    assert "020000000002" not in payload


def test_original_native_deadline_is_inclusive_but_never_slides_on_diagnostics(provider):
    original = provider.manager.read()[0].power_stamp
    provider.advance(106)  # The raw field was already 14 seconds old.
    at_boundary = provider.manager.read()[0]
    assert at_boundary.power_valid
    assert at_boundary.power_stamp == original
    for _ in range(3):
        assert provider.manager.source_status()["valid"]
        assert provider.manager.read()[0].power_stamp == original
    provider.advance(.001)
    expired = provider.manager.source_status()
    assert not expired["valid"]
    assert provider.manager.read()[0].power_w is None


@pytest.mark.parametrize("confirmed", [False, True])
def test_diagnostic_reads_keep_unknown_power_out_of_phase_and_solar_budget(provider, confirmed):
    from test_marstek_phase113 import phase_view

    provider.manager.configs["storage"]["ac_power_confirmed"] = confirmed
    provider.coordinator.data["es_status_fresh"] = False
    for _ in range(3):
        assert not provider.manager.source_status()["valid"]
        assert not provider.runtime._site_data()[1]
        assert not sg_solar_budget(provider.runtime)["valid"]
        assert phase_view(provider)["phases"][0]["batteries"] == []
    assert not provider.hass.services.calls


def test_opposite_flows_and_same_legacy_reference_are_corrected_once():
    runtime, hass = fleet_metered([monitor(), monitor(1, sign="charge_positive")])
    runtime.settings.update(battery_power_entity="sensor.fictional_battery_ac_0",
                            battery_sign="discharge_positive")
    hass.states.set("sensor.fictional_battery_ac_0", 850, {"unit_of_measurement": "W"})
    hass.states.set("sensor.fictional_battery_ac_1", 550, {"unit_of_measurement": "W"})
    result = sample(runtime)
    assert result["valid"] and result["watts"] == 500
    assert result["parts"]["battery_discharge_signed_w"] == 300
    assert result["sources"].count("sensor.fictional_battery_ac_0") == 1
    assert result["sources"].count("sensor.fictional_battery_ac_1") == 1
    assert not hass.services.calls


@pytest.mark.parametrize("forged", [True, False])
def test_baseline_never_accepts_an_incomplete_or_duplicated_reading_set(monkeypatch, forged):
    runtime, _hass = fleet_metered([monitor(), monitor(1)])
    readings = runtime.battery_fleet.read()
    incoming = [readings[0], replace(readings[0], id="bat0")] if forged else [readings[0]]
    monkeypatch.setattr(runtime.battery_fleet, "read", lambda: incoming)
    # Even a loose diagnostic consumer must not replace the concrete reading
    # completeness checks performed by the learning calculation.
    monkeypatch.setattr(runtime.battery_fleet, "source_status", lambda **kwargs:
                        {"valid": True, "reason": ""})
    result = sample(runtime)
    assert not result["valid"] and result["watts"] is None


@pytest.mark.parametrize("age,valid", [(120, True), (120.001, False)])
def test_baseline_respects_original_proof_at_its_own_120_second_boundary(monkeypatch, age, valid):
    runtime, _hass = fleet_metered()
    wall = datetime.now(timezone.utc).timestamp()
    runtime.settings["stale_s"] = 300
    monkeypatch.setattr(runtime.battery_fleet, "_monitor_source_stamp",
                        lambda *_args, **_kwargs: wall-age)
    result = measured_baseline(runtime, datetime.fromtimestamp(wall, timezone.utc), time.monotonic())
    assert result["valid"] is valid
    assert result["watts"] == (200 if valid else None)


@pytest.mark.parametrize("bad_ref", [[], {}, ["sensor.fictional_storage_ac"],
                                    {"entity_id": "sensor.fictional_storage_ac"}])
def test_malformed_active_power_reference_stays_required_and_unknown(bad_ref):
    runtime, hass = fleet_metered()
    runtime.battery_fleet.configs["bat0"]["power_entity"] = bad_ref
    reading = runtime.battery_fleet.read()[0]
    assert not reading.valid and not reading.power_valid and reading.power_w is None
    status = runtime.battery_fleet.source_status()
    assert not status["valid"] and status["reason"]
    assert not runtime._site_data()[1]
    assert not sg_solar_budget(runtime)["valid"]
    result = sample(runtime)
    assert not result["valid"] and result["watts"] is None
    assert not hass.services.calls


@pytest.mark.parametrize("bad_ref", [[], {}, ["sensor.fictional_storage_soc"],
                                    {"entity_id": "sensor.fictional_storage_soc"}])
def test_malformed_optional_soc_reference_cannot_hide_known_monitor_power(bad_ref):
    runtime, hass = fleet_metered()
    runtime.battery_fleet.configs["bat0"]["soc_entity"] = bad_ref
    reading = runtime.battery_fleet.read()[0]
    assert reading.valid and reading.power_valid and reading.power_w == 0
    assert not reading.soc_valid and reading.soc_pct is None
    assert runtime.battery_fleet.source_status()["valid"]
    assert sample(runtime)["watts"] == 200
    assert not hass.services.calls


@pytest.mark.parametrize("bad_key", [[], {}, ["ongrid_power"], {"key": "ongrid_power"}])
def test_malformed_native_descriptor_is_unknown_without_exporting_raw_metadata(provider, bad_key):
    provider.entities["sensor.fictional_storage_ac"].entity_description.key = bad_key
    status = provider.manager.source_status()
    assert not status["valid"] and status["code"] == "native_source_scope"
    assert status["native_key"] is None and status["expected_native_key"] == "ongrid_power"
    assert provider.manager.read()[0].power_w is None
    assert not provider.hass.services.calls
