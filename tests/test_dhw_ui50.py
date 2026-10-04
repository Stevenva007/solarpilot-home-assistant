"""Render the real boiler card with native reports and pending policy proposals."""
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


def render_boiler(dhw, view):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to render the actual JavaScript boiler card")
    script = r"""
const fs = require('node:fs'), vm = require('node:vm');
const definitions = new Map();
const sandbox = {
  HTMLElement: class {}, window: {}, writes: 0,
  customElements: {get: key => definitions.get(key), define: (key, value) => definitions.set(key, value)},
  input: JSON.parse(fs.readFileSync(0, 'utf8'))
};
vm.createContext(sandbox);
vm.runInContext(fs.readFileSync(process.argv[1], 'utf8'), sandbox);
const markup = vm.runInContext(`
  const card = Object.create(SolarPilotCard.prototype);
  card._last = {attributes: {mode: 'solar', pv_w: 6040, grid_w: -5140,
    managed_w: 310, free_w: 4990, reserve_w: 150, devices: [], dhw: input.dhw}};
  card._hass = {states: {}, callService: () => { writes++; }};
  card[input.view](card._ctx());
`, sandbox);
process.stdout.write(JSON.stringify({markup, writes: sandbox.writes}));
"""
    result = subprocess.run(
        [node, "-e", script, str(CARD)],
        input=json.dumps({"dhw": dhw, "view": view}),
        text=True, capture_output=True, check=True,
    )
    rendered = json.loads(result.stdout)
    assert rendered["writes"] == 0
    markup = rendered["markup"]
    return markup, RenderedText(markup).text


def boiler_payload():
    return {
        "configured": True, "enabled": True, "safety_confirmed": True,
        "control_allowed": True, "panasonic_autonomous": True,
        "temperature_c": 50, "actual_target_c": 50, "proposed_target_c": 60,
        "normal_target_c": 50, "minimum_c": 46, "expected_restart_c": 45,
        "reason": "Voldoende werkelijk zonneoverschot; geen actieve of onzekere koeling",
    }


@pytest.mark.parametrize("view", ["_overview", "_dhw"])
@pytest.mark.parametrize(("status", "extra"), [
    ("Extra zonnebuffer wacht nog 1230 s tussen doelverhogingen; Panasonic blijft regelen",
     {"optional_raise_remaining_s": 1230}),
    ("Voldoende werkelijk zonneoverschot; wacht op andere regelopdracht", {}),
    ("Boilerdoel niet uitvoerbaar: toestel ondersteunt deze temperatuur niet", {}),
    ("Wacht op boilerbevestiging (12 s)", {"pending": True}),
])
def test_actual_card_shows_dispatch_wait_without_claiming_proposal_is_native(view, status, extra):
    dhw = boiler_payload()
    dhw.update(status=status, **extra)
    markup, text = render_boiler(dhw, view)
    assert status in text
    assert "aangevraagd" not in text
    if view == "_overview":
        assert "50 °C → 50 °C" in text
        assert "50 °C → 60 °C" not in text
        assert "SolarPilot-voorstel: 60 °C (niet het gemelde toesteldoel)" in text
    else:
        assert '<span>SolarPilot-voorstel</span><strong>60 °C</strong>' in markup
        assert '<span>Panasonic-doel</span><strong>50 °C</strong>' in markup


@pytest.mark.parametrize("view", ["_overview", "_dhw"])
def test_actual_card_keeps_stability_wait_readable(view):
    dhw = boiler_payload()
    dhw.update(proposed_target_c=50, remaining_s=35,
               status=dhw["reason"] + "; stabiliteitscontrole nog 35 s")
    _, text = render_boiler(dhw, view)
    assert "stabiliteitscontrole nog 35 s" in text
    assert "SolarPilot-voorstel: 60 °C" not in text


@pytest.mark.parametrize("view", ["_overview", "_dhw"])
def test_actual_card_uses_policy_reason_for_older_payload_without_status(view):
    dhw = boiler_payload()
    markup, text = render_boiler(dhw, view)
    assert dhw["reason"] in text
    assert "Boilerregeling wacht" not in text
    if view == "_overview":
        assert "50 °C → 50 °C" in text
    else:
        assert '<span>Panasonic-doel</span><strong>50 °C</strong>' in markup


@pytest.mark.parametrize("view", ["_overview", "_dhw"])
def test_actual_card_does_not_replace_missing_protected_status_with_positive_policy_reason(view):
    dhw = boiler_payload()
    dhw.update(control_allowed=False, manual_hold=True)
    _, text = render_boiler(dhw, view)
    assert "Boilerregeling wacht; gemeld toesteldoel blijft leidend" in text
    assert dhw["reason"] not in text


@pytest.mark.parametrize("view", ["_overview", "_dhw"])
def test_actual_card_escapes_runtime_wait_reason(view):
    dhw = boiler_payload()
    dhw["status"] = '<img src=x onerror="bad()"> wacht'
    markup, text = render_boiler(dhw, view)
    assert "<img" not in markup
    assert "&lt;img" in markup
    assert dhw["status"] in text


@pytest.mark.parametrize("view", ["_overview", "_dhw"])
def test_actual_card_shows_confirmed_native_target_without_extra_proposal_annotation(view):
    dhw = boiler_payload()
    dhw.update(actual_target_c=60, status="Boilerdoel bevestigd; Panasonic blijft autonoom regelen")
    markup, text = render_boiler(dhw, view)
    assert dhw["status"] in text
    assert "niet het gemelde toesteldoel" not in text
    if view == "_overview":
        assert "50 °C → 60 °C" in text
    else:
        assert '<span>Panasonic-doel</span><strong>60 °C</strong>' in markup
