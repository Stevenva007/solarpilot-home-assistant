"""Water measurements remain separate, bounded and read-only."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace as NS

import pytest

from custom_components.solar_pilot import water
from custom_components.solar_pilot.water import WaterModel, source_reading
from custom_components.solar_pilot.water_runtime import WaterRecorder, water_storage_key
from test_runtime import build

BASE = datetime(2026, 10, 19, 8, tzinfo=timezone.utc)
CONFIG = {"enabled": True, "volume_entity": "sensor.water_total", "flow_entity": "sensor.water_flow",
          "leak_entity": "binary_sensor.water_leak"}


def state(value, when, unit=None, *, role="volume", **attrs):
    metadata = {"device_class": "moisture" if role == "native_leak" else "volume_flow_rate" if role == "flow" else "water"}
    if unit is not None:
        metadata["unit_of_measurement"] = unit
    return NS(state=value, attributes={**metadata, **attrs}, last_reported=when, last_updated=when)


def sample(when, volume=100, flow=0, leak="off"):
    now = when.timestamp()
    return {"volume": source_reading(state(volume, when, "L"), "volume", now, 300),
            "flow": source_reading(state(flow, when, "L/min", role="flow"), "flow", now, 300),
            "native_leak": source_reading(state(leak, when, role="native_leak"), "native_leak", now, 300)}


def observe(model, offset, *, volume=100, flow=0, leak="off", **kwargs):
    when = BASE+timedelta(seconds=offset)
    model.observe(sample(when, volume, flow, leak), when, binding="a"*64, **kwargs)


@pytest.mark.parametrize("role,raw,unit,expected", [("volume", 1.2, "m³", 1200), ("volume", 0, "L", 0),
    ("volume", 1000, "mL", 1), ("flow", .12, "m³/h", 2), ("flow", 1, "L/s", 60),
    ("flow", 120, "L/h", 2), ("flow", 1, "mL/s", .06)])
def test_selected_units_are_explicitly_normalized(role, raw, unit, expected):
    row = source_reading(state(raw, BASE, unit, role=role), role, BASE.timestamp(), 300)
    assert row["fresh"] and row["value"] == pytest.approx(expected)
    assert row["reported_at"] == BASE.timestamp() and row["valid_until"] == BASE.timestamp()+300


@pytest.mark.parametrize("value", [True, False, None, "unknown", "unavailable", "nan", "inf", -1])
def test_invalid_measurement_is_unknown_and_never_zero(value):
    row = source_reading(state(value, BASE, "L/min", role="flow"), "flow", BASE.timestamp(), 300)
    assert row["fresh"] is False and row["value"] is None


def test_counter_deltas_count_once_and_reset_starts_a_new_baseline():
    model = WaterModel(CONFIG)
    observe(model, 0)
    observe(model, 60, volume=102)
    model.observe(sample(BASE+timedelta(seconds=60), 102), BASE+timedelta(seconds=65), binding="a"*64)
    observe(model, 120, volume=1)
    observe(model, 180, volume=4)
    detail = model.detail(when=BASE+timedelta(seconds=180))
    assert detail["volume_l"] == 5 and detail["volume_covered_s"] == 120
    assert [row["volume_l"] for row in detail["intervals"]] == [2, 3]
    assert any(row["kind"] == "counter_reset" for row in detail["events"])
    assert detail["complete"] is False


def test_counter_gap_is_not_backfilled_or_proportioned_over_midnight():
    model = WaterModel(CONFIG, "UTC")
    start = datetime(2026, 10, 18, 23, 59, tzinfo=timezone.utc)
    model.observe(sample(start), start, binding="a"*64)
    after = start+timedelta(seconds=120)
    model.observe(sample(after, 106), after, binding="a"*64)
    detail = model.detail(when=after)
    assert detail["volume_l"] is None
    assert detail["intervals"] == [{"start": start.timestamp(), "end": after.timestamp(), "volume_l": 6,
                                     "day": None, "reason": "cross_local_day"}]
    gap = after+timedelta(seconds=400)
    model.observe(sample(gap, 150), gap, binding="a"*64)
    assert model.detail(when=gap)["volume_l"] is None


def test_flow_duration_needs_advancing_reports_and_getters_cannot_age_it():
    model = WaterModel({**CONFIG, "continuous_flow_minutes": 1})
    for seconds in (0, 15, 30, 45, 60):
        observe(model, seconds, flow=.1)
    current = model.overview(BASE+timedelta(seconds=60))
    assert current["suspicion"]["state"] == "suspected" and current["suspicion"]["elapsed_s"] == 60
    assert current["alert"]["active"] and current["alert"]["cause"] == "continuous_flow"
    before = model.snapshot()
    assert model.overview(BASE+timedelta(seconds=400))["suspicion"]["state"] == "unknown"
    assert model.overview(BASE+timedelta(seconds=400))["alert"]["evidence_current"] is False
    assert model.snapshot() == before


def test_restart_retains_incident_but_restarts_flow_proof_and_counter_baseline():
    model = WaterModel({**CONFIG, "continuous_flow_minutes": 1})
    for seconds in (0, 30, 60):
        observe(model, seconds, volume=100+seconds, flow=1)
    saved = model.snapshot()
    later = BASE+timedelta(minutes=10)
    other = WaterModel({**CONFIG, "continuous_flow_minutes": 1})
    assert other.restore(saved, later)
    assert other.overview(later)["alert"]["episode_id"] == model.alert["episode_id"]
    assert other.overview(later)["alert"]["evidence_current"] is False
    other.observe(sample(later, 1000, flow=1), later, binding="a"*64)
    assert other.overview(later)["suspicion"]["elapsed_s"] == 0
    assert other.overview(later)["today"]["volume_l"] == 60


@pytest.mark.parametrize("offset", [-10, 0])
def test_old_or_in_place_changed_leak_off_never_clears_an_active_episode(offset):
    model = WaterModel({"enabled": True, "leak_entity": "binary_sensor.water_leak"})
    observe(model, 0, leak="on")
    episode = model.alert["episode_id"]
    bad = sample(BASE+timedelta(seconds=offset), leak="off")
    model.observe(bad, BASE+timedelta(seconds=5), binding="a"*64)
    current = model.overview(BASE+timedelta(seconds=5))
    assert current["alert"]["active"] and current["alert"]["episode_id"] == episode
    assert current["alert"]["evidence_current"] is False
    assert current["native_leak"]["fresh"] is False and current["native_leak"]["value"] is None
    observe(model, 10, leak="off")
    assert model.alert["active"] is False and model.alert["episode_id"] == episode
    assert model.alert["last_evidence_at"] == BASE.timestamp()+10


def test_retained_resolved_episode_cannot_rearm_from_an_older_on_report():
    config = {"enabled": True, "leak_entity": "binary_sensor.water_leak"}
    model = WaterModel(config)
    observe(model, 0, leak="on")
    observe(model, 10, leak="off")
    episode = model.alert["episode_id"]
    restored = WaterModel(config)
    assert restored.restore(model.snapshot(), BASE+timedelta(seconds=20))
    restored.observe(sample(BASE+timedelta(seconds=5), leak="on"), BASE+timedelta(seconds=20), binding="a"*64)
    assert restored.alert["active"] is False and restored.alert["episode_id"] == episode
    assert restored.overview(BASE+timedelta(seconds=20))["native_leak"]["fresh"] is False
    observe(restored, 30, leak="on")
    assert restored.alert["active"] and restored.alert["episode_id"] != episode


def test_captured_context_is_fresh_bounded_and_never_attributes_shared_liters():
    model = WaterModel(CONFIG)
    stamp = BASE.timestamp()
    context = {"boiler": {"temperature": {"value": 52, "reported_at": stamp-20, "valid_until": stamp+100},
                           "target": {"value": 60, "reported_at": stamp-200, "valid_until": stamp-80}},
               "dishwasher": {"value": True, "reported_at": stamp-10, "valid_until": stamp+110}}
    observe(model, 0, context=context, context_binding="b"*64)
    point = model.detail(when=BASE)["points"][0]
    assert point["context_binding"] == "b"*64
    assert point["context"]["boiler"]["temperature"]["value"] == 52
    assert point["context"]["boiler"]["target"]["value"] is None
    assert point["context"]["dishwasher"]["value"] is True
    assert "volume_l" not in point["context"]["boiler"] and "volume_l" not in point["context"]["dishwasher"]


def test_restart_boundary_prevents_new_boiler_correlation_across_the_gap():
    model = WaterModel(CONFIG)
    def context(offset, value):
        stamp = BASE.timestamp()+offset
        return {"boiler": {"temperature": {"value": value, "reported_at": stamp, "valid_until": stamp+120}}}
    observe(model, 0, context=context(0, 52), context_binding="b"*64)
    observe(model, 60, volume=102, context=context(60, 48), context_binding="b"*64)
    restored = WaterModel(CONFIG)
    assert restored.restore(model.snapshot(), BASE+timedelta(seconds=70))
    observe(restored, 130, volume=110, context=context(130, 45), context_binding="b"*64)
    detail = restored.detail(when=BASE+timedelta(seconds=130))
    assert len(detail["correlations"]["boiler_drops"]) == 1
    assert detail["correlations"]["boiler_drops"][0]["end"] == BASE.timestamp()+60


@pytest.mark.parametrize("day,seconds", [("2026-03-29", 23*3600), ("2026-10-25", 25*3600)])
def test_local_day_bounds_follow_dst(day, seconds):
    model = WaterModel(CONFIG)
    when = datetime.fromisoformat(day+"T12:00:00+00:00")
    detail = model.detail(day, when=when)
    assert detail["day_end"]-detail["day_start"] == seconds


def test_point_event_and_interval_memory_caps_are_explicit(monkeypatch):
    monkeypatch.setattr(water, "MAX_POINTS", 3)
    monkeypatch.setattr(water, "MAX_INTERVALS", 3)
    monkeypatch.setattr(water, "MAX_EVENTS", 3)
    model = WaterModel(CONFIG)
    for seconds in range(0, 600, 60):
        observe(model, seconds, volume=seconds, flow=seconds % 120)
    assert len(model.points) == len(model.intervals) == len(model.events) == 3
    assert all(model.dropped[key] > 0 for key in model.dropped)


@pytest.mark.asyncio
async def test_separate_water_store_preserves_sources_and_never_changes_controls():
    runtime, hass = build()
    recorder = WaterRecorder(hass, runtime.entry, CONFIG)
    recorder.now = lambda: BASE
    await recorder.start()
    before = deepcopy((runtime.entry.options, runtime._snapshot(), hass.services.calls))
    for seconds, volume in ((0, 100), (60, 105)):
        when = BASE+timedelta(seconds=seconds)
        hass.states.data["sensor.water_total"] = state(volume, when, "L")
        hass.states.data["sensor.water_flow"] = state(0, when, "L/min", role="flow")
        hass.states.data["binary_sensor.water_leak"] = state("off", when, role="native_leak")
        recorder.observe(when, context_sources={"sensor.original_boiler"})
    assert recorder.model.overview(BASE+timedelta(seconds=60))["today"]["volume_l"] == 5
    await recorder.close()
    assert water_storage_key(runtime.entry.entry_id) == "solar_pilot.test.water_history"
    assert "sensor.original_boiler" in recorder.store.data["access_sources"]
    assert (runtime.entry.options, runtime._snapshot(), hass.services.calls) == before
    other = WaterRecorder(hass, runtime.entry, CONFIG)
    other.now = lambda: BASE+timedelta(minutes=20)
    other.store.data = deepcopy(recorder.store.data)
    await other.start()
    assert not other.error and other.model.overview(other.now())["today"]["volume_l"] == 5
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("data", [{"version": 99}, {"version": 1, "history": {"schema": 99},
    "access_sources": [], "access_sources_complete": True}, ["unreadable"]])
async def test_unsupported_store_is_never_overwritten(data):
    runtime, hass = build()
    recorder = WaterRecorder(hass, runtime.entry, CONFIG)
    recorder.now = lambda: BASE
    recorder.store.data = deepcopy(data)
    await recorder.start()
    recorder.observe(BASE)
    await recorder.close()
    assert recorder.error and recorder.loaded and not recorder._writable
    assert recorder.store.data == data and not recorder.store.saves and not hass.services.calls


@pytest.mark.asyncio
async def test_cleanup_failure_does_not_prevent_other_water_cleanup_or_flush():
    runtime, hass = build()
    recorder = WaterRecorder(hass, runtime.entry, CONFIG)
    recorder.now = lambda: BASE
    await recorder.start()
    recorder.store._async_cleanup_delay_listener = lambda: (_ for _ in ()).throw(RuntimeError("synthetic cleanup failure"))
    calls = []
    recorder.store._async_cleanup_final_write_listener = lambda: calls.append("final")
    await recorder.close()
    assert calls == ["final"] and len(recorder.store.saves) == 1 and not hass.services.calls
