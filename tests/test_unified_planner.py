from datetime import datetime, timezone
from custom_components.solar_pilot.unified_planner import BaseLoadModel, UnifiedPlanner, UNIFIED_PLANNER_DEFAULTS


def dt(h=10):
    return datetime(2026,9,24,h,0,tzinfo=timezone.utc)


def test_base_load_seed_is_used_before_live_confidence():
    m=BaseLoadModel({'base_load_profile':{'median_w_by_hour':{'10':1234}}})
    v,c,src=m.estimate(dt(10))
    assert v==1234 and c>0 and 'bootstrap' in src


def test_base_load_live_profile_replaces_seed_after_distinct_days():
    m=BaseLoadModel({'base_load_profile':{'median_w_by_hour':{'10':500}}})
    for day in range(1,6):
        x=datetime(2026,9,day,10,0,tzinfo=timezone.utc)
        m.observe(day*100000,x,1500+day,contaminated=False)
    v,c,src=m.estimate(dt(10),min_days=4)
    assert v>1400 and c>0.3 and src.startswith('live')


def test_contaminated_samples_do_not_train_baseline():
    m=BaseLoadModel()
    assert not m.observe(1000,dt(),4000,contaminated=True)
    assert m.accepted==0


def test_unified_planner_prefers_solar_slots_for_flexible_goal():
    p=UnifiedPlanner({**UNIFIED_PLANNER_DEFAULTS,'horizon_h':6,'slot_min':60}, {'base_load_profile':{'median_w_by_hour':{str(h):500 for h in range(24)}}})
    pv=[0,0,5000,5000,0,0]
    dev=[{'id':'a','name':'Load','priority':10,'enabled':True,'forecast_deferrable':True,'required_kwh':2,'power_w':1000,'daily_deadline':'23:59:00','cheap_grid_allowed':False,'deadline_grid_allowed':False,'time_window_enabled':False}]
    plan=p.build(local_now=dt(10),pv_hourly_w=pv,import_prices=[.3]*6,export_prices=[.03]*6,devices=dev)
    assert plan.devices['a'].planned_kwh>=2
    assert set(plan.devices['a'].selected_slots).issubset({2,3})


def test_unified_planner_respects_time_window_and_deadline():
    p=UnifiedPlanner({**UNIFIED_PLANNER_DEFAULTS,'horizon_h':8,'slot_min':60}, {'base_load_profile':{'median_w_by_hour':{str(h):300 for h in range(24)}}})
    dev=[{'id':'a','name':'Load','priority':10,'enabled':True,'forecast_deferrable':True,'required_kwh':2,'power_w':1000,'daily_deadline':'14:59:00','cheap_grid_allowed':True,'deadline_grid_allowed':True,'time_window_enabled':True,'time_window_start':'12:00:00','time_window_end':'15:00:00'}]
    plan=p.build(local_now=dt(10),pv_hourly_w=[5000]*8,import_prices=[.3]*8,export_prices=[.03]*8,devices=dev)
    hours=[plan.slots[i].start.hour for i in plan.devices['a'].selected_slots]
    assert hours and all(12<=h<15 for h in hours)


def test_price_optimisation_prefers_cheaper_grid_block_when_allowed():
    p=UnifiedPlanner({**UNIFIED_PLANNER_DEFAULTS,'horizon_h':4,'slot_min':60,'early_grid_enabled':True,'price_optimisation':True}, {'base_load_profile':{'median_w_by_hour':{str(h):500 for h in range(24)}}})
    dev=[{'id':'a','name':'Load','priority':10,'enabled':True,'forecast_deferrable':True,'required_kwh':1,'power_w':1000,'daily_deadline':'23:59:00','cheap_grid_allowed':True,'deadline_grid_allowed':True,'time_window_enabled':False}]
    plan=p.build(local_now=dt(10),pv_hourly_w=[0]*4,import_prices=[.4,.1,.3,.2],export_prices=[.03]*4,devices=dev)
    assert plan.devices['a'].selected_slots==[1]
    assert plan.devices['a'].cheap_grid_slots==[1]


def test_price_optimisation_off_prefers_earlier_equivalent_grid_block():
    p=UnifiedPlanner({**UNIFIED_PLANNER_DEFAULTS,'horizon_h':4,'slot_min':60,'early_grid_enabled':True,'price_optimisation':False}, {'base_load_profile':{'median_w_by_hour':{str(h):500 for h in range(24)}}})
    dev=[{'id':'a','name':'Load','priority':10,'enabled':True,'forecast_deferrable':True,'required_kwh':1,'power_w':1000,'daily_deadline':'23:59:00','cheap_grid_allowed':True,'deadline_grid_allowed':True,'time_window_enabled':False}]
    plan=p.build(local_now=dt(10),pv_hourly_w=[0]*4,import_prices=[.4,.1,.3,.2],export_prices=[.03]*4,devices=dev)
    assert plan.devices['a'].selected_slots==[0]


def test_capacity_penalty_can_steer_away_from_high_base_slot():
    seed={'base_load_profile':{'median_w_by_hour':{'10':4000,'11':500,'12':500,'13':500}}}
    p=UnifiedPlanner({**UNIFIED_PLANNER_DEFAULTS,'horizon_h':4,'slot_min':60,'early_grid_enabled':True,'capacity_penalty_enabled':True,'capacity_penalty_eur_kwh':2},seed)
    dev=[{'id':'a','name':'Load','priority':10,'enabled':True,'forecast_deferrable':True,'required_kwh':1,'power_w':1000,'daily_deadline':'23:59:00','cheap_grid_allowed':True,'deadline_grid_allowed':True,'time_window_enabled':False}]
    plan=p.build(local_now=dt(10),pv_hourly_w=[0]*4,import_prices=[.1]*4,export_prices=[.03]*4,devices=dev,capacity_target_w=3500)
    assert plan.devices['a'].selected_slots[0] != 0


def test_current_device_state_explains_future_wait():
    p=UnifiedPlanner({**UNIFIED_PLANNER_DEFAULTS,'horizon_h':4,'slot_min':60}, {'base_load_profile':{'median_w_by_hour':{str(h):500 for h in range(24)}}})
    dev=[{'id':'a','name':'Load','priority':10,'enabled':True,'forecast_deferrable':True,'required_kwh':1,'power_w':1000,'daily_deadline':'23:59:00','cheap_grid_allowed':False,'deadline_grid_allowed':False,'time_window_enabled':False}]
    plan=p.build(local_now=dt(10),pv_hourly_w=[0,0,5000,0],import_prices=[.3]*4,export_prices=[.03]*4,devices=dev)
    run,grid,reason=plan.current_device_state('a',dt(10))
    assert not run and not grid and 'wacht' in reason.lower()


def test_battery_is_advisory_and_does_not_change_device_permissions():
    p=UnifiedPlanner({**UNIFIED_PLANNER_DEFAULTS,'horizon_h':4,'slot_min':60,'battery_advisory':True}, {'base_load_profile':{'median_w_by_hour':{str(h):500 for h in range(24)}}})
    plan=p.build(local_now=dt(10),pv_hourly_w=[4000,4000,0,0],import_prices=[.3]*4,export_prices=[.03]*4,devices=[],battery={'available_kwh':10,'soc_pct':20,'power_w':3000,'min_soc_pct':20,'max_soc_pct':95})
    assert any(s.battery_w>0 for s in plan.slots)
    assert 'batterijadvies' in ' '.join(plan.findings).lower()


def test_non_interruptible_cycle_is_planned_contiguously():
    p=UnifiedPlanner({**UNIFIED_PLANNER_DEFAULTS,'horizon_h':8,'slot_min':30}, {'base_load_profile':{'median_w_by_hour':{str(h):300 for h in range(24)}}})
    dev=[{'id':'dish','name':'Dish','priority':10,'enabled':True,'forecast_deferrable':True,'required_kwh':.8,'power_w':1800,
          'daily_deadline':'18:00:00','cheap_grid_allowed':False,'deadline_grid_allowed':False,'time_window_enabled':False,
          'contiguous_cycle':True,'cycle_program':'Eco','cycle_confidence':.8,'cycle_duration_min':90,'cycle_average_w':534,'cycle_peak_w':1900}]
    plan=p.build(local_now=dt(10),pv_hourly_w=[0,5000,5000,5000,0,0,0,0],import_prices=[.3]*16,export_prices=[.03]*16,devices=dev)
    slots=plan.devices['dish'].selected_slots
    assert len(slots)==3
    assert slots==list(range(slots[0],slots[0]+3))
    assert plan.devices['dish'].contiguous_cycle


def test_protected_cycle_without_duration_is_not_fragmented_or_guessed():
    p=UnifiedPlanner({**UNIFIED_PLANNER_DEFAULTS,'horizon_h':8,'slot_min':30}, {'base_load_profile':{'median_w_by_hour':{str(h):300 for h in range(24)}}})
    dev=[{'id':'dish','name':'Dish','priority':10,'enabled':True,'forecast_deferrable':True,'required_kwh':.8,'power_w':1800,
          'daily_deadline':'18:00:00','cheap_grid_allowed':False,'deadline_grid_allowed':False,'time_window_enabled':False,
          'contiguous_cycle':True,'cycle_program':'Eco','cycle_confidence':0,'cycle_duration_min':0,'cycle_average_w':0,'cycle_peak_w':1800}]
    plan=p.build(local_now=dt(10),pv_hourly_w=[5000]*8,import_prices=[.3]*16,export_prices=[.03]*16,devices=dev)
    assert plan.devices['dish'].selected_slots == []
    assert plan.devices['dish'].planned_kwh == 0
    assert 'duur' in plan.devices['dish'].reason.lower()


def test_recent_replay_is_cached_between_dashboard_reads():
    p=UnifiedPlanner({**UNIFIED_PLANNER_DEFAULTS,'horizon_h':6,'slot_min':15,'replay_enabled':True}, {'base_load_profile':{'median_w_by_hour':{str(h):500 for h in range(24)}}})
    start=datetime(2026,9,20,0,0,tzinfo=timezone.utc)
    for day in range(2):
        for slot in range(96):
            now=start+__import__('datetime').timedelta(days=day,minutes=slot*15)
            p.replay.observe(local_now=now,pv_w=2000,base_w=500,grid_w=-1500,import_price=.3,export_price=.03,capacity_target_w=3500)
    devices=[{'id':'a','name':'Load','priority':10,'enabled':True,'forecast_deferrable':True,'daily_energy_goal_kwh':1.0,'power_w':1000,
              'daily_deadline':'23:59:00','cheap_grid_allowed':False,'deadline_grid_allowed':False,'time_window_enabled':False}]
    a=p.replay_scenarios(devices)
    b=p.replay_scenarios(devices)
    assert a is b
    assert a['ready']


def test_running_protected_cycle_is_reserved_before_new_flex_loads():
    p=UnifiedPlanner({**UNIFIED_PLANNER_DEFAULTS,'horizon_h':4,'slot_min':30,'early_grid_enabled':True}, {'base_load_profile':{'median_w_by_hour':{str(h):400 for h in range(24)}}})
    devices=[
      {'id':'dish','name':'Dish','priority':5,'enabled':True,'forecast_deferrable':True,'fixed_active_cycle':True,
       'active_cycle_remaining_min':75,'active_cycle_average_w':600,'cycle_program':'Eco','cycle_confidence':.8,'cycle_duration_min':90},
      {'id':'flex','name':'Flex','priority':10,'enabled':True,'forecast_deferrable':True,'required_kwh':.5,'power_w':1000,
       'daily_deadline':'23:59:00','cheap_grid_allowed':True,'deadline_grid_allowed':True,'time_window_enabled':False},
    ]
    plan=p.build(local_now=dt(10),pv_hourly_w=[2000]*4,import_prices=[.3]*8,export_prices=[.03]*8,devices=devices)
    assert plan.devices['dish'].selected_slots == [0,1,2]
    assert all('dish' in plan.slots[i].devices for i in [0,1,2])
    assert plan.slots[0].planned_load_w >= 600


def test_beta36_heatpump_context_is_not_written_into_household_replay():
    p=UnifiedPlanner({**UNIFIED_PLANNER_DEFAULTS,'replay_enabled':True})
    now=datetime(2026,10,1,12,0,tzinfo=timezone.utc)
    p.observe_actual(wall_ts=1_000_000,local_now=now,actual_pv_w=2000,
                     actual_base_w=3200,actual_grid_w=1200,context='space_heating')
    assert p.replay.samples=={}
    p.observe_actual(wall_ts=1_000_301,local_now=now,actual_pv_w=2000,
                     actual_base_w=700,actual_grid_w=-1300,context='normal')
    assert len(p.replay.samples)==1
    assert next(iter(p.replay.samples.values()))['base_w']==700
