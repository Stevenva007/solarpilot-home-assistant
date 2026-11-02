"""Actionable battery source failures, with fictional sources and no writes."""
from copy import deepcopy
from datetime import datetime, timezone
import json

import pytest

from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from test_battery_runtime import setup_battery
from test_marstek_provider113 import provider
from test_marstek_runtime113 import marstek


@pytest.mark.parametrize("confirmation", [False, None, 1, "true"])
def test_missing_ac_confirmation_names_the_required_configuration(confirmation):
    runtime, hass = marstek(power=0, soc=11, confirmed=confirmation)
    manager = runtime.battery_fleet
    original = deepcopy(runtime.entry.options["batteries"])
    status = manager.source_status()
    assert status["valid"] is False and status["code"] == "ac_unconfirmed"
    assert status["battery_id"] == "storage"
    assert "AC" in status["reason"] and "bevestig" in status["reason"].lower()
    assert manager.source_problem() == status["reason"]
    overview = manager.overview()
    row = overview["batteries"][0]
    assert row["source_code"] == status["code"]
    assert row["reason"] and row["reason"] in status["reason"]
    assert status["reason"] == overview["reason"]
    assert row["soc_valid"] and row["soc_pct"] == 11
    assert not row["power_valid"] and row["power_w"] is None
    assert runtime.entry.options["batteries"] == original
    assert manager.configs["storage"]["ac_power_confirmed"] is False
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_same_configuration_failure_reaches_site_sg_and_global_status():
    runtime, hass = marstek(confirmed=False)
    reason = runtime.battery_fleet.source_problem()
    assert not runtime._site_data()[1]
    budget = sg_solar_budget(runtime)
    assert not budget["valid"] and budget["reason"] == reason
    gates = runtime.sg_boost._gates(data_fresh=False, phase_allowed=True,
                                   priority_allowed=True, hard_limit=False)
    assert reason in gates
    await runtime.tick()
    assert runtime.problem == reason
    assert not hass.services.calls


@pytest.mark.parametrize("soc", [11, "unavailable"])
def test_optional_monitor_soc_has_no_source_failure_when_power_is_proven(soc):
    runtime, hass = marstek(power=450, soc=soc)
    manager = runtime.battery_fleet
    assert manager.source_status()["valid"] is True
    assert manager.source_problem() == ""
    row = manager.overview()["batteries"][0]
    assert row["power_valid"] and row["power_w"] == 450
    assert not row["reason"]
    assert runtime._site_data()[1]
    assert not hass.services.calls


@pytest.mark.parametrize("disable_fleet", [False, True])
def test_disabled_observation_does_not_become_a_required_source_failure(disable_fleet):
    runtime, hass = marstek(confirmed=False)
    manager = runtime.battery_fleet
    if disable_fleet:
        manager.settings["enabled"] = False
    else:
        manager.configs["storage"]["enabled"] = False
    assert manager.source_status()["valid"] is True
    assert manager.source_problem() == ""
    assert not hass.services.calls


@pytest.mark.parametrize("key", ["battery_power", "em_total_power", "pv_power"])
def test_wrong_native_measurement_names_its_scope_without_relabeling_it(provider, key):
    manager = provider.manager
    provider.entities["sensor.fictional_storage_ac"].entity_description.key = key
    status = manager.source_status()
    row = manager.overview()["batteries"][0]
    assert not status["valid"] and status["code"] == "native_source_scope"
    assert status["native_key"] == row["native_key"] == key
    assert status["expected_native_key"] == row["expected_native_key"] == "ongrid_power"
    assert "Vermogen netaansluiting" in status["reason"]
    assert not row["power_valid"] and row["power_w"] is None
    assert provider.entities["sensor.fictional_storage_ac"].entity_description.key == key
    assert not provider.hass.services.calls


def test_native_success_flags_without_actual_ac_field_are_explained(provider):
    next(iter(provider.cache.values()))["response"]["result"].pop("ongrid_power")
    status = provider.manager.source_status()
    assert not status["valid"] and status["code"] == "native_field_unverified"
    assert status["reason"]
    assert status["native_key"] == status["expected_native_key"] == "ongrid_power"
    reading = provider.manager.read()[0]
    assert reading.soc_valid and not reading.power_valid
    assert not provider.hass.services.calls


def test_source_diagnostics_never_expose_transport_or_hardware_identity(provider):
    provider.entities["sensor.fictional_storage_ac"].entity_description.key = "battery_power"
    status = provider.manager.source_status()
    row = provider.manager.overview()["batteries"][0]
    payload = json.dumps({"status": status, "row": row})
    assert "battery_power" in payload and "ongrid_power" in payload
    for private in (provider.host, str(provider.port), "020000000002", "fictional-native-entry",
                    "response", "timestamp", "unique_id", "device_ip"):
        assert private not in payload


def test_a_healthy_sibling_does_not_hide_the_profile_needing_confirmation():
    runtime, hass = marstek(confirmed=False)
    manager = runtime.battery_fleet
    manager.configs["healthy"] = {**manager.configs["storage"], "id": "healthy",
        "name": "Fictieve tweede batterij", "power_entity": "sensor.fictional_second_ac",
        "ac_power_confirmed": True}
    hass.states.set("sensor.fictional_second_ac", 0, {"unit_of_measurement": "W"})
    status = manager.source_status()
    assert not status["valid"] and status["battery_id"] == "storage"
    assert status["code"] == "ac_unconfirmed"
    assert manager.read()[1].power_valid
    assert not runtime._site_data()[1]
    assert not hass.services.calls


def test_diagnostics_do_not_renew_expired_native_field_proof(provider):
    initial = provider.manager.read()[0]
    assert initial.power_valid
    provider.advance(121)
    provider.cache.clear()
    provider.fresh_reply({"bat_soc": 52})
    # Keep the HA publication current while the power field itself was absent.
    for entity in ("sensor.fictional_storage_ac", "sensor.fictional_storage_soc"):
        provider.hass.states.get(entity).last_reported = datetime.fromtimestamp(
            provider.clock.wall, timezone.utc)
    for _ in range(3):
        status = provider.manager.source_status()
        assert not status["valid"] and status["reason"]
    current = provider.manager.read()[0]
    assert not current.power_valid and current.power_w is None
    assert current.soc_valid
    assert not provider.hass.services.calls


@pytest.mark.parametrize("failure,code", [
    ("missing", "source_missing"), ("unit", "source_unit"),
    ("unavailable", "source_unavailable"), ("old", "source_stale"),
    ("future", "source_stale"), ("estimated", "source_estimated"),
])
def test_other_invalid_power_sources_keep_distinct_actionable_reasons(failure, code):
    runtime, hass = marstek()
    cfg = runtime.battery_fleet.configs["storage"]
    if failure == "missing":
        cfg["power_entity"] = "sensor.fictional_missing"
    else:
        attrs = {"unit_of_measurement": "A" if failure == "unit" else "W"}
        if failure == "estimated":
            attrs["estimated"] = True
        age = 121 if failure == "old" else -30 if failure == "future" else 0
        hass.states.set(cfg["power_entity"], "unavailable" if failure == "unavailable" else 0,
                        attrs, reported_age=age)
    status = runtime.battery_fleet.source_status()
    assert not status["valid"] and status["code"] == code
    assert status["reason"] and "Fictieve Venus" in status["reason"]
    assert not runtime._site_data()[1]
    assert not hass.services.calls


def test_generic_battery_still_requires_its_soc_without_borrowing_monitor_policy():
    runtime, hass = setup_battery()
    hass.states.set("sensor.bat_soc", "unavailable", {"unit_of_measurement": "%"})
    status = runtime.battery_fleet.source_status()
    assert not status["valid"] and status["code"] == "source_soc"
    assert status["reason"] and "laadstand" in status["reason"]
    assert not runtime._site_data()[1]
    assert not hass.services.calls
