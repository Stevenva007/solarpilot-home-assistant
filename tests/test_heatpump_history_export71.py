"""Private history exports preserve real local-day evidence and UTC windows."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from custom_components.solar_pilot import analysis_export
from test_heatpump_history_runtime70 import BASE, observe, recorder


@pytest.mark.asyncio
@pytest.mark.parametrize("end,hours,first,last,count,short_day,long_day", [
    ("2026-10-11T10:00:00+02:00", 1, "2026-10-11", "2026-10-11", 1, None, None),
    ("2026-10-11T10:00:00+02:00", 24, "2026-10-10", "2026-10-11", 2, None, None),
    ("2026-10-11T10:00:00+02:00", 168, "2026-10-04", "2026-10-11", 8, None, None),
    ("2026-10-11T00:00:00+02:00", 1, "2026-10-10", "2026-10-10", 1, None, None),
    ("2026-10-11T00:00:00+02:00", 24, "2026-10-10", "2026-10-10", 1, None, None),
    ("2026-10-11T00:00:00+02:00", 168, "2026-10-04", "2026-10-10", 7, None, None),
    ("2026-10-11T01:00:00+02:00", 1, "2026-10-11", "2026-10-11", 1, None, None),
    ("2026-03-30T00:30:00+02:00", 24, "2026-03-28", "2026-03-30", 3, "2026-03-29", None),
    ("2026-03-30T00:30:00+02:00", 168, "2026-03-22", "2026-03-30", 9, "2026-03-29", None),
    ("2026-10-26T00:00:00+01:00", 24, "2026-10-25", "2026-10-25", 1, None, "2026-10-25"),
    ("2026-10-26T00:00:00+01:00", 168, "2026-10-19", "2026-10-25", 7, None, "2026-10-25"),
    ("2026-10-25T02:30:00+02:00", 1, "2026-10-25", "2026-10-25", 1, None, "2026-10-25"),
    ("2026-10-25T02:30:00+01:00", 1, "2026-10-25", "2026-10-25", 1, None, "2026-10-25"),
])
async def test_exact_utc_interval_selects_all_overlapping_local_dates(
        end, hours, first, last, count, short_day, long_day):
    _, _, rec = await recorder()
    when = datetime.fromisoformat(end)
    exported = rec.export(hours, when=when)
    dates = [row["date"] for row in exported["days"]]
    assert len(dates) == exported["exported_days"] == count
    assert dates[0] == first and dates[-1] == last
    assert dates == sorted(set(dates))
    assert exported["retention_days"] == 30 and exported["requested_hours"] == hours
    assert exported["timezone"] == "Europe/Brussels"
    assert exported["aggregate_scope"] == "full_local_calendar_day"
    start = datetime.fromisoformat(exported["window_start"]).timestamp()
    wall = datetime.fromisoformat(exported["window_end"]).timestamp()
    assert wall == when.timestamp() and wall-start == hours*3600
    assert sum(row["window_overlap_s"] for row in exported["days"]) == hours*3600
    boundaries = []
    for row in exported["days"]:
        day_start, day_end = rec.model.lanes._bounds(row["date"])
        assert day_start < wall and day_end > start
        assert row["window_overlap_s"] == min(day_end, wall)-max(day_start, start)
        assert row["window_boundary_partial"] == (start > day_start or wall < day_end)
        assert row["aggregate_scope"] == "full_local_calendar_day"
        if row["window_boundary_partial"]:
            boundaries.append(row["date"])
    assert exported["partial_boundary_dates"] == boundaries
    if short_day:
        assert next(row for row in exported["days"] if row["date"] == short_day)["day_seconds"] == 23*3600
    if long_day:
        assert next(row for row in exported["days"] if row["date"] == long_day)["day_seconds"] == 25*3600


@pytest.mark.asyncio
async def test_first_partial_calendar_day_is_retained_without_prorating_its_energy():
    _, h, rec = await recorder()
    # The first interval precedes the rolling cutoff, but belongs to its first
    # local day. The second falls inside the request; retained day totals cover
    # both real intervals, with an explicit full-day scope rather than a guess.
    for when in (BASE-timedelta(days=7, minutes=30), BASE-timedelta(days=7)+timedelta(minutes=30)):
        observe(rec, when)
        observe(rec, when+timedelta(seconds=20))
    before = deepcopy(rec.model.snapshot())
    exported = rec.export(168, when=BASE)
    early = exported["days"][0]
    assert early["date"] == "2026-10-04" and early["window_boundary_partial"] is True
    assert early["energy_known_s"] == early["on_s"] == 40
    assert early["energy_kwh"] == pytest.approx(.02)
    assert len(early["sessions"]) == 2
    assert early["sessions"][0]["segment_start"] < exported["window_start"]
    assert early["aggregate_scope"] == "full_local_calendar_day"
    after = rec.model.snapshot()
    assert after["energy_days"] == before["energy_days"]
    for field in ("lanes", "tasks"):
        for key, row in before[field]["devices"].items():
            for evidence in ("days", "sessions", "events"):
                assert after[field]["devices"][key][evidence] == row[evidence]
    assert not rec.store.saves and not h.services.calls


@pytest.mark.asyncio
async def test_empty_requested_days_remain_unknown_instead_of_zero_energy():
    _, _, rec = await recorder()
    exported = rec.export(168, when=BASE)
    for row in exported["days"]:
        assert not row["has_data"] and row["on_s"] is None
        assert row["energy_kwh"] is None and row["energy_known_s"] == 0
        assert not row["sessions"] and not row["task_sessions"] and not row["task_totals"]
        assert all(lane["on_s"] is None and lane["known_s"] == 0 for lane in row["sg"].values())


@pytest.mark.asyncio
@pytest.mark.parametrize("hours", [1, 24, 168])
async def test_analysis_export_passes_its_own_frozen_wall_even_near_midnight(monkeypatch, hours):
    r, _, rec = await recorder()
    wall = datetime(2026, 10, 11, 21, 59, 59, 123456, tzinfo=timezone.utc)
    monkeypatch.setattr(analysis_export.time, "time", lambda: wall.timestamp())
    def unexpected_clock():
        raise AssertionError("History must use the analysis wall instead of its own clock")
    rec.now = unexpected_clock
    prepared = r.analysis.prepare(hours=hours)
    exported = prepared["components"]["heatpump_history"]
    assert not prepared["coverage"]["section_errors"]
    assert exported["window_end"] == prepared["created_at"] == wall.isoformat()
    assert exported["requested_hours"] == prepared["requested_hours"] == hours
    assert exported["window_start"] == (wall-timedelta(hours=hours)).isoformat()
    assert exported["days"][-1]["date"] == "2026-10-11"
    assert all(row["generated_at"] == "2026-10-11T21:59:59+00:00" for row in exported["days"])


@pytest.mark.asyncio
@pytest.mark.parametrize("hours", [0, -1, 2, 169, 100000, 24.0, True, "24", None, float("nan")])
async def test_direct_export_hours_are_bounded_to_existing_choices(hours):
    _, _, rec = await recorder()
    with pytest.raises(ValueError):
        rec.export(hours, when=BASE)


@pytest.mark.asyncio
async def test_export_rejects_naive_timestamp():
    _, _, rec = await recorder()
    with pytest.raises(ValueError):
        rec.export(24, when=datetime(2026, 10, 11, 8))
