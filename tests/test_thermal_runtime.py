from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import pytest
from custom_components.solar_pilot.thermal_runtime import SmartClimateManager
from custom_components.solar_pilot.thermal_climate import ClimateDecision, SMART_CLIMATE_DEFAULTS, ThermalProfile
from test_runtime import build, Services


class ClimateServices(Services):
    def __init__(self,states):
        super().__init__(states)
        now=datetime.now(timezone.utc)
        self.forecast=[{'datetime':(now+timedelta(hours=h+1)).isoformat(),'temperature':21,'condition':'partlycloudy','humidity':60} for h in range(48)]
    async def async_call(self,domain,action,data=None,blocking=False,target=None,return_response=False,**kwargs):
        data=data or {}
        if domain=='weather' and action=='get_forecasts':
            self.calls.append((domain,action,{'data':data,'target':target}))
            entity=(target or {}).get('entity_id')
            return {entity:{'forecast':self.forecast}}
        if domain=='climate' and action=='set_hvac_mode':
            self.calls.append((domain,action,data))
            obj=self.states.get(data['entity_id'])
            attrs=dict(obj.attributes)
            self.states.set(data['entity_id'],data['hvac_mode'],attrs)
            return None
        return await super().async_call(domain,action,data,blocking)


def setup_climate(*, control=False, temp=21, target=21, mode='auto'):
    r,h=build()
    h.config=SimpleNamespace(time_zone='Europe/Brussels',units=SimpleNamespace(temperature_unit='°C'))
    h.services=ClimateServices(h.states)
    attrs={'current_temperature':temp,'temperature':target,'temperature_unit':'°C',
           'hvac_action':'idle','hvac_modes':['heat','off','cool','auto']}
    h.states.set('climate.home',mode,attrs)
    h.states.set('climate.salon',mode,attrs)
    h.states.set('sensor.outdoor',21,{'unit_of_measurement':'°C'})
    h.states.set('weather.home','partlycloudy',{'temperature':21,'temperature_unit':'°C'})
    h.states.set('sensor.native_program','heat_cool',{})
    # These tests retain the previous opt-out coast policy; beta.54 automatic
    # zone management has dedicated behavior and integration regressions.
    r.entry.options['smart_climate']={**SMART_CLIMATE_DEFAULTS,'automatic_zone_control':False,'enabled':True,'control_enabled':control,
        'zone_entities':['climate.home','climate.salon'],'weather_entity':'weather.home',
        'outside_temp_entity':'sensor.outdoor','operation_mode_entity':'sensor.native_program','decision_interval_h':12,'forecast_horizon_h':48}
    r.smart_climate=SmartClimateManager(r)
    return r,h


def mature(manager):
    for entity_id in ('climate.home','climate.salon'):
        p=ThermalProfile(); p.samples=100; p.days={str(x) for x in range(10)}; p.passive_k=[0.01]*20; p.heat_gain=[0.2]*20; p.cool_gain=[0.2]*20; p.response_delays_h=[2]*10
        manager.state.profiles[entity_id]=p


@pytest.mark.asyncio
async def test_global_learning_reset_preserves_live_climate_state_and_sends_no_command():
    r,h=setup_climate(control=True)
    state=r.smart_climate.state
    mature(r.smart_climate)
    state.weather_bias.errors['12']=[1.0]
    state.weather_bias.pending={'sample':{'valid_ts':1,'predicted_c':20,'bucket':12}}
    state.coast_feedback.history=[{'outcome':'correct'}]
    state.coast_feedback.adjust_h=.5
    active={'started_ts':10,'targets':{'climate.home':21}}
    pending={'evaluate_after_ts':20,'action_seen':False}
    state.coast_feedback.active=active
    state.coast_feedback.pending=pending
    decision=ClimateDecision('off','lopende SolarPilot-coast')
    state.last_sample_wall=101
    state.last_decision_wall=102
    state.last_guard_wall=103
    state.last_forecast_wall=104
    state.forecast=[{'temperature':20}]
    state.last_decision=decision
    state.manual_hold_until=105
    state.command_day='2026-10-02'
    state.commands_today=4
    state.expected_mode={'climate.home':'off'}
    state.last_command_wall=106
    state.last_command_mode='off'
    state.fault='veilig geblokkeerd'

    await r.reset_learning()

    assert r.smart_climate.state is state
    assert state.profiles=={}
    assert all(not values for values in state.weather_bias.errors.values())
    assert state.weather_bias.pending=={}
    assert state.coast_feedback.history==[]
    assert state.coast_feedback.adjust_h==0
    assert state.coast_feedback.active is active
    assert state.coast_feedback.pending is pending
    assert state.last_sample_wall==101
    assert state.last_decision_wall==102
    assert state.last_guard_wall==103
    assert state.last_forecast_wall==104
    assert state.forecast==[{'temperature':20}]
    assert state.last_decision is decision
    assert state.manual_hold_until==105
    assert state.command_day=='2026-10-02'
    assert state.commands_today==4
    assert state.expected_mode=={'climate.home':'off'}
    assert state.last_command_wall==106
    assert state.last_command_mode=='off'
    assert state.fault=='veilig geblokkeerd'
    saved=r.store.data['smart_climate']
    assert saved['manual_hold_until']==105
    assert saved['commands_today']==4
    assert saved['expected_mode']=={'climate.home':'off'}
    assert saved['last_command_mode']=='off'
    assert saved['fault']=='veilig geblokkeerd'
    assert not h.services.calls
    assert r.logs[0]['message'].startswith('Apparaat-, lokale PV-, fase- en klimaatleerdata gewist.')


@pytest.mark.asyncio
async def test_smart_climate_fetches_hourly_forecast_but_advisory_mode_does_not_control():
    r,h=setup_climate(control=False)
    await r.smart_climate.tick(local_now=datetime(2026,9,22,8),allow_command=True)
    assert len(r.smart_climate.state.forecast)==48
    assert not any(c[0]=='climate' for c in h.services.calls)


@pytest.mark.asyncio
async def test_hard_comfort_breach_releases_owned_coast_not_heat_or_cool_and_keeps_target():
    r,h=setup_climate(control=True,temp=19.5,target=21,mode='off')
    r.smart_climate.state.expected_mode={'climate.home':'off','climate.salon':'off'}
    await r.smart_climate.tick(local_now=datetime(2026,9,22,8),allow_command=True)
    climate_calls=[c for c in h.services.calls if c[0]=='climate']
    assert len(climate_calls)==2
    assert all(c[2]['hvac_mode']=='auto' for c in climate_calls)
    assert not any(c[2]['hvac_mode'] in ('heat','cool') for c in climate_calls)
    assert all('temperature' not in c[2] for c in climate_calls)
    assert h.states.get('climate.home').attributes['temperature']==21


@pytest.mark.asyncio
async def test_clear_winter_preserves_unowned_off_zone_at_upper_boundary():
    r,h=setup_climate(control=True,temp=21,target=21,mode='auto')
    attrs=dict(h.states.get('climate.home').attributes)
    attrs['current_temperature']=22
    h.states.set('climate.home','off',attrs)
    h.states.set('sensor.outdoor',14,{'unit_of_measurement':'°C'})
    h.services.forecast=[{**row,'temperature':14} for row in h.services.forecast]

    await r.smart_climate.tick(local_now=datetime(2026,10,2,8),allow_command=True)

    assert r.smart_climate.state.last_decision.desired_mode=='auto'
    assert r.smart_climate.state.last_decision.season_context=='winter'
    assert not any(c[0]=='climate' for c in h.services.calls)
    assert h.states.get('climate.home').state=='off'
    assert h.states.get('climate.salon').state=='auto'
    assert any(a['title']=='Handmatige OFF-zone behouden' for a in r.smart_climate.overview()['alerts'])


@pytest.mark.asyncio
async def test_winter_releases_only_solarpilot_owned_off_zone_to_auto():
    r,h=setup_climate(control=True,temp=21,target=21,mode='auto')
    attrs=dict(h.states.get('climate.home').attributes)
    h.states.set('climate.home','off',attrs)
    r.smart_climate.state.expected_mode={'climate.home':'off'}
    h.states.set('sensor.outdoor',14,{'unit_of_measurement':'°C'})
    h.services.forecast=[{**row,'temperature':14} for row in h.services.forecast]

    await r.smart_climate.tick(local_now=datetime(2026,10,2,8),allow_command=True)

    climate_calls=[c for c in h.services.calls if c[0]=='climate']
    assert len(climate_calls)==1
    assert climate_calls[0][2]=={'entity_id':'climate.home','hvac_mode':'auto'}
    assert h.states.get('climate.salon').state=='auto'


@pytest.mark.asyncio
async def test_removal_releases_owned_coast_without_waking_manual_off_zone():
    r,h=setup_climate(control=True,temp=21,target=21,mode='off')
    r.smart_climate.state.expected_mode={'climate.home':'off'}

    assert await r.smart_climate.prepare_for_removal() is True

    climate_calls=[c for c in h.services.calls if c[0]=='climate']
    assert len(climate_calls)==1
    assert climate_calls[0][2]=={'entity_id':'climate.home','hvac_mode':'auto'}
    assert h.states.get('climate.home').state=='auto'
    assert h.states.get('climate.salon').state=='off'


@pytest.mark.asyncio
async def test_hard_cold_breach_preserves_manual_off_zone():
    r,h=setup_climate(control=True,temp=21,target=21,mode='auto')
    attrs=dict(h.states.get('climate.home').attributes)
    attrs['current_temperature']=19.8
    h.states.set('climate.home','off',attrs)

    await r.smart_climate.tick(local_now=datetime(2026,10,2,8),allow_command=True)

    climate_calls=[c for c in h.services.calls if c[0]=='climate']
    assert not climate_calls
    assert h.states.get('climate.home').state=='off'
    assert h.states.get('climate.salon').state=='auto'


@pytest.mark.asyncio
async def test_mature_shoulder_model_can_put_zones_in_off_coast():
    r,h=setup_climate(control=True,temp=21,target=21,mode='auto')
    r.smart_climate.settings['solar_gain_enabled'] = False  # Passive-model fixture, no PV source.
    mature(r.smart_climate)
    await r.smart_climate.tick(local_now=datetime(2026,9,22,8),allow_command=True)
    climate_calls=[c for c in h.services.calls if c[0]=='climate']
    assert climate_calls
    assert all(c[2]['hvac_mode']=='off' for c in climate_calls)


@pytest.mark.asyncio
async def test_manual_fixed_heat_mode_is_never_overridden_even_with_hard_breach():
    r,h=setup_climate(control=True,temp=23,target=21,mode='heat')
    mature(r.smart_climate)
    await r.smart_climate.tick(local_now=datetime(2026,9,22,8),allow_command=True)
    assert not any(c[0]=='climate' for c in h.services.calls)
    assert 'nooit' in r.smart_climate.overview()['decision']['reason'].lower()


@pytest.mark.asyncio
async def test_manual_thermostat_target_is_taken_as_new_reference():
    r,h=setup_climate(control=False,temp=21,target=22)
    await r.smart_climate.tick(local_now=datetime(2026,9,22,8),allow_command=False)
    assert r.smart_climate.overview()['zones'][0]['target']==22


@pytest.mark.asyncio
async def test_missing_selected_zone_blocks_physical_climate_control():
    r,h=setup_climate(control=True,temp=19.5,target=21,mode='off')
    h.states.set('climate.salon','unavailable',{})
    await r.smart_climate.tick(local_now=datetime(2026,9,22,8),allow_command=True)
    assert not any(c[0]=='climate' for c in h.services.calls)
    assert r.smart_climate.state.fault


@pytest.mark.asyncio
async def test_send_mode_has_hard_invariant_against_heat_cool():
    r,h=setup_climate(control=True)
    zones=r.smart_climate._zones()
    assert await r.smart_climate._send_mode('heat',zones) is False
    assert await r.smart_climate._send_mode('cool',zones) is False
    assert not any(c[0]=='climate' for c in h.services.calls)


@pytest.mark.asyncio
async def test_dashboard_setting_update_applies_immediately_and_persists_to_options_without_reload_stub():
    r,h=setup_climate(control=False)
    await r.smart_climate.async_set_setting('soft_band_c',0.7)
    assert r.smart_climate.settings['soft_band_c']==0.7
    assert r.entry.options['smart_climate']['soft_band_c']==0.7


@pytest.mark.asyncio
async def test_dashboard_setting_rejects_hard_band_below_soft_band():
    r,h=setup_climate(control=False)
    from homeassistant.exceptions import HomeAssistantError
    await r.smart_climate.async_set_setting('hard_band_c',1.5)
    await r.smart_climate.async_set_setting('soft_band_c',1.2)
    with pytest.raises(HomeAssistantError):
        await r.smart_climate.async_set_setting('hard_band_c',0.8)


@pytest.mark.asyncio
async def test_forecast_refresh_queues_weather_bias_training_points():
    r,h=setup_climate(control=False)
    now=datetime.now().astimezone()
    h.services.forecast=[{'datetime':(now.replace(minute=0,second=0,microsecond=0)+__import__('datetime').timedelta(hours=i)).isoformat(),'temperature':20+i*.01,'condition':'partlycloudy'} for i in range(1,55)]
    await r.smart_climate._refresh_forecast()
    assert r.smart_climate.state.weather_bias.pending


def test_climate_overview_contains_settings_findings_alerts_and_explanation():
    r,h=setup_climate(control=False)
    ov=r.smart_climate.overview()
    assert len(ov['settings_catalog']) == len(SMART_CLIMATE_DEFAULTS)
    assert 'weather_bias' in ov and 'solar_gain' in ov and 'coast_feedback' in ov
    assert isinstance(ov['alerts'],list)
    assert any('Open ramen' in x for x in ov['explanation'])


@pytest.mark.asyncio
async def test_changing_outside_temperature_source_resets_dependent_learned_models():
    r,h=setup_climate(control=False)
    h.states.set('sensor.outdoor2',20.5,{'unit_of_measurement':'°C'})
    mature(r.smart_climate)
    r.smart_climate.state.weather_bias.errors['12']=[1.0]*12
    r.smart_climate.state.weather_bias.days['12']={'d1','d2','d3','d4'}
    assert r.smart_climate.state.profiles
    await r.smart_climate.async_set_setting('outside_temp_entity','sensor.outdoor2')
    assert r.smart_climate.state.profiles == {}
    assert r.smart_climate.state.weather_bias.errors['12'] == []
    assert 'leren veilig opnieuw' in r.smart_climate.last_forecast_error
