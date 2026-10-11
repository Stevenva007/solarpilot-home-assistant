"""Read-only tank inference and rejected-source evidence survive export/UI."""
from copy import deepcopy
import time

import pytest

from custom_components.solar_pilot.analysis_review import heatpump_record, _regime
from test_heatpump_compact68 import interpretation, render, primary_label, named
from test_analysis_review67 import electrical_sample


def independent_tank(data):
    data["panasonic"]["native_task"].update(inactive=True, inactive_action="off",
        inactive_scope="space_circuit", independent_tank_on=True, verified_global_off=False,
        source="aquarea_poll", observed_at=data.get("ts", time.time()), stale_s=120)
    return data


@pytest.mark.parametrize("view", ["board", "comfort", "loads"])
def test_independent_tank_on_with_space_off_is_compact_inferred_boiler(view):
    root, = render(independent_tank(interpretation("tapwater_heating", inactive_action="off")), view)
    assert primary_label(root, "data-heatpump-task") == "Boiler opwarmen"
    assert named(root, "data-heatpump-task").attributes["data-heatpump-task"] == "inferred"
    assert "OFF" in named(root, "data-heatpump-provenance").text()


@pytest.mark.parametrize("field,value", [("independent_tank_on", False), ("inactive_scope", "global"),
                                        ("verified_global_off", True)])
def test_incomplete_or_global_off_proof_cannot_become_inferred_boiler(field, value):
    data = independent_tank(interpretation("tapwater_heating", inactive_action="off"))
    data["panasonic"]["native_task"][field] = value
    root, = render(data)
    assert primary_label(root, "data-heatpump-operation") == "Warmtepomp werkt"


def test_space_off_scope_does_not_allow_selected_space_heating():
    root, = render(independent_tank(interpretation("space_heating", inactive_action="off")))
    assert primary_label(root, "data-heatpump-operation") == "Warmtepomp werkt"


def test_projected_history_keeps_raw_scope_and_rejected_source_without_backfill():
    data = independent_tank(electrical_sample())
    p = data["panasonic"]
    p["task_context"] = {"function": "tapwater_heating", "kind": "tank_route",
        "source": "aquarea_entity", "observed_at": data["ts"], "stale_s": 120}
    p["power_activity"].update(function_source="aquarea_entity", activity_kind="main")
    p["power_activity"]["supplies"][0].update(watts=1500, observed_at=data["ts"])
    p["power_activity"]["supplies"][1].update(watts=0, observed_at=data["ts"])
    p["power_source_quality"] = {"supply1": {"source_reported_wall": 850, "source_unit": "W",
        "source_value": "-1", "source_watts": -1, "rejection_reason": "negative", "reason": "Negatieve bronwaarde"}}
    before = deepcopy(data)
    projected = heatpump_record(data)
    assert projected["native_task"]["inactive_scope"] == "space_circuit"
    assert projected["supplies"][0]["source_quality"]["rejection_reason"] == "negative"
    assert _regime(projected) == "tapwater_heating_inferred"
    assert data == before
    p["native_task"]["verified_global_off"] = True
    assert _regime(heatpump_record(data)) != "tapwater_heating_inferred"
