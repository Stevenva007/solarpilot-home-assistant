"""Forecast coverage, elapsed time and independent calibration accounting."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from custom_components.solar_pilot.pv_forecast import PVForecast
from custom_components.solar_pilot.pv_forecast_source import ForecastSolarSource, PowerSeries
from custom_components.solar_pilot.pv_calibration import PVCalibration
from custom_components.solar_pilot.unified_planner import UnifiedPlanner
from custom_components.solar_pilot.planner_quality import ReplayBuffer
from test_pv_forecast33 import settings, source_fixture
from test_runtime import build


UTC = timezone.utc
BRUSSELS = ZoneInfo("Europe/Brussels")
NOW = datetime(2026, 10, 4, 10, tzinfo=UTC)


def planner():
    return UnifiedPlanner({"horizon_h": 6, "slot_min": 60}, {
        "base_load_profile": {"median_w_by_hour": {str(h): 500 for h in range(24)}},
    })


def plan(p, pv, now=NOW, **extra):
    return p.build(local_now=now, pv_hourly_w=pv, import_prices=[.3]*6,
                   export_prices=[.03]*6, devices=[{
                       "id": "load", "forecast_deferrable": True,
                       "required_kwh": 6, "power_w": 1000,
                   }], **extra)


def test_truncated_pv_horizon_never_repeats_last_sunny_hour_into_unknown_future():
    result = plan(planner(), [5000])

    assert result.devices["load"].selected_slots == [0]
    assert all(slot.pv_w == 0 for slot in result.slots[1:])
    assert all(not slot.pv_available for slot in result.slots[1:])
    assert result.warnings
    assert result.overview()["timeline"][1]["pv_w"] is None


def test_known_night_zero_and_missing_pv_have_distinct_quality_coverage():
    p = planner()
    result = plan(p, [0, None, 0, None, 0, None])
    complete = plan(planner(), [0]*6)

    assert result.slots[0].pv_available
    assert not result.slots[1].pv_available
    assert result.confidence < complete.confidence
    for hour in (0, 1):
        local_now = NOW + timedelta(hours=hour)
        p.observe_actual(wall_ts=local_now.timestamp(), local_now=local_now,
                         actual_pv_w=0, actual_base_w=500, actual_grid_w=500)
    report = p.quality.overview()["last_7d"]
    assert report["samples"] == 1
    assert report["net_mae_w"] == 0
    assert report["base_mae_w"] == 0
    assert report["context_samples"]["normal"] == 2


@pytest.mark.parametrize("now", [
    datetime(2026, 3, 29, 1, tzinfo=BRUSSELS),
    datetime(2026, 10, 25, 1, tzinfo=BRUSSELS),
])
def test_planner_slots_and_current_selection_follow_elapsed_hours_across_dst(now):
    p = planner()
    result = plan(p, [0, 1000, 2000, 3000, 4000, 5000], now)

    assert [slot.start.timestamp() for slot in result.slots] == [
        now.timestamp() + i*3600 for i in range(6)
    ]
    for i, slot in enumerate(result.slots):
        current = datetime.fromtimestamp(now.timestamp() + i*3600 + 60, BRUSSELS)
        assert p.current_slot(current) is slot


@pytest.mark.parametrize("offset", [-1, 6*3600, 10*3600])
def test_plan_cannot_claim_a_running_slot_outside_its_observed_horizon(offset):
    p = planner()
    result = plan(p, [5000]*6)
    current = NOW + timedelta(seconds=offset)

    assert p.current_slot(current) is None
    assert result.current_device_state("load", current)[:2] == (False, False)


@pytest.mark.parametrize("role,unit", [("now_entity", "W"), ("tomorrow_entity", "kWh")])
def test_restored_forecast_scalar_cannot_grant_forecast_validity(role, unit):
    runtime, hass = build()
    hass.states.set("sensor.forecast", 3000, {"unit_of_measurement": unit, "restored": True})
    source = ForecastSolarSource(hass, settings(**{role: "sensor.forecast"}))

    source.refresh(datetime.now(UTC).timestamp())

    assert not source.valid
    assert source.scalars[role] is None
    assert not hass.services.calls


def test_restored_scalar_cannot_validate_retained_coordinator_curve(monkeypatch):
    runtime, hass, entries, now = source_fixture(monkeypatch)
    hass.states.get("sensor.renamed_by_user").attributes["restored"] = True
    source = ForecastSolarSource(hass, settings())

    source.refresh(now.timestamp())

    assert not source.valid
    assert not source.series.points
    assert source.raw_at(now.timestamp() + 7200, now.timestamp()) is None


def test_forecast_scalar_last_reported_none_uses_real_last_updated():
    runtime, hass = build()
    hass.states.set("sensor.forecast", 3000, {"unit_of_measurement": "W"})
    hass.states.get("sensor.forecast").last_reported = None
    source = ForecastSolarSource(hass, settings(now_entity="sensor.forecast"))

    source.refresh(datetime.now(UTC).timestamp())

    assert source.valid and source.scalars["now_entity"] == 3000


@pytest.mark.parametrize("now", [
    datetime(2026, 3, 29, 1, 30, tzinfo=BRUSSELS),
    datetime(2026, 10, 25, 2, 30, tzinfo=BRUSSELS, fold=0),
    datetime(2026, 10, 25, 2, 30, tzinfo=BRUSSELS, fold=1),
])
def test_pv_current_next_hour_and_power_horizon_use_real_elapsed_time(now):
    runtime, hass = build()
    forecast = PVForecast(runtime)
    source = forecast.source
    start = now.replace(minute=0, second=0, microsecond=0).timestamp()
    source.valid = True
    source.series = PowerSeries([(start + i*3600, 1000*(i+1)) for i in range(6)])
    source.scalars = {}
    source.refresh = lambda ts: None

    forecast.update(now)

    assert not forecast.error
    assert forecast.cached["raw_current_hour_kwh"] == pytest.approx(1.5)
    assert forecast.cached["raw_next_hour_kwh"] == pytest.approx(2.5)
    assert [datetime.fromisoformat(row["time"]).timestamp() for row in forecast.cached["horizon"]] == [
        now.timestamp() + i*3600 for i in range(4)
    ]
    assert [row["raw_w"] for row in forecast.cached["horizon"]] == [1500, 2500, 3500, 4500]


def test_backward_meter_report_cannot_be_used_as_an_independent_calibration_sample():
    model = PVCalibration(settings())
    model.started = NOW.timestamp() - 1000
    for minute in range(16):
        now = NOW + timedelta(minutes=minute)
        # Both reports pass age checks, but each odd report predates the prior
        # report and must not count as a new independent meter observation.
        stamp = now.timestamp() + 5 if minute % 2 == 0 else now.timestamp() - 110
        model.observe(now=now, actual_w=2400, raw_w=3000, meter_stamp=stamp,
                      azimuth=190, elevation=35)

    assert model.counts["accepted"] == 0
    assert not model.history[-1]["accepted"]
    assert not model.bins


@pytest.mark.parametrize("meter_stamp", [True, [], "invalid", float("nan"), float("inf")])
def test_invalid_meter_timestamp_does_not_poison_later_independent_pv_learning(meter_stamp):
    model = PVCalibration(settings())
    model.started = NOW.timestamp() - 1000
    model.observe(now=NOW, actual_w=2400, raw_w=3000, meter_stamp=meter_stamp,
                  azimuth=190, elevation=35)
    assert model.last_meter_stamp is None
    for minute in range(15, 31):
        now=NOW+timedelta(minutes=minute)
        model.observe(now=now, actual_w=2400, raw_w=3000, meter_stamp=now.timestamp(),
                      azimuth=190, elevation=35)

    assert model.counts["accepted"]==1


def test_future_meter_timestamp_cannot_freeze_calibration_after_fresh_reports_resume():
    model = PVCalibration(settings())
    model.started = NOW.timestamp() - 1000
    model.observe(now=NOW, actual_w=2400, raw_w=3000, meter_stamp=NOW.timestamp()+86400,
                  azimuth=190, elevation=35)
    assert model.last_meter_stamp is None
    for minute in range(15, 31):
        now=NOW+timedelta(minutes=minute)
        model.observe(now=now, actual_w=2400, raw_w=3000, meter_stamp=now.timestamp(),
                      azimuth=190, elevation=35)

    assert model.counts["accepted"]==1


def test_valid_complete_forecast_and_chronological_meter_reports_keep_existing_results():
    result = plan(planner(), [5000]*6)
    assert result.devices["load"].planned_kwh == 6
    assert all(slot.pv_available for slot in result.slots)
    assert result.predicted_export_kwh == 21
    model = PVCalibration(settings())
    model.started = NOW.timestamp() - 1000
    for minute in range(16):
        now = NOW + timedelta(minutes=minute)
        model.observe(now=now, actual_w=2400, raw_w=3000, meter_stamp=now.timestamp(),
                      azimuth=190, elevation=35)
    assert model.counts["accepted"] == 1


def test_replay_keeps_valid_zero_tariffs_instead_of_substituting_defaults():
    replay = ReplayBuffer()
    replay.observe(local_now=NOW, pv_w=0, base_w=500, grid_w=500,
                   import_price=0, export_price=0)

    assert replay.rows()[0][1]["import_price"] == 0
    assert replay.rows()[0][1]["export_price"] == 0


def replay_day(p, start, *, quarter_count=None, skip=None):
    end = (start + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
    quarters = int((end.timestamp()-start.timestamp())//900)
    for i in range(quarters if quarter_count is None else quarter_count):
        if i == skip:
            continue
        dt = datetime.fromtimestamp(start.timestamp() + i*900, start.tzinfo)
        p.replay.observe(local_now=dt, pv_w=0, base_w=500, grid_w=500,
                         import_price=0, export_price=0)


def test_partial_replay_days_are_preserved_without_fabricated_full_day_scenarios():
    p = planner()
    replay_day(p, NOW.replace(hour=0), quarter_count=48)
    replay_day(p, (NOW+timedelta(days=1)).replace(hour=0), quarter_count=48)

    result = p.replay_scenarios([])

    assert not result["ready"]
    assert not result["scenarios"]
    assert result["buffer"]["samples"] == 96
    assert len(p.replay.samples) == 96


def test_one_missing_quarter_does_not_become_zero_pv_in_a_daily_replay_claim():
    p = planner()
    replay_day(p, NOW.replace(hour=0))
    replay_day(p, (NOW+timedelta(days=1)).replace(hour=0), skip=40)

    assert not p.replay_scenarios([])["ready"]
    assert len(p.replay.samples) == 191


@pytest.mark.parametrize("start,expected_quarters,expected_import_kwh", [
    (datetime(2026, 3, 28, tzinfo=BRUSSELS), 96+92, (24+23)*.5),
    (datetime(2026, 10, 24, tzinfo=BRUSSELS), 96+100, (24+25)*.5),
    (NOW.replace(hour=0), 96+96, 24),
])
def test_complete_replay_days_use_actual_dst_duration_and_real_zero_prices(
        start, expected_quarters, expected_import_kwh):
    p = planner()
    replay_day(p, start)
    replay_day(p, start+timedelta(days=1))

    result = p.replay_scenarios([])

    assert result["ready"]
    assert result["buffer"]["samples"] == expected_quarters
    assert all(row["import_kwh"] == expected_import_kwh for row in result["scenarios"])
    assert all(row["cost_eur"] == 0 for row in result["scenarios"])


def test_exact_hourly_forecast_cache_does_not_alias_different_seconds_in_same_minute():
    runtime, hass = build()
    forecast = PVForecast(runtime)
    forecast.source.valid = True
    start = NOW.timestamp()
    forecast.source.series = PowerSeries([(start, 1000), (start+7200, 3000)])

    first = forecast.hourly(NOW, 1)
    shifted = forecast.hourly(NOW+timedelta(seconds=30), 1)

    assert first == [1500]
    assert shifted == pytest.approx([1500+30*1000/3600])
