"""Absolute battery targets preserve physical grid feedback and safe transitions."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.battery_fleet import (
    BatteryReading, BATTERY_FLEET_DEFAULTS, recommend,
)
from test_battery_runtime import setup_battery


def reading(i="a", *, soc=60, power=0, controllable=True, charge=5000, discharge=5000):
    return BatteryReading(i, i, True, soc, power, 10, 5, 15, 95,
                          charge, discharge, controllable, "three_phase")


def recommendation(rows, grid, **settings):
    return recommend({**BATTERY_FLEET_DEFAULTS, "enabled": True, **settings}, rows, grid)


def projected_grid(grid, rows, allocations):
    return grid + sum(r.power_w for r in rows if r.controllable) - sum(allocations.values())


@pytest.mark.parametrize("grid,current,target,expected_grid", [
    (100, 1900, 1900, 100),
    (-150, -1850, -1850, -150),
    (150, -2000, -1700, -150),
    (-50, 1900, 1750, 100),
])
def test_controlled_charge_discharge_feedback_retains_absolute_steady_target(
        grid, current, target, expected_grid):
    rows=[reading(power=current)]

    result=recommendation(rows,grid)

    assert result.total_target_w==target
    assert result.control_allocations=={"a":target}
    assert projected_grid(grid,rows,result.control_allocations)==expected_grid


@pytest.mark.parametrize("power,grid", [(1900,100), (-1850,-150)])
def test_readonly_flow_stays_in_control_residual_with_separate_absolute_advice(power,grid):
    rows=[reading("readonly",soc=80 if power>0 else 20,power=power,controllable=False),
          reading("controlled",soc=50)]

    result=recommendation(rows,grid)

    assert result.total_target_w==power
    assert result.allocations["readonly"]==power
    assert result.control_allocations=={"readonly":0,"controlled":0}
    assert projected_grid(grid,rows,result.control_allocations)==grid


def test_opposing_controlled_flows_use_signed_net_not_positive_only_discharge_credit():
    rows=[reading("discharge",soc=80,power=2000),reading("charge",soc=40,power=-2000)]

    result=recommendation(rows,1800)

    assert sum(result.control_allocations.values())==1700
    assert projected_grid(1800,rows,result.control_allocations)==100
    assert result.control_allocations["charge"]==0


def test_hybrid_peak_shaving_keeps_discharge_already_holding_grid_at_budget():
    rows=[reading(power=1500)]
    result=recommend({**BATTERY_FLEET_DEFAULTS,"enabled":True,"strategy":"hybrid",
                      "discharge_reserve_w":5000},rows,2500,2500)

    assert result.control_allocations=={"a":1500}
    assert projected_grid(2500,rows,result.control_allocations)==2500


@pytest.mark.parametrize("soc,power,grid", [(15,1900,100),(14,1900,100),(95,-1850,-150)])
def test_current_battery_flow_cannot_create_soc_headroom(soc,power,grid):
    result=recommendation([reading(soc=soc,power=power)],grid)

    assert result.total_target_w==0
    assert result.control_allocations=={"a":0}


def test_readonly_capacity_does_not_enlarge_actual_control_allocation():
    rows=[reading("readonly",soc=80,controllable=False),
          reading("controlled",soc=50,power=500,discharge=500)]

    result=recommendation(rows,1500)

    assert result.total_target_w==1900
    assert result.control_allocations=={"readonly":0,"controlled":500}
    assert projected_grid(1500,rows,result.control_allocations)==1500


def second_battery(manager,hass,*,power=0,soc=40):
    cfg=deepcopy(manager.configs["bat1"])
    cfg.update(id="bat2",name="Batterij 2",soc_entity="sensor.bat2_soc",
               power_entity="sensor.bat2_power",number_entity="number.bat2_setpoint")
    manager.configs["bat2"]=cfg
    hass.states.set("sensor.bat2_soc",soc,{"unit_of_measurement":"%"})
    hass.states.set("sensor.bat2_power",power,{"unit_of_measurement":"W"})
    hass.states.set("number.bat2_setpoint",power,
                    {"unit_of_measurement":"W","min":-5000,"max":5000,"step":50})


@pytest.mark.asyncio
@pytest.mark.parametrize("power,grid", [(2000,-200),(200,1900)])
async def test_runtime_moves_discharge_ownership_by_reducing_old_battery_before_starting_new(power,grid):
    runtime,hass=setup_battery(global_control=True,profile_control=True,exclusive=True)
    manager=runtime.battery_fleet
    manager.settings["charge_reserve_w"]=150
    hass.states.set("sensor.bat_soc",80,{"unit_of_measurement":"%"})
    second_battery(manager,hass,power=power,soc=40)

    sent=await manager.tick(grid_w=grid,allow_command=True)

    assert sent
    assert hass.services.calls==[("number","set_value",{
        "entity_id":"number.bat2_setpoint","value":0,
    })]
    assert manager.state.pending["id"]=="bat2"


@pytest.mark.asyncio
async def test_runtime_reverses_battery_sign_via_confirmed_neutral_first():
    runtime,hass=setup_battery(global_control=True,profile_control=True,exclusive=True)
    manager=runtime.battery_fleet
    manager.settings["charge_reserve_w"]=150
    hass.states.set("sensor.bat_power",-2000,{"unit_of_measurement":"W"})
    hass.states.set("number.bat_setpoint",-2000,
                    {"unit_of_measurement":"W","min":-5000,"max":5000,"step":50})

    sent=await manager.tick(grid_w=4000,allow_command=True)

    assert sent
    assert hass.services.calls==[("number","set_value",{
        "entity_id":"number.bat_setpoint","value":0,
    })]
    assert manager.state.pending["target_w"]==0
