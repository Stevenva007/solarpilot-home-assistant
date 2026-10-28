"""Command-time SG evidence remains immutable and cannot become authority."""
from copy import deepcopy
import importlib
import json

import pytest

from custom_components.solar_pilot.const import VERSION
from custom_components.solar_pilot.sg_boost import SGBoostManager
from custom_components.solar_pilot.sg_investigation import SGSessionResearch, clean_session_provenance, session_policy_hash
from custom_components.solar_pilot.sg_transport import ShellyLeaseError
from test_sg_controller62 import boosted, fixture, tick
from test_sg_investigation75 import finish


@pytest.mark.asyncio
async def test_confirmed_start_freezes_original_policy_sources_owner_and_command_across_renewal_and_end():
    manager, adapter, clock, runtime = fixture(profile="general", profile_confirmed=True,
        cooling_protection_confirmed=True)
    runtime.settings = {"max_import_w": 3500}
    await tick(manager, solar_stamp=clock(), grid_import_source=("sensor.grid", "import_positive"))
    clock.advance(manager.settings["start_delay_s"])
    started = clock()
    await tick(manager, solar_stamp=clock(), grid_import_source=("sensor.grid", "import_positive"))
    original = deepcopy(manager.overview()["active_session_provenance"])
    assert original["release"] == VERSION and original["owner"] == "solarpilot"
    assert len(original["command_identity"]) == 32
    assert original["policy_hash"] == session_policy_hash(original["policy"])
    assert original["source_reports"]["grid"]["stamp"] == started
    assert original["source_reports"]["solar"]["watts"] == 4000
    assert original["source_reports"]["contact"]["output"] is False
    original["source_reports"]["grid"]["watts"] = 99999
    frozen = deepcopy(manager._session_provenance)
    clock.advance(manager.settings["renew_s"])
    await tick(manager, solar_stamp=clock(), grid_import_source=("sensor.grid", "import_positive"))
    assert manager._session_provenance == frozen
    manager.update_config({**manager.settings, "import_threshold_w": 700})
    runtime.settings["max_import_w"] = 4000
    await manager._release("Aanhoudende netafname; extra SG-aanvraag vrijgegeven")
    last = manager._last_session
    assert last["session_provenance"] == frozen
    assert last["session_provenance"]["policy"]["import_threshold_w"] == 600
    assert last["session_provenance"]["policy"]["fixed_import_limit_w"] == 3500
    assert last["transport"]["operation"] == "off" and last["transport"]["phase"] == "confirmed"
    wait = manager.overview()["rearm_wait"]
    assert wait["original_stop_reason"] == last["reason"]
    assert wait["original_hold_reason"] == "response_unknown"
    assert "bruikbaar zonnevermogen" in wait["current_condition"]
    assert wait["command_identity"] == frozen["command_identity"]


@pytest.mark.asyncio
async def test_natural_local_deadline_records_its_own_end_without_borrowing_a_previous_transport():
    manager, adapter, clock, runtime = await boosted(max_session_s=300, min_session_s=0)
    identity = manager._session_provenance["command_identity"]
    manager._last_session = {"ended_at": clock()-999, "reason": "unrelated old failure"}
    clock.advance(300)
    await tick(manager)
    last = manager.overview()["last_session"]
    assert last["reason"] == "Begrensde SG-sessieduur bereikt"
    assert last["transport"] is None and last["command_identity"] == identity
    assert manager.overview()["rearm_wait"]["original_stop_reason"] == last["reason"]
    assert adapter.calls == [("on", 300-manager.settings["ack_timeout_s"])]


@pytest.mark.asyncio
async def test_external_timer_takeover_records_loss_of_ownership_and_never_writes_off():
    manager, adapter, clock, runtime = await boosted()
    identity = manager._session_provenance["command_identity"]
    adapter.expiry += 100
    clock.advance(5)
    await tick(manager)
    assert manager.external_control_overview()["active"] and not manager.owned
    assert manager._last_session["command_identity"] == identity
    assert "eigenaarschap vrijgegeven" in manager._last_session["reason"]
    assert manager._last_session["transport"] is None
    assert manager._session_started is None
    assert adapter.calls == [("on", 300)]


@pytest.mark.asyncio
async def test_policy_change_during_ack_preserves_the_actual_sent_policy_and_records_safe_closure():
    manager, adapter, clock, runtime = fixture()
    runtime.settings = {"max_import_w": 3500}
    original_on = adapter.set_on
    async def changed_after_write(lease_s):
        result = await original_on(lease_s)
        manager.update_config({**manager.settings, "import_threshold_w": 700})
        runtime.settings["max_import_w"] = 4000
        manager._import_observation = {"watts": 99999, "stamp": clock()+10, "source": "new"}
        return result
    adapter.set_on = changed_after_write
    await tick(manager)
    clock.advance(manager.settings["start_delay_s"])
    command_stamp = clock()
    await tick(manager, grid_import_source="original")
    assert not manager.owned and adapter.calls == [("on", 300), ("off", None)]
    provenance = manager._last_session["session_provenance"]
    assert provenance["policy"]["import_threshold_w"] == 600
    assert provenance["policy"]["fixed_import_limit_w"] == 3500
    assert provenance["source_reports"]["grid"] == {"watts": 0.0, "stamp": command_stamp, "source": "original"}
    assert "Verouderde" in manager._last_session["reason"]


@pytest.mark.asyncio
async def test_failed_off_keeps_controller_stop_transport_uncertainty_and_rearm_condition_separate():
    manager, adapter, clock, runtime = await boosted(profile="general", profile_confirmed=True,
        cooling_protection_confirmed=True)
    async def unavailable():
        raise ShellyLeaseError("unavailable", "fixture")
    adapter.set_off = unavailable
    reason = "Netgrens overschreden: 3697 W afname > 3500 W"
    await manager._release(reason)
    frozen = deepcopy(manager._last_session)
    assert frozen["reason"] == reason and frozen["transport"]["phase"] == "not_sent"
    assert frozen["transport"]["command_attempted"] is False
    adapter.on = False
    clock.advance(5)
    manager._observe_contact(await manager._read(force=True))
    assert manager._last_session == frozen
    assert manager.overview()["rearm_wait"]["original_stop_reason"] == reason
    assert "bruikbaar zonnevermogen" in manager.overview()["rearm_wait"]["current_condition"]


@pytest.mark.asyncio
async def test_restart_carries_original_provenance_without_replay_or_retrospective_release_fill():
    manager, adapter, clock, runtime = await boosted()
    original = deepcopy(manager._session_provenance)
    saved = json.loads(json.dumps(manager.snapshot()))
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = restored
    restored.restore(saved)
    assert not restored.owned
    await tick(restored)
    assert restored.owned and restored._session_provenance == original
    assert adapter.calls == [("on", 300)]
    legacy = deepcopy(saved)
    legacy.pop("session_provenance", None)
    legacy["session_checkpoint"].pop("session_provenance", None)
    restored_legacy = SGBoostManager(runtime, adapter=adapter, clock=clock)
    restored_legacy.restore(legacy)
    assert restored_legacy._session_provenance is None


def test_legacy_completion_hold_does_not_attach_an_unrelated_last_stop_or_current_release():
    manager, adapter, clock, runtime = fixture(profile="general", profile_confirmed=True,
        cooling_protection_confirmed=True)
    saved = manager.snapshot()
    saved.update(completion_hold=True, hold_reason="session_limit", last_session={
        "ended_at": clock()-1000, "duration_s": 665, "reason": "older unreachable output"})
    manager.restore(saved)
    wait = manager.overview()["rearm_wait"]
    assert wait["provenance_status"] == "unknown_legacy"
    assert wait["original_stop_reason"] is None and wait["command_identity"] is None
    assert "nieuwe zonneperiode" in wait["current_condition"]
    assert "release" not in manager._last_session


def test_research_snapshots_preserve_source_hash_and_leave_legacy_missing_evidence_unknown():
    research, runtime, final = finish()
    original = deepcopy(research.sessions[0])
    assert original["policy_hash"] == session_policy_hash(original["policy"])
    assert original["source_reports"]["grid"]["stamp"] == original["started_at"]
    saved = research.snapshot()
    restored = SGSessionResearch()
    restored.restore(saved)
    assert restored.sessions[0]["policy_hash"] == original["policy_hash"]
    saved["sessions"][0].pop("policy_hash")
    saved["sessions"][0].pop("source_reports")
    restored.restore(saved)
    assert restored.sessions[0]["policy_hash"] is None
    assert restored.sessions[0]["source_reports"] is None
    assert not restored.sessions[0]["comparable"]


@pytest.mark.asyncio
async def test_forged_or_mutated_provenance_cannot_be_repaired_from_current_policy_or_restore_authority():
    manager, adapter, clock, runtime = await boosted()
    forged = deepcopy(manager._session_provenance)
    forged["policy"]["import_threshold_w"] = 9999
    assert clean_session_provenance(forged) is None
    saved = manager.snapshot()
    saved["session_provenance"] = forged
    saved["session_checkpoint"]["session_provenance"] = forged
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    restored.restore(saved)
    assert not restored.owned and restored._session_provenance is None


@pytest.mark.asyncio
async def test_real_controller_research_end_matches_command_and_survives_restore_without_relabeling(monkeypatch):
    manager, adapter, clock, runtime = fixture(min_session_s=0, stop_delay_s=60)
    research = SGSessionResearch()
    def observe(recorder, sg=None, imported=0):
        recorder.observe(clock(), sg or manager.overview(), {},
            grid={"watts": imported, "stamp": clock(), "source": "sensor.grid"},
            context={"release": VERSION, "policy": manager.settings, "binding": "a"*64,
                "fixed_import_limit_w": 3500,
                "pv": {"watts": 4000, "stamp": clock(), "source": "sensor.pv"}})
    await tick(manager)
    observe(research)
    for _ in range(int(manager.settings["start_delay_s"]/20)):
        clock.advance(20)
        await tick(manager)
        observe(research)
    assert manager.owned and research.active["known_start"]
    for _ in range(3):
        clock.advance(20)
        await tick(manager, imported=800)
        observe(research, imported=800)
    mismatched = deepcopy(research)
    clock.advance(20)
    await tick(manager, imported=800)
    observe(research, imported=800)
    record = research.sessions[-1]
    assert record["controller_stop"]["command_identity"] == manager._last_session["command_identity"]
    assert record["consistency"] == "consistent_observation"
    restored = SGSessionResearch()
    monkeypatch.setattr(importlib.import_module("custom_components.solar_pilot.sg_investigation").time, "time", clock)
    restored.restore(json.loads(json.dumps(research.snapshot())))
    assert restored.sessions[-1]["controller_stop"] == record["controller_stop"]
    unrelated = manager.overview()
    unrelated["last_session"]["session_provenance"]["command_identity"] = "0"*32
    unrelated["last_session"]["command_identity"] = "0"*32
    observe(mismatched, sg=unrelated, imported=800)
    assert mismatched.sessions[-1]["controller_stop"] is None
    assert mismatched.sessions[-1]["reason"] == ""
    assert not mismatched.sessions[-1]["comparable"]


@pytest.mark.asyncio
async def test_manual_reissue_records_actual_session_origin_and_effective_minimum_separately_from_command():
    manager, adapter, clock, runtime = fixture(max_session_s=600, min_session_s=600)
    await manager.start()
    await manager.set_manual_control("on", 1800)
    await tick(manager)
    origin = manager._session_started
    clock.advance(100)
    await manager._release("Elektrische grens tijdelijk bereikt")
    clock.advance(50)
    issued = clock()
    await tick(manager)
    assert manager.owned
    provenance = manager._session_provenance
    assert provenance["started_at"] == origin
    assert provenance["command_issued_at"] == issued
    assert provenance["policy"]["effective_min_session_s"] == manager._effective_minimum_s() == 450


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["bad", [], {}, True, float("nan"), float("inf")])
async def test_malformed_persisted_policy_is_unknown_evidence_and_cannot_break_startup(bad):
    manager, adapter, clock, runtime = await boosted()
    forged = deepcopy(manager._session_provenance)
    forged["policy"]["import_threshold_w"] = bad
    assert clean_session_provenance(forged) is None
    saved = manager.snapshot()
    saved["session_provenance"] = forged
    saved["session_checkpoint"]["session_provenance"] = forged
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    restored.restore(saved)
    assert restored._session_provenance is None and not restored.owned
