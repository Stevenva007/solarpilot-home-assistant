"""Execute restart-policy dashboard controls and native switch service routing.

These use Node and a minimal HA entity double, not real Home Assistant Core.
"""
import asyncio
from html.parser import HTMLParser
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest


ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "custom_components/solar_pilot/frontend/solar-pilot-card.js"


def dashboard(payload):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required for real frontend execution")
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const calls=[],sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},input,calls};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
vm.runInContext(`(async()=>{
 const card=Object.create(SolarPilotCard.prototype);card._busy=!!input.busy;
 card._last={attributes:input.a||{}};card._ctx=()=>({a:input.a||{}});card._render=()=>calls.push({render:true,busy:card._busy,error:card._error||''});
 card._hass={callService:async(domain,service,data)=>{calls.push({domain,service,data});if(input.fail)throw new Error('Opslaan is mislukt');}};
 if(input.click){const button={disabled:!!input.disabled,dataset:{action:'restart_auto'}};
   await card._click({target:{closest:()=>button}});return {calls,error:card._error,busy:card._busy};}
 return {html:card._modeBar(input.a||{})};
})()`,sandbox).then(x=>process.stdout.write(JSON.stringify(x))).catch(e=>{process.stderr.write(e.stack);process.exitCode=1;});
'''
    result = subprocess.run([node, "-e", script, str(CARD)], input=json.dumps(payload),
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


class RestartControl(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.control = None
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "button" and values.get("data-action") == "restart_auto":
            self.control = values


@pytest.mark.parametrize("mode", ["observe", "solar", "paused"])
@pytest.mark.parametrize("enabled", [True, False])
def test_restart_policy_switch_is_accessible_in_every_main_mode(mode, enabled):
    markup = dashboard({"a": {"mode": mode, "auto_resume_after_restart": enabled,
                                "auto_resume_after_restart_entity": "switch.restart"}})["html"]
    control = RestartControl(markup).control
    assert control["role"] == "switch" and control["aria-checked"] == str(enabled).lower()
    assert control["aria-label"] == "Na herstart automatisch hervatten"
    assert "disabled" not in control
    assert "Geldt voor Pauze; Alleen bekijken blijft behouden." in markup


@pytest.mark.parametrize("value", [None, "true", 1])
def test_dashboard_does_not_infer_enabled_from_a_missing_or_nonboolean_policy(value):
    markup = dashboard({"a": {"mode": "paused", "auto_resume_after_restart": value,
                                "auto_resume_after_restart_entity": "switch.restart"}})["html"]
    assert RestartControl(markup).control["aria-checked"] == "false"
    assert "Pauze blijft na een herstart behouden." in markup


def test_previous_backend_without_policy_entity_cannot_offer_a_working_switch():
    markup = dashboard({"a": {"mode": "paused"}})["html"]
    assert "disabled" in RestartControl(markup).control
    assert "Niet beschikbaar" in markup
    assert dashboard({"a": {"mode": "paused"}, "click": True})["calls"] == []


@pytest.mark.parametrize("cause", ["user", "legacy"])
def test_ordinary_pause_explains_next_restart_policy_without_claiming_immediate_resume(cause):
    markup = dashboard({"a": {"mode": "paused", "pause_cause": cause,
                                "pause_reason": "Pauze is ingeschakeld",
                                "auto_resume_after_restart": True}})["html"]
    assert "Pauze is ingeschakeld" in markup
    assert "Bij de volgende herstart hervat SolarPilot automatisch na de opstartcontrole." in markup
    assert "zodra de herstartcontrole klaar is" not in markup


@pytest.mark.parametrize("cause", ["internal_fault", "command_fault", "removal"])
def test_fault_and_removal_pause_never_promises_automatic_resume(cause):
    markup = dashboard({"a": {"mode": "paused", "pause_cause": cause,
                                "pause_reason": "Controle nodig",
                                "auto_resume_after_restart": True,
                                "restart_requested_mode": "solar"}})["html"]
    assert "Deze bescherming wordt niet automatisch opgeheven." in markup
    assert "hervat automatisch" not in markup


@pytest.mark.parametrize("mode", ["paused", "observe"])
def test_queued_restart_is_explained_as_waiting_for_automatic_control(mode):
    markup = dashboard({"a": {"mode": mode, "restart_requested_mode": "solar",
                                "auto_resume_after_restart": True}})["html"]
    assert "SolarPilot hervat automatisch zodra de herstartcontrole klaar is." in markup
    assert "Alleen bekijken blijft ook na een herstart behouden." not in markup


def test_selected_observe_keeps_its_mode_and_does_not_claim_automatic_resume():
    markup = dashboard({"a": {"mode": "observe", "auto_resume_after_restart": True}})["html"]
    assert "Alleen bekijken blijft ook na een herstart behouden." in markup
    assert "hervat automatisch" not in markup


def test_pause_reason_is_escaped_instead_of_interpreted_as_dashboard_markup():
    markup = dashboard({"a": {"mode": "paused", "pause_reason": "Wacht <script>alert(1)</script>"}})["html"]
    assert "<script>" not in markup and "Wacht &lt;script&gt;" in markup


@pytest.mark.parametrize("enabled,service", [(True, "turn_off"), (False, "turn_on")])
def test_dashboard_policy_toggle_only_calls_the_native_switch_service(enabled, service):
    result = dashboard({"a": {"mode": "paused", "auto_resume_after_restart": enabled,
                               "auto_resume_after_restart_entity": "switch.restart"}, "click": True})
    assert result["calls"] == [{"render": True, "busy": True, "error": ""},
                               {"domain": "switch", "service": service,
                                "data": {"entity_id": "switch.restart"}},
                               {"render": True, "busy": False, "error": ""}]
    assert result["busy"] is False


@pytest.mark.parametrize("flag", ["busy", "disabled"])
def test_busy_or_disabled_policy_control_cannot_send_duplicate_services(flag):
    result = dashboard({"a": {"auto_resume_after_restart_entity": "switch.restart"},
                        "click": True, flag: True})
    assert result["calls"] == []


def test_switch_save_error_is_reported_and_does_not_leave_the_dashboard_busy():
    result = dashboard({"a": {"auto_resume_after_restart_entity": "switch.restart"},
                        "click": True, "fail": True})
    assert result["error"] == "Opslaan is mislukt" and result["busy"] is False
    assert result["calls"] == [{"render": True, "busy": True, "error": ""},
                               {"domain": "switch", "service": "turn_on",
                                "data": {"entity_id": "switch.restart"}},
                               {"render": True, "busy": False, "error": "Opslaan is mislukt"}]


@pytest.fixture
def native_switch(monkeypatch):
    ha_entity = ModuleType("homeassistant.helpers.entity")
    ha_entity.Entity = type("Entity", (), {})
    ha_entity.DeviceInfo = dict
    monkeypatch.setitem(sys.modules, ha_entity.__name__, ha_entity)
    entity_path = ROOT / "custom_components/solar_pilot/entity.py"
    entity_spec = importlib.util.spec_from_file_location("custom_components.solar_pilot._native_entity58", entity_path)
    entity_module = importlib.util.module_from_spec(entity_spec)
    entity_spec.loader.exec_module(entity_module)
    ha_switch = ModuleType("homeassistant.components.switch")
    ha_switch.SwitchEntity = type("SwitchEntity", (), {})
    monkeypatch.setitem(sys.modules, "custom_components.solar_pilot.entity", entity_module)
    monkeypatch.setitem(sys.modules, ha_switch.__name__, ha_switch)
    path = ROOT / "custom_components/solar_pilot/switch.py"
    spec = importlib.util.spec_from_file_location("custom_components.solar_pilot._switch_dashboard58", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    calls = []

    async def set_policy(value):
        calls.append(value)
        runtime.auto_resume_after_restart = value

    runtime = SimpleNamespace(entry=SimpleNamespace(entry_id="entry"), dhw=SimpleNamespace(configured=False),
                              auto_resume_after_restart=True, data_loaded=True,
                              set_auto_resume_after_restart=set_policy)
    return module, runtime, calls


def test_native_restart_policy_switch_exists_without_a_boiler_or_any_load(native_switch):
    module, runtime, _ = native_switch
    entities = module._entities(runtime)
    switch = next(entity for entity in entities if entity.suffix == "auto_resume_after_restart")
    assert switch._attr_name == "Na herstart automatisch hervatten"
    assert switch._attr_unique_id == "entry_auto_resume_after_restart"
    assert switch.is_on is True and switch.available is True
    assert "Alleen bekijken" in switch.extra_state_attributes["observe_meaning"]
    assert "nooit automatisch" in switch.extra_state_attributes["protection_meaning"]


def test_native_switch_turn_on_and_off_only_change_restart_policy(native_switch):
    module, runtime, calls = native_switch
    switch = next(entity for entity in module._entities(runtime) if entity.suffix == "auto_resume_after_restart")
    asyncio.run(switch.async_turn_off())
    assert switch.is_on is False
    asyncio.run(switch.async_turn_on())
    assert switch.is_on is True and calls == [False, True]
    runtime.data_loaded = False
    assert switch.available is False


def test_native_policy_platform_registers_the_switch_for_dynamic_addition(native_switch):
    module, runtime, _ = native_switch
    registrations = []
    runtime.platforms = SimpleNamespace(register=lambda *args: registrations.append(args))
    add_entities = lambda _entities: None
    asyncio.run(module.async_setup_entry(None, SimpleNamespace(runtime_data=runtime), add_entities))
    platform, add, factory = registrations[0]
    assert platform == "switch" and add is add_entities
    assert any(entity.suffix == "auto_resume_after_restart" for entity in factory())
