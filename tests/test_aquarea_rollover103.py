"""SolarPilot captures Aquarea 1.8.1's native periods, without running its API."""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from custom_components.solar_pilot.cloud_energy_period import cloud_energy_periods, period_evidence
from test_cloud_energy_period91 import setup_source


UTC = timezone.utc
PROVIDER = {"integration_loaded": True, "integration_domain": "aquarea",
            "integration_version": "1.8.1", "library_distribution": "aioaquarea-ng",
            "library_version": "1.4.0"}


def month_source(monkeypatch, start, capture):
    env = setup_source(monkeypatch, key="accumulated_energy_consumption")
    env.entity.period_being_processed = start
    env.coordinator.consumption_month = start.date()
    env.coordinator._last_monthly_fetch_time = capture-timedelta(minutes=2)
    env.state.last_reported = capture-timedelta(seconds=2)
    env.captured = capture
    return env


def capture(env, at=None):
    return cloud_energy_periods(env.hass, [env.eid], PROVIDER,
                               captured_at=env.captured if at is None else at)


@pytest.mark.parametrize("start,capture_time,end", [
    ("2026-03-01T00:00:00+00:00", "2026-04-01T03:30:00+02:00", "2026-04-01T00:00:00+00:00"),
    ("2026-10-01T00:00:00+00:00", "2026-11-01T03:30:00+01:00", "2026-11-01T00:00:00+00:00"),
    ("2026-12-01T00:00:00+00:00", "2027-01-01T02:30:00+01:00", "2027-01-01T00:00:00+00:00"),
])
def test_delayed_native_month_is_not_replaced_by_the_new_capture_month(start, capture_time, end, monkeypatch):
    original, at = datetime.fromisoformat(start), datetime.fromisoformat(capture_time)
    env = month_source(monkeypatch, original, at)
    before = (env.entity.period_being_processed, env.coordinator._last_monthly_fetch_time,
              env.state.last_reported, env.entity.native_value)
    row = capture(env)[env.eid]
    assert row["provider"]["integration_version"] == "1.8.1"
    assert row["status"] == "known_period" and row["period_start"] == start
    assert row["reported_period_start"] == start and row["period_end"] == end
    assert row["period_contains_capture"] is False and row["period_end_exclusive"] is True
    assert row["source_fetched_at"] == before[1].isoformat()
    assert row["source_reported_at"] == before[2].isoformat()
    assert row["freshness_evaluated"] is False and row["coverage_complete"] is False
    assert row["coverage_start"] is row["coverage_end"] is None
    assert (env.entity.period_being_processed, env.coordinator._last_monthly_fetch_time,
            env.state.last_reported, env.entity.native_value) == before


def test_actual_sensor_rollover_changes_only_the_new_capture_not_the_saved_old_period(monkeypatch):
    old = datetime(2026, 12, 1, tzinfo=UTC)
    at = datetime(2027, 1, 1, 2, 30, tzinfo=UTC)
    env = month_source(monkeypatch, old, at)
    first = capture(env)[env.eid]
    retained = deepcopy(first)
    new = datetime(2027, 1, 1, tzinfo=UTC)
    env.entity.period_being_processed = new
    env.coordinator.consumption_month = new.date()
    env.captured = at+timedelta(hours=2)
    env.coordinator._last_monthly_fetch_time = env.captured-timedelta(seconds=5)
    env.state.last_reported = env.captured-timedelta(seconds=1)
    env.entity.native_value, env.state.state = 0, "0"
    second = capture(env)[env.eid]
    assert second["period_start"] == new.isoformat() and second["period_contains_capture"] is True
    assert second["period_end"] == "2027-02-01T00:00:00+00:00"
    assert second["source_fetched_at"] != first["source_fetched_at"]
    assert first == retained and first["period_start"] == old.isoformat()
    assert second["coverage_complete"] is False and second["freshness_evaluated"] is False


def test_ahead_of_cloud_preserved_native_period_is_metadata_not_new_measurement_coverage(monkeypatch):
    at = datetime(2027, 1, 1, 1, tzinfo=UTC)
    # An earlier integration may already have reset the restored value to
    # January while 1.8.1's coordinator still shows December. SolarPilot
    # records the sensor's actual period, not the coordinator's month or now.
    env = month_source(monkeypatch, datetime(2027, 1, 1, tzinfo=UTC), at)
    env.coordinator.consumption_month = date(2026, 12, 1)
    env.entity.native_value, env.state.state = 0, "0"
    row = capture(env)[env.eid]
    assert row["status"] == "known_period" and row["period_start"] == "2027-01-01T00:00:00+00:00"
    assert row["period_contains_capture"] is True
    assert row["coverage_complete"] is False and row["freshness_evaluated"] is False
    assert row["coverage_start"] is row["coverage_end"] is None


def test_failed_poll_then_recovery_never_advances_original_period_or_fetch_time(monkeypatch):
    at = datetime(2026, 11, 1, 1, tzinfo=UTC)
    env = month_source(monkeypatch, datetime(2026, 10, 1, tzinfo=UTC), at)
    original_fetch, original_report = env.coordinator._last_monthly_fetch_time, env.state.last_reported
    env.coordinator.last_update_success = False
    assert capture(env, at+timedelta(hours=2)) == {}
    assert env.coordinator._last_monthly_fetch_time == original_fetch
    env.coordinator.last_update_success = True
    row = capture(env, at+timedelta(hours=2))[env.eid]
    assert row["period_start"] == "2026-10-01T00:00:00+00:00"
    assert row["source_fetched_at"] == original_fetch.isoformat()
    assert row["source_reported_at"] == original_report.isoformat()
    assert row["source_fetch_age_s"] == 2*3600+120
    assert row["freshness_evaluated"] is False and row["coverage_complete"] is False


def test_explicit_ha_restored_state_never_acquires_period_proof(monkeypatch):
    at = datetime(2026, 11, 1, 1, tzinfo=UTC)
    env = month_source(monkeypatch, datetime(2026, 10, 1, tzinfo=UTC), at)
    env.state.attributes["restored"] = True
    assert capture(env) == {}


@pytest.mark.parametrize("native_start", [None, datetime(2026, 10, 1),
                                        datetime(2026, 10, 1, tzinfo=ZoneInfo("Europe/Brussels"))])
def test_missing_naive_or_local_restored_period_is_not_inferred_from_consumption_month(native_start, monkeypatch):
    at = datetime(2026, 11, 1, 1, tzinfo=UTC)
    env = month_source(monkeypatch, datetime(2026, 10, 1, tzinfo=UTC), at)
    env.entity.period_being_processed = native_start
    row = capture(env)[env.eid]
    assert row["status"] == "unknown" and row["period_start"] is row["period_end"] is None
    assert row["coverage_complete"] is False


@pytest.mark.parametrize("missing", ["fetch", "report", "future_report"])
def test_new_version_label_and_valid_month_cannot_replace_original_source_times(missing):
    at = datetime(2026, 11, 1, 1, tzinfo=UTC)
    values = {"period_start": datetime(2026, 10, 1, tzinfo=UTC),
              "fetched_at": at-timedelta(minutes=2), "reported_at": at-timedelta(seconds=2),
              "captured_at": at}
    if missing == "fetch":
        values["fetched_at"] = None
    elif missing == "report":
        values["reported_at"] = None
    else:
        values["reported_at"] = at+timedelta(seconds=6)
    before = deepcopy((PROVIDER, values))
    result = period_evidence(PROVIDER, "accumulated_energy_consumption", **values)
    assert result["status"] == "unknown" and result["period_start"] is result["period_end"] is None
    assert result["freshness_evaluated"] is False and result["coverage_complete"] is False
    assert (PROVIDER, values) == before
