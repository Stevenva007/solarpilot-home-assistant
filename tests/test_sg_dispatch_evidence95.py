"""Rejected SG boundaries explain decisions without changing their authority."""
from copy import deepcopy
import importlib
import json

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from custom_components.solar_pilot.sg_investigation import (
    SGSessionResearch, _category, clean_dispatch_rejection,
)
from test_sg_budget_priority62 import configured
from test_sg_controller62 import boosted
from test_sg_investigation75 import BASE, finish
from test_sg_minimum_adversarial72 import live_dispatch


def test_rejected_fixed_net_gate_records_actual_boundary_values_and_success_clears_the_previous_denial():
    runtime, hass = configured(export=0, reserve=0)
    runtime.settings["max_import_w"] = 3500
    hass.states.set("sensor.public_hp", 0, {"unit_of_measurement": "W"})
    hass.states.set("sensor.grid", 2000, {"unit_of_measurement": "W"})
    assert runtime.sg_dispatch_allowed(ignore_solar=True) is False
    evidence = deepcopy(runtime._sg_dispatch_rejection)
    assert evidence["code"] == "net_limit" and evidence["renewal"] is False
    assert evidence["readings"]["grid_w"] == 2000
    assert evidence["readings"]["extra_w"] == 3200
    assert evidence["readings"]["projected_grid_w"] == 5200
    assert evidence["readings"]["fixed_import_limit_w"] == 3500
    assert evidence["source_reports"]["site_grid"] == {"watts": 2000,
        "reported_at": hass.states.get("sensor.grid").last_reported.timestamp()}
    assert evidence["source_reports"]["site_pv"] == {"watts": 8000,
        "reported_at": hass.states.get("sensor.public_pv").last_reported.timestamp()}
    assert 0 < evidence["readings"]["budget_oldest_reported_at"] <= evidence["evaluated_at"]
    assert not hass.services.calls
    hass.states.set("sensor.grid", -5000, {"unit_of_measurement": "W"})
    assert runtime.sg_dispatch_allowed() is True
    assert runtime._sg_dispatch_rejection is None
    assert evidence["readings"]["grid_w"] == 2000


@pytest.mark.parametrize("guard,code", [
    ("pause", "runtime_mode"), ("pending", "pending_command"),
    ("fault", "runtime_fault"), ("stale_pv", "site_source"),
    ("missing_phases", "phase_source"), ("missing_quarter", "capacity_source"),
])
def test_existing_rejection_guards_still_reject_with_distinct_bounded_reasons(guard, code):
    runtime, hass = configured(export=5000)
    if guard == "pause":
        runtime.mode = "paused"
    elif guard == "pending":
        runtime.pending = {"fictional": True}
    elif guard == "fault":
        runtime.faults["a"] = "Fictional fault"
    elif guard == "stale_pv":
        obj = hass.states.get("sensor.public_pv")
        hass.states.set("sensor.public_pv", obj.state, obj.attributes, age=121)
    elif guard == "missing_phases":
        runtime.phase_settings.update(enabled=True, control_starts=True)
    else:
        runtime.capacity_settings.update(enabled=True)
    assert runtime.sg_dispatch_allowed() is False
    evidence = runtime._sg_dispatch_rejection
    assert evidence["code"] == code
    assert evidence == clean_dispatch_rejection(evidence)
    assert not hass.services.calls
    assert "entity_id" not in json.dumps(evidence)
    if guard == "missing_phases":
        phases = {key: report for key, report in evidence["source_reports"].items() if key.startswith("phase_")}
        assert len(phases) == 3
        assert all(report["reported_at"] is None for report in phases.values())


@pytest.mark.asyncio
@pytest.mark.parametrize("off_confirmed", [True, False])
async def test_owned_renewal_rejection_after_await_freezes_the_actual_gate_before_off_and_survives_restore(off_confirmed):
    manager, adapter, clock, runtime = await boosted()
    original_policy = deepcopy(manager._session_provenance)
    live, hass = live_dispatch(manager, imported=400)
    clock.advance(60)
    assert manager._on_authorized(manager._generation, True)
    saved_original = runtime.store.async_save
    changed = False
    async def reject_during_intent_save(snapshot):
        nonlocal changed
        await saved_original(snapshot)
        if not changed:
            changed = True
            hass.states.set("sensor.grid", 600, {"unit_of_measurement": "W"})
    runtime.store.async_save = reject_during_intent_save
    off_original = adapter.set_off
    adapter.off_bad = not off_confirmed
    async def off_with_later_recovery():
        # A new read during OFF cannot replace the actual earlier rejection.
        hass.states.set("sensor.grid", -5000, {"unit_of_measurement": "W"})
        live.sg_dispatch_allowed(ignore_solar=True)
        return await off_original()
    adapter.set_off = off_with_later_recovery
    before_calls = list(adapter.calls)
    await manager._issue_on(renewal=True)
    assert adapter.calls == before_calls + [("off", None)]
    assert manager._last_session["session_provenance"] == original_policy
    evidence = deepcopy(manager._last_session["stop_evidence"])
    assert evidence["code"] == "net_limit" and evidence["renewal"] is True
    assert evidence["readings"]["grid_w"] == 600
    assert evidence["readings"]["extra_w"] == 0
    assert evidence["readings"]["fixed_import_limit_w"] == 500
    assert "vaste netgrens" in manager._last_session["reason"]
    assert manager._last_session["transport"]["operation"] == "off"
    assert (manager._last_session["transport"]["phase"] == "confirmed") is off_confirmed
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    restored.restore(json.loads(json.dumps(manager.snapshot())))
    assert not restored.owned
    assert restored.overview()["last_session"]["stop_evidence"] == evidence
    assert restored.overview()["last_session"]["session_provenance"] == original_policy


@pytest.mark.asyncio
async def test_custom_false_gate_cannot_borrow_previous_runtime_rejection_evidence():
    manager, adapter, clock, runtime = await boosted()
    runtime._sg_dispatch_rejection = clean_dispatch_rejection({"schema": 1, "code": "net_limit",
        "evaluated_at": manager._wall_clock(), "renewal": True, "readings": {"grid_w": 99999}})
    runtime.sg_dispatch_allowed = lambda *, renewal=False: False
    clock.advance(60)
    await manager._issue_on(renewal=True)
    assert manager._last_session["stop_evidence"]["code"] == "dispatch_unexplained"
    assert manager._last_session["stop_evidence"]["readings"] == {}
    assert _category(manager._last_session["reason"], manager._last_session["stop_evidence"]) == "unknown"


@pytest.mark.parametrize("reason,category", [
    ("SG-voorwaarden gewijzigd; eigen aanvraag vrijgegeven", "unknown"),
    ("SG-voorwaarden gewijzigd; verse zonnebeoordeling volgt", "unknown"),
    ("SG-uitgang niet bereikbaar; status onbekend, de lokale toestemming wordt niet vernieuwd", "source_or_contact_fault"),
    ("SG-toepassingsbereik gewijzigd; vorige aanvraag veilig vrijgegeven", "manual_or_configuration"),
])
def test_legacy_generic_stops_stay_unknown_and_explicit_contact_loss_is_classified(reason, category):
    assert _category(reason) == category


def test_historical_research_uses_only_original_bounded_stop_evidence_not_present_policy(monkeypatch):
    research, runtime, final = finish(reason="SG-voorwaarden gewijzigd; eigen aanvraag vrijgegeven")
    original = research.snapshot()
    restored = SGSessionResearch()
    restored.restore(deepcopy(original))
    assert restored.sessions[-1]["stop_category"] == "unknown"
    assert restored.sessions[-1]["stop_evidence"] is None
    assert restored.sessions[-1]["controller_stop"]["category"] == "unknown"
    evidence = clean_dispatch_rejection({"schema": 1, "code": "phase_limit", "renewal": True,
        "evaluated_at": original["sessions"][-1]["ended_at"]-1,
        "readings": {"phase_headroom_w": 50},
        "source_reports": {"phase_1": {"watts": 5000, "reported_at": BASE+1200}}})
    original["sessions"][-1]["stop_evidence"] = evidence
    original["sessions"][-1]["controller_stop"]["stop_evidence"] = deepcopy(evidence)
    restored.restore(json.loads(json.dumps(original)))
    assert restored.sessions[-1]["stop_category"] == "electrical_limit"
    assert restored.sessions[-1]["controller_stop"]["category"] == "electrical_limit"
    assert restored.sessions[-1]["stop_evidence"] == evidence
    assert restored.sessions[-1]["policy"] == research.sessions[-1]["policy"]


@pytest.mark.parametrize("stamp", [None, 0, -1, True, "new", float("nan"), float("inf"), 1e308])
def test_invalid_original_timestamps_are_never_replaced_by_evaluation_or_restore_time(stamp):
    value = {"schema": 1, "code": "phase_source", "renewal": True, "evaluated_at": BASE,
        "readings": {"budget_oldest_reported_at": stamp},
        "source_reports": {"phase_1": {"watts": 0, "reported_at": stamp}}}
    cleaned = clean_dispatch_rejection(value)
    assert cleaned["source_reports"]["phase_1"] == {"watts": 0, "reported_at": None}
    assert cleaned["readings"]["budget_oldest_reported_at"] is None


def test_optional_diagnostic_failure_cannot_change_dispatch_boolean(monkeypatch):
    module = importlib.import_module("custom_components.solar_pilot.sg_investigation")
    monkeypatch.setattr(module, "clean_dispatch_rejection", lambda value: (_ for _ in ()).throw(ValueError("fixture")))
    runtime, hass = configured(export=5000)
    assert runtime.sg_dispatch_allowed() is True
    runtime.mode = "paused"
    assert runtime.sg_dispatch_allowed() is False
    assert runtime._sg_dispatch_rejection is None
    assert not hass.services.calls
