"""Rolling boiler comparisons use actual source roles and disjoint windows."""
from copy import deepcopy
from datetime import timedelta

import pytest

from custom_components.solar_pilot.water import WaterModel
from custom_components.solar_pilot.water_correlations import correlate_water_history
from test_water101 import BASE, CONFIG, sample

AT = BASE.timestamp()
BINDING = "b"*64


def context(offset, temperature):
    stamp = AT+offset
    return {"boiler": {"temperature": {"value": temperature, "reported_at": stamp, "valid_until": stamp+120}}}


def point(offset, temperature, *, reported=None, binding=BINDING):
    row = {"captured_at": AT+offset, "context_binding": binding, "context": context(offset, temperature)}
    if reported is not None:
        row["context"]["boiler"]["temperature"].update(reported_at=AT+reported, valid_until=AT+reported+120)
    return row


def interval(start, end, volume=1):
    return {"start": AT+start, "end": AT+end, "volume_l": volume, "reason": "counter_delta"}


def drops(points, *, intervals=(), events=()):
    return correlate_water_history({"points": points, "intervals": list(intervals), "events": list(events)})["boiler_drops"]


def test_one_degree_steps_form_disjoint_two_degree_windows_without_double_counting():
    rows = [point(index*60, value) for index, value in enumerate((55, 54, 53, 52, 51))]
    output = drops(rows, intervals=[interval(index*60, (index+1)*60) for index in range(4)])
    assert [(row["start"]-AT, row["end"]-AT, row["drop_c"], row["observed_volume_l"]) for row in output] == [
        (0, 120, 2, 2), (120, 240, 2, 2)]
    assert sum(row["observed_volume_l"] for row in output) == 4
    assert all(row["volume_partial"] is True for row in output)
    assert not any("boiler_l" in row or "dishwasher_l" in row for row in output)


def test_highest_reference_and_earliest_equal_peak_are_deterministic():
    output = drops([point(0, 55), point(60, 56), point(120, 56), point(180, 55), point(240, 54)])
    assert len(output) == 1 and output[0]["start"] == AT+60 and output[0]["end"] == AT+240
    assert output[0]["temperature_start_c"] == 56 and output[0]["drop_c"] == 2


@pytest.mark.parametrize("end,expected", [(1800, 1), (1800.001, 0)])
def test_thirty_minute_window_has_an_exact_inclusive_boundary(end, expected):
    assert len(drops([point(0, 55), point(900, 54), point(end, 53)])) == expected


def test_duplicate_original_report_does_not_advance_or_repeat_a_drop():
    output = drops([point(0, 55), point(30, 55, reported=0), point(60, 54),
                    point(90, 54, reported=60), point(120, 53), point(150, 53, reported=120)],
                   intervals=[interval(0, 60), interval(60, 120)])
    assert len(output) == 1 and output[0]["start"] == AT and output[0]["end"] == AT+120
    assert output[0]["observed_volume_l"] == 2


def test_same_report_mutation_and_repair_cannot_reuse_the_old_reference():
    output = drops([point(0, 55), point(30, 54, reported=0), point(60, 55, reported=0),
                    point(120, 53), point(180, 51)], intervals=[interval(0, 120, 100), interval(120, 180, 2)])
    assert len(output) == 1 and output[0]["start"] == AT+120 and output[0]["end"] == AT+180
    assert output[0]["observed_volume_l"] == 2


@pytest.mark.parametrize("role,expected", [("flow", 1), ("volume", 0), ("boiler_temperature", 0), (None, 0)])
def test_only_explicit_flow_gap_leaves_temperature_and_counter_evidence_intact(role, expected):
    event = {"kind": "source_gap", "at": AT+30}
    if role is not None:
        event["source_role"] = role
    output = drops([point(0, 55), point(60, 54), point(120, 53)],
                   intervals=[interval(0, 60), interval(60, 120)], events=[event])
    assert len(output) == expected
    if output:
        assert output[0]["observed_volume_l"] == 2 and output[0]["flow_observed"] is False


def test_gap_known_at_capture_blocks_a_report_that_predates_the_gap():
    output = drops([point(0, 55), point(120, 53, reported=60)],
                   events=[{"kind": "source_gap", "source_role": "boiler_temperature", "at": AT+90}])
    assert output == []


def test_missing_temperature_between_reports_does_not_bridge_the_window():
    missing = point(60, None)
    output = drops([point(0, 55), missing, point(120, 53), point(180, 51)])
    assert len(output) == 1 and output[0]["start"] == AT+120 and output[0]["end"] == AT+180


def model_observe(model, seconds, temperature, *, binding=BINDING, flow=0, volume=100):
    when = BASE+timedelta(seconds=seconds)
    rows = sample(when, volume=volume, flow=flow)
    if flow is None:
        rows["flow"].update(value=None, fresh=False, reason="stale")
    model.observe(rows, when, binding="a"*64, context=context(seconds, temperature), context_binding=binding)


def test_missing_then_recovered_context_is_retained_before_the_heartbeat():
    model = WaterModel(CONFIG)
    model_observe(model, 0, 55)
    model_observe(model, 5, None)
    model_observe(model, 10, 53)
    assert [row["captured_at"]-AT for row in model.points] == [0, 5, 10]
    assert {"kind": "source_gap", "at": AT+5, "source_role": "boiler_temperature"} in model.events
    assert model.detail(when=BASE+timedelta(seconds=10))["correlations"]["boiler_drops"] == []
    # A changed temperature alone does not create a five-second time series.
    for seconds in range(15, 305, 5):
        model_observe(model, seconds, 51)
    assert len(model.points) == 3
    model_observe(model, 310, 51)
    output = model.detail(when=BASE+timedelta(seconds=310))["correlations"]["boiler_drops"]
    assert len(output) == 1 and output[0]["start"] == AT+10 and output[0]["end"] == AT+310


def test_context_binding_roundtrip_between_heartbeats_cannot_hide_the_break():
    model = WaterModel(CONFIG)
    model_observe(model, 0, 55)
    model_observe(model, 5, 54, binding="c"*64)
    model_observe(model, 10, 53)
    assert [row["context_binding"] for row in model.points] == [BINDING, "c"*64, BINDING]
    assert len([event for event in model.events if event.get("source_role") == "boiler_temperature"]) == 2
    assert model.detail(when=BASE+timedelta(seconds=10))["correlations"]["boiler_drops"] == []


def test_discrete_inactive_dishwasher_context_is_not_lost_between_heartbeats():
    model = WaterModel(CONFIG)
    for seconds, active in ((0, True), (5, False), (10, True)):
        when = BASE+timedelta(seconds=seconds)
        recorded = context(seconds, 55)
        recorded["dishwasher"] = {"value": active, "reported_at": AT+seconds, "valid_until": AT+seconds+120}
        model.observe(sample(when), when, binding="a"*64, context=recorded, context_binding=BINDING)
    assert [row["context"]["dishwasher"]["value"] for row in model.points] == [True, False, True]
    assert model.detail(when=BASE+timedelta(seconds=10))["correlations"]["dishwasher_intervals"] == []


def test_model_flow_gap_is_scoped_without_losing_current_counter_intervals():
    model = WaterModel(CONFIG)
    model_observe(model, 0, 55, volume=100)
    model_observe(model, 5, 54, flow=None, volume=101)
    model_observe(model, 10, 53, volume=102)
    assert {"kind": "source_gap", "at": AT+5, "source_role": "flow"} in model.events
    output = model.detail(when=BASE+timedelta(seconds=10))["correlations"]["boiler_drops"]
    assert len(output) == 1 and output[0]["observed_volume_l"] == 2


@pytest.mark.parametrize("role", ["flow", "volume", "boiler_temperature"])
def test_new_scoped_gap_roundtrips_in_store_schema_one(role):
    model = WaterModel(CONFIG)
    model.events = [{"kind": "source_gap", "at": AT, "source_role": role}]
    saved = model.snapshot()
    restored = WaterModel(CONFIG)
    assert saved["schema"] == 1 and restored.restore(saved, BASE+timedelta(seconds=10))
    assert restored.events == model.events


def test_legacy_generic_gap_is_preserved_without_invented_source_provenance():
    model = WaterModel(CONFIG)
    model.events = [{"kind": "source_gap", "at": AT}]
    saved = model.snapshot()
    restored = WaterModel(CONFIG)
    assert restored.restore(saved, BASE+timedelta(seconds=10))
    assert restored.events == saved["events"] and "source_role" not in restored.events[0]


def test_role_field_on_an_unrelated_event_is_rejected_atomically():
    model = WaterModel(CONFIG)
    model_observe(model, 0, 55)
    before = model.snapshot()
    damaged = deepcopy(before)
    damaged["events"].append({"kind": "counter_reset", "at": AT, "source_role": "volume"})
    assert model.restore(damaged, BASE+timedelta(seconds=10)) is False
    assert model.snapshot() == before
