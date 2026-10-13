"""SG research uses witnessed source evidence and never controller authority."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot.const import VERSION
from custom_components.solar_pilot.sg_config import SG_DEFAULTS
from custom_components.solar_pilot.sg_investigation import MAX_SESSIONS, SGSessionResearch, assessment


BASE = 1_700_000_000.0


def policy(**changes):
    return {**SG_DEFAULTS, "entity_id": "switch.sg", "enabled": True,
            "profile": "general", "expected_power_w": 3000.0, **changes}


def point(offset, on, *, last=None, settings=None, watts=800.0, pv=4000.0):
    when = BASE + offset
    settings = settings or policy()
    sg = {"configured": True, "enabled": True, "observed_at": when,
          "owner": "solarpilot" if on else "none", "lease_confirmed": on,
          "desired_on": on, "relay_on": on, "relay_confirmed": True,
          "relay_observed_at": when, "relay_valid_until": when + 120,
          "relay_stale_s": 120, "lease_remaining_s": 300 if on else 0,
          "import_threshold_w": settings["import_threshold_w"],
          "stop_delay_s": settings["stop_delay_s"], "min_session_s": settings["min_session_s"],
          "effective_min_session_s": min(settings["min_session_s"], settings["max_session_s"]),
          "last_session": last, "fault": ""}
    native = {"native_task": {"function": "tapwater_heating", "observed_at": when,
                              "source": "aquarea_poll", "stale_s": 120}}
    context = {"release": VERSION, "binding": "a" * 64, "policy": settings,
               "fixed_import_limit_w": 3500,
               "pv": {"watts": pv, "stamp": when, "source": "sensor.pv"}}
    grid = {"watts": watts, "stamp": when, "source": ("import_positive", "sensor.grid", None)}
    return when, sg, native, grid, context


def observe(research, value):
    now, sg, native, grid, context = value
    research.observe(now, sg, native, grid=grid, context=context)


def finish(research=None, *, duration=1200, reason="Aanhoudende netafname; extra SG-aanvraag vrijgegeven", settings=None, alter=None):
    research = research or SGSessionResearch()
    settings = settings or policy()
    observe(research, point(0, False, settings=settings))
    observe(research, point(20, True, settings=settings))
    for offset in range(40, duration + 20, 20):
        value = point(offset, True, settings=settings)
        if alter is not None:
            alter(value, offset)
        observe(research, value)
    last = {"ended_at": BASE + duration + 20, "duration_s": float(duration), "reason": reason}
    final = point(duration + 20, False, last=last, settings=settings)
    observe(research, final)
    runtime = SimpleNamespace(sg_boost=SimpleNamespace(settings=settings, overview=lambda: final[1]),
                              settings={"max_import_w": 3500})
    return research, runtime, final


def test_real_legacy_last_session_does_not_validate_installed_timers():
    last = {"ended_at": BASE - 5000, "duration_s": 665.2,
            "reason": "Netgrens overschreden: 3726 W afname > 3500 W"}
    value = point(0, False, last=last)
    runtime = SimpleNamespace(sg_boost=SimpleNamespace(settings=policy()))
    result = assessment(runtime, BASE, sg=value[1])
    assert result["status"] == "collecting"
    assert result["metrics"]["last_session"]["release"] is None
    assert result["metrics"]["last_session"]["historical"] is None
    assert result["metrics"]["last_session"]["stop_category"] == "hard_net_limit"
    assert result["metrics"]["comparable_sessions"] == 0
    assert any("geen softwareversie" in text for text in result["evidence"])
    assert any("vóór twintig minuten" in text for text in result["hypotheses"])
    assert not any("verhoog" in proposal["text"] or "verlaag" in proposal["text"] for proposal in result["proposals"])


def test_explicit_old_release_is_historical_not_current_timer_validation():
    value = point(0, False, last={"release": "1.0.0-beta.70", "ended_at": BASE-100,
                                "duration_s": 385, "reason": "Aanhoudende netafname; extra SG-aanvraag vrijgegeven"})
    result = assessment(SimpleNamespace(sg_boost=SimpleNamespace(settings=policy())), BASE, sg=value[1])
    assert result["metrics"]["last_session"]["historical"] is True
    assert result["status"] == "collecting"
    assert any("historische" in text for text in result["evidence"])


def test_complete_witnessed_current_session_is_a_timing_observation_only():
    research, runtime, final = finish()
    record = research.sessions[0]
    assert record["known_start"] and record["source_complete"] and record["end_matched"]
    assert record["release"] == VERSION and record["policy"]["import_threshold_w"] == 600
    assert record["consistency"] == "consistent_observation"
    result = assessment(runtime, final[0], research=research)
    assert result["status"] == "observed_ok"
    assert result["metrics"]["comparable_sessions"] == 1
    assert result["metrics"]["last_session"]["release"] == VERSION
    assert not any(word in result["summary"].lower() for word in ("levensduur", "compressor", "besparing"))


def test_complete_early_soft_release_proposes_trace_not_setting_mutation():
    research, runtime, final = finish(duration=100)
    result = assessment(runtime, final[0], research=research)
    assert research.sessions[0]["consistency"] == "review_timing"
    assert result["status"] == "check_needed"
    assert result["metrics"]["timing_review_sessions"] == 1
    assert any(proposal["id"] == "sg_timing_trace" for proposal in result["proposals"])


@pytest.mark.parametrize("reason,category", [
    ("Netgrens overschreden: 3726 W afname > 3500 W", "hard_net_limit"),
    ("Kwartierbudget overschreden: 2000 W afname > 1500 W resterende kwartiergrens", "electrical_limit"),
    ("Netmeting niet actueel; extra SG-aanvraag vrijgegeven", "source_or_contact_fault"),
    ("Bevestigde boost voltooid of geen extra opname", "native_completion"),
    ("Eigen SG-aanvraag vrijgegeven voor afsluiten", "manual_or_configuration"),
    ("SG-voorwaarden gewijzigd; eigen aanvraag vrijgegeven", "manual_or_configuration"),
    ("Begrensde SG-sessieduur bereikt", "session_limit"),
    ("Een andere, niet herkende reden", "unknown"),
])
def test_short_other_stop_reasons_do_not_become_soft_timer_failures(reason, category):
    research, runtime, final = finish(duration=100, reason=reason)
    assert research.sessions[0]["stop_category"] == category
    assert research.sessions[0]["consistency"] == "separate_stop_reason"
    result = assessment(runtime, final[0], research=research)
    assert result["metrics"]["timing_review_sessions"] == 0
    assert result["status"] != "observed_ok"


@pytest.mark.parametrize("change", ["stale_grid", "stale_pv", "unknown_contact", "expired_lease", "restored_pv", "binding", "release", "policy", "backdated_grid"])
def test_source_or_policy_changes_invalidate_whole_session_comparison(change):
    def alter(value, offset):
        if offset != 200:
            return
        now, sg, native, grid, context = value
        if change == "stale_grid":
            grid["stamp"] = now - 120
        elif change == "stale_pv":
            context["pv"]["stamp"] = now - 120
        elif change == "unknown_contact":
            sg["relay_on"] = None
        elif change == "expired_lease":
            sg["relay_valid_until"] = now
        elif change == "restored_pv":
            context["pv"]["restored"] = True
        elif change == "binding":
            context["binding"] = "b" * 64
        elif change == "release":
            context["release"] = "1.0.0-beta.70"
        elif change == "policy":
            sg["import_threshold_w"] = 700
        elif change == "backdated_grid":
            grid["stamp"] = now - 25
    research, runtime, final = finish(alter=alter)
    assert research.sessions[0]["consistency"] == "unknown"
    assert assessment(runtime, final[0], research=research)["metrics"]["comparable_sessions"] == 0


def test_first_observed_on_is_not_a_witnessed_start():
    research = SGSessionResearch()
    observe(research, point(20, True))
    assert not research.active["known_start"]
    last = {"ended_at": BASE+40, "duration_s": 1200, "reason": "Aanhoudende netafname; extra SG-aanvraag vrijgegeven"}
    observe(research, point(40, False, last=last))
    assert research.sessions[0]["consistency"] == "unknown"


def test_restore_keeps_bounded_completed_records_but_discards_continuity():
    original, runtime, final = finish()
    data = original.snapshot()
    data["sessions"] *= MAX_SESSIONS + 5
    data["active"] = {"known_start": True}
    data["previous"] = {"state": False}
    restored = SGSessionResearch()
    restored.restore(data)
    assert len(restored.sessions) == MAX_SESSIONS
    assert restored.previous is None and restored.active is None
    observe(restored, point(5000, True))
    assert restored.active["known_start"] is False
    assert original.sessions[0] == data["sessions"][0]


@pytest.mark.parametrize("changes", [
    {"grid_reports": 0, "pv_reports": 0, "contact_reports": 0, "gaps": 33,
     "started_at": None, "start_lower_at": None},
    {"gaps": 1}, {"grid_reports": 1}, {"contact_reports": True},
    {"started_at": BASE-10}, {"start_lower_at": BASE+100},
    {"ended_at": BASE-20}, {"duration_s": 3000},
])
def test_contradictory_restored_flags_do_not_override_missing_real_proof(changes):
    original, runtime, final = finish()
    data = original.snapshot()
    data["sessions"][0].update(changes)
    restored = SGSessionResearch()
    restored.restore(data)
    assert restored.sessions[0]["consistency"] == "unknown"
    assert assessment(runtime, final[0], research=restored)["status"] != "observed_ok"


def test_expired_previous_source_and_long_sampling_gap_do_not_bridge_start():
    research = SGSessionResearch()
    observe(research, point(0, False))
    observe(research, point(31, True))
    assert research.active["known_start"] is False
    research = SGSessionResearch()
    first = point(0, False)
    first[1]["relay_observed_at"] = BASE - 110
    observe(research, first)
    observe(research, point(20, True))
    assert research.active["known_start"] is False


def test_clock_rollback_invalidates_active_coverage():
    research = SGSessionResearch()
    observe(research, point(0, False))
    observe(research, point(20, True))
    observe(research, point(40, True))
    observe(research, point(39, True))
    assert research.active is None
    assert research.sessions[-1]["source_complete"] is False
    assert research.sessions[-1]["interruption"] == "source_gap"


def test_repeated_polls_are_not_new_original_source_reports():
    research = SGSessionResearch()
    observe(research, point(0, False))
    observe(research, point(20, True))
    for offset in (40, 60, 80, 100):
        value = point(offset, True)
        value[3]["stamp"] = BASE + 20
        value[4]["pv"]["stamp"] = BASE + 20
        value[1]["relay_observed_at"] = BASE + 20
        observe(research, value)
    assert research.active["grid_reports"] == 1
    assert research.active["pv_reports"] == 1
    assert research.active["contact_reports"] == 1
    assert research.active["source_complete"] is True
    value = point(140, True)
    value[3]["stamp"] = BASE + 20
    observe(research, value)
    assert research.active is None
    assert research.sessions[-1]["source_complete"] is False
    assert research.sessions[-1]["interruption"] == "source_loss"


def test_different_ending_last_session_does_not_borrow_old_duration():
    research = SGSessionResearch()
    observe(research, point(0, False))
    observe(research, point(20, True))
    observe(research, point(40, False, last={"ended_at": BASE-200, "duration_s": 1200,
                                          "reason": "Aanhoudende netafname; extra SG-aanvraag vrijgegeven"}))
    assert research.sessions[0]["end_matched"] is False
    assert research.sessions[0]["consistency"] == "unknown"


@pytest.mark.parametrize("bad", [True, False, None, "1200", float("nan"), float("inf"), -1, 10**1000])
def test_invalid_minimum_cannot_become_comparable_or_throw(bad):
    research = SGSessionResearch()
    settings = policy(min_session_s=bad)
    value = point(0, False)
    observe(research, value)
    value = point(20, True)
    value[1]["effective_min_session_s"] = bad
    value[4]["policy"] = settings
    observe(research, value)
    value = point(40, True)
    value[1]["effective_min_session_s"] = bad
    value[4]["policy"] = settings
    observe(research, value)
    assert research.active["source_complete"] is False


def test_live_fixed_limit_deficit_is_quantified_without_reducing_estimate():
    research = SGSessionResearch()
    value = point(0, False, watts=655, pv=0)
    observe(research, value)
    runtime = SimpleNamespace(sg_boost=SimpleNamespace(settings=policy()), settings={"max_import_w": 3500})
    result = assessment(runtime, BASE, sg=value[1], research=research)
    assert result["metrics"]["fixed_import_room_w"] == 2845
    assert result["metrics"]["fixed_limit_extra_deficit_w"] == 155
    assert result["metrics"]["effective_policy"]["expected_power_w"] == 3000


def test_import_zero_does_not_pretend_to_reveal_signed_export_headroom():
    research = SGSessionResearch()
    value = point(0, False, watts=0)
    observe(research, value)
    runtime = SimpleNamespace(sg_boost=SimpleNamespace(settings=policy(expected_power_w=4000)), settings={"max_import_w": 3500})
    result = assessment(runtime, BASE, sg=value[1], research=research)
    assert "fixed_import_room_w" not in result["metrics"]
    assert not any("ontbreekt" in text for text in result["evidence"])


def test_readonly_assessment_and_observer_leave_all_source_inputs_unchanged():
    value = point(0, False)
    before = deepcopy(value)
    runtime = SimpleNamespace(sg_boost=SimpleNamespace(settings=policy()), settings={"max_import_w": 3500})
    options = deepcopy(runtime.sg_boost.settings)
    research = SGSessionResearch()
    observe(research, value)
    result = assessment(runtime, BASE, sg=value[1], research=research)
    result["metrics"]["effective_policy"]["import_threshold_w"] = 1000
    assert value == before and runtime.sg_boost.settings == options
    assert research.latest["policy"]["import_threshold_w"] == 600
    assert set(result) == {"id", "title", "status", "summary", "next_action", "evidence", "hypotheses", "proposals", "metrics"}


def test_legacy_stubs_and_explicit_not_configured_do_not_throw():
    assert assessment(SimpleNamespace(), BASE)["status"] == "collecting"
    assert assessment(SimpleNamespace(), BASE, sg={"configured": False})["status"] == "not_configured"


def test_current_fault_overrides_historical_success_status():
    research, runtime, final = finish()
    final[1]["fault"] = "Contactbevestiging ontbreekt"
    assert assessment(runtime, final[0], research=research)["status"] == "check_needed"


@pytest.mark.parametrize("history_failure", [False, True])
def test_runtime_hook_shares_exact_sample_and_has_no_physical_calls(history_failure):
    from test_runtime import build
    runtime, hass = build()
    value = point(0, False)
    calls, samples, history_samples = [], [], []
    runtime.panasonic.overview = lambda: calls.append("native") or value[2]
    runtime.sg_boost.overview = lambda: calls.append("sg") or value[1]
    runtime.sg_boost.settings = policy()
    runtime._sg_import_observation = lambda: value[3]
    def capture(native, sg, stamp, **kwargs):
        history_samples.append((native, sg, stamp))
        if history_failure:
            raise ValueError("incomplete history")
    stamp = datetime.fromtimestamp(BASE, timezone.utc)
    runtime.heatpump_history = SimpleNamespace(loaded=True, _closed=False, now=lambda: stamp,
        observe=capture, error="", model=SimpleNamespace(pause_recording=lambda: None))
    runtime.learning_hub.investigation = SimpleNamespace(sg_research=SimpleNamespace(
        observe=lambda *args, **kwargs: samples.append((args, kwargs))))
    before_calls = deepcopy(hass.services.calls)
    before_options = deepcopy(runtime.entry.options)
    runtime._capture_heatpump_history()
    assert calls == ["native", "sg"]
    assert len(samples) == 1 and len(history_samples) == 1
    args, kwargs = samples[0]
    assert args[0] == BASE and args[1] is value[1] and args[2] is value[2]
    assert history_samples[0][0] is args[2] and history_samples[0][1] is args[1]
    assert history_samples[0][2] is stamp
    assert kwargs["grid"] is value[3]
    assert kwargs["context"]["release"] == VERSION
    assert kwargs["context"]["policy"] is runtime.sg_boost.settings
    assert len(kwargs["context"]["binding"]) == 64
    assert hass.services.calls == before_calls and runtime.entry.options == before_options
