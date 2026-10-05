"""Observed demand and causal room traces, independent of forecast optimism."""
from copy import deepcopy
from types import SimpleNamespace
import time

import pytest

from custom_components.solar_pilot.thermal_climate import ThermalProfile, decide_zone
from test_automatic_climate_model54 import SETTINGS, room
from test_automatic_climate_runtime54 import automatic, refresh
from test_thermal_runtime_beta48 import climate_calls, report, tick


def sample(profile, wall, temperature, action):
    return profile.observe(wall_ts=wall, day="2026-10-05", indoor_c=temperature,
                           outdoor_c=14., hvac_action=action, pv_w=0., settings=SETTINGS)


@pytest.mark.parametrize("previous,current,temperature,other_outside,direction", [
    ("heating", "idle", 22., 14., "cooling"),
    ("cooling", "idle", 20., 30., "heating"),
])
def test_mixed_action_interval_cannot_create_reactive_opposing_demand(previous, current, temperature, other_outside, direction):
    profile = ThermalProfile()
    now = time.time()
    sample(profile, now - 900, temperature + (-.1 if previous == "heating" else .1), previous)
    sample(profile, now, temperature, current)
    decision = decide_zone(settings=SETTINGS, zone=room(temperature, action=current),
                           profile=profile, outside_c=other_outside, outside_hourly=[other_outside] * 48)
    assert decision.desired_mode == "off"
    assert decision.comfort_direction != direction


@pytest.mark.parametrize("old_action,temperature,outside", [("heating", 22., 14.), ("cooling", 20., 30.)])
def test_active_sample_slope_does_not_become_passive_when_live_action_changes(old_action, temperature, outside):
    profile = ThermalProfile()
    now = time.time()
    sample(profile, now - 900, temperature + (-.1 if old_action == "heating" else .1), old_action)
    sample(profile, now, temperature, old_action)
    decision = decide_zone(settings=SETTINGS, zone=room(temperature, action="off"),
                           profile=profile, outside_c=outside, outside_hourly=[outside] * 48)
    assert decision.desired_mode == "off"


@pytest.mark.parametrize("temperature,actual_outside,future_outside", [(22., 14., 40.), (20., 30., 5.)])
def test_future_weather_without_validated_response_is_not_current_reactive_demand(temperature, actual_outside, future_outside):
    decision = decide_zone(settings=SETTINGS, zone=room(temperature), profile=ThermalProfile(),
                           outside_c=actual_outside, outside_hourly=[future_outside] * 48)
    assert decision.desired_mode == "off"


@pytest.mark.parametrize("age,endpoint,expected", [(0, 22., "auto"), (1801, 22., "off"), (0, 22.2, "off")])
def test_only_fresh_same_temperature_passive_interval_establishes_opposing_context(age, endpoint, expected):
    profile = ThermalProfile()
    now = time.time()
    sample(profile, now - age - 900, 21.9, "off")
    sample(profile, now - age, 22., "off")
    decision = decide_zone(settings=SETTINGS, zone=room(endpoint), profile=profile,
                           outside_c=14., outside_hourly=[14.] * 48)
    assert decision.desired_mode == expected


@pytest.mark.asyncio
async def test_no_false_salon_auto_after_heating_to_idle_and_other_room_stays_off(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=22, outside=14)
    profile = manager.state.profile("climate.salon")
    sample(profile, wall[0] - 900, 21.9, "heating")
    sample(profile, wall[0], 22., "idle")
    manager.state.last_sample_wall = wall[0]
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert manager.zone_decisions["climate.salon"].desired_mode == "off"
    assert manager.zone_decisions["climate.home"].desired_mode == "off"


@pytest.mark.asyncio
async def test_unconfirmed_auto_then_baseline_off_report_is_not_guessed_external_command(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.salon"])
    await tick(manager, wall[0])
    issued = wall[0]
    wall[0] += 5
    report(hass, "climate.salon", "auto", current_temperature=21.)
    await tick(manager, wall[0])  # Too early to confirm, potentially optimistic.
    assert manager.pending_commands
    wall[0] += 10
    report(hass, "climate.salon", "off", current_temperature=21.)
    await tick(manager, wall[0])
    assert manager.pending_commands
    assert not manager.cancelled_auto and not manager.zone_holds
    wall[0] += 15
    report(hass, "climate.salon", "auto", current_temperature=21.)
    await tick(manager, wall[0])
    assert not manager.pending_commands
    wall[0] = issued + 3600
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    assert [call[2]["hvac_mode"] for call in climate_calls(hass)] == ["auto", "off"]


@pytest.mark.asyncio
@pytest.mark.parametrize("caused_by_own_command", [False, True])
async def test_explicit_foreign_off_service_wins_during_pending_even_without_user_id(monkeypatch, caused_by_own_command):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.salon"])
    await tick(manager, wall[0])
    manager.on_service_event(SimpleNamespace(
        data={"domain": "climate", "service": "set_hvac_mode", "service_data": {
            "entity_id": "climate.salon", "hvac_mode": "off"}},
        context=SimpleNamespace(user_id=None, id="external_automation",
                                parent_id=manager.pending_commands["climate.salon"]["context_id"] if caused_by_own_command else None)))
    assert not manager.pending_commands
    assert manager.zone_holds["climate.salon"] > wall[0]
    assert "climate.salon" in manager.cancelled_auto


@pytest.mark.asyncio
async def test_own_parent_context_does_not_create_external_hold(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.salon"])
    await tick(manager, wall[0])
    pending = manager.pending_commands["climate.salon"]
    before = deepcopy(hass.states.get("climate.salon"))
    report(hass, "climate.salon", "auto")
    current = hass.states.get("climate.salon")
    current.context = SimpleNamespace(user_id="inherited_user", id="native_child", parent_id=pending["context_id"])
    manager.on_event(SimpleNamespace(data={"entity_id": "climate.salon", "old_state": before, "new_state": current}))
    assert manager.pending_commands
    assert not manager.zone_holds


@pytest.mark.asyncio
async def test_soft_demand_waits_ten_minutes_and_real_report_then_commands_once(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=20., zones=["climate.salon"])
    issued = wall[0]
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    view = manager.overview()["zones"][0]
    assert view["execution_status"] == "demand_confirmation"
    assert view["demand_confirmation_remaining_s"] == 600
    for elapsed in (5, 100, 599, 600, 700):
        wall[0] = issued + elapsed
        await tick(manager, wall[0])
        assert not climate_calls(hass)  # One old report cannot prove persistence.
        assert manager._demand_since["climate.salon"]["wall"] == issued
    report(hass, "climate.salon", current_temperature=20.)
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 1
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 1
    stages = [row["stage"] for row in manager.decision_trace]
    assert "journal" in stages and "issued" in stages


@pytest.mark.asyncio
async def test_one_brief_soft_excursion_does_not_wake_room_and_timer_resets(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=20., zones=["climate.salon"])
    await tick(manager, wall[0])
    wall[0] += 590
    report(hass, "climate.salon", current_temperature=21.)
    await tick(manager, wall[0])
    assert not manager._demand_since
    wall[0] += 20
    report(hass, "climate.salon", current_temperature=20.)
    await tick(manager, wall[0])
    assert manager._demand_since["climate.salon"]["wall"] == wall[0]
    assert not climate_calls(hass)


@pytest.mark.asyncio
async def test_source_outage_and_restart_never_count_as_confirmed_soft_demand(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=20., zones=["climate.salon"])
    await tick(manager, wall[0])
    saved = manager.snapshot()
    report(hass, "climate.salon", "unavailable")
    await tick(manager, wall[0])
    assert not manager._demand_since
    manager.restore(saved)
    assert not manager._demand_since
    wall[0] += 700
    report(hass, "climate.salon", "off", current_temperature=20.)
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert manager._demand_since["climate.salon"]["wall"] == wall[0]


@pytest.mark.asyncio
async def test_traces_deduplicate_ticks_include_exact_command_inputs_and_persist(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=22., outside=14., zones=["climate.salon"])
    events = []
    runtime.analysis = SimpleNamespace(event=lambda *args: events.append(args))
    await tick(manager, wall[0])
    trace = manager.decision_trace[-1]
    assert trace["inputs"]["current_c"] == 22.
    assert trace["inputs"]["target_c"] == 21.
    assert trace["inputs"]["outside_c"] == 14.
    assert trace["inputs"]["action_known"] is True
    assert trace["outcome"] == "already_reported"
    assert trace["decision"]["mode"] == "off"
    assert not trace["confirmed"]
    for _ in range(10):
        wall[0] += 5
        await tick(manager, wall[0])
    assert len(manager.decision_trace) == len(events) == 1
    snapshot = manager.snapshot()
    manager.restore(snapshot)
    assert list(manager.decision_trace) == snapshot["decision_trace"]
    wall[0] += 900
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    assert len(manager.decision_trace) == len(events) == 2
    for idx in range(200):
        manager._trace("climate.salon", "decision", "test", str(idx), force=True)
    assert len(manager.decision_trace) == 128


@pytest.mark.asyncio
async def test_parent_gate_is_visible_per_room_and_in_trace(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.salon"])
    from datetime import datetime, timezone
    await manager.tick(local_now=datetime.fromtimestamp(wall[0], timezone.utc), allow_command=False,
                       dispatch_block_code="dhw_protected", dispatch_block_reason="Panasonic-sterilisatie is beschermd")
    assert not climate_calls(hass)
    view = manager.overview()
    assert view["zones"][0]["execution_status"] == "dhw_protected"
    assert view["zones"][0]["execution_reason"] == "Panasonic-sterilisatie is beschermd"
    assert view["decision_trace"][-1]["gates"]["parent_block_code"] == "dhw_protected"


@pytest.mark.asyncio
async def test_no_blanket_hold_from_baseline_report_but_unconfirmed_timeout_stays_sticky(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.salon"])
    await tick(manager, wall[0])
    wall[0] += 5
    report(hass, "climate.salon", "auto")
    await tick(manager, wall[0])
    wall[0] += 10
    report(hass, "climate.salon", "off")
    await tick(manager, wall[0])
    wall[0] += manager.COMMAND_TIMEOUT_S
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    assert "climate.salon" in manager.command_faults
    assert not manager.pending_commands
    assert len(climate_calls(hass)) == 1
    assert any(row["event"] == "timeout" and row["outcome"] == "unconfirmed" for row in manager.decision_trace)


@pytest.mark.asyncio
@pytest.mark.parametrize("temperature,outside,native_program", [(19.5, 5., "cool"), (23., 40., "heat"),
                                                            (19.5, 5., "auto_cool"), (23., 40., "auto_heat")])
async def test_programme_cannot_supply_opposite_measured_demand(monkeypatch, temperature, outside, native_program):
    _, hass, manager, wall = automatic(monkeypatch, temp=temperature, outside=outside, zones=["climate.salon"])
    hass.states.set("sensor.native_program", native_program, {})
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    decision = manager.zone_decisions["climate.salon"]
    assert decision.desired_mode == "off"
    assert decision.block_reason == "native_program_mismatch"
    assert "Panasonic-programma" in decision.reason
    assert manager.overview()["zones"][0]["native_program"]["raw_mode"] == native_program


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["auto", "PUMP", "WATER", "unavailable", "restored", "stale", "future"])
async def test_unknown_or_bad_programme_never_enables_auto(monkeypatch, bad):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.salon"])
    attrs = {"restored": True} if bad == "restored" else {}
    hass.states.set("sensor.native_program", "heat" if bad in ("restored", "stale", "future") else bad,
                    attrs, reported_age=1801 if bad == "stale" else -10 if bad == "future" else 0)
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert manager.overview()["zones"][0]["execution_status"] == "native_program_unknown"


@pytest.mark.asyncio
@pytest.mark.parametrize("native_program", ["heat", "heating", "auto_heat", "heat_cool"])
async def test_verified_heating_programme_can_supply_real_heating_need(monkeypatch, native_program):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.salon"])
    hass.states.set("sensor.native_program", native_program, {})
    await tick(manager, wall[0])
    assert [call[2] for call in climate_calls(hass)] == [{"entity_id": "climate.salon", "hvac_mode": "auto"}]


@pytest.mark.asyncio
async def test_programme_change_while_journal_saves_cancels_unissued_auto(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.salon"])
    hass.states.set("sensor.native_program", "heat", {})
    original = runtime.store.async_save
    changed = []
    async def change_programme(data):
        await original(data)
        if not changed:
            changed.append(True)
            hass.states.set("sensor.native_program", "cool", {})
    runtime.store.async_save = change_programme
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert not manager.pending_commands
    assert not runtime.store.data["smart_climate"]["pending_commands"]


@pytest.mark.asyncio
async def test_dashboard_explicit_auto_remains_a_user_choice_even_with_unknown_programme(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.salon"])
    hass.states.set("sensor.native_program", "unknown", {})
    await manager.async_set_override("climate.salon", "auto")
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 1
    assert climate_calls(hass)[0][2]["hvac_mode"] == "auto"


def native_control(monkeypatch, *, mode="auto", temp=21, outside=14):
    from homeassistant.helpers import entity_registry as er
    from custom_components.solar_pilot import native_program as native_module
    from test_native_program56 import Coordinator
    runtime, hass, manager, wall = automatic(monkeypatch, mode=mode, temp=temp,
                                            outside=outside, zones=["climate.salon"])
    coordinator = Coordinator()
    entry = SimpleNamespace(domain="aquarea", runtime_data={"pump": coordinator})
    rows = {"climate.salon": SimpleNamespace(platform="aquarea", config_entry_id="native",
                                             unique_id="pump_climate_2")}
    hass.config_entries = SimpleNamespace(async_get_entry=lambda eid: entry if eid == "native" else None)
    monkeypatch.setattr(er, "async_get", lambda _hass: SimpleNamespace(async_get=rows.get))
    monkeypatch.setattr(native_module.time, "monotonic", lambda: wall[0])
    manager.settings["operation_mode_entity"] = ""
    manager._zones()  # A cached snapshot alone cannot prove the programme.
    return runtime, hass, manager, wall, coordinator, rows


@pytest.mark.asyncio
@pytest.mark.parametrize("programme,temperature,outside,direction", [
    ("HEAT", 19.5, 5., "heating"), ("COOL", 23., 40., "cooling"),
])
async def test_own_confirmed_off_can_resume_from_fresh_off_and_proven_intention(monkeypatch, programme, temperature, outside, direction):
    from test_native_program56 import ExtendedOperationMode
    _, hass, manager, wall, coordinator, _ = native_control(monkeypatch, outside=outside)
    coordinator.poll(ExtendedOperationMode[programme])
    await tick(manager, wall[0])  # No current need: request our own pause.
    assert climate_calls(hass)[0][2]["hvac_mode"] == "off"
    wall[0] += 15
    coordinator.poll(ExtendedOperationMode.OFF)
    report(hass, "climate.salon", "off")
    await tick(manager, wall[0])
    assert not manager.pending_commands
    proof = manager._operation_program("climate.salon")
    assert proof["current_native_program"] == "off"
    assert proof["programme_intent"] == direction
    assert proof["source"] == "owned_off_programme"
    wall[0] += 3600
    refresh(hass, wall[0], outside=outside)
    coordinator.poll(ExtendedOperationMode.OFF)
    report(hass, "climate.salon", "off", current_temperature=temperature)
    await tick(manager, wall[0])
    assert [call[2]["hvac_mode"] for call in climate_calls(hass)] == ["off", "auto"]


@pytest.mark.asyncio
async def test_own_cooling_pause_cannot_release_auto_for_low_temperature(monkeypatch):
    from test_native_program56 import ExtendedOperationMode
    _, hass, manager, wall, coordinator, _ = native_control(monkeypatch, outside=5.)
    coordinator.poll(ExtendedOperationMode.COOL)
    await tick(manager, wall[0])
    wall[0] += 15
    coordinator.poll(ExtendedOperationMode.OFF)
    report(hass, "climate.salon", "off")
    await tick(manager, wall[0])
    assert manager._operation_program("climate.salon")["programme_intent"] == "cooling"
    wall[0] += 3600
    refresh(hass, wall[0], outside=5.)
    coordinator.poll(ExtendedOperationMode.OFF)
    report(hass, "climate.salon", "off", current_temperature=19.5)
    await tick(manager, wall[0])
    assert [call[2]["hvac_mode"] for call in climate_calls(hass)] == ["off"]
    assert manager.zone_decisions["climate.salon"].block_reason == "native_program_mismatch"


@pytest.mark.asyncio
async def test_restored_lease_cannot_use_late_first_off_proof_from_corrupt_journal(monkeypatch):
    from custom_components.solar_pilot.thermal_runtime import SmartClimateManager
    from test_native_program56 import ExtendedOperationMode
    runtime, hass, manager, wall, coordinator, _ = native_control(monkeypatch, mode="off", temp=19.5)
    coordinator.poll(ExtendedOperationMode.HEAT)
    binding = manager._operation_program("climate.salon")["binding_key"]
    manager.state.expected_mode["climate.salon"] = "off"
    manager.program_leases["climate.salon"] = {
        "source": "aquarea_poll", "program": "heating", "raw_mode": "HEAT",
        "binding_key": binding, "entity_id": "climate.salon",
        "issued_wall": wall[0] - 3600, "ack_wall": wall[0] - 3585,
        "off_proven_wall": wall[0] - 1,  # Corrupt: not within the initial 180s.
    }
    snapshot = manager.snapshot()
    manager.close()
    restored = SmartClimateManager(runtime)
    restored.settings = dict(manager.settings)
    runtime.smart_climate = restored
    restored.restore(snapshot)
    assert "off_proven_wall" not in restored.program_leases["climate.salon"]
    restored._zones()
    coordinator.poll(ExtendedOperationMode.OFF)
    await tick(restored, wall[0])
    assert not climate_calls(hass)
    assert restored._operation_program("climate.salon")["program"] == "off"


@pytest.mark.asyncio
@pytest.mark.parametrize("invalidate", ["unowned", "stale", "failed_poll", "foreign_off", "rebind"])
async def test_prior_programme_never_resumes_when_ownership_or_current_proof_is_missing(monkeypatch, invalidate):
    from test_native_program56 import ExtendedOperationMode
    _, hass, manager, wall, coordinator, rows = native_control(monkeypatch)
    coordinator.poll(ExtendedOperationMode.HEAT)
    await tick(manager, wall[0])
    wall[0] += 15
    coordinator.poll(ExtendedOperationMode.OFF)
    report(hass, "climate.salon", "off")
    await tick(manager, wall[0])
    manager._operation_program("climate.salon")
    wall[0] += 3600
    refresh(hass, wall[0])
    report(hass, "climate.salon", "off", current_temperature=19.5)
    if invalidate != "stale":
        coordinator.poll(ExtendedOperationMode.OFF, success=invalidate != "failed_poll")
    if invalidate == "unowned":
        manager.state.expected_mode.clear()
    elif invalidate == "foreign_off":
        manager.on_service_event(SimpleNamespace(data={"domain": "climate", "service": "set_hvac_mode",
            "service_data": {"entity_id": "climate.salon", "hvac_mode": "off"}},
            context=SimpleNamespace(id="foreign", user_id=None, parent_id=None)))
        assert not manager.program_leases
    elif invalidate == "rebind":
        rows["climate.salon"].unique_id = "pump_climate_1"
        manager._operation_program("climate.salon")
        assert not manager.program_leases
        rows["climate.salon"].unique_id = "pump_climate_2"
        manager._operation_program("climate.salon")
        coordinator.poll(ExtendedOperationMode.OFF)
    await tick(manager, wall[0])
    assert [call[2]["hvac_mode"] for call in climate_calls(hass)] == ["off"]


@pytest.mark.asyncio
async def test_tunable_settings_preserve_confirmed_pause_intention_but_source_change_revokes_it(monkeypatch):
    from test_native_program56 import ExtendedOperationMode
    _, hass, manager, wall, coordinator, _ = native_control(monkeypatch)
    coordinator.poll(ExtendedOperationMode.HEAT)
    await tick(manager, wall[0])
    wall[0] += 15
    coordinator.poll(ExtendedOperationMode.OFF)
    report(hass, "climate.salon", "off")
    await tick(manager, wall[0])
    manager._operation_program("climate.salon")
    before = deepcopy(manager.program_leases)
    manager.apply_settings({**manager.settings, "sampling_interval_s": 600})
    assert manager.program_leases == before
    assert manager._operation_program("climate.salon")["source"] == "owned_off_programme"
    manager.apply_settings({**manager.settings, "operation_mode_entity": "sensor.native_program"})
    assert not manager.program_leases


@pytest.mark.asyncio
async def test_same_entity_programme_binding_change_during_journal_cancels_auto(monkeypatch):
    from test_native_program56 import ExtendedOperationMode
    from test_native_program56 import Coordinator
    runtime, hass, manager, wall, coordinator, rows = native_control(monkeypatch, mode="off", temp=19.5)
    coordinator.poll(ExtendedOperationMode.HEAT)
    # Both zones can have fresh evidence before a registry rebind during save.
    rows["climate.other"] = SimpleNamespace(platform="aquarea", config_entry_id="native", unique_id="pump_climate_1")
    manager.native_program.read("climate.other")
    coordinator.poll(ExtendedOperationMode.HEAT)
    original = runtime.store.async_save
    changed = []
    async def rebind(data):
        await original(data)
        if not changed:
            changed.append(True)
            rows["climate.salon"].unique_id = "pump_climate_1"
    runtime.store.async_save = rebind
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert not manager.pending_commands


@pytest.mark.asyncio
async def test_legacy_automatic_release_also_blocks_cooling_programme_for_heat_need(monkeypatch):
    _, hass, manager, wall = automatic(monkeypatch, temp=19.5, zones=["climate.salon"])
    manager.settings["automatic_zone_control"] = False
    manager.state.expected_mode["climate.salon"] = "off"
    hass.states.set("sensor.native_program", "cool", {})
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert manager.zone_decisions["climate.salon"].block_reason == "native_program_mismatch"


@pytest.mark.parametrize("bad", ["string", True, float("nan"), float("inf")])
def test_invalid_native_report_timestamp_cannot_break_diagnosis_callback(monkeypatch, bad):
    _, hass, manager, _ = automatic(monkeypatch, zones=["climate.salon"])
    obj = hass.states.get("climate.salon")
    obj.last_reported = SimpleNamespace(timestamp=lambda: bad)
    manager._trace("climate.salon", "native_report", "observed", "Rapport gecontroleerd", force=True)
    assert manager.decision_trace[-1]["inputs"]["reported_wall"] is None
