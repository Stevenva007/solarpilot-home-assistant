"""Runtime tests against explicit HA doubles, not Home Assistant Core."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import time
import pytest
from custom_components.solar_pilot.runtime import SolarRuntime
from custom_components.solar_pilot.engine import Action, Plan
from homeassistant.exceptions import HomeAssistantError


class States:
    def __init__(self):
        self.data = {}
    def get(self, id):
        return self.data.get(id)
    def set(self, id, state, attrs=None, age=0, reported_age=None):
        stamp = datetime.now(timezone.utc) - timedelta(seconds=age)
        reported = datetime.now(timezone.utc) - timedelta(seconds=reported_age) if reported_age is not None else stamp
        self.data[id] = SimpleNamespace(state=str(state), attributes=attrs or {}, last_updated=stamp, last_reported=reported)


class Services:
    def __init__(self, states):
        self.states = states
        self.calls = []
        self.respond = True
        self.fail = False
        self.on_call = None
    def has_service(self, domain, action):
        return True
    async def async_call(self, domain, action, data, blocking=False):
        self.calls.append((domain, action, data))
        if self.on_call:
            self.on_call(domain, action, data)
        if self.fail:
            raise HomeAssistantError("offline")
        if not self.respond or domain in ("script", "persistent_notification"):
            return
        entity = data["entity_id"]
        previous = self.states.get(entity)
        attrs = previous.attributes if previous else {}
        self.states.set(entity, data["value"] if action == "set_value" else "on" if action == "turn_on" else "off", attrs)


def build(kind="switch", power=False, settings=None, device=None):
    states = States()
    states.set("sensor.grid", -2500, {"unit_of_measurement": "W"})
    states.set("switch.load", "off")
    states.set("number.amps", 6, {"min": 6, "max": 16, "step": 1, "unit_of_measurement": "A"})
    states.set("sensor.load", 0, {"unit_of_measurement": "W"})
    states.set("binary_sensor.running", "off")
    states.set("input_boolean.ready", "on")
    config = {"id": "a", "name": "Testtoestel", "kind": kind, "control_entity": "switch.load",
              "start_script": "script.start", "stop_script": "script.stop", "active_entity": "binary_sensor.running",
              "number_entity": "number.amps", "start_delay_s": 0, "stop_delay_s": 0,
              "min_on_s": 0, "min_off_s": 0, "start_margin_w": 0, **(device or {})}
    if power or kind == "number":
        config["power_entity"] = "sensor.load"
    hass = SimpleNamespace(states=states, services=Services(states))
    entry = SimpleNamespace(entry_id="test", data={"grid_entity": "sensor.grid", "settle_s": 5, "reserve_w": 0, **(settings or {})},
                            options={"devices": [config]})
    runtime = SolarRuntime(hass, entry)
    return runtime, hass


@pytest.mark.asyncio
async def test_default_observe_never_calls_a_load():
    r, h = build()
    r.device_modes["a"] = "auto"
    await r.tick()
    assert h.services.calls == []
    assert r.result.action is not None


@pytest.mark.asyncio
async def test_new_device_defaults_to_disabled():
    r, h = build()
    r.mode = "solar"
    await r.tick()
    assert h.services.calls == []
    assert r.states["a"].enabled is False


@pytest.mark.asyncio
async def test_intent_saved_before_physical_command():
    r, h = build()
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    def check(domain, action, data):
        assert "a" in r.store.data["leases"]
    h.services.on_call = check
    await r.tick()
    assert r.pending and h.states.get("switch.load").state == "on"
    await r.tick()
    assert r.pending is None and r.states["a"].owned


@pytest.mark.asyncio
async def test_number_set_before_enable():
    r, h = build(kind="number")
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    await r.tick()
    assert [x[1] for x in h.services.calls] == ["set_value", "turn_on"]
    assert 6 <= h.services.calls[0][2]["value"] <= 16


@pytest.mark.asyncio
async def test_stop_number_does_not_write_zero_amps():
    r, h = build(kind="number")
    h.states.set("switch.load", "on")
    r.states["a"].owned = True
    r.states["a"].on = True
    r.states["a"].target_w = 1380
    await r._send(Action("a", 0, "Pauze"), time.monotonic())
    assert [x[1] for x in h.services.calls] == ["turn_off"]


@pytest.mark.asyncio
async def test_missing_feedback_latches_fault_no_blind_retry():
    r, h = build()
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    h.services.respond = False
    await r.tick()
    assert r.pending is not None
    r.pending["issued"] -= 100
    await r.tick()
    assert r.pending is None and "a" in r.faults
    calls = len(h.services.calls)
    await r.tick()
    assert len(h.services.calls) == calls


@pytest.mark.asyncio
async def test_service_failure_preserves_ambiguous_lease():
    r, h = build()
    h.services.fail = True
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    await r.tick()
    assert r.states["a"].owned and r.store.data["leases"]["a"]
    assert "a" in r.faults


@pytest.mark.asyncio
async def test_external_start_never_owned():
    r, h = build()
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    h.states.set("switch.load", "on")
    await r.tick()
    assert not r.states["a"].owned and h.services.calls == []


@pytest.mark.asyncio
async def test_external_stop_respected_and_lease_released():
    r, h = build()
    r.states["a"].owned = True
    r.states["a"].on = True
    r.states["a"].target_w = 1000
    await r.tick()
    assert not r.states["a"].owned
    assert r.states["a"].manual_until > time.monotonic()
    assert not r.store.data["leases"]


@pytest.mark.asyncio
async def test_number_changed_externally_is_not_fought():
    r, h = build(kind="number")
    h.states.set("switch.load", "on")
    h.states.set("number.amps", 10, {"min": 6, "max": 16, "step": 1})
    r.states["a"].owned = True
    r.states["a"].on = True
    r.states["a"].target_w = 1380
    await r.tick()
    assert not r.states["a"].owned and h.services.calls == []


@pytest.mark.asyncio
async def test_stale_meter_does_not_start():
    r, h = build()
    h.states.set("sensor.grid", -5000, {"unit_of_measurement": "W"}, age=500)
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    await r.tick()
    assert r.grid_w is None and h.services.calls == [] and r.problem


@pytest.mark.asyncio
async def test_last_reported_not_last_changed_is_freshness_source():
    r, h = build()
    h.states.set("sensor.grid", -5000, {"unit_of_measurement": "W"}, age=500, reported_age=1)
    await r.tick()
    assert r.grid_w == -5000


@pytest.mark.asyncio
async def test_kwh_never_interpreted_as_power():
    r, h = build()
    h.states.set("sensor.grid", 2000, {"unit_of_measurement": "kWh"})
    await r.tick()
    assert r.grid_w is None


@pytest.mark.asyncio
async def test_kw_converted_to_watts():
    r, h = build()
    h.states.set("sensor.grid", -2, {"unit_of_measurement": "kW"})
    await r.tick()
    assert r.grid_w == -2000


@pytest.mark.asyncio
async def test_nonfinite_power_rejected():
    r, h = build()
    h.states.set("sensor.grid", "nan", {"unit_of_measurement": "W"})
    await r.tick()
    assert r.grid_w is None


@pytest.mark.asyncio
async def test_separate_meter_conversion_and_sign():
    r, h = build(settings={"grid_sign": "separate", "export_entity": "sensor.export"})
    h.states.set("sensor.grid", 0, {"unit_of_measurement": "kW"})
    h.states.set("sensor.export", 2, {"unit_of_measurement": "kW"})
    await r.tick()
    assert r.grid_w == -2000


@pytest.mark.asyncio
async def test_export_positive_sign_converted():
    r, h = build(settings={"grid_sign": "export_positive"})
    h.states.set("sensor.grid", 2000, {"unit_of_measurement": "W"})
    await r.tick()
    assert r.grid_w == -2000


@pytest.mark.asyncio
async def test_old_separate_export_meter_blocks():
    r, h = build(settings={"grid_sign": "separate", "export_entity": "sensor.export"})
    h.states.set("sensor.export", 5000, {"unit_of_measurement": "W"}, age=500)
    await r.tick()
    assert r.grid_w is None


@pytest.mark.asyncio
async def test_restart_reconciles_known_on_device_and_resumes_previous_solar_mode_without_replay():
    r, h = build()
    h.states.set("switch.load", "on")
    r.store.data = {"mode": "solar", "leases": {"a": {"watts": 1000, "name": "Testtoestel"}}, "device_modes": {"a": "auto"}}
    await r.start()
    assert not r.recovery and r.mode == "solar"
    assert r.states["a"].owned and r.states["a"].on and r.states["a"].target_w == 1000
    assert not [call for call in h.services.calls if call[0] == "switch"]


@pytest.mark.asyncio
async def test_restart_reconciles_known_off_device_and_normal_rules_may_continue():
    r, h = build()
    h.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    h.states.set("switch.load", "off")
    r.store.data = {"mode": "solar", "leases": {"a": {"watts": 1000, "name": "Testtoestel"}}, "device_modes": {"a": "auto"}}
    await r.start()
    assert not r.recovery and r.mode == "solar"
    assert not r.states["a"].owned and not r.states["a"].on
    assert not [call for call in h.services.calls if call[0] == "switch"]


@pytest.mark.asyncio
async def test_restart_unknown_device_still_requires_review_without_forcing_off():
    r, h = build()
    h.states.set("switch.load", "unavailable")
    r.store.data = {"mode": "solar", "leases": {"a": {"watts": 1000, "name": "Testtoestel"}}, "device_modes": {"a": "auto"}}
    await r.start()
    assert r.recovery and r.mode == "observe"
    assert not [call for call in h.services.calls if call[0] == "switch"]


@pytest.mark.asyncio
async def test_observe_cannot_be_selected_with_owned_load():
    r, h = build()
    r.states["a"].owned = True
    with pytest.raises(HomeAssistantError):
        await r.set_mode("observe")


@pytest.mark.asyncio
async def test_reset_refuses_unknown_or_on_device():
    r, h = build()
    r.faults["a"] = "test"
    h.states.set("switch.load", "unavailable")
    with pytest.raises(HomeAssistantError):
        await r.reset()


@pytest.mark.asyncio
async def test_cycle_rearm_requires_off_and_demand_false():
    r, h = build(kind="script", device={"non_interruptible": True, "condition_entity": "input_boolean.ready"})
    r.states["a"].cycle_armed = False
    await r.tick()
    assert not r.states["a"].cycle_armed
    h.states.set("input_boolean.ready", "off")
    await r.tick()
    assert r.states["a"].cycle_armed


@pytest.mark.asyncio
async def test_meter_stuck_before_command_does_not_allow_new_increase():
    r, h = build()
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    r.last_issued = time.monotonic() - 100
    r.last_issued_wall = time.time() + 1
    await r.tick()
    assert h.services.calls == []


@pytest.mark.asyncio
async def test_max_runtime_fault_does_not_immediately_restart():
    r, h = build()
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    s = r.states["a"]
    s.owned = True
    s.on = True
    s.target_w = 1000
    h.states.set("switch.load", "on")
    await r._send(Action("a", 0, "Maximale looptijd bereikt"), time.monotonic())
    await r.tick()
    assert not s.owned and "a" in r.faults


@pytest.mark.asyncio
async def test_missing_battery_power_blocks_increases():
    r, h = build(settings={"battery_power_entity": "sensor.battery"})
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    await r.tick()
    assert r.problem and h.services.calls == []


@pytest.mark.asyncio
async def test_manual_handover_allows_removed_device_without_physical_command():
    r, h = build()
    h.states.set("switch.load", "unavailable")
    r.states["a"].owned = True
    r.recovery["a"] = {"watts": 1000}
    r.faults["a"] = "offline"
    r.mode = "paused"
    await r.takeover("a")
    assert not r.states["a"].owned and not r.recovery and not r.faults
    assert r.device_modes["a"] == "disabled" and r.editable
    assert h.services.calls == []


@pytest.mark.asyncio
async def test_handover_rejected_in_automatic_mode():
    r, h = build()
    r.mode = "solar"
    with pytest.raises(HomeAssistantError):
        await r.takeover("a")


def test_daily_runtime_counts_observed_on_time_and_resets_at_local_midnight():
    r, h = build(device={"min_daily_runtime_s": 3600, "daily_deadline": "18:00:00"})
    r.runtime_day = "2026-09-21"
    r.states["a"].on = True
    r._update_daily_runtime(datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc), 5)
    assert r.states["a"].daily_runtime_s == 5
    r._update_daily_runtime(datetime(2026, 9, 22, 0, 1, tzinfo=timezone.utc), 5)
    assert r.states["a"].daily_runtime_s == 5
    assert r.runtime_day == "2026-09-22"


def test_daily_deadline_marks_urgent_only_when_remaining_runtime_fills_window():
    r, h = build(device={"min_daily_runtime_s": 3600, "daily_deadline": "18:00:00", "deadline_grid_allowed": True})
    r.runtime_day = "2026-09-21"
    r._update_daily_runtime(datetime(2026, 9, 21, 16, 0, tzinfo=timezone.utc), 0)
    assert not r.states["a"].deadline_urgent
    r._update_daily_runtime(datetime(2026, 9, 21, 17, 0, tzinfo=timezone.utc), 0)
    assert r.states["a"].deadline_urgent and r.states["a"].deadline_force
    r.states["a"].daily_runtime_s = 3600
    r._update_daily_runtime(datetime(2026, 9, 21, 17, 30, tzinfo=timezone.utc), 0)
    assert not r.states["a"].deadline_urgent and not r.states["a"].deadline_force


def test_daily_maximum_disables_deadline_force_even_if_minimum_is_inconsistent():
    r, h = build(device={"min_daily_runtime_s": 7200, "max_daily_runtime_s": 3600,
                         "daily_deadline": "18:00:00", "deadline_grid_allowed": True})
    r.runtime_day = "2026-09-21"
    r.states["a"].daily_runtime_s = 3600
    r._update_daily_runtime(datetime(2026, 9, 21, 17, 30, tzinfo=timezone.utc), 0)
    assert not r.states["a"].deadline_urgent and not r.states["a"].deadline_force


def test_native_time_window_supports_day_and_overnight_ranges():
    r,_=build()
    cfg={'time_window_enabled':True,'time_window_start':'11:00:00','time_window_end':'18:00:00'}
    assert r._time_window_active(datetime(2026,9,21,12,0),cfg)
    assert not r._time_window_active(datetime(2026,9,21,20,0),cfg)
    cfg={'time_window_enabled':True,'time_window_start':'22:00:00','time_window_end':'06:00:00'}
    assert r._time_window_active(datetime(2026,9,21,23,0),cfg)
    assert r._time_window_active(datetime(2026,9,21,5,0),cfg)
    assert not r._time_window_active(datetime(2026,9,21,12,0),cfg)


def test_invalid_native_time_window_fails_closed():
    r,_=build()
    assert not r._time_window_active(datetime(2026,9,21,12,0),
        {'time_window_enabled':True,'time_window_start':'xx','time_window_end':'18:00'})


def test_day_window_end_becomes_implicit_daily_deadline():
    r,_=build()
    cfg={'time_window_enabled':True,'time_window_start':'11:00:00','time_window_end':'18:00:00'}
    assert r._day_window_end_seconds(datetime(2026,9,21,17,30),cfg)==1800
    assert r._day_window_end_seconds(datetime(2026,9,21,19,0),cfg)==0
    cfg={'time_window_enabled':True,'time_window_start':'22:00:00','time_window_end':'06:00:00'}
    assert r._day_window_end_seconds(datetime(2026,9,21,23,0),cfg) is None

def test_daily_energy_integrates_measured_power_and_resets_with_day():
    r, h = build(power=True, settings={"interval_s": 300}, device={"daily_energy_goal_kwh": 2.0})
    r.runtime_day = "2026-09-21"
    r.states["a"].on = True
    r.states["a"].measured_w = 1800
    r._update_daily_runtime(datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc), 600)
    assert r.states["a"].daily_energy_kwh == pytest.approx(0.3)
    r.states["a"].measured_w = 1200
    r._update_daily_runtime(datetime(2026, 9, 21, 12, 10, tzinfo=timezone.utc), 600)
    assert r.states["a"].daily_energy_kwh == pytest.approx(0.5)
    r._update_daily_runtime(datetime(2026, 9, 22, 0, 1, tzinfo=timezone.utc), 0)
    assert r.states["a"].daily_energy_kwh == 0


def test_planner_prices_align_today_and_tomorrow_arrays_to_clock_time():
    r, h = build()
    h.states.set("sensor.dynamic_import", 0.30, {
        "today": [round(0.10 + i * 0.01, 2) for i in range(24)],
        "tomorrow": [round(0.50 + i * 0.01, 2) for i in range(24)],
    })
    r.economy_settings["import_price_entity"] = "sensor.dynamic_import"
    r.planner_settings["slot_min"] = 15
    local_now = datetime(2026, 9, 21, 14, 37, tzinfo=timezone.utc)
    imports, _ = r._planner_prices(48, local_now)
    # Plan aligns to 14:30; every quarter in that hour must use hour 14, not midnight index 0.
    assert imports[0] == pytest.approx(0.24)
    assert imports[1] == pytest.approx(0.24)
    # Crossing midnight switches to tomorrow's profile.
    long_imports, _ = r._planner_prices(48, datetime(2026, 9, 21, 20, 0, tzinfo=timezone.utc))
    assert long_imports[16] == pytest.approx(0.50)


def test_planner_prices_use_timestamped_blocks_when_available():
    r, h = build()
    h.states.set("sensor.dynamic_import", 0.30, {
        "prices": [
            {"start": "2026-09-21T14:00:00+00:00", "price": 0.11},
            {"start": "2026-09-21T15:00:00+00:00", "price": 0.31},
        ]
    })
    r.economy_settings["import_price_entity"] = "sensor.dynamic_import"
    imports, _ = r._planner_prices(8, datetime(2026, 9, 21, 14, 30, tzinfo=timezone.utc))
    assert imports[:2] == pytest.approx([0.11, 0.11])
    assert imports[2:6] == pytest.approx([0.31, 0.31, 0.31, 0.31])
    assert r.planner_price_sources["import"] == "tijdgestempelde prijsreeks"


def test_overview_with_configured_device_uses_real_device_id_for_cycle_learning():
    """Regression: adding the first flex load must not break sensor.solarpilot_status."""
    r, _ = build(device={"non_interruptible": False, "cycle_program": "standaard"})
    rows = r.overview()
    assert len(rows) == 1
    assert rows[0]["id"] == "a"
    assert rows[0]["cycle_learning"]["program"] == "standaard"
    requirements = rows[0]["start_requirements"]
    assert requirements["availability_and_fault"]["available"] is None
    assert requirements["release"]["released"] is None
    assert requirements["demand_or_time_window"]["demand"] is None


@pytest.mark.asyncio
async def test_overview_exposes_live_start_power_and_stability_without_replacing_engine_reason():
    r, _ = build(device={"start_delay_s": 30, "start_margin_w": 150, "min_off_s": 0})
    r.mode = "solar"
    r.device_modes["a"] = "auto"

    await r.tick()

    row = r.overview()[0]
    requirements = row["start_requirements"]
    diagnostics = row["start_diagnostics"]
    assert all(requirements[key]["met"] for key in (
        "global_solar_mode", "recovery_clear", "automatic_participation",
        "reliable_energy_measurement", "availability_and_fault",
        "release", "demand_or_time_window", "minimum_rest",
        "non_interruptible_cycle_release", "daily_maximum",
        "planner_start_block", "wallbox_start_block", "runtime_start_block",
        "general_increase_permission"))
    assert diagnostics["summary"] == row["reason"] == r.result.reasons["a"]
    assert diagnostics["summary_source"] == "result.reason"
    assert diagnostics["missing"] == []
    assert diagnostics["power"]["minimum_w"] == 1000.0
    assert diagnostics["power"]["start_margin_w"] == 150.0
    assert diagnostics["power"]["required_start_w"] == 1150.0
    assert diagnostics["power"]["measured_free_w"] == 2500.0
    assert diagnostics["power"]["measurement_valid"] is True
    assert diagnostics["power"]["effective_import_limit_w"] == 3500.0
    assert "hogere prioriteiten" in diagnostics["power"]["note"]
    assert diagnostics["stable_start"]["building"]
    assert 0 < diagnostics["stable_start"]["remaining_s"] <= 30


def test_overview_reports_each_known_start_block_and_hides_invalid_free_power():
    r, _ = build(device={"non_interruptible": True, "min_off_s": 120,
                         "max_daily_runtime_s": 3600, "start_margin_w": 200})
    s = r.states["a"]
    r.mode = "observe"
    r.device_modes["a"] = "disabled"
    s.available = False
    s.fault = "Vermogensmeting onbetrouwbaar"
    s.interlock = False
    s.demand = False
    s.last_off = time.monotonic()
    s.cycle_armed = False
    s.daily_runtime_s = 3600
    s.planner_hold = True
    s.planner_reason = "Planner wacht op gepland venster"
    r._start_context = {
        "measurement_valid": False,
        "device_start_blocks": {"a": "Beschermde hogere prioriteit wacht"},
        "wallbox_start_blocks": {"a": "Wallbox krijgt eerst zonnevermogen"},
        "wallbox_global_block": False,
        "wallbox_reason": "",
        "can_increase": False,
        "increase_reason": "Fasebewaking blokkeert nieuwe verhogingen",
        "effective_import_limit_w": 0,
        "max_increase_w": 0,
        "device_increase_limits": {"a": 0},
    }
    r.result = Plan(free_w=9999, targets={"a": 0},
                    reasons={"a": "Doorslaggevende bestaande regeluitkomst"})

    row = r.overview()[0]
    requirements = row["start_requirements"]
    diagnostics = row["start_diagnostics"]
    assert diagnostics["summary"] == "Doorslaggevende bestaande regeluitkomst"
    assert diagnostics["power"]["measured_free_w"] is None
    assert diagnostics["power"]["required_start_w"] == 1200.0
    assert requirements["minimum_rest"]["remaining_s"] > 0
    assert not requirements["non_interruptible_cycle_release"]["met"]
    assert not requirements["daily_maximum"]["met"]
    assert requirements["planner_start_block"]["reason"] == "Planner wacht op gepland venster"
    assert requirements["wallbox_start_block"]["reason"] == "Wallbox krijgt eerst zonnevermogen"
    assert requirements["runtime_start_block"]["reason"] == "Beschermde hogere prioriteit wacht"
    assert not requirements["reliable_energy_measurement"]["met"]
    assert requirements["general_increase_permission"]["reason"] == "Fasebewaking blokkeert nieuwe verhogingen"
    assert set(diagnostics["missing"]) == {
        "global_solar_mode", "automatic_participation", "reliable_energy_measurement",
        "availability_and_fault",
        "release", "demand_or_time_window", "minimum_rest",
        "non_interruptible_cycle_release", "daily_maximum",
        "planner_start_block", "wallbox_start_block", "runtime_start_block",
        "general_increase_permission",
    }


@pytest.mark.asyncio
async def test_pure_wallbox_start_block_is_not_duplicated_as_runtime_block():
    r, _ = build(device={"min_off_s": 0})
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    wallbox_reason = "Wallbox krijgt eerst zonnevermogen"
    r._wallbox_device_constraints = lambda *args: ({}, {"a": wallbox_reason}, set())

    await r.tick()

    row = r.overview()[0]
    requirements = row["start_requirements"]
    assert not requirements["wallbox_start_block"]["met"]
    assert requirements["wallbox_start_block"]["reason"] == wallbox_reason
    assert requirements["runtime_start_block"]["met"]
    assert requirements["runtime_start_block"]["reason"] == ""
    assert "wallbox_start_block" in row["start_diagnostics"]["missing"]
    assert "runtime_start_block" not in row["start_diagnostics"]["missing"]
    assert row["reason"] == wallbox_reason


@pytest.mark.asyncio
async def test_invalid_grid_measurement_is_an_explicit_missing_start_requirement():
    r, h = build(device={"min_off_s": 0})
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    h.states.set("sensor.grid", -3000, {"unit_of_measurement": "W"}, age=500)

    await r.tick()

    row = r.overview()[0]
    requirement = row["start_requirements"]["reliable_energy_measurement"]
    assert not requirement["met"] and not requirement["valid"]
    assert "reliable_energy_measurement" in row["start_diagnostics"]["missing"]
    assert row["start_diagnostics"]["power"]["measured_free_w"] is None


def test_recovery_is_reported_separately_from_solar_mode():
    r, _ = build(device={"min_off_s": 0})
    r.mode = "solar"
    r.recovery["a"] = {"reason": "controle nodig"}

    requirements = r.overview()[0]["start_requirements"]

    assert requirements["global_solar_mode"]["met"]
    assert not requirements["recovery_clear"]["met"]
    assert requirements["recovery_clear"]["active"]


def test_dishwasher_start_pool_is_read_only_and_hidden_with_invalid_site_measurement():
    from test_dishwasher import setup
    r, h, cfg = setup()
    pool = {"available_solar_w": 1450.0, "wallbox_solar_w": 1000.0,
            "source": "dishwasher_priority.evaluate", "not_a_start_guarantee": True}
    r.dishwasher_priority.view.start_power['a'] = dict(pool)
    r._start_context = {"measurement_valid": True}
    row = r.overview()[0]
    assert row['start_diagnostics']['power']['solar_start_pool'] == pool
    row['start_diagnostics']['power']['solar_start_pool']['wallbox_solar_w'] = 9999
    assert r.dishwasher_priority.view.start_power['a'] == pool
    assert not r.dishwasher_priority.view.ev_credit and not h.services.calls
    r._start_context['measurement_valid'] = False
    assert r.overview()[0]['start_diagnostics']['power']['solar_start_pool'] is None


@pytest.mark.asyncio
async def test_manual_start_and_stop_are_explicit_and_confirmed():
    r, h = build()
    r.mode = "solar"
    await r.manual_start("a")
    assert r.states["a"].manual_forced
    assert h.states.get("switch.load").state == "on"
    await r.tick()  # confirm the start
    assert r.states["a"].owned and r.states["a"].on
    r.last_issued -= 10
    await r.manual_stop("a")
    assert r.states["a"].manual_stop_requested
    assert h.states.get("switch.load").state == "off"
    await r.tick()  # confirm the stop
    assert not r.states["a"].owned and not r.states["a"].manual_forced and not r.states["a"].manual_stop_requested


@pytest.mark.asyncio
async def test_manual_start_is_rejected_outside_solar_mode():
    r, _h = build()
    with pytest.raises(HomeAssistantError):
        await r.manual_start("a")


@pytest.mark.asyncio
async def test_beta36_active_owned_switch_does_not_receive_duplicate_turn_on_for_new_estimate():
    r,h=build(power=True)
    r.states["a"].on=True
    r.states["a"].owned=True
    r.states["a"].target_w=310
    h.states.set("switch.load","on")
    await r._send(Action("a",325,"Nieuw geleerd planningsvermogen"),time.monotonic())
    assert h.services.calls==[]
    assert r.states["a"].target_w==325
    assert r.result.reasons["a"]=="Reeds ingeschakeld; alleen planningsvermogen bijgewerkt"
