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
