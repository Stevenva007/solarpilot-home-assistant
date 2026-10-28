"""Central order defaults and real final SG/Wallbox arbitration."""
from copy import deepcopy
import time

import pytest

from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from custom_components.solar_pilot.house_first import HouseFirstGuard
from test_priority_board35 import multiple, activate
from test_sg_wallbox_independence93 import unknown_wallbox


@pytest.mark.asyncio
async def test_generated_order_moves_wallbox_last_once_and_preserves_permissions():
    runtime, hass = multiple()
    await runtime.priority_board.migrate_beta36()
    permissions = runtime.priority_board.permissions()
    before = deepcopy(runtime.configs)
    assert await runtime.priority_board.migrate_beta106()
    assert runtime.priority_board.order()[-1] == "wallbox"
    assert runtime.priority_board.permissions() == permissions
    assert runtime.configs == before and not hass.services.calls
    assert not await runtime.priority_board.migrate_beta106()


@pytest.mark.asyncio
async def test_explicit_user_order_survives_upgrade_and_next_restart():
    runtime, _ = multiple()
    order = ["device:a", "wallbox", "dhw_extra", "device:second_consumer"]
    activate(runtime, order)
    runtime.entry.options["priority_board"]["source"] = "central_beta36"
    await runtime.priority_board.migrate_beta106()
    assert runtime.priority_board.order() == order
    assert not await runtime.priority_board.migrate_beta106()


@pytest.mark.asyncio
async def test_new_flexible_device_is_inserted_before_last_wallbox():
    runtime, _ = multiple()
    await runtime.priority_board.migrate_beta36()
    await runtime.priority_board.migrate_beta106()
    runtime.configs["new"] = {**runtime.configs["a"], "id": "new", "name": "New"}
    assert runtime.priority_board.order()[-2:] == ["device:new", "wallbox"]


def test_wallbox_last_and_sg_first_are_valid_order_and_have_no_wallbox_constraint():
    runtime, _ = multiple()
    order = ["dhw_extra", "device:a", "device:second_consumer", "wallbox"]
    board = runtime.priority_board
    board.validate(board.revision(), order, board.permissions(), True)
    activate(runtime, order)
    assert board.active and board.sg_before_wallbox()
    assert all(rule["before"] != "wallbox" for rule in board.constraints())


def solar_wallbox():
    runtime, hass = unknown_wallbox(issue="unknown_demand", export=0)
    runtime.settings["max_import_w"] = 4000
    runtime.learning.effective_stable_s = lambda _seconds: 0
    runtime.wallbox_settings["session_mode_entity"] = "sensor.fixture_session"
    hass.states.set("sensor.fixture_session", "Zonne-auto · laden")
    hass.states.set("sensor.public_ev_status", "Charging")
    hass.states.set("sensor.public_ev_power", 4000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.public_hp", 0, {"unit_of_measurement": "W"})
    activate(runtime, ["dhw_extra", "device:a", "wallbox"])
    return runtime, hass


def test_last_wallbox_supplies_conditional_solar_budget_but_no_physical_export():
    runtime, hass = solar_wallbox()
    budget = sg_solar_budget(runtime)
    assert budget["available_w"] == 0
    assert budget["eligible_w"] == 3850 and budget["ev_solar_w"] == 4000
    assert runtime.sg_dispatch_allowed(automatic=True)
    assert isinstance(runtime.sg_wallbox_guard, HouseFirstGuard)
    assert not hass.services.calls
    runtime.entry.options["priority_board"]["order"] = ["wallbox", "dhw_extra", "device:a"]
    assert sg_solar_budget(runtime)["ev_solar_w"] == 4000
    assert runtime.sg_dispatch_allowed(automatic=True)


@pytest.mark.parametrize("invalid", ["stale", "manual", "unknown", "missing"])
def test_conditional_ev_budget_requires_actual_current_autonomous_solar_mode(invalid):
    runtime, hass = solar_wallbox()
    if invalid == "stale":
        hass.states.set("sensor.public_ev_power", 4000, {"unit_of_measurement": "W"}, age=121)
    elif invalid == "manual":
        hass.states.set("select.public_ev_solar", "disabled")
    elif invalid == "unknown":
        hass.states.set("sensor.public_ev_status", "unknown")
    else:
        hass.states.set("sensor.public_ev_power", "unavailable", {"unit_of_measurement": "W"})
    assert sg_solar_budget(runtime)["ev_solar_w"] == 0
    assert not runtime.sg_dispatch_allowed(automatic=True)


def test_external_continuation_uses_current_consumption_and_rejects_late_import():
    runtime, hass = solar_wallbox()
    hass.states.set("sensor.public_ev_power", 0, {"unit_of_measurement": "W"})
    hass.states.set("sensor.public_hp", 3200, {"unit_of_measurement": "W"})
    runtime.sg_boost._adopting_external = True
    runtime.sg_boost.relay_confirmed = runtime.sg_boost.relay_on = True
    assert runtime.sg_dispatch_allowed(automatic=True)
    hass.states.set("sensor.grid", 601, {"unit_of_measurement": "W"})
    assert not runtime.sg_dispatch_allowed(automatic=True)
    assert not hass.services.calls


def test_deliberate_manual_on_is_not_blocked_by_a_lower_wallbox_solar_cap():
    from test_sg_timed84 import manual_on
    runtime, hass = solar_wallbox()
    hass.states.set("sensor.public_ev_power", 0, {"unit_of_measurement": "W"})
    manual_on(runtime)
    assert runtime.sg_dispatch_allowed()
    assert runtime.heat_pump_increase_allowed()[0]
    hass.states.set("sensor.grid", 900, {"unit_of_measurement": "W"})
    assert not runtime.sg_dispatch_allowed()
    assert not runtime.heat_pump_increase_allowed()[0]
    assert not hass.services.calls
