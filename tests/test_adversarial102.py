"""Independent beta102 evidence boundaries, using fictional source data only."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from custom_components.solar_pilot.heatpump_learning import (
    CONTEXT_HEATING, CONTEXT_NORMAL, CONTEXT_UNKNOWN,
    HeatPumpActivityModel, classify_heatpump_observation,
)
from custom_components.solar_pilot.planner_quality import PlanQualityTracker
from custom_components.solar_pilot.water import WaterModel
from custom_components.solar_pilot.water_correlations import correlate_water_history
from custom_components.solar_pilot.water_diagnostics import water_monitor_diagnostic
from test_aquarea_semantics98 import NOW, split_snapshot


BASE = datetime(2026, 10, 20, 10, tzinfo=timezone.utc).timestamp()


def quality_sample(tracker, index, predicted, actual):
    at = datetime(2026, 10, 1, tzinfo=timezone.utc) + timedelta(minutes=5*index)
    assert tracker.observe(wall_ts=at.timestamp(), local_now=at,
                           predicted_pv_w=predicted, actual_pv_w=actual)


def test_clean_night_padding_cannot_hide_a_daylight_warning_or_rewrite_daylight_metrics():
    tracker = PlanQualityTracker()
    for index in range(12):
        quality_sample(tracker, index, 1800, 800)
    before = tracker.overview()
    saved_daylight = {key: value for key, value in before["last_7d"].items()
                      if key.startswith("pv_daylight_")}
    for index in range(12, 132):
        quality_sample(tracker, index, 0, 0)
    after = tracker.overview()
    assert before["findings"] == after["findings"]
    assert any("PV-voorspelling" in finding for finding in after["findings"])
    assert after["last_7d"]["pv_mae_w"] < 100 < before["last_7d"]["pv_mae_w"]
    assert {key: value for key, value in after["last_7d"].items()
            if key.startswith("pv_daylight_")} == saved_daylight
    snapshot = deepcopy(tracker.snapshot())
    tracker.overview()
    assert tracker.snapshot() == snapshot


def enablement_snapshot():
    view = split_snapshot()
    view["native_task"].update(function=CONTEXT_HEATING, inactive=False,
                               verified_global_off=False,
                               raw_evidence=[{"operation_status_scope": "device_enablement"}])
    # A previously rendered optimistic result must not be an evidence source.
    view["operation_display"] = {"context": CONTEXT_HEATING, "function": CONTEXT_HEATING,
                                  "tier": "confirmed", "model_eligible": True,
                                  "kind": "coherent_native_context"}
    return view


@pytest.mark.parametrize("failure", ["pump_off", "cached", "partial", "missing_contract"])
def test_modern_enablement_cannot_borrow_cached_display_or_normal_household_permission(failure):
    view = enablement_snapshot()
    view.update(context=CONTEXT_NORMAL, context_reliable=True, context_stamp=NOW-1)
    if failure == "pump_off":
        view["source_contract"]["pump"]["state"] = "off"
        view.update(power_w=0)
        view["power_activity"].update(active=False, state="off", total_w=0)
        for row in view["power_activity"]["supplies"]:
            row.update(watts=0, state="off")
    elif failure == "cached":
        view["source_contract"]["status_data_mode"] = "CACHED"
    elif failure == "partial":
        view.update(power_complete=False, power_w=None)
        view["power_activity"].update(complete=False, state="partial", total_w=None)
    else:
        view.pop("source_contract")
    before = deepcopy(view)
    result = classify_heatpump_observation(view, now_wall=NOW)
    assert result["context"] == CONTEXT_UNKNOWN and result["tier"] == "unknown"
    assert result["model_eligible"] is False
    assert view == before


@pytest.mark.parametrize("scope", ["device_enablement", "unverified", None, False, True, "", "global"])
@pytest.mark.parametrize("placement", ["raw_row", "native"])
def test_explicit_modern_scope_alone_cannot_become_confirmed_native_task(scope, placement):
    view = enablement_snapshot()
    view.pop("source_contract")
    if placement == "raw_row":
        view["native_task"]["raw_evidence"][0]["operation_status_scope"] = scope
    else:
        view["native_task"].pop("raw_evidence")
        view["native_task"]["operation_status_scope"] = scope
    result = classify_heatpump_observation(view, now_wall=NOW)
    assert result["context"] == CONTEXT_UNKNOWN and not result["model_eligible"]


def test_coherent_enablement_direction_is_diagnostic_and_never_accumulates_a_power_model():
    view = enablement_snapshot()
    before = deepcopy(view)
    result = classify_heatpump_observation(view, now_wall=NOW)
    assert result["context"] == CONTEXT_HEATING and result["tier"] == "derived"
    assert result["model_eligible"] is False and view == before
    model = HeatPumpActivityModel()
    for index in range(100):
        model.observe(NOW+index*5, "2026-10-14", result["context"], 2300,
                      evidence=result["tier"], detail=result)
    assert model.estimate(CONTEXT_HEATING).watts is None
    assert not model.confirmed_samples[CONTEXT_HEATING]


def point(at, temperature, *, binding="a"*64, stamp=None, flow=None):
    stamp = at if stamp is None else stamp
    row = {"captured_at": at, "context_binding": binding,
           "context": {"boiler": {"temperature": {
               "value": temperature, "reported_at": stamp, "valid_until": at+300}}}}
    if flow is not None:
        row["flow"] = {"value": flow, "fresh": True, "reported_at": at, "valid_until": at+300}
    return row


def intervals(count):
    return [{"start": BASE+index*60, "end": BASE+(index+1)*60,
             "volume_l": 1, "reason": "counter_delta", "day": "2026-10-20"}
            for index in range(count)]


def test_quantized_one_degree_steps_form_disjoint_drop_windows_without_double_counting_litres():
    detail = {"points": [point(BASE+index*60, 55-index) for index in range(5)],
              "intervals": intervals(4)}
    before = deepcopy(detail)
    result = correlate_water_history(detail)
    drops = result["boiler_drops"]
    assert [(row["temperature_start_c"], row["temperature_end_c"]) for row in drops] == [(55, 53), (53, 51)]
    assert drops[0]["end"] == drops[1]["start"]
    assert sum(row["observed_volume_l"] for row in drops) == 4
    assert all(row["volume_partial"] is True for row in drops)
    assert result["read_only"] is True and detail == before


@pytest.mark.parametrize("role,expected", [("flow", 1), ("volume", 0),
                                           ("boiler_temperature", 0), (None, 0)])
def test_only_explicit_unrelated_flow_gap_can_preserve_independent_volume_temperature_pair(role, expected):
    event = {"at": BASE+90, "kind": "source_gap"}
    if role is not None:
        event["source_role"] = role
    detail = {"points": [point(BASE, 55, flow=0), point(BASE+60, 54, flow=0),
                          point(BASE+120, 53, flow=0)],
              "intervals": intervals(2), "events": [event]}
    drops = correlate_water_history(detail)["boiler_drops"]
    assert len(drops) == expected
    if expected:
        assert drops[0]["observed_volume_l"] == 2
        assert drops[0]["water_observed"] is True
        assert drops[0]["flow_observed"] is False


def test_held_original_temperature_report_cannot_become_a_new_rolling_baseline():
    detail = {"points": [point(BASE, 55),
                          point(BASE+600, 54, stamp=BASE),
                          point(BASE+660, 53)], "intervals": intervals(11)}
    assert correlate_water_history(detail)["boiler_drops"] == []


def test_changed_context_identity_discards_every_old_rolling_baseline():
    detail = {"points": [point(BASE, 55), point(BASE+60, 54, binding="b"*64),
                          point(BASE+120, 53, binding="b"*64)], "intervals": intervals(2)}
    assert correlate_water_history(detail)["boiler_drops"] == []


def test_late_capture_cannot_resurrect_an_original_temperature_report_from_before_a_known_gap():
    detail = {"points": [point(BASE, 55), point(BASE+120, 53, stamp=BASE+60)],
              "intervals": intervals(1),
              "events": [{"at": BASE+90, "kind": "source_gap",
                          "source_role": "boiler_temperature"}]}
    assert correlate_water_history(detail)["boiler_drops"] == []


@pytest.mark.parametrize("kind", ["counter_reset", "counter_gap", "restart", "binding_changed",
                                  "clock_reversal", "disabled"])
def test_flow_role_cannot_narrow_an_unrelated_hard_history_barrier(kind):
    detail = {"points": [point(BASE, 55), point(BASE+60, 54), point(BASE+120, 53)],
              "intervals": intervals(2),
              "events": [{"at": BASE+90, "kind": kind, "source_role": "flow"}]}
    assert correlate_water_history(detail)["boiler_drops"] == []
    model = WaterModel()
    saved = deepcopy(model.snapshot())
    saved["events"] = deepcopy(detail["events"])
    assert model.restore(saved, BASE+120) is False


@pytest.mark.parametrize("role", [None, False, True, 0, [], {}, "temperature", "FLOW", "volume,flow"])
def test_invalid_explicit_restored_gap_role_is_rejected_atomically(role):
    model = WaterModel()
    original = deepcopy(model.snapshot())
    corrupted = deepcopy(original)
    corrupted["events"] = [{"at": BASE, "kind": "source_gap", "source_role": role}]
    assert model.restore(corrupted, BASE+10) is False
    assert model.snapshot() == original


def test_legacy_unscoped_gap_remains_unscoped_through_restore_and_cannot_gain_pairing_rights():
    model = WaterModel()
    saved = deepcopy(model.snapshot())
    saved["events"] = [{"at": BASE+90, "kind": "source_gap"}]
    assert model.restore(saved, BASE+120) is True
    restored = next(row for row in model.snapshot()["events"] if row["kind"] == "source_gap")
    assert "source_role" not in restored
    detail = {"points": [point(BASE, 55), point(BASE+60, 54), point(BASE+120, 53)],
              "intervals": intervals(2), "events": [restored]}
    assert correlate_water_history(detail)["boiler_drops"] == []


def test_independently_fresh_counter_cannot_refresh_either_configured_water_detector():
    settings = {"enabled": True, "volume_entity": "sensor.fictional_counter",
                "flow_entity": "sensor.fictional_flow", "leak_entity": "binary_sensor.fictional_leak"}
    view = {"observed_at": BASE, "volume": {"fresh": True, "value": 12345,
              "reported_at": BASE, "valid_until": BASE+300},
            "flow": {"fresh": False, "value": None, "reason": "stale",
              "reported_at": BASE-301, "valid_until": BASE-1},
            "native_leak": {"fresh": False, "value": None, "reason": "stale",
              "reported_at": BASE-301, "valid_until": BASE-1},
            "alert": {"active": False}, "suspicion": {"state": "unknown"}}
    before = deepcopy((settings, view))
    result = water_monitor_diagnostic(view, settings)
    assert result["state"] == "unavailable" and result["read_only"] is True
    assert not result["continuous_flow_ready"] and not result["native_leak_ready"]
    assert result["flow_monitoring"]["reported_at"] == BASE-301
    assert (settings, view) == before


def test_fresh_explicit_false_leak_is_usable_but_does_not_hide_missing_flow_or_create_proof():
    settings = {"enabled": True, "flow_entity": "sensor.fictional_flow",
                "leak_entity": "binary_sensor.fictional_leak"}
    view = {"observed_at": BASE,
            "native_leak": {"fresh": True, "value": False,
                            "reported_at": BASE-1, "valid_until": BASE+299},
            "suspicion": {"state": "unknown", "elapsed_s": 0}, "alert": {"active": False}}
    before = deepcopy(view)
    result = water_monitor_diagnostic(view, settings)
    assert result["state"] == "incomplete"
    assert result["native_leak_ready"] is True and result["continuous_flow_ready"] is False
    assert view == before
    expired = water_monitor_diagnostic({**view, "observed_at": BASE+300}, settings)
    assert expired["state"] == "unavailable" and not expired["native_leak_ready"]


def detector_view():
    settings = {"enabled": True, "flow_entity": "sensor.fictional_flow",
                "leak_entity": "binary_sensor.fictional_leak"}
    view = {"schema": 1, "read_only": True, "configured": True, "enabled": True,
            "observed_at": BASE,
            "flow": {"fresh": True, "value": 0, "unit": "L/min",
                     "reported_at": BASE-299, "valid_until": BASE+1},
            "native_leak": {"fresh": True, "value": False,
                            "reported_at": BASE-1, "valid_until": BASE+299}}
    view["diagnostic"] = water_monitor_diagnostic(view, settings)
    return view


def ui_diagnostic(view, body, *, now=BASE):
    from test_audit_ui79 import execute
    return execute("""
Date.now=()=>%s;
const c=Object.create(SolarPilotCard.prototype),view=JSON.parse(%s);
c._hass={config:{time_zone:'Europe/Brussels'},callService:()=>{throw Error('No writes');}};
c._activityObservationsCurrent=()=>true;
%s
""" % (now*1000, json.dumps(json.dumps(view)), body))


def test_actual_backend_diagnostic_expires_each_ui_channel_without_borrowing_a_new_counter():
    view = detector_view()
    view["volume"] = {"fresh": True, "value": 5000, "unit": "L",
                      "reported_at": BASE+2, "valid_until": BASE+302}
    result = ui_diagnostic(view, "console.log(JSON.stringify(c._waterDiagnostic({water:view})));", now=BASE+2)
    assert result["valid"] is True and result["state"] == "incomplete"
    assert result["continuous_flow_ready"] is False and result["native_leak_ready"] is True
    assert result["flow_monitoring"]["reported_at"] == BASE-299
    assert result["flow_monitoring"]["valid_until"] == BASE+1


def test_ui_cannot_silently_replace_a_diagnostic_original_report_with_a_different_fresh_reading():
    view = detector_view()
    view["flow"].update(reported_at=BASE, valid_until=BASE+300)
    result = ui_diagnostic(view, "console.log(JSON.stringify(c._waterDiagnostic({water:view})));", now=BASE+1)
    assert result["state"] == "incomplete" and not result["continuous_flow_ready"]
    assert result["native_leak_ready"] is True
    assert result["flow_monitoring"]["reported_at"] == BASE-299


@pytest.mark.parametrize("corruption", ["boolean", "open_shape", "state_code"])
def test_malformed_diagnostic_cannot_claim_current_coverage_or_render_unescaped_text(corruption):
    view = detector_view()
    raw = view["diagnostic"]
    if corruption == "boolean":
        raw["flow_monitoring"]["current"] = 1
    elif corruption == "open_shape":
        raw["flow_monitoring"]["entity_id"] = "sensor.fictional_other"
    else:
        raw["code"] = "detector_sources_unavailable"
    raw["summary"] = '<img src=x onerror="fictional_attack()">'
    result = ui_diagnostic(view, "console.log(JSON.stringify({d:c._waterDiagnostic({water:view}),html:c._waterDiagnosticHtml({water:view})}));")
    assert result["d"]["valid"] is False and result["d"]["state"] == "unavailable"
    assert '<img ' not in result["html"] and "fictional_attack" not in result["html"]
