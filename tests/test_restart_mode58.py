"""Restart mode policy and safety boundaries against explicit HA doubles.

The scenarios exercise persisted user choices, real restart reconciliation,
and command admission. They do not run Home Assistant Core or real devices.
"""
from copy import deepcopy
import time

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.current_guide import GUIDE_VERSION
from custom_components.solar_pilot.runtime import SolarRuntime
from test_dishwasher import setup as dishwasher_setup
from test_electricity_sensor import sensor_class
from test_restart_auto47 import attempted_dishwasher, saved_lease
from test_restart_isolation53 import paired_runtime
from test_runtime import build


def commands(hass):
    return [call for call in hass.services.calls if call[0] != "persistent_notification"]


def reboot(runtime, hass):
    resumed = SolarRuntime(hass, runtime.entry)
    resumed.store.data = deepcopy(runtime.store.data)
    return resumed


@pytest.mark.asyncio
@pytest.mark.parametrize("cause", [None, "legacy", "user"])
async def test_saved_ordinary_pause_resumes_automatically_without_forcing_a_load(cause):
    runtime, hass = build()
    hass.states.set("sensor.grid", 500, {"unit_of_measurement": "W"})
    runtime.store.data = {"mode": "paused", "device_modes": {"a": "auto"}}
    if cause is not None:
        runtime.store.data["pause_cause"] = cause

    await runtime.start()

    assert runtime.auto_resume_after_restart is True
    assert runtime.mode == "solar" and runtime.restart_requested_mode is None
    assert runtime.pause_cause == "" and not runtime._restart_resume_from_pause
    assert runtime.store.data["mode"] == "solar"
    assert runtime.store.data["pause_cause"] == ""
    assert not commands(hass)


@pytest.mark.asyncio
async def test_saved_pause_only_starts_an_enabled_load_when_normal_solar_rules_allow_it():
    runtime, hass = build()
    runtime.store.data = {"mode": "paused", "device_modes": {"a": "auto"}}

    await runtime.start()
    await runtime.tick()

    assert runtime.mode == "solar"
    assert runtime.states["a"].owned and runtime.states["a"].on
    assert commands(hass) == [("switch", "turn_on", {"entity_id": "switch.load"})]


@pytest.mark.asyncio
@pytest.mark.parametrize("prior_store", [None, {}, {"mode": "observe"},
    {"mode": "observe", "restart_requested_mode": None, "device_modes": {"a": "auto"},
     "leases": {"a": {"watts": 1000, "name": "Testtoestel"}}}])
async def test_new_installation_or_saved_observation_is_not_automatic_activation(prior_store):
    runtime, hass = build()
    runtime.store.data = deepcopy(prior_store)

    await runtime.start()
    await runtime.tick()

    assert runtime.mode == "observe" and runtime.auto_resume_after_restart is True
    assert runtime.restart_requested_mode is None
    assert not commands(hass)


@pytest.mark.asyncio
async def test_explicit_disabled_policy_preserves_pause_through_two_restarts():
    runtime, hass = build()
    runtime.store.data = {"mode": "paused", "pause_cause": "user",
                          "auto_resume_after_restart": False, "device_modes": {"a": "auto"}}
    for _ in range(2):
        await runtime.start()
        await runtime.tick()
        assert runtime.mode == "paused" and runtime.pause_cause == "user"
        assert runtime.auto_resume_after_restart is False
        assert runtime.store.data["auto_resume_after_restart"] is False
        assert not commands(hass)
        runtime = reboot(runtime, hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["paused", "observe", "solar"])
@pytest.mark.parametrize("enabled", [True, False])
async def test_policy_toggle_is_durable_without_changing_live_mode_or_sending_commands(mode, enabled):
    runtime, hass = build()
    runtime.mode = mode
    runtime.pause_cause = "user" if mode == "paused" else ""
    before = len(runtime.store.saves)

    await runtime.set_auto_resume_after_restart(enabled)

    assert runtime.mode == mode and not commands(hass)
    assert runtime.auto_resume_after_restart is enabled
    assert len(runtime.store.saves) == before + 1
    assert runtime.store.data["auto_resume_after_restart"] is enabled
    assert runtime.store.data["mode"] == mode


@pytest.mark.asyncio
@pytest.mark.parametrize("malformed", [None, 0, 1, "true", "false", [], {}])
async def test_malformed_saved_policy_does_not_enable_pause_auto_resume(malformed):
    runtime, hass = build()
    runtime.store.data = {"mode": "paused", "auto_resume_after_restart": malformed,
                          "device_modes": {"a": "auto"}}

    await runtime.start()

    assert runtime.auto_resume_after_restart is False and runtime.mode == "paused"
    assert not commands(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("malformed", [None, 0, 1, "true", "false", [], {}])
async def test_policy_service_rejects_nonboolean_input_without_a_partial_save(malformed):
    runtime, hass = build()
    runtime.mode = "paused"

    with pytest.raises(HomeAssistantError, match="Aan of Uit"):
        await runtime.set_auto_resume_after_restart(malformed)

    assert runtime.mode == "paused" and runtime.auto_resume_after_restart is True
    assert not runtime.store.saves and not commands(hass)


@pytest.mark.asyncio
async def test_internal_exception_reason_survives_healthy_cycles_and_restart(monkeypatch):
    runtime, hass = build()
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    normal_tick = runtime._tick

    async def fail_once():
        raise RuntimeError("synthetic controller failure")

    monkeypatch.setattr(runtime, "_tick", fail_once)
    await runtime.tick()
    assert runtime.mode == "paused" and runtime.pause_cause == "internal_fault"
    assert runtime.store.data["pause_cause"] == "internal_fault"

    monkeypatch.setattr(runtime, "_tick", normal_tick)
    for _ in range(2):
        await runtime.tick()
        assert runtime.problem_kind == "internal_fault"
        assert runtime.problem == runtime.pause_reason
        assert runtime.mode == "paused" and not commands(hass)

    resumed = reboot(runtime, hass)
    await resumed.start()
    await resumed.tick()
    assert resumed.mode == "paused" and resumed.pause_cause == "internal_fault"
    assert resumed.problem_kind == "internal_fault"
    assert resumed.problem == resumed.pause_reason and "interne fout" in resumed.pause_reason
    assert not commands(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("cause", ["internal_fault", "command_fault", "removal", "unexpected_reason"])
async def test_protected_or_unrecognised_pause_cause_cannot_be_cleared_by_restart(cause):
    runtime, hass = build()
    runtime.store.data = {"mode": "paused", "pause_cause": cause,
                          "auto_resume_after_restart": True, "device_modes": {"a": "auto"}}

    await runtime.start()
    await runtime.tick()

    assert runtime.mode == "paused"
    assert runtime.pause_cause == ("internal_fault" if cause == "unexpected_reason" else cause)
    assert runtime.restart_requested_mode is None and not commands(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("cause", ["internal_fault", "command_fault", "removal"])
async def test_protected_pause_overrides_a_stale_saved_solar_resume_intent(cause):
    runtime, hass = build()
    runtime.store.data = {"mode": "observe", "pause_cause": cause,
                          "restart_requested_mode": "solar", "restart_resume_from_pause": True,
                          "auto_resume_after_restart": True, "device_modes": {"a": "auto"}}

    await runtime.start()

    assert runtime.mode == "paused" and runtime.pause_cause == cause
    assert runtime.restart_requested_mode is None and not runtime._restart_resume_from_pause
    assert not commands(hass)


@pytest.mark.asyncio
async def test_prepare_removal_persists_and_never_stops_a_running_dishwasher():
    runtime, hass, _cfg = dishwasher_setup()
    hass.states.set("sensor.dw_phase", "Running")
    runtime.store.data = saved_lease(runtime, watts=2000)
    await runtime.start()
    assert runtime.states["a"].owned and runtime.states["a"].on

    await runtime.prepare_removal()
    assert runtime.store.data["removal_requested"] is True
    assert runtime.store.data["pause_cause"] == "removal"
    resumed = reboot(runtime, hass)
    await resumed.start()
    await resumed.tick()

    assert resumed.removal_requested and resumed.mode == "paused"
    assert resumed.pause_cause == "removal"
    assert resumed.states["a"].owned and resumed.states["a"].on
    assert not resumed.removal_overview()["ready"]
    assert not commands(hass)


@pytest.mark.asyncio
async def test_removal_requested_flag_itself_blocks_resume_without_a_cause():
    runtime, hass = build()
    runtime.store.data = {"mode": "paused", "removal_requested": True,
                          "auto_resume_after_restart": True, "device_modes": {"a": "auto"}}

    await runtime.start()

    assert runtime.removal_requested and runtime.mode == "paused"
    assert not commands(hass)


@pytest.mark.asyncio
async def test_unconfirmed_start_is_reconciled_before_pause_auto_resume_and_never_replayed():
    runtime, hass = attempted_dishwasher(mode="paused")
    await runtime.start()

    assert runtime.mode == "observe" and runtime.restart_blocking
    assert runtime.pause_cause == "command_fault"
    assert runtime.restart_requested_mode == "paused"
    assert runtime.dishwasher.tickets["a"]["attempted"]
    assert not commands(hass)

    hass.states.set("sensor.dw_connection", "Connected")
    hass.states.set("sensor.dw_phase", "Idle")
    for _ in range(3):
        await runtime.tick()
    assert runtime.restart_blocking and runtime.dishwasher.tickets["a"]["attempted"]
    assert not commands(hass)

    hass.states.set("sensor.dw_phase", "Running")
    await runtime.tick()
    assert not runtime.restart_blocking and runtime.mode == "paused"
    assert runtime.pause_cause == "command_fault"
    assert runtime.states["a"].owned and runtime.states["a"].on
    assert not commands(hass)


@pytest.mark.asyncio
async def test_durable_unconfirmed_start_does_not_replay_across_two_restarts():
    runtime, hass = attempted_dishwasher(mode="paused")
    for _ in range(2):
        await runtime.start()
        await runtime.tick()
        assert runtime.restart_blocking and runtime.pause_cause == "command_fault"
        assert runtime.dishwasher.tickets["a"]["attempted"]
        assert not commands(hass)
        runtime = reboot(runtime, hass)


@pytest.mark.asyncio
async def test_unavailable_ordinary_load_is_isolated_while_another_load_resumes_after_pause():
    runtime, hass = paired_runtime()
    runtime.store.data.update(mode="paused", pause_cause="user")

    await runtime.start()
    await runtime.tick()

    assert runtime.mode == "solar" and not runtime.restart_blocking
    assert "a" in runtime.recovery and "a" in runtime.source_isolated_devices
    assert runtime.states["b"].owned and runtime.states["b"].on
    assert commands(hass) == [("switch", "turn_on", {"entity_id": "switch.healthy"})]


@pytest.mark.asyncio
async def test_user_pause_cancels_an_existing_delayed_pause_auto_resume(monkeypatch):
    runtime, hass = build()
    runtime.store.data = {"mode": "paused", "pause_cause": "user",
                          "device_modes": {"a": "auto"}}
    monkeypatch.setattr(runtime, "legacy_conflicts", lambda: [{"name": "Previous controller"}])
    await runtime.start()
    assert runtime.mode == "observe" and runtime.restart_requested_mode == "solar"
    assert runtime._restart_resume_from_pause and not commands(hass)

    await runtime.set_mode("paused")
    monkeypatch.setattr(runtime, "legacy_conflicts", lambda: [])
    await runtime.tick()

    assert runtime.mode == "paused" and runtime.pause_cause == "user"
    assert runtime.restart_requested_mode is None and not runtime._restart_resume_from_pause
    assert runtime.store.data["restart_requested_mode"] is None
    assert not commands(hass)


@pytest.mark.asyncio
async def test_disabling_policy_cancels_delayed_pause_resume_without_changing_current_mode(monkeypatch):
    runtime, hass = build()
    runtime.store.data = {"mode": "paused", "pause_cause": "user",
                          "device_modes": {"a": "auto"}}
    monkeypatch.setattr(runtime, "legacy_conflicts", lambda: [{"name": "Previous controller"}])
    await runtime.start()
    assert runtime.mode == "observe" and runtime._restart_resume_from_pause

    await runtime.set_auto_resume_after_restart(False)
    assert runtime.mode == "observe" and runtime.restart_requested_mode is None
    assert not runtime._restart_resume_from_pause
    monkeypatch.setattr(runtime, "legacy_conflicts", lambda: [])
    await runtime.tick()

    assert runtime.mode == "observe" and not commands(hass)
    resumed = reboot(runtime, hass)
    await resumed.start()
    assert resumed.mode == "observe" and resumed.auto_resume_after_restart is False
    assert not commands(hass)


@pytest.mark.asyncio
async def test_disabled_policy_cancels_an_interrupted_durable_pause_resume_before_starting():
    runtime, hass = build()
    runtime.store.data = {"mode": "observe", "pause_cause": "user",
                          "restart_requested_mode": "solar", "restart_resume_from_pause": True,
                          "auto_resume_after_restart": False, "device_modes": {"a": "auto"}}

    await runtime.start()

    assert runtime.mode == "paused" and runtime.restart_requested_mode is None
    assert runtime.pause_cause == "user" and not runtime._restart_resume_from_pause
    assert not commands(hass)


@pytest.mark.asyncio
async def test_status_sensor_reports_policy_entity_and_persistent_pause_reason(monkeypatch):
    runtime, hass = build()
    runtime.store.data = {"mode": "paused", "pause_cause": "internal_fault"}
    await runtime.start()
    monkeypatch.setattr(runtime, "entity_id", lambda domain, suffix, *args: f"{domain}.{suffix}")
    cls = sensor_class()
    cls.extra_state_attributes.fget.__globals__["GUIDE_VERSION"] = GUIDE_VERSION
    attrs = cls(runtime, "status", "Status").extra_state_attributes

    assert attrs["mode"] == "paused"
    assert attrs["auto_resume_after_restart"] is True
    assert attrs["auto_resume_after_restart_entity"] == "switch.auto_resume_after_restart"
    assert attrs["pause_cause"] == "internal_fault"
    assert attrs["pause_reason"] == runtime.pause_reason
    assert attrs["problem_kind"] == "internal_fault"
    assert attrs["restart_requested_mode"] is None
    assert not commands(hass)


def put_fault(runtime, data, kind):
    """Supply a genuine module fault using its native persisted journal shape."""
    reason = "Geen opdrachtbevestiging; controle nodig"
    if kind == "ordinary":
        data["faults"] = {"a": reason}
    elif kind == "battery":
        data["battery_fleet"] = {"faults": {"restart": reason}}
    return reason


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["ordinary", "battery"])
async def test_persisted_pause_resume_queue_rechecks_all_actual_module_faults(kind):
    runtime, hass = build()
    runtime.entry.options["_beta37_activation_profile"] = 1
    data = {"mode": "observe", "pause_cause": "user", "device_modes": {"a": "auto"},
            "auto_resume_after_restart": True, "restart_requested_mode": "solar",
            "restart_resume_from_pause": True}
    put_fault(runtime, data, kind)
    runtime.store.data = data

    await runtime.start()
    await runtime.tick()

    assert runtime.mode == "paused" and runtime.pause_cause == "command_fault"
    assert runtime.restart_requested_mode is None and not runtime._restart_resume_from_pause
    assert runtime.store.data["pause_cause"] == "command_fault"
    assert runtime.store.data["restart_resume_from_pause"] is False
    assert not commands(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["ordinary", "battery"])
async def test_deferred_pause_resume_is_cancelled_if_a_fault_arrives_before_final_retry(kind, monkeypatch):
    runtime, hass = build()
    runtime.store.data = {"mode": "paused", "pause_cause": "user", "device_modes": {"a": "auto"}}
    monkeypatch.setattr(runtime, "legacy_conflicts", lambda: [{"name": "Previous controller"}])
    await runtime.start()
    assert runtime.restart_requested_mode == "solar" and runtime._restart_resume_from_pause
    reason = "Nieuwe opdrachtfout tijdens opstartcontrole"
    if kind == "ordinary":
        runtime.faults["a"] = reason
    elif kind == "battery":
        runtime.battery_fleet.state.faults["restart"] = reason
    monkeypatch.setattr(runtime, "legacy_conflicts", lambda: [])

    await runtime._retry_restart_recovery(time.monotonic())
    await runtime.tick()

    assert runtime.mode == "paused" and runtime.pause_cause == "command_fault"
    assert runtime.restart_requested_mode is None and not runtime._restart_resume_from_pause
    assert runtime.store.data["pause_cause"] == "command_fault"
    assert runtime.store.data["mode"] == "paused"
    assert not commands(hass)


@pytest.mark.asyncio
async def test_internal_fault_stays_visible_if_the_immediate_fault_save_also_fails(monkeypatch):
    runtime, hass = build()
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"

    async def controller_failure():
        raise RuntimeError("synthetic controller failure")

    async def storage_failure(_data):
        raise OSError("synthetic disk write failure")

    monkeypatch.setattr(runtime, "_tick", controller_failure)
    monkeypatch.setattr(runtime.store, "async_save", storage_failure)
    await runtime.tick()

    assert runtime.mode == "paused" and runtime.pause_cause == "internal_fault"
    assert runtime.problem_kind == "internal_fault" and "Interne fout" in runtime.problem
    assert runtime.restart_requested_mode is None and not runtime._restart_resume_from_pause
    assert not commands(hass)


@pytest.mark.asyncio
async def test_read_only_analysis_export_includes_the_actual_restart_policy_and_pause_cause():
    runtime, hass = build()
    runtime.store.data = {"mode": "paused", "pause_cause": "internal_fault",
                          "auto_resume_after_restart": True}
    await runtime.start()
    before = (runtime.mode, runtime.pause_cause, runtime.restart_requested_mode, list(hass.services.calls))

    report = runtime.analysis.build(include_names=True)

    last = report["telemetry"]["fast"][-1]
    assert last["mode"] == "paused" and last["pause_cause"] == "internal_fault"
    assert last["auto_resume_after_restart"] is True and last["restart_requested_mode"] is None
    assert last["problem_kind"] == "internal_fault"
    assert before == (runtime.mode, runtime.pause_cause, runtime.restart_requested_mode, hass.services.calls)


@pytest.mark.asyncio
@pytest.mark.parametrize("arrival", ["persisted", "during_retry"])
async def test_transient_climate_source_wait_does_not_block_an_independent_load(arrival, monkeypatch):
    runtime, hass = build()
    data = {"mode": "observe", "pause_cause": "user", "device_modes": {"a": "auto"},
            "restart_requested_mode": "solar", "restart_resume_from_pause": True,
            "auto_resume_after_restart": True}
    reason = "Actuele buitentemperatuur ontbreekt of is te oud"
    if arrival == "persisted":
        data["smart_climate"] = {"fault": reason}
    else:
        monkeypatch.setattr(runtime, "legacy_conflicts", lambda: [{"name": "Previous controller"}])
    runtime.store.data = data
    await runtime.start()
    if arrival == "during_retry":
        assert runtime.mode == "observe" and runtime._restart_resume_from_pause
        runtime.panasonic_archive.setdefault("backup_store", {})["smart_climate"] = {"fault": reason}
        monkeypatch.setattr(runtime, "legacy_conflicts", lambda: [])
    await runtime.tick()
    await runtime.tick()

    assert runtime.mode == "solar" and runtime.pause_cause == ""
    assert runtime.panasonic_archive["backup_store"]["smart_climate"]["fault"] == reason
    assert runtime.states["a"].owned and runtime.states["a"].on
    assert commands(hass) == [("switch", "turn_on", {"entity_id": "switch.load"})]


@pytest.mark.asyncio
@pytest.mark.parametrize("cause", ["internal_fault", "command_fault"])
async def test_explicit_safe_review_clears_the_protected_cause_without_enabling_auto(cause):
    runtime, hass = build()
    runtime.store.data = {"mode": "paused", "pause_cause": cause, "device_modes": {"a": "auto"}}
    if cause == "command_fault":
        runtime.store.data["faults"] = {"a": "Geen opdrachtbevestiging"}
    await runtime.start()
    assert runtime.mode == "paused" and runtime.pause_cause == cause

    await runtime.reset()

    assert runtime.mode == "paused" and runtime.pause_cause == "user"
    assert runtime.problem_kind != "internal_fault" and not runtime.faults
    assert runtime.store.data["pause_cause"] == "user"
    assert runtime.store.data["mode"] == "paused"
    assert any("Foutpauze gecontroleerd" in row["message"] for row in runtime.logs)
    assert not commands(hass)
