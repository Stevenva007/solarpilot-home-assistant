"""Real pure HP history invariants using synthetic measurements only."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from custom_components.solar_pilot.heatpump_history import HeatpumpHistory, MAX_GAP_S

UTC = timezone.utc
BASE = datetime(2026, 10, 11, 9, tzinfo=UTC)


def source(at, *, watts=1800, task="space_heating", tier="confirmed", main=None, heater=0):
    stamp = at.timestamp()
    main = watts-heater if main is None else main
    active = watts >= 200
    kind = "tank_route" if task == "tapwater_heating" else "selected_program"
    context_source = "aquarea_entity" if kind == "tank_route" else "native_program"
    native = {"function": task, "source": "native_hvac_action", "observed_at": stamp, "stale_s": 120}
    if tier != "confirmed" or not task:
        native = {"function": None, "source": "aquarea_poll", "observed_at": stamp,
                  "inactive": True, "inactive_action": "idle", "stale_s": 120}
    return {"configured": True, "program": "heating", "source_stale_s": 120,
        "context": "space_heating", "context_reliable": True, "context_stamp": stamp,
        "native_task": native,
        "task_context": {"function": task, "kind": kind, "source": context_source, "observed_at": stamp, "stale_s": 120},
        "power_w": watts, "power_kind": "measured", "power_scope": "split", "power_complete": True,
        "power_observed_at": stamp, "power_supply1_entity": "sensor.synthetic_feed_one",
        "power_supply2_entity": "sensor.synthetic_feed_two", "power_supply1_w": main, "power_supply2_w": heater,
        "power_supply1_valid": True, "power_supply2_valid": True,
        "power_supply1_observed_at": stamp, "power_supply2_observed_at": stamp,
        "power_activity": {"complete": True, "active": active, "state": "active" if active else "basis" if watts else "off",
            "function": task if active else None, "function_kind": "native_action" if tier == "confirmed" else kind,
            "function_source": "native_hvac_action" if tier == "confirmed" else context_source,
            "observed_at": stamp, "context_observed_at": stamp, "stale_s": 120, "threshold_w": 200, "total_w": watts,
            "activity_kind": "heater" if heater >= 200 and main < 200 else "mixed" if heater >= 200 else "main",
            "supplies": [{"number": 1, "role": "main", "valid": True, "watts": main, "observed_at": stamp,
                          "state": "active" if main >= 200 else "basis" if main else "off"},
                         {"number": 2, "role": "heater", "valid": True, "watts": heater, "observed_at": stamp,
                          "state": "active" if heater >= 200 else "basis" if heater else "off"}]}}


def sg(at, request=False, contact=False):
    return {"configured": True, "observed_at": at.timestamp(), "desired_on": request,
            "relay_confirmed": True, "relay_on": contact, "relay_observed_at": at.timestamp(), "relay_stale_s": 120}


def observe(model, at, *, p=None, s=None, binding="same", **kwargs):
    p = source(at, **kwargs) if p is None else p
    s = {} if s is None else s
    before = deepcopy((p, s))
    model.observe(p, s, at, binding=binding)
    assert (p, s) == before


def test_native_activity_and_complete_electrical_energy_are_independent_of_sg():
    model = HeatpumpHistory()
    observe(model, BASE)
    observe(model, BASE+timedelta(seconds=20))
    data = model.detail(None, BASE+timedelta(seconds=20))
    assert data["device_id"] == "heatpump" and data["on_s"] == 20
    assert data["energy_kwh"] == 0.01 and data["energy_known_s"] == 20
    assert data["task_totals"] == [{"task": "space_heating", "label": "Ruimte verwarmen", "tier": "confirmed", "on_s": 20}]
    assert data["starts"] == 0  # Already active at first observation.
    assert not data["sessions"][0]["start_confirmed"]
    assert all(lane["on_s"] is None and not lane["has_data"] for lane in data["sg"].values())


def test_derived_tank_route_does_not_become_selected_heating_or_native_proof():
    model = HeatpumpHistory()
    observe(model, BASE, task="tapwater_heating", tier="derived")
    observe(model, BASE+timedelta(seconds=10), task="tapwater_heating", tier="derived")
    data = model.detail(None, BASE+timedelta(seconds=10))
    assert data["task_totals"][0]["task"] == "tapwater_heating"
    assert data["task_totals"][0]["tier"] == "derived"


def test_selected_programme_and_conflicting_actual_tasks_do_not_invent_confirmed_function():
    model = HeatpumpHistory()
    for n in (0, 10):
        at = BASE+timedelta(seconds=n)
        p = source(at, tier="derived")
        p["native_task"]["conflict"] = True
        observe(model, at, p=p)
    data = model.detail(None, BASE+timedelta(seconds=10))
    assert data["on_s"] == 10 and data["energy_known_s"] == 10
    assert data["task_totals"][0]["task"] == "heatpump_unknown"
    assert data["task_totals"][0]["tier"] == "unknown"


@pytest.mark.parametrize("condition", ["partial", "old_feed", "old_total", "estimated", "negative", "missing", "bool"])
def test_unusable_total_power_has_no_whole_hp_energy_even_with_native_task(condition):
    model = HeatpumpHistory()
    for n in (0, 10):
        at = BASE+timedelta(seconds=n)
        p = source(at)
        if condition == "partial":
            p["power_complete"] = False
        elif condition == "old_feed":
            p["power_supply2_observed_at"] = at.timestamp()-121
        elif condition == "old_total":
            p["power_observed_at"] = at.timestamp()-121
        elif condition == "estimated":
            p["power_kind"] = "estimated"
        elif condition == "negative":
            p["power_w"] = -1
        elif condition == "missing":
            p["power_w"] = None
        else:
            p["power_w"] = True
        observe(model, at, p=p)
    data = model.detail(None, BASE+timedelta(seconds=10))
    assert data["energy_kwh"] is None and data["energy_known_s"] == 0
    assert data["on_s"] == 10 and data["task_totals"][0]["tier"] == "confirmed"


def test_fresh_partial_positive_feed_proves_activity_but_not_total_energy_or_task():
    model = HeatpumpHistory()
    for n in (0, 10):
        at = BASE+timedelta(seconds=n)
        p = source(at, task=None, tier="derived")
        p["power_complete"] = False
        p["power_activity"].update(complete=False, state="partial")
        observe(model, at, p=p)
    data = model.detail(None, BASE+timedelta(seconds=10))
    assert data["on_s"] == 10 and data["energy_kwh"] is None
    assert data["task_totals"][0]["task"] == "heatpump_unknown"


def test_partial_zero_and_no_native_source_never_prove_whole_hp_off():
    model = HeatpumpHistory()
    p = source(BASE, watts=0, task=None, tier="derived")
    p.update(power_complete=False, context_reliable=False)
    p["power_activity"].update(complete=False, state="partial")
    observe(model, BASE, p=p)
    assert model.brief(BASE)["on_s"] is None
    assert model.detail(None, BASE)["on_s"] is None


def test_legacy_valid_partial_meter_without_assigned_supplies_keeps_observed_activity_only():
    model = HeatpumpHistory()
    for n in (0, 10):
        at = BASE+timedelta(seconds=n)
        p = source(at, task=None)
        p.update(power_scope="unconfirmed", power_complete=False)
        p["power_activity"].update(complete=False, state="partial", supplies=[])
        observe(model, at, p=p)
    data = model.detail(None, BASE+timedelta(seconds=10))
    assert data["on_s"] == 10 and data["energy_kwh"] is None
    assert data["task_totals"][0]["task"] == "heatpump_unknown"


def test_unknown_and_measured_zero_energy_remain_distinct():
    model = HeatpumpHistory()
    observe(model, BASE, p={})
    assert model.detail(None, BASE)["energy_kwh"] is None
    observe(model, BASE+timedelta(seconds=5), watts=0, task=None)
    assert model.detail(None, BASE+timedelta(seconds=5))["energy_kwh"] is None
    observe(model, BASE+timedelta(seconds=10), watts=0, task=None)
    data = model.detail(None, BASE+timedelta(seconds=10))
    assert data["energy_kwh"] == 0 and data["energy_known_s"] == 5
    assert data["on_s"] == 0 and data["has_data"]


@pytest.mark.parametrize("native_task,expected,tier", [(None, "electrical_support", "derived"),
                                                       ("tapwater_heating", "tapwater_heating", "confirmed")])
def test_heater_only_watts_do_not_invent_boiler_work_or_hide_confirmed_native_action(native_task, expected, tier):
    model = HeatpumpHistory()
    for n in (0, 10):
        observe(model, BASE+timedelta(seconds=n), watts=2800, main=40, heater=2760, task=native_task)
    total = model.detail(None, BASE+timedelta(seconds=10))["task_totals"][0]
    assert total["task"] == expected and total["tier"] == tier


def test_fresh_defrost_is_native_condition_even_below_electrical_threshold():
    model = HeatpumpHistory()
    for n in (0, 10):
        at = BASE+timedelta(seconds=n)
        p = source(at, watts=0, task=None)
        p["defrost"] = {"state": "active", "source": "aquarea_entity", "observed_at": at.timestamp(), "stale_s": 120}
        observe(model, at, p=p)
    data = model.detail(None, BASE+timedelta(seconds=10))
    assert data["on_s"] == 10 and data["energy_kwh"] == 0
    assert data["task_totals"][0]["task"] == "defrost"


def test_sg_request_contact_received_have_separate_actual_history():
    model = HeatpumpHistory()
    for n in (0, 10):
        at = BASE+timedelta(seconds=n)
        p = source(at, watts=0, task=None)
        p.update(sg_status_entity="sensor.synthetic_received_sg", sg_status_confirmed=True,
                 sg_status="inactive", sg_status_observed_at=at.timestamp())
        observe(model, at, p=p, s=sg(at, request=True, contact=False))
    data = model.detail(None, BASE+timedelta(seconds=10))
    assert data["on_s"] == 0 and not data["task_sessions"]
    assert data["sg"]["request"]["on_s"] == 10
    assert data["sg"]["contact"]["on_s"] == data["sg"]["received"]["on_s"] == 0
    assert "extra warmte" in data["note"]


@pytest.mark.parametrize("fault", ["no_config", "old_contact", "unconfirmed_contact", "old_received", "missing_received_source"])
def test_unknown_sg_layers_do_not_publish_false_zeroes(fault):
    model = HeatpumpHistory()
    p = source(BASE, watts=0, task=None)
    p.update(sg_status_entity="sensor.synthetic_received_sg", sg_status_confirmed=True,
             sg_status="inactive", sg_status_observed_at=BASE.timestamp())
    s = sg(BASE)
    if fault == "no_config":
        s["configured"] = False
        affected = ("request", "contact")
    elif fault == "old_contact":
        s["relay_observed_at"] -= 121
        affected = ("contact",)
    elif fault == "unconfirmed_contact":
        s["relay_confirmed"] = False
        affected = ("contact",)
    elif fault == "old_received":
        p["sg_status_observed_at"] -= 121
        affected = ("received",)
    else:
        p["sg_status_entity"] = ""
        affected = ("received",)
    observe(model, BASE, p=p, s=s)
    data = model.detail(None, BASE)
    assert all(data["sg"][key]["on_s"] is None for key in affected)


@pytest.mark.parametrize("interruption", ["gap", "unknown", "binding", "reload"])
def test_interruption_never_bridges_activity_or_energy_or_confirms_false_stop(interruption):
    model = HeatpumpHistory()
    observe(model, BASE)
    observe(model, BASE+timedelta(seconds=10))
    resume = BASE+timedelta(seconds=20)
    binding = "same"
    if interruption == "gap":
        resume = BASE+timedelta(seconds=10+MAX_GAP_S+1)
    elif interruption == "unknown":
        observe(model, BASE+timedelta(seconds=15), p={})
    elif interruption == "binding":
        binding = "different"
    else:
        snapshot = model.snapshot()
        model = HeatpumpHistory()
        assert model.restore(snapshot, resume)
    observe(model, resume, binding=binding)
    observe(model, resume+timedelta(seconds=10), binding=binding)
    data = model.detail(None, resume+timedelta(seconds=10))
    assert data["on_s"] == data["energy_known_s"] == 20
    assert len(data["sessions"]) == 2 and data["starts"] == data["stops"] == 0
    assert not data["sessions"][0]["stop_confirmed"]
    assert not data["sessions"][1]["start_confirmed"]


def test_duplicate_or_backwards_time_cannot_count_again_and_pause_is_not_off():
    model = HeatpumpHistory()
    observe(model, BASE)
    observe(model, BASE+timedelta(seconds=10))
    old = model.snapshot()
    observe(model, BASE+timedelta(seconds=10), watts=5000)
    observe(model, BASE+timedelta(seconds=5), watts=5000)
    assert model.snapshot() == old
    model.pause_recording()
    observe(model, BASE+timedelta(seconds=20))
    observe(model, BASE+timedelta(seconds=30))
    assert model.detail(None, BASE+timedelta(seconds=30))["energy_known_s"] == 20


def test_read_after_stalled_controller_cannot_claim_open_hp_task_or_sg_still_active():
    model = HeatpumpHistory()
    for n in (0, 5):
        at = BASE+timedelta(seconds=n)
        p = source(at)
        p.update(sg_status_entity="sensor.synthetic_received_sg", sg_status_confirmed=True,
                 sg_status="active", sg_status_observed_at=at.timestamp())
        observe(model, at, p=p, s=sg(at, request=True, contact=True))
    snapshot = model.snapshot()
    later = BASE+timedelta(minutes=5)
    data = model.detail(None, later)
    for lane in [data, *data["sg"].values()]:
        assert lane["on_s"] == 5 and lane["stops"] == 0
        assert not lane["sessions"][0]["ongoing"] and not lane["sessions"][0]["stop_confirmed"]
        assert lane["sessions"][0]["end"] == lane["sessions"][0]["observed_until"]
    assert not data["task_sessions"][0]["ongoing"]
    assert not model.brief(later)["ongoing"]
    assert model.snapshot() == snapshot


def test_source_deadline_can_end_current_task_before_the_polling_gap_limit():
    model = HeatpumpHistory()
    for n in (0, 5):
        at = BASE+timedelta(seconds=n)
        p = source(at)
        p["native_task"].update(observed_at=BASE.timestamp(), stale_s=20)
        observe(model, at, p=p)
    later = BASE+timedelta(seconds=25)
    data = model.detail(None, later)
    assert data["sessions"][0]["ongoing"]  # Complete electrical source is still current.
    assert not data["task_sessions"][0]["ongoing"]
    assert data["task_sessions"][0]["stop_source"] == "unknown"
    assert model.brief(later)["task"] is None


@pytest.mark.parametrize("watts", [0, 150])
def test_inactive_electrical_reading_cannot_extend_expired_native_active_proof(watts):
    model = HeatpumpHistory()
    for n in (0, 5):
        at = BASE+timedelta(seconds=n)
        p = source(at, watts=watts)
        p["native_task"].update(observed_at=BASE.timestamp(), stale_s=20)
        observe(model, at, p=p)
    later = BASE+timedelta(seconds=25)
    data = model.detail(None, later)
    assert data["on_s"] == 5 and data["energy_known_s"] == 5
    assert data["energy_kwh"] == round(watts*5/3600000, 6)
    assert not data["sessions"][0]["ongoing"] and not data["task_sessions"][0]["ongoing"]
    assert not data["sessions"][0]["stop_confirmed"] and data["stops"] == 0
    assert not model.brief(later)["ongoing"]


def test_stale_open_interval_does_not_claim_unobserved_continuation_after_midnight():
    model = HeatpumpHistory("Europe/Amsterdam")
    start = datetime(2026, 10, 11, 23, 59, tzinfo=ZoneInfo("Europe/Amsterdam"))
    observe(model, start)
    observe(model, start+timedelta(seconds=5))
    later = start+timedelta(minutes=3)
    data = model.detail("2026-10-11", later)
    assert not data["sessions"][0]["continues_next_day"]
    assert not data["task_sessions"][0]["continues_next_day"]
    assert not data["sessions"][0]["ongoing"]
    assert data["on_s"] == 5 and data["stops"] == 0


def test_meter_context_age_does_not_reject_independent_fresh_energy_and_held_reports_expire():
    model = HeatpumpHistory()
    for n in (0, 10, 20):
        at = BASE+timedelta(seconds=n)
        p = source(BASE, task=None)
        p["power_activity"]["observed_at"] -= 1000
        observe(model, at, p=p)
    assert model.detail(None, BASE+timedelta(seconds=20))["energy_known_s"] == 20
    # All raw reports become stale despite a fresh-looking cycle/context time.
    p = source(BASE, task=None)
    p["power_activity"]["observed_at"] = (BASE+timedelta(seconds=121)).timestamp()
    observe(model, BASE+timedelta(seconds=121), p=p)
    assert model.detail(None, BASE+timedelta(seconds=121))["energy_known_s"] == 20


def test_midnight_splits_linear_energy_and_activity_without_extending_through_query_time():
    zone = ZoneInfo("Europe/Amsterdam")
    start = datetime(2026, 10, 11, 23, 59, 50, tzinfo=zone)
    finish = start+timedelta(seconds=20)
    model = HeatpumpHistory("Europe/Amsterdam")
    observe(model, start, watts=1800)
    observe(model, finish, watts=5400)
    before = model.detail("2026-10-11", finish)
    after = model.detail("2026-10-12", finish+timedelta(seconds=60))
    assert before["on_s"] == after["on_s"] == 10
    assert before["energy_kwh"] == 0.0075 and after["energy_kwh"] == 0.0125
    assert before["sessions"][0]["continues_next_day"]
    assert after["sessions"][0]["continued_from_previous_day"]
    assert not model.brief(finish+timedelta(seconds=60))["ongoing"]


@pytest.mark.parametrize("day,seconds", [("2026-03-29", 23*3600), ("2026-10-25", 25*3600)])
def test_dst_days_use_real_elapsed_duration_and_daily_energy(day, seconds):
    zone = ZoneInfo("Europe/Amsterdam")
    start = datetime.fromisoformat(day).replace(tzinfo=zone)
    model = HeatpumpHistory("Europe/Amsterdam")
    for elapsed in range(0, seconds+1, 30):
        at = datetime.fromtimestamp(start.timestamp()+elapsed, UTC)
        observe(model, at, watts=3600)
    end = datetime.fromtimestamp(start.timestamp()+seconds, UTC)
    data = model.detail(day, end)
    assert data["day_seconds"] == seconds
    assert data["on_s"] == data["known_s"] == data["energy_known_s"] == seconds
    assert data["energy_kwh"] == seconds/1000
    assert data["sessions"][0]["width_pct"] == 100
    assert data["task_totals"][0]["on_s"] == seconds


def test_retention_is_30_local_days_and_snapshot_is_detached():
    model = HeatpumpHistory()
    for n in range(40):
        at = BASE+timedelta(days=n)
        observe(model, at)
        observe(model, at+timedelta(seconds=10))
    end = BASE+timedelta(days=39, seconds=10)
    data = model.detail(None, end)
    assert len(data["days"]) == len(model.energy_days) == 30
    assert data["first_date"] == "2026-10-21"
    with pytest.raises(ValueError, match="30 dagen"):
        model.detail("2026-10-20", end)
    snapshot = model.snapshot()
    snapshot["energy_days"].clear()
    assert len(model.energy_days) == 30


def test_task_detail_cap_keeps_daily_totals_and_reports_truncation(monkeypatch):
    import custom_components.solar_pilot.heatpump_history as module
    monkeypatch.setattr(module, "MAX_TASK_SESSIONS", 3)
    model = HeatpumpHistory()
    for n in range(8):
        observe(model, BASE+timedelta(seconds=n*5), task="space_heating" if n % 2 else "space_cooling")
    data = model.detail(None, BASE+timedelta(seconds=35))
    assert len(data["task_sessions"]) == 3 and data["task_sessions_truncated"]
    assert sum(row["on_s"] for row in data["task_totals"]) == 35
    assert data["on_s"] == 35


@pytest.mark.parametrize("fault", ["version", "energy_nan", "energy_unknown", "bad_daily", "bad_session", "timezone"])
def test_nonempty_incompatible_or_corrupt_store_is_rejected_without_replacing_model(fault):
    model = HeatpumpHistory()
    observe(model, BASE)
    observe(model, BASE+timedelta(seconds=10))
    original = model.snapshot()
    bad = deepcopy(original)
    day = next(iter(bad["energy_days"]))
    if fault == "version":
        bad["version"] = 99
    elif fault == "energy_nan":
        bad["energy_days"][day]["energy_kwh"] = float("nan")
    elif fault == "energy_unknown":
        bad["energy_days"][day]["energy_known_s"] = -1
    elif fault == "bad_daily":
        bad["lanes"]["devices"]["heatpump"]["days"][day]["known_s"] = "bad"
    elif fault == "bad_session":
        bad["lanes"]["devices"]["heatpump"]["sessions"][0]["start"] = None
    else:
        bad["timezone"] = "UTC"
    with pytest.raises(ValueError):
        model.restore(bad, BASE+timedelta(seconds=20))
    assert model.snapshot() == original


def test_first_empty_history_has_unknown_runtime_and_empty_days_without_backfill():
    model = HeatpumpHistory()
    assert model.restore(None, BASE)
    assert model.restore({}, BASE)
    detail = model.detail(None, BASE)
    assert detail["on_s"] is None and not detail["has_data"]
    assert all(day["on_s"] is None and day["energy_kwh"] is None for day in detail["days"])
    assert detail["energy_kwh"] is None and not detail["sessions"] and not detail["task_sessions"]


def test_naive_timestamps_and_dates_outside_retention_are_rejected():
    model = HeatpumpHistory()
    with pytest.raises(ValueError, match="timezone-aware"):
        model.observe({}, {}, datetime(2026, 10, 11))
    with pytest.raises(ValueError):
        model.detail("2026-10-12", BASE)
