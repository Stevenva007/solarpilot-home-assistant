from custom_components.solar_pilot.phase_learning import PhaseLearning, phase_allocation_from_hint, phase_total_headroom_w


def settings():
    return {"learning_enabled":True,"learning_min_delta_w":200,"learning_settle_s":5,"learning_max_window_s":60,"learning_min_samples":3,"use_learned_device_map":False,"learning_min_confidence":.7}


def test_controlled_event_learns_l3():
    p=PhaseLearning(settings())
    for n in range(5):
        p.begin_controlled("load",n*100,(300,200,400),0)
        p.observe(now=n*100+6,day=f"2026-09-{n+1:02d}",phase_values=(320,220,1420),device_powers={"load":1000})
    prof=p.profile("load")
    assert prof["classification"]=="L3" and prof["confidence"]>.7


def test_passive_event_requires_isolated_device_change():
    p=PhaseLearning(settings())
    p.observe(now=0,day="d1",phase_values=(100,100,100),device_powers={"a":0,"b":0})
    p.observe(now=10,day="d1",phase_values=(1100,100,100),device_powers={"a":1000,"b":0})
    assert p.profile("a")["samples"]==1
    p.observe(now=20,day="d1",phase_values=(2100,1100,100),device_powers={"a":2000,"b":1000})
    assert p.profile("a")["samples"]==1


def test_manual_phase_hint_wins():
    shares, source=phase_allocation_from_hint("l2",{"classification":"L3","confidence":.99})
    assert shares==(0,1,0) and source=="handmatig"


def test_low_confidence_learning_not_used_for_control():
    shares, source=phase_allocation_from_hint("auto",{"classification":"L3","confidence":.5},.75)
    assert shares is None and source=="leren"


def test_phase_headroom_respects_relevant_phase():
    assert phase_total_headroom_w((1000,3000,500),5000,(0,1,0))==2000
    assert phase_total_headroom_w((1000,3000,500),5000,(1/3,1/3,1/3))==6000
