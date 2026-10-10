"""Known shared Panasonic electrical watts remain read-only and undivided."""
from copy import deepcopy
import pytest
from custom_components.solar_pilot.heatpump_budget import heatpump_power
from test_runtime import build


def measured_heat_pump(*, scope="total", watts=2300):
    runtime, hass = build(power=True)
    runtime.panasonic.update_config({"power_entity": "sensor.boiler_power", "power_scope": scope,
                                    "stale_s": 300, "zone_entities": ["climate.home", "climate.salon"]})
    hass.states.set("sensor.boiler_power", watts, {"unit_of_measurement": "W"})
    return runtime, hass


@pytest.mark.parametrize("value,unit,watts", [(2300,"W",2300),(2.3,"kW",2300),(0,"W",0)])
def test_whole_heat_pump_meter_is_one_shared_total_not_per_room_power(value,unit,watts):
    runtime,hass=measured_heat_pump()
    hass.states.set("sensor.boiler_power",value,{"unit_of_measurement":unit})
    reading=heatpump_power(runtime);view=runtime.panasonic.overview()
    assert reading["valid"] and reading["watts"]==watts
    assert reading["meter_scope"]=="total" and reading["shared"]
    assert reading["measured_wall"]>0 and view["power_w"]==watts and view["power_kind"]=="measured"
    assert all("power" not in z and "power_w" not in z for z in view["zones"])
    assert hass.services.calls==[]


@pytest.mark.parametrize("scope",["supply1","supply2","unconfirmed"])
def test_partial_meter_does_not_claim_a_whole_heat_pump_total(scope):
    runtime,_=measured_heat_pump(scope=scope,watts=1450)
    reading=heatpump_power(runtime);view=runtime.panasonic.overview()
    assert reading["valid"] and reading["watts"]==1450
    assert reading["meter_scope"]==scope and view["power_scope"]==scope
    assert all("power_w" not in z for z in view["zones"])


@pytest.mark.parametrize("state,attributes,age",[
 (2300,{"restored":True},0),(2300,{"estimated":True},0),(2300,{"is_estimated":True},0),
 (2300,{"friendly_name":"Geschat warmtepompvermogen"},0),(2300,{},301),(2300,{},-6),
 (2300,{"unit_of_measurement":"kWh"},0),(-2300,{},0),("unavailable",{},0),
 ("unknown",{},0),("nan",{},0),("inf",{},0),
])
def test_untrusted_power_stays_unknown(state,attributes,age):
    runtime,hass=measured_heat_pump()
    hass.states.set("sensor.boiler_power",state,{"unit_of_measurement":"W",**attributes},age=age)
    reading=heatpump_power(runtime);view=runtime.panasonic.overview()
    assert not reading["valid"] and reading["watts"] is None and reading["measured_wall"] is None
    assert view["power_w"] is None and view["power_kind"]=="unknown"


@pytest.mark.parametrize("binding",["grid","pv","battery","wallbox","consumer"])
def test_reused_load_or_site_meter_is_not_a_heat_pump_total(binding):
    runtime,hass=measured_heat_pump();meter="sensor.boiler_power"
    if binding=="consumer":runtime.configs["a"]["power_entity"]=meter
    elif binding=="wallbox":runtime.wallbox_settings.update(enabled=False,power_entity=meter)
    else:runtime.settings[{"grid":"grid_entity","pv":"pv_entity","battery":"battery_power_entity"}[binding]]=meter
    assert not heatpump_power(runtime)["valid"]
    assert runtime.panasonic.overview()["power_w"] is None
    assert hass.services.calls==[]


def test_source_heartbeat_controls_freshness_even_if_watts_have_not_changed():
    runtime,hass=measured_heat_pump()
    hass.states.set("sensor.boiler_power",2300,{"unit_of_measurement":"W"},age=86400,reported_age=2)
    assert heatpump_power(runtime)["valid"]
    runtime.panasonic.settings["stale_s"]=1
    assert not heatpump_power(runtime)["valid"]


def test_invalid_presentation_timeout_does_not_extend_power_evidence():
    runtime,hass=measured_heat_pump()
    runtime.panasonic.update_config({**runtime.panasonic.settings,"stale_s":900})
    hass.states.set("sensor.boiler_power",2300,{"unit_of_measurement":"W"},age=400)
    assert runtime.panasonic.settings["stale_s"]<=600
    assert not heatpump_power(runtime)["valid"]


def test_missing_meter_never_substitutes_estimated_heat_pump_watts():
    runtime,_=measured_heat_pump()
    runtime.panasonic.settings.update(power_entity="",estimated_heat_power_w=3200)
    assert not heatpump_power(runtime)["valid"] and heatpump_power(runtime)["watts"] is None
    assert runtime.panasonic.overview()["power_w"] is None


def test_readonly_power_overviews_do_not_change_commands_ownership_or_policy():
    runtime,hass=measured_heat_pump();before=deepcopy(runtime._snapshot())
    for _ in range(3):runtime.panasonic.overview();heatpump_power(runtime)
    assert runtime._snapshot()==before and hass.services.calls==[]
