"""Independent, read-only SG profile/metrology evidence with fictive sources."""
from copy import deepcopy
from types import MappingProxyType, SimpleNamespace

import pytest

from custom_components.solar_pilot.heatpump_budget import heatpump_power, sg_solar_budget
from custom_components.solar_pilot.sg_config import normalize_config, source_errors, validate_config
from test_runtime import build


def observed(**config):
    runtime, hass = build(power=True, settings={"pv_entity": "sensor.sun", "reserve_w": 0})
    runtime.panasonic.update_config(config)
    hass.states.set("sensor.sun", 6000, {"unit_of_measurement": "W"})
    return runtime, hass


def split(**config):
    runtime, hass = observed(power_supply1_entity="sensor.hp_supply_one",
                            power_supply2_entity="sensor.hp_supply_two",
                            split_power_confirmed=True, **config)
    hass.states.set("sensor.hp_supply_one", 1.4, {"unit_of_measurement": "kW"})
    hass.states.set("sensor.hp_supply_two", 0, {"unit_of_measurement": "W"})
    return runtime, hass


def test_new_fields_default_to_unconfirmed_and_old_single_config_survives_immutable_input():
    raw = MappingProxyType({"power_entity": "sensor.hp_total", "power_scope": "total",
                            "zone_entities": ("climate.room",)})
    first = normalize_config(raw)
    assert first["power_entity"] == "sensor.hp_total" and first["power_scope"] == "total"
    assert first["zone_entities"] == ["climate.room"]
    assert first["profile"] == "dhw_only"
    assert all(first[key] is False for key in ("profile_confirmed", "split_power_confirmed", "cooling_protection_confirmed"))
    assert normalize_config(MappingProxyType(first)) == first
    assert not validate_config(first)


@pytest.mark.parametrize("key", ["profile_confirmed", "split_power_confirmed", "cooling_protection_confirmed"])
def test_permission_types_are_not_coerced(key):
    assert key in validate_config({key: "true"})


def test_general_automatic_scope_requires_its_separate_local_confirmation():
    config = {"entity_id": "switch.sg", "enabled": True, "commissioning_confirmed": True,
              "watchdog_confirmed": True, "profile": "general"}
    assert validate_config(config) == {"profile_confirmed": "sg_profile_confirmation"}
    assert not validate_config({**config, "profile_confirmed": True})


def test_split_w_kw_sum_and_measured_zero_are_actual_and_do_not_credit_net_budget():
    runtime, hass = split()
    before = sg_solar_budget(runtime)
    reading, view = heatpump_power(runtime), runtime.panasonic.overview()
    assert reading["valid"] and reading["complete"] and reading["watts"] == 1400
    assert view["power_scope"] == "split" and view["power_complete"]
    assert view["power_supply1_w"] == 1400 and view["power_supply2_w"] == 0
    assert view["power_supply2_valid"]
    assert sg_solar_budget(runtime) == before
    assert hass.services.calls == []


@pytest.mark.parametrize("bad", ["missing", "stale", "restored", "estimated", "negative", "unit", "nan", "implausible", "future"])
def test_incomplete_split_keeps_known_part_without_fictitious_total(bad):
    runtime, hass = split()
    if bad == "missing":
        hass.states.data.pop("sensor.hp_supply_two")
    else:
        value = {"negative": -1, "nan": "nan", "implausible": 100001}.get(bad, 0)
        attrs = {"unit_of_measurement": "A" if bad == "unit" else "W"}
        if bad in ("restored", "estimated"):
            attrs[bad] = True
        hass.states.set("sensor.hp_supply_two", value, attrs, age={"stale": 121, "future": -6}.get(bad, 0))
    reading, view = heatpump_power(runtime), runtime.panasonic.overview()
    assert not reading["valid"] and reading["watts"] is None and not reading["complete"]
    assert view["power_supply1_w"] == 1400 and view["power_supply1_valid"]
    assert view["power_supply2_w"] is None and not view["power_supply2_valid"]
    assert view["power_w"] is None and view["power_kind"] == "unknown"
    assert hass.services.calls == []


def test_unconfirmed_split_never_claims_total_but_readings_are_visible():
    runtime, _hass = split()
    runtime.panasonic.settings["split_power_confirmed"] = False
    view = runtime.panasonic.overview()
    assert view["power_w"] is None and not view["power_complete"]
    assert view["power_supply1_w"] == 1400 and view["power_supply2_w"] == 0


def test_split_heartbeat_even_at_zero_proves_freshness_without_changing_value():
    runtime, hass = split()
    hass.states.set("sensor.hp_supply_two", 0, {"unit_of_measurement": "W"}, age=86400, reported_age=1)
    assert heatpump_power(runtime)["valid"]
    hass.states.set("sensor.hp_supply_two", 0, {"unit_of_measurement": "W"}, age=1, reported_age=121)
    assert not heatpump_power(runtime)["valid"]


@pytest.mark.parametrize("case", ["duplicate", "total_plus_parts", "reserved", "declared_template", "loaded_template", "transitive"])
def test_split_overlap_cannot_create_a_total_at_save_or_runtime(case):
    runtime, hass = split()
    config = runtime.panasonic.settings
    if case == "duplicate":
        config["power_supply2_entity"] = config["power_supply1_entity"]
    elif case == "total_plus_parts":
        config["power_entity"] = "sensor.total"
        hass.states.set("sensor.total", 1400, {"unit_of_measurement": "W"})
    elif case == "reserved":
        runtime.settings["grid_entity"] = config["power_supply1_entity"]
    elif case == "declared_template":
        hass.states.set(config["power_supply2_entity"], 0, {"unit_of_measurement": "W", "source_entity": config["power_supply1_entity"]})
    elif case == "loaded_template":
        entity = SimpleNamespace(_config={"state": SimpleNamespace(template="{{ states('sensor.hp_supply_one') }}")})
        hass.data["sensor"] = SimpleNamespace(get_entity=lambda eid: entity if eid == config["power_supply2_entity"] else None)
    else:
        hass.states.set(config["power_supply1_entity"], 1400, {"unit_of_measurement": "W", "source_entity": "sensor.intermediate"})
        hass.states.set("sensor.intermediate", 1400, {"source_entity": config["power_supply2_entity"]})
    assert not heatpump_power(runtime)["valid"]
    errors = source_errors(hass, config, site=runtime.settings, devices=runtime.configs.values())
    assert any(errors.get(key) in ("sg_meter_overlap", "dedicated_meter") for key in ("power_entity", "power_supply1_entity", "power_supply2_entity"))
    assert not hass.services.calls


@pytest.mark.parametrize("state", ["WATER", "PUMP", "IDLE", "unknown", "on"])
def test_programme_or_valve_state_and_meter_cannot_prove_compressor_or_received_sg(state):
    runtime, hass = observed(activity_entity="sensor.hp_direction", power_entity="sensor.hp_total", power_scope="total")
    hass.states.set("sensor.hp_direction", state)
    hass.states.set("sensor.hp_total", 2200, {"unit_of_measurement": "W"})
    view = runtime.panasonic.overview()
    assert view["compressor_running"] is None and view["compressor_frequency_hz"] is None
    assert view["sg_status"] == "unknown" and not view["sg_status_confirmed"]
    assert not view["sg_effect_confirmed"]


@pytest.mark.parametrize("value,running", [(0, False), (32, True)])
def test_actual_frequency_is_separate_from_sg_status_or_effect(value, running):
    runtime, hass = observed(compressor_frequency_entity="sensor.hp_frequency", sg_status_entity="binary_sensor.hp_received_sg")
    hass.states.set("sensor.hp_frequency", value, {"unit_of_measurement": "Hz"})
    hass.states.set("binary_sensor.hp_received_sg", "off")
    view = runtime.panasonic.overview()
    assert view["compressor_running"] is running and view["compressor_frequency_hz"] == value
    assert view["sg_status"] == "inactive" and view["sg_status_confirmed"]
    assert not view["sg_effect_confirmed"] and not hass.services.calls


@pytest.mark.parametrize("value,unit,age", [(32, "W", 0), (32, "Hz", 121), (-1, "Hz", 0), (201, "Hz", 0), ("nan", "Hz", 0)])
def test_invalid_frequency_remains_unknown(value, unit, age):
    runtime, hass = observed(compressor_frequency_entity="sensor.hp_frequency")
    hass.states.set("sensor.hp_frequency", value, {"unit_of_measurement": unit}, age=age)
    assert runtime.panasonic.overview()["compressor_running"] is None


@pytest.mark.parametrize("value", ["unknown", "unavailable", "1", "capacity 1", "WATER"])
def test_sg_numeric_capacity_and_programme_values_are_not_guessed(value):
    runtime, hass = observed(sg_status_entity="sensor.hp_received_sg")
    hass.states.set("sensor.hp_received_sg", value)
    assert not runtime.panasonic.overview()["sg_status_confirmed"]


def test_received_sg_is_confirmed_without_claiming_compressor_start_or_extra_consumption():
    runtime, hass = observed(sg_status_entity="binary_sensor.hp_received_sg", compressor_frequency_entity="sensor.hp_frequency")
    hass.states.set("binary_sensor.hp_received_sg", "on")
    hass.states.set("sensor.hp_frequency", 0, {"unit_of_measurement": "Hz"})
    view = runtime.panasonic.overview()
    assert view["sg_status"] == "active" and view["sg_status_confirmed"]
    assert view["compressor_running"] is False and not view["sg_effect_confirmed"]
    hass.states.set("binary_sensor.hp_received_sg", "on", age=121)
    assert not runtime.panasonic.overview()["sg_status_confirmed"]


def test_relay_derived_sensor_cannot_be_received_panasonic_sg_proof():
    runtime, hass = observed(entity_id="switch.sg", sg_status_entity="binary_sensor.relay_state")
    hass.states.set("switch.sg", "on")
    hass.states.set("binary_sensor.relay_state", "on", {"source_entity": "switch.sg"})
    assert source_errors(hass, runtime.panasonic.settings)["sg_status_entity"] == "sg_status_source"
    assert not runtime.panasonic.overview()["sg_status_confirmed"]


@pytest.mark.parametrize("mode,action,context,cooling_possible", [
    ("heat", "idle", "space_heating", False), ("auto", "heating", "space_heating", True),
    ("auto", "idle", "normal", True), ("cool", "cooling", "space_cooling", True),
    ("unknown", "heating", "heatpump_unknown", True),
])
def test_current_native_context_does_not_overstate_auto_cooling_safety(mode, action, context, cooling_possible):
    runtime, hass = observed(zone_entities=["climate.room"])
    hass.states.set("climate.room", mode, {"hvac_action": action})
    view = runtime.panasonic.overview()
    assert view["context"] == context and view["cooling_possible"] is cooling_possible
    if mode == "unknown" or mode == "auto" and action == "idle":
        assert not view["context_reliable"] and view["context_stamp"] is None
    else:
        assert view["context_reliable"] and view["context_stamp"]
    assert view["compressor_running"] is None


def test_actual_cooling_wins_over_tank_action_and_conflicting_zones_fail_conservative():
    runtime, hass = observed(zone_entities=["climate.room"], tank_target_entity="water_heater.tank")
    hass.states.set("water_heater.tank", "on", {"temperature": 50, "hvac_action": "heating", "temperature_unit": "°C"})
    hass.states.set("climate.room", "cool", {"hvac_action": "cooling"})
    view = runtime.panasonic.overview()
    assert view["context"] == "space_cooling" and view["cooling_possible"]
    runtime.panasonic.settings["zone_entities"].append("climate.other_room")
    hass.states.set("climate.other_room", "heat", {"hvac_action": "heating"})
    view = runtime.panasonic.overview()
    assert view["context"] == "heatpump_unknown" and view["cooling_possible"] and not view["context_reliable"]


def test_semantic_context_signature_excludes_samples_and_repeated_reads():
    runtime, hass = observed(zone_entities=["climate.room"], power_entity="sensor.hp_total",
                            power_scope="total", compressor_frequency_entity="sensor.hp_frequency")
    hass.states.set("climate.room", "heat", {"hvac_action": "heating", "temperature_unit": "°C", "current_temperature": 18})
    hass.states.set("sensor.hp_total", 1800, {"unit_of_measurement": "W"})
    hass.states.set("sensor.hp_frequency", 32, {"unit_of_measurement": "Hz"})
    first = runtime.panasonic.overview()
    before = deepcopy(runtime._snapshot())
    hass.states.set("climate.room", "heat", {"hvac_action": "heating", "temperature_unit": "°C", "current_temperature": 19})
    hass.states.set("sensor.hp_total", 2000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.hp_frequency", 38, {"unit_of_measurement": "Hz"})
    second = runtime.panasonic.overview()
    assert second["context_signature"] == first["context_signature"]
    assert second["context_stamp"] > first["context_stamp"]
    assert runtime._snapshot() == before and not hass.services.calls
    hass.states.set("climate.room", "heat", {"hvac_action": "heating"}, age=121)
    stale = runtime.panasonic.overview()
    assert not stale["context_reliable"] and stale["context_signature"] is None and stale["cooling_possible"]


@pytest.mark.parametrize("second_mode,second_program,fresh", [
    ("auto", "unknown", False), ("auto", "unknown", True),
    ("auto", "cooling", True), ("unknown", "heating", True),
])
def test_one_native_heating_zone_never_certifies_other_ambiguous_zone_cooling_safety(second_mode, second_program, fresh):
    runtime, hass = observed(zone_entities=["climate.room", "climate.other_room"])
    hass.states.set("climate.room", "auto", {"hvac_action": "idle"})
    hass.states.set("climate.other_room", second_mode, {"hvac_action": "idle"})
    stamp = hass.states.get("climate.room").last_reported.timestamp()
    rows = {"climate.room": {"program": "heating", "raw_mode": "AUTO_HEAT", "fresh": True, "observed_at": stamp},
            "climate.other_room": {"program": second_program, "raw_mode": "AUTO", "fresh": fresh, "observed_at": stamp}}
    runtime.panasonic.native_program = SimpleNamespace(read=rows.get)
    assert runtime.panasonic.overview()["cooling_possible"] is True


def test_every_zone_explicitly_disambiguated_native_auto_heating_can_exclude_cooling():
    runtime, hass = observed(zone_entities=["climate.room", "climate.other_room"])
    for eid in runtime.panasonic.settings["zone_entities"]:
        hass.states.set(eid, "auto", {"hvac_action": "idle"})
    stamp = hass.states.get("climate.room").last_reported.timestamp()
    runtime.panasonic.native_program = SimpleNamespace(read=lambda eid: {
        "entity_id": eid, "program": "heating", "raw_mode": "AUTO_HEAT", "fresh": True, "observed_at": stamp})
    view = runtime.panasonic.overview()
    assert view["context"] == "space_heating" and view["context_reliable"]
    assert view["cooling_possible"] is False and view["compressor_running"] is None


def test_actual_zero_power_exposes_real_report_stamp_while_incomplete_or_stale_total_has_none():
    runtime, hass = split()
    hass.states.set("sensor.hp_supply_one", 0, {"unit_of_measurement": "W"}, reported_age=1)
    hass.states.set("sensor.hp_supply_two", 0, {"unit_of_measurement": "W"}, reported_age=2)
    view = runtime.panasonic.overview()
    assert view["power_w"] == 0 and view["power_kind"] == "measured"
    assert view["power_stamp"] == hass.states.get("sensor.hp_supply_two").last_reported.timestamp()
    hass.states.set("sensor.hp_supply_two", 0, {"unit_of_measurement": "W"}, reported_age=121)
    stale = runtime.panasonic.overview()
    assert stale["power_w"] is None and stale["power_stamp"] is None
    assert stale["power_supply1_w"] == 0 and stale["power_supply1_valid"]
    hass.states.data.pop("sensor.hp_supply_two")
    incomplete = runtime.panasonic.overview()
    assert incomplete["power_w"] is None and incomplete["power_stamp"] is None
    assert incomplete["power_supply1_w"] == 0


def test_single_actual_zero_power_stamp_is_source_report_not_overview_read_time():
    runtime, hass = observed(power_entity="sensor.hp_total", power_scope="total")
    hass.states.set("sensor.hp_total", 0, {"unit_of_measurement": "W"}, reported_age=2)
    first = runtime.panasonic.overview()
    second = runtime.panasonic.overview()
    assert first["power_w"] == 0 and first["power_stamp"]
    assert second["power_stamp"] == first["power_stamp"]
    hass.states.set("sensor.hp_total", 0, {"unit_of_measurement": "W"}, reported_age=121)
    assert runtime.panasonic.overview()["power_stamp"] is None



def test_unknown_auto_programme_gap_cannot_become_a_reliable_native_idle_episode():
    runtime, hass = observed(zone_entities=["climate.room"])
    hass.states.set("climate.room", "auto", {"hvac_action": "idle"})
    stamp = hass.states.get("climate.room").last_reported.timestamp()
    evidence = {"entity_id": "climate.room", "program": "heating", "raw_mode": "AUTO_HEAT", "fresh": True, "observed_at": stamp}
    runtime.panasonic.native_program = SimpleNamespace(read=lambda _eid: evidence)
    active = runtime.panasonic.overview()
    assert active["context"] == "space_heating" and active["context_reliable"]
    evidence.update(program="unknown", fresh=False)
    gap = runtime.panasonic.overview()
    assert gap["context"] == "normal" and not gap["context_reliable"]
    assert gap["context_stamp"] is None and gap["context_signature"] is None
    evidence.update(program="heating", fresh=True)
    recovered = runtime.panasonic.overview()
    assert recovered["context_reliable"] and recovered["context_signature"] == active["context_signature"]


def test_explicit_off_is_idle_evidence_while_unavailable_is_not():
    runtime, hass = observed(zone_entities=["climate.room"])
    hass.states.set("climate.room", "off", {"hvac_action": "idle"})
    assert runtime.panasonic.overview()["context_reliable"]
    hass.states.set("climate.room", "unavailable", {"hvac_action": "idle"})
    unavailable = runtime.panasonic.overview()
    assert not unavailable["context_reliable"] and unavailable["context_signature"] is None


@pytest.mark.asyncio
async def test_general_hold_with_actual_monitor_survives_native_auto_poll_gap_and_same_recovery(monkeypatch):
    from datetime import datetime, timezone
    from test_sg_controller62 import fixture, tick
    from custom_components.solar_pilot import panasonic_monitor

    manager, adapter, clock, manager_runtime = fixture(
        profile="general", profile_confirmed=True, cooling_protection_confirmed=True)
    meter_runtime, hass = observed(zone_entities=["climate.room"])
    monitor = meter_runtime.panasonic
    manager_runtime.panasonic = monitor
    monkeypatch.setattr(panasonic_monitor.time, "time", clock)
    evidence = {"entity_id": "climate.room", "program": "heating", "raw_mode": "AUTO_HEAT", "fresh": True, "observed_at": clock()}
    monitor.native_program = SimpleNamespace(read=lambda _eid: evidence)

    async def reported(**kwargs):
        hass.states.set("climate.room", "auto", {"hvac_action": "idle"})
        obj = hass.states.get("climate.room")
        obj.last_reported = datetime.fromtimestamp(clock(), timezone.utc)
        evidence["observed_at"] = clock()
        return await tick(manager, native_observation=monitor.overview(), solar_stamp=clock(), **kwargs)

    await reported()
    clock.advance(120)
    await reported()
    assert adapter.calls == [("on", 300)]
    clock.advance(60)
    await reported(physical_evidence={"verified": True, "no_uptake": True})
    assert manager.completion_hold and adapter.calls[-1] == ("off", None)
    clock.advance(900)
    evidence.update(program="unknown", fresh=False)
    await reported()
    clock.advance(300)
    await reported()
    assert manager._general_reference["native_reset_stamp"] is None
    evidence.update(program="heating", fresh=True)
    await reported()
    clock.advance(300)
    await reported()
    assert manager.completion_hold and adapter.calls == [("on", 300), ("off", None)]
