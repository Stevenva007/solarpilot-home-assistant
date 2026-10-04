"""A malformed planner snapshot cannot block valid retained learning data."""
from datetime import datetime, timedelta, timezone
import json
import time

import pytest

from custom_components.solar_pilot.unified_planner import BaseLoadModel, UnifiedPlanner
from custom_components.solar_pilot.planner_quality import PlanQualityTracker, ReplayBuffer


UTC=timezone.utc


@pytest.mark.parametrize("counter", [None, [], "invalid", True, float("inf"), float("nan")])
def test_invalid_base_counter_does_not_discard_valid_sibling_profile_or_freeze_learning(counter):
    now=datetime.now(UTC)
    key=BaseLoadModel._key(now)
    day=now.date().isoformat()
    model=BaseLoadModel()
    model.restore({"accepted":counter,"last_sample_wall":time.time()+86400,"bins":{
        key:{"days":{day:[1200,True,float("nan"),1300]}},
        "weekday:wrong":{"days":{day:[3000]}},"weekend:0":[],
    }})

    assert model.accepted==0
    assert model.last_sample_wall==0
    assert model.bins[key]["days"][day]==[1200,1300]
    assert len(model.bins)==1
    assert model.observe(time.time(),now,1400)
    json.dumps(model.snapshot(),allow_nan=False)


@pytest.mark.parametrize("profile", [None, [], {"median_w_by_hour":[]}, {
    "median_w_by_hour":{"bad":4000,"12":float("inf")},
    "median_w_by_daytype_hour":{"weekday":None,"weekend":[]},
}])
def test_malformed_base_seed_falls_back_without_invalid_confidence(profile):
    model=BaseLoadModel({"base_load_profile":profile})

    value,confidence,source=model.estimate(datetime.now(UTC))

    assert value==800 and confidence==.1
    assert source=="conservatieve fallback"


def test_base_restore_retains_valid_days_and_rejects_far_future_learning():
    now=datetime.now(UTC)
    key=BaseLoadModel._key(now)
    day=now.date().isoformat()
    future=(now+timedelta(days=60)).date().isoformat()
    model=BaseLoadModel()
    model.restore({"bins":{key:{"days":{day:[700],future:[19000],"bad":[500]}}}})

    assert model.bins[key]["days"]=={day:[700]}
    assert model.detail(now)["days"]==1


def test_invalid_day_rows_cannot_push_valid_learning_out_of_restore_limit():
    now=datetime.now(UTC)
    key=BaseLoadModel._key(now)
    day=now.date().isoformat()
    rows={f"invalid-{i}":[9000] for i in range(100)}
    rows[day]=[700]
    model=BaseLoadModel()

    model.restore({"bins":{key:{"days":rows}}})

    assert model.bins[key]["days"]=={day:[700]}


@pytest.mark.parametrize("counter", [None, [], "invalid", True, float("inf"), float("nan")])
def test_quality_restore_quarantines_invalid_shapes_without_losing_legacy_error_rows(counter):
    now=datetime.now(UTC)
    day=now.date().isoformat()
    q=PlanQualityTracker()
    q.restore({"retention_days":counter,"last_sample_wall":time.time()+86400,"days":{
        day:{"count":2,"pv_abs":600,"pv_bias":-400,"new_samples":3,
             "contexts":[],"covered_seconds":float("nan"),"base_count":counter},
        "bad-date":{"count":100},
        (now-timedelta(days=1)).date().isoformat():[],
    }})

    assert q.overview()["last_7d"]["pv_mae_w"]==300
    assert q.overview()["last_7d"]["covered_hours"] is None
    assert q.last_sample_wall==0
    assert q.observe(wall_ts=time.time(),local_now=now,predicted_pv_w=1000,actual_pv_w=1200)
    assert q.overview()["last_7d"]["samples"]==3
    json.dumps(q.snapshot(),allow_nan=False)


def test_invalid_future_quality_day_cannot_hide_recent_observed_errors():
    now=datetime.now(UTC)
    day=now.date().isoformat()
    future=(now+timedelta(days=60)).date().isoformat()
    q=PlanQualityTracker()
    q.restore({"days":{day:{"count":2,"pv_abs":600,"pv_bias":-400},
                       future:{"count":1000,"pv_abs":0}}})

    assert q.overview()["last_7d"]["samples"]==2
    assert set(q.days)=={day}


@pytest.mark.parametrize("bad_row", [None, [], {"pv_w":True}, {
    "pv_w":float("inf"),"base_w":500,"grid_w":100,
}])
def test_replay_restore_preserves_valid_partial_rows_and_zero_prices(bad_row):
    now=datetime.now(UTC).replace(minute=0,second=0,microsecond=0)
    valid={"pv_w":0,"base_w":500,"grid_w":500,"import_price":0,"export_price":0}
    replay=ReplayBuffer()
    replay.restore({"retention_days":"invalid","samples":{
        now.isoformat():valid,
        (now-timedelta(minutes=15)).isoformat():bad_row,
        "bad-date":valid,
    }})

    assert replay.overview()["samples"]==1
    assert replay.rows()[0][1]["import_price"]==0
    assert replay.rows()[0][1]["export_price"]==0
    json.dumps(replay.snapshot(),allow_nan=False)


def test_invalid_planner_run_counter_keeps_valid_base_and_replay_siblings():
    now=datetime.now(UTC)
    planner=UnifiedPlanner()
    planner.restore({"plan_runs":"invalid","base_load":{"accepted":12},
                     "quality":{"days":{}},"replay":{"samples":{now.isoformat():{
                         "pv_w":0,"base_w":500,"grid_w":500,"import_price":0,"export_price":0,
                     }}}})

    assert planner.plan_runs==0
    assert planner.base_load.accepted==12
    assert planner.replay.overview()["samples"]==1
