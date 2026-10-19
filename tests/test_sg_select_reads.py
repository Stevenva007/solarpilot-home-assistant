"""Native SG selection reads stay cheap without caching timed policy state."""
from types import SimpleNamespace as NS
from unittest.mock import Mock

import pytest

from test_sg_control_api84 import select_class
from test_sg_controller62 import Clock, fixture


CHOICES = [("auto", "auto", None), ("on_30", "on", 1800),
           ("on_60", "on", 3600), ("off_30", "off", 1800),
           ("off_60", "off", 3600)]
AUTO = {"mode": "auto", "duration_s": None, "expires_at": None,
        "remaining_s": 0, "active": False, "returns_to": "auto"}


async def select_environment(mode="auto", duration=None):
    manager, adapter, clock, runtime = fixture()
    wall = Clock()
    wall.advance(1000)
    manager._wall_clock = wall
    runtime._closed, runtime.data_loaded = False, True
    await manager.set_manual_control(mode, duration)
    return NS(manager=manager, adapter=adapter, clock=clock, wall=wall,
              runtime=runtime, entity=select_class()(runtime))


def forbid_getter_work(monkeypatch, env):
    forbidden = Mock(side_effect=AssertionError("A selection read performed unrelated work"))
    for owner, names in (
            (env.manager, ("overview",)),
            (env.runtime.panasonic, ("overview",)),
            (env.adapter, ("get_status", "set_on", "set_off")),
            (env.runtime.store, ("async_save",)),
            (env.runtime, ("note", "publish", "sensor_overview"))):
        for name in names:
            monkeypatch.setattr(owner, name, forbidden, raising=False)
    monkeypatch.setattr(env.runtime.hass, "services", NS(async_call=forbidden), raising=False)
    return forbidden


@pytest.mark.asyncio
@pytest.mark.parametrize("option,mode,duration", CHOICES)
async def test_select_reads_all_choices_without_full_overviews_or_actions(monkeypatch, option, mode, duration):
    env = await select_environment(mode, duration)
    expected = (dict(AUTO) if mode == "auto" else {
        "mode": mode, "duration_s": duration, "expires_at": env.wall()+duration,
        "remaining_s": duration, "active": True, "returns_to": "auto"})
    assert env.manager.manual_control_overview() == env.manager.overview()["manual_control"] == expected
    before = env.manager.snapshot()
    forbidden = forbid_getter_work(monkeypatch, env)

    for _ in range(2):
        assert env.entity.available is True
        assert env.entity.current_option == option
        assert env.entity.extra_state_attributes == {
            "expires_at": expected["expires_at"], "remaining_s": expected["remaining_s"],
            "active": expected["active"], "reason": None}
        assert env.manager.manual_control_overview() == expected

    forbidden.assert_not_called()
    assert env.manager.snapshot() == before


@pytest.mark.asyncio
@pytest.mark.parametrize("option,mode,duration", CHOICES[1:])
@pytest.mark.parametrize("deadline_clock", ["clock", "wall"])
async def test_select_expires_at_either_deadline_without_tick_or_publish(
        monkeypatch, option, mode, duration, deadline_clock):
    env = await select_environment(mode, duration)
    before = env.manager.snapshot()
    deadline = env.manager._manual_deadline
    with monkeypatch.context() as reads:
        forbidden = forbid_getter_work(reads, env)
        advancing = getattr(env, deadline_clock)
        advancing.advance(duration-0.25)
        assert env.entity.current_option == option
        assert env.entity.extra_state_attributes["remaining_s"] == 1
        advancing.advance(0.25)
        assert env.entity.current_option == "auto"
        assert env.entity.extra_state_attributes == {
            "expires_at": None, "remaining_s": 0, "active": False, "reason": None}
        assert env.manager.manual_control_overview() == AUTO
        assert env.entity.available is True
        forbidden.assert_not_called()
        assert env.manager.snapshot() == before
        assert env.manager._manual_deadline == deadline

    assert env.manager.overview()["manual_control"] == env.manager.manual_control_overview() == AUTO


@pytest.mark.asyncio
@pytest.mark.parametrize("state,available", [
    ("active", True), ("closed", False), ("inactive", False),
    ("not_loaded", False), ("not_configured", False), ("auto_disabled", True),
])
async def test_select_availability_preserves_existing_guards_without_diagnostics(monkeypatch, state, available):
    env = await select_environment()
    if state == "closed":
        env.runtime._closed = True
    elif state == "inactive":
        monkeypatch.setattr(env.entity, "_inactive", lambda: True)
    elif state == "not_loaded":
        env.runtime.data_loaded = False
    elif state == "not_configured":
        env.manager.settings["entity_id"] = ""
    elif state == "auto_disabled":
        env.manager.settings["enabled"] = False
    forbidden = forbid_getter_work(monkeypatch, env)

    assert env.entity.available is available
    assert env.entity.current_option == "auto"
    assert env.entity.extra_state_attributes == {
        "expires_at": None, "remaining_s": 0, "active": False, "reason": None}
    forbidden.assert_not_called()
