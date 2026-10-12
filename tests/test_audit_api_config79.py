"""Source-driven regressions for config edits; only fictitious HA sources."""
import ast
import asyncio
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from test_runtime import build
from test_analysis_api import api as analysis_api
from test_consumer_history_api import api as history_api, context as history_context
from custom_components.solar_pilot.const import DEFAULTS
from custom_components.solar_pilot.const import DOMAIN
from homeassistant.exceptions import HomeAssistantError
from custom_components.solar_pilot.ems import PHASE_DEFAULTS
from custom_components.solar_pilot.unified_planner import UNIFIED_PLANNER_DEFAULTS
from custom_components.solar_pilot.pv_forecast_source import PV_FORECAST_DEFAULTS, ENTITY_ROLES, finite
from custom_components.solar_pilot.wallbox import WALLBOX_DEFAULTS
from custom_components.solar_pilot.house_first import HOUSE_DEFAULTS
from custom_components.solar_pilot.consumer_wallbox import PRIORITY_DEFAULTS
from custom_components.solar_pilot.wallbox_profile import PROFILE_DEFAULTS
from custom_components.solar_pilot.wallbox_policy import SESSION_DEFAULTS
from custom_components.solar_pilot.diagnostics import async_get_config_entry_diagnostics
from custom_components.solar_pilot.feedback_store import FeedbackValidationError


COMP = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot"


def source_function(filename, name, namespace):
    tree = ast.parse((COMP / filename).read_text(encoding="utf-8"))
    node = next(node for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)
    node.decorator_list = []
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(COMP / filename), "exec"), namespace)
    return namespace[name]


def flow(group, values):
    runtime, hass = build()
    base = deepcopy(runtime.entry.options)
    base[group] = deepcopy(values)

    class Flow:
        config_entry = runtime.entry

        def __init__(self):
            self.hass = hass
            self.saved = None

        def _base_options(self):
            return base

        def _site(self):
            return {**DEFAULTS, **runtime.entry.data, **base.get("settings", {})}

        async def _save(self, options):
            self.saved = options
            return {"saved": True}

        def async_show_form(self, **kwargs):
            return kwargs

    selectors = NS(BooleanSelector=lambda: {}, SelectSelector=lambda value: value,
                   TextSelector=lambda: {}, EntitySelector=lambda value: value)
    vol = NS(Required=lambda key, **kwargs: key, Optional=lambda key, **kwargs: key,
             Schema=lambda value: value)
    namespace = dict(deepcopy=deepcopy, DEFAULTS=DEFAULTS, merged_site=lambda v: {**DEFAULTS, **v},
                     sources_schema=lambda values: values, UNIFIED_PLANNER_DEFAULTS=UNIFIED_PLANNER_DEFAULTS,
                     PHASE_DEFAULTS=PHASE_DEFAULTS, PV_FORECAST_DEFAULTS=PV_FORECAST_DEFAULTS,
                     ENTITY_ROLES=ENTITY_ROLES, finite=finite, vol=vol, selector=selectors,
                     optional=lambda key, values: key, num=lambda *args: {}, entity=lambda domains: {},
                     WALLBOX_DEFAULTS=WALLBOX_DEFAULTS, HOUSE_DEFAULTS=HOUSE_DEFAULTS,
                     PRIORITY_DEFAULTS=PRIORITY_DEFAULTS, PROFILE_DEFAULTS=PROFILE_DEFAULTS,
                     SESSION_DEFAULTS=SESSION_DEFAULTS, apply_first_install_suggestions=lambda h, c, g: c,
                     discover_session_candidate=lambda h, c: None,
                     wallbox_errors_for=lambda *args: {}, validate_profile=lambda c: {})
    namespace["site_errors"] = source_function("config_flow.py", "site_errors", namespace)
    return Flow(), hass, base, namespace


@pytest.mark.asyncio
async def test_cleared_separate_export_is_validated_before_save():
    f, h, _, ns = flow("settings", {"grid_sign": "separate", "grid_entity": "sensor.import",
                                   "export_entity": "sensor.export"})
    h.states.set("sensor.import", "100", {"unit_of_measurement": "W"})
    h.states.set("sensor.export", "0", {"unit_of_measurement": "W"})
    method = source_function("config_flow.py", "async_step_settings", ns)
    result = await method(f, {"grid_sign": "separate", "grid_entity": "sensor.import",
                              "battery_sign": "discharge_positive"})
    assert f.saved is None
    assert result["errors"] == {"export_entity": "required"}


@pytest.mark.asyncio
async def test_clearing_missing_battery_reference_does_not_validate_old_source():
    f, _, _, ns = flow("settings", {"grid_entity": "sensor.grid", "battery_power_entity": "sensor.missing",
                                   "battery_soc_entity": "sensor.missing_soc"})
    method = source_function("config_flow.py", "async_step_settings", ns)
    result = await method(f, {"grid_entity": "sensor.grid", "grid_sign": "import_positive",
                              "battery_sign": "discharge_positive"})
    assert result == {"saved": True}
    assert f.saved["settings"]["battery_power_entity"] == ""
    assert f.saved["settings"]["battery_soc_entity"] == ""


@pytest.mark.asyncio
async def test_visible_planner_edit_preserves_hidden_disabled_optimisation():
    stored = {**UNIFIED_PLANNER_DEFAULTS, "joint_optimisation": False, "max_timeline_slots": 16,
              "forecast_deferral_enabled": False, "deadline_guard_s": 240}
    f, h, base, ns = flow("planner", stored)
    method = source_function("config_flow.py", "async_step_planner", ns)
    await method(f, {"horizon_h": 48})
    for key in ("joint_optimisation", "max_timeline_slots", "forecast_deferral_enabled", "deadline_guard_s"):
        assert f.saved["planner"][key] == stored[key]
    assert f.saved["planner"]["horizon_h"] == 48
    for key in base.keys() - {"planner"}:
        assert f.saved[key] == base[key]
    assert not h.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("method_name,group,values,input_values,cleared", [
    ("async_step_pv_forecast", "pv_forecast", {"now_entity": "sensor.old_forecast", "forecast_entry_id": "old_entry"},
     {}, ("now_entity", "forecast_entry_id")),
    ("async_step_phase", "phase", {"enabled": False, "phase_1_entity": "sensor.old_phase", "learning_min_delta_w": 321},
     {"enabled": False}, ("phase_1_entity",)),
    ("async_step_phase_learning", "phase", {"monitor_power_entities": ["sensor.old_monitor"], "limit_w": 4500},
     {}, ("monitor_power_entities",)),
    ("async_step_wallbox", "wallbox", {"enabled": False, "power_entity": "sensor.old_charger",
                                         "status_entity": "sensor.old_state", "session_mode_entity": "sensor.old_session",
                                         "stale_s": 600},
     {"enabled": False}, ("power_entity", "status_entity", "session_mode_entity")),
])
async def test_omitted_optional_source_is_cleared(method_name, group, values, input_values, cleared):
    f, h, _, ns = flow(group, values)
    method = source_function("config_flow.py", method_name, ns)
    await method(f, input_values)
    assert f.saved is not None
    for key in cleared:
        assert not f.saved[group].get(key)
    for key in values.keys() - set(cleared):
        assert f.saved[group][key] == values[key]
    assert not h.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("filename,name,operation", [
    ("pv_forecast_api.py", "websocket_pv_diagnostics", {"reset_confirm": True}),
    ("learning_api.py", "websocket_learning", {"operation": "policy", "setting": "notifications", "value": False}),
    ("priority_api.py", "websocket_priority_board", {"save": {"revision": "current", "order": [], "wallbox_power": {}, "confirm": True}}),
])
@pytest.mark.parametrize("closed", [True, False])
async def test_queued_api_mutation_rechecks_runtime_after_lock(filename, name, operation, closed):
    runtime, hass = build()
    runtime.entry.domain = DOMAIN
    runtime.entry.runtime_data = runtime
    hass.config_entries = NS(async_get_entry=lambda entry_id: runtime.entry)
    calls, results, errors = [], [], []
    connection = NS(user=NS(is_admin=True), send_result=lambda *args: results.append(args),
                    send_error=lambda *args: errors.append(args))

    async def changed(*args):
        calls.append(args)
        return {}

    class Gate:
        async def __aenter__(self):
            await asyncio.sleep(0)
            if closed:
                runtime._closed = True
            else:
                runtime.entry.runtime_data = NS(_closed=False)

        async def __aexit__(self, *args):
            return False

    runtime._lock = Gate()
    runtime.pv_forecast.reset = lambda: calls.append("reset")
    runtime.learning_hub.set_policy = changed
    runtime.priority_board.save = changed
    namespace = dict(deepcopy=deepcopy, DOMAIN=DOMAIN, HomeAssistantError=HomeAssistantError)
    method = source_function(filename, name, namespace)
    await method(hass, connection, {"id": 1, "config_entry_id": "test", **operation})
    assert not calls and not results
    assert errors[0][1] == "not_loaded"
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("download", [True, False])
async def test_queued_export_never_prepares_from_closed_runtime(analysis_api, download):
    runtime, hass, connection, results, errors = history_context()
    connection.user.id = "fictional_admin"
    prepared = []
    original = runtime.analysis.prepare

    def prepare(*args):
        prepared.append(True)
        return original(*args)

    class Gate:
        async def __aenter__(self):
            await asyncio.sleep(0)
            runtime._closed = True

        async def __aexit__(self, *args):
            return False

    runtime._lock = Gate()
    runtime.analysis.prepare = prepare
    await analysis_api.websocket_analysis_export(hass, connection,
        {"id": 1, "config_entry_id": "test", "download": download})
    assert not prepared and not results and errors == ["not_loaded"]
    assert not runtime.analysis.exporting
    assert hass.data[analysis_api._DOWNLOADS]["preparing"] == 0
    assert not hass.data[analysis_api._DOWNLOADS]["files"] and not hass.services.calls


@pytest.mark.asyncio
async def test_inline_export_rechecks_runtime_after_provenance_await(analysis_api):
    runtime, hass, connection, results, errors = history_context()
    original = runtime.analysis_feedback.note_export

    async def note_export(*args, **kwargs):
        await original(*args, **kwargs)
        runtime._closed = True

    runtime.analysis_feedback.note_export = note_export
    await analysis_api.websocket_analysis_export(hass, connection,
        {"id": 1, "config_entry_id": "test"})
    assert not results and errors == ["not_loaded"]
    assert not runtime.analysis.exporting and not hass.services.calls


def test_consumer_history_rebind_requires_old_source_read_permission(history_api):
    runtime, hass, connection, results, errors = history_context(admin=False)
    old_source = runtime.configs["a"]["control_entity"]
    runtime.configs["a"]["control_entity"] = "switch.fictional_new_consumer"
    runtime.consumer_history.model.ensure("a", runtime.configs["a"], runtime.consumer_history.now())
    connection.user.permissions.check_entity = lambda entity, policy: entity != old_source
    before = deepcopy(runtime.consumer_history.model.snapshot())
    history_api.websocket_consumer_history(hass, connection,
        {"id": 1, "config_entry_id": "test", "device_id": "a"})
    assert not results and errors == ["unauthorized"]
    assert runtime.consumer_history.model.snapshot() == before
    assert not hass.services.calls


def test_consumer_history_complete_permissions_allow_preserved_rebound_data_without_acl_leak(history_api):
    runtime, hass, connection, results, errors = history_context(admin=False)
    old_source = runtime.configs["a"]["control_entity"]
    runtime.configs["a"]["control_entity"] = "switch.fictional_new_consumer"
    runtime.consumer_history.model.ensure("a", runtime.configs["a"], runtime.consumer_history.now())
    checked = []
    connection.user.permissions.check_entity = lambda entity, policy: checked.append(entity) or True
    history_api.websocket_consumer_history(hass, connection,
        {"id": 1, "config_entry_id": "test", "device_id": "a"})
    assert not errors and results and old_source in checked
    assert "switch.fictional_new_consumer" in checked
    assert "access_sources" not in results[0] and "access_sources_complete" not in results[0]
    assert "binding" not in results[0]
    assert not hass.services.calls


@pytest.mark.parametrize("admin", [False, True])
def test_legacy_consumer_history_unknown_provenance_is_retained_for_admin(history_api, admin):
    runtime, hass, connection, results, errors = history_context(admin=admin)
    saved = runtime.consumer_history.model.snapshot()
    row = saved["devices"]["a"]
    row.pop("access_sources", None)
    row.pop("access_sources_complete", None)
    runtime.consumer_history.model.restore(saved, runtime.consumer_history.configs, runtime.consumer_history.now())
    assert "a" in runtime.consumer_history.model.devices
    history_api.websocket_consumer_history(hass, connection,
        {"id": 1, "config_entry_id": "test", "device_id": "a"})
    assert bool(results) is admin
    assert errors == ([] if admin else ["unauthorized"])
    assert not hass.services.calls


def test_consumer_history_permission_provider_error_fails_closed(history_api):
    _, hass, connection, results, errors = history_context(admin=False)

    def denied(*args):
        raise RuntimeError("Permission provider unavailable")

    connection.user.permissions.check_entity = denied
    history_api.websocket_consumer_history(hass, connection,
        {"id": 1, "config_entry_id": "test", "device_id": "a"})
    assert not results and errors == ["unauthorized"]
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_public_diagnostics_never_include_nested_phase_names_or_source_ids():
    runtime, hass = build(power=True)
    runtime.entry.runtime_data = runtime
    runtime.configs["a"]["name"] = "Fictional confidential consumer label"
    runtime.phase_settings["monitor_power_entities"] = ["sensor.fictional_confidential_meter"]
    hass.states.set("sensor.fictional_confidential_meter", "50",
                    {"unit_of_measurement": "W", "friendly_name": "Fictional confidential source label"})
    before = deepcopy(runtime._snapshot())
    result = await async_get_config_entry_diagnostics(hass, runtime.entry)
    import json
    serialized = json.dumps(result)
    for marker in ("Fictional confidential consumer label", "Fictional confidential source label",
                   "sensor.fictional_confidential_meter", "sensor.load", "monitor::"):
        assert marker not in serialized
    assert runtime._snapshot() == before and not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("download", [False, True])
async def test_export_provenance_storage_failure_is_not_reported_as_size_limit(analysis_api, download):
    runtime, hass, connection, results, errors = history_context()
    connection.user.id = "fictional_admin"
    messages = []
    connection.send_error = lambda message_id, code, message: (errors.append(code), messages.append(message))

    async def blocked(*args, **kwargs):
        raise FeedbackValidationError("Bestaande adviesopslag niet geladen; deze wordt niet overschreven")

    runtime.analysis_feedback.note_export = blocked
    await analysis_api.websocket_analysis_export(hass, connection,
        {"id": 1, "config_entry_id": "test", "download": download})
    assert not results and errors == ["export_failed"]
    assert "adviesopslag" in messages[0]
    assert not runtime.analysis.exporting and not hass.services.calls
    assert hass.data[analysis_api._DOWNLOADS]["preparing"] == 0
    assert not hass.data[analysis_api._DOWNLOADS]["files"]
