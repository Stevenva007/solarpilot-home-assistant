"""Execute the real overview card with Node/DOM doubles, not a browser or HA.

The assertions cover displayed evidence and disclosure behavior. They do not
prove network delivery, browser layout, appliance operation or live acceptance.
"""
from html.parser import HTMLParser
import json
from pathlib import Path
import shutil
import subprocess
import time

import pytest


CARD = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot/frontend/solar-pilot-card.js"


def execute_card(payload):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node required to execute the actual overview card")
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},
  setTimeout:()=>0,clearTimeout:()=>{},requestAnimationFrame:callback=>callback(),input};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
const result=vm.runInContext(`(()=>{
  let writes=0;
  const card=Object.create(SolarPilotCard.prototype);
  card._hass={config:{time_zone:'Europe/Brussels'},callService:()=>{writes++;}};
  if(input.render){return {html:card._decisionBoard(input.render),writes};}
  const detail=spec=>({
    open:!!spec.open,textContent:spec.text||'',
    dataset:spec.key==null?{}:{uiKey:spec.key},
    getAttribute:name=>name==='data-ui-key'?(spec.key??null):null,
    hasAttribute:name=>name==='data-ui-key'&&spec.key!=null
  });
  let nodes=(input.before||[]).map(detail);
  card.shadowRoot={querySelectorAll:selector=>{
    if(selector==='details')return nodes;
    if(selector==='details[data-ui-key]')return nodes.filter(node=>node.hasAttribute('data-ui-key'));
    if(selector==='details:not([data-ui-key])')return nodes.filter(node=>!node.hasAttribute('data-ui-key'));
    throw new Error('Unexpected selector: '+selector);
  }};
  card._content=card.shadowRoot;
  card._view=input.view||'overview';card._lastRenderedView=input.previousView||'overview';
  const saved=card._captureUiState();
  nodes=(input.after||[]).map(detail);
  card._restoreUiState(saved);
  return {opened:nodes.map(node=>node.open),captured:saved!==null};
})()`,sandbox);
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run([node, "-e", script, str(CARD)], input=json.dumps(payload),
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


class Element:
    def __init__(self, tag, attributes=None):
        self.tag = tag
        self.attributes = dict(attributes or [])
        self.children = []

    def walk(self):
        yield self
        for child in self.children:
            if isinstance(child, Element):
                yield from child.walk()

    def text(self):
        return " ".join(child.text() if isinstance(child, Element) else child
                        for child in self.children)


class Markup(HTMLParser):
    def __init__(self, html):
        super().__init__(convert_charrefs=True)
        self.root = Element("root")
        self.stack = [self.root]
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        element = Element(tag, attrs)
        self.stack[-1].children.append(element)
        if tag not in {"br", "hr", "img", "input", "meta", "link", "wbr"}:
            self.stack.append(element)

    def handle_endtag(self, tag):
        for index in range(len(self.stack)-1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                break

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def board(**parts):
    context = {"a": {"mode": "solar"}, "devices": [], "panasonic": {},
               "sgBoost": {}, "smartClimate": {}, "wb": {}, "batteryFleet": {}}
    context.update(parts)
    result = execute_card({"render": context})
    assert result["writes"] == 0
    html = result["html"]
    return html, Markup(html).root


def article(root, name):
    return next(node for node in root.walk()
                if node.tag == "article" and name in node.text())


def explanation(row):
    return next(node for node in row.walk() if node.tag == "details"
                and "reason-details" in node.attributes.get("class", "").split())


def test_each_configured_consumer_has_an_independent_collapsed_why_disclosure():
    _, root = board(
        panasonic={"configured": True, "temperature_c": 48, "target_c": 50,
                   "zones": [{"entity_id": "climate.zone", "name": "Ruimte",
                              "mode": "off", "current": 22, "target": 21}]},
        sgBoost={"configured": True, "reason": "Rusttijd", "relay_on": False,
                 "relay_confirmed": True},
        devices=[{"id": "dehumidifier", "name": "Ontvochtiger", "kind": "switch",
                  "available": True, "on": False, "mode": "auto", "power_w": 0}],
        wb={"enabled": True, "activity_known": True, "power_w": 0},
        batteryFleet={"enabled": True, "control_enabled": False})
    rows = [article(root, name) for name in
            ("Warmtepomp — Panasonic-regeling", "Ontvochtiger", "Auto laden", "Batterij")]
    details = [explanation(row) for row in rows]
    keys = [node.attributes.get("data-ui-key") for node in details]
    assert all(keys) and len(set(keys)) == len(keys)
    assert all("open" not in node.attributes for node in details)
    assert all(any(child.tag == "summary" and "waarom" in child.text().lower()
                   for child in node.children if isinstance(child, Element))
               for node in details)
    assert "Ruimte" in explanation(rows[0]).text()


def test_open_consumer_and_nested_history_survive_reorder_and_a_changed_reason():
    result = execute_card({"before": [
        {"key": "consumer:a", "open": True, "text": "Wacht op zon"},
        {"key": "history:a", "open": True}, {"key": "consumer:b", "open": False}],
        "after": [{"key": "consumer:b"}, {"key": "consumer:new"},
                  {"key": "consumer:a", "text": "Andere reden na nieuwe meting"},
                  {"key": "history:a"}]})
    assert result == {"opened": [False, False, True, True], "captured": True}


def test_actual_rendered_consumer_keys_remain_stable_across_insertion_and_reordering():
    def device(identifier, name, reason):
        return {"id": identifier, "name": name, "kind": "switch", "available": True,
                "on": False, "mode": "auto", "power_w": 0, "reason": reason,
                "history": {"last_change": {"reason": "Vorige beslissing", "confirmed": True}}}

    first_a = device("a", "Ontvochtiger", "Wacht op zon")
    b = device("b", "Ventilator", "Wacht op voorrang")
    _, before = board(devices=[first_a, b])
    _, after = board(devices=[b, device("new", "Nieuw toestel", "Nieuwe regel"),
                              device("a", "Ontvochtiger", "Actuele reden is veranderd")])
    before_a = article(before, "Ontvochtiger")
    a_keys = {node.attributes["data-ui-key"] for node in before_a.walk() if node.tag == "details"}
    assert len(a_keys) == 2
    assert a_keys == {node.attributes["data-ui-key"]
                      for node in article(after, "Ontvochtiger").walk() if node.tag == "details"}
    assert explanation(article(before, "Ventilator")).attributes["data-ui-key"] == \
        explanation(article(after, "Ventilator")).attributes["data-ui-key"]
    old_nodes = [{"key": node.attributes["data-ui-key"], "open": node.attributes["data-ui-key"] in a_keys}
                 for node in before.walk() if node.tag == "details"]
    new_nodes = [{"key": node.attributes["data-ui-key"]}
                 for node in after.walk() if node.tag == "details"]
    restored = execute_card({"before": old_nodes, "after": new_nodes})["opened"]
    assert restored == [spec["key"] in a_keys for spec in new_nodes]


def test_new_consumer_cannot_inherit_a_removed_consumers_open_disclosure():
    result = execute_card({"before": [{"key": "consumer:removed", "open": True}],
                           "after": [{"key": "consumer:added"}]})
    assert result["opened"] == [False]


def test_unkeyed_legacy_details_have_a_separate_lane_from_reordered_consumers():
    result = execute_card({"before": [{"open": True}, {"key": "consumer:a", "open": True},
                                       {"open": False}],
                           "after": [{"key": "consumer:new"}, {"open": False},
                                     {"key": "consumer:a"}, {"open": False}]})
    assert result["opened"] == [False, True, True, False]


def test_a_changed_view_does_not_carry_open_disclosures_into_the_other_screen():
    result = execute_card({"view": "comfort", "previousView": "overview",
                           "before": [{"key": "consumer:a", "open": True}, {"open": True}],
                           "after": [{"key": "consumer:a"}, {"open": False}]})
    assert result == {"opened": [False, False], "captured": False}


def test_missing_saved_details_leave_new_disclosures_closed():
    result = execute_card({"before": [], "after": [{"key": "consumer:a"}, {}]})
    assert result["opened"] == [False, False]


def test_overview_device_why_contains_real_start_requirements_and_stability_wait():
    _, root = board(devices=[{
        "id": "one", "name": "Ontvochtiger", "kind": "switch", "available": True,
        "on": False, "mode": "auto", "power_w": 0,
        "start_diagnostics": {"summary": "Nog onvoldoende vermogen", "missing": ["minimum_rest"],
            "power": {"measurement_valid": True, "measured_free_w": 100,
                      "required_start_w": 350}, "stable_start": {"remaining_s": 25}},
        "start_requirements": {"minimum_rest": {"met": False, "remaining_s": 40}}}])
    text = explanation(article(root, "Ontvochtiger")).text()
    assert "350 W" in text and "100 W" in text
    assert "40 s" in text and "25 s" in text and "Nog onvoldoende vermogen" in text


def test_sg_explanation_uses_actual_block_reasons_and_no_retired_boiler_gates():
    _, root = board(panasonic={"configured": True, "temperature_c": 48, "target_c": 50},
                    sgBoost={"configured": True, "reason": "Wacht op rusttijd",
                             "blocked_reasons": ["Wacht nog 80 s op rusttijd"],
                             "rest_remaining_s": 80, "start_threshold_w": 3000})
    details = explanation(article(root, "Warmtepomp — Panasonic-regeling")).text()
    assert "Wacht nog 80 s op rusttijd" in details
    assert "3 kW" in details and "50 °C" in details
    assert "SolarPilot stelt voor" not in details and "doelverhogingen" not in details


def test_untrusted_device_diagnostics_names_and_keys_are_displayed_as_text():
    hostile = '<img src=x onerror="window.pwned=true">'
    html, root = board(devices=[{"id": hostile, "name": hostile, "kind": "switch",
                                "available": True, "on": False, "mode": "auto",
                                "reason": hostile, "start_diagnostics": {"summary": hostile}}])
    assert hostile in root.text()
    assert "<img" not in html and "&lt;img" in html
    assert not any(node.tag == "img" or "onerror" in node.attributes for node in root.walk())


@pytest.mark.parametrize("kind", ["sg", "panasonic", "wallbox", "battery"])
def test_regulation_diagnostics_cannot_insert_executable_markup(kind):
    hostile = '<img src=x onerror="window.pwned=true">'
    parts = {
        "sg": {"sgBoost": {"configured": True, "reason": hostile,
                            "blocked_reasons": [hostile]}},
        "panasonic": {"panasonic": {"configured": True, "program": hostile,
            "zones": [{"entity_id": "climate.zone", "name": hostile,
                       "mode": "off", "current": 22, "target": 21}]}},
        "wallbox": {"wb": {"enabled": True, "activity_known": True, "power_w": 0,
                            "activity_details": {"current": {"reason": hostile, "known": True}},
                            "consumer_priority": {"reason": hostile}}},
        "battery": {"batteryFleet": {"enabled": True, "control_enabled": True,
                                     "reason": hostile, "faults": {"one": hostile}}},
    }[kind]
    html, root = board(**parts)
    assert hostile in root.text()
    assert "<img" not in html and "&lt;img" in html
    assert not any(node.tag == "img" or "onerror" in node.attributes for node in root.walk())


@pytest.mark.parametrize("watts,estimated,expected", [
    (0, False, "0 W"), (320, False, "320 W"), (320, True, "320 W")])
def test_overview_distinguishes_measured_and_estimated_device_power(watts, estimated, expected):
    _, root = board(devices=[{"id": "one", "name": "Ontvochtiger", "kind": "switch",
                             "available": True, "on": watts > 0, "mode": "auto",
                             "power_w": watts, "estimated": estimated, "reason": "Toestelstatus"}])
    text = article(root, "Ontvochtiger").text()
    assert expected in text
    assert ("geschat" in text.lower() or "≈" in text) is estimated


def test_missing_device_power_and_rest_time_do_not_turn_into_zero_or_completed_wait():
    _, root = board(devices=[{"id": "one", "name": "Ontvochtiger", "kind": "switch",
                             "available": True, "on": False, "mode": "auto", "power_w": None,
                             "start_diagnostics": {"summary": "Wacht op ontbrekende informatie",
                                                   "missing": ["minimum_rest"]},
                             "start_requirements": {"minimum_rest": {"met": False, "remaining_s": None}}}])
    text = article(root, "Ontvochtiger").text()
    assert "0 W" not in text and "nog 0 s" not in text
    assert "onbekend" in text.lower() or "niet bekend" in text.lower() or "ontbreekt" in text.lower()


def test_actual_zero_rest_time_remains_zero_instead_of_unknown():
    _, root = board(devices=[{"id": "one", "name": "Ontvochtiger", "kind": "switch",
                             "available": True, "on": False, "mode": "auto", "power_w": 0,
                             "start_diagnostics": {"summary": "Wacht op zon", "missing": ["minimum_rest"]},
                             "start_requirements": {"minimum_rest": {"met": False, "remaining_s": 0}}}])
    assert "0 s" in explanation(article(root, "Ontvochtiger")).text()


def test_wallbox_unknown_status_does_not_invent_a_stop_reason_or_measured_zero():
    _, root = board(wb={"enabled": True, "activity_known": False, "power_w": None,
                       "reason": "Zonnevermogen verdelen", "consumer_priority": {"reason": "Voorrang voor boiler"}})
    text = article(root, "Auto laden").text()
    assert "ONBEKEND" in text and "0 W" not in text
    assert "Voorrang voor boiler" in text
    assert "Wallbox" in explanation(article(root, "Auto laden")).text()
    assert "boiler stopte" not in text.lower()


def test_battery_execution_fault_is_not_hidden_by_a_positive_planning_advice():
    _, root = board(batteryFleet={"enabled": True, "control_enabled": True,
                                  "reason": "Planner adviseert laden", "faults": {"one": "Opdracht niet bevestigd"},
                                  "pending": {}, "aggregate": {"valid": True, "charge_w": 0, "discharge_w": 0}})
    text = article(root, "Batterij").text()
    assert "Controle nodig" in text and "Opdracht niet bevestigd" in text
    assert "Planner adviseert laden" in text


def test_battery_pending_acknowledgement_is_distinct_from_a_charging_advice():
    _, root = board(batteryFleet={"enabled": True, "control_enabled": True,
                                  "reason": "Advies: laden met zonneoverschot",
                                  "pending": {"id": "one", "target_w": -1000,
                                              "issued_wall": time.time(), "kind": "number"},
                                  "faults": {},
                                  "batteries": [{"id": "one", "name": "Thuisbatterij"}],
                                  "aggregate": {"valid": True, "power_w": 0,
                                                "charge_w": 0, "discharge_w": 0}})
    text = article(root, "Batterij").text()
    assert "Wacht op bevestiging" in text
    details = explanation(article(root, "Batterij")).text()
    assert details.count("Thuisbatterij: wacht op bevestiging") == 1
    assert "Batterij: wacht op bevestiging" not in details
    assert "issued_wall" not in details and "target_w" not in details
    assert "Advies: laden met zonneoverschot" in text
    assert "Batterij laadt" not in text and "1 kW" not in text
    assert "0 W" in text


def test_null_battery_journal_does_not_invent_a_pending_command():
    _, root = board(batteryFleet={"enabled": True, "control_enabled": True,
                                  "reason": "Advies: laad later", "pending": None, "faults": {},
                                  "batteries": [{"id": "one", "name": "Thuisbatterij"}],
                                  "aggregate": {"valid": True, "power_w": 0,
                                                "charge_w": 0, "discharge_w": 0}})
    text = article(root, "Batterij").text()
    assert "Wacht op bevestiging" not in text and "wacht op bevestiging" not in text
    assert "Advies: laad later" in text and "Regeling aan" in text


def test_shared_heatpump_meter_is_shown_once_and_not_attributed_to_each_room():
    _, root = board(panasonic={"configured": True, "temperature_c": 48, "target_c": 50,
        "power_w": 1234, "power_kind": "measured", "power_scope": "total", "zones": [
            {"entity_id": "climate.a", "name": "Ruimte A", "mode": "auto", "current": 21},
            {"entity_id": "climate.b", "name": "Ruimte B", "mode": "auto", "current": 21}]},
        sgBoost={"configured": True, "reason": "Zonneboost actief", "relay_confirmed": True, "relay_on": True})
    meters = [node for node in root.walk() if "reason-power" in node.attributes.get("class", "").split()]
    assert len(meters) == 1 and "1,23 kW" in meters[0].text()
    assert "Totaal warmtepomp" in meters[0].text()
    zones = [node for node in root.walk() if "zone" in node.attributes.get("class", "").split()]
    assert len(zones) == 2 and all("1,23 kW" not in zone.text() for zone in zones)


@pytest.mark.parametrize("value,kind", [(None, "measured"), (1234, "unknown"), (None, "unknown")])
def test_unreliable_or_expired_shared_meter_is_not_presented_as_measured_power(value, kind):
    _, root = board(panasonic={"configured": True, "power_w": value,
                              "power_kind": kind, "power_scope": "total"})
    meter = next(node for node in root.walk() if "reason-power" in node.attributes.get("class", "").split())
    assert "1,23 kW" not in meter.text() and "niet bekend" in meter.text()
    assert "0 W" not in meter.text()


def test_partial_supply_meter_is_labeled_and_not_claimed_as_a_heatpump_total():
    _, root = board(panasonic={"configured": True, "power_w": 800,
                              "power_kind": "measured", "power_scope": "supply_1"})
    row = article(root, "Warmtepomp — Panasonic-regeling")
    assert "800 W" in row.text() and "Alleen voeding 1 · gedeeltelijke meting" in row.text()
    assert "Totaal warmtepomp" not in row.text()


def test_readonly_room_information_does_not_resurrect_removed_climate_planning():
    _, root = board(panasonic={"configured": True, "zones": [
        {"entity_id": "climate.zone", "name": "Ruimte", "mode": "off", "current": 22, "target": 21,
         "execution_reason": "Vervallen klimaatopdracht", "decision_reason": "Vervallen klimaatplan"}]},
        sgBoost={"configured": True, "reason": "Geen extra zonneboost nodig"})
    content = article(root, "Warmtepomp — Panasonic-regeling").text()
    assert "Geen extra zonneboost nodig" in content and "Ruimte" in content
    assert "Vervallen klimaatopdracht" not in content and "Vervallen klimaatplan" not in content
