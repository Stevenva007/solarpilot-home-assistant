"""Fictitious storage-boundary regressions, without household exports or controls."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import time

import pytest

from custom_components.solar_pilot.consumer_history import ConsumerHistory
from custom_components.solar_pilot.consumer_history_runtime import ConsumerHistoryRecorder
from custom_components.solar_pilot.analysis_review import build_review_bundle
from custom_components.solar_pilot.feedback_store import AnalysisFeedbackStore, FeedbackValidationError
from custom_components.solar_pilot.heatpump_learning import HeatPumpActivityModel
from test_runtime import build
from test_analysis_review67_audit import recorded, package

NOW = datetime(2026, 10, 12, 8, tzinfo=timezone.utc)


def known_history(runtime):
    model = ConsumerHistory("Europe/Brussels")
    model.observe("a", runtime.configs["a"], False, NOW)
    model.observe("a", runtime.configs["a"], True, NOW + timedelta(seconds=5))
    model.observe("a", runtime.configs["a"], True, NOW + timedelta(seconds=20))
    model.pause_recording()
    return model.snapshot()


@pytest.mark.asyncio
@pytest.mark.parametrize("raw", [False, [], "invalid", {"version": 999, "devices": {}},
    {"version": True, "devices": {}}, {"version": 1, "devices": []}])
async def test_unknown_consumer_history_store_is_preserved_during_observe_and_close(raw):
    runtime, hass = build()
    recorder = ConsumerHistoryRecorder(hass, runtime.entry, runtime.configs)
    recorder.now = lambda: NOW + timedelta(hours=1)
    recorder.store.data = deepcopy(raw)
    await recorder.start()
    recorder.observe("a", True, recorder.now())
    await recorder.close()
    assert recorder.store.data == raw
    assert recorder.store.saves == []
    assert recorder.error
    assert recorder.model.brief("a", recorder.now())["ongoing"] is False
    assert hass.services.calls == []


@pytest.mark.asyncio
async def test_unreadable_consumer_history_store_is_not_replaced(monkeypatch):
    runtime, hass = build()
    recorder = runtime.consumer_history
    recorder.store.data = {"private_existing_history": "retain"}
    async def cannot_load():
        raise OSError("Fictitious unavailable storage")
    monkeypatch.setattr(recorder.store, "async_load", cannot_load)
    await recorder.start()
    recorder.observe("a", True, NOW)
    await recorder.close()
    assert recorder.store.data == {"private_existing_history": "retain"}
    assert recorder.store.saves == []
    assert recorder.error and hass.services.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("empty", [None, {}])
async def test_empty_consumer_history_first_install_remains_writable(empty):
    runtime, hass = build()
    recorder = runtime.consumer_history
    recorder.now = lambda: NOW
    recorder.store.data = empty
    await recorder.start()
    recorder.observe("a", False, NOW)
    recorder.observe("a", True, NOW + timedelta(seconds=5))
    await recorder.close()
    assert recorder.store.saves[-1]["version"] == 1
    assert len(recorder.store.data["devices"]["a"]["sessions"]) == 1
    assert not recorder.error and hass.services.calls == []


@pytest.mark.asyncio
async def test_valid_consumer_history_preserves_known_intervals_without_downtime_bridge():
    runtime, hass = build()
    recorder = runtime.consumer_history
    raw = known_history(runtime)
    recorder.store.data = deepcopy(raw)
    recorder.now = lambda: NOW + timedelta(hours=1)
    await recorder.start()
    recorder.observe("a", True, recorder.now())
    await recorder.close()
    row = recorder.store.data["devices"]["a"]
    assert row["days"]["2026-10-12"]["on_s"] == 15
    assert row["sessions"][0]["stop_confirmed"] is False
    assert len(row["sessions"]) == 2
    assert not recorder.error and hass.services.calls == []


@pytest.mark.asyncio
async def test_consumer_history_close_cancels_delayed_writes_and_does_not_record_after_close():
    runtime, _hass = build()
    recorder = runtime.consumer_history
    recorder.now = lambda: NOW
    await recorder.start()
    callbacks, cancelled = [], []
    recorder.store.async_delay_save = lambda callback, delay: callbacks.append(callback)
    def cancel_delay():
        cancelled.append("delay")
        callbacks.clear()
    recorder.store._async_cleanup_delay_listener = cancel_delay
    recorder.store._async_cleanup_final_write_listener = lambda: cancelled.append("final")
    recorder.observe("a", False, NOW)
    assert callbacks
    await recorder.close(persist=False)
    revision = recorder.model.revision
    recorder.observe("a", True, NOW + timedelta(seconds=10))
    await recorder.close()
    assert not callbacks and cancelled == ["delay", "final"]
    assert recorder.model.revision == revision and not recorder.store.saves


@pytest.mark.asyncio
async def test_changed_calendar_timezone_does_not_reinterpret_existing_consumer_daily_totals():
    runtime, hass = build()
    recorder = runtime.consumer_history
    raw = known_history(runtime)
    raw["timezone"] = "America/New_York"
    recorder.store.data = deepcopy(raw)
    recorder.now = lambda: NOW + timedelta(hours=1)
    await recorder.start()
    recorder.observe("a", True, recorder.now())
    await recorder.close()
    assert recorder.store.data == raw and not recorder.store.saves
    assert recorder.error


def test_consumer_history_retains_private_acl_sources_across_binding_changes_and_reload():
    runtime, _hass = build()
    model = ConsumerHistory()
    cfg = deepcopy(runtime.configs["a"])
    cfg["control_entity"] = "switch.original_load"
    model.observe("a", cfg, True, NOW)
    cfg["control_entity"] = "switch.replacement_load"
    model.observe("a", cfg, True, NOW + timedelta(seconds=20))
    sources, complete = model.access_sources("a")
    assert complete and {"switch.original_load", "switch.replacement_load"} <= sources
    restored = ConsumerHistory()
    assert restored.restore(model.snapshot(), {"a": cfg}, NOW + timedelta(hours=1))
    assert restored.access_sources("a") == (sources, True)
    detail = restored.detail("a", None, NOW + timedelta(hours=1))
    assert "access_sources" not in detail and "access_sources_complete" not in detail
    assert "original_load" not in str(detail) and "replacement_load" not in str(detail)


def test_legacy_consumer_history_is_kept_without_borrowing_replacement_source_acl():
    runtime, _hass = build()
    raw = known_history(runtime)
    for row in raw["devices"].values():
        row.pop("access_sources")
        row.pop("access_sources_complete")
    restored = ConsumerHistory()
    cfg = {**runtime.configs["a"], "control_entity": "switch.replacement_load"}
    assert restored.restore(raw, {"a": cfg}, NOW + timedelta(hours=1))
    sources, complete = restored.access_sources("a")
    assert "switch.replacement_load" in sources and complete is False
    assert restored.detail("a", None, NOW + timedelta(hours=1))["on_s"] == 15


@pytest.mark.asyncio
async def test_future_analysis_store_is_preserved_on_close():
    runtime, hass = build()
    recorder = runtime.analysis
    raw = {"schema_version": 999, "future_records": [{"ts": 1000}]}
    recorder.store.data = deepcopy(raw)
    await recorder.start()
    await recorder.close()
    assert recorder.store.data == raw and not recorder.store.saves
    assert recorder.error and hass.services.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("malformed", [[], False, {"schema_version": True},
    {"schema_version": 2, "samples": [{"ts": float("nan")}]},
    {"schema_version": 2, "samples": [] , "started": float("inf")},
    {"schema_version": 2, "samples": "wrong"},
    {"schema_version": 2, "dropped": {"samples": "wrong"}}])
async def test_malformed_analysis_storage_is_not_replaced(malformed):
    runtime, _hass = build()
    recorder = runtime.analysis
    recorder.store.data = malformed
    await recorder.start()
    await recorder.close()
    assert not recorder.store.saves
    assert recorder.error
    assert recorder.store.data is malformed


@pytest.mark.asyncio
async def test_future_stored_analysis_sample_does_not_invent_future_measurement_coverage():
    runtime, _hass = build()
    recorder = runtime.analysis
    wall = time.time()
    recorder.store.data = {"schema_version": 2, "started": wall - 10,
        "samples": [{"ts": wall, "grid_w": 0, "pv_w": 0},
                    {"ts": wall + 300, "grid_w": 0, "pv_w": 0}], "changes": [], "events": []}
    await recorder.start()
    payload = recorder.prepare(hours=1)
    assert all(row["ts"] <= datetime.fromisoformat(payload["created_at"]).timestamp()
               for row in payload["telemetry"]["samples"])
    assert payload["coverage_summary"]["covered_hours"] == 0
    await recorder.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("started", [True, False])
async def test_boolean_analysis_collection_start_is_not_promoted_to_1970_timestamp(started):
    runtime, _hass = build()
    recorder = runtime.analysis
    raw = {"schema_version": 2, "started": started, "samples": [], "changes": [], "events": []}
    recorder.store.data = deepcopy(raw)
    await recorder.start()
    await recorder.close()
    assert recorder.error and not recorder.store.saves and recorder.store.data == raw


@pytest.mark.asyncio
@pytest.mark.parametrize("version", [1, 2])
async def test_known_analysis_storage_versions_remain_writable(version):
    runtime, _hass = build()
    recorder = runtime.analysis
    recorder.store.data = {"schema_version": version, "samples": [], "changes": [], "events": []}
    await recorder.start()
    await recorder.close()
    assert recorder.store.saves[-1]["schema_version"] == 2 and not recorder.error


@pytest.mark.asyncio
@pytest.mark.parametrize("persist", [False, True])
async def test_analysis_close_cancels_delayed_callbacks_before_final_authorized_save(persist):
    runtime, _hass = build()
    recorder = runtime.analysis
    await recorder.start()
    callbacks, cancelled = [], []
    recorder.store.async_delay_save = lambda callback, delay: callbacks.append(callback)
    def cancel_delay():
        cancelled.append("delay")
        callbacks.clear()
    recorder.store._async_cleanup_delay_listener = cancel_delay
    recorder.store._async_cleanup_final_write_listener = lambda: cancelled.append("final")
    runtime._observe(time.monotonic(), datetime.now(timezone.utc))
    recorder.capture(3)
    assert callbacks
    await recorder.close(persist=persist)
    recorder.capture(3)
    await recorder.close()
    assert not callbacks and cancelled == ["delay", "final"]
    assert len(recorder.store.saves) == (1 if persist else 0)
    if persist:
        assert recorder.store.saves[-1]["events"][-1]["kind"] == "shutdown"


@pytest.mark.asyncio
async def test_future_feedback_store_is_preserved_on_export():
    runtime, hass = build()
    recorder = AnalysisFeedbackStore(runtime)
    raw = {"schema_version": 999, "future_report": "retain"}
    recorder.store.data = deepcopy(raw)
    await recorder.start()
    source = {"export_id": "export_" + "a"*32, "export_sha256": "b"*64,
              "release": "1.0.0-beta.78", "created_at": "2026-10-12T08:00:00+00:00"}
    with pytest.raises(FeedbackValidationError):
        await recorder.note_export(source)
    await recorder.close()
    assert recorder.store.data == raw and not recorder.store.saves
    assert recorder.error and hass.services.calls == []


@pytest.mark.asyncio
async def test_unreadable_feedback_store_does_not_get_replaced_by_export(monkeypatch):
    runtime, _hass = build()
    recorder = AnalysisFeedbackStore(runtime)
    recorder.store.data = {"report": "Fictitious retained data"}
    async def cannot_load():
        raise OSError("Fictitious unavailable storage")
    monkeypatch.setattr(recorder.store, "async_load", cannot_load)
    await recorder.start()
    source = {"export_id": "export_" + "a"*32, "export_sha256": "b"*64,
              "release": "1.0.0-beta.78", "created_at": "2026-10-12T08:00:00+00:00"}
    with pytest.raises(FeedbackValidationError):
        await recorder.note_export(source)
    assert recorder.store.data == {"report": "Fictitious retained data"}
    assert not recorder.store.saves


def test_overflowing_optional_heatpump_model_value_does_not_reset_other_valid_evidence():
    model = HeatPumpActivityModel()
    data = {"schema": 1, "samples": {"space_heating": [10**400, 1500]},
            "days": {"space_heating": ["2026-10-11"]},
            "confirmed_samples": {"space_heating": [1500, 1600]},
            "confirmed_days": {"space_heating": ["2026-10-10", "2026-10-11"]}}
    assert model.restore(data) is True
    assert model.samples["space_heating"] == [1500]
    assert model.confirmed_samples["space_heating"] == [1500, 1600]
    assert model.days["space_heating"] == {"2026-10-11"}


def test_analysis_preserves_a_fresh_reported_sterilization_task_as_its_own_regime():
    row = recorded(1000)
    row["panasonic"]["native_task"]["function"] = "sterilization"
    bundle = build_review_bundle(package([row]))
    assert bundle["quality"]["regime_observation_counts"] == {"sterilization_reported": 1}


def test_analysis_global_off_veto_matches_the_live_heatpump_classifier():
    row = recorded(1000)
    row["panasonic"]["native_task"]["verified_global_off"] = True
    bundle = build_review_bundle(package([row]))
    assert "space_heating_reported" not in bundle["quality"]["regime_observation_counts"]


def test_analysis_scoped_off_cannot_become_inferred_tank_when_global_off_is_verified():
    row = recorded(1000, function=None)
    native = row["panasonic"]["native_task"]
    native.update(inactive=True, inactive_action="off", inactive_scope="global", verified_global_off=True)
    power = row["panasonic"]["power_activity"]
    power.update(function="tapwater_heating", function_kind="tank_route", function_source="aquarea_entity",
                 evidence="metered_power_and_context", context_observed_at=1000)
    row["panasonic"]["task_context"] = {"function": "tapwater_heating", "kind": "tank_route",
                                            "source": "aquarea_entity", "observed_at": 1000}
    assert "tapwater_heating_inferred" not in build_review_bundle(package([row]))["quality"]["regime_observation_counts"]


def test_analysis_sterilization_cannot_be_inferred_from_electrical_uptake_and_programme():
    row = recorded(1000, function=None)
    row["panasonic"]["power_activity"].update(function="sterilization", function_kind="selected_program",
                                               evidence="metered_power_and_context", context_observed_at=1000)
    assert "sterilization_inferred" not in build_review_bundle(package([row]))["quality"]["regime_observation_counts"]


def test_extreme_nested_analysis_meter_value_is_unknown_quality_without_export_failure():
    row = recorded(1000)
    row["panasonic"]["power_supply1_w"] = 10**400
    bundle = build_review_bundle(package([row]))
    assert bundle["quality"]["feed_quality"]["supply1"]["valid_fresh_sample_count"] == 0
    assert bundle["quality"]["feed_quality"]["supply2"]["valid_fresh_sample_count"] == 1


@pytest.mark.parametrize("field,value", [("policy", []), ("audit", 42), ("active_candidates", 42),
    ("days", {"2026-10-12": {"accepted": 10**400}}),
    ("days", {"2026-10-12": {"accepted": "1.5"}})])
def test_malformed_optional_learning_hub_fields_do_not_block_restore_or_discard_valid_policy(field, value):
    runtime, hass = build()
    raw = {"schema": 1, "policy": {"sampling": "quiet", "adaptation": "assisted"},
           "days": {"2026-10-11": {"accepted": 3}}, field: value}
    runtime.learning_hub.restore(raw)
    if field != "policy":
        assert runtime.learning_hub.policy["sampling"] == "quiet"
    if field != "days":
        assert runtime.learning_hub.days["2026-10-11"]["accepted"] == 3
    assert hass.services.calls == []


@pytest.mark.parametrize("schema", [999, True, "1"])
def test_unknown_learning_hub_schema_is_preserved_without_trusting_its_policy(schema):
    runtime, hass = build()
    raw = {"schema": schema, "policy": {"adaptation": "automatic"}, "future_evidence": ["preserve"]}
    before = deepcopy(raw)
    runtime.learning_hub.restore(raw)
    assert runtime.learning_hub.snapshot() == before
    assert runtime.learning_hub.policy["adaptation"] == "assisted"
    assert runtime.unified_planner.base_load.adaptive_enabled is False
    assert raw == before and hass.services.calls == []


@pytest.mark.parametrize("schema", [999, True, "1"])
def test_unknown_heatpump_learning_schema_is_preserved_without_gaining_planning_evidence(schema):
    model = HeatPumpActivityModel()
    raw = {"schema": schema, "confirmed_samples": {"space_heating": [1500]*8},
           "confirmed_days": {"space_heating": ["2026-10-10", "2026-10-11"]}, "future_evidence": ["preserve"]}
    before = deepcopy(raw)
    assert model.restore(raw) is False
    assert model.snapshot() == before
    assert model.estimate("space_heating").watts is None
    assert raw == before
