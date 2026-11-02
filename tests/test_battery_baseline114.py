"""Complete measured battery flow can qualify planning evidence, never control.

All meters and profiles below are fictional; no native provider is contacted.
"""
from copy import deepcopy
from types import SimpleNamespace
import time

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.solar_pilot.battery_profiles import MARSTEK_PROFILE
from custom_components.solar_pilot.battery_runtime import BatteryFleetManager
from test_learning_hub30 import metered, sample


def monitor(index=0, *, sign="discharge_positive", profile=MARSTEK_PROFILE):
    return {"id": f"bat{index}", "name": f"Fictional battery {index}",
            "profile": profile, "power_entity": f"sensor.fictional_battery_ac_{index}",
            "soc_entity": f"sensor.fictional_battery_soc_{index}",
            "power_sign": sign, "ac_power_confirmed": True}


def fleet_metered(profiles=None):
    runtime, hass = metered()
    profiles = [monitor()] if profiles is None else profiles
    for cfg in profiles:
        hass.states.set(cfg["power_entity"], 0, {"unit_of_measurement": "W"})
        if cfg.get("soc_entity"):
            hass.states.set(cfg["soc_entity"], 50, {"unit_of_measurement": "%"})
    runtime.entry.options.update(batteries=profiles,
        battery_fleet={"enabled": True, "control_enabled": False})
    runtime.battery_fleet = BatteryFleetManager(runtime)
    return runtime, hass


@pytest.mark.parametrize("sign,raw,signed", [
    ("discharge_positive", 400, 400), ("charge_positive", -400, 400),
    ("discharge_positive", -400, -400), ("charge_positive", 400, -400),
])
def test_battery_flow_recovers_same_household_residual_in_both_directions(sign, raw, signed):
    runtime, hass = fleet_metered([monitor(sign=sign)])
    hass.states.set("sensor.fictional_battery_ac_0", raw, {"unit_of_measurement": "W"})
    # Battery flow changes P1; correcting it restores the same actual residual.
    hass.states.set("sensor.grid", -700-signed, {"unit_of_measurement": "W"})
    result = sample(runtime)
    assert result["valid"] and result["watts"] == 200
    assert result["parts"]["battery_discharge_signed_w"] == signed
    assert not hass.services.calls


def test_multiple_batteries_are_corrected_as_complete_signed_flow_once():
    runtime, hass = fleet_metered([monitor(), monitor(1, sign="charge_positive")])
    hass.states.set("sensor.fictional_battery_ac_0", .8, {"unit_of_measurement": "kW"})
    hass.states.set("sensor.fictional_battery_ac_1", 250, {"unit_of_measurement": "W"})
    hass.states.set("sensor.grid", -1250, {"unit_of_measurement": "W"})
    result = sample(runtime)
    assert result["valid"] and result["watts"] == 200
    assert result["parts"]["battery_discharge_signed_w"] == 550
    assert len(result["sources"]) == len(set(result["sources"])) == 6


@pytest.mark.parametrize("soc", [None, "unknown", "unavailable", -1, 101, 11])
def test_monitor_soc_has_no_reserve_rule_for_measured_baseline(soc):
    runtime, hass = fleet_metered()
    if soc is None:
        runtime.battery_fleet.configs["bat0"]["soc_entity"] = ""
    else:
        hass.states.set("sensor.fictional_battery_soc_0", soc, {"unit_of_measurement": "%"})
    assert sample(runtime)["valid"]
    assert sample(runtime)["watts"] == 200
    assert not hass.services.calls


@pytest.mark.parametrize("fault", ["missing", "stale", "future", "estimated", "restored", "unit"])
def test_one_unknown_active_battery_prevents_partial_residual(fault):
    runtime, hass = fleet_metered([monitor(), monitor(1)])
    eid = "sensor.fictional_battery_ac_1"
    attrs, value, age = {"unit_of_measurement": "W"}, 0, 0
    if fault == "missing":
        value = "unavailable"
    elif fault == "stale":
        age = 121
    elif fault == "future":
        age = -30
    elif fault in ("estimated", "restored"):
        attrs[fault] = True
    else:
        attrs["unit_of_measurement"] = "kWh"
    hass.states.set(eid, value, attrs, reported_age=age)
    result = sample(runtime)
    assert not result["valid"] and result["watts"] is None
    runtime.battery_fleet.configs["bat1"]["enabled"] = False
    assert sample(runtime)["valid"]


@pytest.mark.parametrize("source", ["sensor.grid", "sensor.pv", "sensor.ev", "sensor.load"])
def test_battery_meter_cannot_reuse_site_ev_or_owned_load_meter(source):
    runtime, _hass = fleet_metered()
    runtime.battery_fleet.configs["bat0"]["power_entity"] = source
    assert not sample(runtime)["valid"]


def test_duplicate_active_battery_meter_does_not_become_two_contributions():
    runtime, _hass = fleet_metered([monitor(), monitor(1)])
    runtime.battery_fleet.configs["bat1"]["power_entity"] = "sensor.fictional_battery_ac_0"
    assert not sample(runtime)["valid"]


@pytest.mark.parametrize("platform", ["template", "integration", "statistics", "derivative"])
def test_known_virtual_battery_meter_remains_excluded(monkeypatch, platform):
    runtime, _hass = fleet_metered()
    monkeypatch.setattr(er, "async_get", lambda _hass: SimpleNamespace(
        async_get=lambda eid: SimpleNamespace(platform=platform if eid ==
            "sensor.fictional_battery_ac_0" else "shelly")))
    assert not sample(runtime)["valid"]


def test_legacy_same_meter_is_counted_once_but_unknown_scope_is_rejected():
    runtime, hass = fleet_metered()
    runtime.settings.update(battery_power_entity="sensor.fictional_battery_ac_0",
                            battery_sign="discharge_positive")
    hass.states.set("sensor.fictional_battery_ac_0", 300, {"unit_of_measurement": "W"})
    hass.states.set("sensor.grid", -1000, {"unit_of_measurement": "W"})
    result = sample(runtime)
    assert result["valid"] and result["watts"] == 200
    assert result["sources"].count("sensor.fictional_battery_ac_0") == 1
    runtime.settings["battery_power_entity"] = "sensor.fictional_unknown_scope"
    hass.states.set("sensor.fictional_unknown_scope", 300, {"unit_of_measurement": "W"})
    assert not sample(runtime)["valid"]
    runtime.settings["battery_power_entity"] = "sensor.fictional_battery_ac_0"
    runtime.settings["battery_sign"] = "charge_positive"
    assert not sample(runtime)["valid"]


@pytest.mark.parametrize("original_age", [121, -30])
def test_fresh_ha_publication_cannot_make_old_or_future_native_proof_usable(monkeypatch, original_age):
    runtime, _hass = fleet_metered()
    runtime.settings["stale_s"] = 300
    original = time.time()-original_age
    monkeypatch.setattr(runtime.battery_fleet, "_monitor_source_stamp",
                        lambda _eid, _role, _stamp, _value, **kwargs: original)
    reading = runtime.battery_fleet.read()[0]
    assert reading.valid  # The learning contract is independently stricter.
    assert not sample(runtime)["valid"]


def test_original_native_receipt_participates_in_source_alignment(monkeypatch):
    runtime, hass = fleet_metered()
    original = time.time()-119
    monkeypatch.setattr(runtime.battery_fleet, "_monitor_source_stamp",
                        lambda _eid, _role, _stamp, _value, **kwargs: original)
    hass.states.set("sensor.grid", -700, {"unit_of_measurement": "W"}, reported_age=-4)
    result = sample(runtime)
    assert not result["valid"] and result["code"] == "source_alignment"


def test_generic_profile_needs_explicit_ac_and_retains_soc_validation():
    runtime, hass = fleet_metered([monitor(profile="generic")])
    cfg = runtime.battery_fleet.configs["bat0"]
    cfg.pop("ac_power_confirmed")
    assert not sample(runtime)["valid"]
    cfg["ac_power_confirmed"] = True
    assert sample(runtime)["valid"]
    hass.states.set("sensor.fictional_battery_soc_0", "unknown", {"unit_of_measurement": "%"})
    assert not sample(runtime)["valid"]


def test_concrete_fleet_source_reason_is_preserved(monkeypatch):
    runtime, _hass = fleet_metered()
    monkeypatch.setattr(runtime.battery_fleet, "source_status", lambda **kwargs:
        {"valid": False, "code": "native_field", "reason": "Fictional AC receipt is missing"})
    result = sample(runtime)
    assert not result["valid"] and result["reason"] == "Fictional AC receipt is missing"


def test_sampling_with_valid_monitor_does_not_change_permissions_or_realtime_budget():
    runtime, hass = fleet_metered()
    before = deepcopy(runtime.settings), deepcopy(runtime.battery_fleet.configs)
    budget_before = runtime._site_data()
    result = sample(runtime)
    assert result["valid"]
    assert (runtime.settings, runtime.battery_fleet.configs) == before
    assert runtime._site_data()[:4] == budget_before[:4]
    assert not hass.services.calls
