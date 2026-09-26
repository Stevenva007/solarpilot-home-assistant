from datetime import datetime, timezone
from custom_components.solar_pilot.pv_model import LocalPVModel


def seed():
    return {"source":{"sunny_days_used":79},"pv_profile":{"median_actual_to_forecast_ratio_by_hour":{"16":.7,"17":.4,"18":.8}}}


def test_historical_seed_is_low_confidence_bootstrap():
    m=LocalPVModel({"min_days":3},seed())
    factor, confidence, source, days=m.factor_for(datetime(2026,9,1,16,tzinfo=timezone.utc),200,20)
    assert source=="historische bootstrap" and .2 <= factor <= 1.8 and confidence <= .45 and days==79


def test_live_distinct_days_override_seed():
    m=LocalPVModel({"min_days":3,"sample_interval_s":0},seed())
    for day in range(1,6):
        dt=datetime(2026,9,day,16,tzinfo=timezone.utc)
        assert m.observe(wall_stamp=day*1000,local_now=dt,actual_w=400,forecast_w=1000,azimuth=200,elevation=20)
    factor, confidence, source, days=m.factor_for(datetime(2026,9,20,16,tzinfo=timezone.utc),200,20)
    assert source.startswith("live") and .35 < factor < .45 and days>=5 and confidence>0


def test_cloudy_low_forecast_not_learned():
    m=LocalPVModel({"sample_interval_s":0,"min_forecast_w":400},seed())
    ok=m.observe(wall_stamp=100,local_now=datetime.now(timezone.utc),actual_w=50,forecast_w=100,azimuth=180,elevation=20)
    assert not ok and m.samples==0


def test_prediction_corrects_external_forecast():
    m=LocalPVModel({},seed())
    p=m.prediction(local_now=datetime(2026,9,1,16,tzinfo=timezone.utc),forecast_power_w=2000,current_hour_kwh=2,next_hour_kwh=2,azimuth=200,elevation=20)
    assert p.corrected_power_w is not None and p.corrected_power_w < 2000
    assert p.corrected_current_hour_kwh is not None


def test_snapshot_restore_keeps_live_profile():
    m=LocalPVModel({"min_days":2,"sample_interval_s":0},seed())
    for day in (1,2,3):
        m.observe(wall_stamp=day*1000,local_now=datetime(2026,8,day,15,tzinfo=timezone.utc),actual_w=600,forecast_w=1000,azimuth=190,elevation=25)
    snap=m.snapshot(); n=LocalPVModel({"min_days":2},seed()); n.restore(snap)
    assert n.samples==m.samples and n.factor_for(datetime(2026,8,10,15,tzinfo=timezone.utc),190,25)[2].startswith("live")
