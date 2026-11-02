"""Actual Marstek form and frontend with fictitious Home Assistant sensors."""
import ast
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace as NS
from uuid import uuid4

import pytest

from custom_components.solar_pilot.battery_fleet import BATTERY_DEFAULTS, BATTERY_FLEET_DEFAULTS
from custom_components.solar_pilot.battery_profiles import MARSTEK_PROFILE, normalize_battery_config, battery_source_error
from test_audit_ui79 import execute


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def flow(monkeypatch):
    path = ROOT / "custom_components/solar_pilot/config_flow.py"
    tree = ast.parse(path.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == "SolarPilotOptions")
    cls.bases = []
    cls.keywords = []
    env = dict(__name__="custom_components.solar_pilot.config_flow",
        __package__="custom_components.solar_pilot", deepcopy=deepcopy, uuid4=uuid4, BATTERY_DEFAULTS=BATTERY_DEFAULTS,
        BATTERY_FLEET_DEFAULTS=BATTERY_FLEET_DEFAULTS, MARSTEK_PROFILE=MARSTEK_PROFILE,
        normalize_battery_config=normalize_battery_config, battery_source_error=battery_source_error,
        merged_site=lambda values: values,
        vol=NS(Required=lambda key, **kw: key, Schema=lambda data: data),
        selector=NS(BooleanSelector=lambda: "bool", TextSelector=lambda: "text", SelectSelector=lambda values: values),
        optional=lambda key, values: key, entity=lambda domains: domains)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), str(path), "exec"), env)

    class Flow(env["SolarPilotOptions"]):
        def _base_options(self):
            return self.options

        def async_show_form(self, **kwargs):
            return kwargs

        def async_show_menu(self, **kwargs):
            return kwargs

        async def _save(self, options):
            self.saved = options
            return {"saved": options}

    f = Flow()
    f.config_entry = NS(data={"grid_entity": "sensor.fixture_grid", "pv_entity": "sensor.fixture_pv"})
    f.options = {"batteries": [], "battery_fleet": {"control_enabled": True}, "untouched": {"keep": True}}
    f.saved = None
    f.reads = []
    f.states = {
        "sensor.fixture_ac": NS(state="0", attributes={"unit_of_measurement": "W"}),
        "sensor.fixture_soc": NS(state="11", attributes={"unit_of_measurement": "%"}),
        "sensor.fixture_car_soc": NS(state="30", attributes={"unit_of_measurement": "%"}),
        "sensor.fixture_grid": NS(state="100", attributes={"unit_of_measurement": "W"}),
        "sensor.fixture_pv": NS(state="1000", attributes={"unit_of_measurement": "W"}),
    }

    def read(entity):
        f.reads.append(entity)
        return f.states.get(entity)

    def forbidden(*args, **kwargs):
        raise AssertionError("A monitor form must not discover sources or operate devices")

    f.hass = NS(states=NS(get=read, async_all=forbidden), services=NS(async_call=forbidden, call=forbidden))
    from homeassistant.helpers import entity_registry as er
    monkeypatch.setattr(er, "async_get", lambda hass: NS(async_get=lambda entity:
        NS(platform="wallbox" if entity == "sensor.fixture_car_soc" else "marstek")))
    return f


def inputs(**changes):
    return {"name": "Fictional Venus", "power_entity": "sensor.fixture_ac",
            "power_sign": "discharge_positive", "ac_power_confirmed": True, **changes}


@pytest.mark.asyncio
async def test_monitor_form_has_only_explicit_sources_and_no_control_adapter(flow):
    before = deepcopy(flow.options)
    menu = await flow.async_step_battery()
    result = await flow.async_step_battery_marstek()
    assert "battery_marstek" in menu["menu_options"]
    assert set(result["data_schema"]) == {"name", "power_entity", "power_sign", "ac_power_confirmed", "soc_entity", "phase_hint"}
    assert flow._battery.get("power_sign") == ""
    assert flow.reads == [] and flow.saved is None and flow.options == before


@pytest.mark.asyncio
async def test_saving_monitor_enables_reading_preserves_other_permissions_and_strips_posted_actuators(flow):
    await flow.async_step_battery_marstek()
    result = await flow.async_step_battery_marstek(inputs(control_kind="signed_number", control_enabled=True,
        exclusive_control_confirmed=True, number_entity="number.fixture_forbidden", charge_script="script.fixture_forbidden",
        profile="generic", capacity_kwh=100, soc_entity="sensor.fixture_soc"))
    assert "saved" in result
    battery = result["saved"]["batteries"][0]
    assert battery["profile"] == MARSTEK_PROFILE and battery["control_kind"] == "read_only"
    assert battery["capacity_kwh"] == 5.12
    assert not battery["control_enabled"] and not battery["exclusive_control_confirmed"]
    assert not {"number_entity", "number_sign", "charge_script", "discharge_script", "idle_script"} & battery.keys()
    assert result["saved"]["battery_fleet"]["enabled"]
    assert result["saved"]["battery_fleet"]["control_enabled"]  # Unrelated batteries keep their choice.
    assert result["saved"]["untouched"] == {"keep": True}


@pytest.mark.asyncio
async def test_editing_monitor_and_direct_control_route_stay_in_the_compact_form(flow):
    await flow.async_step_battery_marstek()
    result = await flow.async_step_battery_marstek(inputs())
    flow.options = result["saved"]
    battery = flow.options["batteries"][0]
    edited = await flow.async_step_battery_edit({"battery_id": battery["id"]})
    assert edited["step_id"] == "battery_marstek"
    direct = await flow.async_step_battery_control()
    assert direct["step_id"] == "battery_marstek" and "number_entity" not in direct["data_schema"]


@pytest.mark.asyncio
@pytest.mark.parametrize("change", [
    {"power_sign": ""}, {"power_sign": None}, {"power_sign": []},
    {"power_entity": "sensor.fixture_grid"}, {"power_entity": "sensor.fixture_pv"},
    {"soc_entity": "sensor.fixture_car_soc"}, {"power_entity": "input_number.fixture_ac"},
])
async def test_ambiguous_or_non_battery_sources_cannot_be_saved(flow, change):
    await flow.async_step_battery_marstek()
    result = await flow.async_step_battery_marstek(inputs(**change))
    assert result["errors"] and flow.saved is None


@pytest.mark.asyncio
async def test_soc_optional_and_scope_confirmation_requires_literal_true(flow):
    await flow.async_step_battery_marstek()
    result = await flow.async_step_battery_marstek(inputs(ac_power_confirmed="true"))
    assert result["errors"] == {"ac_power_confirmed": "battery_ac_confirmation"}
    assert flow.saved is None and flow._battery["ac_power_confirmed"] is False
    result = await flow.async_step_battery_marstek(inputs())
    assert result["saved"]["batteries"][0]["soc_entity"] == ""


def render(**changes):
    battery = {"id": "fictional", "name": "Fictional Venus", "profile": MARSTEK_PROFILE,
        "power_valid": True, "soc_valid": True, "power_w": 0, "soc_pct": 11,
        "power_stamp": 1800000000, "soc_stamp": 1800000000, "stale_s": 120, **changes}
    return execute("""
Date.now=()=>1800000000000;
const card=Object.create(SolarPilotCard.prototype),b=%s;
card._sourceHistoryButton=()=>'';
card._hass={callService:()=>{throw Error('No control allowed');}};
const fleet={enabled:true,control_enabled:true,reason:'Unrelated advisory target',batteries:[b],aggregate:{power_w:9999,soc_pct:99}};
const storage=card._storage({batteryFleet:fleet,batteryAnalysis:{enabled:true,scenarios:[{power_kw:5}]}});
const explanation=card._overviewBatteryExplanation(fleet);
console.log(JSON.stringify({storage,explanation,reading:card._marstekReading(b)}));
""" % json.dumps(battery))


@pytest.mark.parametrize("power,label", [(-1200, "Laden"), (1200, "Ontladen"), (0, "Rust")])
def test_monitor_displays_actual_direction_without_advice_or_controls(power, label):
    result = render(power_w=power)
    assert result["reading"]["state"] == label
    assert "Alleen monitoren · Marstek regelt zelf" in result["storage"]
    assert "11%" in result["storage"] and label in result["storage"]
    for forbidden in ["BEDIENING TOEGESTAAN", "Batterijscenario", "Advies voor", "Unrelated advisory", "bestuurbaar"]:
        assert forbidden not in result["storage"] + result["explanation"]


@pytest.mark.parametrize("changes", [
    {"power_valid": False}, {"power_w": None}, {"power_w": True},
    {"power_stamp": 1799999879}, {"power_stamp": 1800000006}, {"power_stamp": None},
])
def test_missing_stale_or_invalid_power_stays_unknown(changes):
    result = render(**changes)
    assert result["reading"]["state"] == "Onbekend" and result["reading"]["power"] is None
    assert "Onbekend" in result["storage"] and "11%" in result["storage"]


def test_stale_soc_does_not_hide_valid_charging_and_markup_is_escaped():
    result = render(power_w=-500, soc_stamp=1799999879, name='<img src=x onerror="bad()">')
    assert result["reading"]["state"] == "Laden" and result["reading"]["soc"] is None
    assert "Onbekend" in result["storage"] and "500 W" in result["storage"]
    assert "<img" not in result["storage"] and "&lt;img" in result["storage"]
