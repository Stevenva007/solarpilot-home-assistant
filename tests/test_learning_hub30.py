"""Learning/source contracts. No real HA, cloud, hardware or actuator tests."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
import json
import time
import pytest
from test_runtime import build
from custom_components.solar_pilot.learning_hub import LearningHub, measured_baseline
from custom_components.solar_pilot.unified_planner import BaseLoadModel
from custom_components.solar_pilot.planner_quality import PlanQualityTracker


def metered():
    r, h = build(power=True, settings={'pv_entity': 'sensor.pv'})
    h.states.set('sensor.grid', -700, {'unit_of_measurement': 'W'})
    h.states.set('sensor.pv', 2500, {'unit_of_measurement': 'W'})
    h.states.set('sensor.load', 300, {'unit_of_measurement': 'W'})
    h.states.set('sensor.ev', 1300, {'unit_of_measurement': 'W'})
    r.wallbox_settings.update(enabled=True, power_entity='sensor.ev')
    st = r.states['a']; st.owned = st.on = st.available = True
    st.last_on = time.monotonic()-600; st.measured_w = 300
    return r, h


def sample(r):
    return measured_baseline(r, datetime.now(timezone.utc), time.monotonic())


def test_metered_load_and_ev_no_longer_remove_all_daytime_learning():
    r,h=metered();x=sample(r)
    assert x['valid'] and x['watts']==200 and x['old_rule_would_skip']
    assert not h.services.calls
    r.learning_hub.observe(datetime.now(timezone.utc),time.monotonic())
    assert r.unified_planner.base_load.accepted==1
    assert next(iter(r.learning_hub.days.values()))['accepted_corrected']==1


@pytest.mark.parametrize('field,value', [('sensor.pv','unavailable'),('sensor.grid','unknown'),('sensor.ev','nan'),('sensor.load','inf')])
def test_missing_sources_not_zeroes(field,value):
    r,h=metered();h.states.set(field,value,{'unit_of_measurement':'W'})
    x=sample(r);assert not x['valid'] and x['watts'] is None


@pytest.mark.parametrize('entity', ['sensor.grid','sensor.pv','sensor.ev','sensor.load'])
@pytest.mark.parametrize('unit', ['kWh','A','Wh',''])
def test_only_watts_or_kw_may_be_subtracted(entity,unit):
    r,h=metered();h.states.get(entity).attributes['unit_of_measurement']=unit
    assert not sample(r)['valid']


def test_kw_conversion_only_once_and_zero_load_is_valid():
    r,h=metered();h.states.set('sensor.ev',1.3,{'unit_of_measurement':'kW'})
    assert sample(r)['watts']==200
    h.states.set('sensor.grid',-900,{'unit_of_measurement':'W'})
    assert sample(r)['watts']==0


@pytest.mark.parametrize('kwargs',[{'age':1000},{'reported_age':1000},{'reported_age':-100}])
def test_stale_and_future_wallbox_measurement_rejects_learning(kwargs):
    r,h=metered();h.states.set('sensor.ev',1300,{'unit_of_measurement':'W'},**kwargs)
    assert not sample(r)['valid']


@pytest.mark.parametrize('attrs',[{'estimated':True},{'is_estimated':True},{'restored':True},{'friendly_name':'Afwasmachine geschat vermogen'}])
def test_estimates_are_not_used_as_exclusive_meter(attrs):
    r,h=metered();h.states.get('sensor.load').attributes.update(attrs)
    assert not sample(r)['valid']


def test_known_template_meter_rejected(monkeypatch):
    from homeassistant.helpers import entity_registry as er
    r,h=metered()
    monkeypatch.setattr(er,'async_get',lambda _:SimpleNamespace(async_get=lambda e:SimpleNamespace(platform='template' if e=='sensor.load' else 'shelly')))
    assert not sample(r)['valid']


@pytest.mark.parametrize('duplicate',['sensor.grid','sensor.pv','sensor.ev'])
def test_duplicate_meter_ref_never_double_subtracted(duplicate):
    r,h=metered();r.configs['a']['power_entity']=duplicate
    assert not sample(r)['valid']


def test_negative_residual_rejected_not_clipped_to_zero():
    r,h=metered();h.states.set('sensor.grid',-5000,{'unit_of_measurement':'W'})
    x=sample(r);assert not x['valid'] and x['code']=='balance' and x['watts'] is None


def test_new_start_settles_before_learning():
    r,h=metered();r.states['a'].last_on=time.monotonic()-20
    assert sample(r)['code']=='settling'
    r.states['a'].last_on=time.monotonic()-130
    assert sample(r)['valid']


@pytest.mark.parametrize('pending',['pending','handover'])
def test_no_learning_while_command_unconfirmed(pending):
    r,h=metered();setattr(r,pending,{'intent':'pending'})
    assert sample(r)['code']=='settling'


@pytest.mark.parametrize('sign,value',[('discharge_positive',100),('charge_positive',-100)])
def test_simple_signed_battery_no_false_base_inflation(sign,value):
    r,h=metered();r.settings.update(battery_power_entity='sensor.battery',battery_sign=sign)
    h.states.set('sensor.battery',value,{'unit_of_measurement':'W'})
    assert sample(r)['watts']==300
    assert not h.services.calls


def test_quiet_policy_still_available_and_no_permission_change():
    r,h=metered();before=deepcopy(r.settings);r.learning_hub.policy['sampling']='quiet'
    r.learning_hub.observe(datetime.now(timezone.utc),time.monotonic())
    assert r.unified_planner.base_load.accepted==0
    assert next(iter(r.learning_hub.days.values()))['quiet_policy']==1
    assert before==r.settings and not h.services.calls


def test_protected_context_scores_separately_and_does_not_train_normal_demand():
    r,h=metered()
    # The read-only monitor supplies native activity; no obsolete DHW writer
    # or clock-only sterilisation assumption is involved in this learning test.
    r.panasonic.overview=lambda: {'context':'sterilization', 'status':'Native sterilisation confirmed'}
    x=r.learning_hub.observe(datetime.now(timezone.utc),time.monotonic())
    assert x['valid'] and x['context']=='sterilization'
    assert r.unified_planner.base_load.accepted==0
    assert next(iter(r.learning_hub.days.values()))['heatpump_sterilization']==1
    q=PlanQualityTracker();q.observe(wall_ts=1000,local_now=datetime(2026,9,28,12),predicted_pv_w=1000,actual_pv_w=1000,predicted_base_w=200,actual_base_w=3200,context=x['context'])
    a=q.overview()['last_7d']
    assert a['base_mae_w'] is None
    assert a['protected_dhw_base_mae_w']==3000


def test_no_passive_store_write_before_runtime_load():
    r,h=metered();r.store.data={'old_data':'must stay'}
    r.learning_hub.observe(datetime.now(timezone.utc),time.monotonic());r.learning_hub.refresh()
    assert r.store.data=={'old_data':'must stay'}


def populated():
    m=BaseLoadModel();start=datetime(2026,8,1,10,tzinfo=timezone.utc)
    for i in range(60):
        day=start+timedelta(days=i)
        m.observe(day.timestamp(),day,500 if i<38 else 750)
    return m,start+timedelta(days=60)


def test_candidate_requires_optin_and_out_of_sample_improvement():
    m,day=populated();d=m.detail(day)
    assert d['candidate_eligible'] and d['validation_days']>=4 and not d['candidate_applied']
    v=m.estimate(day)[0];assert v==d['incumbent_w']
    m.adaptive_enabled=True
    d=m.detail(day);assert d['candidate_applied']
    assert d['incumbent_w']*.75 <= d['prediction_w'] <= d['incumbent_w']*1.25
    assert d['candidate_mae_w'] <= d['incumbent_mae_w']*.9


def test_insufficient_distinct_days_no_adaptation_or_confidence_pumping():
    m=BaseLoadModel();day=datetime(2026,9,29,10)
    for i in range(20):m.observe(1000+i*901,day,500)
    m.adaptive_enabled=True
    d=m.detail(day);assert d['days']==1 and not d['candidate_applied'] and d['confidence']==.1
    old=m.estimate(day)
    for _ in range(210):assert m.estimate(day)==old


def test_future_values_never_train_a_past_prediction():
    m,day=populated();old=m.detail(day)['prediction_w']
    later=day+timedelta(days=7);m.observe(later.timestamp(),later,10000)
    assert m.detail(day)['prediction_w']==old


def test_old_live_profile_expires_by_calendar_time():
    m,day=populated();late=day+timedelta(days=100)
    info=m.detail(late);assert info['days']==0 and 'fallback' in info['source']


def test_bad_recent_candidate_falls_back_even_when_automatic():
    m,day=populated();m.adaptive_enabled=True
    for i in range(20):
        x=day+timedelta(days=i);m.observe(x.timestamp(),x,500)
    info=m.detail(day+timedelta(days=20));assert not info['candidate_applied']


def test_snapshot_restores_data_without_invented_measurements():
    m,day=populated();n=BaseLoadModel();n.restore(m.snapshot())
    assert n.snapshot()==m.snapshot() and n.estimate(day)==m.estimate(day)


def test_legacy_quality_rows_do_not_gain_fake_daylight_or_coverage():
    q=PlanQualityTracker();q.restore({'days':{'2026-09-28':{'count':100,'pv_abs':10000,'pv_bias':-10000}}})
    v=q.overview()['last_7d'];assert v['pv_mae_w']==100
    assert v['pv_daylight_mae_w'] is None and v['covered_hours'] is None


def test_daylight_metric_excludes_both_night_zeroes_not_bad_solar_predictions():
    q=PlanQualityTracker();start=datetime(2026,9,29,1,tzinfo=timezone.utc)
    for i in range(12):q.observe(wall_ts=1000+i*301,local_now=start+timedelta(seconds=i*301),predicted_pv_w=0,actual_pv_w=0)
    q.observe(wall_ts=5000,local_now=start+timedelta(hours=2),predicted_pv_w=1500,actual_pv_w=0)
    v=q.overview()['last_7d'];assert v['pv_daylight_mae_w']==1500 and v['pv_daylight_samples']==1
    assert v['pv_mae_w']<1500 and v['pv_daylight_bias_w']==-1500


def test_coverage_does_not_fill_an_outage_or_restart():
    q=PlanQualityTracker();dt=datetime(2026,9,29,12,tzinfo=timezone.utc)
    for i in (0,301,602,10000):q.observe(wall_ts=1000+i,local_now=dt+timedelta(seconds=i),predicted_pv_w=1000,actual_pv_w=1100)
    assert q.overview()['last_7d']['covered_hours']==round(602/3600,2)
    saved=q.snapshot();q2=PlanQualityTracker();q2.restore(saved)
    q2.observe(wall_ts=11301,local_now=dt+timedelta(seconds=10301),predicted_pv_w=1000,actual_pv_w=1100)
    assert q2.overview()['last_7d']['covered_hours']==q.overview()['last_7d']['covered_hours']


def test_no_answer_means_no_new_prediction_permissions():
    r,h=build();hub=r.learning_hub;before=deepcopy(r.settings)
    for _ in range(10):hub.refresh(force=True)
    assert not r.unified_planner.base_load.adaptive_enabled
    assert hub.policy['adaptation']=='assisted' and before==r.settings and not h.services.calls
    assert any(q['id']=='adaptation' for q in hub.cached['questions'])


@pytest.mark.asyncio
async def test_answer_is_durable_no_devices_and_duplicate_refused():
    r,h=build();hub=r.learning_hub;q=next(q for q in hub.refresh()['questions'] if q['id']=='adaptation')
    original=deepcopy(r.settings);out=await hub.answer(q['id'],q['revision'],'auto')
    assert hub.policy['adaptation']=='automatic' and r.store.data['learning_hub']['policy']['adaptation']=='automatic'
    assert original==r.settings and not h.services.calls
    with pytest.raises(ValueError,match='stale_question'):await hub.answer(q['id'],q['revision'],'auto')
    r2,h2=build();r2.learning_hub.restore(r.store.data['learning_hub']);assert r2.unified_planner.base_load.adaptive_enabled


@pytest.mark.asyncio
async def test_old_revision_after_source_change_cannot_apply():
    r,h=build();q=r.learning_hub.refresh()['questions'][0];r.settings['grid_entity']='sensor.other'
    with pytest.raises(ValueError,match='stale_question'):await r.learning_hub.answer(q['id'],q['revision'],'auto')
    assert not r.unified_planner.base_load.adaptive_enabled and not h.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize('key,value',[('minimum_c',30),('control_enabled',True),('notifications','true'),('sampling','unsafe'),('adaptation',True),('grid_limit',99999)])
async def test_policy_endpoint_cannot_change_safety_or_permissions(key,value):
    r,h=build();before=r.learning_hub.snapshot()
    with pytest.raises(ValueError,match='invalid_policy'):await r.learning_hub.set_policy(key,value)
    assert before==r.learning_hub.snapshot() and not h.services.calls


@pytest.mark.asyncio
async def test_decline_remembered_no_repeated_popup_until_source_changes():
    r,h=build();hub=r.learning_hub;q=hub.refresh()['questions'][0]
    await hub.answer(q['id'],q['revision'],'keep')
    assert q['id'] not in [x['id'] for x in hub.refresh(force=True)['questions']]
    r.settings['grid_entity']='sensor.other'
    assert q['id'] in [x['id'] for x in hub.refresh(force=True)['questions']]


@pytest.mark.asyncio
async def test_notification_optin_deduplicated_and_separate_from_faults():
    r,h=build();hub=r.learning_hub;await hub.tick();assert not h.services.calls
    await hub.set_policy('notifications',True);await hub.tick();await hub.tick()
    assert len(h.services.calls)==1
    domain,action,data=h.services.calls[0];assert (domain,action)==('persistent_notification','create')
    assert data['notification_id']=='solar_pilot_learning_test'
    r.settings['grid_entity']='sensor.different';hub.refresh(force=True);await hub.tick()
    assert len(h.services.calls)==1  # no repeated notification inside 24 h


def test_export_includes_questions_models_and_answer_history():
    r,h=build();data=r.analysis.build(include_names=True)
    info=data['components']['learning_evidence_and_questions']
    assert len(info['models'])==8 and info['questions'] and info['policy']['adaptation']=='assisted'
    assert any(model['id']=='heatpump' for model in info['models'])
    assert 'coverage_note' in info['quality']['last_7d'] and not h.services.calls


def test_learner_counters_retained_60_days_and_fixed_size_audit():
    r,h=build();hub=r.learning_hub
    for i in range(200):hub._event('test',{'n':i})
    assert len(hub.audit)==150
    hub.restore({'days':{(datetime(2026,1,1)+timedelta(days=i)).date().isoformat():{'accepted':1} for i in range(200)}})
    assert len(hub.days)==60

@pytest.mark.asyncio
async def test_advisory_sampler_failure_does_not_pause_the_engine(monkeypatch):
    r,h=build();r.mode='observe'
    def fail(*args):raise RuntimeError('test learner failure')
    monkeypatch.setattr(r.learning_hub,'observe',fail)
    await r.tick()
    assert r.mode=='observe' and not r.problem and not h.services.calls
    assert 'Basislastanalyse overgeslagen' in r.learning_hub.error


def test_disabled_planner_and_phase_are_not_shown_as_collecting():
    r,h=build();r.planner_settings['enabled']=False;r.phase_settings['enabled']=False
    data=r.learning_hub.refresh()
    assert not next(m for m in data['models'] if m['id']=='base')['enabled']
    assert not next(m for m in data['models'] if m['id']=='phase')['enabled']
    assert any(q['id']=='base_disabled' for q in data['questions'])

@pytest.mark.asyncio
async def test_answered_questions_clear_only_own_notification():
    r,h=build();hub=r.learning_hub
    await hub.set_policy('notifications',True);await hub.tick()
    for q in list(hub.refresh()['questions']):await hub.answer(q['id'],q['revision'],'keep')
    await hub.tick()
    assert h.services.calls[-1]==('persistent_notification','dismiss',{'notification_id':'solar_pilot_learning_test'})
    assert not hub.notification_signature


def test_beta36_space_heating_is_not_learned_as_household_base():
    r,h=metered()
    r.panasonic.settings.update(zone_entities=['climate.zone'])
    h.states.set('climate.zone','auto',{'hvac_action':'heating'})
    x=r.learning_hub.observe(datetime.now(timezone.utc),time.monotonic())
    assert x['valid'] and x['context']=='space_heating'
    assert r.unified_planner.base_load.accepted==0
    counts=next(iter(r.learning_hub.days.values()))
    assert counts['heatpump_space_heating']==1


def test_beta36_unknown_high_residual_is_not_silently_added_to_base_profile():
    r,h=metered()
    # Seed a usable household bucket so the spike filter has evidence to compare.
    now=datetime.now(timezone.utc)
    key=r.unified_planner.base_load._key(now)
    r.unified_planner.base_load.bins[key]={'days':{
        (now-timedelta(days=d)).date().isoformat():[500.0] for d in range(1,6)
    }}
    h.states.set('sensor.grid',3000,{'unit_of_measurement':'W'})
    x=r.learning_hub.observe(now,time.monotonic())
    assert x['valid']
    assert x['context']=='heatpump_unknown'
    assert r.unified_planner.base_load.accepted==0
