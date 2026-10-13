"""Real recorder time boundary, historical-only checkpoints and stop evidence."""
from copy import deepcopy
from datetime import datetime, timezone, tzinfo
import json
import importlib
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from custom_components.solar_pilot.const import VERSION
from custom_components.solar_pilot.sg_investigation import MAX_SESSIONS, SGSessionResearch, assessment
from test_runtime import build
from test_sg_investigation75 import BASE, finish, observe, point, policy


def hook_runtime(zone):
    runtime, hass = build(settings={"pv_entity": "sensor.fixture_pv"})
    recorder = runtime.heatpump_history
    # Keep the actual HeatpumpHistoryRecorder.now() method and exercise its
    # real return type; only its datetime clock is replaced below by the test.
    assert isinstance(recorder.now(), datetime) and recorder.now().utcoffset() is not None
    recorder.loaded = True
    runtime.sg_boost.settings = policy()
    research = runtime.learning_hub.investigation.sg_research
    captured = []
    recorder.observe = lambda native, sg, stamp, **kw: captured.append((native, sg, stamp))
    current = {"value": point(0, False)}
    runtime.panasonic.overview = lambda: current["value"][2]
    runtime.sg_boost.overview = lambda: current["value"][1]
    runtime._sg_import_observation = lambda: current["value"][3]
    runtime._power = lambda *a: (current["value"][4]["pv"]["watts"], current["value"][0])
    class ClockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromtimestamp(current["value"][0], zone)
    return runtime, hass, recorder, research, current, captured, ClockDatetime


@pytest.mark.parametrize("zone", [timezone.utc, ZoneInfo("Europe/Brussels")])
def test_real_recorder_now_runtime_hook_reaches_real_research_without_changing_history_time(monkeypatch, zone):
    runtime, hass, recorder, research, current, captured, clock = hook_runtime(zone)
    monkeypatch.setattr(importlib.import_module("custom_components.solar_pilot.heatpump_history_runtime"), "datetime", clock)
    before = deepcopy((runtime.entry.options, runtime.sg_boost.snapshot(), hass.services.calls))
    for offset in range(0, 1241, 20):
        last = {"ended_at": BASE+1240, "duration_s": 1220.0,
                "reason": "Aanhoudende netafname; extra SG-aanvraag vrijgegeven"} if offset == 1240 else None
        current["value"] = point(offset, offset not in (0, 1240), last=last)
        inputs = deepcopy(current["value"])
        runtime._capture_heatpump_history()
        assert current["value"] == inputs
        assert captured[-1][2].tzinfo is zone
        assert captured[-1][2].timestamp() == BASE+offset
    assert len(research.sessions) == 1
    record = research.sessions[0]
    assert record["release"] == VERSION and record["known_start"]
    assert record["consistency"] == "consistent_observation" and record["comparable"]
    assert record["controller_stop"]["category"] == "soft_cloud_import"
    assert record["contact_end"] == {"state": False, "reported_at": BASE+1240}
    assert (runtime.entry.options, runtime.sg_boost.snapshot(), hass.services.calls) == before


class InvalidZone(tzinfo):
    def utcoffset(self, dt):
        raise ValueError("invalid fixture zone")


@pytest.mark.parametrize("bad", [None, BASE, "2023-01-01", datetime(2023, 1, 1),
    datetime.fromtimestamp(0, timezone.utc), datetime(2023, 1, 1, tzinfo=InvalidZone())])
def test_invalid_recorder_times_break_only_research_continuity(bad):
    runtime, hass, recorder, research, current, captured, _ = hook_runtime(timezone.utc)
    observe(research, point(0, False))
    observe(research, point(20, True))
    recorder.now = lambda: bad
    current["value"] = point(40, True)
    before = deepcopy((runtime.entry.options, runtime.sg_boost.snapshot(), hass.services.calls))
    runtime._capture_heatpump_history()
    assert captured[-1][2] is bad
    assert research.active is research.previous is None
    assert research.sessions[-1]["interruption"] == "invalid_time"
    assert not research.sessions[-1]["comparable"]
    assert (runtime.entry.options, runtime.sg_boost.snapshot(), hass.services.calls) == before


@pytest.mark.parametrize("until", [100, 1240])
def test_checkpoint_before_and_after_minimum_restores_only_interrupted_history(until):
    research = SGSessionResearch()
    observe(research, point(0, False))
    for offset in range(20, until+1, 20):
        observe(research, point(offset, True))
    original = deepcopy((research.active, research.previous))
    saved = json.loads(json.dumps(research.snapshot()))
    saved["checkpoint"].update(owned=True, lease_confirmed=True, active={"state": True}, comparable=True,
                               source_complete=True, consistency="consistent_observation")
    restored = SGSessionResearch()
    restored.restore(saved)
    assert restored.active is restored.previous is None and restored.latest == {}
    record = restored.sessions[-1]
    assert record["interrupted"] and record["interruption"] == "restart"
    assert record["last_observed_at"] == BASE+until
    assert record["ended_at"] is None and record["consistency"] == "unknown" and not record["comparable"]
    assert not record["source_complete"] and not record["end_matched"]
    assert not any(key in record for key in ("owned", "lease_confirmed", "active", "previous", "desired_on"))
    assert (research.active, research.previous) == original
    observe(restored, point(until+100, True))
    assert restored.active["known_start"] is False
    assert restored.sessions[0]["interrupted"]


@pytest.mark.parametrize("change,kind", [("contact", "source_loss"), ("grid", "source_loss"),
    ("pv", "source_loss"), ("gap", "source_gap"), ("binding", "binding_changed")])
def test_live_loss_archives_evidence_without_inventing_a_physical_stop(change, kind):
    research = SGSessionResearch()
    observe(research, point(0, False))
    observe(research, point(20, True))
    value = point(80 if change == "gap" else 40, True)
    if change == "contact":
        value[1]["relay_on"] = None
    elif change == "grid":
        value[3]["stamp"] = value[0]-120
    elif change == "pv":
        value[4]["pv"]["stamp"] = value[0]-120
    elif change == "binding":
        value[4]["binding"] = "b"*64
    before = deepcopy(value)
    observe(research, value)
    assert value == before
    assert research.active is None
    record = research.sessions[-1]
    assert record["interruption"] == kind and record["ended_at"] is None
    assert record["duration_s"] == 0 and record["last_observed_at"] == BASE+20
    assert record["consistency"] == "unknown" and not record["comparable"]


def transport(offset, *, operation="off", phase="send_uncertain", category="write_uncertain"):
    return {"operation": operation, "phase": phase, "category": category, "observed_at": BASE+offset,
            "command_attempted": True, "command_applied": None}


def test_controller_stop_unknown_contact_and_later_off_remain_separate_and_not_comparable():
    research = SGSessionResearch()
    observe(research, point(0, False))
    observe(research, point(20, True))
    last = {"ended_at": BASE+40, "duration_s": 20,
            "reason": "SG-voorwaarden gewijzigd; eigen aanvraag vrijgegeven", "transport": transport(40)}
    failed = point(40, False, last=last)
    failed[1].update(relay_on=None, relay_confirmed=False, transport_evidence=transport(40))
    observe(research, failed)
    record = research.sessions[-1]
    assert record["ended_at"] is None and record["controller_stop"]["ended_at"] == BASE+40
    assert record["contact_end"]["state"] is None
    assert record["transport"]["phase"] == "send_uncertain"
    later = point(60, False, last=last)
    later[1]["transport_evidence"] = transport(60, operation="read", phase="confirmed", category="none")
    observe(research, later)
    assert record["contact_end"] == {"state": False, "reported_at": BASE+60}
    assert record["transport"]["observed_at"] == BASE+40  # Later read did not retry or accept the old write.
    assert record["ended_at"] is None and not record["comparable"]
    runtime = SimpleNamespace(sg_boost=SimpleNamespace(settings=policy()))
    assert assessment(runtime, later[0], sg=later[1], research=research)["metrics"]["comparable_sessions"] == 0


def test_old_session_transport_cannot_be_attributed_to_a_new_interruption():
    research, _, final = finish(duration=100)
    old = deepcopy(final[1]["last_session"])
    old["transport"] = transport(120)
    observe(research, point(140, True, last=old))
    loss = point(160, True, last=old)
    loss[3]["stamp"] = BASE
    loss[1]["transport_evidence"] = transport(120)
    observe(research, loss)
    record = research.sessions[-1]
    assert record["interrupted"] and record["controller_stop"] is None and record["transport"] is None


def test_bad_checkpoint_schema_and_nested_diagnostics_are_bounded_or_rejected():
    research, _, _ = finish()
    data = research.snapshot()
    data["sessions"] *= MAX_SESSIONS+3
    data["sessions"][-1].update(transport={"operation": [], "phase": [], "category": [], "observed_at": BASE})
    data["checkpoint"] = {"started_at": BASE, "last_observed_at": None, "duration_s": 0, "interruption": []}
    restored = SGSessionResearch()
    restored.restore(data)
    assert len(restored.sessions) == MAX_SESSIONS and restored.sessions[-1]["transport"] is None
    assert restored.active is restored.previous is None
    restored.restore({"schema": True, "sessions": data["sessions"], "checkpoint": data["checkpoint"]})
    assert restored.sessions == [] and restored.active is None


def test_restored_future_contact_or_transport_reports_are_unknown(monkeypatch):
    original, _, final = finish()
    data = original.snapshot()
    data["sessions"][0]["contact_end"] = {"state": False, "reported_at": BASE+99999}
    data["sessions"][0]["transport"] = transport(99999, phase="confirmed", category="none")
    monkeypatch.setattr(importlib.import_module("custom_components.solar_pilot.sg_investigation").time,
                        "time", lambda: final[0]+60)
    restored = SGSessionResearch()
    restored.restore(data)
    assert restored.sessions[0]["contact_end"] == {"state": None, "reported_at": None}
    assert restored.sessions[0]["transport"] is None


def test_runtime_checkpoints_are_persisted_without_actuator_or_configuration_writes(monkeypatch):
    runtime, hass, recorder, research, current, captured, clock = hook_runtime(timezone.utc)
    monkeypatch.setattr(importlib.import_module("custom_components.solar_pilot.heatpump_history_runtime"), "datetime", clock)
    runtime.data_loaded = True
    before = deepcopy((runtime.entry.options, runtime.sg_boost.snapshot(), hass.services.calls))
    current["value"] = point(0, False)
    runtime._capture_heatpump_history()
    current["value"] = point(20, True)
    runtime._capture_heatpump_history()
    checkpoint = runtime.store.data["learning_hub"]["investigation"]["sg_sessions"]["checkpoint"]
    assert checkpoint["interrupted"] and not checkpoint["comparable"] and checkpoint["ended_at"] is None
    assert (runtime.entry.options, runtime.sg_boost.snapshot(), hass.services.calls) == before


@pytest.mark.asyncio
async def test_real_runtime_close_persists_only_shutdown_history_without_new_commands():
    runtime, hass = build()
    research = runtime.learning_hub.investigation.sg_research
    observe(research, point(0, False))
    observe(research, point(20, True))
    observe(research, point(40, True))
    before_options, before_calls = deepcopy((runtime.entry.options, hass.services.calls))
    await runtime.close()
    saved = runtime.store.data["learning_hub"]["investigation"]["sg_sessions"]
    assert saved["checkpoint"] is None
    assert saved["sessions"][-1]["interruption"] == "shutdown"
    assert saved["sessions"][-1]["ended_at"] is None
    assert not saved["sessions"][-1]["comparable"]
    assert runtime.entry.options == before_options and hass.services.calls == before_calls


def test_failed_coherent_source_capture_interrupts_research_and_leaves_controllers_unchanged():
    runtime, hass, recorder, research, current, captured, _ = hook_runtime(timezone.utc)
    observe(research, point(0, False))
    observe(research, point(20, True))
    runtime.data_loaded = True
    def unavailable():
        raise ValueError("fixture source unavailable")
    runtime.panasonic.overview = unavailable
    before = deepcopy((runtime.entry.options, runtime.sg_boost.snapshot(), hass.services.calls))
    runtime._capture_heatpump_history()
    assert research.active is None and captured == []
    assert research.sessions[-1]["interruption"] == "source_loss"
    saved = runtime.store.data["learning_hub"]["investigation"]["sg_sessions"]
    assert saved["sessions"][-1]["ended_at"] is None
    assert (runtime.entry.options, runtime.sg_boost.snapshot(), hass.services.calls) == before
