"""Render the actual climate card in Node; no Home Assistant or device writes."""
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "custom_components/solar_pilot/frontend/solar-pilot-card.js"


class RenderedText(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.parts = []
        self.feed(markup)

    def handle_data(self, data):
        self.parts.append(data)

    @property
    def text(self):
        return " ".join(self.parts)


def render_climate(payload):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to render the actual JavaScript climate card")
    script = r"""
const fs = require('node:fs'), vm = require('node:vm');
const definitions = new Map();
const sandbox = {
  HTMLElement: class {}, window: {},
  customElements: {get: key => definitions.get(key), define: (key, value) => definitions.set(key, value)},
  climatePayload: JSON.parse(fs.readFileSync(0, 'utf8'))
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);
process.stdout.write(vm.runInContext('Object.create(SolarPilotCard.prototype)._climate({smartClimate: climatePayload})', sandbox));
"""
    result = subprocess.run(
        [node, "-e", script, str(CARD)],
        input=json.dumps(payload), text=True, capture_output=True, check=True,
    )
    return result.stdout, RenderedText(result.stdout).text


def climate_payload():
    return {
        "enabled": True, "control_enabled": True,
        "season_context": "winter",
        "decision": {"mode": "auto", "reason": "Duidelijke wintercontext", "hard_override": False},
        "settings": {"decision_interval_h": 12, "model_confidence_min": 0.55},
        "zones": [{"entity_id": "climate.salon", "name": "Kapsalon", "current": 22, "target": 21, "mode": "off", "action": "off"}],
        "profiles": {}, "alerts": [],
    }


def learned_component(samples=20, confidence=0.98, need=6):
    return {"samples": samples, "confidence": confidence, "required_samples": need,
            "status": "Betrouwbaar" if samples else "Nog niet geleerd"}


def add_passive_profile(payload, *, heating_ready=False):
    readiness = {
        "forecast_confidence": 0.98,
        "confidence": 0.98 if heating_ready else 0,
        "control_ready": heating_ready,
        "required_components": ["passive_temperature_change", "heating_response", "response_delay"],
        "missing_components": [] if heating_ready else ["heating_response", "response_delay"],
        "block_reason": "" if heating_ready else "Wacht op bruikbare verwarmingsrespons en reactievertraging.",
        "directions": ["heating"],
    }
    payload["decision"].update({
        "forecast_confidence": readiness["forecast_confidence"],
        "control_ready": readiness["control_ready"],
        "required_components": readiness["required_components"],
        "missing_components": readiness["missing_components"],
        "block_reason": readiness["block_reason"],
        "readiness_by_zone": {"climate.salon": readiness},
        "predicted_min_c": 21.4, "predicted_max_c": 22,
    })
    payload["profiles"] = {"climate.salon": {
        "samples": 633, "days": 7,
        # Keep the complete model conservative: no cooling evidence yet.
        "confidence": 0, "reliability_status": "Eerste metingen",
        "confidence_components": {
            "passive_temperature_change": learned_component(40, need=12),
            "solar_gain": learned_component(20, need=12),
            "heating_response": learned_component(10 if heating_ready else 0),
            "cooling_response": learned_component(0),
            "response_delay": learned_component(5 if heating_ready else 0, need=4),
        },
    }}


def test_actual_card_explains_learned_passive_model_and_missing_heating_evidence():
    payload = climate_payload()
    add_passive_profile(payload)
    payload["zones"][0]["manual_off"] = True
    markup, text = render_climate(payload)
    assert "Panasonic beschikbaar laten" in text
    assert "Dit advies is geen actuele verwarmings- of koelvraag" in text
    assert "Model voor pauzeren" in text and "Wacht op metingen" in text
    assert "voorspelling tijdens pauze 98%" in text
    assert "Wacht op bruikbare verwarmingsrespons en reactievertraging" in text
    assert "633 temperatuurmetingen" in text and "7 dagen" in text
    assert "Betrouwbaar · 98%" in text and "40 / 12 bruikbare metingen" in text
    assert "Nodig; nog onvoldoende metingen" in text
    assert "Niet nodig voor deze beslissing" in text
    assert "Handmatig uit · blijft uit" in text
    assert "Thermisch model 0%" not in text
    assert "AUTO vrijgeven" not in text
    assert "class=\"climate-model\"" in markup


def test_actual_card_can_show_heating_ready_without_claiming_cooling_was_learned():
    payload = climate_payload()
    add_passive_profile(payload, heating_ready=True)
    markup, text = render_climate(payload)
    assert "Voldoende geleerd" in text
    assert "Wacht op metingen" not in text
    assert "Respons bij koelen" in text and "Nog niet geleerd" in text
    assert "0 / 6 bruikbare metingen" in text
    assert "geen algemene 100%-score" not in text
    assert "Geen verwarmings- of koelvraag" not in markup  # Actual activity is OFF.


def test_actual_card_distinguishes_reported_mode_from_pending_command():
    payload = climate_payload()
    payload["pending_commands"] = [{"entity_id": "climate.salon", "name": "Kapsalon", "mode": "auto", "remaining_s": 25}]
    markup, text = render_climate(payload)
    assert "Wacht op bevestiging: Automatisch" in text
    assert "Uit" in text and "Niet actief" in text
    assert "off · off" not in markup
    assert "AUTO/COAST AAN" not in text


def test_actual_card_reports_unknown_activity_instead_of_inventing_idle():
    payload = climate_payload()
    payload["zones"][0].update(mode="auto", action="idle", action_known=False)
    markup, text = render_climate(payload)
    assert "Activiteit onbekend" in text
    assert "<small>Geen verwarmings- of koelvraag</small>" not in markup
    assert "Je hoeft geen warmte of koeling te forceren" in text


def test_actual_card_escapes_model_reason_zone_name_and_component_status():
    payload = climate_payload()
    add_passive_profile(payload)
    payload["zones"][0]["name"] = '<img src=x onerror="bad()">'
    payload["decision"]["block_reason"] = "<script>bad()</script>"
    payload["profiles"]["climate.salon"]["confidence_components"]["heating_response"]["status"] = "<svg onload=bad()>"
    markup, text = render_climate(payload)
    assert "<img" not in markup and "<script" not in markup and "<svg" not in markup
    assert "&lt;img" in markup and "&lt;script" in markup and "&lt;svg" in markup


def test_actual_card_keeps_previous_payload_and_fixed_modes_readable():
    payload = climate_payload()
    payload["manual_fixed_mode"] = True
    payload["zones"][0].update(mode="heat", action="heating")
    payload["reliability"] = {"automatic_coast": {"confidence": 0, "status": "Eerste metingen"}}
    _, text = render_climate(payload)
    assert "Eerste metingen" in text
    assert "Handmatige Panasonic-stand actief" in text
    assert "Een handmatige HEAT/COOL-stand wordt door SolarPilot met rust gelaten" in text
    assert "Verwarmen" in text and "Verwarmt" in text


def test_actual_card_does_not_mistake_season_block_for_missing_model_evidence():
    payload = climate_payload()
    add_passive_profile(payload, heating_ready=True)
    payload["decision"].update(control_ready=False, block_reason="Winterpauzes staan uit; Panasonic blijft beschikbaar.")
    _, text = render_climate(payload)
    assert "Nu niet pauzeren" in text
    assert "Winterpauzes staan uit" in text
    assert "Wacht op metingen" not in text


def test_actual_card_identifies_missing_forecast_as_a_source_problem():
    payload = climate_payload()
    add_passive_profile(payload, heating_ready=True)
    payload["decision"].update(control_ready=False, missing_components=["hourly_forecast"], block_reason="Geen bruikbare uurvoorspelling beschikbaar.")
    _, text = render_climate(payload)
    assert "Wacht op uurvoorspelling" in text
    assert "Geen bruikbare uurvoorspelling beschikbaar" in text
    assert "Wacht op metingen" not in text


def test_actual_card_identifies_missing_solar_forecast_without_resetting_learned_model():
    payload = climate_payload()
    add_passive_profile(payload, heating_ready=True)
    payload["decision"].update(control_ready=False, missing_components=["solar_forecast"], block_reason="PV-verwachting voor de pauze ontbreekt.")
    payload["decision"]["readiness_by_zone"]["climate.salon"]["missing_components"]=["solar_forecast"]
    payload["solar_gain"] = {"next_24h_kwh_proxy": None, "peak_w_proxy": None}
    _, text = render_climate(payload)
    assert "Wacht op PV-verwachting" in text
    assert "PV-verwachting voor de pauze ontbreekt" in text
    assert "Wacht op metingen" not in text
    assert "Betrouwbaar · 98%" in text
    assert "Nog geen bruikbare zonneproxy" in text
    assert "PV-verwachting Actuele voorspellingsbron" in text
    assert "Bewaarde modelmetingen blijven behouden" in text


def test_actual_card_reports_both_missing_forecasts_as_source_problems():
    payload = climate_payload()
    add_passive_profile(payload, heating_ready=True)
    payload["decision"].update(control_ready=False, missing_components=["hourly_forecast", "solar_forecast"], block_reason="Uurvoorspelling en PV-verwachting ontbreken.")
    _, text = render_climate(payload)
    assert "Wacht op voorspellingen" in text
    assert "Wacht op metingen" not in text


def test_actual_card_keeps_missing_learning_visible_when_solar_forecast_is_also_missing():
    payload = climate_payload()
    add_passive_profile(payload)
    payload["decision"]["missing_components"].append("solar_forecast")
    _, text = render_climate(payload)
    assert "Wacht op metingen" in text
    assert "Wacht op PV-verwachting" not in text


def test_actual_card_limits_temperature_prediction_to_evaluated_forecast_hours():
    payload = climate_payload()
    add_passive_profile(payload, heating_ready=True)
    payload["settings"]["horizon_h"]=48
    payload["decision"]["evaluated_forecast_h"]=8
    _, text = render_climate(payload)
    assert "Alleen de komende 8 uur beoordeeld" in text
    assert "geen grens binnen deze periode" in text
    assert "komende 48" not in text


def test_actual_card_does_not_claim_a_checked_comfort_horizon_without_forecast():
    payload = climate_payload()
    payload["decision"]["evaluated_forecast_h"]=0
    _, text = render_climate(payload)
    assert "Geen bruikbare voorspellingshorizon" in text
    assert "geen temperatuurgrens beoordeeld" in text
