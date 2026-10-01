"""Beta.37 one-time activation profile: configured modules on, no invented rights."""
import pytest
from test_runtime import build


@pytest.mark.asyncio
async def test_activation_enables_configured_models_and_safe_controls_once():
    r, h = build(power=True)
    for entity in ("sensor.p1", "sensor.p2", "sensor.p3"):
        h.states.set(entity, 0, {"unit_of_measurement": "W"})
    h.states.set("climate.zone", "auto", {
        "hvac_modes": ["off", "auto", "heat", "cool"],
        "current_temperature": 21, "temperature": 21,
        "temperature_unit": "°C", "hvac_action": "idle",
    })
    h.states.set("water_heater.tank", "heat", {"current_temperature": 50, "temperature": 50})
    h.states.set("sensor.tank", 50, {"unit_of_measurement": "°C"})
    h.states.set("sensor.wallbox", 0, {"unit_of_measurement": "kW"})

    r.entry.options.update({
        "planner": {"enabled": False, "base_load_learning": False, "replay_enabled": False,
                    "forecast_deferral_enabled": False, "adaptive_power_guard": False},
        "analysis": {"enabled": False},
        "local_pv": {"enabled": False, "seed_enabled": False},
        "battery_analysis": {"enabled": False, "seed_enabled": False},
        "economy": {"enabled": False},
        "phase": {"enabled": False, "learning_enabled": False, "control_starts": False,
                  "phase_1_entity": "sensor.p1", "phase_2_entity": "sensor.p2",
                  "phase_3_entity": "sensor.p3"},
        "smart_climate": {"enabled": False, "control_enabled": False,
                          "zone_entities": ["climate.zone"]},
        "dhw": {"enabled": False, "safety_confirmed": True,
                "target_entity": "water_heater.tank", "temperature_entity": "sensor.tank"},
        "wallbox": {"enabled": False, "power_entity": "sensor.wallbox"},
        "devices": [{**r.entry.options["devices"][0], "cycle_learning_enabled": False}],
    })

    changed = await r._migrate_beta37_activation_profile()
    assert changed is True
    o = r.entry.options
    assert o["_beta37_activation_profile"] == 1
    assert o["analysis"]["enabled"] is True
    assert o["planner"]["enabled"] and o["planner"]["base_load_learning"]
    assert o["planner"]["replay_enabled"] and o["planner"]["forecast_deferral_enabled"]
    assert o["local_pv"]["enabled"] and o["battery_analysis"]["enabled"]
    assert o["economy"]["enabled"] is True
    assert o["phase"]["enabled"] and o["phase"]["learning_enabled"] and o["phase"]["control_starts"]
    assert o["smart_climate"]["enabled"] and o["smart_climate"]["control_enabled"]
    assert o["dhw"]["enabled"] is True
    assert o["wallbox"]["enabled"] is True
    assert o["devices"][0]["cycle_learning_enabled"] is True
    assert r.learning.enabled is True
    assert r.learning_hub.policy["adaptation"] == "automatic"
    assert r.learning_hub.policy["notifications"] is True
    assert r.device_modes.get("a", "disabled") == "disabled"
    assert h.services.calls == []


@pytest.mark.asyncio
async def test_activation_does_not_invent_safety_or_missing_control_sources():
    r, h = build()
    r.entry.options.update({
        "smart_climate": {"enabled": False, "control_enabled": False,
                          "zone_entities": ["climate.missing"]},
        "dhw": {"enabled": False, "safety_confirmed": False,
                "target_entity": "water_heater.tank", "temperature_entity": "sensor.tank"},
        "phase": {"enabled": False, "learning_enabled": False,
                  "phase_1_entity": "sensor.p1", "phase_2_entity": "", "phase_3_entity": ""},
        "wallbox": {"enabled": False, "power_entity": ""},
    })
    await r._migrate_beta37_activation_profile()
    o = r.entry.options
    assert o["smart_climate"]["enabled"] is True
    assert o["smart_climate"]["control_enabled"] is False
    assert o["dhw"]["enabled"] is False
    assert o["dhw"]["safety_confirmed"] is False
    assert o["phase"]["enabled"] is False
    assert o["wallbox"]["enabled"] is False
    assert h.services.calls == []


@pytest.mark.asyncio
async def test_activation_marker_makes_later_user_choices_sticky():
    r, h = build(power=True)
    r.entry.options["_beta37_activation_profile"] = 1
    r.entry.options["planner"] = {"enabled": False, "base_load_learning": False}
    r.learning.enabled = False
    r.learning_hub.policy["adaptation"] = "assisted"
    before = dict(r.entry.options["planner"])

    changed = await r._migrate_beta37_activation_profile()

    assert changed is False
    assert r.entry.options["planner"] == before
    assert r.learning.enabled is False
    assert r.learning_hub.policy["adaptation"] == "assisted"
    assert h.services.calls == []
