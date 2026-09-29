"""Runtime protection and sensor decoding against HA doubles only."""
from types import SimpleNamespace
import time
import pytest
from custom_components.solar_pilot.runtime import SolarRuntime
from custom_components.solar_pilot.engine import Action
from custom_components.solar_pilot.wallbox import protected_entity, conflicting_devices, WallboxGuard
from homeassistant.helpers import entity_registry as er
from homeassistant.exceptions import HomeAssistantError
from test_runtime import build


def setup(**settings):
    old, h = build()
    old.entry.options["wallbox"] = {
        "enabled": True, "power_entity": "sensor.ev_power", "status_entity": "sensor.ev_status",
        "mode_entity": "select.ev_solar", **settings,
    }
    h.states.set("sensor.ev_power", 2, {"unit_of_measurement": "kW"})
    h.states.set("sensor.ev_status", "Charging")
    h.states.set("select.ev_solar", "full_solar")
    r = SolarRuntime(h, old.entry)
    # These beta.2 regression cases explicitly exercise Wallbox-first / monitor.
    # New default-on house-first runtime cases are in test_house_runtime.py.
    r.others_first = False
    r.wallbox_guard = WallboxGuard(r.wallbox_settings)
    return r, h


@pytest.mark.asyncio
async def test_monitor_has_no_service_calls_and_never_enters_owned_energy():
    r, h = setup()
    await r.tick()
    assert r.wallbox_guard.reading.power_w == 2000
    assert r.managed_w == 0 and set(r.states) == {"a"}
    assert h.services.calls == []


@pytest.mark.asyncio
async def test_wallbox_consumption_not_added_or_subtracted_from_budget():
    r, h = setup(policy="monitor")
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    h.states.set("sensor.grid", -400, {"unit_of_measurement": "W"})
    await r.tick()
    assert r.result.budget_w == 400 and r.result.free_w == 400
    assert h.services.calls == []


@pytest.mark.asyncio
async def test_ev_power_has_its_own_cloud_freshness_threshold():
    r, h = setup()
    h.states.set("sensor.ev_power", 2, {"unit_of_measurement": "kW"}, age=180)
    await r.tick()
    assert r.wallbox_guard.reading.valid
    h.states.set("sensor.ev_power", 2, {"unit_of_measurement": "kW"}, age=301)
    await r.tick()
    assert not r.wallbox_guard.reading.valid and r.wallbox_guard.result.block_increase


@pytest.mark.asyncio
@pytest.mark.parametrize("value,unit", [(5, "kWh"), (-200, "W"), ("nan", "W"), ("unavailable", "kW")])
async def test_invalid_ev_meter_cannot_be_interpreted_as_available_power(value, unit):
    r, h = setup()
    h.states.set("sensor.ev_power", value, {"unit_of_measurement": unit})
    await r.tick()
    assert not r.wallbox_guard.reading.valid


@pytest.mark.asyncio
async def test_unknown_status_does_not_imply_fully_charged():
    r, h = setup()
    h.states.set("sensor.ev_power", 0, {"unit_of_measurement": "W"})
    h.states.set("sensor.ev_status", "Something new")
    await r.tick()
    assert r.wallbox_guard.reading.demand is None and r.wallbox_guard.result.block_increase


@pytest.mark.asyncio
async def test_offline_status_not_assumed_to_mean_car_unplugged():
    r, h = setup()
    h.states.set("sensor.ev_power", 0, {"unit_of_measurement": "W"})
    h.states.set("sensor.ev_status", "Disconnected")
    await r.tick()
    assert not r.wallbox_guard.reading.valid


@pytest.mark.asyncio
async def test_explicit_demand_helper_is_allowed_to_remain_unchanged():
    r, h = setup(demand_entity="input_boolean.ev_request")
    h.states.set("input_boolean.ev_request", "on", age=86400)
    h.states.set("sensor.ev_status", "unavailable")
    await r.tick()
    assert r.wallbox_guard.reading.valid and r.wallbox_guard.reading.demand


@pytest.mark.asyncio
async def test_unknown_demand_helper_blocks():
    r, h = setup(demand_entity="input_boolean.ev_request")
    h.states.set("input_boolean.ev_request", "unknown")
    await r.tick()
    assert not r.wallbox_guard.reading.valid


@pytest.mark.asyncio
async def test_waiting_ev_releases_managed_load_not_charger():
    r, h = setup()
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    h.states.set("sensor.ev_power", 0, {"unit_of_measurement": "W"})
    h.states.set("sensor.ev_status", "Waiting in queue by Eco-Smart")
    h.states.set("switch.load", "on")
    s = r.states["a"]
    s.owned = s.on = True
    s.target_w = 1000
    await r.tick()
    assert [(d, a, x["entity_id"]) for d, a, x in h.services.calls] == [("switch", "turn_off", "switch.load")]


@pytest.mark.asyncio
async def test_observe_mode_still_never_switches_even_if_ev_waits():
    r, h = setup()
    h.states.set("sensor.ev_power", 0, {"unit_of_measurement": "W"})
    h.states.set("sensor.ev_status", "Waiting in queue by Eco-Smart")
    await r.tick()
    assert h.services.calls == []


@pytest.mark.asyncio
async def test_direct_calls_to_monitor_entities_are_rejected():
    r, h = setup()
    with pytest.raises(HomeAssistantError, match="alleen-lezen"):
        await r._call("select.ev_solar", "select_option", {"option": "eco_mode"})
    assert not h.services.calls


def test_other_controls_on_same_registered_charger_are_protected(monkeypatch):
    r, h = setup()
    registry = SimpleNamespace(async_get=lambda entity: SimpleNamespace(device_id="wallbox-device") if entity.startswith(("sensor.ev_", "select.ev_", "number.ev_")) else None)
    monkeypatch.setattr(er, "async_get", lambda hass: registry)
    assert protected_entity(h, r.wallbox_settings, "number.ev_current")
    assert not protected_entity(h, r.wallbox_settings, "switch.load")


@pytest.mark.asyncio
async def test_duplicate_managed_power_meter_is_blocked_at_runtime():
    r, h = setup()
    r.configs["a"]["power_entity"] = "sensor.ev_power"
    assert conflicting_devices(h, r.wallbox_settings, list(r.configs.values())) == ["a"]
    await r._send(Action("a", 1000, "test"), time.monotonic())
    assert not h.services.calls and not r.states["a"].owned


@pytest.mark.asyncio
async def test_status_source_cannot_be_stale_even_if_local_power_is_fresh():
    r, h = setup()
    h.states.set("sensor.ev_status", "Ready", age=600)
    await r.tick()
    assert not r.wallbox_guard.reading.valid


@pytest.mark.asyncio
async def test_optional_mode_stale_gives_warning_not_claim_of_full_green():
    r, h = setup()
    h.states.set("select.ev_solar", "full_solar", age=600)
    await r.tick()
    assert r.wallbox_guard.reading.mode == "unknown"
    assert r.wallbox_guard.reading.raw_mode is None
    assert "niet beschikbaar" in r.wallbox_guard.result.warning


@pytest.mark.asyncio
async def test_no_extra_updates_of_wallbox_cloud_are_requested():
    r, h = setup()
    for _ in range(30):
        await r.tick()
    assert not h.services.calls
