from types import SimpleNamespace
import pytest
from custom_components.solar_pilot.battery_runtime import BatteryFleetManager
from custom_components.solar_pilot.battery_fleet import BATTERY_FLEET_DEFAULTS, BATTERY_DEFAULTS
from test_runtime import build


def setup_battery(*, global_control=False, profile_control=False, exclusive=False, kind='signed_number'):
    r,h=build()
    h.states.set('sensor.bat_soc',60,{'unit_of_measurement':'%'})
    h.states.set('sensor.bat_power',0,{'unit_of_measurement':'W'})
    h.states.set('number.bat_setpoint',0,{'unit_of_measurement':'W','min':-5000,'max':5000,'step':50})
    profile={**BATTERY_DEFAULTS,'id':'bat1','name':'Batterij 1','capacity_kwh':10,
             'soc_entity':'sensor.bat_soc','power_entity':'sensor.bat_power',
             'control_kind':kind,'control_enabled':profile_control,
             'exclusive_control_confirmed':exclusive,'number_entity':'number.bat_setpoint'}
    r.entry.options['battery_fleet']={**BATTERY_FLEET_DEFAULTS,'enabled':True,'control_enabled':global_control,'charge_reserve_w':0}
    r.entry.options['batteries']=[profile]
    r.battery_fleet=BatteryFleetManager(r)
    # Actual loaded sequences prove the signed-power script target remains the
    # independent battery actuator. A script name alone grants no authority.
    scripts = {
        entity: SimpleNamespace(script=SimpleNamespace(sequence=[{
            'action': 'number.set_value',
            'target': {'entity_id': 'number.bat_setpoint'},
            'data': {'value': '{{ signed_power_w }}'},
        }])) for entity in ('script.charge', 'script.discharge', 'script.idle')
    }
    ordinary_lookup = r.hass.data['script'].get_entity
    r.hass.data['script'] = SimpleNamespace(get_entity=lambda entity: scripts.get(entity) or ordinary_lookup(entity))
    return r,h


@pytest.mark.asyncio
async def test_read_only_or_missing_double_permission_never_sends_battery_command():
    r,h=setup_battery(global_control=True,profile_control=True,exclusive=False)
    await r.battery_fleet.tick(grid_w=-2000,allow_command=True)
    assert h.services.calls == []
    assert r.battery_fleet.overview()['recommendation_w'] == -2000


@pytest.mark.asyncio
async def test_first_battery_command_is_not_blocked_by_low_system_uptime(monkeypatch):
    import sys
    r,h=setup_battery(global_control=True,profile_control=True,exclusive=True)
    battery_runtime=sys.modules['custom_components.solar_pilot.battery_runtime']
    monkeypatch.setattr(battery_runtime.time, 'monotonic', lambda: 5.0)
    sent=await r.battery_fleet.tick(grid_w=-1800,allow_command=True)
    assert sent


@pytest.mark.asyncio
async def test_signed_number_battery_command_requires_all_permissions_and_is_serialized():
    r,h=setup_battery(global_control=True,profile_control=True,exclusive=True)
    sent=await r.battery_fleet.tick(grid_w=-1800,allow_command=True)
    assert sent
    assert h.services.calls[-1] == ('number','set_value',{'entity_id':'number.bat_setpoint','value':-1800.0})
    assert r.battery_fleet.busy
    calls=len(h.services.calls)
    await r.battery_fleet.tick(grid_w=-1800,allow_command=True)
    assert len(h.services.calls)==calls


def test_restart_with_unconfirmed_battery_command_requires_review():
    r,h=setup_battery()
    r.battery_fleet.restore({'pending':{'id':'bat1','target_w':1000},'faults':{}})
    assert not r.battery_fleet.busy
    assert 'restart' in r.battery_fleet.state.faults


@pytest.mark.asyncio
async def test_script_adapter_receives_signed_and_absolute_power_variables():
    r,h=setup_battery(global_control=True,profile_control=True,exclusive=True,kind='scripts')
    cfg=r.battery_fleet.configs['bat1']
    cfg.update({'charge_script':'script.charge','discharge_script':'script.discharge','idle_script':'script.idle'})
    h.states.set('script.charge','off'); h.states.set('script.discharge','off'); h.states.set('script.idle','off')
    sent=await r.battery_fleet.tick(grid_w=1200,allow_command=True)
    assert sent
    call=h.services.calls[-1]
    assert call[0:2]==('script','turn_on')
    assert call[2]['entity_id']=='script.discharge'
    assert call[2]['variables']['signed_power_w']>0
