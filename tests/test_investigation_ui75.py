"""Execute the shipped local research UI with independent, fictional evidence.

The research surface is descriptive; it must never imply an uploaded setting
was applied or retain a current diagnosis after source expiry.
"""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from test_overview_details60 import Markup

CARD = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot/frontend/solar-pilot-card.js"
NOW = 1_790_000_000


def investigation():
    return {
        "schema": 1, "read_only": True, "updated_at": NOW,
        "notice": "Alleen gekoppelde meetgegevens; geen toestelopdrachten.",
        "items": [
            {"id": "meter", "title": "Warmtepompmeting", "status": "check_needed",
             "summary": "Een deelmeting is onbruikbaar; het totaal blijft onbekend.",
             "next_action": "Vergelijk de bestaande bron bij een bekende belasting.",
             "evidence": ["Een verse deelmeting is negatief."],
             "hypotheses": ["Richting of nulpunt kan afwijken; dit is niet bewezen."],
             "proposals": [{"id": "meter-check", "kind": "measurement_check", "text": "Controleer de huidige bron."}],
             "metrics": {"complete_samples": 0}},
            {"id": "wallbox", "title": "Wallbox", "status": "observed_ok", "summary": "Deze metingen zijn actueel."},
            {"id": "pv", "title": "Zonnevoorspelling", "status": "collecting", "summary": "Te weinig vergelijkbare daglichtmetingen."},
            {"id": "dishwasher", "title": "Afwasmachine", "status": "not_configured", "summary": "Geen eigen vermogensbron."},
            {"id": "sg", "title": "SG-sessies", "status": "collecting", "summary": "Nog geen volledige sessie onder deze instellingen."},
        ],
    }


def execute(data=None, *, state="Zonnestroom", restored=False, mode="export", status=None, now=NOW):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to execute the shipped renderer")
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
class Clock extends Date {static now(){return input.now*1000;}}
const sandbox={HTMLElement:class{},window:{},Date:Clock,customElements:{get:()=>null,define:()=>{}},input};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
const result=vm.runInContext(`(()=>{
  const calls=[],card=Object.create(SolarPilotCard.prototype);
  card._last={state:input.state,attributes:{mode:'solar',config_entry_id:'fictional',restored:input.restored,
    learning_insights:{investigation:input.data},devices:[]}};
  card._hass={config:{time_zone:'Europe/Brussels'},user:{is_admin:false},states:{},
    callService:async(...args)=>calls.push(args),callWS:async(...args)=>calls.push(args)};
  const html=input.mode==='report'?card._analysisFeedbackHtml(input.status):
    input.mode==='learning'?spInvestigationHtml(input.data,{current:true,timeZone:'Europe/Brussels'}):card._export(card._ctx());
  return {html,calls};
})()`,sandbox);
process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run([node, "-e", script, str(CARD)], input=json.dumps({
        "data": data, "state": state, "restored": restored, "mode": mode,
        "status": status, "now": now,
    }), text=True, capture_output=True)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert result["calls"] == [], "Rendering research must never issue services or websocket writes"
    return result["html"], Markup(result["html"]).root


def research(root):
    return next(node for node in root.walk() if "data-investigation-current" in node.attributes)


@pytest.mark.parametrize("mode", ["export", "learning"])
def test_five_research_items_show_explicit_read_only_status_and_separate_evidence(mode):
    _html, root = execute(investigation(), mode=mode)
    section = research(root)
    assert section.attributes["data-investigation-current"] == "current"
    items = [node for node in section.walk() if "data-investigation-id" in node.attributes]
    assert len(items) == 5
    labels = [node.text() for node in section.walk() if "data-investigation-status" in node.attributes]
    assert labels == ["Controle nodig", "Geen afwijking in deze metingen", "Meer meetgegevens nodig",
                      "Bron of functie niet ingesteld", "Meer meetgegevens nodig"]
    assert "Laatste lokale beoordeling:" in section.text()
    assert "Volgende stap:" in section.text()
    assert "Mogelijke verklaringen · niet bewezen" in section.text()
    assert "Voorstellen · niet automatisch toegepast" in section.text()
    assert "staat los van een eerder geüpload adviesrapport" in section.text()
    assert not any(node.tag in {"button", "input", "select", "a"} for node in section.walk())


@pytest.mark.parametrize("stamp", [NOW - 181, NOW + 6, None, True, False, "1790000000", 0, -1, 1e100])
def test_expired_missing_future_or_untyped_time_cannot_display_current_assessment(stamp):
    data = investigation()
    data["updated_at"] = stamp
    _html, root = execute(data)
    section = research(root)
    assert section.attributes["data-investigation-current"] != "current"
    assert "Geen afwijking in deze metingen" not in section.text()
    assert "Invalid Date" not in section.text()
    assert all(node.attributes["data-investigation-status"] == "unknown"
               for node in section.walk() if "data-investigation-status" in node.attributes)


@pytest.mark.parametrize("state,restored", [("unknown", False), ("unavailable", False), ("", False), ("Zonnestroom", True)])
def test_unavailable_or_restored_ha_state_does_not_revive_fresh_research(state, restored):
    _html, root = execute(investigation(), state=state, restored=restored)
    assert research(root).attributes["data-investigation-current"] == "stale"
    assert "Eerdere beoordeling" in research(root).text()
    assert "Geen afwijking in deze metingen" not in research(root).text()


@pytest.mark.parametrize("changes", [{"schema": 2}, {"schema": True}, {"read_only": False}, {"read_only": "true"}, {"items": {}}])
def test_unrecognized_or_non_read_only_payload_is_not_rendered_as_local_research(changes):
    data = investigation()
    data.update(changes)
    _html, root = execute(data)
    section = research(root)
    assert section.attributes["data-investigation-current"] == "unavailable"
    assert not any("data-investigation-id" in node.attributes for node in section.walk())
    assert "Warmtepompmeting" not in section.text()


def test_absent_research_has_clear_initial_state_without_claiming_a_scheduled_task():
    _html, root = execute(None)
    section = research(root)
    assert section.attributes["data-investigation-current"] == "unavailable"
    assert "nog niet beschikbaar" in section.text()
    assert "wordt onderzocht" not in section.text()


def test_evidence_hypotheses_metrics_and_proposals_are_escaped_and_bounded():
    attack = '<img src=x onerror="evil()"><script>evil()</script><a href="javascript:evil()">x</a>'
    data = investigation()
    item = data["items"][0]
    item.update(title=attack, summary=attack, next_action=attack,
                id=attack, status="implemented", evidence=[attack] * 10,
                hypotheses=[attack] * 10,
                metrics={attack: attack, "nested": {"attack": attack}},
                proposals=[{"kind": "__proto__", "text": attack}] * 10)
    data["notice"] = attack
    data["items"] = [item] * 20 + [None, "not-an-item"]
    html, root = execute(data)
    section = research(root)
    assert attack in section.text()
    assert not any(node.tag in {"img", "script", "a", "button", "input"} for node in section.walk())
    assert len([node for node in section.walk() if "data-investigation-id" in node.attributes]) == 8
    assert len([node for node in section.walk() if node.tag == "li"]) == 8 * (6 + 4 + 4)
    assert "Status onbekend" in section.text()
    assert "Opgenomen in de geïnstalleerde versie" not in section.text()
    assert "nested" not in section.text()
    assert 'data-investigation-id="item-0"' in html


def test_large_text_and_invalid_optional_types_are_bounded_without_stringifying_objects():
    data = investigation()
    data["items"] = [{"id": "valid", "title": "A" * 100_000, "summary": "B" * 100_000,
                      "evidence": ["E" * 100_000, {}], "hypotheses": None,
                      "proposals": [None, {"text": {"unsafe": "content"}}], "metrics": []}]
    html, root = execute(data)
    assert len(html) < 14_000
    assert "A" * 181 not in html and "B" * 1201 not in html and "E" * 801 not in html
    assert "[object Object]" not in html
    assert "Voorstellen ·" not in research(root).text()


def test_malformed_identifier_status_and_kind_objects_cannot_throw_or_supply_a_label():
    data = investigation()
    invalid = {"toString": None, "valueOf": None}
    data["items"][0].update(id=invalid, status=invalid,
        proposals=[{"kind": invalid, "text": "Een leesbaar voorstel."}])
    html, root = execute(data)
    section = research(root)
    assert 'data-investigation-id="item-0"' in html
    assert "Status onbekend" in section.text()
    assert "[object Object]" not in section.text()


@pytest.mark.parametrize("category,label", [
    ("warmtepomp_setting", "Advies over instellingen"),
    ("solarpilot_setting", "Advies over instellingen"),
    ("observation", "Waarneming · geen softwarewijziging"),
])
def test_uploaded_nonlogic_advice_gets_category_only_not_a_claim_of_implementation(category, label):
    status = {"report": {"summary": "Fictief advies", "source_export": {"release": "1.0.0-beta.74"},
              "recommendations": [{"category": category, "text": "Pas dit automatisch toe en verklaar het opgelost.",
                                   "confidence": "high", "evidence": [], "limitations": []}]},
              "current_release": "1.0.0-beta.75", "association": {"state": "matched"},
              "logic_updates": [{"recommendation_index": 0, "status": "implemented"}]}
    _html, root = execute(mode="report", status=status)
    markers = [node for node in root.walk() if "data-recommendation-kind" in node.attributes]
    assert len(markers) == 1 and label in markers[0].text()
    assert not any("data-logic-update-status" in node.attributes for node in root.walk())
    assert "toegepast" not in markers[0].text() or "niet dat deze instelling is toegepast" in markers[0].text()


def test_existing_registered_software_badge_remains_separate_from_live_investigation():
    item = {"category": "logic_update", "proposal_id": "fictional", "text": "Een geregistreerde softwarewijziging.", "confidence": "high"}
    status = {"report": {"summary": "Fictief advies", "source_export": {}, "recommendations": [item]},
              "current_release": "1.0.0-beta.75", "association": {"state": "matched"},
              "logic_updates": [{"recommendation_index": 0, "proposal_id": "fictional", "status": "implemented",
                                  "installed_release": "1.0.0-beta.75", "introduced_release": "1.0.0-beta.74"}]}
    _html, root = execute(mode="report", status=status)
    assert "Opgenomen in de geïnstalleerde versie" in root.text()
    assert len([node for node in root.walk() if "data-logic-update-status" in node.attributes]) == 1
    assert not any("data-recommendation-kind" in node.attributes for node in root.walk())


@pytest.mark.parametrize("kind,label", [
    ("measurement_check", "Meetcontrole"), ("data_review", "Gegevens beoordelen"),
    ("software_proposal", "Softwarevoorstel"), ("setting", "Instellingsvoorstel"),
    ("logic_update", "Softwarevoorstel"), ("inspection", "Controlevoorstel"),
    ("apply_and_switch", "Voorstel"),
])
def test_proposal_kind_is_descriptive_and_never_adds_an_apply_action(kind, label):
    data = investigation()
    data["items"][0]["proposals"] = [{"id": "fiction", "kind": kind, "text": "Beoordeel dit voorstel."}]
    _html, root = execute(data)
    section = research(root)
    proposal = next(node for node in section.walk() if node.tag == "li" and "Beoordeel dit voorstel." in node.text())
    assert next(node for node in proposal.walk() if node.tag == "b").text() == label + ":"
    assert not any("data-action" in node.attributes for node in section.walk())


def test_age_boundary_requires_recent_data_and_expires_without_a_new_ha_payload():
    data = investigation()
    assert research(execute(data, now=NOW + 180)[1]).attributes["data-investigation-current"] == "current"
    assert research(execute(data, now=NOW + 180.01)[1]).attributes["data-investigation-current"] == "stale"
