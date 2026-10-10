"""Exercise shipped SG UI/API boundaries; no live hardware acceptance implied."""
import ast
import json
from pathlib import Path
import shutil
import subprocess
import time
from types import SimpleNamespace

import pytest

from test_overview_details60 import Markup
from test_electricity_sensor import sensor_class

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "custom_components/solar_pilot/frontend/solar-pilot-card.js"


def attributes(**boost):
    observed_at = time.time()
    return {"mode": "solar", "config_entry_id": "example", "devices": [],
            "panasonic": {"configured": True, "temperature_c": 48, "target_c": 50,
                "power_w": 3700, "power_kind": "measured", "power_scope": "total",
                "source_stale_s": 120, "temperature_stamp": observed_at,
                "target_stamp": observed_at, "context_stamp": observed_at,
                "power_stamp": observed_at, "power_observed_at": observed_at,
                "compressor_stamp": observed_at, "sg_status_stamp": observed_at,
                "power_supply1_observed_at": observed_at, "power_supply2_observed_at": observed_at,
                "zones": [{"name": "Ruimte", "current": 21, "target": 21, "mode": "auto", "action": "idle", "observed_at": observed_at}]},
            "sg_boost": {"configured": True, "enabled": True, "state": "waiting",
                "reason": "Wacht op voldoende stabiel zonneoverschot", "desired_on": False,
                "relay_on": False, "relay_confirmed": True, "panasonic_confirmed": None,
                "observed_at": observed_at, "relay_observed_at": observed_at, "relay_stale_s": 120,
                "switch_entity": "switch.physical_sg_output", "enabled_entity": "switch.example_sg_enabled", "resume_entity": "button.example_sg_resume",
                "start_threshold_w": 3000, "estimated_power_w": 3200, **boost}}


def execute(data, *, view="comfort", actions=()):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for actual frontend execution")
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},input};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
vm.runInContext(`(async()=>{
  const calls=[],card=Object.create(SolarPilotCard.prototype);
  card._last={attributes:input.attributes};card._busy=false;card._error='';
  card._hass={states:{},config:{time_zone:'Europe/Brussels'},callService:async(domain,service,data)=>calls.push({domain,service,data})};
  card._render=()=>{};window.confirm=()=>true;
  const render=()=>input.view==='board'?card._decisionBoard(card._ctx()):card._comfort(card._ctx());
  const initial=render();
  for(const action of input.actions){
    if(action.kind==='change')await card._change({target:{dataset:action.dataset,value:'60',checked:true,checkValidity:()=>true}});
    else await card._click({target:{closest:()=>({disabled:false,dataset:{action:action.action||action}})}});
  }
  return {initial,final:render(),calls,error:card._error,feedback:card._feedback};
})()`,sandbox).then(result=>process.stdout.write(JSON.stringify(result))).catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
"""
    completed = subprocess.run([node, "-e", script, str(CARD)],
        input=json.dumps({"attributes": data, "view": view, "actions": actions}), text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def text(html):
    return Markup(html).root.text()


def test_compact_heatpump_has_one_sg_switch_and_no_panasonic_controls():
    result = execute(attributes())
    root = Markup(result["initial"]).root
    switches = [n for n in root.walk() if n.attributes.get("role") == "switch"]
    assert len(switches) == 1 and switches[0].attributes["aria-label"] == "Automatische zonneboost"
    assert "Warmtepomp — Panasonic-regeling" in text(result["initial"])
    assert "Wacht op voldoende stabiel zonneoverschot" in text(result["initial"])
    assert "50 °C" in text(result["initial"]) and "48 °C" in text(result["initial"])
    assert not result["calls"]
    assert not any(n.attributes.get("data-action", "").startswith(("dhw_", "climate_")) for n in root.walk())
    assert not any("data-dhw-setting" in n.attributes or "data-climate-setting" in n.attributes for n in root.walk())


@pytest.mark.parametrize("view", ["comfort", "board"])
def test_relay_feedback_is_never_presented_as_panasonic_confirmation(view):
    data = attributes(desired_on=True, relay_on=True, relay_confirmed=True,
                      reason="SG-contact actief; Panasonic-reactie niet afzonderlijk bevestigd")
    result = execute(data, view=view)
    rendered = text(result["initial"])
    assert "SG-contact actief; Panasonic-reactie niet afzonderlijk bevestigd" in rendered
    assert "Niet afzonderlijk bevestigd" in rendered
    assert "50 °C" in rendered  # unchanged native target does not become a fault
    assert "Boilercontrole" not in rendered and "niet bevestigde boileropdracht" not in rendered
    assert not result["calls"]


@pytest.mark.parametrize("relay_on,confirmed,expected", [
    (True, False, "Nog niet bevestigd"), (False, False, "Nog niet bevestigd"),
    (False, True, "Open"), (True, True, "Actief"), (None, True, "Onbekend")])
def test_contact_feedback_does_not_invent_an_off_or_on_confirmation(relay_on, confirmed, expected):
    result = execute(attributes(relay_on=relay_on, relay_confirmed=confirmed))
    assert expected in text(result["initial"])
    assert not result["calls"]


@pytest.mark.parametrize("scope,label", [("total", "Totaal warmtepomp"),
    ("supply_1", "Alleen voeding 1 · gedeeltelijke meting"), ("heater", "Alleen elektrische ondersteuning"),
    ("unknown", "Dekking onbekend")])
def test_power_coverage_is_labeled_and_measured_once(scope, label):
    data = attributes()
    data["panasonic"]["power_scope"] = scope
    result = execute(data, view="board")
    root = Markup(result["initial"]).root
    powers = [n for n in root.walk() if "reason-power" in n.attributes.get("class", "").split()]
    assert len(powers) == 1
    assert "3,7 kW" in powers[0].text() and label in powers[0].text()
    assert "gemeten" in powers[0].text()
    assert not result["calls"]


@pytest.mark.parametrize("value,kind,label", [(None, "measured", "Vermogen nog niet bekend"),
    (2500, "estimated", "geschat"), (2500, "unknown", "Vermogen nog niet bekend")])
def test_missing_or_estimated_power_is_never_shown_as_a_measurement(value, kind, label):
    data = attributes()
    data["panasonic"].update(power_w=value, power_kind=kind)
    assert label in text(execute(data)["initial"])


def test_only_sg_policy_switch_is_called_from_the_enable_button():
    result = execute(attributes(enabled=False), actions=[{"action": "sg_boost_enabled"}])
    assert result["calls"] == [{"domain": "switch", "service": "turn_on",
                                 "data": {"entity_id": "switch.example_sg_enabled"}}]
    assert "aria-checked=\"false\"" in result["final"]  # no optimistic relay or policy confirmation


def test_resume_button_calls_only_the_native_resume_entity():
    result = execute(attributes(manual_hold=True), actions=[{"action": "sg_boost_resume"}])
    assert result["calls"] == [{"domain": "button", "service": "press",
                                 "data": {"entity_id": "button.example_sg_resume"}}]
    assert "actuele voorwaarden" in result["feedback"]


@pytest.mark.parametrize("action,key", [("sg_boost_enabled", "enabled_entity"), ("sg_boost_resume", "resume_entity")])
def test_missing_policy_entity_gives_visible_error_without_physical_call(action, key):
    result = execute(attributes(**{key: None}), actions=[{"action": action}])
    assert not result["calls"] and result["error"]


def test_removed_buttons_and_setting_controls_cannot_be_activated_by_stale_dom():
    obsolete = ["dhw_enabled", "dhw_pause", "dhw_review", "dhw_takeover", "climate_manual",
                "climate_manual_mode", "climate_review", "climate_reset"]
    actions = [{"action": action} for action in obsolete]
    actions += [{"kind": "change", "dataset": {key: "normal_c"}}
                for key in ["dhwSetting", "climateSetting"]]
    result = execute(attributes(), actions=actions)
    assert not result["calls"]


def test_overview_explanations_have_stable_unique_keys_and_remain_closed():
    data = attributes(desired_on=True, relay_on=True)
    root = Markup(execute(data, view="board")["initial"]).root
    details = [n for n in root.walk() if n.tag == "details"]
    keys = [n.attributes.get("data-ui-key") for n in details]
    assert keys == ["overview:sg:why", "sg:overview:monitor"]
    assert len(set(keys)) == len(keys)
    assert not any("open" in n.attributes for n in details)
    data["sg_boost"]["reason"] = "Andere actuele reden"
    updated = Markup(execute(data, view="board")["initial"]).root
    assert keys == [n.attributes.get("data-ui-key") for n in updated.walk() if n.tag == "details"]


def load_platform(name):
    """Compile the actual entities/factory using HA interface doubles."""
    source = ROOT / f"custom_components/solar_pilot/{name}.py"
    class Entity:
        def __init__(self, runtime, suffix, label, key=None):
            self.runtime, self.suffix, self.key = runtime, suffix, key
    namespace = {"SolarEntity": Entity, "ButtonEntity": type("ButtonEntity", (), {}),
        "SwitchEntity": type("SwitchEntity", (), {}), "NumberEntity": type("NumberEntity", (), {}),
        "NumberMode": SimpleNamespace(BOX="box")}
    nodes = [n for n in ast.parse(source.read_text()).body
             if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)) and n.name != "async_setup_entry"]
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return namespace


def test_native_heatpump_factories_have_no_temperature_numbers_or_old_review_buttons():
    runtime = SimpleNamespace(configs={})
    assert load_platform("number")["_entities"](runtime) == []
    buttons = {b.suffix for b in load_platform("button")["_entities"](runtime)}
    switches = {b.suffix for b in load_platform("switch")["_entities"](runtime)}
    assert "sg_boost_resume" in buttons and "sg_boost_enabled" in switches
    assert not any(s.startswith("dhw_") or s.startswith("climate_") for s in buttons | switches)


@pytest.mark.asyncio
async def test_native_switch_and_resume_use_only_sg_runtime_methods():
    calls = []
    async def enabled(value):
        calls.append(("enabled", value))
    async def resume():
        calls.append(("resume",))
    runtime = SimpleNamespace(sg_boost=SimpleNamespace(set_enabled=enabled, resume_automation=resume,
        overview=lambda: {"enabled": False}))
    sw = load_platform("switch")["SolarSwitch"](runtime, "sg_boost_enabled", "Zonneboost")
    button = load_platform("button")["SolarButton"](runtime, "sg_boost_resume", "Hervatten")
    await sw.async_turn_on()
    await sw.async_turn_off()
    await button.async_press()
    assert calls == [("enabled", True), ("enabled", False), ("resume",)]


@pytest.mark.parametrize("suffix,value", [("dhw_temperature", 48), ("dhw_target", 50),
    ("panasonic_power", 3700), ("panasonic_status", "Panasonic regelt zelfstandig"),
    ("sg_boost_status", "Wacht op stabiele zon")])
def test_native_monitor_entities_show_reported_values_without_any_old_controller(suffix, value):
    monitor = {"temperature_c": 48, "target_c": 50, "power_w": 3700, "status": "Panasonic regelt zelfstandig"}
    runtime = SimpleNamespace(panasonic=SimpleNamespace(overview=lambda: monitor),
        sg_boost=SimpleNamespace(overview=lambda: {"reason": "Wacht op stabiele zon"}))
    cls = sensor_class()
    entity = object.__new__(cls)
    entity.runtime, entity.suffix, entity.key = runtime, suffix, None
    assert entity.native_value == value
    if suffix != "sg_boost_status":
        assert entity.extra_state_attributes["read_only"] is True


def test_climate_services_and_temperature_number_class_are_removed_from_public_api():
    entry = (ROOT / "custom_components/solar_pilot/__init__.py").read_text()
    services = (ROOT / "custom_components/solar_pilot/services.yaml").read_text()
    numbers = (ROOT / "custom_components/solar_pilot/number.py").read_text()
    assert "set_climate_setting" not in entry + services
    assert "set_climate_override" not in entry + services
    assert "DHWNumber" not in numbers and "DHW_NUMBERS" not in numbers


def test_registry_cleanup_preserves_current_switches_and_readonly_monitor_ids():
    """Exercise the actual startup cleanup against virtual registry entries."""
    source = ROOT / "custom_components/solar_pilot/__init__.py"
    function = next(n for n in ast.parse(source.read_text()).body
                    if isinstance(n, ast.AsyncFunctionDef) and n.name == "_async_setup_entry")
    start = next(i for i, n in enumerate(function.body)
                 if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "valid_prefixes"
                                                     for t in n.targets))
    end = next(i for i, n in enumerate(function.body[start:], start)
               if isinstance(n, ast.Expr) and isinstance(n.value, ast.Await))
    removed = []
    runtime = SimpleNamespace(configs={"device": {}}, capacity_settings={"enabled": False},
        phase_settings={"enabled": False}, wallbox_settings={"enabled": False})
    switch_ids = {e.suffix for e in load_platform("switch")["_entities"](runtime)}
    preserved = switch_ids | {"dhw_status", "dhw_temperature", "dhw_target",
                             "sg_boost_status", "sg_boost_resume", "panasonic_status", "panasonic_power"}
    obsolete = {"dhw_enabled", "dhw_review", "dhw_normal_c", "smart_climate_status", "smart_climate_confidence", "smart_climate_predicted_min"}
    entries = [SimpleNamespace(unique_id=f"entry_{suffix}", entity_id=f"native.{suffix}")
               for suffix in preserved | obsolete]
    entries.append(SimpleNamespace(unique_id="entry_device_manual_start", entity_id="button.device_start"))
    registry = SimpleNamespace(async_remove=removed.append)
    namespace = {"runtime": runtime, "entry": SimpleNamespace(entry_id="entry"), "hass": object(),
        "PV_SENSOR_DEFINITIONS": {}, "er": SimpleNamespace(async_get=lambda _: registry,
            async_entries_for_config_entry=lambda *_: entries)}
    exec(compile(ast.Module(body=function.body[start:end], type_ignores=[]), str(source), "exec"), namespace)
    assert set(removed) == {f"native.{suffix}" for suffix in obsolete}


@pytest.mark.asyncio
async def test_entry_removal_clears_both_software_notifications_without_equipment_calls():
    source = ROOT / "custom_components/solar_pilot/__init__.py"
    function = next(n for n in ast.parse(source.read_text()).body
                    if isinstance(n, ast.AsyncFunctionDef) and n.name == "async_remove_entry")
    calls, removed, frontend = [], [], []
    class Store:
        def __init__(self, _hass, _version, key):
            self.key = key
        async def async_remove(self):
            removed.append(self.key)
    async def executor(fn):
        fn()
    async def service(domain, action, payload, **kwargs):
        calls.append((domain, action, payload))
    hass = SimpleNamespace(async_add_executor_job=executor,
        services=SimpleNamespace(has_service=lambda domain, action: domain == "persistent_notification",
            async_call=service, async_remove=lambda *_: None),
        config_entries=SimpleNamespace(async_entries=lambda _: []))
    namespace = {"DOMAIN": "solar_pilot", "Store": Store,
        "history_storage_key": lambda entry: f"history.{entry}",
        "analysis_storage_key": lambda entry: f"analysis.{entry}",
        "delete_private_files_if_requested": lambda: None,
        "async_unregister_frontend": lambda *_args, **kwargs: frontend.append(kwargs),
        "SERVICE_SET_PLANNER_SETTING": "set_planner_setting"}
    future = ast.ImportFrom(module="__future__", names=[ast.alias(name="annotations")], level=0)
    exec(compile(ast.fix_missing_locations(ast.Module(body=[future, function], type_ignores=[])),
                 str(source), "exec"), namespace)
    await namespace["async_remove_entry"](hass, SimpleNamespace(entry_id="entry"))
    assert calls == [("persistent_notification", "dismiss", {"notification_id": "solar_pilot_entry"}),
                     ("persistent_notification", "dismiss", {"notification_id": "solar_pilot_entry_action_required"})]
    assert set(removed) == {"solar_pilot.entry", "history.entry", "analysis.entry"}
    assert frontend == [{"final": True}]
