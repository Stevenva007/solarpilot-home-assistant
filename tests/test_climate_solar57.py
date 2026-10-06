"""Real surplus releases AUTO independently of thermal demand and learning."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.thermal_runtime import SmartClimateManager
from test_automatic_climate_runtime54 import automatic, refresh
from test_thermal_runtime_beta48 import climate_calls, report, tick


def solar(monkeypatch, *, watts=2500., mode="off", zones=None):
    runtime, hass, manager, wall = automatic(monkeypatch, temp=21., outside=14., mode=mode,
                                           zones=zones or ["climate.home"])
    budget = {"valid": True, "available_w": watts, "residual_w": watts,
              "measured_wall": wall[0], "heatpump_w": 0.,
              "heatpump_meter_valid": True, "solar_ceiling_w": 5000.}
    runtime.climate_solar_budget = lambda: {**budget, "compensated_w": budget.get(
        "compensated_w", min(budget["solar_ceiling_w"], budget["available_w"] + (budget["heatpump_w"] or 0.)))}
    return runtime, hass, manager, wall, budget


async def advance(hass, manager, wall, budget, seconds=60):
    wall[0] += seconds
    refresh(hass, wall[0])
    budget["measured_wall"] = wall[0]
    return await tick(manager, wall[0])


@pytest.mark.asyncio
@pytest.mark.parametrize("programme", ["heat", "cool", "heat_cool", "off"])
async def test_solar_auto_at_inclusive_2500_works_without_model_or_matching_thermal_need(monkeypatch, programme):
    _, hass, manager, wall, budget = solar(monkeypatch)
    hass.states.set("sensor.native_program", programme)
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert manager.zone_decisions["climate.home"].block_reason == "solar_confirmation"
    await advance(hass, manager, wall, budget)
    assert [call[2] for call in climate_calls(hass)] == [{"entity_id": "climate.home", "hvac_mode": "auto"}]
    assert manager.zone_decisions["climate.home"].stage == "solar"
    assert not manager.zone_decisions["climate.home"].comfort_required
    assert manager.zone_decisions["climate.home"].missing_components == []
    assert manager.pending_commands["climate.home"]["solar_availability"] is True
    assert not manager.solar_owned  # A command request is not a later report.
    assert "geen actieve" in manager.zone_decisions["climate.home"].reason


@pytest.mark.asyncio
@pytest.mark.parametrize("watts,valid", [(2499., True), (5000., False)])
async def test_solar_start_never_uses_insufficient_or_invalid_headroom(monkeypatch, watts, valid):
    _, hass, manager, wall, budget = solar(monkeypatch, watts=watts)
    budget["valid"] = valid
    await tick(manager, wall[0])
    await advance(hass, manager, wall, budget, 120)
    assert not climate_calls(hass)
    assert manager.zone_decisions["climate.home"].desired_mode == "off"


@pytest.mark.asyncio
async def test_elapsed_time_without_a_new_meter_report_cannot_confirm_surplus(monkeypatch):
    _, hass, manager, wall, budget = solar(monkeypatch)
    await tick(manager, wall[0])
    wall[0] += 60
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert "nieuwe echte vermogensmeting" in manager.zone_decisions["climate.home"].reason
    budget["measured_wall"] = wall[0]
    await tick(manager, wall[0])
    assert len(climate_calls(hass)) == 1


@pytest.mark.asyncio
async def test_shortfall_restarts_continuous_solar_confirmation(monkeypatch):
    _, hass, manager, wall, budget = solar(monkeypatch)
    await tick(manager, wall[0])
    budget["available_w"] = 2499.
    await advance(hass, manager, wall, budget, 40)
    budget["available_w"] = 2500.
    await advance(hass, manager, wall, budget, 20)
    await advance(hass, manager, wall, budget, 59)
    assert not climate_calls(hass)
    await advance(hass, manager, wall, budget, 1)
    assert len(climate_calls(hass)) == 1


@pytest.mark.asyncio
async def test_unknown_native_program_still_blocks_solar_write(monkeypatch):
    _, hass, manager, wall, budget = solar(monkeypatch)
    hass.states.set("sensor.native_program", "unavailable")
    await tick(manager, wall[0])
    await advance(hass, manager, wall, budget)
    assert not climate_calls(hass)
    assert manager.zone_decisions["climate.home"].block_reason == "native_program_unknown"


@pytest.mark.asyncio
@pytest.mark.parametrize("guard", ["dashboard_off", "external_hold", "fault", "minimum_off", "advice_only"])
async def test_solar_availability_preserves_actual_permission_and_cycle_guards(monkeypatch, guard):
    _, hass, manager, wall, budget = solar(monkeypatch)
    if guard == "dashboard_off":
        manager.dashboard_overrides["climate.home"] = "off"
    elif guard == "external_hold":
        manager.zone_holds["climate.home"] = wall[0] + 600
    elif guard == "fault":
        manager.command_faults["climate.home"] = "Niet bevestigd"
    elif guard == "minimum_off":
        manager.zone_command_walls["climate.home"] = wall[0]
    else:
        manager.settings["control_enabled"] = False
    await tick(manager, wall[0])
    await advance(hass, manager, wall, budget)
    assert not climate_calls(hass)


@pytest.mark.asyncio
async def test_dashboard_fixed_auto_does_not_wait_for_solar_confirmation(monkeypatch):
    _, hass, manager, wall, _ = solar(monkeypatch)
    manager.dashboard_overrides["climate.home"] = "auto"
    await tick(manager, wall[0])
    assert [call[2]["hvac_mode"] for call in climate_calls(hass)] == ["auto"]
    assert "solar_availability" not in manager.pending_commands["climate.home"]


@pytest.mark.asyncio
async def test_confirmation_countdown_is_visible_without_new_log_for_each_tick(monkeypatch):
    _, hass, manager, wall, budget = solar(monkeypatch)
    await tick(manager, wall[0])
    original_reason = manager.zone_decisions["climate.home"].reason
    original_decisions = len([row for row in manager.decision_trace if row["event"] == "decision"])
    for _ in range(5):
        await advance(hass, manager, wall, budget, 5)
    assert manager.zone_decisions["climate.home"].reason == original_reason
    assert len([row for row in manager.decision_trace if row["event"] == "decision"]) == original_decisions
    assert manager.overview()["zones"][0]["solar_confirmation_remaining_s"] == 35.


@pytest.mark.asyncio
async def test_solar_availability_does_not_spend_the_predictive_optimization_daily_limit(monkeypatch):
    _, hass, manager, wall, budget = solar(monkeypatch)
    manager.zone_command_counts["climate.home"] = {"day": manager._local_day(), "count": 20, "optimization_count": 2}
    await tick(manager, wall[0])
    await advance(hass, manager, wall, budget)
    assert len(climate_calls(hass)) == 1
    assert manager.zone_command_counts["climate.home"]["optimization_count"] == 2


@pytest.mark.asyncio
async def test_existing_auto_with_high_surplus_does_not_turn_off_while_start_confirmation_runs(monkeypatch):
    _, hass, manager, wall, _ = solar(monkeypatch, mode="auto")
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert manager.zone_decisions["climate.home"].stage == "solar"
    assert not manager.solar_owned


@pytest.mark.asyncio
async def test_owned_confirmed_solar_auto_counts_one_shared_heatpump_meter_for_sustain_only(monkeypatch):
    _, hass, manager, wall, budget = solar(monkeypatch, zones=["climate.home", "climate.salon"])
    await tick(manager, wall[0])
    await advance(hass, manager, wall, budget)
    assert len(climate_calls(hass)) == 2
    wall[0] += 10
    refresh(hass, wall[0])
    for eid in manager.settings["zone_entities"]:
        report(hass, eid, "auto")
    budget.update(available_w=500., heatpump_w=1600., measured_wall=wall[0])
    await tick(manager, wall[0])
    assert manager.solar_owned == {"climate.home", "climate.salon"}
    # Both rooms share 2100 W; neither is credited another room's copy.
    assert all(d.stage == "solar" for d in manager.zone_decisions.values())
    await advance(hass, manager, wall, budget, 3590)
    assert len(climate_calls(hass)) == 2
    budget["heatpump_w"] = 1499.
    await advance(hass, manager, wall, budget, 1)
    assert [call[2]["hvac_mode"] for call in climate_calls(hass)] == ["auto", "auto", "off", "off"]


@pytest.mark.asyncio
@pytest.mark.parametrize("guard", ["unowned", "missing_meter", "pv_ceiling"])
async def test_sustain_cannot_invent_solar_power_from_unowned_or_unproven_hp_draw(monkeypatch, guard):
    _, hass, manager, wall, budget = solar(monkeypatch, mode="auto", watts=500.)
    budget["heatpump_w"] = 4000.
    if guard != "unowned":
        manager.solar_owned.add("climate.home")
        manager.state.expected_mode["climate.home"] = "auto"
    if guard == "missing_meter":
        budget["heatpump_meter_valid"] = False
    if guard == "pv_ceiling":
        budget["solar_ceiling_w"] = 1999.
    await tick(manager, wall[0])
    assert [call[2]["hvac_mode"] for call in climate_calls(hass)] == ["off"]


@pytest.mark.asyncio
async def test_sustain_preserves_import_in_the_compensated_budget(monkeypatch):
    _, hass, manager, wall, budget = solar(monkeypatch, mode="auto", watts=0.)
    manager.solar_owned.add("climate.home")
    manager.state.expected_mode["climate.home"] = "auto"
    # 1000 W net import and 2800 W HP draw leave only 1800 W real solar.
    budget.update(heatpump_w=2800., compensated_w=1800.)
    await tick(manager, wall[0])
    assert [call[2]["hvac_mode"] for call in climate_calls(hass)] == ["off"]


@pytest.mark.asyncio
async def test_hp_compensation_cannot_start_another_off_room_when_net_headroom_is_low(monkeypatch):
    _, hass, manager, wall, budget = solar(monkeypatch, watts=500., zones=["climate.home", "climate.salon"])
    report(hass, "climate.home", "auto")
    manager.solar_owned.add("climate.home")
    manager.state.expected_mode["climate.home"] = "auto"
    budget["heatpump_w"] = 3000.
    await tick(manager, wall[0])
    await advance(hass, manager, wall, budget)
    assert not climate_calls(hass)
    assert manager.zone_decisions["climate.home"].stage == "solar"
    assert manager.zone_decisions["climate.salon"].desired_mode == "off"


@pytest.mark.asyncio
async def test_real_runtime_solar_budget_releases_auto_and_honours_new_meter_settling(monkeypatch):
    runtime, hass, manager, wall = automatic(monkeypatch, zones=["climate.home"], temp=21.)
    runtime.settings["pv_entity"] = "sensor.pv"
    hass.states.set("sensor.pv", 4000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.grid", -2500, {"unit_of_measurement": "W"})
    await tick(manager, wall[0])
    assert manager._solar_budget["available_w"] == 2500.
    runtime.last_issued_wall = wall[0]
    wall[0] += 60
    # Re-reading the same pre-command reports cannot start solar AUTO.
    await tick(manager, wall[0])
    assert not climate_calls(hass)
    assert manager._solar_since is None
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    wall[0] += 60
    refresh(hass, wall[0])
    await tick(manager, wall[0])
    assert [call[2]["hvac_mode"] for call in climate_calls(hass)] == ["auto"]


@pytest.mark.asyncio
async def test_power_collapse_while_persisting_command_cancels_before_write(monkeypatch):
    runtime, hass, manager, wall, budget = solar(monkeypatch)
    await tick(manager, wall[0])
    saved = runtime.store.async_save

    async def change_headroom(data):
        await saved(data)
        budget["available_w"] = 2400.

    runtime.store.async_save = change_headroom
    await advance(hass, manager, wall, budget)
    assert not climate_calls(hass)
    assert not manager.pending_commands
    assert not manager.state.expected_mode


@pytest.mark.asyncio
async def test_second_zone_rechecks_current_surplus_after_first_cloud_write(monkeypatch):
    _, hass, manager, wall, budget = solar(monkeypatch, zones=["climate.home", "climate.salon"])
    await tick(manager, wall[0])
    call = hass.services.async_call

    async def consume_surplus(domain, service, data=None, **kwargs):
        result = await call(domain, service, data, **kwargs)
        if domain == "climate":
            budget["available_w"] = 2400.
        return result

    hass.services.async_call = consume_surplus
    await advance(hass, manager, wall, budget)
    assert [row[2]["entity_id"] for row in climate_calls(hass)] == ["climate.home"]
    assert list(manager.pending_commands) == ["climate.home"]


@pytest.mark.asyncio
async def test_reboot_preserves_confirmed_ownership_but_not_elapsed_start_confirmation(monkeypatch):
    runtime, hass, manager, wall, budget = solar(monkeypatch)
    await tick(manager, wall[0])
    saved = deepcopy(manager.snapshot())
    runtime.smart_climate = manager = SmartClimateManager(runtime)
    manager.settings.update(automatic_zone_control=True, solar_gain_enabled=False, zone_entities=["climate.home"])
    manager.restore(saved)
    await advance(hass, manager, wall, budget)
    assert not climate_calls(hass)
    await advance(hass, manager, wall, budget)
    assert len(climate_calls(hass)) == 1
    wall[0] += 10
    refresh(hass, wall[0])
    report(hass, "climate.home", "auto")
    budget.update(available_w=500., heatpump_w=1700., measured_wall=wall[0])
    await tick(manager, wall[0])
    saved = deepcopy(manager.snapshot())
    runtime.smart_climate = manager = SmartClimateManager(runtime)
    manager.settings.update(automatic_zone_control=True, solar_gain_enabled=False, zone_entities=["climate.home"])
    manager.restore(saved)
    await tick(manager, wall[0])
    assert manager.solar_owned == {"climate.home"}
    assert manager.zone_decisions["climate.home"].stage == "solar"


@pytest.mark.parametrize("damaged", [None, 123, {"climate.home": True}, "climate.home"])
def test_malformed_solar_ownership_cannot_restore_permission(monkeypatch, damaged):
    _, _, manager, _, _ = solar(monkeypatch)
    manager.restore({"expected_mode": {"climate.home": "auto"}, "solar_owned": damaged})
    assert manager.solar_owned == set()
