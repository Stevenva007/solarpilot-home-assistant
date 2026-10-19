"""Independent adversarial water evidence tests; no real HA or device access."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace as NS
import asyncio
import json
import math

import pytest

from custom_components.solar_pilot.water import WaterModel, source_reading
from custom_components.solar_pilot.water_notifications import WaterNotifications
from custom_components.solar_pilot.water_runtime import WaterRecorder
from custom_components.solar_pilot.water_correlations import correlate_water_history
from custom_components.solar_pilot.water_context import capture_water_context
from test_water_ui101 import run_water, water_day
from test_audit_ui79 import execute


BASE = datetime(2026, 10, 19, 10, tzinfo=timezone.utc).timestamp()
MISSING = object()
CONFIG = dict(enabled=True, volume_entity="sensor.fictional_total", flow_entity="sensor.fictional_flow",
              leak_entity="binary_sensor.fictional_leak", source_stale_s=300,
              continuous_flow_l_min=.1, continuous_flow_minutes=60, notifications=True)


def model(**changes):
    return WaterModel({**CONFIG, **changes})


def state(value, role, reported, *, unit=None, **attributes):
    attrs = {"device_class": "moisture"} if role == "native_leak" else {
        "unit_of_measurement": unit or ("L/min" if role == "flow" else "L")}
    attrs.update(attributes)
    return NS(state=value, attributes=attrs,
              last_reported=datetime.fromtimestamp(reported, timezone.utc),
              last_updated=datetime.fromtimestamp(reported, timezone.utc),
              last_changed=datetime.fromtimestamp(BASE-86400, timezone.utc))


def readings(m, now, *, volume=MISSING, flow=MISSING, leak=MISSING, report=None):
    values = dict(volume=volume, flow=flow, native_leak=leak)
    result = {}
    for role, key in (("volume", "volume_entity"), ("flow", "flow_entity"), ("native_leak", "leak_entity")):
        value = values[role]
        reported = report.get(role, now) if isinstance(report, dict) else now if report is None else report
        obj = None if value is MISSING else state(value, role, reported)
        result[role] = source_reading(obj, role, now, m.settings["source_stale_s"], configured=bool(m.settings[key]))
    return result


def observe(m, now, *, binding="1"*64, context=None, **values):
    rows = readings(m, now, **values)
    m.observe(rows, now, binding=binding, context=context)
    return m.overview(now)


def sustained(m, start=BASE, seconds=3600, *, step=10, value=.1):
    for offset in range(0, seconds+1, step):
        result = observe(m, start+offset, flow=value, leak="off")
    return result


@pytest.mark.parametrize("role", ["volume", "flow"])
@pytest.mark.parametrize("value", [False, True, None, "", "unknown", "unavailable", "NaN", "Infinity", [], {}])
def test_invalid_numeric_source_never_becomes_measured_zero(role, value):
    row = source_reading(state(value, role, BASE), role, BASE, 300)
    assert row["value"] is None and row["fresh"] is False


def test_fresh_same_state_zero_uses_report_time_without_rewriting_physical_time():
    obj = state("0", "flow", BASE)
    before = deepcopy(vars(obj))
    row = source_reading(obj, "flow", BASE, 300)
    assert row["fresh"] and row["value"] == 0 and row["reported_at"] == BASE
    assert vars(obj) == before
    obj.last_reported = datetime.fromtimestamp(BASE+10, timezone.utc)
    repeated = source_reading(obj, "flow", BASE+10, 300)
    assert repeated["fresh"] and repeated["value"] == 0 and repeated["reported_at"] == BASE+10
    assert obj.last_changed.timestamp() == BASE-86400
    m = model();m.observe({**readings(m, BASE+10), "flow": repeated}, BASE+10)
    assert "rapporttijd is geen bewezen fysiek meettijdstip" in m.overview(BASE+10)["note"]


@pytest.mark.parametrize("role,value", [("flow", "0"), ("volume", "1000"), ("native_leak", "off")])
def test_replayed_receipt_cannot_hide_original_stale_report(role, value):
    obj = state(value, role, BASE-301)
    obj.last_updated = datetime.fromtimestamp(BASE, timezone.utc)
    row = source_reading(obj, role, BASE, 300)
    assert row["fresh"] is False and row["value"] is None
    assert row["reported_at"] == BASE-301 and row["reason"] == "stale"


@pytest.mark.parametrize("flag", ["restored", "estimated", "is_estimated"])
def test_explicit_restored_or_estimated_source_does_not_start_flow_proof(flag):
    row = source_reading(state("10", "flow", BASE, **{flag: True}), "flow", BASE, 300)
    assert row["fresh"] is False and row["value"] is None


@pytest.mark.parametrize("raw", [False, True, "false", "true", "0", "1", "dry", "wet", "unknown", "unavailable"])
def test_native_leak_requires_on_off_contract_not_truthiness(raw):
    row = source_reading(state(raw, "native_leak", BASE), "native_leak", BASE, 300)
    assert row["fresh"] is False and row["value"] is None
    off = source_reading(state("off", "native_leak", BASE), "native_leak", BASE, 300)
    assert off["fresh"] is True and off["value"] is False


def test_one_held_initial_report_cannot_establish_sixty_minutes_of_flow():
    m = model(source_stale_s=86400)
    for elapsed in range(0, 7201, 10):
        result = observe(m, BASE+elapsed, flow="1", report=BASE)
    assert result["flow"]["fresh"] is True
    assert result["suspicion"]["elapsed_s"] == 0
    assert result["suspicion"]["state"] != "suspected" and result["alert"]["active"] is False


def test_retained_initial_frame_does_not_backdate_new_flow_proof():
    m = model()
    first = observe(m, BASE, flow="1", report=BASE-20)
    assert first["suspicion"]["state"] == "unknown"
    for elapsed in range(10, 3601, 10):
        result = observe(m, BASE+elapsed, flow=".1", leak="off")
    assert result["suspicion"]["elapsed_s"] == 3590 and not result["alert"]["active"]
    final = observe(m, BASE+3610, flow=".1", leak="off")
    assert final["suspicion"]["elapsed_s"] == 3600 and final["alert"]["active"]
    assert final["alert"]["cause"] == "continuous_flow"


def test_threshold_and_sixty_minute_boundary_require_sustained_new_explicit_flow():
    m = model()
    result = sustained(m, seconds=3590)
    assert result["suspicion"]["state"] == "pending" and not result["alert"]["active"]
    result = observe(m, BASE+3600, flow=".1", leak="off")
    assert result["suspicion"]["state"] == "suspected" and result["alert"]["active"]
    low = model();result = sustained(low, value=.0999)
    assert result["suspicion"]["state"] == "clear" and not result["alert"]["active"]


@pytest.mark.parametrize("interruption", ["missing", "unknown", "unavailable", "false", "stale", "future"])
def test_missing_invalid_or_outdated_flow_breaks_the_sixty_minute_candidate(interruption):
    m = model();sustained(m, seconds=3000)
    value = MISSING if interruption == "missing" else False if interruption == "false" else ".1" if interruption in ("stale", "future") else interruption
    stamp = BASE+3010-301 if interruption == "stale" else BASE+3020 if interruption == "future" else BASE+3010
    interrupted = observe(m, BASE+3010, flow=value, report={"flow": stamp}, leak="off")
    assert interrupted["suspicion"]["state"] == "unknown"
    for elapsed in range(3020, 3611, 10):
        result = observe(m, BASE+elapsed, flow=".1", leak="off")
    assert result["suspicion"]["elapsed_s"] == 590 and not result["alert"]["active"]


def test_source_report_gap_over_three_hundred_seconds_restarts_proof_without_bridging():
    m = model();sustained(m, seconds=3000)
    result = observe(m, BASE+3301, flow=".1", leak="off")
    assert result["suspicion"]["elapsed_s"] == 0 and not result["alert"]["active"]
    result = observe(m, BASE+3600, flow=".1", leak="off")
    assert result["suspicion"]["elapsed_s"] == 299 and not result["alert"]["active"]


def test_quantized_counter_pulses_never_prove_continuous_flow_or_appliance_consumption():
    m = model(flow_entity="", leak_entity="")
    for elapsed in range(0, 7201, 120):
        result = observe(m, BASE+elapsed, volume=str(1000+elapsed//120))
    assert result["today"]["volume_l"] == 60
    assert result["suspicion"]["state"] == "unknown" and not result["alert"]["active"]
    detail = m.detail(when=BASE+7200)
    assert all("flow" not in interval and "dishwasher_l" not in interval and "dhw_l" not in interval for interval in detail["intervals"])


def test_counter_gap_reset_and_rebind_do_not_create_large_or_negative_consumption():
    m = model(flow_entity="", leak_entity="")
    observe(m, BASE, volume="1000");observe(m, BASE+10, volume="1001")
    observe(m, BASE+1000, volume="1500")
    observe(m, BASE+1010, volume="1")
    observe(m, BASE+1020, volume="2")
    observe(m, BASE+1030, volume="90000", binding="2"*64)
    result = observe(m, BASE+1040, volume="90001", binding="2"*64)
    assert result["today"]["volume_l"] == 3
    assert [row["volume_l"] for row in m.intervals if row["day"] is not None] == [1, 1, 1]
    gap = next(row for row in m.intervals if row["reason"] == "counter_gap")
    assert gap["day"] is None and gap["volume_l"] == 499
    assert {row["kind"] for row in m.events} >= {"counter_gap", "counter_reset", "binding_changed"}


def test_out_of_order_or_mutated_same_report_cannot_add_volume_or_shortcut_flow():
    m = model();sustained(m, seconds=3000)
    observe(m, BASE+3010, volume="100", flow=".1", leak="off")
    before = deepcopy(m.intervals)
    result = observe(m, BASE+3020, volume="100000", flow="500", leak="off", report={"volume": BASE+3010, "flow": BASE+3010})
    assert m.intervals == before and result["suspicion"]["state"] == "unknown"
    result = observe(m, BASE+3030, volume="100001", flow=".1", leak="off")
    assert result["suspicion"]["elapsed_s"] == 0 and not result["alert"]["active"]


def test_restart_does_not_restore_partial_flow_proof_or_first_frame_freshness():
    m = model();sustained(m, seconds=3000)
    restarted = model();assert restarted.restore(m.snapshot(), BASE+3010)
    assert restarted.overview(BASE+3010)["flow"]["fresh"] is False
    for elapsed in range(3020, 3611, 10):
        result = observe(restarted, BASE+elapsed, flow=".1", leak="off")
    assert result["suspicion"]["elapsed_s"] == 590 and not result["alert"]["active"]


def test_unresolved_episode_survives_restart_without_repeated_advisory_start():
    m = model();first = sustained(m)
    episode = first["alert"]["episode_id"]
    restarted = model();assert restarted.restore(m.snapshot(), BASE+3610)
    result = sustained(restarted, start=BASE+3620)
    assert result["alert"]["active"] and result["alert"]["episode_id"] == episode
    assert len([e for e in restarted.events if e["kind"] == "advisory_started"]) == 1
    clear = observe(restarted, BASE+7230, flow="0", leak="off")
    assert clear["suspicion"]["state"] == "clear" and not clear["alert"]["active"]
    new = sustained(restarted, start=BASE+7240)
    assert new["alert"]["episode_id"] != episode


def test_invalid_native_false_does_not_clear_but_fresh_explicit_off_does():
    m = model(flow_entity="", volume_entity="")
    initial = observe(m, BASE, leak="on")
    assert initial["alert"]["active"]
    invalid = observe(m, BASE+10, leak=False)
    assert invalid["native_leak"]["value"] is None and invalid["alert"]["active"]
    assert invalid["alert"]["evidence_current"] is False
    clear = observe(m, BASE+20, leak="off")
    assert clear["native_leak"]["fresh"] and clear["native_leak"]["value"] is False
    assert clear["alert"]["active"] is False


def test_fresh_native_off_does_not_keep_expired_continuous_flow_evidence_current():
    m = model();sustained(m)
    # Both reports are current now, but the flow expires one second later.
    result = observe(m, BASE+3899, flow=".1", leak="off", report={"flow": BASE+3600})
    assert result["alert"]["active"] and result["alert"]["evidence_current"]
    later = m.overview(BASE+3901)
    assert later["native_leak"]["fresh"] and not later["flow"]["fresh"]
    assert later["alert"]["active"] and later["alert"]["evidence_current"] is False


@pytest.mark.parametrize("role", ["volume", "flow"])
@pytest.mark.parametrize("field,value", [("reported_at", None), ("reported_at", BASE+6), ("valid_until", None), ("valid_until", BASE-1)])
def test_restore_rejects_fresh_numeric_points_without_valid_original_report_window(role, field, value):
    original = model();observe(original, BASE, volume="100", flow=".1", leak="off")
    snapshot = original.snapshot();snapshot["points"][0][role][field] = value
    restored = model()
    assert restored.restore(snapshot, BASE+10) is False


@pytest.mark.parametrize("field,value", [("revision", "bad"), ("revision", float("nan")), ("dropped", {"points": "bad"}), ("dropped", {"events": float("inf")})])
def test_rejected_restore_does_not_partially_publish_different_history(field, value):
    valid = model();observe(valid, BASE, volume="100", flow="0", leak="off")
    other = model();observe(other, BASE+60, volume="200", flow="0", leak="off")
    corrupt = other.snapshot();corrupt[field] = value
    before = valid.snapshot()
    assert valid.restore(corrupt, BASE+70) is False
    assert valid.snapshot() == before


@pytest.mark.parametrize("day,start,end,seconds", [
    ("2026-03-29", "2026-03-28T23:00:00+00:00", "2026-03-29T22:00:00+00:00", 82800),
    ("2026-10-25", "2026-10-24T22:00:00+00:00", "2026-10-25T23:00:00+00:00", 90000),
])
def test_water_history_uses_actual_local_dst_bounds_without_normalizing_day_to_24h(day, start, end, seconds):
    left = datetime.fromisoformat(start).timestamp();right = datetime.fromisoformat(end).timestamp()
    m = model(flow_entity="", leak_entity="")
    observe(m, left, volume="100");observe(m, left+60, volume="101")
    detail = m.detail(day, when=right-1)
    assert detail["day_start"] == left and detail["day_end"] == right
    assert detail["day_end"]-detail["day_start"] == seconds and detail["volume_l"] == 1
    assert detail["complete"] is False


def test_changed_source_cannot_clear_old_incident_but_new_positive_evidence_gets_new_episode():
    m = model(volume_entity="", flow_entity="")
    first = observe(m, BASE, leak="on", binding="1"*64)
    old_id = first["alert"]["episode_id"]
    changed = observe(m, BASE+10, leak="off", binding="2"*64)
    assert changed["alert"]["active"] and changed["alert"]["episode_id"] == old_id
    assert changed["alert"]["evidence_current"] is False
    assert not any(event["kind"] == "advisory_resolved" for event in m.events)
    positive = observe(m, BASE+20, leak="on", binding="2"*64)
    assert positive["alert"]["active"] and positive["alert"]["evidence_current"]
    assert positive["alert"]["episode_id"] != old_id


@pytest.mark.parametrize("field,value", [("state", "invented"), ("elapsed_s", float("nan")),
    ("elapsed_s", True), ("required_s", False), ("threshold_l_min", float("inf"))])
def test_restore_rejects_malformed_historical_suspicion_without_promoting_it(field, value):
    m = model();observe(m, BASE, flow=".1", leak="off")
    saved = m.snapshot();saved["points"][0]["suspicion"][field] = value
    other = model()
    assert other.restore(saved, BASE+10) is False
    assert other.overview(BASE+10)["suspicion"]["state"] == "unknown"
    assert other.points == []


def notification_runtime(settings=None):
    calls, saves = [], []

    class Services:
        fail = False

        def has_service(self, domain, service):
            assert domain == "persistent_notification" and service in ("create", "dismiss")
            return True

        async def async_call(self, domain, service, data, **kwargs):
            assert domain == "persistent_notification" and service in ("create", "dismiss")
            calls.append((domain, service, deepcopy(data)))
            if self.fail:
                raise RuntimeError("Fictional notification transport failure")

    runtime = NS(entry=NS(entry_id="fictional"), _closed=False, hass=NS(services=Services()),
                 water=NS(settings=settings or CONFIG))
    notifier = WaterNotifications(runtime)
    runtime._snapshot = lambda: {"water_notifications": notifier.snapshot()}
    runtime.store = NS(async_delay_save=lambda callback, _delay: saves.append(callback()))
    return runtime, notifier, calls, saves


@pytest.mark.asyncio
async def test_regular_use_and_unknown_native_leak_never_notify():
    _, notifier, calls, _ = notification_runtime()
    m = model()
    for offset in range(0, 7201, 60):
        view = observe(m, BASE+offset, volume=str(1000+offset//60), flow=".05", leak="unknown")
        await notifier.sync(view)
    assert calls == []


@pytest.mark.asyncio
async def test_water_notification_deduplicates_concurrent_ticks_and_persisted_restart():
    _, notifier, calls, saves = notification_runtime()
    m = model();view = sustained(m)
    await asyncio.gather(*(notifier.sync(deepcopy(view)) for _ in range(12)))
    assert len(calls) == 1 and calls[0][1] == "create" and len(saves) == 1
    message = calls[0][2]["message"]
    assert "geen fysiek lek vastgesteld" in message and "sluit geen waterkraan" in message
    _, restarted, restart_calls, _ = notification_runtime()
    restarted.restore(saves[-1]["water_notifications"])
    await restarted.sync(view)
    assert restart_calls == []


@pytest.mark.asyncio
async def test_unknown_cannot_dismiss_native_water_notice_but_fresh_off_can():
    _, notifier, calls, _ = notification_runtime()
    m = model(volume_entity="", flow_entity="")
    await notifier.sync(observe(m, BASE, leak="on"))
    await notifier.sync(observe(m, BASE+10, leak="unknown"))
    await notifier.sync(observe(m, BASE+20, leak=False))
    assert [row[1] for row in calls] == ["create"]
    await notifier.sync(observe(m, BASE+30, leak="off"))
    assert [row[1] for row in calls] == ["create", "dismiss"]
    assert calls[0][2]["notification_id"] == calls[1][2]["notification_id"]


@pytest.mark.asyncio
async def test_notification_transport_failure_isolated_and_retries_same_episode_once():
    runtime, notifier, calls, saves = notification_runtime()
    m = model(volume_entity="", flow_entity="")
    view = observe(m, BASE, leak="on");before = m.snapshot()
    runtime.hass.services.fail = True
    await notifier.sync(view)
    assert notifier.snapshot()["delivered_episodes"] == [] and saves == []
    assert m.snapshot() == before
    runtime.hass.services.fail = False
    await notifier.sync(view);await notifier.sync(view)
    assert [row[1] for row in calls] == ["create", "create"]
    assert len(notifier.snapshot()["delivered_episodes"]) == 1
    assert len(saves) == 1 and m.snapshot() == before


@pytest.mark.parametrize("change", [{"active": "true"}, {"evidence_current": 1},
    {"cause": "ordinary_use"}, {"episode_id": "untrusted"}, {"evidence_current": False}])
@pytest.mark.asyncio
async def test_malformed_or_unproven_alert_cannot_deliver_a_notice(change):
    _, notifier, calls, _ = notification_runtime()
    alert = dict(active=True, evidence_current=True, cause="continuous_flow", episode_id="a"*24)
    alert.update(change)
    await notifier.sync({"alert": alert})
    assert calls == []


@pytest.mark.asyncio
async def test_recorder_rebind_preserves_private_old_sources_and_never_sends_device_commands(monkeypatch):
    from homeassistant.helpers import entity_registry as registry_module

    source_rows = {CONFIG["volume_entity"]: NS(config_entry_id="fictional-meter", device_id="meter-1", unique_id="total-1")}
    monkeypatch.setattr(registry_module, "async_get", lambda _h: NS(async_get=lambda entity: source_rows.get(entity)))
    states, calls = {}, []
    hass = NS(states=NS(get=states.get), config=NS(time_zone="Europe/Brussels"),
              services=NS(async_call=lambda *args, **kwargs: calls.append((args, kwargs))))
    cfg = {**CONFIG, "flow_entity": "", "leak_entity": ""}
    recorder = WaterRecorder(hass, NS(entry_id="fictional"), cfg)
    recorder.now = lambda: datetime.fromtimestamp(BASE, timezone.utc)
    await recorder.start()
    for elapsed, total in ((0, "100"), (60, "101")):
        states[CONFIG["volume_entity"]] = state(total, "volume", BASE+elapsed)
        recorder.observe(BASE+elapsed, context_sources={"sensor.fictional_old_boiler"})
    source_rows[CONFIG["volume_entity"]] = NS(config_entry_id="fictional-meter", device_id="meter-2", unique_id="total-2")
    states[CONFIG["volume_entity"]] = state("90000", "volume", BASE+120)
    recorder.observe(BASE+120, context_sources={"sensor.fictional_new_boiler"})
    assert recorder.model.overview(BASE+120)["today"]["volume_l"] == 1
    assert recorder.access_sources >= {CONFIG["volume_entity"], "sensor.fictional_old_boiler", "sensor.fictional_new_boiler"}
    assert "sensor.fictional_old_boiler" not in str(recorder.model.detail(when=BASE+120))
    await recorder.close()
    assert calls == []


def context_point(at, *, temperature=MISSING, temp_stamp=None, active=MISSING, dish_stamp=None, binding="a"*64):
    boiler = {} if temperature is MISSING else {"temperature": {"value": temperature,
        "reported_at": at if temp_stamp is None else temp_stamp, "valid_until": at+300}}
    context = {"boiler": boiler}
    if active is not MISSING:
        context["dishwasher"] = {"value": active, "reported_at": at if dish_stamp is None else dish_stamp,
                                 "valid_until": at+300}
    return {"captured_at": at, "context_binding": binding, "context": context}


def test_context_role_swap_changes_pairing_identity_even_when_source_set_is_identical(monkeypatch):
    from homeassistant.helpers import entity_registry as registry_module

    monkeypatch.setattr(registry_module, "async_get", lambda _h: NS(async_get=lambda entity:
        NS(config_entry_id="fictional", device_id=entity, unique_id=entity)))
    runtime = NS(configs={}, hass=NS(states=NS(get=lambda _e: None)))
    p = dict(source_stale_s=300, temperature_entity="sensor.fictional_a", target_entity="sensor.fictional_b",
             temperature_c=52, target_c=50, temperature_stamp=BASE, target_stamp=BASE)
    first, sources, binding = capture_water_context(runtime, p, now=BASE)
    swapped = {**p, "temperature_entity": p["target_entity"], "target_entity": p["temperature_entity"]}
    second, swapped_sources, swapped_binding = capture_water_context(runtime, swapped, now=BASE)
    assert first == second and sources == swapped_sources
    assert binding != swapped_binding
    rows = [context_point(BASE, temperature=52, binding=binding),
            context_point(BASE+60, temperature=49, binding=swapped_binding)]
    assert correlate_water_history({"points": rows})["boiler_drops"] == []


def test_repeated_boiler_timestamp_does_not_skip_independent_fresh_dishwasher_comparison():
    detail = {"points": [context_point(BASE, temperature=52, active=True),
                          context_point(BASE+60, temperature=52, temp_stamp=BASE, active=True)],
              "intervals": [{"start": BASE, "end": BASE+60, "volume_l": 3, "reason": "counter_delta"}]}
    before = deepcopy(detail)
    result = correlate_water_history(detail)
    assert result["boiler_drops"] == []
    assert result["dishwasher_intervals"][0]["observed_volume_l"] == 3
    assert result["dishwasher_intervals"][0]["scope"] == "household_during_observed_dishwasher"
    assert detail == before


@pytest.mark.parametrize("middle", ["missing", "stale", "false", "binding-missing", "binding-change"])
def test_unknown_or_changed_boiler_context_breaks_pairing_instead_of_skipping_the_gap(middle):
    mid = context_point(BASE+60, temperature=51)
    if middle == "missing":
        mid["context"]["boiler"] = {}
    elif middle == "stale":
        mid["context"]["boiler"]["temperature"]["valid_until"] = BASE+59
    elif middle == "false":
        mid["context"]["boiler"]["temperature"]["value"] = False
    else:
        mid["context_binding"] = None if middle == "binding-missing" else "b"*64
    detail = {"points": [context_point(BASE, temperature=52), mid,
                          context_point(BASE+120, temperature=49)]}
    assert correlate_water_history(detail)["boiler_drops"] == []


def test_counter_gap_volume_is_never_attributed_to_same_period_appliance_context():
    detail = {"points": [context_point(BASE, temperature=52, active=True),
                          context_point(BASE+120, temperature=49, active=True)],
              "intervals": [{"start": BASE, "end": BASE+120, "volume_l": 500,
                             "day": None, "reason": "counter_gap"}]}
    result = correlate_water_history(detail)
    assert result["dishwasher_intervals"] == []
    drop = result["boiler_drops"][0]
    assert drop["observed_volume_l"] is None and drop["water_observed"] is None
    assert drop["flow_observed"] is False


def test_correlations_sum_small_selected_volume_without_large_prefix_cancellation():
    intervals = [{"start": BASE+60*n, "end": BASE+60*(n+1), "volume_l": 1e15,
                  "reason": "counter_delta"} for n in range(10)]
    intervals.append({"start": BASE+1000, "end": BASE+1060, "volume_l": 1,
                      "reason": "counter_delta"})
    result = correlate_water_history({"intervals": intervals,
        "points": [context_point(BASE+1000, temperature=52), context_point(BASE+1060, temperature=49)]})
    assert result["boiler_drops"][0]["observed_volume_l"] == 1


def test_very_large_accepted_counter_resets_keep_daily_totals_and_json_finite():
    m = model(flow_entity="", leak_entity="")
    for n in range(101):
        observe(m, BASE+2*n, volume="0")
        view = observe(m, BASE+2*n+1, volume=str(10**15))
    assert math.isfinite(view["today"]["volume_l"]) and view["today"]["volume_l"] == pytest.approx(101e15)
    json.dumps(m.snapshot(), allow_nan=False)
    invalid = observe(m, BASE+300, volume="1e309")
    assert invalid["volume"]["value"] is None and not invalid["volume"]["fresh"]
    json.dumps(m.snapshot(), allow_nan=False)


@pytest.mark.parametrize("role", ["flow", "volume", "native_leak"])
@pytest.mark.parametrize("fresh", [None, 1, "true"])
def test_water_ui_primary_history_source_requires_explicit_fresh_flag_at_capture(role, fresh):
    data = water_day();data["points"][0][role]["fresh"] = fresh
    key = "leak" if role == "native_leak" else role
    result = run_water(data, f"return d._pointWater(d._data.points[0]);")
    assert result[key] is None
    assert result["temperature"] == 49  # Independent valid appliance context survives.


def test_water_ui_gap_never_fills_from_latest_source_and_snap_uses_actual_capture_time():
    data = water_day();at = data["points"][0]["captured_at"]
    data.update(current={"flow": {"value": 9999}, "volume": {"value": 987654}})
    data["points"].append({**deepcopy(data["points"][0]), "captured_at": at+600})
    result = run_water(data, f"""
d._setScrub({at}+20);const snapped=d._scrubState(),html=d._scrubReadoutHtml();
d._setScrub({at}+300);return {{snappedAt:snapped.at,first:html,gap:d._scrubReadoutHtml(),at:d._scrubState().at}};
""")
    assert result["snappedAt"] == at and "Meetpunt" in result["first"]
    assert result["at"] == at+300 and "Waarden bij deze tijd zijn onbekend" in result["gap"]
    assert "9999" not in result["gap"] and "987654" not in result["gap"]
    assert "L/min" not in result["gap"]


def test_water_ui_disappearing_selected_point_stays_unknown_after_same_day_refresh():
    data = water_day()
    result = run_water(data, """
d._setScrub(d._data.points[0].captured_at);const old=d._scrub.at;
d._data.points=[{...d._data.points[0],captured_at:old+5}];
return {at:d._scrubState().at,point:d._scrubState().point,html:d._scrubReadoutHtml()};
""")
    assert result["point"] is None and "Waarden bij deze tijd zijn onbekend" in result["html"]


def test_water_ui_zero_and_false_remain_distinct_from_unknown_at_the_same_capture():
    data = water_day();point = data["points"][0]
    point["flow"]["value"] = point["volume"]["value"] = 0
    point["context"]["dishwasher"]["value"] = False
    point["native_leak"]["value"] = False
    result = run_water(data, "d._setScrub(d._data.points[0].captured_at);return d._scrubReadoutHtml();")
    assert "0 L/min" in result and "0 L" in result and "Niet actief gemeld" in result and "Niet gemeld" in result
    point["native_leak"].update(value=None, fresh=False)
    second = run_water(data, "return d._pointWater(d._data.points[0]);")
    assert second["leak"] is None and second["dishwasher"] is False and second["flow"] == 0


def ui_request_probe(body):
    execute("""
globalThis.CustomEvent=class {constructor(type,args={}){this.type=type;Object.assign(this,args);}};
document.removeEventListener=()=>{};
const payload=JSON.parse(%s),pending=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return{promise,resolve,reject};};
const nodes=new Map(),statuses=[],requests=[];let renders=0;
const d=Object.create(SolarPilotWaterHistoryDialog.prototype);
Object.assign(d,{_seq:0,_isOpen:true,_inflight:0,_lastFetch:0,_entryId:'entry',_deviceId:'water',_day:payload.date,
 _data:null,_input:{value:''},_scroll:{scrollTop:0},_body:{innerHTML:'',querySelector:()=>null,querySelectorAll:()=>[]},
 _dialog:{open:true,close(){this.open=false;}},_status:(text,error)=>statuses.push({text,error}),_renderData:()=>renders++,
 _hass:{user:{id:'fictional-user',is_admin:false},callService:()=>{throw Error('Device command forbidden');}},
 shadowRoot:{querySelector:selector=>{if(!nodes.has(selector))nodes.set(selector,{});return nodes.get(selector);}},dispatchEvent:()=>{}});
d._waterIdentity=d._waterUser();
""" % json.dumps(json.dumps(water_day())) + body)


@pytest.mark.parametrize("mode", ["user", "admin", "entry", "closed", "detached"])
@pytest.mark.parametrize("late_error", [False, True])
def test_water_history_late_reply_cannot_cross_user_entry_or_closed_lifecycle(mode, late_error):
    ui_request_probe("""
const mode=%s,reply=pending();d._hass.callWS=msg=>{requests.push(msg);return reply.promise;};const first=d._fetch(true);
if(mode==='user'||mode==='admin'){d._hass.user[mode==='user'?'id':'is_admin']=mode==='user'?'different-user':true;d.setContext(d._hass,null,'entry');}
else if(mode==='entry')d.setContext(d._hass,null,'new-entry');else if(mode==='detached')d.disconnectedCallback();else d.close();
if(%s)reply.reject(Error('OLD ERROR'));else reply.resolve(payload);await first;
assert.equal(d._isOpen,false);assert.equal(d._data,null);assert.equal(renders,0);
assert.equal(statuses.some(row=>row.text==='OLD ERROR'),false);
assert.deepEqual(requests,[{type:'solar_pilot/water_history',config_entry_id:'entry',date:payload.date}]);
""" % (json.dumps(mode), str(late_error).lower()))


@pytest.mark.parametrize("late_error", [False, True])
def test_new_water_day_request_keeps_its_identity_when_old_success_or_error_arrives(late_error):
    ui_request_probe("""
const old=pending(),current=pending();d._hass.callWS=msg=>{requests.push(msg);return requests.length===1?old.promise:current.promise;};
const first=d._fetch(true);d._selectDay('2026-10-18');const currentSeq=d._inflight;
if(%s)old.reject(Error('OLD DAY ERROR'));else old.resolve(payload);await first;
assert.equal(d._inflight,currentSeq);assert.equal(d._day,'2026-10-18');assert.equal(d._data,null);assert.equal(renders,0);
current.resolve({...payload,date:'2026-10-18',day_start:payload.day_start-86400,day_end:payload.day_end-86400});
while(d._inflight)await Promise.resolve();assert.equal(d._data.date,'2026-10-18');assert.equal(renders,1);
assert.equal(statuses.some(row=>row.text==='OLD DAY ERROR'),false);
""" % str(late_error).lower())


def test_water_source_catalogue_has_no_subject_selector_and_rejects_injected_item():
    execute("""
const d=Object.create(SolarPilotSourceHistoryDialog.prototype);d._entryId='entry';d._kind='water';d._itemId='injected-device';
assert.deepEqual(d._request(),{type:'solar_pilot/source_history',config_entry_id:'entry',kind:'water'});
const response={schema:1,read_only:true,scope:'current_configured_sources',kind:'water',name:'Water',sources:[]};
assert.equal(d._validated(response).kind,'water');assert.throws(()=>d._validated({...response,item_id:'other-device'}));
""")
