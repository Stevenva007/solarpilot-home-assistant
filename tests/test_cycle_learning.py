from custom_components.solar_pilot.cycle_learning import CycleEnergyModel


def test_complete_cycles_learn_energy_duration_and_peak():
    m=CycleEnergyModel()
    for day in range(1,5):
        start=day*100000
        m.begin('dish','Eco',start,f'2026-09-{day:02d}')
        for _ in range(60):
            m.observe('dish',600,60)
        for _ in range(5):
            m.observe('dish',1800,60)
        sample=m.finish('dish',start+65*60)
        assert sample is not None
    e=m.estimate('dish','Eco')
    assert e.energy_kwh>0.6
    assert e.duration_min>=60
    assert e.peak_w>=1700
    assert e.confidence>=0.45
    assert e.days==4


def test_partial_or_short_cycle_is_not_learned():
    m=CycleEnergyModel(); m.begin('x','Quick',1000,'2026-09-01')
    m.observe('x',1000,30)
    assert m.finish('x',1060) is None
    assert m.accepted==0 and m.rejected==1


def test_fallback_cycle_profile_before_learning():
    m=CycleEnergyModel()
    e=m.estimate('x','Eco',fallback_energy_kwh=.8,fallback_duration_min=90,fallback_peak_w=2000)
    assert e.energy_kwh==.8
    assert e.duration_min==90
    assert e.source.startswith('ingestelde')
