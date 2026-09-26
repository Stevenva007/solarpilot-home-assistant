from datetime import datetime, timezone, timedelta
from custom_components.solar_pilot.planner_quality import PlanQualityTracker, ReplayBuffer


def test_quality_tracker_reports_mae_and_execution_match():
    q=PlanQualityTracker()
    t=datetime(2026,9,1,12,0,tzinfo=timezone.utc)
    for i in range(12):
        q.observe(wall_ts=1000+i*301,local_now=t+timedelta(minutes=5*i),predicted_pv_w=2000,actual_pv_w=2200,
                  predicted_base_w=800,actual_base_w=900,predicted_net_w=-1200,actual_net_w=-1300,execution_total=2,execution_matches=2)
    o=q.overview()['last_7d']
    assert o['pv_mae_w']==200
    assert o['base_mae_w']==100
    assert o['execution_match_pct']==100
    assert o['quality_score']>80


def test_replay_buffer_is_15_minute_keyed_and_bounded():
    r=ReplayBuffer(retention_days=3)
    t=datetime(2026,9,10,10,7,tzinfo=timezone.utc)
    assert r.observe(local_now=t,pv_w=1000,base_w=500,grid_w=-500,import_price=.3,export_price=.03)
    assert r.observe(local_now=t+timedelta(minutes=3),pv_w=1100,base_w=500,grid_w=-600,import_price=.3,export_price=.03)
    assert len(r.samples)==1
    row=r.rows()[0][1]
    assert row['pv_w']==1100
