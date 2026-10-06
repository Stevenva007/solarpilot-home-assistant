"""Independent countdown proof with ordinary ticks and native 50 °C feedback."""
from datetime import datetime, timedelta, timezone
import time

import pytest

from custom_components.solar_pilot.dhw import DHWPolicy, DHWReading
from test_dhw_runtime import setup


START=datetime(2026,10,6,12,tzinfo=timezone.utc)


@pytest.mark.parametrize("rise", [60,300])
@pytest.mark.parametrize("temperature", [45,50])
@pytest.mark.parametrize("standby", [None,50])
def test_continuous_five_second_solar_samples_complete_one_policy_countdown(
        rise,temperature,standby):
    policy=DHWPolicy({"rise_delay_s":rise,"fall_delay_s":300})
    reading=DHWReading(temperature_c=temperature,actual_target_c=50,pv_w=6000,
                       export_w=5110,grid_w=-5110,cooling=False,standby_c=standby)
    remaining=[]
    for elapsed in range(0,rise+66,5):
        decision=policy.update(1000+elapsed,START+timedelta(seconds=elapsed),reading)
        remaining.append(decision.remaining_s)
        assert decision.target_c==(50 if elapsed<rise else 60)

    assert remaining==[max(0,rise-elapsed) for elapsed in range(0,rise+66,5)]
    assert policy.current==60
    assert policy.candidate is None


def test_schedule_comfort_target_below_solar_target_does_not_restart_surplus_countdown():
    policy=DHWPolicy({"rise_delay_s":60,"fall_delay_s":300})
    reading=DHWReading(temperature_c=50,actual_target_c=50,pv_w=6000,
                       export_w=4990,grid_w=-4990,cooling=False)
    for elapsed in range(0,66,5):
        reading.comfort_target_c=55 if elapsed%10 else None
        reading.comfort_reason="Avondvoorraad"
        decision=policy.update(1000+elapsed,START+timedelta(seconds=elapsed),reading)
        assert decision.remaining_s==max(0,60-elapsed)
    assert decision.target_c==60


@pytest.mark.asyncio
@pytest.mark.parametrize("cooldown", [300,1800])
@pytest.mark.parametrize("queued_at_expiry", [False,True])
async def test_runtime_optional_cooldown_cannot_restart_finished_solar_stability_countdown(
        monkeypatch,cooldown,queued_at_expiry):
    runtime,hass=setup(config={"rise_delay_s":60,"fall_delay_s":300,
                              "optional_raise_interval_s":cooldown})
    wall=[float(int(time.time()))]
    start_wall=wall[0]
    monkeypatch.setattr(time,"time",lambda:wall[0])
    manager=runtime.dhw
    manager.last_command_wall=start_wall
    runtime.pv_w=6000
    hass.states.set("sensor.pv",6000,{"unit_of_measurement":"W"})
    original_set=hass.states.set

    def report(entity,state,attrs):
        original_set(entity,state,attrs)
        obj=hass.states.get(entity)
        obj.last_reported=obj.last_updated=datetime.fromtimestamp(wall[0],timezone.utc)

    end=cooldown+5 if queued_at_expiry else cooldown
    for elapsed in range(0,end+1,5):
        wall[0]=start_wall+elapsed
        for entity in list(hass.states.data):
            obj=hass.states.get(entity)
            report(entity,obj.state,dict(obj.attributes))
        report("sensor.water",50,{"unit_of_measurement":"°C"})
        report("climate.home","off",{"hvac_action":"off"})
        report("climate.salon","off",{"hvac_action":"off"})
        allow=not (queued_at_expiry and elapsed==cooldown)
        await manager.tick(1000+elapsed,-5110,True,0,allow,
                           START+timedelta(seconds=elapsed))
        if 60<=elapsed<cooldown or queued_at_expiry and elapsed==cooldown:
            assert manager.policy.result.remaining_s==0, f"Elapsed {elapsed}: {manager.status}"
            assert manager.policy.result.target_c==60
            assert manager.overview()["optional_raise_remaining_s"]==max(0,cooldown-elapsed)
            assert not hass.services.calls

    assert hass.services.calls==[("water_heater","set_temperature",{
        "entity_id":"water_heater.boiler","temperature":60,
    })]
    assert manager.pending["target"]==60


@pytest.mark.asyncio
@pytest.mark.parametrize("block", ["serialization","observe","bounds"])
async def test_queued_unissued_55_proposal_cannot_use_owned_pv_hold_hysteresis(monkeypatch,block):
    runtime,hass=setup(config={"solar_c":55,"rise_delay_s":60,"fall_delay_s":300,
                              "optional_raise_interval_s":0})
    wall=[float(int(time.time()))]
    start_wall=wall[0]
    monkeypatch.setattr(time,"time",lambda:wall[0])
    manager=runtime.dhw
    runtime.pv_w=2000
    hass.states.set("sensor.pv",2000,{"unit_of_measurement":"W"})
    hass.states.set("sensor.water",50,{"unit_of_measurement":"°C"})
    if block=="observe":
        runtime.mode="observe"
    if block=="bounds":
        obj=hass.states.get("water_heater.boiler")
        hass.states.set("water_heater.boiler",obj.state,{**obj.attributes,"max_temp":50})
    original_set=hass.states.set

    def refresh():
        for entity in list(hass.states.data):
            obj=hass.states.get(entity)
            original_set(entity,obj.state,dict(obj.attributes))
            fresh=hass.states.get(entity)
            fresh.last_reported=fresh.last_updated=datetime.fromtimestamp(wall[0],timezone.utc)

    for elapsed in range(0,61,5):
        wall[0]=start_wall+elapsed
        refresh()
        await manager.tick(1000+elapsed,100,True,0,block!="serialization",
                           START+timedelta(seconds=elapsed))
    assert not hass.services.calls
    assert manager.reading.actual_target_c==50

    # A queued proposal has never been issued or observed as native55. Once the
    # start threshold fails, the hysteresis band must not authorize that raise.
    wall[0]+=5
    runtime.pv_w=950
    hass.states.set("sensor.pv",950,{"unit_of_measurement":"W"})
    runtime.mode="solar"
    if block=="bounds":
        obj=hass.states.get("water_heater.boiler")
        original_set("water_heater.boiler",obj.state,{**obj.attributes,"max_temp":65})
    refresh()
    await manager.tick(1065,100,True,0,True,START+timedelta(seconds=65))

    assert manager.policy.result.target_c==50
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_cooldown_of_60_candidate_preserves_verified_owned_55_pv_hold(monkeypatch):
    runtime,hass=setup(config={"solar_c":55,"rise_delay_s":60,"fall_delay_s":300,
                              "optional_raise_interval_s":1800})
    wall=[float(int(time.time()))]
    start_wall=wall[0]
    monkeypatch.setattr(time,"time",lambda:wall[0])
    manager=runtime.dhw
    manager.owned_target=55
    manager.policy.current=55
    manager.last_command_wall=start_wall
    target=hass.states.get("water_heater.boiler")
    hass.states.set("water_heater.boiler",target.state,{**target.attributes,"temperature":55})
    hass.states.set("sensor.water",50,{"unit_of_measurement":"°C"})
    runtime.pv_w=6000
    hass.states.set("sensor.pv",6000,{"unit_of_measurement":"W"})
    original_set=hass.states.set

    def refresh():
        for entity in list(hass.states.data):
            obj=hass.states.get(entity)
            original_set(entity,obj.state,dict(obj.attributes))
            fresh=hass.states.get(entity)
            fresh.last_reported=fresh.last_updated=datetime.fromtimestamp(wall[0],timezone.utc)

    for elapsed in range(0,66,5):
        wall[0]=start_wall+elapsed
        refresh()
        await manager.tick(1000+elapsed,-5110,True,0,True,START+timedelta(seconds=elapsed))
    assert not hass.services.calls

    wall[0]+=5
    runtime.pv_w=950
    hass.states.set("sensor.pv",950,{"unit_of_measurement":"W"})
    refresh()
    await manager.tick(1070,0,True,0,True,START+timedelta(seconds=70))

    assert manager.policy.result.target_c==55
    assert manager.policy.result.remaining_s==0
    assert manager.owned_target==55
    assert not hass.services.calls
