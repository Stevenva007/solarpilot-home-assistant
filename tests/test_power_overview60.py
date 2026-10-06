"""Show known electrical watts without fabricating a tank/room allocation."""
from copy import deepcopy

import pytest

from test_dhw_runtime import setup


def measured_heat_pump(*, scope="heat_pump", watts=2300):
    runtime, hass = setup(config={"power_entity": "sensor.boiler_power",
                                  "power_meter_scope": scope})
    runtime.smart_climate.settings["zone_entities"] = ["climate.home", "climate.salon"]
    hass.states.set("sensor.boiler_power", watts, {"unit_of_measurement": "W"})
    return runtime, hass


@pytest.mark.parametrize("value,unit,watts", [(2300, "W", 2300), (2.3, "kW", 2300), (0, "W", 0)])
def test_whole_heat_pump_meter_is_one_shared_total_not_per_room_power(value, unit, watts):
    runtime, hass = measured_heat_pump()
    hass.states.set("sensor.boiler_power", value, {"unit_of_measurement": unit})

    dhw = runtime.dhw.overview()
    climate = runtime.smart_climate.overview()

    assert dhw["power"]["valid"] and climate["power"]["valid"]
    assert dhw["power"] == climate["power"]
    assert dhw["power"]["value_w"] == watts
    assert dhw["power"]["scope"] == "heat_pump"
    assert dhw["power"]["shared_with_rooms"]
    assert dhw["power"]["source"] == "measured"
    assert dhw["power"]["measured_wall"] > 0
    assert all("power" not in zone and "power_w" not in zone for zone in climate["zones"])
    assert hass.services.calls == []


def test_exclusive_tank_meter_does_not_claim_a_room_climate_total():
    runtime, _ = measured_heat_pump(scope="tank", watts=1450)

    dhw = runtime.dhw.overview()["power"]
    climate = runtime.smart_climate.overview()["power"]

    assert dhw["valid"] and dhw["value_w"] == 1450 and dhw["scope"] == "tank"
    assert not climate["valid"] and climate["value_w"] is None
    assert climate["scope"] == "tank" and climate["measured_wall"] is None


@pytest.mark.parametrize("state,attributes,age", [
    (2300, {"restored": True}, 0),
    (2300, {"estimated": True}, 0),
    (2300, {"is_estimated": True}, 0),
    (2300, {"friendly_name": "Geschat warmtepompvermogen"}, 0),
    (2300, {}, 301),
    (2300, {}, -6),
    (2300, {"unit_of_measurement": "kWh"}, 0),
    (-2300, {}, 0),
    ("unavailable", {}, 0),
    ("unknown", {}, 0),
    ("nan", {}, 0),
    ("inf", {}, 0),
])
def test_untrusted_power_stays_unknown_in_both_overviews(state, attributes, age):
    runtime, hass = measured_heat_pump()
    hass.states.set("sensor.boiler_power", state,
                    {"unit_of_measurement": "W", **attributes}, age=age)

    for power in (runtime.dhw.overview()["power"], runtime.smart_climate.overview()["power"]):
        assert power["configured"]
        assert not power["valid"] and power["value_w"] is None
        assert power["measured_wall"] is None


@pytest.mark.parametrize("binding", ["grid", "pv", "battery", "wallbox", "consumer"])
def test_reused_load_or_site_meter_is_not_a_heat_pump_total(binding):
    runtime, hass = measured_heat_pump()
    meter = "sensor.boiler_power"
    if binding == "consumer":
        runtime.configs["a"]["power_entity"] = meter
    elif binding == "wallbox":
        runtime.wallbox_settings.update(enabled=False, power_entity=meter)
    else:
        runtime.settings[{"grid": "grid_entity", "pv": "pv_entity", "battery": "battery_power_entity"}[binding]] = meter

    assert not runtime.dhw.overview()["power"]["valid"]
    assert not runtime.smart_climate.overview()["power"]["valid"]
    assert hass.services.calls == []


def test_source_heartbeat_controls_freshness_even_if_watts_have_not_changed():
    runtime, hass = measured_heat_pump()
    hass.states.set("sensor.boiler_power", 2300, {"unit_of_measurement": "W"},
                    age=86400, reported_age=2)
    assert runtime.dhw.overview()["power"]["valid"]

    runtime.dhw.settings["stale_s"] = 1
    assert not runtime.dhw.overview()["power"]["valid"]


def test_presentation_maximum_age_does_not_extend_a_long_controller_timeout():
    runtime, hass = measured_heat_pump()
    runtime.dhw.settings["stale_s"] = 900
    hass.states.set("sensor.boiler_power", 2300, {"unit_of_measurement": "W"}, age=400)

    assert runtime.dhw._metered_power() == 2300
    power = runtime.dhw.overview()["power"]
    assert power["stale_s"] == 300 and not power["valid"]
    assert power["value_w"] is None


def test_missing_meter_never_substitutes_estimated_heat_pump_watts():
    runtime, _ = measured_heat_pump()
    runtime.dhw.config["power_entity"] = ""
    runtime.dhw.settings["estimated_heat_power_w"] = 3200

    for power in (runtime.dhw.overview()["power"], runtime.smart_climate.overview()["power"]):
        assert not power["configured"] and not power["valid"]
        assert power["value_w"] is None


def test_readonly_power_overviews_do_not_change_commands_ownership_or_policy():
    runtime, hass = measured_heat_pump()
    # The existing climate overview initializes model rows. Compare only after
    # that ordinary initialization, then exercise repeated presentation reads.
    runtime.smart_climate.overview()
    before = deepcopy(runtime._snapshot())
    stability = (runtime.dhw.policy.current, runtime.dhw.policy.candidate,
                 runtime.dhw.policy.candidate_since)

    for _ in range(3):
        runtime.dhw.overview()
        runtime.smart_climate.overview()

    assert runtime._snapshot() == before
    assert (runtime.dhw.policy.current, runtime.dhw.policy.candidate,
            runtime.dhw.policy.candidate_since) == stability
    assert hass.services.calls == []
