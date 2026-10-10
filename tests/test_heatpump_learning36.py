"""Beta.36 heat-pump classification and conservative power learning."""
from types import SimpleNamespace as NS
from datetime import datetime, timezone
import pytest
from test_runtime import build

from custom_components.solar_pilot.heatpump_learning import (
    CONTEXT_COOLING,
    CONTEXT_DHW,
    CONTEXT_HEATING,
    CONTEXT_NORMAL,
    HeatPumpActivityModel,
    classify_heatpump,
)
from custom_components.solar_pilot.panasonic_monitor import PanasonicMonitor


class States:
    def __init__(self):
        self.rows = {}
    def set(self, entity_id, state, attrs=None):
        self.rows[entity_id] = NS(state=state, attributes=attrs or {},
                                  last_reported=datetime.now(timezone.utc))
    def get(self, entity_id):
        return self.rows.get(entity_id)


def fake_runtime():
    states = States()
    runtime = NS(hass=NS(states=states), settings={}, configs={})
    runtime._power = lambda entity, stale=None: (None, 0)
    runtime.panasonic = PanasonicMonitor(runtime, {"zone_entities": ["climate.zone_1"]})
    return runtime, states


@pytest.mark.parametrize("action,expected", [
    ("heating", CONTEXT_HEATING), ("preheating", CONTEXT_HEATING),
    (" HEATING ", CONTEXT_HEATING), ("cooling", CONTEXT_COOLING),
    ("precooling", CONTEXT_COOLING), (" COOLING ", CONTEXT_COOLING),
])
def test_classifies_space_heating_and_cooling_from_panasonic_action(action, expected):
    runtime, states = fake_runtime()
    states.set("climate.zone_1", "auto", {"hvac_action": action})
    assert classify_heatpump(runtime, NS())[0] == expected


@pytest.mark.parametrize("action", ["heating", "preheating", "heat", "dhw", "hot_water", " HEATING "])
def test_explicit_space_cooling_remains_visible_beside_tapwater_action(action):
    runtime, states = fake_runtime()
    runtime.panasonic.settings["tank_target_entity"] = "water_heater.tank"
    states.set("water_heater.tank", "heat", {"hvac_action": action})
    states.set("climate.zone_1", "auto", {"hvac_action": "cooling"})
    # Current SG safety must not hide reported cooling behind a tank action.
    # Both can be reported while tank heat uses an electrical auxiliary heater;
    # this does not prove which compressor task is physically active.
    assert classify_heatpump(runtime, NS(weekday=lambda: 1, time=lambda: None))[0] == CONTEXT_COOLING
    observed = runtime.panasonic.overview()
    assert observed["context_reliable"] and observed["cooling_possible"]
    assert observed["compressor_running"] is None


@pytest.mark.parametrize("action", ["heating", "preheating", "heat", "dhw", "hot_water", " HEATING "])
def test_tapwater_action_still_classifies_when_no_space_action_is_reported(action):
    runtime, states = fake_runtime()
    runtime.panasonic.settings["tank_target_entity"] = "water_heater.tank"
    states.set("water_heater.tank", "heat", {"hvac_action": action})
    states.set("climate.zone_1", "auto", {"hvac_action": "idle"})
    assert classify_heatpump(runtime, NS())[0] == CONTEXT_DHW
    observed = runtime.panasonic.overview()
    assert observed["context_reliable"] and observed["compressor_running"] is None
    # A tank action alone does not rule out an AUTO cooling programme.
    assert observed["cooling_possible"]


def test_stable_transitions_learn_planning_power_but_never_claim_realtime_headroom():
    model = HeatPumpActivityModel()

    def feed(start, day, context, watts, count=5):
        learned = False
        for n in range(count):
            learned = model.observe(start + n * 5, day, context, watts) or learned
        return learned

    # Day 1: stable normal -> heating -> normal gives two independent edges.
    feed(0, "2026-10-01", CONTEXT_NORMAL, 800)
    assert feed(25, "2026-10-01", CONTEXT_HEATING, 3300)
    assert feed(50, "2026-10-01", CONTEXT_NORMAL, 800)

    # A long gap resets transition state. Day 2 must build a fresh stable baseline.
    feed(86400, "2026-10-02", CONTEXT_NORMAL, 820)
    assert feed(86425, "2026-10-02", CONTEXT_HEATING, 3320)
    assert feed(86450, "2026-10-02", CONTEXT_NORMAL, 820)

    estimate = model.estimate(CONTEXT_HEATING)
    assert estimate.samples >= 4
    assert estimate.days >= 2
    assert 2300 <= estimate.watts <= 2700
    overview = model.overview()
    assert overview["planning_only"] is True
    assert overview["realtime_headroom_uses_estimate"] is False


def test_incompatible_heatpump_model_resets_only_itself():
    model = HeatPumpActivityModel()
    assert model.restore({"schema": 99, "samples": {"space_heating": [2500]}}) is False
    assert model.estimate(CONTEXT_HEATING).samples == 0
    assert "alleen dit model" in model.restore_note


def test_heatpump_transition_gap_is_not_learned_as_compressor_step():
    model=HeatPumpActivityModel()
    for n in range(5):
        model.observe(n*5,"2026-10-01",CONTEXT_NORMAL,800)
    for n in range(5):
        model.observe(3600+n*5,"2026-10-01",CONTEXT_HEATING,3300)
    assert model.estimate(CONTEXT_HEATING).samples==0


def test_learned_heatpump_power_never_changes_realtime_site_measurement():
    r,h=build(settings={'pv_entity':'sensor.pv'})
    h.states.set('sensor.pv',3000,{'unit_of_measurement':'W'})
    r.heatpump_learning.samples[CONTEXT_HEATING]=[5000,5100,4950,5050]
    r.heatpump_learning.days[CONTEXT_HEATING]={'2026-09-29','2026-09-30'}
    assert r.heatpump_learning.estimate(CONTEXT_HEATING).watts is not None
    grid,valid,discharge,ready,_stamp=r._site_data()
    assert valid and ready
    assert grid==-2500
    assert discharge==0
    # The learned 5 kW estimate is not subtracted from P1 and cannot create headroom.
    assert grid != -7500
