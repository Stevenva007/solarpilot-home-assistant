"""A phase map cannot substitute for live phase measurements at dispatch."""

import pytest

from custom_components.solar_pilot.engine import State
from test_runtime import build


def phase_runtime(*, use_map=True, control_starts=True, enabled=True):
    runtime, hass = build(device={"phase_hint": "l2"})
    runtime.mode = "solar"
    runtime.device_modes["a"] = "auto"
    runtime.phase_settings.update(
        enabled=enabled,
        control_starts=control_starts,
        use_learned_device_map=use_map,
        phase_1_entity="sensor.phase_one",
        phase_2_entity="sensor.phase_two",
        phase_3_entity="sensor.phase_three",
        limit_w=7000,
        margin_w=300,
        start_headroom_w=500,
        stale_s=120,
        learning_enabled=False,
    )
    for name in ("sensor.phase_one", "sensor.phase_two", "sensor.phase_three"):
        hass.states.set(name, 0, {"unit_of_measurement": "W"})
    return runtime, hass


def lose_phase(hass, source):
    entity = "sensor.phase_one"
    if source == "missing":
        del hass.states.data[entity]
    else:
        hass.states.set(
            entity,
            "unavailable" if source == "unavailable" else 0,
            {"unit_of_measurement": "kWh" if source == "wrong_unit" else "W",
             **({"restored": True} if source == "restored" else {})},
            age=180 if source == "old" else 0,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("use_map", [False, True])
@pytest.mark.parametrize("source", ["missing", "unavailable", "old", "wrong_unit", "restored"])
async def test_missing_live_phase_blocks_starts_with_or_without_phase_map(use_map, source):
    runtime, hass = phase_runtime(use_map=use_map)
    lose_phase(hass, source)
    await runtime.tick()
    assert runtime.phase.enabled and not runtime.phase.valid
    assert runtime.phase.block_increase
    assert not hass.services.calls and runtime.pending is None
    assert runtime.result.action is None
    assert "Fasevermogens ontbreken" in runtime.result.reasons["a"]


@pytest.mark.asyncio
@pytest.mark.parametrize("use_map", [False, True])
async def test_restored_phase_report_releases_start_without_manual_reset(use_map):
    runtime, hass = phase_runtime(use_map=use_map)
    lose_phase(hass, "missing")
    await runtime.tick()
    assert not hass.services.calls
    hass.states.set("sensor.phase_one", 0, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert runtime.phase.valid and runtime.pending is not None
    assert hass.services.calls == [("switch", "turn_on", {"entity_id": "switch.load"})]


@pytest.mark.asyncio
@pytest.mark.parametrize("use_map", [False, True])
async def test_advisory_only_phase_mode_does_not_block_on_missing_source(use_map):
    runtime, hass = phase_runtime(use_map=use_map, control_starts=False)
    lose_phase(hass, "missing")
    await runtime.tick()
    assert not runtime.phase.valid and not runtime.phase.block_increase
    assert runtime.pending is not None
    assert hass.services.calls == [("switch", "turn_on", {"entity_id": "switch.load"})]


@pytest.mark.asyncio
async def test_disabled_phase_mode_does_not_create_a_missing_source_guard():
    runtime, hass = phase_runtime(enabled=False)
    lose_phase(hass, "missing")
    await runtime.tick()
    assert not runtime.phase.enabled
    assert runtime.pending is not None
    assert hass.services.calls == [("switch", "turn_on", {"entity_id": "switch.load"})]


@pytest.mark.asyncio
@pytest.mark.parametrize("use_map, expected_start", [(False, False), (True, True)])
async def test_valid_phase_map_can_start_on_roomy_phase_beside_a_busy_phase(use_map, expected_start):
    runtime, hass = phase_runtime(use_map=use_map)
    hass.states.set("sensor.phase_one", 6600, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert runtime.phase.valid and runtime.phase.block_increase
    assert bool(runtime.pending) is expected_start
    assert bool(hass.services.calls) is expected_start
    if expected_start:
        assert hass.services.calls == [("switch", "turn_on", {"entity_id": "switch.load"})]


@pytest.mark.asyncio
@pytest.mark.parametrize("use_map", [False, True])
@pytest.mark.parametrize("meter_attrs", [None, {"estimated": True}, {"is_estimated": True}])
async def test_unknown_isolated_load_future_draw_is_reserved_on_each_phase(use_map, meter_attrs):
    runtime, hass = phase_runtime(use_map=use_map)
    runtime.configs["b"] = {**runtime.configs["a"], "id": "b", "name": "Offline load",
                            "control_entity": "switch.offline_load", "nominal_w": 300,
                            "phase_hint": "auto"}
    runtime.states["b"] = State(available=False)
    runtime.device_modes["b"] = "auto"
    runtime.recovery["b"] = {"name": "Offline load", "watts": 300}
    hass.states.set("switch.offline_load", "unavailable")
    if meter_attrs is not None:
        runtime.configs["b"]["power_entity"] = "sensor.offline_power"
        # An estimate matching nominal power proves no part of physical load
        # is already represented in the actual phase measurement.
        hass.states.set("sensor.offline_power", 300,
                        {"unit_of_measurement": "W", **meter_attrs})
    # P1 has ample current export. A 1000 W healthy load still cannot fit on
    # L2 beside an unknown compressor's possible 300 W future restart.
    hass.states.set("sensor.phase_two", 5500, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert runtime.phase.valid and runtime.phase.headroom_w == 1200
    assert runtime.isolated_reserve_w == 300
    assert runtime.result.action is None and not hass.services.calls
    assert runtime.pending is None and "b" in runtime.recovery
    # The quarantine holds only its own future commitment; enough real phase
    # headroom lets the healthy load start without waking the offline device.
    hass.states.set("sensor.phase_two", 5300, {"unit_of_measurement": "W"})
    await runtime.tick()
    assert runtime.phase.headroom_w == 1400 and runtime.isolated_reserve_w == 300
    assert runtime.pending is not None and runtime.pending["id"] == "a"
    assert hass.services.calls == [("switch", "turn_on", {"entity_id": "switch.load"})]
    assert "b" in runtime.recovery
