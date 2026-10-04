"""Execute the real climate card's dashboard switches in a Node VM.

These checks cover DOM strings and service arguments, not a browser or hardware.
"""
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess

import pytest


CARD = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot/frontend/solar-pilot-card.js"


class Markup(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.parts = []
        self.buttons = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        if tag == "button":
            self.buttons.append(dict(attrs))

    def handle_data(self, value):
        self.parts.append(value)

    @property
    def text(self):
        return " ".join(self.parts)

    def switch(self, action, entity="climate.salon"):
        return next(button for button in self.buttons
                    if button.get("data-action") == action
                    and button.get("data-climate-entity") == entity)


def card(payload, *, action=None, entity="climate.salon", busy=False):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to execute the actual climate card")
    script = r"""
const fs = require('node:fs'), vm = require('node:vm');
const definitions = new Map(), input = JSON.parse(fs.readFileSync(0, 'utf8'));
const sandbox = {
  HTMLElement: class {}, window: {confirm:()=>{throw new Error('A switch should not open a confirmation dialog');}},
  customElements: {get:key=>definitions.get(key), define:(key,value)=>definitions.set(key,value)},
  input, calls: []
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);
const run = vm.runInContext(`(async()=>{
  const card = Object.create(SolarPilotCard.prototype);
  card._last = {attributes: {config_entry_id:'entry', mode:input.mode||'solar', devices:[], ems:{smart_climate:input.payload}}};
  card._hass = {states:{}, callService:async(domain,service,data)=>{calls.push({domain,service,data});}};
  card._busy = input.busy; card._render = ()=>{};
  const markup = card._climate(card._ctx());
  if(input.action){
    const button = {disabled:false, dataset:{action:input.action,climateEntity:input.entity}};
    await card._click({target:{closest:()=>button}});
  }
  return {markup,calls};
})()`, sandbox);
run.then(result=>process.stdout.write(JSON.stringify(result))).catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
"""
    result = subprocess.run(
        [node, "-e", script, str(CARD)], input=json.dumps({
            "payload": payload, "action": action, "entity": entity,
            "busy": busy, "mode": "solar" if payload.get("control_enabled") else "observe",
        }), text=True, capture_output=True, check=True,
    )
    rendered = json.loads(result.stdout)
    return rendered["markup"], Markup(rendered["markup"]), rendered["calls"]


def climate_payload():
    return {
        "enabled": True, "control_enabled": True, "automatic_zone_control": True,
        "settings": {"automatic_zone_control": True},
        "decision": {"mode": "hold", "reason": "Per zone", "evaluated_forecast_h": 5},
        "zones": [
            {"entity_id": "climate.salon", "name": "Kapsalon", "current": 21.2, "target": 21,
             "mode": "off", "action": "off", "action_known": True, "hvac_modes": ["auto", "off"],
             "dashboard_override": "", "control_stage": "reactive"},
            {"entity_id": "climate.living", "name": "Woonkamer", "current": 22, "target": 21,
             "mode": "auto", "action": "idle", "action_known": True, "hvac_modes": ["auto", "off"],
             "dashboard_override": "", "control_stage": "predictive"},
        ], "profiles": {}, "alerts": [],
    }


def expected_call(entity, mode):
    return {"domain": "solar_pilot", "service": "set_climate_override",
            "data": {"config_entry_id": "entry", "entity_id": entity, "mode": mode}}


def test_automatic_default_has_a_manual_control_switch_for_each_independent_zone():
    _, result, calls = card(climate_payload())
    assert calls == []
    for entity in ("climate.salon", "climate.living"):
        button = result.switch("climate_manual", entity)
        assert button["role"] == "switch" and button["aria-checked"] == "false"
        assert "disabled" not in button
    assert not any(x.get("data-action") == "climate_manual_mode" for x in result.buttons)
    assert "SolarPilot schakelt elke ruimte zelf tussen AUTO en UIT" in result.text
    assert "Handmatig bedienen staat uit: SolarPilot kiest zelf AUTO of UIT" in result.text
    assert "een handmatig uitgeschakelde ruimte blijft uit" not in result.text
    assert "AUTO geeft Panasonic toestemming" in result.text
    assert "betekent niet dat de compressor draait" in result.text


@pytest.mark.parametrize("entity,mode", [("climate.salon", "off"), ("climate.living", "auto")])
def test_enabling_manual_switch_persists_the_current_mode_for_only_this_zone(entity, mode):
    _, _, calls = card(climate_payload(), action="climate_manual", entity=entity)
    assert calls == [expected_call(entity, mode)]


@pytest.mark.parametrize("override,checked,requested", [("off", "false", "auto"), ("auto", "true", "off")])
def test_manual_auto_off_switch_has_fixed_requested_state_and_correct_command(override, checked, requested):
    payload = climate_payload()
    payload["zones"][0]["dashboard_override"] = override
    _, result, calls = card(payload, action="climate_manual_mode")
    assert result.switch("climate_manual")["aria-checked"] == "true"
    assert result.switch("climate_manual_mode")["aria-checked"] == checked
    assert "tot je automatische regeling kiest" in result.text
    assert calls == [expected_call("climate.salon", requested)]


def test_return_to_automatic_clears_only_override_even_while_source_and_command_are_uncertain():
    payload = climate_payload()
    payload["zones"][0].update(dashboard_override="off", mode="unavailable", current=None,
                                 action_known=False, pending_mode="auto", command_fault="Timeout")
    _, result, calls = card(payload, action="climate_manual")
    assert "disabled" not in result.switch("climate_manual")
    assert "disabled" in result.switch("climate_manual_mode")
    assert calls == [expected_call("climate.salon", "automatic")]


@pytest.mark.parametrize("source", [
    {"pending_mode": "auto"}, {"command_fault": "Timeout"}, {"valid": False},
    {"available": False}, {"action_known": False}, {"current": None},
    {"target": None}, {"mode": "heat"}, {"mode": "cool"}, {"mode": "unavailable"},
])
def test_pending_fault_stale_and_fixed_native_modes_cannot_trigger_a_manual_write(source):
    payload = climate_payload()
    payload["zones"][0].update(source)
    _, result, calls = card(payload, action="climate_manual")
    assert "disabled" in result.switch("climate_manual")
    assert ("disabled" in result.switch("climate_manual", "climate.living")) == bool(source.get("pending_mode"))
    assert calls == []


def test_manual_auto_off_cannot_bypass_fault_gate_even_through_direct_click_handler():
    payload = climate_payload()
    payload["zones"][0].update(dashboard_override="off", command_fault="No confirmed response")
    _, result, calls = card(payload, action="climate_manual_mode")
    assert "Opdracht onzeker: No confirmed response" in result.text
    assert "disabled" in result.switch("climate_manual_mode")
    assert calls == []


@pytest.mark.parametrize("entity", ["climate.salon", "climate.living"])
def test_pending_command_from_overview_also_blocks_a_second_request(entity):
    payload = climate_payload()
    payload["pending_commands"] = [{"entity_id": "climate.salon", "mode": "auto"}]
    _, result, calls = card(payload, action="climate_manual", entity=entity)
    assert "Wacht op bevestiging: Automatisch" in result.text
    assert "disabled" in result.switch("climate_manual", entity)
    assert calls == []


def test_busy_card_disables_both_switches_and_dispatches_no_second_call():
    payload = climate_payload()
    payload["zones"][0]["dashboard_override"] = "auto"
    _, result, calls = card(payload, action="climate_manual", busy=True)
    assert "disabled" in result.switch("climate_manual")
    assert "disabled" in result.switch("climate_manual_mode")
    assert calls == []


def test_observe_mode_can_save_manual_choice_but_explains_delayed_execution():
    payload = climate_payload()
    payload["control_enabled"] = False
    _, result, calls = card(payload, action="climate_manual")
    assert "Handmatige opdrachten wachten tot Automatisch regelen actief is" in result.text
    assert calls == [expected_call("climate.salon", "off")]
    assert "ALLEEN ADVIES" in result.text


def test_legacy_optout_is_explicit_without_claiming_autonomous_zone_control():
    payload = climate_payload()
    payload["automatic_zone_control"] = payload["settings"]["automatic_zone_control"] = False
    payload["zones"][0]["manual_off"] = True
    _, result, calls = card(payload)
    assert calls == []
    assert "Automatische zoneregeling staat uit" in result.text
    assert "Handmatig uit · blijft uit" in result.text
    assert "SolarPilot schakelt elke ruimte zelf" not in result.text


def test_per_zone_stage_reason_and_restart_timing_do_not_change_the_other_zone():
    payload = climate_payload()
    payload["zones"][0].update(control_stage="predictive", decision_reason="Koeling later nodig", restart_after_h=3.5, desired_mode="off", urgent_auto=True)
    payload["zone_decisions"] = {"climate.salon": {"required_lead_h": 20.5, "evaluated_forecast_h": 48}}
    payload["decision"].update(predicted_min_c=21.2, predicted_max_c=22)
    _, result, calls = card(payload)
    assert calls == []
    assert "Voorspellend geregeld" in result.text
    assert "Koeling later nodig" in result.text
    assert "Voorstel: ruimtebedrijf UIT" in result.text
    assert "Tijdige AUTO-herstart nodig voor comfort" in result.text
    assert "Benodigde herstartvoorsprong ±20,5 u" in result.text
    assert "Deze ruimte: 48 u voorspelling beoordeeld" in result.text
    assert "Opnieuw AUTO over ±3,5 u" in result.text
    assert "Alleen de komende 5 uur beoordeeld" in result.text
    assert "Dit bewijst nog niet dat de bouwschil vooraf genoeg afkoelt" in result.text
    assert "komende 48" not in result.text


def test_dynamic_zone_names_faults_reasons_and_entity_ids_are_escaped():
    payload = climate_payload()
    payload["zones"][0].update(name='<img src=x onerror="bad()">', command_fault="<svg onload=bad()>",
                                 decision_reason="<script>bad()</script>", entity_id='climate.salon" onclick="bad()')
    markup, _, calls = card(payload)
    assert calls == []
    assert "<img" not in markup and "<svg" not in markup and "<script" not in markup
    assert 'data-climate-entity="climate.salon&quot; onclick=&quot;bad()"' in markup


def test_learning_evidence_uses_direction_specific_days_instead_of_passive_profile_age():
    payload = climate_payload()
    payload["profiles"] = {"climate.salon": {
        "samples": 633, "days": 7,
        "confidence_components": {"heating_response": {"samples": 6, "confidence": 0.98}},
        "directional_evidence": {
            "heating_response": {"samples": 6, "required_samples": 6, "days": 1,
                                 "required_days": 5, "confidence": 0.196,
                                 "consistent": False, "status": "Eerste metingen"},
            "cooling_delay": {"samples": 0, "required_samples": 4, "days": 0,
                              "required_days": 5, "confidence": 0, "status": "Nog niet geleerd"},
        },
    }}
    _, result, calls = card(payload)
    assert calls == []
    assert "633 temperatuurmetingen" in result.text
    assert "20% meetdekking" in result.text and "98% meetdekking" not in result.text
    assert "6 / 6 bruikbare metingen · 1 / 5 dagen met deze metingen · respons nog wisselvallig" in result.text
    assert "Reactievertraging koelen" in result.text
    assert "0 / 4 bruikbare metingen · 0 / 5 dagen met deze metingen" in result.text
    assert "percentage is geen bewezen voorspellingsnauwkeurigheid" in result.text


def test_measured_prediction_error_and_actual_validated_horizon_are_separate_from_evidence_counts():
    payload = climate_payload()
    payload["profiles"] = {"climate.salon": {"validation": {
        "passive": {"samples": 12, "mean_absolute_error_c": 0.123, "max_horizon_h": 0.25},
        "heating": {"samples": 0, "mean_absolute_error_c": None, "max_horizon_h": None},
    }}}
    _, result, calls = card(payload)
    assert calls == []
    assert "Gecontroleerde voorspellingsfout" in result.text
    assert "0,123 °C gemiddelde absolute fout" in result.text
    assert "12 vergelijkingen · gecontroleerd tot 0,25 u tussen metingen" in result.text
    assert "Nog geen gecontroleerde voorspellingen" in result.text
    assert "bewijst geen nauwkeurigheid over 48 uur" in result.text
    assert "100%" not in result.text


def test_missing_model_evidence_still_explains_the_active_reactive_comfort_control():
    payload = climate_payload()
    payload["decision"].update(missing_components=["heating_response", "heating_delay", "heating_validation"],
                                 control_ready=False, forecast_confidence=0.98)
    _, result, calls = card(payload)
    assert calls == []
    assert "Comfortbewaking · model leert" in result.text
    assert "Comfortbewaking tijdens leren" in result.text
    assert "meetdekking van pauzevoorspelling 98%" in result.text
    assert "voorspelling tijdens pauze 98%" not in result.text
    assert "Thermisch model 0%" not in result.text


@pytest.mark.parametrize("action", ["climate_manual", "climate_manual_mode"])
def test_click_cannot_target_a_zone_outside_the_overview(action):
    _, _, calls = card(climate_payload(), action=action, entity="climate.unselected")
    assert calls == []


def test_hidden_manual_auto_off_switch_cannot_create_an_override_directly():
    _, _, calls = card(climate_payload(), action="climate_manual_mode")
    assert calls == []


def test_native_fixed_heat_cool_protects_the_shared_pump_but_keeps_override_release_available():
    payload = climate_payload()
    payload["manual_fixed_mode"] = True
    payload["zones"][1].update(mode="heat", action="heating")
    _, result, calls = card(payload, action="climate_manual")
    assert calls == []
    assert "disabled" in result.switch("climate_manual")
    payload["zones"][0]["dashboard_override"] = "off"
    _, result, calls = card(payload, action="climate_manual")
    assert "disabled" not in result.switch("climate_manual")
    assert calls == [expected_call("climate.salon", "automatic")]


def test_new_controller_shows_actual_pause_feedback_without_an_unused_coast_adjustment():
    payload = climate_payload()
    payload["coast_feedback"] = {"counts": {"correct": 2, "te_lang": 1},
                                  "adjustment_h": -2, "effective_min_coast_window_h": 8}
    _, result, _ = card(payload)
    assert "Correct" in result.text and "Te lang" in result.text
    assert "praktijkcontrole vergelijkt automatische pauzes" in result.text
    assert "Automatische fijnafstelling" not in result.text
    assert "effectief minimum" not in result.text


def test_reactive_source_coverage_without_a_model_curve_does_not_claim_no_comfort_crossing():
    payload = climate_payload()
    _, result, _ = card(payload)
    assert "Beschikbare voorspellingsdekking: 5 uur" in result.text
    assert "nog geen temperatuurvoorspelling beoordeeld" in result.text
    assert "geen grens binnen deze periode" not in result.text


@pytest.mark.parametrize("reported", ["auto", "off"])
def test_fault_review_adopts_reported_mode_through_custom_service_without_an_auto_off_command(reported):
    payload = climate_payload()
    payload["zones"][0].update(mode=reported, command_fault="Previous command unconfirmed",
                                 control_stage="command_uncertain")
    _, rendered, render_calls = card(payload)
    assert render_calls == []
    review = rendered.switch("climate_review")
    assert "disabled" not in review and "role" not in review
    assert "Gemelde stand behouden" in rendered.text
    assert "Neemt de gemelde stand handmatig over; verstuurt geen AUTO/UIT-opdracht" in rendered.text
    assert "disabled" in rendered.switch("climate_manual")
    _, _, calls = card(payload, action="climate_review")
    assert calls == [expected_call("climate.salon", "review")]
    assert all(call["domain"] != "climate" for call in calls)


@pytest.mark.parametrize("zone,global_state", [
    ({"valid": False}, {}), ({"action_known": False}, {}), ({"current": None}, {}),
    ({"mode": "unavailable"}, {}), ({"hvac_modes": ["auto"]}, {}),
    ({}, {"manual_fixed_mode": True}),
    ({}, {"pending_commands": [{"entity_id": "climate.living", "mode": "off"}]}),
])
def test_fault_review_requires_known_fresh_supported_report_and_no_pending_shared_mode(zone, global_state):
    payload = climate_payload()
    payload["zones"][0].update(command_fault="No confirmed command", **zone)
    payload.update(global_state)
    _, rendered, calls = card(payload, action="climate_review")
    assert "disabled" in rendered.switch("climate_review")
    assert calls == []


def test_fault_review_is_absent_and_direct_review_handler_is_inert_without_a_fault():
    _, rendered, calls = card(climate_payload(), action="climate_review")
    assert not any(button.get("data-action") == "climate_review" for button in rendered.buttons)
    assert calls == []


def test_fault_review_is_disabled_during_an_in_flight_card_service():
    payload = climate_payload()
    payload["zones"][0]["command_fault"] = "Needs review"
    _, rendered, calls = card(payload, action="climate_review", busy=True)
    assert "disabled" in rendered.switch("climate_review")
    assert calls == []
