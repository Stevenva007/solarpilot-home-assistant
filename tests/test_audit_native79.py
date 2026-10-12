"""Fictional native/SG audit regressions; no physical acceptance claims."""
from copy import deepcopy

import pytest

from test_sg_controller62 import boosted, fixture as sg_fixture, tick
from test_sg_observations64 import observed
from test_native_program56 import setup as native_program_setup
from test_wallbox_profile27 import setup as wallbox_profile_setup
from custom_components.solar_pilot.wallbox_profile import validate_profile
from test_sg_transport62 import native, writes
from custom_components.solar_pilot.sg_transport import ShellyLeaseError
import asyncio
from types import SimpleNamespace
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from test_runtime import build
from test_dishwasher import setup as dishwasher_setup
from custom_components.solar_pilot.dishwasher import read as read_dishwasher
from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from custom_components.solar_pilot.sg_config import validate_config
from custom_components.solar_pilot.sg_config import normalize_config, NUMBER_LIMITS
from test_sg_budget_priority62 import configured as solar_runtime_sg_setup, mature_reclaim
from custom_components.solar_pilot.engine import Action
import time


@pytest.mark.parametrize("flag", ["estimated", "is_estimated"])
@pytest.mark.parametrize("mode,action", [("heat", "heating"), ("off", "idle")])
def test_estimated_zone_cannot_certify_native_context_or_exclude_cooling(flag, mode, action):
    runtime, hass = observed(zone_entities=["climate.audit_zone"])
    hass.states.set("climate.audit_zone", mode, {"hvac_action": action, flag: True})
    view = runtime.panasonic.overview()
    assert not view["context_reliable"]
    assert view["context_signature"] is None
    assert view["cooling_possible"] is True
    assert not hass.services.calls


@pytest.mark.parametrize("flag", ["estimated", "is_estimated"])
def test_estimated_tank_cannot_be_new_measured_storage_evidence(flag):
    runtime, hass = observed(tank_temperature_entity="sensor.audit_tank_temperature")
    hass.states.set("sensor.audit_tank_temperature", 48,
                    {"unit_of_measurement": "°C", flag: True})
    view = runtime.panasonic.overview()
    assert view["temperature_c"] is None
    assert view["temperature_stamp"] is None
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["shortened", "cancelled"])
async def test_external_timer_change_never_renews_our_previous_request(change):
    manager, adapter, clock, runtime = await boosted()
    clock.advance(manager.settings["renew_s"])
    if change == "shortened":
        adapter.duration -= 120
        adapter.expiry -= 120
    else:
        adapter.duration, adapter.expiry = 0, None
    calls = deepcopy(adapter.calls)
    await tick(manager)
    assert manager.manual_hold
    assert not manager.owned and not manager.desired_on
    assert adapter.calls == calls
    for _ in range(3):
        clock.advance(60)
        await tick(manager)
    assert adapter.calls == calls


def test_validated_decimal_phase_string_does_not_crash_control_tick():
    settings = {"charging_phases": "3.0", "profile_auto": False}
    assert not validate_profile(settings)
    profile, hass = wallbox_profile_setup(**settings)
    view = profile.update()
    assert view["phases"] == 3 and view["maximum_power_w"] == 17250
    assert not hass.services.calls


@pytest.mark.parametrize("flag", ["estimated", "is_estimated"])
def test_estimated_wallbox_profile_is_not_claimed_as_live_integrated_capacity(flag):
    profile, hass = wallbox_profile_setup(max_current_entity="number.audit_current",
                                         phases_entity="sensor.audit_phases")
    hass.states.set("number.audit_current", 80, {"unit_of_measurement": "A", flag: True})
    hass.states.set("sensor.audit_phases", 3, {flag: True})
    view = profile.update()
    assert view["current_source"] != "Wallbox-integratie"
    assert view["max_current_a"] == 25 and view["phases"] == 1
    assert not hass.services.calls


def test_disabled_native_zone_cannot_supply_programme_guard_proof(monkeypatch):
    helper, coordinator, rows, entries, wall = native_program_setup(monkeypatch)
    helper.read("climate.salon")
    coordinator.poll()
    rows["climate.salon"].disabled_by = "user"
    assert not helper.read("climate.salon")["fresh"]


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["shortened", "extended", "cancelled", "off"])
async def test_timer_takeover_during_production_preflight_has_no_renewal_write(native, change):
    manager, _, clock, runtime = sg_fixture()
    manager._adapter = native.adapter
    await tick(manager)
    clock.advance(120)
    native.device.clock += 120
    await tick(manager)
    assert manager.owned
    original = native.adapter.set_on

    async def pause_before_set(lease_s):
        native.device.pause_read = asyncio.Event()
        native.device.release_read = asyncio.Event()
        return await original(lease_s)

    native.adapter.set_on = pause_before_set
    clock.advance(60)
    native.device.clock += 60
    before = deepcopy(writes(native))
    renewal = asyncio.create_task(tick(manager))
    # No wall-clock sleep: let the task reach its synthetic transport await.
    for _ in range(100):
        if native.device.pause_read is not None and native.device.pause_read.is_set():
            break
        await asyncio.sleep(0)
    assert native.device.pause_read.is_set()
    if change == "cancelled":
        native.device.duration = 0
    elif change == "off":
        native.device.output = False
        native.device.started = native.device.duration = None
    else:
        native.device.duration += -120 if change == "shortened" else 120
    native.device.release_read.set()
    await renewal
    assert manager.manual_hold and not manager.owned and not manager.desired_on
    assert writes(native) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("expired", [False, True])
async def test_restart_read_failure_can_reconcile_original_lease_on_later_report(expired):
    old, adapter, clock, runtime = await boosted()
    stored = old.snapshot()
    manager, _, _, _ = sg_fixture()
    manager._clock = manager._wall_clock = clock
    manager._adapter = adapter
    manager.restore(stored)
    adapter.online = False
    await manager.start()
    assert manager._restart_release
    adapter.online = True
    clock.advance(360 if expired else 30)
    await tick(manager)
    assert not manager._restart_release and not manager.busy
    assert not manager.manual_hold
    assert manager.relay_on is False and not manager.desired_on
    if not expired:
        assert adapter.calls[-1] == ("off", None)
    else:
        assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", [False, True])
@pytest.mark.parametrize("scripted", [False, True])
async def test_configured_wallbox_keeps_read_only_authority_when_monitor_disabled(monkeypatch, enabled, scripted):
    runtime, hass = build()
    runtime.wallbox_settings.update(enabled=enabled, power_entity="sensor.audit_ev_power")
    rows = {eid: SimpleNamespace(entity_id=eid, device_id="audit_ev", platform="wallbox")
            for eid in ("sensor.audit_ev_power", "number.audit_ev_current")}
    monkeypatch.setattr(er, "async_get", lambda _: SimpleNamespace(async_get=rows.get, entities=rows))
    if scripted:
        script = SimpleNamespace(script=SimpleNamespace(sequence=[{
            "action": "number.set_value", "target": {"entity_id": "number.audit_ev_current"},
            "data": {"value": 6}}]))
        hass.data["script"] = SimpleNamespace(get_entity=lambda _: script)
        entity, service, data = "script.audit_charger_change", "turn_on", None
    else:
        entity, service, data = "number.audit_ev_current", "set_value", {"value": 6}
    with pytest.raises(HomeAssistantError):
        await runtime._call(entity, service, data)
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["shortened", "extended", "cancelled"])
async def test_unread_restart_later_manual_timer_is_preserved_without_off(change):
    previous, adapter, clock, _ = await boosted()
    manager, _, _, _ = sg_fixture()
    manager._clock = manager._wall_clock = clock
    manager._adapter = adapter
    manager.restore(previous.snapshot())
    adapter.online = False
    await manager.start()
    clock.advance(30)
    adapter.online = True
    if change == "cancelled":
        adapter.duration, adapter.expiry = 0, None
    else:
        adapter.duration += -120 if change == "shortened" else 120
        adapter.expiry += -120 if change == "shortened" else 120
    await tick(manager)
    assert manager.manual_hold and not manager._restart_release and not manager.busy
    assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_recovery_off_disconnect_does_not_retry_or_outlive_proven_local_lease():
    previous, adapter, clock, _ = await boosted()
    manager, _, _, _ = sg_fixture()
    manager._clock = manager._wall_clock = clock
    manager._adapter = adapter
    manager.restore(previous.snapshot())
    adapter.online = False
    await manager.start()
    clock.advance(30)
    adapter.online = True
    original = adapter.set_off

    async def disconnected_off():
        adapter.online = False
        return await original()

    adapter.set_off = disconnected_off
    await tick(manager)
    assert not manager._restart_release and manager.fault_code == "off_failed"
    calls = deepcopy(adapter.calls)
    assert calls == [("on", 300), ("off", None)]
    clock.advance(60)
    await tick(manager)
    assert manager.busy and adapter.calls == calls
    clock.advance(300)
    await tick(manager)
    assert not manager.busy and adapter.calls == calls
    adapter.online = True
    clock.advance(300)
    await tick(manager)
    assert manager.relay_on is False and not manager.owned
    assert adapter.calls == calls


@pytest.mark.asyncio
async def test_native_repeated_poll_and_own_renewal_are_not_manual_takeover(native):
    manager, _, clock, _ = sg_fixture()
    manager._adapter = native.adapter
    await tick(manager)
    clock.advance(120)
    native.device.clock += 120
    await tick(manager)
    native.device.duration += 1  # Exact-expiry tolerance is independent of remaining time.
    for _ in range(20):
        clock.advance(15)
        native.device.clock += 15
        await tick(manager)
        assert manager.owned and not manager.manual_hold and not manager.fault
    assert len(writes(native)) == 6
    assert all(params["on"] is True for _, params in writes(native))


@pytest.mark.asyncio
async def test_initial_native_on_takeover_during_preflight_does_not_create_or_release_a_request(native):
    manager, _, clock, _ = sg_fixture()
    manager._adapter = native.adapter
    await tick(manager)
    clock.advance(120)
    native.device.clock += 120
    original = native.adapter.set_on

    async def manual_on_preflight(lease_s):
        native.device.output = True
        native.device.started = native.device.clock
        native.device.duration = 600
        return await original(lease_s)

    native.adapter.set_on = manual_on_preflight
    await tick(manager)
    assert manager.manual_hold and not manager.owned and not manager.desired_on
    assert not manager.fault and not writes(native)


@pytest.mark.asyncio
async def test_async_fresh_status_callback_is_rejected_without_running_work(native):
    async def invalid_async_callback(status):
        raise AssertionError("Ownership callbacks must stay synchronous")

    native.adapter.before_on_status = invalid_async_callback
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code == "dispatch_changed" and not caught.value.command_attempted
    assert not writes(native)


@pytest.mark.asyncio
async def test_close_does_not_overwrite_a_manual_timer_changed_after_the_last_tick(native):
    manager, _, clock, _ = sg_fixture()
    manager._adapter = native.adapter
    await tick(manager)
    clock.advance(120)
    native.device.clock += 120
    await tick(manager)
    assert manager.owned
    native.device.duration += 120
    before = deepcopy(writes(native))
    await manager.close()
    assert manager.manual_hold and not manager.owned
    assert writes(native) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("release", ["close", "pause", "hard"])
@pytest.mark.parametrize("change", ["shortened", "extended", "zero_cancel", "off"])
async def test_release_preflight_respects_proven_takeover_or_already_off(native, release, change):
    manager, _, clock, runtime = sg_fixture()
    manager._adapter = native.adapter
    await tick(manager)
    clock.advance(120)
    native.device.clock += 120
    await tick(manager)
    before = deepcopy(writes(native))
    original = native.device.call_rpc
    changed = False

    async def takeover(method, params=None, timeout=None):
        nonlocal changed
        if not changed and native.adapter.before_off_status is not None and method == "Shelly.GetDeviceInfo":
            changed = True
            if change == "zero_cancel":
                native.device.duration = 0
            elif change == "off":
                native.device.output = False
                native.device.started = native.device.duration = None
            else:
                native.device.duration += -120 if change == "shortened" else 120
        return await original(method, params=params, timeout=timeout)

    native.device.call_rpc = takeover
    if release == "close":
        await manager.close()
    elif release == "pause":
        runtime.mode = "paused"
        await tick(manager)
    else:
        await tick(manager, hard_limit=True)
    assert changed and not manager.owned and not manager.desired_on
    assert manager.manual_hold is (change != "off")
    assert not manager.fault and writes(native) == before


@pytest.mark.asyncio
@pytest.mark.parametrize("uncertainty", ["clock_unknown", "firmware_changed", "config_changed",
    "read_unavailable", "fields_missing", "fields_invalid", "fields_overflow", "sum_overflow"])
async def test_known_owned_off_remains_available_without_capability_or_full_status(native, uncertainty):
    manager, _, clock, runtime = sg_fixture()
    manager._adapter = native.adapter
    await tick(manager)
    clock.advance(120)
    native.device.clock += 120
    await tick(manager)
    original = native.device.call_rpc
    affected = False
    if uncertainty == "firmware_changed":
        native.device.info.update(ver="2.0.0", fw_id="fictional-v2")
    elif uncertainty == "config_changed":
        native.device.config.update(in_mode="follow", initial_state="on", auto_on=True)

    async def uncertain_status(method, params=None, timeout=None):
        nonlocal affected
        if uncertainty == "clock_unknown" and method == "Sys.GetStatus":
            return {"unixtime": None}
        if not affected and native.adapter.before_off_status is not None and method == "Switch.GetStatus":
            affected = True
            if uncertainty == "read_unavailable":
                raise ConnectionError("fictional unavailable status")
            if uncertainty == "fields_missing":
                return {"id": 0, "output": True}
            if uncertainty == "fields_invalid":
                return {"id": 0, "output": True, "timer_duration": "bad", "timer_started_at": "bad"}
            if uncertainty == "fields_overflow":
                return {"id": 0, "output": True, "timer_duration": 10**400, "timer_started_at": 10**400}
            if uncertainty == "sum_overflow":
                return {"id": 0, "output": True, "timer_duration": 1e308, "timer_started_at": 1e308}
        return await original(method, params=params, timeout=timeout)

    native.device.call_rpc = uncertain_status
    runtime.mode = "paused"
    await manager.prepare_for_removal()
    assert writes(native)[-1] == ("Switch.Set", {"id": 0, "on": False})
    assert not manager.owned and not manager.desired_on and not manager.manual_hold
    assert not manager.fault and manager.sent_this_tick


@pytest.mark.asyncio
async def test_cancelled_on_after_possible_delivery_never_replays_the_request():
    manager, adapter, clock, _ = sg_fixture()
    await tick(manager)
    clock.advance(120)
    entered = asyncio.Event()
    release = asyncio.Event()
    original = adapter.set_on

    async def applied_but_not_acknowledged(lease_s):
        status = await original(lease_s)
        entered.set()
        await release.wait()
        return status

    adapter.set_on = applied_but_not_acknowledged
    task = asyncio.create_task(tick(manager))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    adapter.set_on = original
    calls = deepcopy(adapter.calls)
    await tick(manager)
    assert not manager.desired_on and not manager.owned
    assert sum(call[0] == "on" for call in adapter.calls) == 1
    assert manager.fault and not manager.minimum_hold_active


@pytest.mark.asyncio
@pytest.mark.parametrize("renewal", [False, True])
async def test_cancelled_production_on_or_renewal_keeps_uncertainty_separate_from_manual_takeover(native, renewal):
    manager, _, clock, _ = sg_fixture()
    manager._adapter = native.adapter
    await tick(manager)
    clock.advance(120)
    native.device.clock += 120
    if renewal:
        await tick(manager)
        clock.advance(60)
        native.device.clock += 60
    entered, release = asyncio.Event(), asyncio.Event()
    original = native.adapter.set_on

    async def applied_without_manager_ack(lease_s):
        status = await original(lease_s)
        entered.set()
        await release.wait()
        return status

    native.adapter.set_on = applied_without_manager_ack
    task = asyncio.create_task(tick(manager))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    native.adapter.set_on = original
    assert not manager.manual_hold and manager.fault_code == "on_failed"
    assert writes(native)[-1] == ("Switch.Set", {"id": 0, "on": False})
    count = len(writes(native))
    await tick(manager)
    assert len(writes(native)) == count
    assert not manager.owned and not manager.desired_on


@pytest.mark.asyncio
async def test_lost_renewal_ack_is_not_mislabeled_as_manual_timer_and_still_gets_safe_off(native):
    manager, _, clock, _ = sg_fixture()
    manager._adapter = native.adapter
    await tick(manager)
    clock.advance(120)
    native.device.clock += 120
    await tick(manager)
    previous_expiry = manager._lease_expiry
    original = native.device.call_rpc

    async def lost_write_ack(method, params=None, timeout=None):
        result = await original(method, params=params, timeout=timeout)
        if method == "Switch.Set" and params.get("on") is True:
            assert native.device.started+native.device.duration > previous_expiry
            raise ConnectionError("fictional acknowledgement lost after applied renewal")
        return result

    native.device.call_rpc = lost_write_ack
    clock.advance(60)
    native.device.clock += 60
    await tick(manager)
    assert not manager.manual_hold and manager.fault_code == "on_failed"
    assert writes(native)[-1] == ("Switch.Set", {"id": 0, "on": False})
    assert not manager.owned and not manager.desired_on


@pytest.mark.asyncio
@pytest.mark.parametrize("enabled", ["auto", "disabled"])
@pytest.mark.parametrize("target", ["button.dw_start", "button.audit_dw_pause", "switch.audit_dw_plug"])
async def test_aeg_targets_and_bound_siblings_never_become_generic_actuators(monkeypatch, enabled, target):
    runtime, hass, cfg = dishwasher_setup(power_entity="sensor.audit_dw_power")
    runtime.device_modes["a"] = enabled
    rows = {eid: SimpleNamespace(entity_id=eid, device_id="fictional_dishwasher", platform="electrolux_status")
            for eid in ("button.dw_start", "sensor.dw_phase", "button.audit_dw_pause")}
    rows.update({eid: SimpleNamespace(entity_id=eid, device_id="fictional_metered_plug", platform="shelly")
                 for eid in ("sensor.audit_dw_power", "switch.audit_dw_plug")})
    monkeypatch.setattr(er, "async_get", lambda _: SimpleNamespace(async_get=rows.get, entities=rows))
    action = "turn_on" if target.startswith("switch.") else "press"
    with pytest.raises(HomeAssistantError):
        await runtime._call(target, action)
    script = SimpleNamespace(script=SimpleNamespace(sequence=[{
        "action": target.split(".")[0]+"."+action, "target": {"entity_id": target}}]))
    hass.data["script"] = SimpleNamespace(get_entity=lambda _: script)
    with pytest.raises(HomeAssistantError):
        await runtime._call("script.audit_appliance", "turn_on")
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("platform", ["electrolux", "electrolux_status", "aeg"])
async def test_registered_unconfigured_aeg_button_does_not_get_generic_permission(monkeypatch, platform):
    runtime, hass = build()
    row = SimpleNamespace(entity_id="button.audit_native_start", platform=platform, device_id="fixture_aeg")
    monkeypatch.setattr(er, "async_get", lambda _: SimpleNamespace(async_get=lambda eid: row if eid == row.entity_id else None))
    with pytest.raises(HomeAssistantError):
        await runtime._call(row.entity_id, "press")
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_exact_native_owned_aeg_payload_cannot_be_reused_for_a_second_start():
    runtime, hass, cfg = dishwasher_setup()
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    wall = time.time()
    runtime.dishwasher.arm(cfg, read_dishwasher(hass, cfg, wall), wall)
    runtime.dishwasher.sent(cfg, wall)
    runtime.states["a"].owned = True
    runtime.states["a"].target_w = cfg["nominal_w"]
    runtime.pending = {"id": "a", "watts": cfg["nominal_w"], "issued_wall": wall}
    await runtime._call_dishwasher_start("a", cfg["start_button"])
    assert hass.services.calls == [("button", "press", {"entity_id": cfg["start_button"]})]
    with pytest.raises(HomeAssistantError):
        await runtime._call_dishwasher_start("a", cfg["start_button"])
    assert len(hass.services.calls) == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("during_preflight", [False, True])
@pytest.mark.parametrize("bad", ["missing", "invalid", "overflow"])
async def test_unproven_timer_does_not_become_manual_takeover_or_new_on_permission(native, during_preflight, bad):
    manager, _, clock, _ = sg_fixture()
    manager._adapter = native.adapter
    await tick(manager)
    clock.advance(120)
    native.device.clock += 120
    await tick(manager)
    before_count = len(writes(native))
    if during_preflight:
        original = native.adapter.set_on

        async def changed_status(lease_s):
            if bad == "missing":
                native.device.started = native.device.duration = None
            elif bad == "invalid":
                native.device.started = native.device.duration = "invalid"
            else:
                native.device.started = native.device.duration = 1e308
            return await original(lease_s)

        native.adapter.set_on = changed_status
    elif bad == "missing":
        native.device.started = native.device.duration = None
    elif bad == "invalid":
        native.device.started = native.device.duration = "invalid"
    else:
        native.device.started = native.device.duration = 1e308
    clock.advance(60)
    native.device.clock += 60
    await tick(manager)
    assert not manager.manual_hold and manager.fault_code == "lease_invalid"
    assert not manager.owned and not manager.desired_on
    assert writes(native)[before_count:] == [("Switch.Set", {"id": 0, "on": False})]


@pytest.mark.asyncio
@pytest.mark.parametrize("production", [False, True])
async def test_cancelled_applied_off_finishes_uncertain_lifecycle_without_retry_or_early_on(native, production):
    if production:
        manager, _, clock, runtime = sg_fixture()
        adapter = native.adapter
        manager._adapter = adapter
        await tick(manager)
        clock.advance(120)
        native.device.clock += 120
        await tick(manager)
    else:
        manager, adapter, clock, runtime = await boosted()
    entered, release = asyncio.Event(), asyncio.Event()
    original = adapter.set_off

    async def applied_without_manager_ack():
        status = await original()
        entered.set()
        await release.wait()
        return status

    adapter.set_off = applied_without_manager_ack
    runtime.mode = "paused"
    task = asyncio.create_task(tick(manager))
    await entered.wait()
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert manager.fault_code == "off_failed" and not manager.desired_on
    assert manager._session_started is None and manager._last_session is not None
    assert manager._rest_until > clock()
    assert manager.relay_on is None and not manager.relay_confirmed
    adapter.set_off = original
    count = len(writes(native)) if production else len(adapter.calls)
    runtime.mode = "solar"
    await tick(manager)
    assert manager.relay_on is False and not manager.owned
    assert not manager.fault and manager.state == "rest"
    assert (len(writes(native)) if production else len(adapter.calls)) == count
    assert manager._rest_until > clock()


@pytest.mark.asyncio
async def test_valid_numeric_string_threshold_remains_usable_in_low_solar_reason():
    manager, adapter, clock, _ = sg_fixture(threshold_w="3000")
    assert not validate_config(manager.settings)
    await tick(manager, surplus=2000)
    assert manager.state == "waiting_surplus" and "3000 W" in manager.reason
    assert not adapter.calls


@pytest.mark.asyncio
async def test_valid_numeric_string_freshness_preserves_soft_import_policy():
    manager, adapter, clock, _ = await boosted(stale_s="120")
    assert not validate_config(manager.settings)
    await tick(manager, imported=1000)
    clock.advance(60)
    await tick(manager, imported=1000)
    assert manager.minimum_hold_active and manager.cloud_hold_active
    assert all(call[0] == "on" for call in adapter.calls)


def test_valid_numeric_string_freshness_is_not_a_solar_budget_type_error():
    runtime, hass = observed()
    before = sg_solar_budget(runtime)
    runtime.sg_boost.settings["stale_s"] = "120"
    assert sg_solar_budget(runtime) == before
    assert not hass.services.calls


def test_valid_numeric_string_effective_view_preserves_saved_options_and_every_runtime_consumer():
    runtime, hass = solar_runtime_sg_setup()
    raw = {**runtime.sg_boost.settings,
           **{key: str(runtime.sg_boost.settings[key]) for key in NUMBER_LIMITS}}
    assert not validate_config(raw)
    original = deepcopy(raw)
    runtime.entry.options["sg_boost"] = raw
    runtime.sg_boost.update_config(raw)
    runtime.panasonic.update_config(raw)
    assert all(isinstance(runtime.sg_boost.settings[key], (int, float)) for key in NUMBER_LIMITS)
    assert runtime.entry.options["sg_boost"] == original == raw
    assert runtime.sg_dispatch_allowed() is True
    assert runtime._sg_import_observation()["watts"] == 0
    assert runtime.electrical_limits_overview()["source_stale_s"] == 120
    assert runtime._power(runtime.settings["pv_entity"], runtime.sg_boost.settings["stale_s"])[0] == 8000
    # The already running lower load has no new start to hold; evaluating its
    # current SG threshold must still accept the normalized quoted settings.
    assert runtime.priority_board.extra_start_blocks(100) == {}
    runtime.priority_board.extra_reclaim_sent(Action("a", 0, "Zonnestroom vrijmaken voor SG-zonneboost"), 100)
    assert runtime.priority_board._extra_lease_until == 250
    assert runtime.entry.options["sg_boost"] == original and not hass.services.calls


def test_valid_string_priority_reclaim_uses_same_threshold_demand_and_delay_without_option_write():
    runtime, hass = solar_runtime_sg_setup(export=2200)
    raw = {**runtime.sg_boost.settings, "threshold_w": "3000", "expected_power_w": "3200",
           "start_delay_s": "30", "stale_s": "120"}
    runtime.entry.options["sg_boost"] = deepcopy(raw)
    runtime.sg_boost.update_config(raw)
    runtime.panasonic.update_config(raw)
    action = mature_reclaim(runtime, hass)
    assert action is not None and action.id == "a" and action.watts == 0
    assert runtime.entry.options["sg_boost"] == raw and not hass.services.calls


@pytest.mark.parametrize("key,value", [("threshold_w", "nan"), ("threshold_w", "499"),
    ("stale_s", "601"), ("start_delay_s", "29"), ("enabled", "True")])
def test_invalid_numeric_or_permission_strings_keep_visible_validation_and_no_new_right(key, value):
    normalized = normalize_config({key: value})
    assert normalized[key] == value
    assert key in validate_config(normalized)


@pytest.mark.parametrize("config", [{"charging_phases": True}, {"charging_phases": None},
    {"charging_phases": "nan"}, {"max_current_a": "nan"}, {"max_current_a": 10**400},
    {"voltage_v": None}, {"minimum_current_a": False}])
def test_invalid_manual_profile_is_visible_bounded_fallback_without_controller_crash(config):
    assert validate_profile(config)
    profile, hass = wallbox_profile_setup(profile_auto=False, **config)
    view = profile.update()
    assert view["warning"] and 0 < view["minimum_power_w"] < float("inf")
    assert 0 < view["maximum_power_w"] < float("inf")
    assert not hass.services.calls

