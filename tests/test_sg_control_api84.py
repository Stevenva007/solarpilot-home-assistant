"""Native SG policy service/select validation and captured runtime authority."""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace as NS

import pytest
import voluptuous as vol

from homeassistant.exceptions import HomeAssistantError
from custom_components.solar_pilot.sg_control_api import (
    SG_MANUAL_OPTIONS, SG_MANUAL_SERVICE_SCHEMA, async_handle_sg_manual_control,
    async_set_sg_manual_control, validate_manual_control,
)


def context(*, user_id="admin", is_admin=True):
    calls = []

    async def command(mode, duration_s=None):
        calls.append((mode, duration_s))

    async def user(_user_id):
        return NS(is_admin=is_admin)

    entry = NS(entry_id="example", runtime_data=None)
    hass = NS(auth=NS(async_get_user=user), config_entries=NS(async_entries=lambda _: [entry]))
    runtime = NS(entry=entry, hass=hass, _closed=False, data_loaded=True,
                 sg_boost=NS(set_manual_control=command))
    entry.runtime_data = runtime
    return runtime, hass, NS(user_id=user_id), calls


@pytest.mark.parametrize("mode,duration", [("auto", None), ("on", 1800), ("on", 3600),
                                           ("off", 1800), ("off", 3600)])
def test_reviewed_native_service_schema_has_exact_five_choices(mode, duration):
    data = {"config_entry_id": "example", "mode": mode}
    if duration is not None:
        data["duration_s"] = duration
    assert SG_MANUAL_SERVICE_SCHEMA(data) == data
    assert validate_manual_control(mode, duration) == (mode, duration)


@pytest.mark.parametrize("data", [
    {}, {"mode": None}, {"mode": True}, {"mode": 1}, {"mode": "ON"}, {"mode": "on_30"},
    {"mode": "auto", "duration_s": None}, {"mode": "auto", "duration_s": 0},
    {"mode": "on"}, {"mode": "on", "duration_s": None}, {"mode": "on", "duration_s": True},
    {"mode": "on", "duration_s": 1800.0}, {"mode": "on", "duration_s": "1800"},
    {"mode": "off", "duration_s": 3600.0}, {"mode": "off", "duration_s": float("inf")},
    {"mode": "off", "duration_s": float("nan")}, {"mode": "off", "duration_s": -1800},
    {"mode": "off", "duration_s": 300}, {"mode": "on", "duration_s": 7200},
    {"mode": "auto", "config_entry_id": True}, {"mode": "auto", "force": True},
    {"mode": "on", "duration_s": 1800, "entity_id": "switch.fictional_sg"},
])
def test_service_schema_never_coerces_or_accepts_unreviewed_choices(data):
    with pytest.raises(vol.Invalid):
        SG_MANUAL_SERVICE_SCHEMA(data)


@pytest.mark.asyncio
@pytest.mark.parametrize("mode,duration", [("auto", None), ("on", 1800), ("on", 3600),
                                           ("off", 1800), ("off", 3600)])
async def test_admin_native_service_only_dispatches_reviewed_policy(mode, duration):
    _, hass, admin, calls = context()
    data = {"config_entry_id": "example", "mode": mode}
    if duration is not None:
        data["duration_s"] = duration
    await async_handle_sg_manual_control(hass, NS(data=data, context=admin))
    assert calls == [(mode, duration)]


@pytest.mark.asyncio
@pytest.mark.parametrize("user_state", [None, NS(is_admin=False)])
async def test_non_admin_service_and_select_guard_cannot_dispatch(user_state):
    runtime, hass, user_context, calls = context(is_admin=False)

    async def user(_user_id):
        return user_state

    hass.auth.async_get_user = user
    with pytest.raises(HomeAssistantError, match="beheerder"):
        await async_handle_sg_manual_control(hass, NS(data={"mode": "on", "duration_s": 1800}, context=user_context))
    assert not calls
    with pytest.raises(HomeAssistantError, match="beheerder"):
        await async_set_sg_manual_control(runtime, "off", 3600, context=user_context)
    assert not calls


@pytest.mark.asyncio
@pytest.mark.parametrize("changed", ["closed", "replacement"])
async def test_auth_wait_cannot_send_command_from_retired_runtime(changed):
    runtime, hass, admin, calls = context()
    admitted, release = asyncio.Event(), asyncio.Event()

    async def user(_user_id):
        admitted.set()
        await release.wait()
        return NS(is_admin=True)

    hass.auth.async_get_user = user
    task = asyncio.create_task(async_set_sg_manual_control(runtime, "on", 1800, context=admin))
    await admitted.wait()
    if changed == "closed":
        runtime._closed = True
    else:
        runtime.entry.runtime_data = NS(_closed=False)
    release.set()
    with pytest.raises(HomeAssistantError, match="vernieuw"):
        await task
    assert not calls


@pytest.mark.asyncio
async def test_internal_home_assistant_automation_has_the_standard_admin_service_semantics():
    runtime, _, automation, calls = context(user_id=None)
    await async_set_sg_manual_control(runtime, "off", 1800, context=automation)
    assert calls == [("off", 1800)]


@pytest.mark.asyncio
@pytest.mark.parametrize("entries", [0, 2])
async def test_ambiguous_or_missing_entry_cannot_dispatch(entries):
    runtime, hass, admin, calls = context()
    hass.config_entries.async_entries = lambda _: [runtime.entry] * entries
    with pytest.raises(HomeAssistantError, match="één geladen"):
        await async_handle_sg_manual_control(hass, NS(data={"mode": "off", "duration_s": 1800}, context=admin))
    assert not calls


def select_class():
    """Execute the actual shipped entity classes against narrow HA doubles."""
    source = Path(__file__).parents[1] / "custom_components/solar_pilot/select.py"

    class Entity:
        def __init__(self, runtime, suffix, name, key=None):
            self.runtime, self.suffix, self.key = runtime, suffix, key

        def _inactive(self):
            return self.runtime._closed

    namespace = {"SolarEntity": Entity, "SelectEntity": type("SelectEntity", (), {}),
                 "SG_MANUAL_OPTIONS": SG_MANUAL_OPTIONS,
                 "async_set_sg_manual_control": async_set_sg_manual_control}
    nodes = [node for node in ast.parse(source.read_text()).body if isinstance(node, ast.ClassDef)]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace["SGManualControl"]


@pytest.mark.asyncio
@pytest.mark.parametrize("option,expected", [("auto", ("auto", None)), ("on_30", ("on", 1800)),
    ("on_60", ("on", 3600)), ("off_30", ("off", 1800)), ("off_60", ("off", 3600))])
async def test_native_select_uses_same_user_context_and_strict_controller_contract(option, expected):
    runtime, _, admin, calls = context()
    entity = select_class()(runtime)
    entity._context = admin
    await entity.async_select_option(option)
    assert calls == [expected]


@pytest.mark.asyncio
async def test_native_select_does_not_bypass_admin_policy():
    runtime, _, non_admin, calls = context(is_admin=False)
    entity = select_class()(runtime)
    entity._context = non_admin
    with pytest.raises(HomeAssistantError, match="beheerder"):
        await entity.async_select_option("on_30")
    assert not calls


@pytest.mark.asyncio
@pytest.mark.parametrize("option", [True, None, "on", "off_5", "on_120", "Aan 30 min"])
async def test_native_select_rejects_unreviewed_option_before_any_call(option):
    runtime, _, _, calls = context()
    with pytest.raises(HomeAssistantError):
        await select_class()(runtime).async_select_option(option)
    assert not calls


@pytest.mark.parametrize("manual,expected", [
    ({"mode": "auto", "duration_s": None}, "auto"),
    ({"mode": "on", "duration_s": 1800}, "on_30"),
    ({"mode": "off", "duration_s": 3600}, "off_60"),
    ({"mode": "on", "duration_s": True}, None),
    ({"mode": "on", "duration_s": 1800.0}, None),
    ({}, None),
])
def test_native_select_reports_backend_mode_without_inventing_auto_or_duration(manual, expected):
    runtime, _, _, _ = context()
    runtime.sg_boost.configured = True
    runtime.sg_boost.manual_control_overview = lambda: manual
    entity = select_class()(runtime)
    assert entity.current_option == expected
    assert entity.available


def test_registration_uses_home_assistant_admin_helper_and_preserves_select_registry_id():
    source = (Path(__file__).parents[1] / "custom_components/solar_pilot/__init__.py").read_text()
    assert "async_register_admin_service(" in source
    tree = ast.parse(source)
    setup = next(node for node in tree.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "_async_setup_entry")
    registrations = [node for node in ast.walk(setup) if isinstance(node, ast.Call)
                     and isinstance(node.func, ast.Name) and node.func.id == "async_register_admin_service"]
    assert len(registrations) == 1
    assert isinstance(registrations[0].args[2], ast.Name)
    assert registrations[0].args[2].id == "SERVICE_SG_MANUAL_CONTROL"
    assert '"sg_manual_control"' in source[source.index("hub_suffixes.update({\"dhw_status\""):]
