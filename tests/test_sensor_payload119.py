"""Bound live telemetry without dropping the complete dashboard/export frame."""
from copy import deepcopy
import json

import pytest

from test_runtime import build
from test_sensor_recorder59 import sensor


FAMILIES = (
    "ems_solar_today", "ems_value_today", "ems_self_consumption",
    "capacity_status", "capacity_limit", "capacity_headroom",
    "phase_status", "phase_headroom", "phase_learning_status",
    "phase_l1_known", "phase_l1_residual", "phase_l2_known", "phase_l2_residual",
    "phase_l3_known", "phase_l3_residual", "local_pv_status",
    "local_pv_corrected_power", "local_pv_confidence", "battery_analysis_status",
    "battery_10_5_avoided", "battery_fleet_status", "battery_fleet_soc", "battery_fleet_power",
)


def bytes_of(value):
    return len(json.dumps(value, ensure_ascii=False).encode())


def test_scalar_sensor_payload_does_not_repeat_unrelated_planner_and_forecast():
    runtime, hass = build()
    runtime.pv_forecast.cached = {
        "available": True,
        "horizon": [{"raw_w": 1500, "corrected_w": 1400, "at": n * 900}
                    for n in range(192)],
    }
    complete = sensor(runtime, "ems_status").extra_state_attributes
    # A representative large presentation field is preserved in the hub;
    # it must not be repeated onto all 23 unrelated scalar entities.
    complete["planner"]["synthetic_horizon"] = [
        {"at": n * 900, "reason": "Fictitious planning evidence", "power_w": 500}
        for n in range(192)
    ]
    before = deepcopy(complete)
    original_values = [sensor(runtime, suffix).native_value for suffix in FAMILIES]
    projected = [sensor(runtime, suffix).extra_state_attributes for suffix in FAMILIES]

    baseline = bytes_of(complete) * (len(FAMILIES) + 1)
    published = bytes_of(complete) + sum(map(bytes_of, projected))
    assert published < baseline * .30
    assert all("planner" not in attrs and "pv_forecast" not in attrs for attrs in projected)
    assert sensor(runtime, "ems_status").extra_state_attributes is complete
    assert sensor(runtime, "status").extra_state_attributes["ems"] is complete
    assert complete == before
    assert original_values == [sensor(runtime, suffix).native_value for suffix in FAMILIES]
    assert not hass.services.calls


@pytest.mark.parametrize("suffix,section", [
    ("capacity_headroom", "capacity"),
    ("phase_l2_residual", "phase_attribution"),
    ("local_pv_status", "local_pv"),
    ("battery_fleet_power", "battery_fleet"),
    ("battery_10_5_avoided", "battery_analysis"),
    ("ems_value_today", "today"),
])
def test_family_details_keep_original_unknown_values_and_source_timestamps(suffix, section):
    runtime, hass = build()
    frame = runtime.sensor_overview("ems")
    original = {"value": None, "reported_at": 100, "valid_until": 220, "fresh": False}
    frame[section] = deepcopy(original)
    frame["warnings"] = ["Fictitious stale source"]
    attributes = sensor(runtime, suffix).extra_state_attributes
    assert attributes[section] is frame[section]
    assert attributes[section] == original
    assert attributes["warnings"] == ["Fictitious stale source"]
    assert "panasonic" not in attributes and "sg_boost" not in attributes
    assert not hass.services.calls


def test_unrelated_energy_change_does_not_dirty_local_forecast_sensor_attributes():
    runtime, hass = build()
    entity = sensor(runtime, "local_pv_status")
    full = runtime.sensor_overview("ems")
    previous = deepcopy(entity.extra_state_attributes)
    old_forecast = deepcopy(full["local_pv"])
    full["battery_fleet"]["synthetic_updated_at"] = 12345
    full["planner"]["synthetic_progress"] = 77
    assert entity.extra_state_attributes == previous
    assert entity.extra_state_attributes["local_pv"] == old_forecast
    assert full["battery_fleet"]["synthetic_updated_at"] == 12345
    assert not hass.services.calls


def test_new_publication_still_refreshes_related_phase_details():
    runtime, hass = build()
    entity = sensor(runtime, "phase_l1_known")
    runtime.phase_learning.accepted = 3
    assert entity.extra_state_attributes["phase_learning"]["accepted_events"] == 3
    seen = []
    runtime.subscribe(lambda: seen.append(entity.extra_state_attributes))
    runtime.phase_learning.accepted = 7
    runtime.publish()
    assert seen[0]["phase_learning"]["accepted_events"] == 7
    assert "battery_fleet" not in seen[0]
    assert not hass.services.calls
