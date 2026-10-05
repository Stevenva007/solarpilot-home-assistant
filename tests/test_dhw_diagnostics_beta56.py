"""Explain real command gates and the inclusive surplus boundary with HA doubles."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import time
from zoneinfo import ZoneInfo
from types import SimpleNamespace

import pytest

from test_dhw_runtime import setup, tick, updates
from test_dishwasher_priority32 import running_aeg_with_boiler


TZ = ZoneInfo("Europe/Brussels")
DAY = datetime(2026, 10, 6, 12, tzinfo=TZ)


def gates(manager):
    return {g["code"]: g for g in manager.overview()["execution"]["gates"]}


@pytest.mark.asyncio
@pytest.mark.parametrize("surplus,requested", [(2999.9, False), (3000, True), (3150, True)])
async def test_full_runtime_accepts_3000_measured_surplus_without_requiring_estimated_3200(surplus, requested):
    runtime, hass = setup(config={"night_enabled": False, "estimated_heat_power_w": 3200})
    runtime.settings["reserve_w"] = 150
    hass.states.set("sensor.grid", -surplus, {"unit_of_measurement": "W"})
    await runtime.tick()
    calls = [c for c in hass.services.calls if c[0] == "water_heater"]
    assert bool(calls) is requested
    assert runtime.dhw.settings["surplus_threshold_w"] == 3000
    assert runtime.dhw.settings["estimated_heat_power_w"] == 3200
    assert runtime.dhw.settings["max_surplus_import_w"] == 100
    assert gates(runtime.dhw)["surplus"]["start_threshold_w"] == 3000
    if requested:
        assert calls[0][2]["temperature"] == 60
    else:
        assert runtime.dhw.execution["code"] == "surplus"
        assert "3000 W" in runtime.dhw.status


@pytest.mark.asyncio
async def test_full_runtime_accepts_exactly_3000_after_existing_aeg_reservations(monkeypatch):
    runtime, hass, _, _ = await running_aeg_with_boiler(monkeypatch, 5150)
    assert runtime.dhw.reading.luxury_allowed
    assert runtime.dhw.execution["priority_allocation"]["usable_surplus_w"] == 3000
    assert [c[2]["temperature"] for c in hass.services.calls if c[0] == "water_heater"] == [60]


@pytest.mark.asyncio
@pytest.mark.parametrize("old,expected", [(3500, 3000), (2800, 2800), (4000, 4000)])
async def test_threshold_migration_preserves_custom_values_and_all_other_choices(old, expected):
    runtime, hass = setup(config={"surplus_threshold_w": old, "rise_delay_s": 60,
                                  "cooling_clear_s": 600, "enabled": False})
    before = deepcopy(runtime.dhw.settings)
    assert await runtime.dhw.migrate_beta56()
    after = runtime.entry.options["dhw"]
    assert after["surplus_threshold_w"] == expected
    assert after["surplus_threshold_migration"] == 56
    assert {k: after[k] for k in before if k != "surplus_threshold_w"} == {
        k: v for k, v in before.items() if k != "surplus_threshold_w"}
    assert not hass.services.calls
    assert not await runtime.dhw.migrate_beta56()


@pytest.mark.asyncio
async def test_later_explicit_3500_choice_is_not_remigrated():
    runtime, hass = setup(config={"surplus_threshold_w": 3500})
    await runtime.dhw.migrate_beta56()
    runtime.dhw.settings["surplus_threshold_w"] = 3500
    runtime.dhw._persist_canonical()
    assert not await runtime.dhw.migrate_beta56()
    assert runtime.entry.options["dhw"]["surplus_threshold_w"] == 3500
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_monday_hygiene_primary_reason_has_end_time_and_does_not_claim_native60_ownership():
    runtime, hass = setup(config={"hygiene_schedule_enabled": True})
    updates(hass, "water_heater.boiler", temperature=60)
    hass.states.set("sensor.water", 49, {"unit_of_measurement": "°C"})
    await runtime.dhw.tick(time.monotonic(), -4527, True, 0,
                           local_now=datetime(2026, 10, 5, 14, 40, tzinfo=TZ))
    view = runtime.dhw.overview()
    assert view["execution"]["code"] == "protection"
    assert gates(runtime.dhw)["protection"]["until"] == "2026-10-05T15:00:00+02:00"
    assert "15:00" in view["status"]
    assert view["execution"]["actual_target_c"] == 60
    assert view["execution"]["temperature_c"] == 49
    assert view["execution"]["proposed_target_c"] is None
    assert view["execution"]["heating_evidence"]["reported_heating"] is None
    assert not view["solar_pilot_owns_target"]
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_serialized_mature_boost_has_specific_runtime_reason_and_source_evidence():
    runtime, hass = setup()
    await runtime.dhw.tick(time.monotonic(), -3000, True, 0, allow_command=False,
                           local_now=DAY, dispatch_block_code="battery_pending",
                           dispatch_block_reason="Wacht op bevestiging batterijopdracht")
    execution = runtime.dhw.execution
    assert execution["code"] == "battery_pending"
    assert execution["reason"] == runtime.dhw.status == "Wacht op bevestiging batterijopdracht"
    assert execution["proposed_target_c"] == 60
    assert execution["actual_target_c"] == 50
    assert not gates(runtime.dhw)["dispatch"]["passed"]
    assert execution["source_evidence"]["target"]["age_s"] is not None
    assert execution["source_evidence"]["cooling"][0]["hvac_action"] == "idle"
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_runtime_exit_refreshes_evidence_without_advancing_stability_or_writing():
    runtime, hass = setup(config={"rise_delay_s": 60})
    await runtime.dhw.tick(1000, -4000, True, 0, local_now=DAY)
    before = (runtime.dhw.policy.candidate, runtime.dhw.policy.candidate_since,
              runtime.dhw.policy.last_sample)
    hass.states.set("sensor.water", 48, {"unit_of_measurement": "°C"})
    runtime.dhw.diagnose_runtime_block(1060, -3000, True, 0, local_now=DAY+timedelta(minutes=1),
                                       code="runtime_fault", reason="Regelcyclus afgebroken door fout")
    assert runtime.dhw.execution["code"] == "runtime_fault"
    assert runtime.dhw.execution["temperature_c"] == 48
    assert runtime.dhw.execution["source_evidence"]["temperature"]["state"] == "48"
    assert before == (runtime.dhw.policy.candidate, runtime.dhw.policy.candidate_since,
                      runtime.dhw.policy.last_sample)
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("block,code", [("cooling", "cooling"), ("stale_temperature", "temperature"),
                                        ("manual", "protection"), ("threshold", "surplus")])
async def test_all_evaluated_safety_gates_remain_visible_without_commands(block, code):
    runtime, hass = setup()
    grid = -4000
    if block == "cooling":
        hass.states.set("climate.home", "auto", {"hvac_action": "cooling"})
    elif block == "stale_temperature":
        hass.states.set("sensor.water", 49, {"unit_of_measurement": "°C"}, reported_age=600)
    elif block == "manual":
        hass.states.set("switch.powerful", "on")
    else:
        grid = -2999
    await runtime.dhw.tick(time.monotonic(), grid, True, 0, local_now=DAY)
    assert not gates(runtime.dhw)[code]["passed"]
    assert code in runtime.dhw.execution["blocking_gates"]
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_stability_explanation_counts_down_once_then_requests_same_target(monkeypatch):
    runtime, hass = setup(config={"rise_delay_s": 60, "optional_raise_interval_s": 0})
    wall = [time.time()]
    monkeypatch.setattr(time, "time", lambda: wall[0])
    for elapsed in range(0, 66, 5):
        if elapsed:
            wall[0] += 5
        for obj in hass.states.data.values():
            obj.last_reported = datetime.fromtimestamp(wall[0], timezone.utc)
        await runtime.dhw.tick(1000+elapsed, -3000, True, 0,
                               local_now=DAY+timedelta(seconds=elapsed))
        assert gates(runtime.dhw)["stability"]["remaining_s"] == max(0, 60-elapsed)
        if elapsed < 60:
            assert runtime.dhw.execution["code"] == "stability"
    assert [c[2]["temperature"] for c in hass.services.calls if c[0] == "water_heater"] == [60]


@pytest.mark.asyncio
@pytest.mark.parametrize("report", ["bad", False, SimpleNamespace(timestamp=lambda: float("nan")),
                                    SimpleNamespace(timestamp=lambda: float("inf")),
                                    SimpleNamespace(timestamp=lambda: True),
                                    SimpleNamespace(timestamp=lambda: "123")])
async def test_invalid_explicit_report_stamp_is_a_missing_source_not_a_crashed_cycle(report):
    runtime, hass = setup()
    hass.states.get("sensor.water").last_reported = report
    await runtime.dhw.tick(time.monotonic(), -4000, True, 0, local_now=DAY)
    assert runtime.dhw.reading.temperature_c is None
    assert not gates(runtime.dhw)["temperature"]["passed"]
    assert runtime.dhw.execution["source_evidence"]["temperature"]["age_s"] is None
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_absent_report_stamp_uses_valid_last_updated_without_renewing_invalid_report():
    runtime, hass = setup()
    hass.states.get("sensor.water").last_reported = None
    await runtime.dhw.tick(time.monotonic(), -2999, True, 0, local_now=DAY)
    assert runtime.dhw.reading.temperature_c == 44
    assert gates(runtime.dhw)["temperature"]["passed"]
    assert not hass.services.calls


def test_diagnostic_refresh_failure_keeps_original_runtime_reason(monkeypatch):
    runtime, hass = setup()
    monkeypatch.setattr(runtime.dhw, "_prepare_comfort", lambda *_: (_ for _ in ()).throw(ValueError("bad source")))
    runtime.dhw.diagnose_runtime_block(1000, -4000, True, 0, local_now=DAY,
                                       code="runtime_fault", reason="Oorspronkelijke regelcyclusfout")
    assert runtime.dhw.execution["reason"] == "Oorspronkelijke regelcyclusfout"
    assert runtime.dhw.execution["evidence_refresh_error"] == "ValueError"
    assert runtime.dhw.execution["temperature_c"] is None
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_requested_pending_and_confirmed_change_keep_original_command_reason():
    runtime, hass = setup()
    hass.services.respond = False
    await runtime.dhw.tick(time.monotonic(), -3000, True, 0, local_now=DAY)
    original_reason = runtime.dhw.pending["reason"]
    assert original_reason == runtime.dhw.policy.result.reason
    assert original_reason in runtime.dhw.execution["reason"]
    assert runtime.dhw.execution["last_change"] is None

    await runtime.dhw.tick(time.monotonic(), -3000, True, 0, local_now=DAY)
    assert runtime.dhw.execution["code"] == "pending"
    assert original_reason in runtime.dhw.execution["reason"]
    updates(hass, "water_heater.boiler", temperature=60)
    await runtime.dhw.tick(time.monotonic(), -3000, True, 0, local_now=DAY)
    assert runtime.dhw.last_success["reason"] == original_reason
    change = runtime.dhw.execution["last_change"]
    assert change["at"] == runtime.dhw.last_success["time"]
    assert change["target_c"] == 60 and change["confirmed"]
    assert change["source"] == "solarpilot"
    assert original_reason in change["reason"] and "geen opwarmbewijs" in change["reason"]


@pytest.mark.asyncio
async def test_restart_reconciles_original_reason_without_repeating_command():
    from test_dhw_restart47 import restart, report

    runtime, hass = setup()
    hass.services.respond = False
    await runtime.dhw.tick(time.monotonic(), -3000, True, 0, local_now=DAY)
    original_reason = runtime.dhw.pending["reason"]
    original_calls = list(hass.services.calls)
    manager = restart(runtime, owned=60, pending=runtime.dhw.snapshot()["pending"])
    assert manager.restart_recovery["pending"]["reason"] == original_reason
    report(hass, 60)
    await manager.tick(time.monotonic(), -3000, True, 0, local_now=DAY)
    assert manager.last_success["confirmation"] == "restart_ha_state"
    assert manager.last_success["reason"] == original_reason
    assert original_reason in manager.execution["last_change"]["reason"]
    assert hass.services.calls == original_calls


def test_old_confirmation_does_not_invent_original_reason_and_other_binding_drops_it():
    runtime, _ = setup()
    from custom_components.solar_pilot.dhw_runtime import DHWManager

    old = {"target_c": 60, "time": DAY.isoformat(), "confirmation": "ha_state"}
    runtime.dhw.last_success = old
    change = runtime.dhw._last_confirmed_target_change()
    assert change["reason"] == "Boilerdoel 60 °C teruggelezen in Home Assistant (geen opwarmbewijs)"
    assert old.get("reason") is None
    snapshot = runtime.dhw.snapshot()
    snapshot["target_entity"] = "water_heater.other"
    restored = DHWManager(runtime)
    restored.restore(snapshot)
    assert restored._last_confirmed_target_change() is None
