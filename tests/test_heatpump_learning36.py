"""Beta.36 heat-pump classification and conservative power learning."""
from types import SimpleNamespace as NS

from custom_components.solar_pilot.heatpump_learning import (
    CONTEXT_COOLING,
    CONTEXT_DHW,
    CONTEXT_HEATING,
    CONTEXT_NORMAL,
    HeatPumpActivityModel,
    classify_heatpump,
)


class States:
    def __init__(self):
        self.rows = {}
    def set(self, entity_id, state, attrs=None):
        self.rows[entity_id] = NS(state=state, attributes=attrs or {})
    def get(self, entity_id):
        return self.rows.get(entity_id)


def fake_runtime():
    states = States()
    dhw = NS(
        configured=False,
        settings={},
        config={},
        reading=NS(protection_reason=""),
    )
    climate = NS(settings={"zone_entities": ["climate.zone_1"]})
    return NS(hass=NS(states=states), dhw=dhw, smart_climate=climate), states


def test_classifies_space_heating_and_cooling_from_panasonic_action():
    runtime, states = fake_runtime()
    states.set("climate.zone_1", "auto", {"hvac_action": "heating"})
    assert classify_heatpump(runtime, NS())[0] == CONTEXT_HEATING
    states.set("climate.zone_1", "auto", {"hvac_action": "cooling"})
    assert classify_heatpump(runtime, NS())[0] == CONTEXT_COOLING


def test_classifies_tapwater_before_space_action():
    runtime, states = fake_runtime()
    runtime.dhw.configured = True
    runtime.dhw.config = {"target_entity": "water_heater.tank"}
    runtime.dhw.settings = {"hygiene_schedule_enabled": False}
    states.set("water_heater.tank", "heat", {"hvac_action": "heating"})
    states.set("climate.zone_1", "auto", {"hvac_action": "cooling"})
    assert classify_heatpump(runtime, NS(weekday=lambda: 1, time=lambda: None))[0] == CONTEXT_DHW


def test_stable_transitions_learn_planning_power_but_never_claim_realtime_headroom():
    model = HeatPumpActivityModel()
    day = "2026-10-01"

    def feed(start, context, watts, count=5):
        learned = False
        for n in range(count):
            learned = model.observe(start + n * 5, day, context, watts) or learned
        return learned

    feed(0, CONTEXT_NORMAL, 800)
    assert feed(25, CONTEXT_HEATING, 3300)
    assert feed(50, CONTEXT_NORMAL, 800)
    assert feed(75, CONTEXT_HEATING, 3300)

    estimate = model.estimate(CONTEXT_HEATING)
    assert estimate.samples >= 3
    assert 2300 <= estimate.watts <= 2700
    overview = model.overview()
    assert overview["planning_only"] is True
    assert overview["realtime_headroom_uses_estimate"] is False


def test_incompatible_heatpump_model_resets_only_itself():
    model = HeatPumpActivityModel()
    assert model.restore({"schema": 99, "samples": {"space_heating": [2500]}}) is False
    assert model.estimate(CONTEXT_HEATING).samples == 0
    assert "alleen dit model" in model.restore_note
