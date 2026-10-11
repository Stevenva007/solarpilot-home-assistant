"""Both HA websocket schema engines and historical source READ isolation."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

from test_runtime import build


@pytest.fixture(params=["voluptuous", "probatio"])
def api(monkeypatch, request):
    for backend in ("voluptuous", "probatio"):
        lib = ModuleType(backend)
        lib.Required = lib.Optional = lambda key: key
        monkeypatch.setitem(sys.modules, backend, lib)
    messages = ModuleType("homeassistant.components.websocket_api.messages")
    messages.BASE_COMMAND_MESSAGE_SCHEMA = type("Schema", (), {"__module__": request.param+".schema"})()
    monkeypatch.setitem(sys.modules, messages.__name__, messages)
    components, ws = ModuleType("homeassistant.components"), ModuleType("homeassistant.components.websocket_api")
    def schema(definition):
        def wrap(func):
            func.test_schema = definition
            return func
        return wrap
    ws.websocket_command = schema
    ws.async_register_command = lambda hass, func: hass.registered.append(func)
    components.websocket_api = ws
    monkeypatch.setitem(sys.modules, components.__name__, components)
    monkeypatch.setitem(sys.modules, ws.__name__, ws)
    for name in ("homeassistant.auth", "homeassistant.auth.permissions", "homeassistant.auth.permissions.const"):
        mod = ModuleType(name)
        mod.POLICY_READ = "read"
        monkeypatch.setitem(sys.modules, name, mod)
    path = Path(__file__).resolve().parents[1]/"custom_components/solar_pilot/heatpump_history_api.py"
    name = "custom_components.solar_pilot._test_heatpump_history_api70"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    assert module.vol.__name__ == request.param
    assert module.websocket_heatpump_history.test_schema == {
        "type": "solar_pilot/heatpump_history", "config_entry_id": str, "date": str}
    return module


def context(admin=True, allowed=True):
    r, h = build()
    r.entry.domain, r.entry.state, r.entry.runtime_data = "solar_pilot", "loaded", r
    r.heatpump_history.loaded = r.heatpump_history._writable = True
    r.heatpump_history.now = lambda: datetime(2026, 10, 11, 8, tzinfo=timezone.utc)
    r.panasonic.settings.update(power_entity="sensor.hp_total", tank_target_entity="water_heater.hp_tank",
                                compressor_frequency_entity="sensor.hp_compressor", zone_entities=["climate.hp_zone"])
    r.sg_boost.settings["entity_id"] = "switch.sg_contact"
    h.config_entries = SimpleNamespace(async_get_entry=lambda ident: r.entry if ident == "test" else None)
    h.data, h.registered = {}, []
    out, errors, checked = [], [], []
    def check(entity, policy):
        checked.append((entity, policy))
        return allowed if isinstance(allowed, bool) else entity in allowed
    user = SimpleNamespace(is_admin=admin, permissions=SimpleNamespace(check_entity=check))
    connection = SimpleNamespace(user=user, send_result=lambda ident, result: out.append(result),
                                 send_error=lambda ident, code, msg: errors.append((code, msg)))
    return r, h, connection, out, errors, checked


def query(api, h, c, **extra):
    api.websocket_heatpump_history(h, c, {"id": 1, "type": api.COMMAND, "config_entry_id": "test", **extra})


def test_selected_entry_history_is_read_only_and_contains_no_acl_or_source_bindings(api):
    r, h, c, out, errors, _ = context()
    before = deepcopy((r.entry.data, r.entry.options, r._snapshot(), h.services.calls))
    query(api, h, c, date="2026-10-10")
    assert not errors and out[0]["device_id"] == "heatpump" and out[0]["date"] == "2026-10-10"
    assert set(out[0]["sg"]) == {"request", "contact", "received"}
    assert all(field in out[0] for field in ("task_sessions", "task_totals", "energy_kwh", "energy_known_s"))
    assert "sensor.hp_total" not in json.dumps(out) and "access_sources" not in json.dumps(out)
    assert (r.entry.data, r.entry.options, r._snapshot(), h.services.calls) == before


def test_all_configured_and_historical_sources_require_read_permission(api):
    r, h, c, out, errors, checked = context(admin=False)
    r.heatpump_history.access_sources.add("sensor.old_restricted_hp")
    query(api, h, c)
    assert out and not errors
    assert set(checked) == {(entity, "read") for entity in (
        "sensor.hp_total", "water_heater.hp_tank", "sensor.hp_compressor", "climate.hp_zone",
        "switch.sg_contact", "sensor.old_restricted_hp")}
    out.clear()
    c.user.permissions.check_entity = lambda entity, policy: entity != "sensor.old_restricted_hp"
    query(api, h, c)
    assert not out and errors[-1][0] == "unauthorized"
    assert "sensor.old_restricted_hp" not in errors[-1][1]


@pytest.mark.parametrize("source", ["sensor.hp_total", "water_heater.hp_tank", "sensor.hp_compressor", "climate.hp_zone", "switch.sg_contact"])
def test_denied_current_source_denies_entire_history(api, source):
    _, h, c, out, errors, _ = context(admin=False)
    c.user.permissions.check_entity = lambda entity, policy: entity != source
    query(api, h, c)
    assert not out and errors[0][0] == "unauthorized"


@pytest.mark.parametrize("incomplete", [False, True])
def test_empty_or_incomplete_source_acl_conservatively_denies_nonadmin(api, incomplete):
    r, h, c, out, errors, _ = context(admin=False)
    r.panasonic.settings = r.sg_boost.settings = {}
    r.heatpump_history.access_sources_complete = not incomplete
    if incomplete:
        r.heatpump_history.access_sources.add("sensor.hp_total")
    query(api, h, c)
    assert not out and errors[0][0] == "unauthorized"


def test_permission_failure_denies_without_exposing_error_or_writing(api):
    _, h, c, out, errors, _ = context(admin=False)
    def failed(entity, policy):
        raise RuntimeError("private auth details")
    c.user.permissions.check_entity = failed
    query(api, h, c)
    assert not out and errors[0][0] == "unauthorized" and "private" not in errors[0][1]
    assert not h.services.calls


def test_anonymous_cannot_probe_entries(api):
    _, h, c, out, errors, _ = context()
    c.user = None
    query(api, h, c, config_entry_id="unknown")
    assert not out and errors[0][0] == "unauthorized"


@pytest.mark.parametrize("condition", ["unknown", "wrong_domain", "unloaded", "closed", "wrong_runtime_entry", "history_not_loaded"])
def test_entry_domain_loaded_state_and_runtime_identity_isolation(api, condition):
    r, h, c, out, errors, _ = context()
    if condition == "unknown":
        query(api, h, c, config_entry_id="other-entry")
    else:
        if condition == "wrong_domain": r.entry.domain = "other_integration"
        if condition == "unloaded": r.entry.state = "not_loaded"
        if condition == "closed": r._closed = True
        if condition == "wrong_runtime_entry": r.entry.runtime_data = SimpleNamespace(_closed=False, entry=SimpleNamespace(entry_id="other"))
        if condition == "history_not_loaded": r.heatpump_history.loaded = False
        query(api, h, c)
    assert not out and errors[0][0] == "not_loaded"


@pytest.mark.parametrize("day", ["invalid", "2026-2-1", "2026-02-30", "2026-10-12", "2026-09-11", "../secrets", 4, True])
def test_invalid_dates_do_not_access_other_data_or_actuators(api, day):
    _, h, c, out, errors, _ = context()
    query(api, h, c, date=day)
    assert not out and errors[0][0] == "invalid_date" and not h.services.calls


@pytest.mark.parametrize("extra", [{"apply": True}, {"device_id": "a"}, {"config_entry_id": ""}, {"config_entry_id": 3}, {"type": "solar_pilot/apply"}])
def test_no_mutation_operation_or_arbitrary_request_fields(api, extra):
    _, h, c, out, errors, _ = context()
    query(api, h, c, **extra)
    assert not out and errors[0][0] == "invalid_format" and not h.services.calls


def test_read_failure_has_generic_error_and_keeps_storage(api, monkeypatch):
    r, h, c, out, errors, _ = context()
    r.heatpump_history.store.data = {"retained": "private synthetic data"}
    def failed(*args):
        raise RuntimeError("private source identity")
    monkeypatch.setattr(r.heatpump_history, "detail", failed)
    query(api, h, c)
    assert not out and errors[0][0] == "history_failed" and "identity" not in errors[0][1]
    assert r.heatpump_history.store.data == {"retained": "private synthetic data"} and not h.services.calls


def test_reload_during_detail_never_returns_stale_entry_history(api, monkeypatch):
    r, h, c, out, errors, _ = context()
    actual = r.heatpump_history.detail
    def reload(day):
        result = actual(day)
        r.entry.runtime_data = None
        return result
    monkeypatch.setattr(r.heatpump_history, "detail", reload)
    query(api, h, c)
    assert not out and errors[0][0] == "not_loaded"


def test_registration_is_idempotent_across_entries(api):
    _, h, _, _, _, _ = context()
    api.async_register_heatpump_history_api(h)
    api.async_register_heatpump_history_api(h)
    assert h.registered == [api.websocket_heatpump_history]
