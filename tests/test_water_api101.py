"""Water history has entry and retained-source ACLs; source links stay current-only.

These handler tests use explicit HA doubles, including both websocket schema
engines. They do not contact an installed gateway, broker or Home Assistant.
"""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace as NS

import pytest


@pytest.fixture(params=["voluptuous", "probatio"])
def apis(monkeypatch, request):
    for backend in ("voluptuous", "probatio"):
        lib = ModuleType(backend)
        lib.Required = lib.Optional = lambda key: key
        monkeypatch.setitem(sys.modules, backend, lib)
    messages = ModuleType("homeassistant.components.websocket_api.messages")
    messages.BASE_COMMAND_MESSAGE_SCHEMA = type("Schema", (), {"__module__": request.param + ".schema"})()
    monkeypatch.setitem(sys.modules, messages.__name__, messages)
    components = ModuleType("homeassistant.components")
    ws = ModuleType("homeassistant.components.websocket_api")

    def schema(definition):
        def decorate(function):
            function.test_schema = definition
            return function
        return decorate

    ws.websocket_command = schema
    ws.async_register_command = lambda hass, function: hass.registered.append(function)
    components.websocket_api = ws
    monkeypatch.setitem(sys.modules, components.__name__, components)
    monkeypatch.setitem(sys.modules, ws.__name__, ws)
    for name in ("homeassistant.auth", "homeassistant.auth.permissions", "homeassistant.auth.permissions.const"):
        module = ModuleType(name)
        module.POLICY_READ = "read"
        monkeypatch.setitem(sys.modules, name, module)

    loaded = {}
    for filename in ("water_api", "source_history_api"):
        name = "custom_components.solar_pilot._test_water101_" + filename
        path = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot" / (filename + ".py")
        spec = importlib.util.spec_from_file_location(name, path)
        module = importlib.util.module_from_spec(spec)
        monkeypatch.setitem(sys.modules, name, module)
        spec.loader.exec_module(module)
        assert module.vol.__name__ == request.param
        loaded[filename] = module
    assert loaded["water_api"].websocket_water_history.test_schema == {
        "type": "solar_pilot/water_history", "config_entry_id": str, "date": str}
    return NS(water=loaded["water_api"], sources=loaded["source_history_api"])


def forbidden(*_args, **_kwargs):
    raise AssertionError("A water history read cannot read other domains or write controls/storage")


def context(*, admin=False, allowed=()):
    settings = {"name": "Synthetic water meter", "volume_entity": "sensor.water_total",
                "flow_entity": "sensor.water_flow", "leak_entity": "binary_sensor.water_leak",
                "unapproved_entity": "sensor.unapproved_water_source"}
    retained = {"sensor.previous_water_total"}
    calls, checked, results, errors = [], [], [], []

    def detail(day):
        calls.append(day)
        return {"schema": 1, "read_only": True, "date": day or "2026-10-19",
                "observed_l": 4.5, "coverage_complete": False}

    water = NS(loaded=True, _closed=False, settings=settings, access_sources_complete=True,
        configured_sources=lambda: {settings[key] for key in ("volume_entity", "flow_entity", "leak_entity")
                                    if settings.get(key)},
        access_sources=retained, detail=detail,
        store=NS(data={"retained": "synthetic"}, async_save=forbidden),
        async_save=forbidden, observe=forbidden, reset=forbidden)
    runtime = NS(_closed=False, water=water, configs={},
                 consumer_history=NS(detail=forbidden), heatpump_history=NS(detail=forbidden),
                 analysis=NS(export=forbidden), _apply=forbidden)
    entry = NS(entry_id="entry", domain="solar_pilot", state="loaded", runtime_data=runtime,
               data={}, options={"water": {"volume_entity": "sensor.pending_water_total"}})
    runtime.entry = entry
    entries = {"entry": entry}
    hass = NS(config_entries=NS(async_get_entry=entries.get), data={}, registered=[],
              states=NS(get=forbidden), services=NS(async_call=forbidden), async_create_task=forbidden)
    allow = set(allowed)

    def check(entity, policy):
        assert policy == "read"
        checked.append(entity)
        return entity in allow

    connection = NS(user=NS(is_admin=admin, permissions=NS(check_entity=check)),
                    send_result=lambda _id, data: results.append(data),
                    send_error=lambda _id, code, message: errors.append((code, message)))
    return NS(runtime=runtime, water=water, entry=entry, entries=entries, hass=hass,
              connection=connection, out=results, errors=errors, checked=checked,
              calls=calls, retained=retained)


ALL_SOURCES = {"sensor.water_total", "sensor.water_flow", "binary_sensor.water_leak", "sensor.previous_water_total"}


def query(api, env, **extra):
    api.websocket_water_history(env.hass, env.connection,
        {"id": 7, "type": api.COMMAND, "config_entry_id": "entry", **extra})


def source_query(api, env, **extra):
    api.websocket_source_history(env.hass, env.connection,
        {"id": 8, "type": api.COMMAND, "config_entry_id": "entry", "kind": "water", **extra})


def error_codes(env):
    return [code for code, _message in env.errors]


def forbid_retained_history(env):
    class CurrentSourcesOnly(NS):
        @property
        def access_sources(self):
            return forbidden()
    attributes = dict(vars(env.water))
    attributes.pop("access_sources")
    attributes["detail"] = forbidden
    env.water = env.runtime.water = CurrentSourcesOnly(**attributes)


def test_water_history_is_entry_scoped_read_only_and_does_not_return_acl_metadata(apis):
    env = context(allowed=ALL_SOURCES)
    before = deepcopy((env.entry.data, env.entry.options, env.water.settings, env.water.store.data, env.retained))
    query(apis.water, env, date="2026-10-18")
    assert not env.errors and env.out[0]["date"] == "2026-10-18"
    assert env.calls == ["2026-10-18"] and set(env.checked) == ALL_SOURCES
    assert all(env.checked.count(source) >= 2 for source in ALL_SOURCES)  # Rechecked before publication.
    assert "access_sources" not in json.dumps(env.out) and "sensor." not in json.dumps(env.out)
    assert (env.entry.data, env.entry.options, env.water.settings, env.water.store.data, env.retained) == before


@pytest.mark.parametrize("denied", sorted(ALL_SOURCES))
def test_each_current_or_retained_source_denies_the_entire_history(apis, denied):
    env = context(allowed=ALL_SOURCES - {denied})
    query(apis.water, env)
    assert not env.out and error_codes(env) == ["unauthorized"] and not env.calls
    assert denied not in env.errors[0][1]


@pytest.mark.parametrize("state", ["incomplete", "empty", "truthy_complete", "source_failure", "malformed_source",
                                 "malformed_current", "string_container"])
def test_nonadmin_fails_closed_on_missing_or_unusable_provenance(apis, state):
    env = context(allowed=ALL_SOURCES)
    if state == "incomplete":
        env.water.access_sources_complete = False
    elif state == "empty":
        env.water.settings.clear()
        env.retained.clear()
    elif state == "truthy_complete":
        env.water.access_sources_complete = 1
    elif state == "source_failure":
        env.water.configured_sources = lambda: (_ for _ in ()).throw(RuntimeError("private source details"))
    elif state == "malformed_source":
        env.water.access_sources = {True, "sensor.previous_water_total"}
    elif state == "malformed_current":
        env.water.configured_sources = lambda: {"sensor.water_total", "sensor.private?entity_id=other"}
    else:
        env.water.access_sources = "sensor.previous_water_total"
    query(apis.water, env)
    assert not env.out and error_codes(env) == ["unauthorized"] and not env.calls
    assert "private" not in env.errors[0][1]


def test_admin_can_read_retained_history_with_incomplete_or_empty_source_provenance(apis):
    env = context(admin=True)
    env.water.access_sources_complete = False
    env.water.settings.clear()
    env.retained.clear()
    query(apis.water, env)
    assert env.out and not env.errors and not env.checked and env.calls == [None]


@pytest.mark.parametrize("permission", [1, "yes", object()])
def test_truthy_permission_results_do_not_grant_water_history_access(apis, permission):
    env = context()
    env.connection.user.permissions.check_entity = lambda _entity, _policy: permission
    query(apis.water, env)
    assert not env.out and error_codes(env) == ["unauthorized"] and not env.calls


def test_permission_exception_is_generic_and_cannot_trigger_history_or_storage(apis):
    env = context()
    env.connection.user.permissions.check_entity = lambda *_: (_ for _ in ()).throw(RuntimeError("private ACL identity"))
    query(apis.water, env)
    assert not env.out and error_codes(env) == ["unauthorized"] and not env.calls
    assert "private" not in env.errors[0][1] and env.water.store.data == {"retained": "synthetic"}


def test_anonymous_cannot_probe_entry_existence(apis):
    env = context()
    env.connection.user = None
    env.hass.config_entries.async_get_entry = forbidden
    query(apis.water, env, config_entry_id="unrelated")
    assert not env.out and error_codes(env) == ["unauthorized"]


@pytest.mark.parametrize("condition", ["missing", "wrong_domain", "unloaded", "closed", "missing_runtime",
    "different_owner", "different_id", "history_unloaded"])
def test_only_exact_loaded_entry_and_loaded_water_runtime_can_answer(apis, condition):
    env = context(admin=True)
    if condition == "missing": env.entries.clear()
    elif condition == "wrong_domain": env.entry.domain = "another_integration"
    elif condition == "unloaded": env.entry.state = NS(value="not_loaded")
    elif condition == "closed": env.runtime._closed = True
    elif condition == "missing_runtime": env.entry.runtime_data = None
    elif condition == "different_owner": env.runtime.entry = NS(**vars(env.entry))
    elif condition == "different_id": env.entry.entry_id = "different_entry"
    else: env.water.loaded = False
    query(apis.water, env)
    assert not env.out and error_codes(env) == ["not_loaded"] and not env.calls


@pytest.mark.parametrize("owner,attribute,value", [("water", "loaded", 1), ("water", "loaded", "loaded"),
    ("runtime", "_closed", 0), ("runtime", "_closed", None),
    ("water", "_closed", 0), ("water", "_closed", None), ("water", "_closed", True)])
def test_runtime_load_flags_require_explicit_boolean_evidence(apis, owner, attribute, value):
    env = context(admin=True)
    setattr(getattr(env, owner), attribute, value)
    query(apis.water, env)
    assert not env.out and error_codes(env) == ["not_loaded"] and not env.calls


@pytest.mark.parametrize("day", ["2026-2-01", "2026-02-30", "20261019", "2026-10-19T00:00:00Z",
    "2026-10-19\n", "../private", "", 4, True, [], None])
def test_history_date_requires_a_real_iso_calendar_day(apis, day):
    env = context(admin=True)
    query(apis.water, env, date=day)
    assert not env.out and error_codes(env) == ["invalid_date"] and not env.calls


@pytest.mark.parametrize("day", ["2026-10-19", "2024-02-29"])
def test_valid_iso_day_is_forwarded_without_reinterpreting_its_timezone(apis, day):
    env = context(admin=True)
    query(apis.water, env, date=day)
    assert not env.errors and env.calls == [day] and env.out[0]["date"] == day


@pytest.mark.parametrize("failure,expected", [(ValueError, "invalid_date"), (TypeError, "invalid_date"),
                                             (RuntimeError, "history_failed")])
def test_retention_or_read_failure_does_not_expose_exception_or_clear_storage(apis, failure, expected):
    env = context(admin=True)
    env.water.detail = lambda _day: (_ for _ in ()).throw(failure("private water identity"))
    query(apis.water, env)
    assert not env.out and error_codes(env) == [expected]
    assert "private" not in env.errors[0][1] and env.water.store.data == {"retained": "synthetic"}


@pytest.mark.parametrize("extra", [{"item_id": "water"}, {"device_id": "water"}, {"kind": "water"},
    {"entity_id": "sensor.unrelated"}, {"source": "sensor.unrelated"}, {"apply": True}, {"reset": True},
    {"export": True}, {"config_entry_id": ""}, {"config_entry_id": True}, {"config_entry_id": "a" * 201},
    {"type": "solar_pilot/analysis_export"}])
def test_history_query_cannot_select_other_subjects_entities_or_mutations(apis, extra):
    env = context(admin=True)
    query(apis.water, env, **extra)
    assert not env.out and error_codes(env) == ["invalid_format"] and not env.calls


@pytest.mark.parametrize("message", [None, [], "water", {}, {"id": True}, {"id": 0}, {"id": -1}, {"id": "7"}])
def test_malformed_envelopes_are_rejected_without_probing_water_data(apis, message):
    env = context(admin=True)
    if isinstance(message, dict):
        message = {"type": apis.water.COMMAND, "config_entry_id": "entry", **message}
    apis.water.websocket_water_history(env.hass, env.connection, message)
    assert not env.out and error_codes(env) == ["invalid_format"] and not env.calls


@pytest.mark.parametrize("change", ["reload", "closed", "unloaded", "water_unloaded"])
def test_detail_callback_cannot_publish_after_runtime_load_state_changes(apis, change):
    env = context(admin=True)
    original = env.water.detail
    def detail(day):
        result = original(day)
        if change == "reload": env.entries["entry"] = NS(**vars(env.entry))
        elif change == "closed": env.runtime._closed = True
        elif change == "unloaded": env.entry.state = "not_loaded"
        else: env.water.loaded = False
        return result
    env.water.detail = detail
    query(apis.water, env)
    assert not env.out and error_codes(env) == ["not_loaded"]


@pytest.mark.parametrize("change", ["current", "retained", "complete", "permission"])
def test_changed_acl_or_source_binding_during_detail_never_publishes_previous_authorization(apis, change):
    env = context(allowed=ALL_SOURCES)
    original = env.water.detail
    def detail(day):
        result = original(day)
        if change == "current": env.water.settings["volume_entity"] = "sensor.rebound_private_water"
        elif change == "retained": env.retained.add("sensor.other_private_water")
        elif change == "complete": env.water.access_sources_complete = False
        else: env.connection.user.permissions.check_entity = lambda *_: False
        return result
    env.water.detail = detail
    query(apis.water, env)
    assert not env.out and error_codes(env) == ["unauthorized"]


def test_final_permission_recheck_cannot_close_the_runtime_and_still_publish_history(apis):
    env = context(allowed=ALL_SOURCES)
    completed = [False]
    original = env.water.detail
    def detail(day):
        completed[0] = True
        return original(day)
    def check(_entity, _policy):
        if completed[0]:
            env.runtime._closed = True
        return True
    env.water.detail = detail
    env.connection.user.permissions.check_entity = check
    query(apis.water, env)
    assert not env.out and error_codes(env) == ["not_loaded"]


def test_source_links_filter_current_roles_individually_without_opening_retained_history(apis):
    env = context(allowed={"sensor.water_flow"})
    forbid_retained_history(env)
    source_query(apis.sources, env)
    assert not env.errors and env.out[0]["kind"] == "water" and "item_id" not in env.out[0]
    assert env.out[0]["read_only"] is True and env.out[0]["scope"] == "current_configured_sources"
    assert [(row["role"], row["entity_id"]) for row in env.out[0]["sources"]] == [
        ("flow_entity", "sensor.water_flow")]
    assert set(env.checked) == {"sensor.water_total", "sensor.water_flow", "binary_sensor.water_leak"}
    assert "previous_water" not in json.dumps(env.out) and "unapproved_water" not in json.dumps(env.out)


@pytest.mark.parametrize("extra", [{"item_id": "water"}, {"source": "configured"}, {"date": "2026-10-19"},
                                    {"entity_id": "sensor.unrelated"}, {"reset": True}])
def test_water_source_catalogue_accepts_no_item_source_history_or_write_parameters(apis, extra):
    env = context(admin=True)
    source_query(apis.sources, env, **extra)
    assert not env.out and error_codes(env) == ["invalid_format"] and not env.calls


def test_water_source_catalogue_returns_only_configured_approved_roles_and_preserves_options(apis):
    env = context(admin=True)
    forbid_retained_history(env)
    before = deepcopy((env.entry.options, env.water.settings, env.water.store.data))
    source_query(apis.sources, env)
    assert not env.errors and {row["role"] for row in env.out[0]["sources"]} == {
        "volume_entity", "flow_entity", "leak_entity"}
    assert (env.entry.options, env.water.settings, env.water.store.data) == before
    assert not env.checked and not env.calls


def test_water_source_rebind_during_permissions_discards_obsolete_links(apis):
    env = context()
    def check(_entity, _policy):
        env.water.settings["flow_entity"] = "sensor.rebound_water_flow"
        return True
    env.connection.user.permissions.check_entity = check
    source_query(apis.sources, env)
    assert not env.out and error_codes(env) == ["sources_changed"]


def test_registration_is_idempotent_for_both_read_only_water_endpoints(apis):
    env = context(admin=True)
    apis.water.async_register_water_history_api(env.hass)
    apis.water.async_register_water_history_api(env.hass)
    apis.sources.async_register_source_history_api(env.hass)
    apis.sources.async_register_source_history_api(env.hass)
    assert env.hass.registered == [apis.water.websocket_water_history, apis.sources.websocket_source_history]
