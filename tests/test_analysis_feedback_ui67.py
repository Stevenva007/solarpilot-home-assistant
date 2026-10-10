"""Read-only analysis feedback UI, local file bounds and escaped report text."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from test_overview_details60 import Markup

CARD = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot/frontend/solar-pilot-card.js"
NODE = shutil.which("node")

SCRIPT = r"""
const fs=require('fs'),vm=require('vm');
const args=JSON.parse(fs.readFileSync(0,'utf8')),definitions=new Map();
const context={HTMLElement:class {},window:{},customElements:{get:key=>definitions.get(key),define:(key,value)=>definitions.set(key,value)},
  Blob,URL,Date,setTimeout:()=>0,clearTimeout:()=>{},setInterval:()=>0,clearInterval:()=>{},
  CustomEvent:class{constructor(type,opts){this.type=type;this.detail=opts?.detail;}},console};
vm.createContext(context);vm.runInContext(fs.readFileSync(args.path,'utf8')+'\n globalThis.Card=SolarPilotCard;globalThis.Quality=SolarPilotLearningDialog;globalThis.Analysis=SolarPilotAnalysisDialog;',context);
(async()=>{
 const card=Object.create(context.Card.prototype),calls=[],serviceCalls=[],events=[];
 let readCount=0,renders=0;
 card._last={state:'Zonnestroom',attributes:{config_entry_id:'fictitious-entry',learning_insights:{open_questions:2,findings:[{title:'Fictieve bevinding',message:'Meetkwaliteit controleren'}]}}};
 card._hass={user:{id:'example-admin',is_admin:args.admin!==false},callService:async(...x)=>serviceCalls.push(x),callWS:async message=>{calls.push(message);if(args.wsError)throw new Error(args.wsError);return args.status??{report:null};}};
 card._render=()=>renders++;
 let html='';
 if(args.case==='render')html=card._analysisFeedbackHtml(args.status);
 if(args.case==='banner')html=card._analysisBanner(card._last.attributes);
 if(args.case==='action')await card._analysisFeedbackAction(args.action,args.content);
 if(args.case==='import')await card._importAnalysisFeedback({size:args.size,text:async()=>{readCount++;if(args.readError)throw new Error(args.readError);return args.content;}});
 if(args.case==='changed_user'){
   let resolve;const reading=card._importAnalysisFeedback({size:100,text:()=>{readCount++;return new Promise(done=>resolve=done);}});
   card._hass.user={id:'different-admin',is_admin:true};resolve(args.content);await reading;
 }
 if(args.case==='quality'){
   const q=Object.create(context.Quality.prototype);q._scroll={scrollTop:0};q._body={innerHTML:'',querySelectorAll:()=>[]};
   q._render({questions:[{id:'never-render-choice',title:'OLD QUESTION',choices:[{id:'apply',label:'APPLY NOW'}]}],policy:{adaptation:'automatic'},models:[]});html=q._body.innerHTML;
 }
 if(args.case==='download'){
   const dialog=Object.create(context.Analysis.prototype),elements={'.download':{},'.template':{},'.status':{},'.hours':{value:'168'},'.names':{checked:false}};
   dialog.shadowRoot={querySelector:key=>elements[key]};dialog._hass=card._hass;dialog._entryId='fictitious-entry';dialog._seq=0;dialog._open=true;
   dialog.dispatchEvent=e=>events.push(e.type);context.document={body:{appendChild:()=>{}},createElement:()=>({click:()=>{},remove:()=>{}})};
   await dialog._download();html=elements['.status'].textContent;
 }
 if(!html&&args.case!=='download')html=card._export(card._ctx());
 process.stdout.write(JSON.stringify({html,calls,serviceCalls,readCount,renders,error:card._analysisFeedbackError??'',reading:card._analysisFeedbackReading===true,events}));
})().catch(error=>{console.error(error);process.exitCode=1;});
"""


def run(case, **kwargs):
    if not NODE:
        pytest.skip("node required for card behaviour")
    result = subprocess.run([NODE, "-e", SCRIPT], input=json.dumps({"path": str(CARD), "case": case, **kwargs}),
                            capture_output=True, text=True, check=True)
    answer = json.loads(result.stdout)
    assert not answer["serviceCalls"], "Analysis feedback must never call a device service"
    return answer


def report():
    return {"schema": "solarpilot.analysis_feedback", "schema_version": 1,
            "source_export": {"export_id": "export_" + "a" * 32, "export_sha256": "b" * 64,
                              "release": "1.0.0-beta.67", "created_at": "2026-10-10T12:00:00Z"},
            "analyzed_at": "2026-10-10T13:00:00Z", "summary": "Fictieve samenvatting",
            "question_answers": [], "recommendations": [], "limitations": []}


def test_size_is_checked_before_reading_any_file_or_sending_it():
    for size in [0, -1, 1048577, "1048577"]:
        result = run("import", size=size, content=json.dumps(report()))
        assert result["readCount"] == 0 and result["calls"] == []
        assert "maximaal 1 MiB" in result["error"]
    result = run("import", size=1048576, content=json.dumps(report()))
    assert result["readCount"] == 1 and len(result["calls"]) == 1


@pytest.mark.parametrize("content", ["{", "null", "[]", '{"schema":"solarpilot.analysis","schema_version":1}'])
def test_invalid_local_json_does_not_reach_import_api(content):
    result = run("import", size=100, content=content)
    assert result["calls"] == [] and result["error"]
    assert not result["reading"]


@pytest.mark.parametrize("action", ["status", "remove"])
def test_admin_only_status_and_removal_use_feedback_api_not_device_services(action):
    result = run("action", action=action)
    assert result["calls"] == [{"type": "solar_pilot/analysis_feedback", "config_entry_id": "fictitious-entry", "action": action}]
    assert run("action", action=action, admin=False)["calls"] == []


def test_import_sends_original_json_once_and_does_not_apply_recommendations():
    content = json.dumps(report())
    result = run("import", size=len(content), content=content)
    assert result["calls"] == [{"type": "solar_pilot/analysis_feedback", "config_entry_id": "fictitious-entry", "action": "import", "content": content}]
    result = run("import", admin=False, size=len(content), content=content)
    assert result["readCount"] == 0 and result["calls"] == []
    assert "beheerder" in result["html"]


def test_file_read_started_by_another_user_cannot_import_after_user_changes():
    result = run("changed_user", content=json.dumps(report()))
    assert result["readCount"] == 1 and result["calls"] == []


def test_report_and_errors_are_text_not_html_links_scripts_or_controls():
    value = '<img src=x onerror="evil()"><script>evil()</script><a href="javascript:evil()">x</a>'
    data = report()
    data.update(summary=value, limitations=[value], question_answers=[{"question_id": value, "answer": value, "outcome": "needs_more_data"}])
    data["recommendations"] = [{"category": "logic_update", "text": value, "evidence": [value], "limitations": [value], "confidence": "high"}]
    result = run("render", status={"report": data, "association": {"state": "unverified", "reason": value}, "source_release_matches_current": False})
    root = Markup(result["html"]).root
    assert not any(node.tag in {"img", "script", "a", "input", "select", "button"} for node in root.walk())
    assert value in root.text()
    assert "Bronkoppeling niet bevestigd" in root.text()
    assert "andere SolarPilot-versie" in root.text()
    assert "Meer gegevens nodig" in root.text()
    error = run("import", size=100, content=json.dumps(report()), wsError=value)
    assert not any(node.tag in {"img", "script", "a"} for node in Markup(error["html"]).root.walk())


def test_matched_provenance_is_not_presented_as_recommendation_approval():
    result = run("render", status={"report": report(), "association": {"state": "matched", "reason": "Exacte bronmatch"}})
    assert 'data-analysis-association="matched"' in result["html"]
    assert "bevestigt alleen de herkomst" in result["html"]


def test_logic_status_matches_exact_recommendation_index_and_id_not_uploaded_status():
    data = report()
    data["recommendations"] = [
        {"category": "observation", "text": "Geen softwarevoorstel"},
        {"category": "logic_update", "proposal_id": "same-id", "text": "Geteste inhoud", "status": "pending"},
        {"category": "logic_update", "proposal_id": "same-id", "text": "Gewijzigde inhoud", "status": "implemented"},
        {"category": "logic_update", "proposal_id": "not-in-catalog", "text": "Nieuw voorstel", "status": "implemented"},
    ]
    rows = [{"recommendation_index": 1, "proposal_id": "same-id", "status": "implemented",
             "introduced_release": "1.0.0-beta.67", "installed_release": "1.0.0-beta.67", "summary": "Publieke wijziging"},
            {"recommendation_index": 2, "proposal_id": "same-id", "status": "pending",
             "introduced_release": "1.0.0-beta.67", "installed_release": "1.0.0-beta.67", "reason": "proposal_content_changed"},
            {"recommendation_index": 3, "proposal_id": "wrong-id", "status": "implemented"}]
    result = run("render", status={"report": data, "logic_updates": rows, "current_release": "1.0.0-beta.67"})
    states = [node.attributes["data-logic-update-status"] for node in Markup(result["html"]).root.walk()
              if "data-logic-update-status" in node.attributes]
    assert states == ["implemented", "pending", "untracked"]
    assert "inhoud van dit advies verschilt" in result["html"]
    assert "Geïnstalleerd: 1.0.0-beta.67" in result["html"]


def test_missing_trusted_status_index_does_not_match_by_reused_id_alone():
    data = report()
    data["recommendations"] = [{"category": "logic_update", "proposal_id": "same-id", "text": "Andere inhoud"}]
    result = run("render", status={"report": data, "logic_updates": [{"proposal_id": "same-id", "status": "implemented"}]})
    assert 'data-logic-update-status="untracked"' in result["html"]
    assert 'data-logic-update-status="implemented"' not in result["html"]


def test_analysis_needed_banner_and_quality_dialog_have_no_question_or_policy_choices():
    banner = run("banner")["html"]
    assert "Analyse nodig" in banner and "Maak analysebestand" in banner and "Antwoord uploaden" in banner
    assert "Leren &amp; vragen" not in banner and "leervragen" not in banner
    quality = run("quality")["html"]
    assert "OLD QUESTION" not in quality and "APPLY NOW" not in quality
    assert not any(node.tag in {"button", "select", "input"} for node in Markup(quality).root.walk())


def test_one_click_analysis_requests_seven_days_with_default_pseudonyms():
    result = run("download", status={"filename": "fictitious.json", "content": "{}"})
    assert result["calls"] == [{"type": "solar_pilot/analysis_export", "config_entry_id": "fictitious-entry", "hours": 168, "include_names": False, "download": True}]
    assert "gedownload" in result["html"]
    assert run("download", admin=False)["calls"] == []
