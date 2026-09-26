from custom_components.solar_pilot.learning import LocalLearning, fingerprint


def test_no_adaptation_until_five_confirmed_transfers():
    l=LocalLearning()
    for _ in range(4): l.record_handover(True, 220)
    assert l.effective_stable_s(180)==180
    l.record_handover(True, 220)
    assert l.effective_stable_s(180)==250


def test_learning_never_shortens_configured_wait():
    l=LocalLearning()
    for _ in range(5): l.record_handover(True, 20)
    assert l.effective_stable_s(180)==180


def test_learning_caps_suggested_wait_but_keeps_larger_user_floor():
    l=LocalLearning()
    for _ in range(5): l.record_handover(True, 1000)
    assert l.effective_stable_s(180)==600
    assert l.effective_stable_s(1800)==1800


def test_disabled_learning_is_fixed_and_collects_nothing_new():
    l=LocalLearning()
    for _ in range(5): l.record_handover(True, 220)
    l.enabled=False
    l.record_handover(True, 30); l.observe_report(100); l.observe_device('a',{'power_entity':'sensor.a'},1000,0,1000)
    assert len(l.responses)==5 and not l.profiles and l.last_wallbox_stamp is None
    assert l.effective_stable_s(180)==180


def test_failed_transfers_not_reinterpreted_as_successful_response_samples():
    l=LocalLearning(); l.record_handover(False,240)
    assert l.failures==1 and len(l.responses)==0


def test_repeated_report_timestamps_are_not_new_samples():
    l=LocalLearning()
    for t in (1000,1000,1000,1090,1090,1180): l.observe_report(t)
    assert list(l.report_intervals)==[90,90]


def test_device_profile_requires_new_report_and_separation():
    l=LocalLearning(); c={'power_entity':'sensor.load'}
    l.observe_device('a',c,1000,0,1000)
    l.observe_device('a',c,900,10,1010)
    l.observe_device('a',c,1100,60,1000)
    l.observe_device('a',c,1050,65,1065)
    assert l.overview(180)['profiles']['a']['samples']==2


def test_device_replacement_invalidates_profile_and_deleted_devices_are_pruned():
    l=LocalLearning(); c={'power_entity':'sensor.load'}
    l.observe_device('a',c,1000,0,1000)
    data=l.snapshot(); m=LocalLearning(); m.restore(data, {'a':{'power_entity':'sensor.new'}})
    assert m.profiles=={}
    m.restore(data,{})
    assert m.profiles=={}


def test_restore_and_reset_keep_user_switch_semantics():
    l=LocalLearning(); l.enabled=False; l.record_handover(True,100)
    l.enabled=True; l.record_handover(True,100); l.enabled=False
    m=LocalLearning(); m.restore(l.snapshot(),{})
    assert not m.enabled and list(m.responses)==[100]
    m.reset()
    assert not m.enabled and not m.responses


def test_storage_is_bounded():
    l=LocalLearning()
    c={'power_entity':'sensor.load'}
    for n in range(300):
        l.record_handover(True,100)
        l.observe_device('a',c,1000,n*61,1000+n*61)
    assert len(l.responses)==40 and len(l.profiles['a']['watts'])==120


def test_conservative_power_requires_samples_never_lowers_and_is_capped():
    l=LocalLearning(); cfg={'power_entity':'sensor.load','nominal_w':1000}
    l.profiles['a']={'fingerprint':fingerprint(cfg),'watts':[800]*9,'last_mono':0,'last_stamp':0}
    assert l.conservative_power('a',cfg,10,2)==1000
    l.profiles['a']['watts']=[700,800,900,1000,1100,1200,1300,1400,1500,1600]
    assert l.conservative_power('a',cfg,10,2) >= 1000
    l.profiles['a']['watts']=[5000]*10
    assert l.conservative_power('a',cfg,10,1.5)==1500
    l.profiles['a']['watts']=[100]*10
    assert l.conservative_power('a',cfg,10,2)==1000
