"""Independent SG budget/priority/monitor integration checks with public doubles.

These tests exercise actual P1 calculations and protected choices. They do not
establish Panasonic SG effectiveness or a physical Shelly failsafe test.
"""
from copy import deepcopy
from dataclasses import replace
from datetime import datetime, timezone
from types import SimpleNamespace
import time

import pytest

from custom_components.solar_pilot.engine import Action
from custom_components.solar_pilot.heatpump_budget import heatpump_power, sg_solar_budget
from custom_components.solar_pilot.sg_config import normalize_config
from test_runtime import build


def configured(*, kind="switch", export=4500, reserve=150, device=None):
    r, h = build(kind=kind, power=True,
                 settings={"pv_entity": "sensor.public_pv", "reserve_w": reserve,
                           "max_import_w": 500, "settle_s": 0, "filter_s": 0},
                 device={"nominal_w": 1000, "min_on_s": 60, **(device or {})})
    c = normalize_config({"entity_id": "switch.public_sg", "enabled": True,
                          "commissioning_confirmed": True, "watchdog_confirmed": True,
                          "power_entity": "sensor.public_hp", "power_scope": "total",
                          "start_delay_s": 30, "threshold_w": 3000,
                          "expected_power_w": 3200})
    r.entry.options["sg_boost"] = deepcopy(c)
    r.sg_boost.update_config(c)
    r.panasonic.update_config(c)
    r.entry.options["priority_board"] = {
        "schema": 2, "order": ["wallbox", "dhw_extra", "device:a"],
        "wallbox_power": {"device:a": False}, "dhw_extra_priority_migration": 57,
    }
    r.mode = "solar"
    h.states.set("sensor.grid", -export, {"unit_of_measurement": "W"})
    h.states.set("sensor.public_pv", 8000, {"unit_of_measurement": "W"})
    h.states.set("sensor.public_hp", 3200, {"unit_of_measurement": "W"})
    h.states.set("sensor.load", 1000, {"unit_of_measurement": "W"})
    h.states.set("switch.load", "on")
    h.states.set("binary_sensor.running", "on")
    st = r.states["a"]
    st.enabled = st.available = st.demand = st.interlock = st.cycle_armed = True
    st.on = st.owned = True
    st.target_w = st.measured_w = 1000
    st.last_on = 0
    st.last_off = 0
    r.device_modes["a"] = "auto"
    r.filtered = None
    return r, h


@pytest.mark.parametrize("scope", ["total", "supply1", "supply2", "unconfirmed"])
@pytest.mark.parametrize("value,unit", [(3200, "W"), (3.2, "kW")])
def test_one_hp_reading_is_normalized_but_never_added_back_to_actual_p1(scope, value, unit):
    r, h = configured(export=1000)
    r.panasonic.settings["power_scope"] = scope
    h.states.set("sensor.public_hp", value, {"unit_of_measurement": unit})
    reading = heatpump_power(r)
    assert reading["valid"] and reading["watts"] == 3200 and reading["meter_scope"] == scope
    # Native comfort draw is already part of net P1; total vs partial scope
    # neither gives SG owned watts nor splits tank/climate into two appliances.
    assert r._dishwasher_comfort_context() == (0.0, "")
    assert sg_solar_budget(r)["available_w"] == 850
    r.sg_boost.owned = r.sg_boost.desired_on = True
    r.sg_boost.relay_on = r.sg_boost.relay_confirmed = True
    r.sg_boost._lease_deadline = time.monotonic() + 300
    assert sg_solar_budget(r)["available_w"] == 850


@pytest.mark.parametrize("attrs,value,age", [
    ({"unit_of_measurement": "kWh"}, 3.2, 0),
    ({"unit_of_measurement": "A"}, 12, 0),
    ({}, 3200, 0),
    ({"unit_of_measurement": "W", "estimated": True}, 3200, 0),
    ({"unit_of_measurement": "W", "restored": True}, 3200, 0),
    ({"unit_of_measurement": "W"}, "unavailable", 0),
    ({"unit_of_measurement": "W"}, float("nan"), 0),
    ({"unit_of_measurement": "W"}, -1, 0),
    ({"unit_of_measurement": "W"}, 3200, 121),
])
def test_unusable_hp_measurement_stays_unknown_without_solar_credit(attrs, value, age):
    r, h = configured(export=1000)
    h.states.set("sensor.public_hp", value, attrs, age=age)
    reading = heatpump_power(r)
    assert not reading["valid"] and reading["watts"] is None
    assert sg_solar_budget(r)["available_w"] == 850


def test_shared_grid_or_ordinary_meter_cannot_become_dedicated_hp_reading():
    r, _h = configured(export=1000)
    for meter in ("sensor.grid", "sensor.load", "sensor.public_pv"):
        r.panasonic.settings["power_entity"] = meter
        assert not heatpump_power(r)["valid"]
    assert sg_solar_budget(r)["available_w"] == 850


@pytest.mark.parametrize("entity", ["sensor.grid", "sensor.public_pv"])
def test_stale_actual_net_or_pv_invalidates_sg_even_when_forecast_is_large(entity):
    r, h = configured()
    obj = h.states.get(entity)
    h.states.set(entity, obj.state, obj.attributes, age=121)
    r.pv_w = 20000  # This remembered/forecast-like value is not a fresh source.
    assert not sg_solar_budget(r)["valid"]


@pytest.mark.parametrize("entity", ["sensor.grid", "sensor.public_pv", "sensor.public_hp"])
@pytest.mark.parametrize("bad_stamp", ["os_error", "empty", "zero"])
def test_invalid_reported_timestamp_cannot_refresh_power_from_updated_fallback(entity, bad_stamp):
    r, h = configured()
    obj = h.states.get(entity)
    if bad_stamp == "os_error":
        def invalid_timestamp():
            raise OSError("public fixture invalid clock")
        obj.last_reported = SimpleNamespace(timestamp=invalid_timestamp)
    else:
        obj.last_reported = "" if bad_stamp == "empty" else 0
    # Only an absent timestamp may use last_updated. A malformed report must
    # not become fresh merely because this separate timestamp is usable.
    assert r._power(entity)[0] is None
    if entity == "sensor.public_hp":
        assert not heatpump_power(r)["valid"]
    else:
        assert not sg_solar_budget(r)["valid"]
        assert r.sg_dispatch_allowed() is False


def test_sg_budget_subtracts_battery_discharge_and_one_house_reserve():
    r, h = configured(export=4500)
    r.settings["battery_power_entity"] = "sensor.public_battery"
    h.states.set("sensor.public_battery", 1000, {"unit_of_measurement": "W"})
    assert sg_solar_budget(r)["available_w"] == 3350
    r.filtered = -4000
    assert sg_solar_budget(r)["available_w"] == 2850
    h.states.set("sensor.public_pv", 2500, {"unit_of_measurement": "W"})
    assert sg_solar_budget(r)["available_w"] == 2350


def test_phase_gate_requires_one_full_expected_hp_envelope_without_2500w_shortcut():
    r, _h = configured(export=6000)
    r.phase_settings.update(enabled=True, control_starts=True)
    r.phase = replace(r.phase, enabled=True, valid=True, block_increase=False, headroom_w=2500)
    assert r.heat_pump_increase_allowed()[0] is False
    r.phase = replace(r.phase, headroom_w=3199)
    assert r.heat_pump_increase_allowed()[0] is False
    r.phase = replace(r.phase, headroom_w=3200)
    assert r.heat_pump_increase_allowed()[0] is True


def test_net_gate_does_not_subtract_already_measured_hp_draw_from_future_envelope():
    r, h = configured(export=2000)
    # A partial meter cannot prove which native consumption will be displaced.
    r.panasonic.settings["power_scope"] = "supply1"
    h.states.set("sensor.public_hp", 3200, {"unit_of_measurement": "W"})
    assert r.heat_pump_increase_allowed()[0] is False  # -2000+3200 exceeds 500.
    h.states.set("sensor.grid", -2700, {"unit_of_measurement": "W"})
    assert r.heat_pump_increase_allowed()[0] is True


def test_final_sg_dispatch_rechecks_other_future_commitments_on_phase_headroom():
    r, h = configured(export=6000)
    r.states["a"].target_w = 1500  # 500 W committed but not yet present in P1.
    r.phase_settings.update(enabled=True, control_starts=True, limit_w=3500,
                            phase_1_entity="sensor.public_phase1", phase_2_entity="sensor.public_phase2",
                            phase_3_entity="sensor.public_phase3")
    for eid in ("sensor.public_phase1", "sensor.public_phase2", "sensor.public_phase3"):
        h.states.set(eid, 0, {"unit_of_measurement": "W"})
    r.phase = replace(r.phase, enabled=True, valid=True, block_increase=False, headroom_w=3200)
    assert r.heat_pump_increase_allowed()[0] is False
    assert r.sg_dispatch_allowed() is False
    r.phase_settings["limit_w"] = 4000
    r.phase = replace(r.phase, headroom_w=3700)
    assert r.sg_dispatch_allowed() is True


@pytest.mark.asyncio
async def test_priority_migration_preserves_saved_order_and_permissions_without_beta57_reorder():
    r, _h = configured()
    saved = deepcopy(r.entry.options["priority_board"])
    assert not await r.priority_board.migrate_beta36()
    assert r.entry.options["priority_board"] == saved
    assert r.priority_board.order() == saved["order"]
    assert r.priority_board.permissions() == saved["wallbox_power"]


@pytest.mark.parametrize("field,value", [
    ("owned", False), ("on", False), ("available", False), ("enabled", False),
    ("fault", "public source error"), ("manual_until", 200), ("manual_forced", True),
    ("boost_until", 200), ("deadline_force", True), ("deadline_urgent", True),
    ("planner_grid_force", True), ("last_on", 90),
])
def test_sg_cannot_reclaim_protected_or_manual_lower_load(field, value):
    r, _h = configured(export=2200)
    setattr(r.states["a"], field, value)
    assert r.priority_board._extra_candidates(100) == []


def test_sg_never_reclaims_a_running_dishwasher_even_if_stored_rank_is_lower():
    r, _h = configured(kind="dishwasher", export=2200)
    assert r.priority_board._extra_candidates(100) == []


def test_sg_never_reclaims_wallbox_or_its_shared_meter():
    r, _h = configured(export=2200)
    r.wallbox_settings["enabled"] = True
    r.wallbox_settings["power_entity"] = "sensor.load"
    assert r.priority_board._extra_candidates(100) == []


def test_higher_fitting_load_gets_actual_solar_before_optional_sg():
    r, _h = configured()
    r.entry.options["priority_board"]["order"] = ["device:a", "wallbox", "dhw_extra"]
    r.states["a"].on = r.states["a"].owned = False
    assert r.priority_board.sg_priority_allowed(100) is False
    r.states["a"].demand = False
    assert r.priority_board.sg_priority_allowed(100) is True


def test_due_dishwasher_keeps_priority_even_when_it_needs_other_energy():
    r, _h = configured(kind="dishwasher")
    r.states["a"].on = False
    r.dishwasher_app.due = lambda cfg, wall: True
    assert r.priority_board.sg_priority_allowed(100) is False


def test_sg_off_proposal_is_not_available_watts_before_fresh_actual_p1():
    r, h = configured(export=2200)
    now = 100.0
    before = sg_solar_budget(r)["available_w"]
    assert before == 2050
    assert r.priority_board.extra_reclaim_action(now, datetime.now(timezone.utc)) is None
    h.states.set("sensor.grid", -2200, {"unit_of_measurement": "W"})
    h.states.set("sensor.public_pv", 8000, {"unit_of_measurement": "W"})
    action = r.priority_board.extra_reclaim_action(now + 30, datetime.now(timezone.utc))
    assert action == Action("a", 0.0, "Zonnestroom vrijmaken voor SG-zonneboost: Testtoestel veilig pauzeren")
    assert r.priority_board.extra_reclaim["prospective_freed_w"] == 1000
    r.priority_board.extra_reclaim_sent(action, now + 30)
    r.states["a"].target_w = 0  # Persisted OFF intent is not physical feedback.
    assert sg_solar_budget(r)["available_w"] == before
    r.states["a"].on = False  # Even relay feedback alone cannot credit solar.
    assert sg_solar_budget(r)["available_w"] == before
    h.states.set("sensor.grid", -3200, {"unit_of_measurement": "W"})
    assert sg_solar_budget(r)["available_w"] == 3050


def mature_reclaim(runtime, hass):
    """Supply the two independent reports required for a stable proposal."""
    runtime.priority_board.extra_reclaim_action(100, datetime.now(timezone.utc))
    for eid in ("sensor.grid", "sensor.public_pv"):
        obj = hass.states.get(eid)
        hass.states.set(eid, obj.state, obj.attributes)
    return runtime.priority_board.extra_reclaim_action(130, datetime.now(timezone.utc))


@pytest.mark.parametrize("blocked", ["manual_hold", "completion_hold", "missing_binding",
                                      "invalid_binding", "invalid_lease", "battery_pending", "source_fault"])
def test_sg_unusable_or_held_request_never_pauzes_lower_loads(blocked):
    r, h = configured(export=2200)
    if blocked in ("manual_hold", "completion_hold"):
        setattr(r.sg_boost, blocked, True)
    elif blocked == "missing_binding":
        r.sg_boost.settings["entity_id"] = ""
    elif blocked == "invalid_binding":
        r.sg_boost.settings["entity_id"] = "light.public_sg"
    elif blocked == "invalid_lease":
        r.sg_boost.settings["lease_s"] = 1
    elif blocked == "battery_pending":
        r.battery_fleet.state.pending = {"id": "public_battery", "mode": "idle"}
    else:
        r.sg_boost.fault = "Publieke SG-bron niet beschikbaar"
        r.sg_boost.fault_code = "source_invalid"
    assert mature_reclaim(r, h) is None
    assert r.priority_board.extra_reclaim["state"] == "idle"
    assert not h.services.calls


def test_lower_pause_cannot_create_more_solar_than_actual_pv_production():
    r, h = configured(export=2200)
    h.states.set("sensor.public_pv", 2500, {"unit_of_measurement": "W"})
    assert r.priority_board._extra_candidates(100) == [("a", 1000)]
    assert sg_solar_budget(r)["available_w"] + 1000 >= 3000
    assert mature_reclaim(r, h) is None
    assert r.priority_board.extra_reclaim["state"] == "idle"
    assert not h.services.calls


def test_lower_pause_rejected_if_threshold_fits_but_full_future_hp_envelope_does_not():
    r, h = configured(export=2200)
    r.sg_boost.settings["expected_power_w"] = 5200
    assert sg_solar_budget(r)["available_w"] + 1000 == 3050
    assert mature_reclaim(r, h) is None
    assert r.priority_board.extra_reclaim["state"] == "idle"
    assert not h.services.calls


@pytest.mark.parametrize("case", ["invalid", "allowed_grid", "fallback_target"])
def test_lower_pause_requires_actual_quarter_room_for_full_hp_envelope(case):
    r, h = configured(export=2200)
    r.sg_boost.settings["expected_power_w"] = 3600  # Future import 400 W after lower OFF.
    r.capacity_settings.update(enabled=True, margin_w=100)
    r.capacity = replace(r.capacity, valid=case != "invalid", allowed_grid_w=300,
                         effective_target_w=400)
    if case == "fallback_target":
        r.capacity = replace(r.capacity, allowed_grid_w=None)
    assert mature_reclaim(r, h) is None
    assert r.priority_board.extra_reclaim["state"] == "idle"
    assert not h.services.calls


def test_lower_pause_never_claims_future_off_watts_as_phase_headroom():
    r, h = configured(export=2200)
    r.states["a"].target_w = 1500  # Another 500 W is already committed.
    r.phase_settings.update(enabled=True, control_starts=True)
    r.phase = replace(r.phase, enabled=True, valid=True, block_increase=False,
                      release_flexible=False, headroom_w=3200)
    # The 1000 W candidate must not add fictional headroom before actual OFF.
    assert mature_reclaim(r, h) is None
    assert r.priority_board.extra_reclaim["state"] == "idle"
    assert not h.services.calls


def test_lower_starts_wait_for_live_sg_request_even_before_panasonic_draws():
    r, _h = configured()
    r.states["a"].on = False
    r.sg_boost.owned = r.sg_boost.desired_on = True
    r.sg_boost.relay_on = r.sg_boost.relay_confirmed = True
    r.sg_boost._lease_deadline = time.monotonic() + 300
    assert "a" in r.priority_board.extra_start_blocks(100)
    # Manual and deadline rights remain authoritative while lower Auto waits.
    r.states["a"].manual_forced = True
    assert "a" not in r.priority_board.extra_start_blocks(100)


def test_uncertain_sg_contact_keeps_one_future_envelope_until_actual_off_proof():
    r, _h = configured()
    r.sg_boost._possibly_owned = True
    r.sg_boost.relay_on = None
    r.sg_boost.relay_confirmed = False
    assert r.sg_unconfirmed_reserve_w == 3200
    r.sg_boost.desired_on = False  # Requested OFF is not observed normal mode.
    r.sg_boost._off_attempted = True
    assert r.sg_unconfirmed_reserve_w == 3200
    r.sg_boost._possibly_owned = False
    r.sg_boost.relay_on = False
    r.sg_boost.relay_confirmed = True
    assert r.sg_unconfirmed_reserve_w == 0


@pytest.mark.asyncio
@pytest.mark.parametrize("export,allowed", [(2500, False), (5000, True)])
async def test_unreachable_own_sg_allows_healthy_loads_only_with_real_remaining_room(export, allowed):
    r, h = configured(export=export)
    st = r.states["a"]
    st.on = st.owned = False
    st.target_w = st.measured_w = 0
    h.states.set("switch.load", "off")
    h.states.set("sensor.load", 0, {"unit_of_measurement": "W"})
    r.sg_boost._started = True
    r.sg_boost._possibly_owned = True
    r.sg_boost.relay_on = None
    r.sg_boost.relay_confirmed = False
    r.sg_boost._off_attempted = True  # Already attempted once; avoid a retry storm.
    await r.tick()
    assert r.sg_unconfirmed_reserve_w == 3200
    assert [(domain, service) for domain, service, _data in h.services.calls
            if domain != "persistent_notification"] == ([("switch", "turn_on")] if allowed else [])
    assert bool(r.pending) is allowed
    if allowed:
        assert r.pending["id"] == "a"


def test_fresh_monitor_reads_do_not_change_native_device_or_sg_settings():
    r, h = configured()
    r.panasonic.settings.update(tank_temperature_entity="sensor.public_tank",
                                tank_target_entity="number.public_tank_target",
                                zone_entities=["climate.public_room"])
    h.states.set("sensor.public_tank", 49, {"unit_of_measurement": "°C"})
    h.states.set("number.public_tank_target", 50, {"unit_of_measurement": "°C"})
    h.states.set("climate.public_room", "auto", {"current_temperature": 22, "temperature": 21,
                                                "temperature_unit": "°C", "hvac_action": "idle"})
    before = deepcopy(r.sg_boost.settings)
    view = r.panasonic.overview()
    assert view["temperature_c"] == 49 and view["target_c"] == 50
    assert view["zones"][0]["temperature_c"] == 22 and view["zones"][0]["read_only"]
    assert view["read_only"] and view["context"] == "normal"
    assert h.services.calls == [] and r.sg_boost.settings == before
    h.states.set("sensor.public_tank", 49, {"unit_of_measurement": "°C"}, age=121)
    assert r.panasonic.overview()["temperature_c"] is None


def test_temperature_units_are_converted_to_celsius_and_missing_unit_is_unknown():
    r, h = configured()
    r.panasonic.settings.update(tank_temperature_entity="sensor.public_tank",
                                tank_target_entity="number.public_tank_target",
                                zone_entities=["climate.public_room"])
    h.states.set("sensor.public_tank", 122, {"unit_of_measurement": "°F"})
    h.states.set("number.public_tank_target", 140, {"unit_of_measurement": "°F"})
    h.states.set("climate.public_room", "auto", {"current_temperature": 71.6, "temperature": 69.8,
                                                "temperature_unit": "°F", "hvac_action": "idle"})
    view = r.panasonic.overview()
    assert view["temperature_c"] == pytest.approx(50)
    assert view["target_c"] == pytest.approx(60)
    assert view["zones"][0]["temperature_c"] == pytest.approx(22)
    assert view["zones"][0]["target_c"] == pytest.approx(21)
    h.states.set("sensor.public_tank", 49)
    h.states.set("number.public_tank_target", 50, {"unit_of_measurement": "W"})
    view = r.panasonic.overview()
    assert view["temperature_c"] is None and view["target_c"] is None
