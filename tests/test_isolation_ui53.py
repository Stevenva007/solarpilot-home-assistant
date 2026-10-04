"""Render the shipped card with device-local isolation and independent blockers.

Node VM checks execute actual frontend methods; they are not browser or HA tests.
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
        self.buttons = {}
        self.notices = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "button" and attributes.get("data-action"):
            self.buttons[attributes["data-action"]] = attributes
        classes = attributes.get("class", "").split()
        if tag == "div" and "notice" in classes:
            self.notices.append(classes)

    def handle_data(self, data):
        self.parts.append(data)

    @property
    def text(self):
        return " ".join(self.parts)


def render(method, attributes=None, device=None):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to render the actual SolarPilot card")
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
  card._hass = {states: {}, callService: () => { writes++; }};
  input.device ? card[input.method](input.device, input.attributes.mode || 'solar')
    : card[input.method](card._ctx());
`, sandbox);
process.stdout.write(JSON.stringify({markup, writes: sandbox.writes}));
"""
    result = subprocess.run(
        [node, "-e", script, str(CARD)], text=True, capture_output=True, check=True,
        input=json.dumps({"method": method, "attributes": attributes or {}, "device": device}),
    )
    rendered = json.loads(result.stdout)
    assert rendered["writes"] == 0
    return rendered["markup"], Markup(rendered["markup"])


def isolated_attributes(**extra):
    return {
        "mode": "solar", "problem_kind": "source_wait", "problem": "Offline status",
        "reset_entity": "button.reset", "restart_recovery_pending": False,
        "isolated_devices": [{"id": "offline", "name": "Offline load", "reason": "Control status unavailable", "reserve_w": 350}],
        "isolated_reserve_w": 350, **extra,
    }


def load(**extra):
    return {
        "id": "offline", "name": "Offline load", "kind": "switch", "mode": "auto",
        "available": False, "on": True, "owned": True, "power_w": 0,
        "isolated": True, "isolation_reason": "Control status unavailable",
        "isolation_reserve_w": 350, **extra,
    }


def test_isolation_is_informational_and_does_not_block_healthy_auto_or_offer_reset():
    _, result = render("_globalAlerts", isolated_attributes())
    assert result.notices == [["notice"]]
    assert "Toestel tijdelijk apart gehouden" in result.text
    assert "Offline load: Control status unavailable" in result.text
    assert "Andere beschikbare toestellen kunnen automatisch verder zodra hun eigen voorwaarden zijn gehaald." in result.text
    assert "SolarPilot controleert automatisch opnieuw." in result.text
    assert "Veiligheidsreserve voor mogelijk verbruik: 350 W" in result.text
    assert "Dit is geen gemeten verbruik." in result.text
    assert "Automatische broncontrole" not in result.text
    assert "reset" not in result.buttons


def test_pending_local_restart_lease_uses_isolation_notice_without_global_start_block():
    _, result = render("_globalAlerts", isolated_attributes(
        problem_kind="restart_wait", restart_recovery_pending=True, restart_blocking=False))
    assert result.notices == [["notice"]]
    assert "Toestel tijdelijk apart gehouden" in result.text
    assert "Andere beschikbare toestellen kunnen automatisch verder" in result.text
    assert "Automatische herstartcontrole" not in result.text
    assert "reset" not in result.buttons


def test_explicit_site_restart_hold_is_not_hidden_by_local_isolation():
    _, result = render("_globalAlerts", isolated_attributes(
        problem_kind="restart_wait", restart_recovery_pending=True, restart_blocking=True))
    assert len(result.notices) == 2
    assert "Automatische herstartcontrole" in result.text
    assert "Toestel tijdelijk apart gehouden" in result.text


@pytest.mark.parametrize("mode", ["observe", "paused"])
def test_isolation_does_not_claim_auto_running_while_mode_is_not_auto(mode):
    _, result = render("_globalAlerts", isolated_attributes(mode=mode))
    assert "Toestel tijdelijk apart gehouden" in result.text
    assert "Andere beschikbare toestellen kunnen automatisch verder" not in result.text
    assert "reset" not in result.buttons


@pytest.mark.parametrize(("kind", "restart", "title", "has_reset"), [
    ("command_fault", False, "Aandacht nodig", True),
    ("source_configuration", False, "Toestelgegevens controleren", False),
    ("restart_review", True, "Automatische herstartcontrole", False),
])
def test_independent_blockers_are_not_hidden_by_isolation(kind, restart, title, has_reset):
    _, result = render("_globalAlerts", isolated_attributes(problem_kind=kind, restart_recovery_pending=restart))
    assert title in result.text and "Toestel tijdelijk apart gehouden" in result.text
    assert ("reset" in result.buttons) is has_reset
    assert len(result.notices) == 2


def test_isolation_names_reasons_and_other_warnings_are_escaped():
    attributes = isolated_attributes(
        isolated_devices=[{"id": "offline", "name": '<img src=x onerror="bad()">', "reason": "Unavailable <source>", "reserve_w": 350}],
        ems={"legacy_conflicts": [{"name": "Legacy <control>"}]},
    )
    markup, result = render("_globalAlerts", attributes)
    assert "<img" not in markup and "&lt;img" in markup
    assert "Unavailable <source>" in result.text
    assert "Legacy <control>" in result.text and "Dubbele regeling geblokkeerd" in result.text
    assert "reset" not in result.buttons


@pytest.mark.parametrize("on", [True, False])
@pytest.mark.parametrize("power", [0, 350])
def test_offline_device_is_unknown_without_fake_off_active_or_measured_power(on, power):
    markup, result = render("_deviceCard", {"mode": "solar"}, load(on=on, power_w=power))
    assert "STATUS ONBEKEND" in result.text
    assert '<strong class="devicepower">onbekend</strong>' in markup
    assert "De actuele activiteit is onbekend." in result.text
    assert "ACTIEF ·" not in result.text and "Waarom dit toestel nu actief is" not in result.text
    assert "minimale looptijd, rusttijd en overige voorwaarden" in result.text
    assert "Dit is geen gemeten verbruik." in result.text
    assert "disabled" in result.buttons["manual_start"] and "disabled" in result.buttons["boost"]


def test_offline_manual_stop_button_is_disabled():
    _, result = render("_deviceCard", {"mode": "solar"}, load(manual_forced=True))
    assert "disabled" in result.buttons["manual_stop"]


def test_meter_only_isolation_preserves_confirmed_activity_without_claiming_measured_watts():
    device = load(available=True, power_w=350, estimated=True, isolation_reason="Power report unavailable")
    markup, result = render("_deviceCard", {"mode": "solar"}, device)
    assert "ACTIEF · SOLARPILOT" in result.text
    assert "Het toestel meldt zijn activiteit" in result.text
    assert "De actuele activiteit is onbekend." not in result.text
    assert '<strong class="devicepower">onbekend</strong>' in markup
    assert "VERBRUIKT" not in result.text
    assert "disabled" in result.buttons["manual_start"] and "disabled" in result.buttons["boost"]
    _, active = render("_activeLoads", {"devices": [device]})
    assert "ACTIEF · SOLARPILOT" in active.text
    assert "vermogen onbekend" in active.text
    assert "gemeten vermogen" not in active.text and "geschat vermogen" not in active.text


def test_healthy_device_keeps_start_and_boost_controls_and_measured_power():
    markup, result = render("_deviceCard", {"mode": "solar"}, load(available=True, isolated=False, on=False, power_w=350))
    assert "UIT" in result.text and "Toestel tijdelijk apart gehouden" not in result.text
    assert '<strong class="devicepower">350 W</strong>' in markup
    assert "disabled" not in result.buttons["manual_start"] and "disabled" not in result.buttons["boost"]


def test_isolated_dishwasher_never_claims_measured_power_or_allows_arming_from_old_readiness():
    device = load(kind="dishwasher", dishwasher={"ready": True, "phase": "Running"})
    markup, result = render("_deviceCard", {"mode": "solar"}, device)
    assert "ONBEKEND" in result.text and "PROGRAMMA ACTIEF" not in result.text
    assert '<b class="power">onbekend</b>' in markup
    assert "disabled" in result.buttons["dishwasher_arm"]
    assert "gemeten" not in result.text or "geen gemeten verbruik" in result.text


def test_summary_labels_partial_device_power_without_turning_reserve_into_measured_total():
    markup, result = render("_overview", isolated_attributes(managed_w=0, grid_w=300, free_w=0, pv_w=500, reserve_w=150))
    assert "Deel van de toestelgegevens ontbreekt; mogelijk verbruik wordt apart gereserveerd." in result.text
    assert '<span>Bekend vermogen SolarPilot-toestellen</span><strong>0 W</strong>' in markup
    assert '<span>Bekend vermogen SolarPilot-toestellen</span><strong>350 W</strong>' not in markup


def test_recovery_requirement_is_device_specific_instead_of_claiming_all_starts_blocked():
    device = load(available=True, isolated=False, on=False, start_requirements={"recovery_clear": {"met": False}},
                  start_diagnostics={"missing": ["recovery_clear"], "summary": "Device recovery"})
    _, result = render("_deviceCard", {"mode": "solar"}, device)
    assert "De herstartcontrole voor dit toestel is nog bezig." in result.text
    assert "SolarPilot start nog geen toestel" not in result.text
