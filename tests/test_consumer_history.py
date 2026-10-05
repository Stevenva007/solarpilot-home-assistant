"""Real history model: no HA installation, IO, device commands or wall-clock waits."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from copy import deepcopy
import pytest

from custom_components.solar_pilot.consumer_history import ConsumerHistory, MAX_SESSIONS, MAX_EVENTS

UTC = timezone.utc
CFG = {"name": "Testverbruiker", "kind": "switch", "control_entity": "switch.load", "ack_timeout_s": 60}
BASE = datetime(2026, 9, 27, 10, tzinfo=ZoneInfo("Europe/Brussels"))


def run(model, active, when, **kwargs):
    model.observe("one", CFG, active, when, **kwargs)


def test_confirmed_start_stop_have_exact_action_reasons_and_daily_duration():
    h=ConsumerHistory();run(h,False,BASE)
    h.command("one",CFG,350,"Zonneoverschot na startvertraging",BASE)
    # Request itself is not an actual start.
    assert h.detail("one",None,BASE)["sessions"]==[]
    h.confirm("one");run(h,True,BASE+timedelta(seconds=5))
    run(h,True,BASE+timedelta(seconds=20))
    h.command("one",CFG,0,"Wallbox krijgt voorrang",BASE+timedelta(seconds=20))
    h.confirm("one");run(h,False,BASE+timedelta(seconds=25))
    data=h.detail("one",None,BASE+timedelta(seconds=25))
    assert data["on_s"]==20
    assert data["starts"]==data["stops"]==1
    s=data["sessions"][0]
    assert s["start_reason"]=="Zonneoverschot na startvertraging"
    assert s["stop_reason"]=="Wallbox krijgt voorrang"
    assert s["start_source"]==s["stop_source"]=="solarpilot"
    assert s["duration_s"]==20 and not s["ongoing"]


def test_external_observed_start_stop_is_not_claimed_as_solarpilot():
    h=ConsumerHistory();run(h,False,BASE);run(h,True,BASE+timedelta(seconds=5));run(h,False,BASE+timedelta(seconds=25))
    s=h.detail("one",None,BASE+timedelta(seconds=25))["sessions"][0]
    assert s["start_source"]==s["stop_source"]=="external"
    assert "andere automatisering" in s["start_reason"]


def test_already_on_at_first_install_has_unknown_start_and_no_invented_past():
    h=ConsumerHistory();run(h,True,BASE);run(h,True,BASE+timedelta(seconds=10))
    d=h.detail("one",None,BASE+timedelta(seconds=10))
    assert d["on_s"]==10 and d["starts"]==0 and d["partial"]
    assert d["sessions"][0]["start_source"]=="unknown"
    assert not d["sessions"][0]["start_confirmed"]
    assert h.detail("one","2026-09-26",BASE)["has_data"] is False


def test_no_solar_start_for_unconfirmed_request():
    h=ConsumerHistory();run(h,False,BASE)
    h.command("one",CFG,350,"overschot",BASE)
    run(h,False,BASE+timedelta(seconds=20))
    assert h.detail("one",None,BASE+timedelta(seconds=20))["starts"]==0
    h.failure("one",CFG,"Geen terugmelding",BASE+timedelta(seconds=30))
    d=h.detail("one",None,BASE+timedelta(seconds=30))
    assert not d["sessions"] and d["events"][0]["kind"]=="warning"
    assert "overschot" in d["events"][0]["reason"]


def test_late_transition_after_failed_command_is_external_unknown_not_auto_confirmed():
    h=ConsumerHistory();run(h,False,BASE);h.command("one",CFG,350,"overschot",BASE)
    h.failure("one",CFG,"Uitkomst onzeker",BASE);run(h,True,BASE+timedelta(seconds=5))
    assert h.detail("one",None,BASE+timedelta(seconds=5))["sessions"][0]["start_source"]=="external"


def test_manual_takeover_is_event_without_fake_stop_or_new_session():
    h=ConsumerHistory();run(h,True,BASE)
    h.event("one",CFG,"Handmatig overgenomen; geen uitschakeling",BASE+timedelta(seconds=5))
    run(h,True,BASE+timedelta(seconds=10))
    d=h.detail("one",None,BASE+timedelta(seconds=10))
    assert d["on_s"]==10 and d["stops"]==0 and len(d["sessions"])==1
    assert len(d["events"])==1


def test_unknown_status_does_not_count_as_stop_and_gap_is_not_runtime():
    h=ConsumerHistory();run(h,True,BASE);run(h,True,BASE+timedelta(seconds=10))
    run(h,None,BASE+timedelta(seconds=15));run(h,None,BASE+timedelta(seconds=25))
    run(h,True,BASE+timedelta(seconds=30));run(h,True,BASE+timedelta(seconds=40))
    d=h.detail("one",None,BASE+timedelta(seconds=40))
    assert d["on_s"]==20 and d["stops"]==0 and d["starts"]==0
    assert len(d["sessions"])==2
    assert d["sessions"][0]["stop_source"]=="unknown"
    assert not d["sessions"][0]["stop_confirmed"]


def test_long_polling_gap_not_backfilled_even_when_both_endpoints_on():
    h=ConsumerHistory();run(h,True,BASE);run(h,True,BASE+timedelta(seconds=10))
    run(h,True,BASE+timedelta(hours=2));run(h,True,BASE+timedelta(hours=2,seconds=10))
    d=h.detail("one",None,BASE+timedelta(hours=2,seconds=10))
    assert d["on_s"]==20 and len(d["sessions"])==2


def test_restart_preserves_history_but_never_assumes_operation_during_downtime():
    h=ConsumerHistory();run(h,True,BASE);run(h,True,BASE+timedelta(seconds=20))
    before=h.snapshot();h2=ConsumerHistory();h2.restore(before,{"one":CFG},BASE+timedelta(hours=1))
    run(h2,True,BASE+timedelta(hours=1));run(h2,True,BASE+timedelta(hours=1,seconds=10))
    d=h2.detail("one",None,BASE+timedelta(hours=1,seconds=10))
    assert d["on_s"]==30 and d["stops"]==0 and len(d["sessions"])==2
    assert not d["sessions"][0]["stop_confirmed"]
    assert h.snapshot()==before  # Restore did not mutate the saved object.


def test_graceful_close_does_not_claim_the_device_was_stopped():
    h=ConsumerHistory();run(h,True,BASE);run(h,True,BASE+timedelta(seconds=10));h.pause_recording()
    d=h.detail("one",None,BASE+timedelta(seconds=10))
    assert not d["sessions"][0]["stop_confirmed"] and d["stops"]==0
    assert "niet uitgeschakeld" in d["sessions"][0]["stop_reason"]


def test_midnight_splits_runtime_and_display_intervals_without_new_start():
    h=ConsumerHistory();t=BASE.replace(hour=23,minute=59,second=50)
    run(h,False,t-timedelta(seconds=5));run(h,True,t)
    run(h,True,t+timedelta(seconds=20));run(h,False,t+timedelta(seconds=30))
    d1=h.detail("one","2026-09-27",t+timedelta(seconds=30))
    d2=h.detail("one","2026-09-28",t+timedelta(seconds=30))
    assert d1["on_s"]==10 and d2["on_s"]==20
    assert d1["starts"]==1 and d2["starts"]==0
    assert d1["stops"]==0 and d2["stops"]==1
    assert d1["sessions"][0]["continues_next_day"]
    assert d2["sessions"][0]["continued_from_previous_day"]


@pytest.mark.parametrize('day,hours',[("2026-03-29",23),("2026-10-25",25),("2026-09-27",24)])
def test_dst_days_use_actual_elapsed_seconds_not_assumed_24_hours(day,hours):
    h=ConsumerHistory();t=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo("Europe/Brussels"))
    run(h,True,t)
    end=(t+timedelta(days=1)).astimezone(UTC)
    run(h,False,end,max_gap_s=100000)
    d=h.detail("one",day,end)
    assert d["on_s"]==hours*3600 and d["day_seconds"]==hours*3600
    assert len(d["sessions"])==1 and d["sessions"][0]["duration_s"]==hours*3600
    assert not d["partial"]


def test_session_ending_exactly_midnight_not_duplicated_on_next_day():
    h=ConsumerHistory();t=BASE.replace(hour=23,minute=59,second=50);run(h,True,t);run(h,False,t+timedelta(seconds=10))
    d=h.detail("one",None,t+timedelta(seconds=10))
    assert d["on_s"]==0 and d["sessions"]==[] and d["stops"]==1


def test_config_rename_preserves_session_but_binding_change_does_not_merge_devices():
    h=ConsumerHistory();run(h,True,BASE)
    h.observe("one",{**CFG,"name":"Nieuwe naam"},True,BASE+timedelta(seconds=10))
    assert len(h.devices["one"]["sessions"])==1
    h.observe("one",{**CFG,"control_entity":"switch.other"},True,BASE+timedelta(seconds=20))
    d=h.detail("one",None,BASE+timedelta(seconds=20))
    assert len(d["sessions"])==2 and d["on_s"]==10
    assert "Koppeling gewijzigd" in d["sessions"][0]["stop_reason"]


def test_two_consumers_never_leak_into_each_others_detail():
    h=ConsumerHistory();run(h,True,BASE);h.observe("two",{**CFG,"name":"Other"},False,BASE)
    assert h.detail("one",None,BASE)["name"]=="Testverbruiker"
    assert h.detail("two",None,BASE)["sessions"]==[]
    assert "Other" not in str(h.detail("one",None,BASE))


def test_brief_does_not_contain_session_arrays_or_old_days():
    h=ConsumerHistory();run(h,True,BASE)
    brief=h.brief("one",BASE)
    assert set(brief)=={"date","on_s","recording","ongoing","revision","last_change"}
    assert brief["last_change"]["confirmed"] is False
    assert "sessions" not in str(brief)


def test_continuous_observations_do_not_create_event_or_session_flood():
    h=ConsumerHistory();run(h,True,BASE);rev=h.revision
    for i in range(1,721):run(h,True,BASE+timedelta(seconds=i*5))
    assert len(h.devices["one"]["sessions"])==1 and not h.devices["one"]["events"]
    assert h.revision==rev and h.brief("one",BASE)["on_s"]==3600


def test_idle_day_has_zero_runtime_and_known_coverage_not_missing():
    h=ConsumerHistory();t=BASE.replace(hour=0);run(h,False,t);run(h,False,t+timedelta(seconds=10))
    d=h.detail("one",None,t+timedelta(seconds=10))
    assert d["has_data"] and d["on_s"]==0 and not d["partial"] and not d["sessions"]


@pytest.mark.parametrize('day',["2026-99-33","yesterday","2026-09-28","2026-08-28","20260927","../../secrets.yaml"])
def test_api_day_is_strict_and_bounded(day):
    h=ConsumerHistory();run(h,True,BASE)
    with pytest.raises((ValueError,TypeError)):h.detail("one",day,BASE)


def test_retention_30_days_prunes_old_details_without_affecting_open_session():
    h=ConsumerHistory();run(h,True,BASE)
    for i in range(1,36):run(h,True,BASE+timedelta(days=i),max_gap_s=100000)
    d=h.detail("one",None,BASE+timedelta(days=35))
    assert len(h.devices["one"]["days"])==30 and len(d["days"])==30
    assert d["sessions"][0]["continued_from_previous_day"]


def test_session_cap_keeps_aggregates_and_marks_truncated_details():
    h=ConsumerHistory();run(h,False,BASE)
    for i in range(MAX_SESSIONS+1):
        run(h,True,BASE+timedelta(seconds=i*2+1));run(h,False,BASE+timedelta(seconds=i*2+2))
    d=h.detail("one",None,BASE+timedelta(seconds=2*(MAX_SESSIONS+1)))
    assert len(h.devices["one"]["sessions"])==MAX_SESSIONS
    assert d["starts"]==MAX_SESSIONS+1 and d["on_s"]==MAX_SESSIONS+1
    assert d["sessions_truncated"]


def test_event_cap_and_snapshot_independence():
    h=ConsumerHistory();run(h,False,BASE)
    for _ in range(MAX_EVENTS+10):h.event("one",CFG,"info",BASE)
    assert len(h.devices["one"]["events"])==MAX_EVENTS
    snap=h.snapshot();snap["devices"].clear();assert h.devices


@pytest.mark.parametrize('bad',[None,[],{"version":99},{"version":1,"devices":[]},{"version":1,"devices":{"one": {"since":"bad"}}}])
def test_malformed_optional_storage_does_not_crash(bad):
    h=ConsumerHistory();h.restore(bad,{"one":CFG},BASE);run(h,False,BASE)
    assert h.detail("one",None,BASE)["has_data"]


def test_clock_reversal_not_double_counted():
    h=ConsumerHistory();run(h,True,BASE);run(h,True,BASE+timedelta(seconds=20))
    run(h,True,BASE+timedelta(seconds=10));run(h,True,BASE+timedelta(seconds=25))
    assert h.detail("one",None,BASE+timedelta(seconds=25))["on_s"]==25


def test_naive_timestamp_is_rejected_and_invalid_active_is_not_coerced():
    h=ConsumerHistory()
    with pytest.raises(ValueError):run(h,True,BASE.replace(tzinfo=None))
    with pytest.raises(ValueError):run(h,'on',BASE)


def test_removed_device_not_restored_and_timezone_name_validated():
    h=ConsumerHistory();run(h,True,BASE)
    other=ConsumerHistory('invalid/zone');other.restore(h.snapshot(),{},BASE)
    assert other.timezone_name=='UTC' and other.devices=={}


def test_unknown_first_observation_does_not_publish_zero_runtime():
    model=ConsumerHistory('Europe/Brussels')
    at=datetime(2026,9,27,12,tzinfo=timezone.utc)
    model.observe('missing', {'name':'Demo'}, None, at)
    assert model.brief('missing',at)['on_s'] is None
    assert model.brief('missing',at)['recording'] is False
