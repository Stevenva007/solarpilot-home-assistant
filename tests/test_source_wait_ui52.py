"""Render real global notices with Node VM doubles and backend problem kinds.

These checks exercise the shipped JavaScript, not a browser or a live HA device.
"""
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[1]
CARD = ROOT / "custom_components/solar_pilot/frontend/solar-pilot-card.js"


class NoticeMarkup(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.parts = []
        self.notices = []
        self.actions = []
        self.feed(markup)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        classes = attrs.get("class", "").split()
        if tag == "div" and "notice" in classes:
            self.notices.append(classes)
        if tag == "button":
            self.actions.append(attrs.get("data-action"))

    def handle_data(self, data):
        self.parts.append(data)

    @property
    def text(self):
        return " ".join(self.parts)


def render_alerts(attributes, *, error=""):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to render the actual SolarPilot alerts")
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
  card._last = {attributes: input.attributes};
  card._error = input.error;
  card._hass = {states: {}, callService: () => { writes++; }};
  card._globalAlerts(card._ctx());
`, sandbox);
process.stdout.write(JSON.stringify({markup, writes: sandbox.writes}));
"""
    result = subprocess.run(
        [node, "-e", script, str(CARD)],
        input=json.dumps({"attributes": attributes, "error": error}),
        text=True, capture_output=True, check=True,
    )
    rendered = json.loads(result.stdout)
    assert rendered["writes"] == 0
    return rendered["markup"], NoticeMarkup(rendered["markup"])


@pytest.mark.parametrize("reason", [
    "Ontvochtiger kelder: actuele schakelstatus ontbreekt",
    "Ontvochtiger kelder: vermogensmeter is verouderd",
])
def test_source_wait_is_informational_and_explains_automatic_retry(reason):
    _, notice = render_alerts({
        "problem": reason, "problem_kind": "source_wait", "reset_entity": "button.reset",
    })
    assert "Automatische broncontrole" in notice.text
    assert reason in notice.text
    assert "SolarPilot controleert automatisch opnieuw zodra actuele gegevens beschikbaar zijn." in notice.text
    assert notice.notices == [["notice"]]
    assert "reset" not in notice.actions
    assert "Controle afronden" not in notice.text
    assert "handmatige controle" not in notice.text


@pytest.mark.parametrize("reason", [
    "Ontvochtiger kelder: vermogensmeter gebruikt een ongeldige eenheid",
    "Ontvochtiger kelder: vermogensmeter is ook aan een ander toestel gekoppeld",
])
def test_source_configuration_points_to_source_setup_without_useless_reset(reason):
    _, notice = render_alerts({
        "problem": reason, "problem_kind": "source_configuration", "reset_entity": "button.reset",
    })
    assert "Toestelgegevens controleren" in notice.text
    assert reason in notice.text
    assert "Controleer de gekoppelde bronnen en instellingen van dit toestel." in notice.text
    assert notice.notices == [["notice", "warn"]]
    assert "reset" not in notice.actions
    assert "Controle afronden" not in notice.text
    assert "automatisch opnieuw" not in notice.text


@pytest.mark.parametrize("kind", ["command_fault", "", "unknown_future_kind"])
def test_actual_command_fault_and_legacy_payload_keep_manual_check(kind):
    attributes = {"problem": "Ontvochtiger: uitschakelen niet bevestigd", "reset_entity": "button.reset"}
    if kind:
        attributes["problem_kind"] = kind
    _, notice = render_alerts(attributes)
    assert "Aandacht nodig" in notice.text
    assert "Ontvochtiger: uitschakelen niet bevestigd" in notice.text
    assert notice.notices == [["notice", "warn"]]
    assert notice.actions == ["reset"]
    assert "Controle afronden" in notice.text


@pytest.mark.parametrize("kind", ["source_wait", "source_configuration", "command_fault"])
def test_pending_restart_retains_automatic_recovery_precedence(kind):
    _, notice = render_alerts({
        "problem": "Herstartcontrole: wacht op Ontvochtiger kelder",
        "problem_kind": kind, "restart_recovery_pending": True,
        "reset_entity": "button.reset",
    })
    assert "Automatische herstartcontrole" in notice.text
    assert "Herstartcontrole: wacht op Ontvochtiger kelder" in notice.text
    assert notice.notices == [["notice"]]
    assert "reset" not in notice.actions
    assert "Automatische broncontrole" not in notice.text
    assert "Toestelgegevens controleren" not in notice.text


def test_wait_reason_is_escaped_and_independent_warnings_remain_visible():
    reason = '<img src=x onerror="bad()"> meter wacht'
    markup, notice = render_alerts({
        "problem": reason, "problem_kind": "source_wait", "reset_entity": "button.reset",
        "ems": {"legacy_conflicts": [{"name": "Oude <regelaar>"}]},
    }, error="Knop <geweigerd>")
    assert "<img" not in markup
    assert "&lt;img" in markup
    assert reason in notice.text
    assert "Oude <regelaar>" in notice.text
    assert "Knop <geweigerd>" in notice.text
    assert "Dubbele regeling geblokkeerd" in notice.text
    assert notice.notices == [["notice"], ["notice", "warn"]]
    assert "reset" not in notice.actions


def test_problem_kind_alone_does_not_create_a_stale_banner_or_reset_button():
    markup, notice = render_alerts({"problem": "", "problem_kind": "source_wait", "reset_entity": "button.reset"})
    assert markup == ""
    assert notice.actions == []
