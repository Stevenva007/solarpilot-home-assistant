"""Independent priority audit with fictional meters and no physical devices."""
from __future__ import annotations

from copy import deepcopy
from types import SimpleNamespace as NS
import asyncio
import json
import math
import time

import pytest
from homeassistant.exceptions import HomeAssistantError

from test_runtime import build
from custom_components.solar_pilot.runtime import SolarRuntime
from custom_components.solar_pilot.engine import Action, Device, Site, State, plan
from custom_components.solar_pilot.wallbox import Reading
from custom_components.solar_pilot.consumer_wallbox import follows_wallbox
from custom_components.solar_pilot import wallbox_priority as policy_module


def setup(monkeypatch):
    old, hass = build(power=True, device={"wallbox_precedence": "consumer_first", "nominal_w": 350})
    first = old.entry.options["devices"][0]
    for key, kind in (("fictional_freezer", "switch"), ("fictional_dish", "dishwasher")):
        cfg = {**first, "id": key, "name": key, "kind": kind,
               "control_entity": "switch." + key, "power_entity": "sensor." + key}
        old.entry.options["devices"].append(cfg)
        hass.states.set(cfg["control_entity"], "off")
        hass.states.set(cfg["power_entity"], 0, {"unit_of_measurement": "W"})
    old.entry.options["wallbox"] = {
        "enabled": True, "power_entity": "sensor.ev", "status_entity": "sensor.ev_status",
        "mode_entity": "select.ev_mode", "trust_solar_setting": True, "stable_s": 0,
        "priority_stable_s": 0, "priority_min_power_w": 1380,
    }
    hass.states.set("sensor.ev", 0, {"unit_of_measurement": "W"})
    hass.states.set("sensor.ev_status", "Waiting for green energy")
    hass.states.set("select.ev_mode", "full_solar")
    old.entry.options["priority_board"] = {
        "schema": 2,
        "order": ["device:a", "device:fictional_freezer", "device:fictional_dish", "wallbox", "dhw_extra"],
        "wallbox_power": {"device:a": True, "device:fictional_freezer": True,
                          "device:fictional_dish": True},
    }
    runtime = SolarRuntime(hass, old.entry)
    runtime.data_loaded = True
    clock = [time.time()]
    # Override only the policy clock; original HA meter timestamps stay real.
    monkeypatch.setattr(policy_module, "time", NS(time=lambda: clock[0]))
    return runtime, hass, clock


def commands(hass):
    return [call for call in hass.services.calls if call[0] != "persistent_notification"]


def solar_reading(power=0, *, demand=True, status="Waiting for green energy"):
    return Reading(power_w=power, stamp=time.time(), demand=demand, status=status,
                   mode="full_solar", valid=True, age_s=0, connected=True,
                   raw_mode="full_solar", session_confirmed=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("option,seconds", [("30m", 1800), ("1h", 3600), ("2h", 7200),
                                          ("3h", 10800), ("4h", 14400), ("5h", 18000)])
async def test_absolute_deadline_and_restart_do_not_renew_duration(monkeypatch, option, seconds):
    runtime, hass, clock = setup(monkeypatch)
    await runtime.wallbox_priority.set("device:a", option)
    saved = runtime.wallbox_priority.snapshot()
    deadline = saved["targets"]["device:a"]["expires_at"]
    assert deadline == clock[0] + seconds
    clock[0] += 127.25
    fresh = SolarRuntime(hass, runtime.entry)
    fresh.wallbox_priority.restore(saved)
    view = fresh.wallbox_priority.overview()["devices"]["a"]
    assert view["expires_at"] == deadline
    assert view["remaining_s"] == math.ceil(seconds - 127.25)
    clock[0] = deadline
    assert fresh.wallbox_priority.overview()["devices"]["a"]["option"] == "auto"
    assert not fresh.wallbox_priority.active("device:a")
    assert not commands(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("exception", ["auto", "until_auto", "5h"])
async def test_general_one_shot_fanout_keeps_manual_exceptions_then_resets_everything(monkeypatch, exception):
    runtime, hass, clock = setup(monkeypatch)
    original_options = deepcopy(runtime.entry.options)
    original_modes = deepcopy(runtime.device_modes)
    await runtime.async_set_wallbox_priority("global", "30m")
    assert runtime.wallbox_priority.active("device:a")
    assert runtime.wallbox_priority.active("device:fictional_freezer")
    assert "fictional_dish" not in runtime.wallbox_priority.overview()["devices"]
    clock[0] += 1
    await runtime.async_set_wallbox_priority("device:a", exception)
    assert runtime.wallbox_priority.overview()["devices"]["a"]["option"] == exception
    assert runtime.wallbox_priority.overview()["general"]["option"] == "30m"
    assert runtime.wallbox_priority.overview()["mixed"]
    await runtime.async_set_wallbox_priority("global", "auto")
    assert all(row["option"] == "auto" for row in runtime.wallbox_priority.overview()["devices"].values())
    assert runtime.wallbox_priority.snapshot()["targets"] == {}
    assert runtime.entry.options == original_options and runtime.device_modes == original_modes
    assert not commands(hass)


@pytest.mark.asyncio
async def test_expired_general_clears_later_indefinite_manual_exception_and_next_choice_is_new(monkeypatch):
    runtime, _, clock = setup(monkeypatch)
    await runtime.wallbox_priority.set("global", "30m")
    clock[0] += 90
    await runtime.wallbox_priority.set("device:a", "until_auto")
    clock[0] += 1710
    assert not runtime.wallbox_priority.active("device:a")
    assert not runtime.wallbox_priority.active("device:fictional_freezer")
    await runtime.wallbox_priority.set("device:a", "1h")
    assert runtime.wallbox_priority.active("device:a")
    assert not runtime.wallbox_priority.active("device:fictional_freezer")
    assert runtime.wallbox_priority.overview()["general"]["option"] == "auto"


@pytest.mark.asyncio
async def test_individual_expiry_never_resets_independent_other_choice(monkeypatch):
    runtime, _, clock = setup(monkeypatch)
    await runtime.wallbox_priority.set("device:a", "30m")
    await runtime.wallbox_priority.set("device:fictional_freezer", "until_auto")
    clock[0] += 1800
    await runtime.wallbox_priority.expire()
    assert not runtime.wallbox_priority.active("device:a")
    assert runtime.wallbox_priority.active("device:fictional_freezer")
    assert runtime.wallbox_priority.overview()["devices"]["fictional_freezer"]["label"] == "tot ik terug op automatisch zet"


@pytest.mark.asyncio
async def test_saved_order_and_migration_are_never_overwritten_by_temporary_overlay(monkeypatch):
    runtime, hass, _ = setup(monkeypatch)
    saved = deepcopy(runtime.entry.options["priority_board"])
    revision = runtime.priority_board.revision()
    await runtime.wallbox_priority.set("device:a", "until_auto")
    assert runtime.priority_board.order().index("wallbox") < runtime.priority_board.order().index("device:a")
    assert runtime.priority_board.base_order() == saved["order"]
    assert runtime.priority_board.overview()["order"] == saved["order"]
    assert runtime.priority_board.overview()["effective_order"] == runtime.priority_board.order()
    assert runtime.priority_board.revision() == revision
    assert not await runtime.priority_board.migrate_beta36()
    await runtime.priority_board.save(revision, saved["order"], saved["wallbox_power"], True)
    assert runtime.entry.options["priority_board"] == saved
    await runtime.wallbox_priority.set("device:a", "auto")
    assert runtime.priority_board.order() == saved["order"]
    assert not commands(hass)


@pytest.mark.asyncio
async def test_overlay_restricts_real_board_reclaim_and_dishwasher_contract_is_preserved(monkeypatch):
    runtime, _, _ = setup(monkeypatch)
    dishwasher_before = runtime.priority_board.effective_config("fictional_dish")
    base_permissions = runtime.priority_board.permissions()
    original_configs = deepcopy(runtime.configs)
    assert not follows_wallbox(runtime.priority_board.effective_config("a"), runtime.others_first)
    await runtime.wallbox_priority.set("global", "until_auto")
    effective = runtime.priority_board.effective_config("a")
    assert follows_wallbox(effective, runtime.others_first)
    assert effective["wallbox_power_policy"] == "never" and not effective["allow_wallbox_reclaim"]
    assert runtime.priority_board.permissions() == base_permissions
    dishwasher_after = runtime.priority_board.effective_config("fictional_dish")
    for key in ("wallbox_precedence", "dishwasher_ev_solar_priority", "allow_wallbox_reclaim", "wallbox_power_policy"):
        assert dishwasher_after[key] == dishwasher_before[key]
    assert runtime.configs == original_configs
    with pytest.raises(HomeAssistantError):
        await runtime.wallbox_priority.set("device:fictional_dish", "30m")


@pytest.mark.asyncio
async def test_global_snapshot_does_not_grant_new_or_rewired_device_a_hold(monkeypatch):
    runtime, _, _ = setup(monkeypatch)
    await runtime.wallbox_priority.set("global", "until_auto")
    runtime.configs["added_later"] = {**runtime.configs["a"], "id": "added_later", "control_entity": "switch.new_load"}
    assert not runtime.wallbox_priority.active("device:added_later")
    runtime.configs["a"]["control_entity"] = "switch.rewired_load"
    assert not runtime.wallbox_priority.active("device:a")
    assert runtime.wallbox_priority.active("device:fictional_freezer")
    runtime.wallbox_priority.retire("fictional_freezer")
    assert not runtime.wallbox_priority.active("device:fictional_freezer")


@pytest.mark.asyncio
async def test_label_edit_does_not_destroy_an_existing_timer(monkeypatch):
    runtime, _, _ = setup(monkeypatch)
    await runtime.wallbox_priority.set("device:a", "30m")
    previous = runtime.wallbox_priority.overview()["devices"]["a"]["expires_at"]
    runtime.configs["a"]["name"] = "Another fictional label"
    assert runtime.wallbox_priority.active("device:a")
    assert runtime.wallbox_priority.overview()["devices"]["a"]["expires_at"] == previous


@pytest.mark.asyncio
async def test_store_failure_never_activates_policy_or_commands_devices(monkeypatch):
    runtime, hass, _ = setup(monkeypatch)
    await runtime.wallbox_priority.set("device:a", "until_auto")
    original = runtime.wallbox_priority.snapshot()
    async def fail(_data):
        raise OSError("fictional storage failure")
    monkeypatch.setattr(runtime.store, "async_save", fail)
    with pytest.raises(HomeAssistantError):
        await runtime.async_set_wallbox_priority("global", "1h")
    assert runtime.wallbox_priority.snapshot() == original
    assert not commands(hass)


@pytest.mark.asyncio
async def test_cancelled_save_never_activates_new_policy(monkeypatch):
    runtime, hass, _ = setup(monkeypatch)
    original = runtime.wallbox_priority.snapshot()
    async def cancel(_data):
        raise asyncio.CancelledError()
    monkeypatch.setattr(runtime.store, "async_save", cancel)
    with pytest.raises(asyncio.CancelledError):
        await runtime.async_set_wallbox_priority("global", "1h")
    assert runtime.wallbox_priority.snapshot() == original
    assert not commands(hass)


@pytest.mark.asyncio
async def test_binding_change_during_save_cannot_grant_replacement_policy(monkeypatch):
    runtime, hass, _ = setup(monkeypatch)
    original = runtime.wallbox_priority.snapshot()
    save = runtime.store.async_save
    async def rewire(data):
        await save(data)
        runtime.configs["a"]["control_entity"] = "switch.replacement"
    monkeypatch.setattr(runtime.store, "async_save", rewire)
    with pytest.raises(HomeAssistantError):
        await runtime.async_set_wallbox_priority("device:a", "until_auto")
    assert runtime.wallbox_priority.snapshot() == original
    assert not runtime.wallbox_priority.active("device:a")
    restarted = SolarRuntime(hass, runtime.entry)
    restarted.configs["a"]["control_entity"] = "switch.replacement"
    restarted.wallbox_priority.restore(runtime.store.data["wallbox_priority"])
    assert not restarted.wallbox_priority.active("device:a")
    assert not commands(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("corruption", ["schema_bool", "schema_other", "entry", "binding", "extra",
    "targets_type", "general_type", "general_option", "general_future", "general_nan",
    "general_expiry_bool", "general_duration", "general_expired"])
async def test_untrusted_general_journal_never_leaves_children_active(monkeypatch, corruption):
    runtime, _, clock = setup(monkeypatch)
    await runtime.wallbox_priority.set("global", "30m")
    data = runtime.wallbox_priority.snapshot()
    if corruption == "schema_bool": data["schema"] = True
    elif corruption == "schema_other": data["schema"] = 999
    elif corruption == "entry": data["entry_id"] = "foreign_entry"
    elif corruption == "binding": data["wallbox_binding"] = "foreign_binding"
    elif corruption == "extra": data["unexpected"] = 1
    elif corruption == "targets_type": data["targets"] = []
    elif corruption == "general_type": data["general"] = "30m"
    elif corruption == "general_option": data["general"]["option"] = "6h"
    elif corruption == "general_future": data["general"]["created_at"] = clock[0] + 1
    elif corruption == "general_nan": data["general"]["created_at"] = float("nan")
    elif corruption == "general_expiry_bool": data["general"]["expires_at"] = True
    elif corruption == "general_duration": data["general"]["expires_at"] += 1
    else: clock[0] += 1800
    runtime.wallbox_priority.restore(data)
    assert not runtime.wallbox_priority.any_active()
    assert runtime.wallbox_priority.overview()["general"]["option"] == "auto"


@pytest.mark.asyncio
@pytest.mark.parametrize("corruption", ["missing", "option", "zero_created", "future", "infinite", "binding", "expiry", "extra"])
async def test_invalid_individual_record_drops_only_that_target(monkeypatch, corruption):
    runtime, _, clock = setup(monkeypatch)
    await runtime.wallbox_priority.set("device:a", "30m")
    await runtime.wallbox_priority.set("device:fictional_freezer", "until_auto")
    data = runtime.wallbox_priority.snapshot()
    target = data["targets"]["device:a"]
    if corruption == "missing": target.pop("binding")
    elif corruption == "option": target["option"] = "5 h"
    elif corruption == "zero_created": target["created_at"] = 0
    elif corruption == "future": target["created_at"] = clock[0] + 1
    elif corruption == "infinite": target["created_at"] = float("inf")
    elif corruption == "binding": target["binding"] = "fictional replacement"
    elif corruption == "expiry": target["expires_at"] += 1
    else: target["unexpected"] = None
    runtime.wallbox_priority.restore(data)
    assert not runtime.wallbox_priority.active("device:a")
    assert runtime.wallbox_priority.active("device:fictional_freezer")


@pytest.mark.asyncio
@pytest.mark.parametrize("status,demand", [("Ready", True), ("Waiting for green energy", False)])
async def test_priority_does_not_invent_ev_demand(monkeypatch, status, demand):
    runtime, _, _ = setup(monkeypatch)
    await runtime.wallbox_priority.set("global", "until_auto")
    runtime.filtered = -8000
    holds, blocks, _ = runtime._wallbox_device_constraints(time.monotonic(),
        solar_reading(status=status, demand=demand), -8000, True, 0)
    assert not holds and not blocks
    assert runtime.consumer_wallbox.result.state == "no_request"


@pytest.mark.asyncio
async def test_small_surplus_fallback_survives_forced_priority_and_dishwasher_is_not_blocked(monkeypatch):
    runtime, _, _ = setup(monkeypatch)
    await runtime.wallbox_priority.set("global", "until_auto")
    runtime.filtered = -800
    holds, blocks, no_reclaim = runtime._wallbox_device_constraints(time.monotonic(), solar_reading(), -800, True, 0)
    assert not holds and not blocks
    assert runtime.consumer_wallbox.result.state == "small_surplus"
    assert {"a", "fictional_freezer"} <= no_reclaim
    assert "fictional_dish" not in no_reclaim


@pytest.mark.asyncio
@pytest.mark.parametrize("protected", ["minimum", "non_interruptible", "manual"])
async def test_forced_priority_does_not_cut_protected_owned_cycle(monkeypatch, protected):
    runtime, _, _ = setup(monkeypatch)
    await runtime.wallbox_priority.set("global", "until_auto")
    device = Device("a", nominal_w=350, min_on_s=1200 if protected == "minimum" else 0,
                    non_interruptible=protected == "non_interruptible", start_delay_s=0)
    state = State(owned=True, on=True, target_w=350, measured_w=350, last_on=100,
                  manual_forced=protected == "manual")
    result = plan(Site(now=200, grid_w=0, filtered_grid_w=0, device_holds={"a": "Wallbox-voorrang: test"}), [device], {"a": state})
    assert result.targets["a"] == 350 and result.action is None


@pytest.mark.asyncio
async def test_anonymous_export_preserves_policy_without_private_device_identity(monkeypatch):
    runtime, hass, _ = setup(monkeypatch)
    await runtime.wallbox_priority.set("global", "until_auto")
    report = runtime.analysis.build(include_names=False)
    text = json.dumps(report)
    assert "wallbox_priority" in report["components"]["runtime_and_models"]
    assert "fictional_freezer" not in text and "fictional_dish" not in text
    assert not report["coverage"]["section_errors"]
    assert not commands(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize("expires,hard_import", [(False, False), (True, False), (True, True)])
async def test_final_wallbox_yield_rechecks_expiry_but_keeps_real_hard_safety(monkeypatch, expires, hard_import):
    runtime, hass, clock = setup(monkeypatch)
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    state = runtime.states["a"]
    state.on = state.owned = True
    state.last_on = time.monotonic() - 1000
    state.measured_w = state.target_w = 350
    hass.states.set("switch.load", "on")
    hass.states.set("sensor.load", 350, {"unit_of_measurement": "W"})
    await runtime.wallbox_priority.set("device:a", "30m")
    runtime.filtered = -2500
    # A real sufficient solar window requires a lower owned load to yield.
    reading = solar_reading()
    monkeypatch.setattr(runtime, "_wallbox_reading", lambda: reading)
    now = time.monotonic()
    holds, _, _ = runtime._wallbox_device_constraints(now, reading, -2500, True, 0)
    assert "a" in holds
    original_save = runtime.store.async_save
    journal_seen = False
    async def transition(data):
        nonlocal journal_seen
        await original_save(data)
        if not journal_seen and data.get("leases", {}).get("a", {}).get("watts") == 0:
            journal_seen = True
            if expires:
                clock[0] += 1800
            if hard_import:
                hass.states.set("sensor.grid", runtime.settings["max_import_w"] + 100,
                                {"unit_of_measurement": "W"})
    monkeypatch.setattr(runtime.store, "async_save", transition)
    await runtime._send(Action("a", 0, holds["a"]), now)
    assert journal_seen
    if expires and not hard_import:
        assert not commands(hass)
        assert runtime.pending is None and state.owned and state.target_w == 350
        assert "a" in runtime.store.data["leases"]
    else:
        assert [(call[0], call[1], call[2]["entity_id"]) for call in commands(hass)] == [("switch", "turn_off", "switch.load")]


@pytest.mark.asyncio
@pytest.mark.parametrize("independent_stop", ["manual_stop", "disabled", "demand_revoked", "interlock_revoked",
                                            "battery_wait", "grid_fault_after_grace"])
async def test_expiry_cannot_cancel_independently_required_stop_during_save(monkeypatch, independent_stop):
    runtime, hass, clock = setup(monkeypatch)
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    state = runtime.states["a"]
    state.on = state.owned = True
    state.last_on = time.monotonic() - 1000
    state.measured_w = state.target_w = 350
    hass.states.set("switch.load", "on")
    hass.states.set("sensor.load", 350, {"unit_of_measurement": "W"})
    await runtime.wallbox_priority.set("device:a", "30m")
    runtime.filtered = -2500
    reading = solar_reading()
    monkeypatch.setattr(runtime, "_wallbox_reading", lambda: reading)
    now = time.monotonic()
    holds, _, _ = runtime._wallbox_device_constraints(now, reading, -2500, True, 0)
    assert "a" in holds
    original_site = runtime._site_data
    site_changed = False
    def site():
        grid, valid, discharge, ready, stamp = original_site()
        if site_changed and independent_stop == "battery_wait":
            ready = False
        if site_changed and independent_stop == "grid_fault_after_grace":
            grid, valid = None, False
        return grid, valid, discharge, ready, stamp
    monkeypatch.setattr(runtime, "_site_data", site)
    original_save = runtime.store.async_save
    async def transition(data):
        nonlocal site_changed
        await original_save(data)
        if data.get("leases", {}).get("a", {}).get("watts") != 0 or site_changed:
            return
        site_changed = True
        clock[0] += 1800
        if independent_stop == "manual_stop": state.manual_stop_requested = True
        elif independent_stop == "disabled": state.enabled = False
        elif independent_stop == "demand_revoked": state.demand = False
        elif independent_stop == "interlock_revoked": state.interlock = False
        elif independent_stop == "grid_fault_after_grace":
            runtime.invalid_since = time.monotonic() - runtime.settings["fault_grace_s"] - 1
    monkeypatch.setattr(runtime.store, "async_save", transition)
    await runtime._send(Action("a", 0, holds["a"]), now)
    assert site_changed
    assert [(call[0], call[1], call[2]["entity_id"]) for call in commands(hass)] == [("switch", "turn_off", "switch.load")]
