"""Tariff budget, physical SG gates and credited-solar boundary regressions."""
from dataclasses import replace
from datetime import datetime
import json
import shutil
import subprocess
import time

import pytest

from custom_components.solar_pilot.ems import capacity_decision
from test_general_sg_policy64 import ended, observe
from test_sg_budget_priority62 import configured
from test_sg_controller62 import fixture
from test_sg_ui_platforms62 import CARD, attributes, execute, text


def near_quarter_end(runtime, grid):
    runtime.capacity_settings.update(enabled=True, target_peak_w=6000, margin_w=100)
    runtime.capacity = capacity_decision(datetime(2026, 1, 1, 12, 14, 59),
        1000, 6000, grid, runtime.capacity_settings)


def test_large_remaining_quarter_budget_never_enlarges_fixed_import_room():
    runtime, hass = configured(export=0)
    runtime.settings["max_import_w"] = 3500
    hass.states.set("sensor.grid", 2000, {"unit_of_measurement": "W"})
    near_quarter_end(runtime, 2000)
    assert runtime.capacity.allowed_grid_w > 1_000_000
    view = runtime.electrical_limits_overview()
    assert view["quarter_theoretical_headroom_w"] > 1_000_000
    assert view["fixed_import_headroom_w"] == view["instantaneous_headroom_w"] == 1500
    allowed, reason = runtime.heat_pump_increase_allowed()
    assert not allowed and reason.startswith("Netgrens:")
    assert "3200 W extra" in reason and "1500 W beschikbaar" in reason
    assert not runtime.sg_dispatch_allowed()
    assert not hass.services.calls


def test_phase_and_quarter_limits_remain_independent_smaller_constraints():
    runtime, _ = configured(export=5000)
    near_quarter_end(runtime, -5000)
    runtime.phase_settings.update(enabled=True, control_starts=True)
    runtime.phase = replace(runtime.phase, enabled=True, valid=True,
        block_increase=False, headroom_w=2500)
    view = runtime.electrical_limits_overview()
    assert view["instantaneous_headroom_w"] == 2500
    allowed, reason = runtime.heat_pump_increase_allowed()
    assert not allowed and reason.startswith("Fasegrens:") and "2500 W" in reason
    runtime.phase = replace(runtime.phase, headroom_w=5000)
    runtime.capacity = replace(runtime.capacity, allowed_grid_w=-3000, optional_headroom_w=0)
    view = runtime.electrical_limits_overview()
    assert view["instantaneous_headroom_w"] == 2000
    allowed, reason = runtime.heat_pump_increase_allowed()
    assert not allowed and reason.startswith("Kwartierbudget:") and "2000 W" in reason


def test_phase_start_block_cannot_be_displayed_as_permitted_positive_room():
    runtime, _ = configured(export=5000)
    runtime.phase_settings.update(enabled=True, control_starts=True)
    runtime.phase = replace(runtime.phase, enabled=True, valid=True,
        block_increase=True, headroom_w=5000)
    view = runtime.electrical_limits_overview()
    assert view["phase_headroom_w"] == 5000
    assert view["phase_increase_blocked"] and view["instantaneous_headroom_w"] == 0


def protected_ev(runtime, hass):
    runtime.settings["max_import_w"] = 3500
    runtime.wallbox_settings.update(enabled=True, power_entity="sensor.ev_power",
        status_entity="sensor.ev_status", mode_entity="select.ev_mode",
        trust_solar_setting=True, stable_s=0)
    hass.states.set("sensor.ev_power", 2000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.ev_status", "Charging")
    hass.states.set("select.ev_mode", "full_solar")
    runtime.wallbox_guard = runtime._make_wallbox_guard()
    runtime.sg_wallbox_guard = runtime._make_sg_wallbox_guard()
    grid, _, discharge, _, _ = runtime._site_data()
    reading = runtime._wallbox_reading()
    runtime.wallbox_guard.update(time.monotonic(), reading, grid, 150, discharge)
    runtime.sg_wallbox_guard.update(time.monotonic(), reading, grid, 150, discharge)


def test_solar_credited_hp_never_inherits_house_first_ev_takeover_rights():
    runtime, hass = configured(export=1000)
    protected_ev(runtime, hass)
    assert runtime.others_first
    assert runtime.wallbox_guard.result.max_increase_w == 2850
    assert runtime.sg_wallbox_guard.result.max_increase_w == 850
    assert runtime.electrical_limits_overview()["sg_eligible_solar_w"] >= 3000
    allowed, reason = runtime.heat_pump_increase_allowed()
    assert not allowed and reason.startswith("Wallbox heeft voorrang:")
    assert "850 W" in reason and not runtime.sg_dispatch_allowed()
    assert not hass.services.calls


def test_final_sg_dispatch_rechecks_ev_source_even_after_a_good_guard_result():
    runtime, hass = configured(export=5000)
    protected_ev(runtime, hass)
    assert runtime.sg_dispatch_allowed()
    hass.states.set("sensor.ev_power", 2000, {"unit_of_measurement": "W"}, age=301)
    assert not runtime.sg_dispatch_allowed()
    assert not hass.services.calls


def test_confirmed_idle_ev_does_not_reserve_fictional_charging_capacity():
    runtime, hass = configured(export=1000)
    protected_ev(runtime, hass)
    hass.states.set("sensor.ev_power", 0, {"unit_of_measurement": "W"})
    hass.states.set("sensor.ev_status", "Ready")
    # Even when the effective session source is unavailable, fresh native Ready
    # plus zero draw confirms no request and must retain the existing freedom.
    hass.states.set("select.ev_mode", "unavailable")
    reading = runtime._wallbox_reading()
    runtime.wallbox_guard.update(time.monotonic(), reading, -1000, 150)
    runtime.sg_wallbox_guard.update(time.monotonic(), reading, -1000, 150)
    assert runtime.sg_wallbox_guard.result.state == "idle"
    assert runtime.sg_wallbox_guard.result.max_increase_w is None
    assert runtime.heat_pump_increase_allowed()[0]
    assert runtime.sg_dispatch_allowed()


@pytest.mark.parametrize("mode", ["unknown", "manual", "stopped"])
def test_active_ev_unconfirmed_session_still_gets_actual_residual_priority(mode):
    runtime, hass = configured(export=1000)
    protected_ev(runtime, hass)
    reading = replace(runtime._wallbox_reading(), mode=mode)
    result = runtime._update_sg_wallbox_guard(time.monotonic(), reading, -1000, 150)
    assert result.max_increase_w == 850
    assert runtime.sg_wallbox_guard.reading.mode is None
    assert not runtime.heat_pump_increase_allowed()[0]


@pytest.mark.asyncio
async def test_ordinary_command_invalidates_sg_ev_window_and_requires_new_ev_report():
    from custom_components.solar_pilot.engine import Action
    runtime, hass = configured(export=5000)
    protected_ev(runtime, hass)
    assert runtime.sg_wallbox_guard.history
    ev_stamp = runtime.sg_wallbox_guard.reading.stamp
    await runtime._send(Action("a", 0, "Fixture: pauzeer gewone last"), time.monotonic())
    assert not runtime.sg_wallbox_guard.history
    assert runtime.sg_wallbox_guard.last_action_wall > ev_stamp
    assert not runtime.sg_dispatch_allowed()


def test_committed_loads_reduce_current_room_without_becoming_available_solar():
    runtime, _ = configured(export=5000)
    runtime.states["a"].target_w = 1700
    runtime.states["a"].measured_w = 1000
    view = runtime.electrical_limits_overview()
    assert view["committed_reserve_w"] == 700
    assert view["fixed_import_headroom_w"] == view["instantaneous_headroom_w"] == 4800


@pytest.mark.parametrize("invalid", ["grid", "pv", "phase", "quarter"])
def test_unknown_sources_do_not_display_zero_or_a_power_permission(invalid):
    runtime, hass = configured(export=5000)
    if invalid in ("grid", "pv"):
        hass.states.set("sensor.grid" if invalid == "grid" else "sensor.public_pv",
            5000, {"unit_of_measurement": "W"}, age=121)
    elif invalid == "phase":
        runtime.phase_settings.update(enabled=True, control_starts=True)
        runtime.phase = replace(runtime.phase, enabled=True, valid=False)
    else:
        runtime.capacity_settings["enabled"] = True
        runtime.capacity = replace(runtime.capacity, enabled=True, valid=False)
    view = runtime.electrical_limits_overview()
    assert view["source_valid"] is False and view["instantaneous_headroom_w"] is None


@pytest.mark.asyncio
async def test_concrete_live_electrical_reason_reaches_sg_block_without_contact_write():
    manager, adapter, _, _ = fixture()
    reason = "Netgrens: SG vraagt 3200 W extra; nu 1500 W beschikbaar binnen 3500 W netafname"
    await manager.tick(surplus_w=4000, data_fresh=True, phase_allowed=False,
        electrical_reason=reason)
    assert manager.reason == reason and manager.overview()["blocked_reasons"] == [reason]
    assert not adapter.calls


@pytest.mark.asyncio
async def test_start_uses_eligible_solar_but_keeps_rearm_observation_at_real_export():
    manager, adapter, clock, _ = fixture()
    await manager.tick(surplus_w=4000, real_surplus_w=500, solar_stamp=clock(),
        data_fresh=True, phase_allowed=True)
    assert manager._solar_observation["watts"] == 500
    clock.advance(manager.settings["start_delay_s"])
    await manager.tick(surplus_w=4000, real_surplus_w=500, solar_stamp=clock(),
        data_fresh=True, phase_allowed=True)
    assert adapter.calls == [("on", manager.settings["lease_s"])]
    assert manager._solar_observation["watts"] == 500


@pytest.mark.asyncio
async def test_ongoing_hp_solar_credit_does_not_create_new_solar_episode():
    manager, adapter, clock, _, row = await ended()
    clock.advance(900)
    await observe(manager, clock, row, surplus=4000, real_surplus_w=0)
    clock.advance(300)
    await observe(manager, clock, row, surplus=4000, real_surplus_w=0)
    assert manager._general_reference["solar_reset_stamp"] == clock()
    for _ in range(3):
        clock.advance(300)
        await observe(manager, clock, row, surplus=4000, real_surplus_w=1000)
    assert manager.completion_hold and len(adapter.calls) == 2
    assert manager._last_rearm is None


@pytest.mark.parametrize("residual", [-1, float("nan"), True])
@pytest.mark.asyncio
async def test_invalid_real_export_cannot_be_substituted_by_eligible_solar(residual):
    manager, adapter, clock, _ = fixture()
    for _ in range(2):
        await manager.tick(surplus_w=4000, real_surplus_w=residual,
            data_fresh=True, phase_allowed=True)
        clock.advance(1000)
    assert not adapter.calls and manager._solar_observation is None


def electrical_fixture(age=0):
    return {"observed_at": time.time(), "source_observed_at": time.time() - age,
        "source_stale_s": 120, "source_valid": True, "quarter_enabled": True,
        "quarter_theoretical_headroom_w": 100000,
        "instantaneous_headroom_w": 1500, "fixed_import_limit_w": 3500,
        "sg_solar_valid": True, "sg_solar_observed_at": time.time() - age,
        "sg_eligible_solar_w": 4000, "sg_hp_solar_w": 3500, "sg_residual_solar_w": 500}


def test_sg_details_separate_threshold_solar_real_export_and_physical_room():
    data = attributes()
    data["ems"] = {"electrical_limits": electrical_fixture()}
    rendered = text(execute(data)["initial"])
    for expected in ("Zonnevermogen voor SG-drempel", "Warmtepompbijdrage aan startdrempel",
            "Resterende vrije zonnestroom", "Elektrische ruimte nu", "Theoretisch kwartierbudget"):
        assert expected in rendered
    assert "4 kW" in rendered and "500 W" in rendered and "1,5 kW" in rendered
    assert "verruimt de vaste net- en fasegrenzen nooit" in rendered


def test_expired_electrical_snapshot_does_not_keep_claiming_current_room():
    data = attributes()
    data["ems"] = {"electrical_limits": electrical_fixture(age=121)}
    rendered = text(execute(data)["initial"])
    assert "Elektrische ruimte nu —" in rendered
    assert "Zonnevermogen voor SG-drempel —" in rendered
    assert "1,5 kW" not in rendered and "4 kW" not in rendered


def test_electrical_expiry_changes_refresh_signature_without_hp_sources_or_ha_event():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for shipped-card execution")
    now = time.time()
    data = {"ems": {"electrical_limits": electrical_fixture()}}
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const RealDate=Date;let offset=0;
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},
 Date:class extends RealDate{static now(){return (input.now+offset)*1000;}}};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
const card=vm.runInContext('Object.create(SolarPilotCard.prototype)',sandbox);
card._last={attributes:input.attributes};card._busy=false;
card._hass={states:{},config:{time_zone:'Europe/Brussels'}};
const before=card._heatpumpDisplaySignature(card._ctx());
offset=121;
const after=card._heatpumpDisplaySignature(card._ctx());
const electrical=card._electricalLimits(card._ctx());
process.stdout.write(JSON.stringify({before,after,electrical}));
"""
    result = subprocess.run([node, "-e", script, str(CARD)], input=json.dumps(
        {"attributes": data, "now": now}), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    result = json.loads(result.stdout)
    assert result["before"] != result["after"]
    assert result["electrical"]["instantaneous_headroom_w"] is None
    assert result["electrical"]["sg_eligible_solar_w"] is None
