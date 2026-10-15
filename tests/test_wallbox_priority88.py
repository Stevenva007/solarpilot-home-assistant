"""Durable timed preference semantics; no Wallbox or Home Assistant commands."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace as NS
import pytest
from homeassistant.exceptions import HomeAssistantError
from test_priority_board35 import multiple, activate
from custom_components.solar_pilot.runtime import SolarRuntime
from custom_components.solar_pilot.wallbox_priority import WallboxPriority, DURATIONS
from custom_components.solar_pilot.wallbox_policy import reclaim_permission
from custom_components.solar_pilot import wallbox_priority as module


def ready(monkeypatch, *, sg=True):
    old, hass = multiple()
    old.entry.options["wallbox"] = {"enabled": True, "power_entity": "sensor.ev"}
    runtime = SolarRuntime(hass, old.entry)
    runtime.data_loaded = True
    runtime.entry.runtime_data = runtime
    runtime.publish = lambda: None
    runtime.sg_boost.settings.update(enabled=sg, entity_id="switch.sg" if sg else "")
    wall = NS(value=1800000000.0)
    monkeypatch.setattr(module, "time", NS(time=lambda: wall.value))
    return runtime, hass, wall


@pytest.mark.asyncio
@pytest.mark.parametrize("option,seconds", list(DURATIONS.items()))
async def test_each_allowed_duration_keeps_absolute_deadline_and_no_commands(monkeypatch, option, seconds):
    r, h, clock = ready(monkeypatch)
    old_options = deepcopy(r.entry.options)
    answer = await r.async_set_wallbox_priority("global", option)
    assert answer["general"]["remaining_s"] == seconds
    assert answer["general"]["expires_at"] == clock.value+seconds
    assert answer["general"]["duration_s"] == seconds
    assert all(choice["option"] == option for choice in answer["devices"].values())
    assert answer["sg_boost"]["option"] == option and not answer["mixed"]
    assert r.store.data["wallbox_priority"] == r.wallbox_priority.snapshot()
    assert r.entry.options == old_options and not h.services.calls
    clock.value += seconds/2
    fresh = WallboxPriority(r)
    fresh.restore(r.store.data["wallbox_priority"])
    assert fresh.overview()["general"]["remaining_s"] == seconds/2
    assert fresh.snapshot()["general"]["expires_at"] == answer["general"]["expires_at"]


@pytest.mark.asyncio
async def test_general_fanout_individual_exceptions_and_manual_global_reset(monkeypatch):
    r, h, clock = ready(monkeypatch)
    await r.async_set_wallbox_priority("device:a", "until_auto")
    await r.async_set_wallbox_priority("global", "1h")
    clock.value += 50
    await r.async_set_wallbox_priority("device:a", "auto")
    await r.async_set_wallbox_priority("device:second_consumer", "until_auto")
    view = r.wallbox_priority.overview()
    assert view["general"]["remaining_s"] == 3550
    assert not view["devices"]["a"]["active"]
    assert view["devices"]["second_consumer"]["indefinite"] and view["mixed"]
    await r.async_set_wallbox_priority("global", "auto")
    assert not r.wallbox_priority.any_active()
    assert not r.wallbox_priority.overview()["mixed"]
    assert not h.services.calls


@pytest.mark.asyncio
async def test_general_deadline_clears_later_indefinite_exception_readonly_then_durably(monkeypatch):
    r, _h, clock = ready(monkeypatch)
    await r.async_set_wallbox_priority("global", "30m")
    clock.value += 900
    await r.async_set_wallbox_priority("device:a", "until_auto")
    before = r.wallbox_priority.snapshot()
    clock.value += 900
    view = r.wallbox_priority.overview()
    assert view["general"]["option"] == "auto"
    assert all(not choice["active"] for choice in view["devices"].values())
    assert not view["sg_boost"]["active"]
    assert r.wallbox_priority.snapshot() == before
    await r.wallbox_priority.expire()
    assert r.store.data["wallbox_priority"]["general"] is None
    assert not r.store.data["wallbox_priority"]["targets"]


@pytest.mark.asyncio
async def test_individual_expiry_and_post_expired_global_new_choice_remain_independent(monkeypatch):
    r, _h, clock = ready(monkeypatch)
    await r.async_set_wallbox_priority("global", "1h")
    await r.async_set_wallbox_priority("device:a", "30m")
    clock.value += 1800
    assert not r.wallbox_priority.active("device:a")
    assert r.wallbox_priority.active("device:second_consumer")
    clock.value += 1800
    await r.async_set_wallbox_priority("device:a", "until_auto")
    assert r.wallbox_priority.active("device:a")
    assert r.wallbox_priority.overview()["general"]["option"] == "auto"


@pytest.mark.asyncio
@pytest.mark.parametrize("kind,appliance", [("dishwasher", None), ("switch", "dishwasher"), ("script", "dishwasher")])
async def test_all_dishwasher_semantics_excluded_without_changing_existing_settings(monkeypatch, kind, appliance):
    r, _h, _clock = ready(monkeypatch)
    r.configs["a"].update(kind=kind, appliance_type=appliance)
    original = deepcopy(r.configs["a"])
    await r.async_set_wallbox_priority("global", "until_auto")
    assert "a" not in r.wallbox_priority.overview()["devices"]
    with pytest.raises(HomeAssistantError):
        await r.async_set_wallbox_priority("device:a", "1h")
    assert r.configs["a"] == original


@pytest.mark.asyncio
async def test_effective_board_cannot_leak_into_editor_save_or_restart_migration(monkeypatch):
    r, h, _clock = ready(monkeypatch)
    base = ["device:a", "wallbox", "device:second_consumer", "dhw_extra"]
    activate(r, base)
    before_options = deepcopy(r.entry.options)
    before_revision = r.priority_board.revision()
    await r.async_set_wallbox_priority("device:a", "1h")
    assert r.priority_board.order() == ["wallbox", "device:a", "device:second_consumer", "dhw_extra"]
    editor = r.priority_board.overview()
    assert editor["order"] == base and editor["effective_order"] != base
    assert editor["revision"] == before_revision
    await r.priority_board.save(editor["revision"], editor["order"], editor["wallbox_power"], True)
    await r.priority_board.migrate_beta36()
    assert r.entry.options["priority_board"]["order"] == base
    assert r.entry.options["devices"] == before_options["devices"]
    await r.async_set_wallbox_priority("device:a", "auto")
    assert r.priority_board.order() == base and not h.services.calls


@pytest.mark.asyncio
async def test_current_base_order_is_restored_without_replaying_old_saved_values(monkeypatch):
    r, _h, clock = ready(monkeypatch)
    activate(r, ["device:a", "wallbox", "device:second_consumer", "dhw_extra"])
    await r.async_set_wallbox_priority("device:a", "30m")
    newer = ["device:second_consumer", "device:a", "wallbox", "dhw_extra"]
    r.entry.options["priority_board"]["order"] = newer
    clock.value += 1800
    assert r.priority_board.order() == newer
    assert r.priority_board.overview()["order"] == newer


@pytest.mark.asyncio
async def test_forced_behind_wallbox_never_gets_reclaim_or_modifies_sg_policy(monkeypatch):
    r, _h, _clock = ready(monkeypatch)
    activate(r, ["device:a", "wallbox", "device:second_consumer", "dhw_extra"])
    sg = deepcopy(r.sg_boost.settings)
    await r.async_set_wallbox_priority("global", "until_auto")
    effective = r.priority_board.effective_config("a")
    assert not effective["allow_wallbox_reclaim"]
    assert effective["wallbox_power_policy"] == "never"
    assert reclaim_permission(effective, before_wallbox=False, dedicated_meter=True)[:2] == (False, False)
    assert not next(device for device in r.devices() if device.id == "a").allow_wallbox_reclaim
    assert r.sg_boost.settings == sg


@pytest.mark.asyncio
async def test_new_sg_soft_preference_uses_existing_minimum_and_keeps_existing_ev_guard(monkeypatch):
    from dataclasses import replace
    from test_sg_controller62 import boosted, tick
    from test_sg_minimum72 import advance
    from test_sg_budget_priority62 import configured
    from custom_components.solar_pilot.consumer_wallbox import PriorityResult
    manager, adapter, clock, _runtime = await boosted()
    r, _h = configured()
    r.wallbox_settings["enabled"] = True
    r.sg_boost = manager
    r.data_loaded = True
    r.publish = lambda: None
    await r.async_set_wallbox_priority("dhw_extra", "1h")
    r.consumer_wallbox.result = PriorityResult(block_starts=True)
    assert manager.minimum_hold_active
    assert r.priority_board.sg_priority_allowed(clock())
    # An existing EV guard still blocks; only the new soft opportunity gate is
    # deferred during the already confirmed request's original minimum.
    original = r.sg_wallbox_guard.result
    r.sg_wallbox_guard.result = replace(original, block_increase=True)
    assert not r.priority_board.sg_priority_allowed(clock())
    r.sg_wallbox_guard.result = original
    start = manager._minimum_started
    await advance(manager, clock, 1200, imported=0)
    assert manager.owned and adapter.on
    assert manager._minimum_started == start
    assert not manager.minimum_hold_active
    assert not r.priority_board.sg_priority_allowed(clock())
    await tick(manager, priority_allowed=False)
    assert not manager.owned and adapter.calls[-1] == ("off", None)


@pytest.mark.asyncio
async def test_wallbox_preference_does_not_mask_sg_hard_stop(monkeypatch):
    from test_sg_controller62 import boosted, tick
    manager, adapter, clock, _runtime = await boosted()
    assert manager.minimum_hold_active
    await tick(manager, hard_limit=True)
    assert not manager.owned and adapter.calls[-1] == ("off", None)


@pytest.mark.asyncio
async def test_save_is_before_activation_and_failure_preserves_previous_choice(monkeypatch):
    r, h, _clock = ready(monkeypatch)
    await r.async_set_wallbox_priority("device:a", "30m")
    old = r.wallbox_priority.snapshot()
    async def fail(_data):
        assert r.wallbox_priority.snapshot() == old
        raise OSError("disk")
    r.store.async_save = fail
    with pytest.raises(HomeAssistantError, match="vorige keuze"):
        await r.async_set_wallbox_priority("global", "until_auto")
    assert r.wallbox_priority.snapshot() == old and not h.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("mutation", ["runtime", "entry", "binding", "removed"])
async def test_store_await_epoch_or_binding_change_never_activates_proposed_policy(monkeypatch, mutation):
    r, _h, _clock = ready(monkeypatch)
    old = r.wallbox_priority.snapshot()
    original_save = r.store.async_save
    async def changed(data):
        await original_save(data)
        if mutation == "runtime":
            r.entry.runtime_data = NS()
        elif mutation == "entry":
            r.hass.config_entries = NS(async_get_entry=lambda _key: NS())
        elif mutation == "binding":
            r.configs["a"]["control_entity"] = "switch.other"
        else:
            r.configs.pop("a")
    r.store.async_save = changed
    with pytest.raises(HomeAssistantError, match="gewijzigd"):
        await r.async_set_wallbox_priority("global", "1h")
    assert r.wallbox_priority.snapshot() == old
    assert not r.wallbox_priority.any_active()
    assert r.store.data["wallbox_priority"] == old


@pytest.mark.asyncio
async def test_identical_replacement_object_rejects_inflight_binding_token(monkeypatch):
    r, _h, _clock = ready(monkeypatch)
    scope = r.wallbox_priority.scope("device:a")
    r.configs["a"] = deepcopy(r.configs["a"])
    with pytest.raises(HomeAssistantError, match="gewijzigd"):
        await r.async_set_wallbox_priority("device:a", "1h", expected_scope=scope)
    assert not r.wallbox_priority.any_active() and not r.store.saves


@pytest.mark.asyncio
async def test_lock_wait_rechecks_trusted_binding_scope(monkeypatch):
    r, _h, _clock = ready(monkeypatch)
    await r._lock.acquire()
    task = asyncio.create_task(r.async_set_wallbox_priority("device:a", "until_auto"))
    await asyncio.sleep(0)
    r.configs["a"]["control_entity"] = "switch.changed"
    r._lock.release()
    with pytest.raises(HomeAssistantError, match="gewijzigd"):
        await task
    assert not r.wallbox_priority.any_active()


@pytest.mark.asyncio
async def test_new_removed_rebound_and_retired_identities_never_inherit(monkeypatch):
    r, _h, _clock = ready(monkeypatch)
    await r.async_set_wallbox_priority("global", "until_auto")
    old = deepcopy(r.configs["a"])
    r.configs["new"] = {**old, "id": "new", "control_entity": "switch.new"}
    assert not r.wallbox_priority.active("device:new")
    r.configs["a"]["control_entity"] = "switch.new_a"
    assert not r.wallbox_priority.active("device:a")
    r.wallbox_priority.retire("a")
    r.configs["a"] = old
    assert not r.wallbox_priority.active("device:a")
    assert r.wallbox_priority.active("device:second_consumer")


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [
    ("option", "7h"), ("created_at", True), ("created_at", float("nan")),
    ("created_at", 1800000001.0), ("expires_at", True),
    ("expires_at", float("inf")), ("expires_at", 1900000000.0),
    ("binding", "other"),
])
async def test_invalid_persisted_general_cannot_leave_fanout_active(monkeypatch, field, value):
    r, _h, _clock = ready(monkeypatch)
    await r.async_set_wallbox_priority("global", "1h")
    damaged = r.wallbox_priority.snapshot()
    damaged["general"][field] = value
    r.wallbox_priority.restore(damaged)
    assert not r.wallbox_priority.any_active()


@pytest.mark.asyncio
@pytest.mark.parametrize("target,option", [("a", "1h"), ("device:unknown", "1h"),
    ("wallbox", "1h"), ("global", "30min"), ("global", True), (None, "auto")])
async def test_invalid_commands_never_persist_or_call_services(monkeypatch, target, option):
    r, h, _clock = ready(monkeypatch)
    with pytest.raises((HomeAssistantError, TypeError)):
        await r.async_set_wallbox_priority(target, option)
    assert not r.store.saves and not h.services.calls
