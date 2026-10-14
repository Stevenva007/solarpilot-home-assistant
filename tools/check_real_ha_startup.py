"""Exercise production entry setup against installed Home Assistant Core.

Run outside pytest: the normal unit suite intentionally provides HA doubles.
Only synthetic states and a disposable local configuration are used. HTTP
socket operations and source-IP discovery are replaced with offline no-ops;
no physical device is opened and all integration lifecycle code remains real.
"""
from __future__ import annotations

import argparse
import asyncio
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from importlib.metadata import version
import inspect
import json
import logging
from pathlib import Path
import shutil
import sys
import tempfile
import time
from types import MappingProxyType
from unittest.mock import patch


async def verify_analysis_feedback(hass, runtime, entry):
    """Exercise real Core storage and production admin handlers without control."""
    from custom_components.solar_pilot import analysis_api
    from custom_components.solar_pilot.analysis_review import export_digest
    from custom_components.solar_pilot.feedback_store import SOURCE_FIELDS

    class Connection:
        def __init__(self, admin):
            self.user = type("SyntheticUser", (), {"id": "synthetic_admin", "is_admin": admin})()
            self.results = []
            self.errors = []

        def send_result(self, message_id, result):
            self.results.append(result)

        def send_error(self, message_id, code, message):
            self.errors.append(code)

    # Unwrap only HA's scheduling decorator; the production coroutine still
    # performs its own admin/runtime checks against actual Core and Store.
    export_handler = inspect.unwrap(analysis_api.websocket_analysis_export)
    feedback_handler = inspect.unwrap(analysis_api.websocket_analysis_feedback)
    message = {"id": 1, "config_entry_id": entry.entry_id, "hours": 168}
    denied = Connection(False)
    await export_handler(hass, denied, message)
    assert denied.errors == ["unauthorized"] and not denied.results
    admin = Connection(True)
    await export_handler(hass, admin, message)
    assert not admin.errors and len(admin.results) == 1, admin.errors
    exported = json.loads(admin.results[0]["content"])
    heatpump = exported["components"]["heatpump_history"]
    assert heatpump["requested_hours"] == 168 and heatpump["retention_days"] == 30
    assert heatpump["window_end"] == exported["created_at"]
    wall = datetime.fromisoformat(exported["created_at"]).timestamp()
    cutoff = datetime.fromisoformat(heatpump["window_start"]).timestamp()
    assert wall-cutoff == 168*3600
    lanes = runtime.heatpump_history.model.lanes
    assert heatpump["timezone"] == lanes.timezone_name
    day = datetime.fromtimestamp(cutoff, lanes.zone).date()
    last_day = datetime.fromtimestamp(wall, lanes.zone).date()
    expected_dates, partial_dates = [], []
    while day <= last_day:
        key = day.isoformat()
        start, end = lanes._bounds(key)
        day += timedelta(days=1)
        if end > start and start < wall and end > cutoff:
            expected_dates.append(key)
            if cutoff > start or wall < end:
                partial_dates.append(key)
    assert [row["date"] for row in heatpump["days"]] == expected_dates
    assert heatpump["exported_days"] == len(expected_dates)
    assert heatpump["partial_boundary_dates"] == partial_dates
    assert abs(sum(row["window_overlap_s"] for row in heatpump["days"])-168*3600) < 1e-5
    assert heatpump["aggregate_scope"] == "full_local_calendar_day"
    assert "access_sources" not in heatpump and "binding" not in heatpump
    assert exported["analysis_request"]["schema"] == "solarpilot.analysis_request"
    assert exported["export_provenance"]["export_sha256"] == export_digest(exported)
    source = {key: exported["export_provenance"][key] for key in SOURCE_FIELDS}
    report = {"schema": "solarpilot.analysis_feedback", "schema_version": 1,
              "source_export": source, "analyzed_at": datetime.now(timezone.utc).isoformat(),
              "summary": "Synthetic analysis: continue collecting measured evidence.",
              "recommendations": [{"category": "observation", "text": "No setting change is justified by this short fixture.",
                                   "evidence": ["coverage_summary.covered_hours"], "confidence": "low",
                                   "limitations": ["Synthetic, brief observations."]}],
              "question_answers": [], "limitations": ["No physical heat-pump test."]}
    pending = exported["analysis_request"]["pending_questions"]
    assert pending, "The assisted-learning fixture must expose a finding to analyse"
    answered = pending[0]
    report["question_answers"] = [{"question_id": answered["id"], "revision": answered["revision"],
                                  "answer": "Synthetic review: keep the current learning policy.", "outcome": "reviewed"}]
    baseline = (deepcopy(dict(entry.options)), deepcopy(runtime.sg_boost.snapshot()),
                deepcopy(runtime.learning_hub.policy), deepcopy(runtime.learning_hub.answers))
    upload = {"id": 2, "config_entry_id": entry.entry_id, "action": "import", "content": json.dumps(report)}
    denied.errors.clear()
    await feedback_handler(hass, denied, upload)
    assert denied.errors == ["unauthorized"] and runtime.analysis_feedback.report is None
    admin.results.clear()
    await feedback_handler(hass, admin, upload)
    assert not admin.errors and len(admin.results) == 1, admin.errors
    status = admin.results[0]
    assert status["report"] == report and status["association"]["state"] == "matched"
    remaining = runtime.learning_hub.refresh(force=True)["questions"]
    assert not any(row["id"] == answered["id"] and row["revision"] == answered["revision"] for row in remaining)
    assert (dict(entry.options), runtime.sg_boost.snapshot(), runtime.learning_hub.policy,
            runtime.learning_hub.answers) == baseline
    saved = await runtime.analysis_feedback.store.async_load()
    assert saved["report"] == report and saved["known_exports"][-1]["source_export"] == source
    # Executable fields are rejected as a whole; the previously saved advice
    # remains intact and no native/options/control operation is attempted.
    invalid = {**report, "service": "switch.turn_on"}
    admin.errors.clear()
    await feedback_handler(hass, admin, {**upload, "id": 3, "content": json.dumps(invalid)})
    assert admin.errors and runtime.analysis_feedback.report == report
    assert (dict(entry.options), runtime.sg_boost.snapshot(), runtime.learning_hub.policy,
            runtime.learning_hub.answers) == baseline
    return report


def verify_heatpump_history(hass, runtime, entry, commands, *, metered):
    """Real monitor samples and registered read-only handler, without timers."""
    from custom_components.solar_pilot import heatpump_history_api

    recorder = runtime.heatpump_history
    assert recorder.loaded and recorder.error == "" and recorder._writable
    assert len(commands) == 1
    handler = inspect.unwrap(commands[0])
    assert handler is inspect.unwrap(heatpump_history_api.websocket_heatpump_history)
    baseline = (deepcopy(dict(entry.options)), deepcopy(runtime.sg_boost.snapshot()))
    # Both captures run sequentially without yielding: background polling cannot
    # produce the interval under test. Real elapsed wall time is used, rather
    # than assuming that a timer fired or fabricating five seconds of runtime.
    runtime._capture_heatpump_history()
    before = deepcopy(recorder.model.energy_days)
    runtime._capture_heatpump_history()
    after = deepcopy(recorder.model.energy_days)
    if metered:
        known = sum(row["energy_known_s"] for row in after.values())-sum(
            row["energy_known_s"] for row in before.values())
        energy = sum(row["energy_kwh"] for row in after.values())-sum(
            row["energy_kwh"] for row in before.values())
        assert known > 0
        assert abs(energy-known*1650/3600000) < 1e-9
        assert {"sensor.synthetic_supply1", "sensor.synthetic_supply2"} <= recorder.access_sources
    assert (dict(entry.options), runtime.sg_boost.snapshot()) == baseline
    assert "heatpump_history" not in runtime._snapshot()
    live = runtime.panasonic.overview()["history"]
    assert set(live) <= {"date", "recording", "ongoing", "revision", "recording_error", "storage_available"}

    class Connection:
        def __init__(self, allowed):
            self.user = type("SyntheticHistoryUser", (), {"is_admin": False,
                "permissions": type("ReadPolicy", (), {
                    "check_entity": staticmethod(lambda _entity, _policy: allowed)})()})()
            self.results, self.errors = [], []

        def send_result(self, message_id, result):
            self.results.append(result)

        def send_error(self, message_id, code, message):
            self.errors.append(code)

    message = {"id": 70, "type": heatpump_history_api.COMMAND, "config_entry_id": entry.entry_id}
    denied = Connection(False)
    handler(hass, denied, message)
    assert denied.errors == ["unauthorized"] and not denied.results
    reader = Connection(True)
    handler(hass, reader, message)
    assert not reader.errors and len(reader.results) == 1
    detail = reader.results[0]
    assert detail["device_id"] == "heatpump" and set(detail["sg"]) == {"request", "contact", "received"}
    assert "task_sessions" in detail and "task_totals" in detail
    if metered:
        assert detail["energy_kwh"] is not None
    assert "sensor.synthetic_supply1" not in json.dumps(detail)
    assert (dict(entry.options), runtime.sg_boost.snapshot()) == baseline
    return {"history": deepcopy(recorder.model.snapshot()), "access_sources": set(recorder.access_sources)}


def assert_heatpump_checkpoint(data, baseline, *, restored=None):
    """A reload/unload retains earlier evidence and closes its unknown boundary."""
    assert data["version"] == 1 and data["access_sources_complete"] is True
    assert baseline["access_sources"] <= set(data["access_sources"])
    expected, saved = baseline["history"], data["history"]
    assert saved["timezone"] == expected["timezone"]
    for day, row in expected["energy_days"].items():
        assert saved["energy_days"][day]["energy_known_s"] >= row["energy_known_s"]
        assert saved["energy_days"][day]["energy_kwh"] >= row["energy_kwh"]
    for lane, row in expected["lanes"]["devices"].items():
        retained = saved["lanes"]["devices"][lane]
        for old in row["sessions"]:
            session = next(s for s in retained["sessions"] if s["id"] == old["id"] and s["start"] == old["start"])
            assert session["observed_until"] >= old["observed_until"]
            if old["end"] is None:
                assert session["end"] is not None and session["stop_confirmed"] is False
    if restored is not None:
        assert restored.loaded and restored.error == "" and restored._writable
        assert baseline["access_sources"] <= restored.access_sources
        live = restored.model.snapshot()
        for day, row in saved["energy_days"].items():
            assert live["energy_days"][day]["energy_known_s"] >= row["energy_known_s"]
            assert live["energy_days"][day]["energy_kwh"] >= row["energy_kwh"]
        for lane, row in saved["lanes"]["devices"].items():
            assert {(s["id"], s["start"]) for s in row["sessions"]} <= {
                (s["id"], s["start"]) for s in live["lanes"]["devices"][lane]["sessions"]}


def fixture():
    """Generic protocol-shaped configuration, never household identifiers."""
    options = {
        "devices": [{"id": "synthetic_load", "name": "Synthetic load",
                     "kind": "switch", "control_entity": "switch.synthetic_load",
                     "nominal_w": 350, "priority": 61}],
        "settings": {"reserve_w": 275},
        "priority_board": {"schema": 2,
                           "order": ["wallbox", "dhw_extra", "device:synthetic_load"],
                           "wallbox_power": {"device:synthetic_load": False},
                           "source": "central_beta36"},
        "wallbox": {"enabled": False},
        "dhw": {"enabled": True, "target_entity": "water_heater.synthetic_tank",
                "temperature_entity": "sensor.synthetic_tank",
                "surplus_threshold_w": 3700},
        "smart_climate": {"enabled": True, "zone_entities": ["climate.synthetic_zone"]},
    }
    journal = {
        "mode": "observe", "auto_resume_after_restart": False,
        "device_modes": {"synthetic_load": "disabled"},
        "priorities": {"synthetic_load": 61}, "energy_kwh": 17.25,
        "dhw": {"owned_target": 60, "needs_review": True},
        "smart_climate": {"profiles": {"climate.synthetic_zone": {"samples": 633}}},
    }
    return options, journal


def current_sg_fixture():
    """Already migrated, disabled general SG with synthetic read-only roles."""
    options, journal = fixture()
    options.pop("dhw")
    options.pop("smart_climate")
    options["_panasonic_migration"] = 1
    options["retained_nested"] = {"source": {"values": [1, {"keep": True}]}}
    options["sg_boost"] = {
        "enabled": False, "entity_id": "switch.synthetic_sg",
        "commissioning_confirmed": False, "watchdog_confirmed": False,
        "profile": "general", "profile_confirmed": True,
        "cooling_protection_confirmed": False,
        "tank_temperature_entity": "sensor.synthetic_tank",
        "tank_target_entity": "water_heater.synthetic_tank",
        "activity_entity": "sensor.synthetic_activity",
        "zone_entities": ["climate.synthetic_zone"],
        "power_entity": "", "power_supply1_entity": "sensor.synthetic_supply1",
        "power_supply2_entity": "sensor.synthetic_supply2", "split_power_confirmed": True,
        "compressor_frequency_entity": "sensor.synthetic_frequency",
        "sg_status_entity": "binary_sensor.synthetic_sg_received",
        # Persisted beta.72 default pair: beta.73 upgrades only its effective
        # import policy without changing these immutable options or bindings.
        "hysteresis_w": 300, "stop_delay_s": 60,
    }
    journal.pop("dhw")
    journal.pop("smart_climate")
    journal["panasonic_archive"] = {
        "version": 1, "read_only": True,
        "backup_options": {"retired_options": {"values": [1, 2]}},
        "backup_store": {"retired_learning": {"samples": [3, 4]}},
        "assessment": {"changed": True, "retired_only_pause": False},
    }
    ended = time.time() - 3600
    journal["sg_boost"] = {
        "schema": 1, "relay_entity": "switch.synthetic_sg", "owned": False,
        "manual_hold": True, "completion_hold": True, "profile": "general",
        "hold_reason": "session_limit",
        "general_reference": {"schema": 1, "ended_at": ended,
            "signature": "synthetic_previous_context", "native_stamp": ended,
            "solar_stamp": ended, "solar_reset_stamp": None,
            "native_reset_stamp": None, "profile_transition": False,
            "native_rebase": False, "native_after": None},
    }
    return options, journal


def assert_current_sg(runtime, entry, expected_options, expected_journal):
    """Read-only assertions on real runtime data and immutable HA options."""
    assert dict(entry.options) == expected_options
    assert runtime.panasonic_archive == expected_journal["panasonic_archive"]
    assert runtime.sg_boost.manual_hold is True
    assert runtime.sg_boost.completion_hold is True
    assert runtime.sg_boost._general_reference == expected_journal["sg_boost"]["general_reference"]
    assert runtime.sg_boost.auto_enabled is False
    assert runtime.sg_boost.desired_on is False and runtime.sg_boost.owned is False
    # Upgrade defaults are runtime-only: immutable pre-upgrade options and
    # restored manual/completion holds grant no active minimum or new lease.
    assert "min_session_s" not in expected_options["sg_boost"]
    assert "min_session_s" not in entry.options["sg_boost"]
    assert runtime.sg_boost.settings["min_session_s"] == 1200
    assert runtime.sg_boost.settings["max_session_s"] == 3600
    assert "import_threshold_w" not in expected_options["sg_boost"]
    assert "import_threshold_w" not in entry.options["sg_boost"]
    assert entry.options["sg_boost"]["hysteresis_w"] == 300
    assert entry.options["sg_boost"]["stop_delay_s"] == 60
    assert runtime.sg_boost.settings["hysteresis_w"] == 300
    assert runtime.sg_boost.settings["import_threshold_w"] == 600
    assert runtime.sg_boost.settings["stop_delay_s"] == 300
    sg = runtime.sg_boost.overview()
    assert sg["effective_min_session_s"] == 1200
    assert sg["minimum_remaining_s"] is None
    assert sg["minimum_valid_until"] is None and sg["minimum_active"] is False
    assert sg["import_threshold_w"] == 600 and sg["stop_delay_s"] == 300
    assert sg["cloud_remaining_s"] is None and sg["cloud_active"] is False
    assert sg["cloud_valid_until"] is None and sg["cloud_import_hold"] is False
    overview = runtime.panasonic.overview()
    assert overview["context"] == "space_heating" and overview["context_reliable"] is True
    assert overview["power_scope"] == "split" and overview["power_complete"] is True
    assert overview["power_supply1_w"] == 1400 and overview["power_supply2_w"] == 250
    assert overview["power_w"] == 1650
    assert overview["compressor_running"] is True and overview["compressor_frequency_hz"] == 35
    assert overview["sg_status"] == "unknown" and overview["sg_status_confirmed"] is False
    assert overview["sg_effect_confirmed"] is False
    assert runtime.panasonic.settings["power_activity_threshold_w"] == 200
    assert runtime.panasonic.settings["power_supply1_role"] == "main"
    assert runtime.panasonic.settings["power_supply2_role"] == "heater"
    assert overview["power_activity"]["active"] is True
    assert overview["power_activity"]["threshold_w"] == 200


class FailureEvidence(logging.Handler):
    def __init__(self):
        super().__init__()
        self.failures = []

    def emit(self, record):
        if record.exc_info:
            error = record.exc_info[1]
            self.failures.append((type(error).__name__, str(error)))


async def verify_sg_manual_control(hass, runtime, entry):
    """Use real Core service/entity schemas and user contexts, with no actuator.

    Only the final controller policy dispatcher is replaced. Core registration,
    registry identity, entity service context propagation and both production
    authorization layers stay real. The synthetic reader has ordinary entity
    control permission, so its denial cannot be attributed to Core's entity ACL.
    """
    import voluptuous as vol

    from homeassistant.auth.const import GROUP_ID_ADMIN, GROUP_ID_USER
    from homeassistant.auth.permissions.const import POLICY_CONTROL
    from homeassistant.components.select.const import DATA_COMPONENT
    from homeassistant.core import Context
    from homeassistant.exceptions import HomeAssistantError, Unauthorized
    from homeassistant.helpers import entity_registry as er

    from custom_components.solar_pilot.const import DOMAIN
    from custom_components.solar_pilot.sg_control_api import (
        SERVICE_SG_MANUAL_CONTROL, SG_MANUAL_OPTIONS,
    )

    assert hass.services.has_service(DOMAIN, SERVICE_SG_MANUAL_CONTROL)
    registry = er.async_get(hass)
    entity_id = registry.async_get_entity_id(
        "select", DOMAIN, f"{entry.entry_id}_sg_manual_control")
    assert entity_id is not None
    row = registry.async_get(entity_id)
    assert row is not None and row.config_entry_id == entry.entry_id
    entity = hass.data[DATA_COMPONENT].get_entity(entity_id)
    assert entity is not None and entity.runtime is runtime
    assert entity.translation_key == "sg_manual_control"
    assert tuple(entity.options) == SG_MANUAL_OPTIONS
    assert entity.current_option == "auto"
    assert entity.available is runtime.sg_boost.configured

    admin = await hass.auth.async_create_user(
        "Synthetic SG administrator", group_ids=[GROUP_ID_ADMIN])
    reader = await hass.auth.async_create_user(
        "Synthetic SG regular user", group_ids=[GROUP_ID_USER])
    assert admin.is_admin and not reader.is_admin
    assert reader.permissions.check_entity(entity_id, POLICY_CONTROL)
    admin_context, reader_context = Context(user_id=admin.id), Context(user_id=reader.id)
    baseline = (deepcopy(dict(entry.options)), deepcopy(runtime.sg_boost.snapshot()))
    dispatched = []

    async def record_dispatch(mode, duration_s=None):
        dispatched.append((mode, duration_s))

    async def call_native(data, context=admin_context):
        await hass.services.async_call(
            DOMAIN, SERVICE_SG_MANUAL_CONTROL, data,
            blocking=True, context=context,
        )

    async def expect_rejected(call, errors):
        before = list(dispatched)
        try:
            await call
        except errors:
            pass
        else:
            raise AssertionError("Invalid or unauthorized SG command reached Core successfully")
        assert dispatched == before

    with patch.object(runtime.sg_boost, "set_manual_control", record_dispatch):
        for mode, duration in (("auto", None), ("on", 1800), ("on", 3600),
                               ("off", 1800), ("off", 3600)):
            data = {"config_entry_id": entry.entry_id, "mode": mode}
            if duration is not None:
                data["duration_s"] = duration
            await call_native(data)
            assert dispatched[-1] == (mode, duration)
        assert len(dispatched) == 5
        invalid = (
            {"mode": "auto", "duration_s": None},
            {"mode": "auto", "duration_s": 1800},
            {"mode": "on"}, {"mode": "on", "duration_s": True},
            {"mode": "on", "duration_s": "1800"},
            {"mode": "on", "duration_s": 1800.0},
            {"mode": "off", "duration_s": 1200},
            {"mode": "unknown"}, {"mode": "auto", "extra": "forbidden"},
            {"mode": "auto", "config_entry_id": 1},
        )
        for data in invalid:
            await expect_rejected(call_native(data), (vol.Invalid,))
        await expect_rejected(
            call_native({"mode": "auto", "config_entry_id": "unloaded_synthetic_entry"}),
            (HomeAssistantError,),
        )
        await expect_rejected(
            call_native({"mode": "on", "duration_s": 1800}, reader_context),
            (Unauthorized,),
        )
        await expect_rejected(
            call_native({"mode": "auto"}, Context(user_id="unknown_synthetic_user")),
            (HomeAssistantError,),
        )
        # User-less trusted HA automation context follows Core's admin-service
        # semantics. It still dispatches policy only, never a relay command.
        await call_native({"mode": "auto"}, Context())
        assert dispatched[-1] == ("auto", None)
        native_dispatches = len(dispatched)

        select_dispatches = 0
        if runtime.sg_boost.configured:
            async def call_select(service, data, context):
                await hass.services.async_call(
                    "select", service, {"entity_id": entity_id, **data},
                    blocking=True, context=context,
                )

            for option, expected in (("auto", ("auto", None)), ("on_30", ("on", 1800)),
                                     ("on_60", ("on", 3600)), ("off_30", ("off", 1800)),
                                     ("off_60", ("off", 3600))):
                await call_select("select_option", {"option": option}, admin_context)
                assert dispatched[-1] == expected
                assert entity._context.user_id == admin.id
                select_dispatches += 1
            # The alternate select services reach the same guarded entity path.
            # A preceding administrator call must not leave administrator
            # authority cached on the entity for the next ordinary user.
            for service, data in (("select_option", {"option": "on_30"}),
                                  ("select_first", {}), ("select_last", {})):
                await expect_rejected(call_select(service, data, reader_context),
                                      (HomeAssistantError,))
                assert entity._context.user_id == reader.id
            await expect_rejected(
                call_select("select_option", {"option": "on_20"}, admin_context),
                (HomeAssistantError,),
            )
            await call_select("select_option", {"option": "auto"}, admin_context)
            assert dispatched[-1] == ("auto", None)
            select_dispatches += 1

    assert (dict(entry.options), runtime.sg_boost.snapshot()) == baseline
    return {"entity": entity, "admin_context": admin_context,
            "proof": {"native_schema_and_admin_acl": True,
                      "native_policy_dispatches": native_dispatches,
                      "registered_select_options": list(SG_MANUAL_OPTIONS),
                      "select_context_admin_acl": bool(select_dispatches),
                      "select_policy_dispatches": select_dispatches,
                      "configuration_and_controller_unchanged": True}}


async def check(source: Path, expected_failure: bool, current_sg: bool = False):
    # Imports must be real Core modules; importing tests/conftest.py defeats this
    # check. In particular ConfigEntry itself provides immutable mappings.
    from homeassistant import auth, bootstrap, loader
    from homeassistant.components.http import server as http_server
    from homeassistant.components import websocket_api
    from homeassistant.config_entries import ConfigEntries, ConfigEntry, ConfigEntryState
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers.storage import Store

    core_version = version("homeassistant")
    if not core_version.startswith("2026.10."):
        raise AssertionError(f"Expected Home Assistant 2026.10.x, found {core_version}")
    options, journal = current_sg_fixture() if current_sg else fixture()
    expected_options, expected_journal = deepcopy(options), deepcopy(journal)
    with tempfile.TemporaryDirectory(prefix="solarpilot-real-core-") as directory:
        config_dir = Path(directory)
        target = config_dir / "custom_components" / "solar_pilot"
        shutil.copytree(source / "custom_components" / "solar_pilot", target,
                        ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "userfiles"))
        sys.path.insert(0, str(config_dir))
        hass = HomeAssistant(str(config_dir))
        loader.async_setup(hass)
        hass.config_entries = ConfigEntries(hass, {})
        assert await bootstrap.async_load_base_functionality(hass)
        hass.auth = await auth.auth_manager_from_config(hass, [], [])
        entry = ConfigEntry(
            version=1, minor_version=1, domain="solar_pilot", title="SolarPilot smoke",
            source="user", unique_id="solar_pilot", options=options,
            data={"grid_entity": "sensor.synthetic_grid", "pv_entity": "sensor.synthetic_pv"},
            discovery_keys=MappingProxyType({}), subentries_data=None,
        )
        assert isinstance(entry.options, MappingProxyType)
        assert isinstance(entry.data, MappingProxyType)
        hass.states.async_set("sensor.synthetic_grid", "0", {"unit_of_measurement": "W"})
        hass.states.async_set("sensor.synthetic_pv", "0", {"unit_of_measurement": "W"})
        hass.states.async_set("switch.synthetic_load", "off")
        if current_sg:
            # No Shelly integration/device is configured: the relay cannot open
            # a physical transport. Every state below is local synthetic data.
            hass.states.async_set("switch.synthetic_sg", "off")
            hass.states.async_set("sensor.synthetic_tank", "48", {"unit_of_measurement": "°C"})
            hass.states.async_set("water_heater.synthetic_tank", "eco", {
                "temperature": 51, "current_temperature": 48, "temperature_unit": "°C"})
            hass.states.async_set("sensor.synthetic_activity", "WATER")
            hass.states.async_set("climate.synthetic_zone", "heat", {
                "hvac_action": "idle", "temperature": 20, "current_temperature": 20,
                "temperature_unit": "°C"})
            hass.states.async_set("sensor.synthetic_supply1", "1.4", {"unit_of_measurement": "kW"})
            hass.states.async_set("sensor.synthetic_supply2", "0", {"unit_of_measurement": "W"})
            hass.states.async_set("sensor.synthetic_frequency", "0", {"unit_of_measurement": "Hz"})
            hass.states.async_set("binary_sensor.synthetic_sg_received", "on")
        store = Store(hass, 1, f"solar_pilot.{entry.entry_id}")
        await store.async_save(journal)
        physical_calls = []

        def watch(event):
            if event.data.get("domain") in {"climate", "water_heater", "switch", "number", "button", "script"} or (
                    current_sg and event.data.get("domain") in {"homeassistant", "shelly"}):
                physical_calls.append(dict(event.data))

        remove_watch = hass.bus.async_listen("call_service", watch)
        history_commands = []
        register_command = websocket_api.async_register_command

        def observe_registration(hass, handler, *args, **kwargs):
            result = register_command(hass, handler, *args, **kwargs)
            if getattr(handler, "__name__", "") == "websocket_heatpump_history":
                history_commands.append(handler)
            return result
        evidence = FailureEvidence()
        logging.getLogger().addHandler(evidence)
        # Core 2026.10 binds the HTTP socket during dependency setup. Keep its
        # actual server/router/auth/registration APIs, but exercise them offline.
        # No SolarPilot constructor, migration, Store, platform or entity code
        # is patched. Source-IP discovery is irrelevant to this local check.
        async def no_http_io(*_args, **_kwargs):
            return None

        async def loopback_source(*_args, **_kwargs):
            return "127.0.0.1"

        patches = [patch.object(websocket_api, "async_register_command", observe_registration),
                   patch.object(http_server.HomeAssistantHTTP, "async_bind", no_http_io),
                   patch.object(http_server.HomeAssistantHTTP, "start", no_http_io),
                   patch("homeassistant.components.http.async_get_source_ip", loopback_source)]
        for replacement in patches:
            replacement.start()
        try:
            await hass.config_entries.async_add(entry)
            await hass.async_block_till_done()
            if expected_failure:
                assert entry.state is ConfigEntryState.SETUP_ERROR, entry.state
                assert any(kind == "TypeError" and "mappingproxy" in message
                           for kind, message in evidence.failures), evidence.failures
                assert dict(entry.options) == expected_options
                assert await store.async_load() == expected_journal
                assert not physical_calls, physical_calls
                return {"core": core_version, "result": "expected beta.62 failure reproduced",
                        "error": "TypeError: cannot pickle 'mappingproxy' object",
                        "configuration_and_store_unchanged": True}
            assert entry.state is ConfigEntryState.LOADED, (entry.state, evidence.failures)
            assert not evidence.failures, evidence.failures
            runtime = entry.runtime_data
            assert runtime.data_loaded and not runtime._closed
            assert runtime.mode == "observe"
            assert runtime.configs["synthetic_load"]["control_entity"] == "switch.synthetic_load"
            assert runtime.device_modes["synthetic_load"] == "disabled"
            assert runtime.energy_kwh == 17.25
            assert entry.options["devices"] == expected_options["devices"]
            assert entry.options["priority_board"] == expected_options["priority_board"]
            assert entry.options["sg_boost"]["enabled"] is False
            assert entry.options["sg_boost"]["entity_id"] == ("switch.synthetic_sg" if current_sg else "")
            assert entry.options["sg_boost"]["tank_temperature_entity"] == "sensor.synthetic_tank"
            assert "dhw" not in entry.options and "smart_climate" not in entry.options
            archive = deepcopy(runtime.panasonic_archive)
            if current_sg:
                assert archive == expected_journal["panasonic_archive"]
                observed = runtime.panasonic.overview()
                assert observed["power_w"] == 1400 and observed["power_complete"] is True
                assert observed["power_supply1_w"] == 1400 and observed["power_supply2_w"] == 0
                assert observed["compressor_running"] is False and observed["compressor_frequency_hz"] == 0
                assert observed["sg_status"] == "active" and observed["sg_status_confirmed"] is True
                assert observed["sg_effect_confirmed"] is False
                hass.states.async_set("sensor.synthetic_frequency", "unknown", {"unit_of_measurement": "Hz"})
                observed = runtime.panasonic.overview()
                assert observed["compressor_running"] is None and observed["compressor_frequency_hz"] is None
                # WATER is only programme context, never compressor proof.
                assert observed["activity"] == "WATER" and observed["sg_effect_confirmed"] is False
                # Existing bindings automatically gain the default read-only
                # interpretation. No new role, threshold or helper entity is
                # entered into these immutable pre-upgrade options.
                assert not any(key in entry.options["sg_boost"] for key in (
                    "power_activity_threshold_w", "power_supply1_role", "power_supply2_role"))
                control_before = deepcopy(runtime.sg_boost.snapshot())
                display = observed["power_activity"]
                assert display["label"] == "Ruimte verwarmen" and display["active"] is True
                assert display["threshold_w"] == 200 and display["function"] == "space_heating"
                assert display["function_kind"] == "selected_program"
                assert display["function_source"] == "native_mode"
                # Reproduce the overview's 1.36 kW main / 0 W heater case.
                # The selected heat context changes display only, never SG or
                # the original native/compressor observations.
                hass.states.async_set("sensor.synthetic_supply1", "1360", {"unit_of_measurement": "W"})
                active = runtime.panasonic.overview()
                assert active["power_activity"]["total_w"] == 1360
                assert active["power_activity"]["function"] == "space_heating"
                assert active["native_task"] == observed["native_task"]
                assert active["operation"] == observed["operation"]
                for key in ("context", "context_reliable", "context_signature", "cooling_possible", "sg_status", "sg_effect_confirmed"):
                    assert active[key] == observed[key]
                hass.states.async_set("sensor.synthetic_supply1", "58", {"unit_of_measurement": "W"})
                low = runtime.panasonic.overview()["power_activity"]
                assert low["label"] == "Basisverbruik" and low["active"] is False
                assert [row["state"] for row in low["supplies"]] == ["basis", "off"]
                assert [row["watts"] for row in low["supplies"]] == [58, 0]
                hass.states.async_set("sensor.synthetic_supply1", "0", {"unit_of_measurement": "W"})
                off = runtime.panasonic.overview()["power_activity"]
                assert off["label"] == "Geen elektrisch verbruik" and off["active"] is False
                assert runtime.sg_boost.snapshot() == control_before
                assert dict(entry.options) == expected_options and not physical_calls
                # Main and auxiliary supplies are separate observations. High
                # auxiliary uptake does not become compressor operation.
                hass.states.async_set("sensor.synthetic_supply1", "58", {"unit_of_measurement": "W"})
                hass.states.async_set("sensor.synthetic_supply2", "250", {"unit_of_measurement": "W"})
                heater = runtime.panasonic.overview()
                assert heater["power_activity"]["label"] == "Elektrische bijverwarming actief"
                assert heater["power_activity"]["activity_kind"] == "heater"
                assert heater["power_activity"]["function"] is None and heater["compressor_running"] is None
                assert [row["role"] for row in heater["power_activity"]["supplies"]] == ["main", "heater"]
                assert all(row["role_assumed"] for row in heater["power_activity"]["supplies"])
                hass.states.async_set("sensor.synthetic_supply1", "unavailable", {"unit_of_measurement": "W"})
                partial_heater = runtime.panasonic.overview()
                assert partial_heater["power_w"] is None and partial_heater["power_complete"] is False
                auxiliary = partial_heater["power_activity"]["supplies"][1]
                assert auxiliary["valid"] is True and auxiliary["state"] == "active" and auxiliary["watts"] == 250
                assert partial_heater["power_activity"]["function"] is None
                hass.states.async_set("sensor.synthetic_supply2", "0", {"unit_of_measurement": "W"})
                assert runtime.panasonic.overview()["power_activity"]["supplies"][1]["state"] == "off"
                # Explicit native actions remain useful even when every power
                # meter reports zero. Their labels and metered activity are
                # independent read-only layers.
                hass.states.async_set("sensor.synthetic_supply1", "0", {"unit_of_measurement": "W"})
                hass.states.async_set("water_heater.synthetic_tank", "idle", {
                    "hvac_action": "idle", "operation_mode": "idle", "temperature": 51,
                    "current_temperature": 48, "temperature_unit": "°C"})
                for mode, action, function in (("heat", "heating", "space_heating"),
                                                ("cool", "cooling", "space_cooling")):
                    hass.states.async_set("climate.synthetic_zone", mode, {
                        "hvac_action": action, "temperature": 20, "current_temperature": 20,
                        "temperature_unit": "°C"})
                    native = runtime.panasonic.overview()
                    assert native["native_task"]["function"] == function
                    assert native["native_task"]["source"] == "native_hvac_action"
                    assert native["native_task"]["observed_at"] is not None
                    assert native["power_activity"]["active"] is False
                    hass.states.async_set("sensor.synthetic_supply1", "1.4", {"unit_of_measurement": "kW"})
                    metered = runtime.panasonic.overview()
                    assert metered["power_activity"]["function"] == function
                    assert metered["power_activity"]["function_kind"] == "native_action"
                    hass.states.async_set("sensor.synthetic_supply1", "0", {"unit_of_measurement": "W"})
                hass.states.async_set("climate.synthetic_zone", "off", {
                    "hvac_action": "off", "temperature": 20, "current_temperature": 20,
                    "temperature_unit": "°C"})
                hass.states.async_set("water_heater.synthetic_tank", "heating", {
                    "hvac_action": "heating", "operation_mode": "heating", "temperature": 51,
                    "current_temperature": 48, "temperature_unit": "°C"})
                dhw = runtime.panasonic.overview()
                assert dhw["native_task"]["function"] == "tapwater_heating"
                assert dhw["native_task"]["source"] == "native_hvac_action"
                assert dhw["power_activity"]["active"] is False
                hass.states.async_set("sensor.synthetic_supply1", "1.4", {"unit_of_measurement": "kW"})
                assert runtime.panasonic.overview()["power_activity"]["label"] == "Sanitair water opwarmen"
                assert runtime.sg_boost.snapshot() == control_before
                assert dict(entry.options) == expected_options and not physical_calls
                hass.states.async_set("water_heater.synthetic_tank", "eco", {
                    "temperature": 51, "current_temperature": 48, "temperature_unit": "°C"})
                hass.states.async_set("climate.synthetic_zone", "heat", {
                    "hvac_action": "idle", "temperature": 20, "current_temperature": 20,
                    "temperature_unit": "°C"})
                # Exercise automatic discovery against real Core registries.
                # Only the native identity is installed; no Aquarea component,
                # coordinator or cloud connection is loaded for this fixture.
                from homeassistant.helpers import device_registry as dr
                from custom_components.solar_pilot.panasonic_monitor import PanasonicMonitor
                native_entry = ConfigEntry(
                    version=1, minor_version=1, domain="aquarea", title="Synthetic native registry",
                    source="ignore", unique_id="synthetic-native-registry", data={}, options={},
                    discovery_keys=MappingProxyType({}), subentries_data=None,
                )
                hass.config_entries._entries[native_entry.entry_id] = native_entry
                native_device = dr.async_get(hass).async_get_or_create(
                    config_entry_id=native_entry.entry_id, identifiers={("aquarea", "synthetic_native")},
                    manufacturer="Synthetic", name="Synthetic native heat pump")
                native_registry = er.async_get(hass)
                native_entities = {}
                for domain, suffix, value, attrs in (
                    ("water_heater", "tank", "heating", {"operation_mode": "heating", "temperature": 50,
                        "current_temperature": 49, "temperature_unit": "°C"}),
                    ("climate", "climate_1", "auto", {"hvac_action": "off", "temperature": 21,
                        "current_temperature": 22, "temperature_unit": "°C"}),
                    ("sensor", "direction", "WATER", {}),
                    ("binary_sensor", "defrost", "off", {}),
                ):
                    native_row = native_registry.async_get_or_create(
                        domain, "aquarea", f"synthetic_native_{suffix}", config_entry=native_entry,
                        device_id=native_device.id, suggested_object_id=f"synthetic_native_{suffix}")
                    native_entities[suffix] = native_row.entity_id
                    hass.states.async_set(native_row.entity_id, value, attrs)
                automatic = PanasonicMonitor(runtime, {**runtime.panasonic.settings,
                    "tank_target_entity": "", "zone_entities": []})
                automatic_before = deepcopy(automatic.settings)
                inherited_control = deepcopy(runtime.panasonic.overview())
                discovered = automatic.overview()
                assert discovered["display_sources"]["tank_entity"] == native_entities["tank"]
                assert discovered["display_sources"]["zone_entities"] == [native_entities["climate_1"]]
                assert discovered["display_tank"]["temperature_c"] == 49
                assert discovered["display_tank"]["target_c"] == 50
                assert discovered["display_tank"]["automatic"] is True
                assert discovered["native_task"]["function"] is None
                assert discovered["task_context"]["kind"] == "tank_route"
                assert discovered["power_activity"]["function"] == "tapwater_heating"
                assert discovered["power_activity"]["function_kind"] == "tank_route"
                assert discovered["defrost"]["state"] == "inactive"
                hass.states.async_set(native_entities["defrost"], "on")
                thaw = automatic.overview()
                assert thaw["defrost"]["state"] == "active"
                assert thaw["native_task"]["label"] == "Panasonic meldt ontdooien"
                assert thaw["native_task"].get("conflict") is True
                assert thaw["power_activity"]["function"] is None
                hass.states.async_set(native_entities["defrost"], "off")
                assert automatic.settings == automatic_before
                for key in ("context", "context_reliable", "context_signature", "cooling_possible", "operation"):
                    assert runtime.panasonic.overview()[key] == inherited_control[key]
                assert runtime.sg_boost.snapshot() == control_before
                assert dict(entry.options) == expected_options and not physical_calls
                hass.states.async_set("sensor.synthetic_supply1", "1.4", {"unit_of_measurement": "kW"})
                hass.states.async_set("sensor.synthetic_supply2", "unavailable", {"unit_of_measurement": "W"})
                observed = runtime.panasonic.overview()
                assert observed["power_w"] is None and observed["power_complete"] is False
                assert observed["power_supply1_w"] == 1400 and observed["power_supply2_w"] is None
                hass.states.async_set("sensor.synthetic_supply2", "250", {"unit_of_measurement": "W"})
                hass.states.async_set("sensor.synthetic_frequency", "35", {"unit_of_measurement": "Hz"})
                hass.states.async_set("binary_sensor.synthetic_sg_received", "unknown")
                assert_current_sg(runtime, entry, expected_options, expected_journal)
            else:
                assert archive["backup_options"] == expected_options
                assert archive["backup_store"] == expected_journal
            persisted = await store.async_load()
            assert persisted["panasonic_archive"] == archive
            from check_source_contract81 import verify_source_contract
            source_contract81 = await verify_source_contract(hass)
            heatpump_baseline = verify_heatpump_history(hass, runtime, entry, history_commands, metered=current_sg)
            feedback_report = await verify_analysis_feedback(hass, runtime, entry)
            registry = er.async_get(hass)
            rows = er.async_entries_for_config_entry(registry, entry.entry_id)
            domains = {row.entity_id.split(".", 1)[0] for row in rows}
            assert domains == {"sensor", "binary_sensor", "select", "number", "button", "switch"}, domains
            assert all(hass.states.get(row.entity_id) is not None for row in rows)
            manual_control84 = await verify_sg_manual_control(hass, runtime, entry)
            assert not physical_calls, physical_calls
            assert await hass.config_entries.async_reload(entry.entry_id)
            await hass.async_block_till_done()
            assert entry.state is ConfigEntryState.LOADED
            assert entry.runtime_data is not runtime
            assert runtime._closed
            assert runtime.heatpump_history._closed
            # A retained native entity from the earlier entry epoch cannot
            # dispatch to its retired controller after a real Core reload.
            from homeassistant.exceptions import HomeAssistantError
            retired = manual_control84["entity"]
            retired.async_set_context(manual_control84["admin_context"])
            try:
                await retired.async_select_option("auto")
            except HomeAssistantError:
                pass
            else:
                raise AssertionError("Retired SG select accepted a command after reload")
            heatpump_store = Store(hass, 1, f"solar_pilot.{entry.entry_id}.heatpump_history")
            assert_heatpump_checkpoint(await heatpump_store.async_load(), heatpump_baseline,
                                      restored=entry.runtime_data.heatpump_history)
            assert entry.runtime_data.heatpump_history is not runtime.heatpump_history
            assert len(history_commands) == 1
            assert entry.runtime_data.panasonic_archive == archive
            assert entry.options["devices"] == expected_options["devices"]
            feedback_status = entry.runtime_data.analysis_feedback.status()
            assert feedback_status["report"] == feedback_report
            assert feedback_status["association"]["state"] == "matched"
            await entry.runtime_data.analysis_feedback.remove()
            assert entry.runtime_data.analysis_feedback.report is None
            restored_findings = entry.runtime_data.learning_hub.refresh(force=True)["questions"]
            assert any(row["id"] == feedback_report["question_answers"][0]["question_id"]
                       and row["revision"] == feedback_report["question_answers"][0]["revision"]
                       for row in restored_findings)
            feedback_saved = await entry.runtime_data.analysis_feedback.store.async_load()
            assert feedback_saved["report"] is None and feedback_saved["known_exports"]
            if current_sg:
                assert_current_sg(entry.runtime_data, entry, expected_options, expected_journal)
            assert not physical_calls, physical_calls
            before_unload = {"history": deepcopy(entry.runtime_data.heatpump_history.model.snapshot()),
                             "access_sources": set(entry.runtime_data.heatpump_history.access_sources)}
            assert await hass.config_entries.async_unload(entry.entry_id)
            await hass.async_block_till_done()
            assert_heatpump_checkpoint(await heatpump_store.async_load(), before_unload)
            assert not evidence.failures, evidence.failures
            assert not physical_calls, physical_calls
            if current_sg:
                persisted = await store.async_load()
                assert dict(entry.options) == expected_options
                assert persisted["panasonic_archive"] == expected_journal["panasonic_archive"]
                assert persisted["sg_boost"]["manual_hold"] is True
                assert persisted["sg_boost"]["completion_hold"] is True
                assert persisted["sg_boost"]["general_reference"] == expected_journal["sg_boost"]["general_reference"]
            # An unloaded entry grants no runtime authority, even if the
            # domain-level service remains registered for another installation.
            from custom_components.solar_pilot.const import DOMAIN
            from custom_components.solar_pilot.sg_control_api import SERVICE_SG_MANUAL_CONTROL
            try:
                await hass.services.async_call(DOMAIN, SERVICE_SG_MANUAL_CONTROL,
                    {"config_entry_id": entry.entry_id, "mode": "auto"}, blocking=True,
                    context=manual_control84["admin_context"])
            except HomeAssistantError:
                pass
            else:
                raise AssertionError("Unloaded SolarPilot entry accepted an SG command")
            await hass.config_entries.async_remove(entry.entry_id)
            await hass.async_block_till_done()
            assert hass.config_entries.async_get_entry(entry.entry_id) is None
            assert not hass.services.has_service(DOMAIN, SERVICE_SG_MANUAL_CONTROL)
            assert not evidence.failures, evidence.failures
            assert not physical_calls, physical_calls
            return {"core": core_version, "result": "production setup, reload and unload passed",
                    "actual_platforms": sorted(domains), "registered_entities": len(rows),
                    "immutable_entry_mappings": True, "private_archive_exact": True,
                    "configuration_preserved": True, "physical_service_calls": 0,
                    "analysis_export_feedback_admin_storage_reload_read_only": True,
                    "heatpump_history_registered_read_only_acl_store_reload_unload": True,
                    "template_source_contract81": source_contract81,
                    "sg_manual_control84": {**manual_control84["proof"],
                        "retired_entity_and_unloaded_runtime_rejected": True,
                        "last_entry_removal_unregisters_service": True},
                    **({"fixture": "current general SG with split read-only sources",
                        "immutable_nested_options_exact": True, "manual_and_completion_holds_preserved": True,
                        "split_units_zero_missing_and_sum": True, "compressor_and_sg_proof_separate": True,
                        "automatic_power_display_without_new_settings": True,
                        "independent_heater_supply_and_partial_measurement": True,
                        "native_task_independent_of_metered_power": True,
                        "automatic_registry_siblings_and_defrost_read_only": True}
                       if current_sg else {})}
        finally:
            logging.getLogger().removeHandler(evidence)
            remove_watch()
            await hass.async_stop(force=True)
            for replacement in reversed(patches):
                replacement.stop()
            sys.path.remove(str(config_dir))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--expect-mappingproxy-failure", action="store_true")
    parser.add_argument("--current-sg-fixture", action="store_true")
    args = parser.parse_args()
    if args.expect_mappingproxy_failure and args.current_sg_fixture:
        parser.error("The immutable beta.62 failure uses the unchanged legacy fixture")
    logging.basicConfig(level=logging.WARNING)
    result = asyncio.run(check(args.source_root.resolve(), args.expect_mappingproxy_failure,
                              args.current_sg_fixture))
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
