"""Execute shipped recovery rendering and clicks with Node/HA API doubles.

These checks exercise service routing and visible feedback, not a browser,
network delivery, live Home Assistant or physical boiler operation.
"""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from test_overview_details60 import Element, Markup, article


CARD = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot/frontend/solar-pilot-card.js"
FAULT = "Boilerdoel niet bevestigd; handmatige controle nodig"


def recovery_attributes(mode="paused", **dhw_overrides):
    return {
        "mode": mode, "mode_entity": "select.solar_pilot_mode", "problem": FAULT,
        "problem_kind": "dhw_review", "reset_entity": "button.generic_reset",
        "dhw": {"configured": True, "enabled": True, "fault": FAULT, "status": FAULT,
                "actual_target_c": 50, "temperature_c": 50, "proposed_target_c": 60,
                "review_entity": "button.boiler_review", "review_required": True,
                "review_allowed": mode != "solar", "review_block_reason": "" if mode != "solar" else "Kies eerst Pauze",
                **dhw_overrides},
    }


def execute_recovery(attributes, *, steps=None, view="alerts"):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required to execute actual recovery UI")
    script = r"""
const fs=require('node:fs'),vm=require('node:vm');
const input=JSON.parse(fs.readFileSync(0,'utf8'));
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},input};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
vm.runInContext(`(async()=>{
  const calls=[],confirmations=[],frames=[];
  const card=Object.create(SolarPilotCard.prototype);
  card._last={attributes:input.attributes};card._busy=false;card._error='';
  let step={};
  window.confirm=message=>{confirmations.push(message);return step.confirm!==false;};
  card._hass={states:{},config:{time_zone:'Europe/Brussels'},callService:async(domain,service,data)=>{
    calls.push({domain,service,data});if(step.fail)throw new Error(step.fail);
  }};
  const render=()=>{
    const c=card._ctx(),alerts=card._globalAlerts(c);
    return input.view==='dhw'?alerts+card._dhw(c):input.view==='overview'?alerts+card._decisionBoard(c):alerts;
  };
  card._render=()=>frames.push(render());
  const initial=render();
  for(step of input.steps||[]){
    if(step.attributes)card._last={attributes:step.attributes};
    const html=render(),buttons=[...html.matchAll(/<button\\b[^>]*>/g)].map(match=>match[0]);
    const found=buttons.find(button=>button.includes('data-action="'+step.action+'"'));
    const disabled=found?(/\\sdisabled(?:\\s|>|=)/.test(found)):false;
    if(found||step.direct)await card._click({target:{closest:()=>({dataset:{action:step.action},disabled:step.direct?false:disabled})}});
    frames.push(render());
  }
  return {initial,html:render(),calls,confirmations,frames,busy:card._busy,error:card._error};
})()`,sandbox).then(result=>process.stdout.write(JSON.stringify(result))).catch(error=>{
  process.stderr.write(error.stack);process.exitCode=1;
});
"""
    result = subprocess.run([node, "-e", script, str(CARD)],
                            input=json.dumps({"attributes": attributes, "steps": steps or [], "view": view}),
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def buttons(html):
    return [node for node in Markup(html).root.walk() if node.tag == "button"]


def actions(html):
    return [node.attributes.get("data-action") for node in buttons(html)]


def role_text(html, role):
    return " ".join(node.text() for node in Markup(html).root.walk()
                    if node.attributes.get("role") == role)


def disclosed_text(node):
    """Read native visible disclosure text without claiming browser layout."""
    if node.tag == "details" and "open" not in node.attributes:
        return " ".join(child.text() for child in node.children
                        if isinstance(child, Element) and child.tag == "summary")
    return " ".join(disclosed_text(child) if isinstance(child, Element) else child
                    for child in node.children)


def test_fault_only_global_banner_offers_specific_boiler_review_instead_of_generic_reset():
    result = execute_recovery(recovery_attributes())
    assert "dhw_review" in actions(result["initial"])
    assert "reset" not in actions(result["initial"])
    assert FAULT in Markup(result["initial"]).root.text()
    assert not result["calls"]


def test_fault_only_warm_water_details_also_offer_the_boiler_recovery_control():
    result = execute_recovery(recovery_attributes(), view="dhw")
    assert "dhw_review" in actions(result["initial"])
    assert "reset" not in actions(result["initial"])
    assert FAULT in Markup(result["initial"]).root.text()


def test_automatic_mode_offers_pause_first_and_click_only_requests_the_mode_change():
    result = execute_recovery(recovery_attributes("solar"), steps=[{"action": "dhw_pause"}])
    assert "dhw_pause" in actions(result["initial"])
    assert result["calls"] == [{"domain": "select", "service": "select_option",
                               "data": {"entity_id": "select.solar_pilot_mode", "option": "paused"}}]
    assert "dhw_review" not in actions(result["html"])


def test_review_is_not_sent_until_a_new_ha_payload_confirms_pause():
    paused = recovery_attributes()
    result = execute_recovery(recovery_attributes("solar"), steps=[
        {"action": "dhw_pause"}, {"action": "dhw_review", "direct": True},
        {"action": "dhw_review", "attributes": paused},
    ])
    assert result["calls"] == [
        {"domain": "select", "service": "select_option",
         "data": {"entity_id": "select.solar_pilot_mode", "option": "paused"}},
        {"domain": "button", "service": "press", "data": {"entity_id": "button.boiler_review"}},
    ]
    assert all(call["data"].get("option") != "solar" for call in result["calls"])
    assert not result["busy"]


def test_failed_pause_request_cannot_trigger_boiler_review_or_display_success():
    result = execute_recovery(recovery_attributes("solar"), steps=[
        {"action": "dhw_pause", "fail": "Pauze kiezen mislukt"},
        {"action": "dhw_review", "direct": True},
    ])
    assert result["calls"] == [{"domain": "select", "service": "select_option",
                               "data": {"entity_id": "select.solar_pilot_mode", "option": "paused"}}]
    assert any("Pauze kiezen mislukt" in role_text(frame, "alert") for frame in result["frames"])
    assert role_text(result["html"], "alert")
    assert not role_text(result["html"], "status")


def test_declining_explicit_boiler_review_sends_no_service_request():
    result = execute_recovery(recovery_attributes(), steps=[{"action": "dhw_review", "confirm": False}])
    assert not result["calls"] and result["confirmations"]


@pytest.mark.parametrize("reason,extra", [
    ("Wacht op lopende boileropdracht", {"pending": {"target_c": 60}}),
    ("Actuele tanktemperatuur ontbreekt", {"temperature_c": None}),
    ("Actueel boilerdoel ontbreekt", {"actual_target_c": None}),
    ("Fabrikant-hygiëne is actief", {"protected": True}),
])
def test_backend_review_blocker_is_visible_and_blocks_rendered_and_direct_review_click(reason, extra):
    attrs = recovery_attributes(review_allowed=False, review_block_reason=reason, **extra)
    result = execute_recovery(attrs, steps=[{"action": "dhw_review"}, {"action": "dhw_review", "direct": True}])
    assert ("lopende boileropdracht" if extra.get("pending") else reason) in Markup(result["initial"]).root.text()
    controls = [button for button in buttons(result["initial"])
                if button.attributes.get("data-action") == "dhw_review"]
    assert not controls or all("disabled" in control.attributes for control in controls)
    assert not result["calls"]


def test_successful_specific_review_has_visible_feedback_without_an_automatic_temperature_or_mode_write():
    result = execute_recovery(recovery_attributes(), steps=[{"action": "dhw_review"}])
    assert result["calls"] == [{"domain": "button", "service": "press",
                               "data": {"entity_id": "button.boiler_review"}}]
    assert role_text(result["html"], "status")
    assert not role_text(result["html"], "alert") and not result["error"]


def test_rejected_boiler_review_displays_the_actual_error_and_no_success_feedback():
    result = execute_recovery(recovery_attributes(), steps=[
        {"action": "dhw_review", "fail": "Tanktemperatuur te oud; controleer de bron"}])
    assert "Tanktemperatuur te oud; controleer de bron" in role_text(result["html"], "alert")
    assert not role_text(result["html"], "status")
    assert len(result["calls"]) == 1 and not result["busy"]


def test_flexible_load_fault_keeps_its_own_generic_reset_route():
    attrs = recovery_attributes()
    attrs.update(problem_kind="command_fault", problem="Ontvochtiger: opdracht niet bevestigd")
    result = execute_recovery(attrs, steps=[{"action": "reset"}])
    assert "reset" in actions(result["initial"])
    assert result["calls"] == [{"domain": "button", "service": "press",
                               "data": {"entity_id": "button.generic_reset"}}]


def test_fault_and_blocker_messages_are_escaped_in_the_recovery_widget():
    hostile = '<img src=x onerror="window.pwned=true">'
    attrs = recovery_attributes(fault=hostile, status=hostile, review_allowed=False, review_block_reason=hostile)
    attrs["problem"] = hostile
    html = execute_recovery(attrs)["initial"]
    assert "<img" not in html and "&lt;img" in html
    assert hostile in Markup(html).root.text()


def test_missing_review_entity_is_actionable_and_cannot_silently_call_an_unrelated_button():
    result = execute_recovery(recovery_attributes(review_entity=None),
                              steps=[{"action": "dhw_review", "direct": True}])
    assert not result["calls"]
    assert "reset" not in actions(result["initial"])
    assert "niet beschikbaar" in Markup(result["initial"]).root.text().lower()


@pytest.mark.parametrize("mode", ["solar", "paused"])
def test_automatic_boiler_check_needs_no_manual_click_and_keeps_manual_recovery_collapsed(mode):
    reason = "Wacht op een nieuwe betrouwbare terugmelding; SolarPilot controleert automatisch opnieuw."
    attrs = recovery_attributes(mode, automatic_recovery_pending=True,
                                automatic_recovery_reason=reason,
                                automatic_recovery_remaining_s=None,
                                automatic_recovery_state="source_wait")
    result = execute_recovery(attrs)
    root = Markup(result["initial"]).root
    visible = disclosed_text(root)
    assert "Automatische boilercontrole" in visible and reason in visible
    assert "Je hoeft geen controleknop in te drukken" in visible
    assert "Pauzeer eerst" not in visible and "Controleer de actuele tanktemperatuur" not in visible
    fallback = next(node for node in root.walk() if node.tag == "details"
                    and any(isinstance(child, Element) and child.tag == "summary"
                            and "Zelf controleren" in child.text() for child in node.children))
    assert "open" not in fallback.attributes
    assert ("dhw_pause" if mode == "solar" else "dhw_review") in \
        [node.attributes.get("data-action") for node in fallback.walk() if node.tag == "button"]
    assert "reset" not in actions(result["initial"]) and not result["calls"]


def test_automatic_backoff_reason_and_real_remaining_wait_are_visible_without_requesting_a_retry():
    reason = "SolarPilot controleert opnieuw; nog 120 s wachten vóór een nieuwe beoordeling."
    attrs = recovery_attributes("solar", automatic_recovery_pending=True,
                                automatic_recovery_reason=reason,
                                automatic_recovery_remaining_s=120,
                                automatic_recovery_state="backoff")
    result = execute_recovery(attrs)
    visible = disclosed_text(Markup(result["initial"]).root)
    assert reason in visible and "2m" in visible
    assert "reset" not in actions(result["initial"]) and not result["calls"]


def test_automatic_recovery_with_unknown_remaining_time_does_not_invent_a_zero_wait():
    attrs = recovery_attributes("solar", automatic_recovery_pending=True,
                                automatic_recovery_reason="De actuele terugmelding ontbreekt.",
                                automatic_recovery_remaining_s=None,
                                automatic_recovery_state="source_wait")
    visible = disclosed_text(Markup(execute_recovery(attrs)["initial"]).root)
    assert "De actuele terugmelding ontbreekt" in visible
    assert "0m" not in visible and "0 s" not in visible


def test_automatic_recovery_reason_is_escaped_without_executable_markup():
    hostile = '<img src=x onerror="window.pwned=true">'
    attrs = recovery_attributes("solar", automatic_recovery_pending=True,
                                automatic_recovery_reason=hostile,
                                automatic_recovery_remaining_s=None,
                                automatic_recovery_state="source_wait")
    result = execute_recovery(attrs)
    assert "<img" not in result["initial"] and "&lt;img" in result["initial"]
    assert hostile in disclosed_text(Markup(result["initial"]).root)
    assert not result["calls"]


def test_latest_backend_automatic_wait_reason_is_kept_in_the_boiler_overview_panel():
    reason = "Opnieuw beoordelen na de wachttijd; nog 90 s."
    attrs = recovery_attributes("solar", automatic_recovery_pending=True,
                                automatic_recovery_reason=reason,
                                automatic_recovery_remaining_s=90,
                                automatic_recovery_state="backoff",
                                status=reason,
                                failed_command={"requested_target_c": 60, "reported_target_c": 50,
                                                "waited_s": 181, "reason": "Doel niet bevestigd"},
                                execution={"state": "blocked", "code": "automatic_recovery", "reason": reason})
    result = execute_recovery(attrs, view="overview")
    assert reason in article(Markup(result["initial"]).root, "Sanitair warm water").text()
    assert "reset" not in actions(result["initial"]) and not result["calls"]
    keys = [node.attributes["data-ui-key"] for node in Markup(result["initial"]).root.walk()
            if "data-ui-key" in node.attributes]
    assert len(keys) == len(set(keys))
    assert "dhw-failure:recovery" in keys and "dhw-failure:overview" in keys
