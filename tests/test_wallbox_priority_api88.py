"""All exposed priority commands use current scoped admin policy authority."""
from __future__ import annotations

import ast
import asyncio
from pathlib import Path
from types import SimpleNamespace as NS
from copy import deepcopy

import pytest
import voluptuous as vol

from homeassistant.exceptions import HomeAssistantError
from custom_components.solar_pilot.wallbox_priority_api import (
    WALLBOX_PRIORITY_OPTIONS, WALLBOX_PRIORITY_SERVICE_SCHEMA,
    async_handle_wallbox_priority_control, async_set_wallbox_priority,
    priority_choice_view, validate_priority_choice, websocket_wallbox_priority,
)

ROOT = Path(__file__).parents[1] / "custom_components/solar_pilot"


def build(*, admin=True, user_id="admin"):
    calls = []
    entry = NS(entry_id="example", domain="solar_pilot", runtime_data=None)

    async def user(key):
        return NS(id=key, is_admin=admin)

    hass = NS(auth=NS(async_get_user=user),
              config_entries=NS(async_get_entry=lambda key: entry if key == entry.entry_id else None,
                                async_entries=lambda _: [entry]))
    runtime = NS(entry=entry, hass=hass, data_loaded=True, _closed=False, mode="observe",
                 configs={"load": {"id": "load", "name": "Flexible load", "kind": "switch"},
                          "dish": {"id": "dish", "name": "Dishwasher", "kind": "dishwasher"}},
                 sg_boost=NS(settings={"enabled": True}), wallbox_settings={"enabled": True})
    entry.runtime_data = runtime

    def row(target):
        return {"target": target, "option": "auto", "active": False, "eligible": True,
                "remaining_s": 0, "expires_at": None, "duration_s": None, "indefinite": False}

    def overview():
        return {"general": row("global"), "devices": {key: row("device:" + key)
                for key, cfg in runtime.configs.items() if cfg.get("kind") != "dishwasher"},
                "sg_boost": None, "observed_at": 1000, "available": True}

    def scope(target):
        profiles = (runtime.configs if target == "global" else
                    {target[7:]: runtime.configs.get(target[7:])} if target.startswith("device:") else {})
        sg = {}  # SG is outside every Wallbox preference scope.
        return deepcopy((profiles, sg, runtime.wallbox_settings))

    runtime.wallbox_priority = NS(overview=overview, scope=scope)

    async def command(target, option, *, context=None, expected_scope=None):
        assert expected_scope == scope(target)
        calls.append((target, option, getattr(context, "user_id", None)))
        return overview()

    runtime.async_set_wallbox_priority = command
    return runtime, hass, NS(user_id=user_id), calls


@pytest.mark.parametrize("target", ["global", "device:load", "dhw_extra"])
@pytest.mark.parametrize("option", WALLBOX_PRIORITY_OPTIONS)
def test_service_schema_has_exact_scoped_choices(target, option):
    data = {"config_entry_id": "example", "target": target, "option": option}
    assert WALLBOX_PRIORITY_SERVICE_SCHEMA(data) == data


@pytest.mark.parametrize("data", [
    {}, {"target": "global"}, {"option": "auto"},
    {"target": None, "option": "auto"}, {"target": True, "option": "auto"},
    {"target": 1, "option": "auto"}, {"target": "device:", "option": "auto"},
    {"target": "unknown", "option": "auto"}, {"target": "switch.some_load", "option": "30m"},
    {"target": "global", "option": None}, {"target": "global", "option": True},
    {"target": "global", "option": 1800}, {"target": "global", "option": "1800"},
    {"target": "global", "option": "6h"}, {"target": "global", "option": "forever"},
    {"target": "global", "option": "AUTO"}, {"target": "global", "option": "30 min"},
    {"target": "global", "option": "auto", "duration_s": None},
    {"target": "global", "option": "auto", "config_entry_id": ""},
    {"target": "global", "option": "auto", "config_entry_id": True},
    {"target": "global", "option": "auto", "user_id": "admin"},
    {"target": "global", "option": "auto", "context": {"user_id": "admin"}},
    {"target": "global", "option": "30m", "entity_id": "switch.charger"},
])
def test_service_does_not_coerce_unknown_choices_or_accept_spoofing(data):
    with pytest.raises(vol.Invalid):
        WALLBOX_PRIORITY_SERVICE_SCHEMA(data)


@pytest.mark.asyncio
@pytest.mark.parametrize("option", WALLBOX_PRIORITY_OPTIONS)
async def test_admin_service_uses_scoped_policy_only_in_observer_mode(option):
    runtime, hass, context, calls = build()
    result = await async_handle_wallbox_priority_control(hass, NS(
        data={"config_entry_id": "example", "target": "device:load", "option": option}, context=context))
    assert calls == [("device:load", option, "admin")]
    assert result["general"]["target"] == "global"
    assert runtime.mode == "observe"


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["global", "device:load"])
async def test_non_admin_and_read_only_user_cannot_modify_any_scope(target):
    runtime, _, context, calls = build(admin=False)
    with pytest.raises(HomeAssistantError, match="beheerder"):
        await async_set_wallbox_priority(runtime, target, "30m", context=context)
    assert not calls


@pytest.mark.asyncio
@pytest.mark.parametrize("user_id", ["deleted", True, ""])
async def test_deleted_or_malformed_user_is_not_trusted(user_id):
    runtime, hass, context, calls = build(user_id=user_id)

    async def user(_):
        return None

    hass.auth.async_get_user = user
    with pytest.raises(HomeAssistantError, match="beheerder"):
        await async_set_wallbox_priority(runtime, "global", "auto", context=context)
    assert not calls


@pytest.mark.asyncio
async def test_trusted_home_assistant_automation_uses_standard_admin_service_semantics():
    runtime, _, context, calls = build(user_id=None)
    await async_set_wallbox_priority(runtime, "global", "auto", context=context)
    assert calls == [("global", "auto", None)]


@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["device:dish", "device:removed", "device:sg_boost", "dhw_extra"])
async def test_removed_dishwasher_and_invented_targets_are_rejected(target):
    runtime, _, context, calls = build()
    with pytest.raises(HomeAssistantError, match="bestaat niet"):
        await async_set_wallbox_priority(runtime, target, "1h", context=context)
    assert not calls


@pytest.mark.asyncio
@pytest.mark.parametrize("change", ["closed", "entry_none", "replacement", "registry", "unloaded",
                                    "removed", "dishwasher", "rebind", "wallbox_rebind"])
async def test_auth_wait_never_adopts_stale_runtime_or_rebound_profile(change):
    runtime, hass, context, calls = build()
    admitted, release = asyncio.Event(), asyncio.Event()

    async def user(_):
        admitted.set()
        await release.wait()
        return NS(is_admin=True)

    hass.auth.async_get_user = user
    target = "device:load"
    task = asyncio.create_task(async_set_wallbox_priority(runtime, target, "2h", context=context))
    await admitted.wait()
    if change == "closed":
        runtime._closed = True
    elif change == "entry_none":
        runtime.entry = None
    elif change == "replacement":
        runtime.entry.runtime_data = NS()
    elif change == "registry":
        hass.config_entries.async_get_entry = lambda _: NS()
    elif change == "unloaded":
        runtime.data_loaded = False
    elif change == "removed":
        runtime.configs.pop("load")
    elif change == "dishwasher":
        runtime.configs["load"]["kind"] = "dishwasher"
    elif change == "rebind":
        runtime.configs["load"]["control_entity"] = "switch.new_binding"
    elif change == "wallbox_rebind":
        runtime.wallbox_settings["power_entity"] = "sensor.new_binding"
    else:
        runtime.sg_boost.settings["entity_id"] = "switch.new_sg_binding"
    release.set()
    with pytest.raises(HomeAssistantError):
        await task
    assert not calls


@pytest.mark.asyncio
@pytest.mark.parametrize("count", [0, 2])
async def test_service_requires_unambiguous_entry(count):
    runtime, hass, context, calls = build()
    hass.config_entries.async_entries = lambda _: [runtime.entry] * count
    with pytest.raises(HomeAssistantError, match="één geladen"):
        await async_handle_wallbox_priority_control(hass, NS(
            data={"target": "global", "option": "30m"}, context=context))
    assert not calls


def connection(*, admin=True, user_id="admin"):
    results, errors = [], []
    return NS(user=NS(is_admin=admin, id=user_id), send_result=lambda *args: results.append(args),
              send_error=lambda *args: errors.append(args)), results, errors


@pytest.mark.asyncio
@pytest.mark.parametrize("option", WALLBOX_PRIORITY_OPTIONS)
async def test_websocket_uses_only_actual_connection_identity(option):
    _, hass, _, calls = build()
    conn, results, errors = connection()
    await websocket_wallbox_priority(hass, conn, {"id": 1, "type": "solar_pilot/wallbox_priority",
        "config_entry_id": "example", "target": "global", "option": option})
    assert calls == [("global", option, "admin")] and len(results) == 1 and not errors


@pytest.mark.asyncio
@pytest.mark.parametrize("who", ["non_admin", "none", "missing_id", "spoofed", "revoked"])
async def test_websocket_never_promotes_read_only_or_spoofed_user(who):
    _, hass, _, calls = build(admin=who != "revoked")
    conn, results, errors = connection(admin=who != "non_admin", user_id=None if who == "missing_id" else "admin")
    if who == "none":
        conn.user = None
    msg = {"id": 1, "config_entry_id": "example", "target": "global", "option": "30m"}
    if who == "spoofed":
        msg["user_id"] = "another_admin"
    await websocket_wallbox_priority(hass, conn, msg)
    assert errors and not results and not calls


def entity_namespace(filename):
    class Entity:
        def __init__(self, runtime, suffix, name, key=None):
            self.runtime, self.suffix, self.key = runtime, suffix, key
            self._attr_name = name

        def _inactive(self):
            return getattr(self, "_solar_pilot_retired", False) or self.runtime._closed

    namespace = {"SolarEntity": Entity, "SelectEntity": type("SelectEntity", (), {}),
                 "SwitchEntity": type("SwitchEntity", (), {}), "SG_MANUAL_OPTIONS": (),
                 "MODES": ["observe", "solar", "paused"], "DEVICE_MODES": ["auto", "disabled"],
                 "WALLBOX_PRIORITY_OPTIONS": WALLBOX_PRIORITY_OPTIONS,
                 "async_set_wallbox_priority": async_set_wallbox_priority,
                 "priority_choice_view": priority_choice_view}
    tree = ast.parse((ROOT / filename).read_text())
    nodes = [node for node in tree.body if isinstance(node, ast.ClassDef)
             or isinstance(node, ast.FunctionDef) and node.name == "_entities"]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(ROOT / filename), "exec"), namespace)
    return namespace


@pytest.mark.asyncio
@pytest.mark.parametrize("target,key,sg", [("global", None, False), ("device:load", "load", False)])
@pytest.mark.parametrize("on,option", [(True, "30m"), (False, "auto")])
async def test_native_switch_on_default_and_off_share_authenticated_helper(target, key, sg, on, option):
    runtime, _, context, calls = build()
    entity = entity_namespace("switch.py")["WallboxPrioritySwitch"](runtime, key, sg=sg)
    entity._context = context
    await (entity.async_turn_on() if on else entity.async_turn_off())
    assert calls == [(target, option, "admin")]
    assert entity.extra_state_attributes["on_duration_s"] == 1800
    assert entity.extra_state_attributes["wallbox_read_only"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("option", WALLBOX_PRIORITY_OPTIONS)
async def test_native_duration_select_dispatches_same_explicit_choices(option):
    runtime, _, context, calls = build()
    entity = entity_namespace("select.py")["WallboxPriorityDuration"](runtime, "load")
    entity._context = context
    await entity.async_select_option(option)
    assert calls == [("device:load", option, "admin")]
    assert entity.current_option == "auto" and entity.available


@pytest.mark.asyncio
@pytest.mark.parametrize("filename,classname", [("select.py", "WallboxPriorityDuration"),
                                               ("switch.py", "WallboxPrioritySwitch")])
@pytest.mark.parametrize("retired", [True, False])
async def test_native_entities_do_not_bypass_read_only_or_retirement(filename, classname, retired):
    runtime, _, context, calls = build(admin=False)
    entity = entity_namespace(filename)[classname](runtime, "load")
    entity._context = context
    entity._solar_pilot_retired = retired
    with pytest.raises(HomeAssistantError):
        await (entity.async_select_option("1h") if filename == "select.py" else entity.async_turn_on())
    assert not calls


@pytest.mark.parametrize("filename,classname", [("select.py", "WallboxPriorityDuration"),
                                               ("switch.py", "WallboxPrioritySwitch")])
def test_live_entity_factories_exclude_all_dishwashers(filename, classname):
    runtime, _, _, _ = build()
    namespace = entity_namespace(filename)
    entities = namespace["_entities"](runtime)
    priorities = [row for row in entities if isinstance(row, namespace[classname])]
    assert {row.target for row in priorities} == {"global", "device:load"}
    assert {row.suffix for row in priorities} == {"wallbox_priority"}
    assert priority_choice_view(runtime, "device:dish") is None


def test_registration_is_admin_scoped_and_service_is_removed_only_with_last_entry():
    source = (ROOT / "wallbox_priority_api.py").read_text()
    assert "async_register_admin_service(hass, DOMAIN, SERVICE_WALLBOX_PRIORITY_CONTROL" in source
    assert '"probatio"' in source and "websocket_api.async_response" in source
    init = (ROOT / "__init__.py").read_text()
    assert "async_register_wallbox_priority_api(hass)" in init
    assert 'hub_suffixes.update({"wallbox_priority", "wallbox_priority_sg"})' in init
    remove = ast.parse(init)
    remove = next(node for node in remove.body if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_remove_entry")
    assert "SERVICE_WALLBOX_PRIORITY_CONTROL" in ast.unparse(remove)


@pytest.mark.asyncio
@pytest.mark.parametrize("option", WALLBOX_PRIORITY_OPTIONS)
async def test_real_policy_manager_receives_captured_scope_without_actuator_or_mode_change(option):
    from test_runtime import build as runtime_build
    runtime, hass = runtime_build()
    runtime.entry.domain = "solar_pilot"
    runtime.entry.runtime_data = runtime
    runtime.data_loaded = True
    runtime.wallbox_settings["enabled"] = True
    hass.config_entries = NS(async_get_entry=lambda _: runtime.entry)

    async def admin(_):
        return NS(is_admin=True)

    hass.auth = NS(async_get_user=admin)
    result = await async_set_wallbox_priority(runtime, "device:a", option, context=NS(user_id="admin"))
    assert result["devices"]["a"]["option"] == option
    assert runtime.wallbox_priority.overview()["devices"]["a"]["active"] is (option != "auto")
    assert runtime.mode == "observe" and not hass.services.calls


@pytest.mark.parametrize("backend", ["voluptuous", "probatio"])
def test_registration_matches_live_schema_backend_and_is_idempotent(monkeypatch, backend):
    import sys
    from types import ModuleType
    from custom_components.solar_pilot.wallbox_priority_api import async_register_wallbox_priority_api

    calls, registered = [], []
    messages = ModuleType("homeassistant.components.websocket_api.messages")
    messages.BASE_COMMAND_MESSAGE_SCHEMA = type("Schema", (), {"__module__": backend + ".schema"})()
    monkeypatch.setitem(sys.modules, messages.__name__, messages)
    components = ModuleType("homeassistant.components")
    websocket = ModuleType("homeassistant.components.websocket_api")
    websocket.websocket_command = lambda schema: lambda fn: fn
    websocket.async_response = lambda fn: fn
    websocket.async_register_command = lambda h, fn: registered.append(fn)
    components.websocket_api = websocket
    monkeypatch.setitem(sys.modules, components.__name__, components)
    monkeypatch.setitem(sys.modules, websocket.__name__, websocket)
    if backend == "probatio":
        probatio = ModuleType("probatio")
        probatio.Required = lambda key: key
        monkeypatch.setitem(sys.modules, "probatio", probatio)
    service = ModuleType("homeassistant.helpers.service")

    def register(hass, domain, name, handle, *, schema):
        calls.append((domain, name, schema))
        hass.services.exists = True

    service.async_register_admin_service = register
    monkeypatch.setitem(sys.modules, service.__name__, service)
    hass = NS(data={}, services=NS(exists=False))
    hass.services.has_service = lambda *args: hass.services.exists
    async_register_wallbox_priority_api(hass)
    async_register_wallbox_priority_api(hass)
    assert len(registered) == len(calls) == 1
    assert calls[0][:2] == ("solar_pilot", "wallbox_priority_control")
    assert calls[0][2] is WALLBOX_PRIORITY_SERVICE_SCHEMA
