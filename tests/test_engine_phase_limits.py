from custom_components.solar_pilot.engine import Device, State, Site, plan


def d(id, nominal=1000, priority=1):
    return Device(id=id,name=id,nominal_w=nominal,min_on_s=0,min_off_s=0,start_delay_s=0,stop_delay_s=0,start_margin_w=0,priority=priority)


def test_per_device_phase_limit_blocks_only_that_device():
    site=Site(now=100,grid_w=-2000,filtered_grid_w=-2000,reserve_w=0,device_increase_limits={"a":500,"b":2000})
    out=plan(site,[d("a",1000,1),d("b",1000,2)],{"a":State(),"b":State()})
    assert out.action and out.action.id=="b"


def test_per_device_phase_limit_allows_device_that_fits():
    site=Site(now=100,grid_w=-2000,filtered_grid_w=-2000,reserve_w=0,device_increase_limits={"a":1200})
    out=plan(site,[d("a",1000)],{"a":State()})
    assert out.action and out.action.watts==1000
