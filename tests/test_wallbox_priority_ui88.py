"""Execute the shipped timed-priority UI against synthetic policy snapshots."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from test_overview_details60 import Markup

ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "custom_components/solar_pilot/frontend/solar-pilot-card.js"
NOW = 1_900_000_000
OPTIONS = {"30m": 1800, "1h": 3600, "2h": 7200, "3h": 10800,
           "4h": 14400, "5h": 18000, "until_auto": None}


def choice(target, option="auto"):
    duration = OPTIONS.get(option)
    return {"target": target, "option": option, "mode": "auto" if option == "auto" else "wallbox_first",
            "active": option != "auto", "eligible": True, "duration_s": duration,
            "expires_at": NOW + duration if duration else None,
            "remaining_s": duration, "indefinite": option == "until_auto", "label": "test"}


def attributes(option="auto"):
    return {"config_entry_id": "synthetic-entry", "mode": "solar",
            "devices": [{"id": "fan", "name": "Voorbeeldtoestel", "kind": "switch",
                         "available": True, "mode": "auto", "power_w": 0, "wallbox_first": False},
                        {"id": "dishwasher", "name": "Afwasmachine", "kind": "dishwasher",
                         "available": True, "mode": "auto", "power_w": 0}],
            "wallbox": {"enabled": True}, "sg_boost": {"configured": True},
            "priority_board": {"rows": [{"id": "device:fan", "device_id": "fan", "name": "Voorbeeldtoestel", "position": 1},
                                         {"id": "wallbox", "name": "Auto laden", "position": 2},
                                         {"id": "dhw_extra", "name": "Extra SG-zonneboost", "position": 3}],
                               "protected": []},
            "wallbox_priority": {"general": choice("global", option), "devices": {"fan": choice("device:fan", option)},
                                 "sg_boost": choice("dhw_extra", option), "available": True,
                                 "mixed": False, "observed_at": NOW}}


def execute(data=None, **parameters):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required to execute the shipped frontend")
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
let monotonic=1000;
const BaseDate=Date,sandbox={HTMLElement:class{},customElements:{get:()=>null,define:()=>{}},window:{},
 performance:{now:()=>monotonic},setTimeout,clearTimeout,input,
 Date:class extends BaseDate{static now(){return (input.now+input.clock_skew)*1000;}}};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
vm.runInContext(`(async()=>{
 const card=Object.create(SolarPilotCard.prototype),calls=[],opened=[];
 card._last={state:input.state,attributes:input.attributes};card._busy=false;card._error='';card._feedback='';
 card._hass={user:{id:'synthetic-admin',is_admin:input.admin},states:{},config:{time_zone:'Europe/Brussels'},
   callService:async(domain,service,data)=>{calls.push({domain,service,data});
     if(input.account_change)card._invalidateWallboxPriorityRequest();
     if(input.error)throw Error(input.error);}};
 card._render=()=>{};card._openWallboxPriority=target=>opened.push(target);card._anchorWallboxPriorityClock();
 const c=card._ctx(),view=input.view;
 const html=view==='overview'?card._overview(c):view==='loads'?card._loads(c):view==='comfort'?card._comfort(c):view==='priorities'?card._priorities(c):card._wallboxPriorityControl(c,input.target,{label:input.label,compact:true});
 const clock=spWallboxPriorityCountdown(card._wallboxPriorityChoice(c,input.target),card._wallboxPriorityNow());
 for(const action of input.actions||[])await card._click({target:{closest:()=>({disabled:false,dataset:{action:action.kind,priorityTarget:action.target}})}});
 if(input.option!==null)await card._setWallboxPriority(input.target,input.option);
 return {html,clock,calls,opened,error:card._error,feedback:card._feedback,busy:card._wallboxPriorityBusy,
  options:SP_WALLBOX_PRIORITY_OPTIONS,now:card._wallboxPriorityNow()};
})()`,sandbox).then(value=>process.stdout.write(JSON.stringify(value))).catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
"""
    payload = {"attributes": data or attributes(), "view": "control", "target": "global", "label": "",
               "now": NOW, "clock_skew": 0, "state": "Zonnestroom", "admin": True,
               "option": None, **parameters}
    result = subprocess.run([node, "-e", script, str(CARD)], input=json.dumps(payload),
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_picker_has_exactly_the_seven_requested_times():
    result = execute()
    assert [x[0] for x in result["options"]] == list(OPTIONS)
    assert result["options"][-1][1] == "Tot ik terug uitschakel"
    assert result["calls"] == []


@pytest.mark.parametrize("view", ["overview", "loads", "priorities"])
def test_general_and_individual_switches_are_available_in_actual_views(view):
    result = execute(view=view)
    root = Markup(result["html"]).root
    targets = [n.attributes["data-wallbox-priority-target"] for n in root.walk()
               if "data-wallbox-priority-target" in n.attributes]
    assert sorted(targets) == ["device:fan", "dhw_extra", "global"]
    assert not result["calls"]


def test_warmtepump_switch_is_only_extra_sg_and_preserves_ordinary_sg_controls():
    result = execute(view="comfort")
    text = Markup(result["html"]).root.text()
    assert 'data-wallbox-priority-target="dhw_extra"' in result["html"]
    assert "Alleen extra SG-zonneboost; Panasonic-comfort blijft behouden" in text
    assert 'data-action="sg_boost_enabled"' in result["html"]
    assert 'data-wallbox-priority-target="global"' not in result["html"]


@pytest.mark.parametrize("option", OPTIONS)
@pytest.mark.parametrize("target", ["global", "device:fan", "dhw_extra"])
def test_each_choice_sends_only_the_authorized_policy_service(option, target):
    result = execute(option=option, target=target)
    assert result["calls"] == [{"domain": "solar_pilot", "service": "wallbox_priority_control",
                               "data": {"config_entry_id": "synthetic-entry", "target": target, "option": option}}]
    assert result["busy"] is False


@pytest.mark.parametrize("option,expected", [("30m", "Nog 30:00"), ("1h", "Nog 1:00:00"),
    ("5h", "Nog 5:00:00"), ("until_auto", "tot ik terug op automatisch zet"), ("auto", "Automatisch")])
def test_clock_uses_original_server_deadline_and_survives_browser_clock_skew(option, expected):
    result = execute(attributes(option), clock_skew=7200)
    assert result["clock"] == expected
    assert result["now"] == NOW
    assert not result["calls"]


def test_expired_clock_waits_for_server_and_never_sends_an_automatic_browser_command():
    data = attributes("30m")
    data["wallbox_priority"]["general"]["expires_at"] = NOW - 1
    result = execute(data)
    assert result["clock"] == "Tijd verstreken · wacht op actuele status"
    assert not result["calls"]


def test_general_and_individual_auto_are_explicit_policy_requests():
    result = execute(attributes("1h"), actions=[
        {"kind": "wallbox_priority_toggle", "target": "device:fan"},
        {"kind": "wallbox_priority_toggle", "target": "global"}])
    assert [c["data"] for c in result["calls"]] == [
        {"config_entry_id": "synthetic-entry", "target": "device:fan", "option": "auto"},
        {"config_entry_id": "synthetic-entry", "target": "global", "option": "auto"}]


def test_off_switch_opens_picker_without_writing_and_active_duration_remains_editable():
    result = execute(actions=[{"kind": "wallbox_priority_toggle", "target": "device:fan"},
                              {"kind": "wallbox_priority_duration", "target": "global"}])
    assert result["opened"] == ["device:fan", "global"]
    assert not result["calls"]


def test_general_auto_with_individual_exceptions_still_offers_reset_all():
    data = attributes()
    data["wallbox_priority"]["devices"]["fan"] = choice("device:fan", "1h")
    data["wallbox_priority"]["mixed"] = True
    result = execute(data, actions=[{"kind": "wallbox_priority_auto", "target": "global"}])
    root = Markup(result["html"]).root
    assert "Afzonderlijke keuzes wijken af" in root.text() and "Alles automatisch" in root.text()
    assert result["calls"][0]["data"] == {"config_entry_id": "synthetic-entry", "target": "global", "option": "auto"}


def test_auto_describes_saved_base_policy_instead_of_claiming_device_first():
    data = attributes()
    data["devices"][0]["wallbox_first"] = True
    result = execute(data, target="device:fan")
    assert "Bewaarde verdeling: Wallbox eerst" in Markup(result["html"]).root.text()
    assert 'aria-checked="false"' in result["html"]


@pytest.mark.parametrize("change", ["not_admin", "unavailable", "restored", "ineligible", "legacy", "dishwasher"])
def test_ineligible_or_old_dom_cannot_send_a_policy_request(change):
    data = attributes()
    parameters = {"option": "30m"}
    if change == "not_admin": parameters["admin"] = False
    if change == "unavailable": parameters["state"] = "unavailable"
    if change == "restored": data["restored"] = True
    if change == "ineligible": data["wallbox_priority"]["general"]["eligible"] = False
    if change == "legacy": data.pop("wallbox_priority")
    if change == "dishwasher":
        data["wallbox_priority"]["devices"]["dishwasher"] = choice("device:dishwasher")
        parameters["target"] = "device:dishwasher"
    result = execute(data, **parameters)
    assert not result["calls"]


@pytest.mark.parametrize("target,option", [("device:missing", "30m"), ("wallbox", "1h"),
    ("global", "forever"), ("global", "1800"), ("dhw_extra", True)])
def test_unknown_target_or_option_is_rejected(target, option):
    assert not execute(target=target, option=option)["calls"]


def test_failure_releases_request_and_does_not_change_the_reported_choice():
    result = execute(attributes("1h"), option="30m", error="synthetic failure")
    assert "synthetic failure" in result["error"] and result["busy"] is False
    assert result["clock"] == "Nog 1:00:00"


def test_context_change_discards_late_acknowledgement():
    result = execute(option="30m", account_change=True)
    assert not result["feedback"] and result["busy"] is False


def test_device_name_is_escaped_in_markup_and_aria_label():
    payload = '<img src=x onerror="window.bad=true">'
    result = execute(target="device:fan", label=payload)
    root = Markup(result["html"]).root
    assert payload in root.text() and not any(n.tag == "img" for n in root.walk())
