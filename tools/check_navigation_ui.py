"""Real browser Back/Forward against local fictitious data; never Home Assistant.

The intercepted example origin has no external network, real options saves or
physical services. Navigation stores no options data in browser history.
"""
from collections import deque
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("SOLARPILOT_SCREENSHOT_DIR", "/tmp/solarpilot-navigation-ui"))
OUT.mkdir(parents=True, exist_ok=True)
errors = []
answers = deque()
prompts = []


def respond(dialog):
    prompts.append(dialog.message)
    if answers and answers.popleft():
        dialog.accept()
    else:
        dialog.dismiss()


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=shutil.which("chromium"), headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 1000}, locale="nl-BE")
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("dialog", respond)
    page.route("**/*", lambda route: route.fulfill(status=200, content_type="text/html", body=(ROOT / "SolarPilot-voorbeeld.html").read_text(encoding="utf-8")))
    page.goto("http://solarpilot.example.test/dashboard", wait_until="load")
    page.wait_for_selector("solar-pilot-card >> h1")
    page.evaluate("""() => {
      window.c=document.querySelector('solar-pilot-card');window.apiCalls=[];window.actuatorCalls=[];window.wsCalls=[];
      history.replaceState({hass:{route:'untouched',index:17},foreignValue:'HA blijft intact'},'',location.href);
      const a=structuredClone(c._last.attributes);a.config_entry_id='fictitious-navigation';
      const menu=(step,options)=>({type:'menu',flow_id:'fixture-flow-'+window.flowCount,step_id:step,menu_options:options});
      const form=(step,schema)=>({type:'form',flow_id:'fixture-flow-'+window.flowCount,step_id:step,errors:{},data_schema:schema});
      window.flowCount=0;
      window.fixtureApi=async(method,path,data)=>{
        apiCalls.push({method,path,data});if(method==='delete'){if(window.holdDelete){window.holdDelete=false;return new Promise(resolve=>window.releaseDelete=()=>resolve({}));}return {};}
        if(path==='config/config_entries/options/flow'){flowCount++;return menu('init',['energy_hub','loads_hub']);}
        if(data.next_step_id==='energy_hub'){
          if(window.holdMenu){window.holdMenu=false;return new Promise(resolve=>window.releaseMenu=()=>resolve(menu('energy_hub',['settings'])));}
          return menu('energy_hub',['settings']);
        }
        if(data.next_step_id==='loads_hub')return menu('loads_hub',['manage_device']);
        if(data.next_step_id==='manage_device')return form('manage_device',[]);
        if(data.next_step_id==='settings')return form('settings',[{name:'reserve_w',required:true,default:150,selector:{number:{min:0,max:5000,step:10}}}]);
        if('reserve_w' in data)return form('apply_changes',[{name:'confirm',required:true,default:false,selector:{boolean:{}}}]);
        throw Error('Fictitious probe refuses unexpected payload, including saves.');
      };
      c.hass={...c._hass,user:{is_admin:true},callApi:(...args)=>fixtureApi(...args),callService:async(...args)=>{actuatorCalls.push(args);throw Error('No physical services in this probe');},callWS:async m=>{
        wsCalls.push(m);if(m.type==='solar_pilot/priority_board')return{revision:'fixture-revision',order:['device:fixture','wallbox'],rows:[{id:'device:fixture',name:'Fictief toestel',active:true},{id:'wallbox',name:'Auto laden',active:true}],wallbox_power:{'device:fixture':false},protected:[],constraints:[],note:'Fictieve browserproef'};
        throw Error('Read-only fixture: no real history, learning or PV server');
      },states:{...c._hass.states,[c._entity]:{state:'Fictief voorbeeld',attributes:a}}};
      window.initialLength=history.length;
    }""")
    url = page.url
    card = page.locator("solar-pilot-card").first

    # Actual browser history navigation, not synthetic popstate events.
    card.locator("button[role=tab][data-value=loads]").click()
    card.locator("button[role=tab][data-value=energy]").click()
    page.go_back()
    page.wait_for_function("c._view==='loads'")
    page.go_forward()
    page.wait_for_function("c._view==='energy'")
    assert page.url == url
    assert page.evaluate("history.state.hass.index===17 && history.state.foreignValue==='HA blijft intact'")
    before = page.evaluate("history.length")
    page.evaluate("""() => {for(let n=0;n<100;n++){const a=structuredClone(c._last.attributes);a.grid_w=-1000-n;c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Fictief',attributes:a}}};}}""")
    assert page.evaluate("history.length") == before

    # Popup Back closes nested help first; drafts survive a rejected discard.
    card.locator("button[data-action=configure]").click()
    options = page.locator("solar-pilot-options-dialog")
    page.wait_for_selector("solar-pilot-options-dialog >> button[data-menu=energy_hub]")
    assert options.locator(".back").is_visible()
    options.locator("[data-menu=energy_hub]").click()
    options.locator("[data-menu=settings]").click()
    options.locator("[name=reserve_w]").fill("170")
    options.locator("button[data-help=reserve_w]").click()
    nested = options.locator("solar-pilot-option-help-dialog")
    assert nested.locator("dialog").is_visible()
    page.go_back()
    page.wait_for_function("!c._optionsDialog.helpDialog.dialog.open")
    assert options.locator("dialog").first.is_visible()
    assert options.locator("[name=reserve_w]").input_value() == "170"
    current = page.evaluate("history.state.solarPilotUi.entry")
    api_before = page.evaluate("apiCalls.length")
    answers.append(False)
    page.go_back()
    page.wait_for_function("history.state.solarPilotUi.entry===c._uiHistory.constructor.bus.cursor && c._optionsDialog.dialog.open")
    assert page.evaluate("history.state.solarPilotUi.entry") == current
    assert options.locator("[name=reserve_w]").input_value() == "170"
    assert page.evaluate("apiCalls.length") == api_before
    answers.append(True)
    page.go_back()
    page.wait_for_function("c._optionsDialog.flow?.step_id==='energy_hub' && !c._optionsDialog._busy")
    # Forward opens a NEW native menu flow, never old form values/submissions.
    page.go_forward()
    page.wait_for_selector("solar-pilot-options-dialog >> button[data-menu=settings]")
    assert options.locator("[name=reserve_w]").count() == 0
    assert "Je eerdere invoer is niet teruggezet" in options.locator(".content").inner_text()
    assert page.evaluate("apiCalls.filter(x=>x.data&&'reserve_w' in x.data).length") == 0
    options.locator(".close").first.click()
    page.wait_for_function("!c._optionsDialog.dialog.open && !c._uiHistory.constructor.bus.moving")

    # Visible Back returns to the parent menu through fresh menu-only requests.
    card.locator("button[data-action=configure]").click()
    options.locator("[data-menu=energy_hub]").click()
    options.locator("[data-menu=settings]").click()
    options.locator("[name=reserve_w]").fill("190")
    api_before = page.evaluate("apiCalls.length")
    answers.append(False)
    options.locator(".back").click()
    assert options.locator("[name=reserve_w]").input_value() == "190"
    assert page.evaluate("apiCalls.length") == api_before
    answers.append(True)
    options.locator(".back").click()
    page.wait_for_selector("solar-pilot-options-dialog >> button[data-menu=settings]")
    calls = page.evaluate("apiCalls.slice(-3)")
    assert [call["method"] for call in calls] == ["delete", "post", "post"]
    assert calls[-1]["data"] == {"next_step_id": "energy_hub"}
    options.locator(".back").click()
    page.wait_for_selector("solar-pilot-options-dialog >> button[data-menu=energy_hub]")
    assert options.locator(".back").get_attribute("aria-label") == "Terug naar SolarPilot"
    # A genuine outstanding native request prevents browser Back from closing.
    page.evaluate("window.holdMenu=true")
    options.locator("[data-menu=energy_hub]").click()
    page.wait_for_function("c._optionsDialog._busy && typeof releaseMenu==='function'")
    assert options.locator(".back").is_disabled()
    page.go_back()
    page.wait_for_function("history.state.solarPilotUi.entry===c._uiHistory.constructor.bus.cursor && c._optionsDialog.dialog.open")
    page.evaluate("releaseMenu()")
    page.wait_for_selector("solar-pilot-options-dialog >> button[data-menu=settings]")
    # Staged wizard submission must not be replayed when going back.
    options.locator("[data-menu=settings]").click()
    options.locator("[name=reserve_w]").fill("180")
    options.locator("button[type=submit]").click()
    page.wait_for_selector("solar-pilot-options-dialog >> [name=confirm]")
    staged_before = page.evaluate("apiCalls.filter(x=>x.data&&'reserve_w' in x.data).length")
    answers.append(True)
    options.locator(".back").click()
    page.wait_for_selector("solar-pilot-options-dialog >> button[data-menu=settings]")
    assert page.evaluate("apiCalls.filter(x=>x.data&&'reserve_w' in x.data).length") == staged_before == 1
    options.locator(".close").first.click()
    page.wait_for_function("!c._optionsDialog.dialog.open")
    page.wait_for_function("history.state.solarPilotUi.entry===c._uiHistory.constructor.bus.cursor")

    # Browser/mouse Back follows the settings hierarchy before leaving the popup.
    card.locator("button[data-action=configure]").click()
    options.locator("[data-menu=energy_hub]").click()
    options.locator("[data-menu=settings]").click()
    page.evaluate("window.holdDelete=true;window.flowsBeforeDeletion=flowCount")
    page.go_back()
    page.wait_for_function("typeof releaseDelete==='function' && c._uiHistory.constructor.bus.applying")
    assert page.evaluate("flowCount===flowsBeforeDeletion")
    page.evaluate("releaseDelete()")
    page.wait_for_function("c._optionsDialog.flow?.step_id==='energy_hub' && !c._optionsDialog._busy")
    page.go_back()
    page.wait_for_function("c._optionsDialog.flow?.step_id==='init' && !c._optionsDialog._busy")
    page.go_back()
    page.wait_for_function("!c._optionsDialog.dialog.open")
    page.go_forward()
    page.wait_for_function("c._optionsDialog.flow?.step_id==='init' && !c._optionsDialog._busy")
    page.go_forward()
    page.wait_for_function("c._optionsDialog.flow?.step_id==='energy_hub' && !c._optionsDialog._busy")
    page.go_forward()
    page.wait_for_function("c._optionsDialog.content.textContent.includes('Je eerdere invoer is niet teruggezet')")
    assert options.locator("[name=reserve_w]").count() == 0
    options.locator(".close").first.click()
    page.wait_for_function("!c._optionsDialog.dialog.open && !c._uiHistory.constructor.bus.moving")

    # X and Escape consume popup entries, so another Back reaches the prior TAB.
    card.locator("button[role=tab][data-value=overview]").click()
    card.locator("button[role=tab][data-value=loads]").click()
    page.evaluate("c._openHelp('device','priority','Fictieve navigatie-uitleg')")
    page.wait_for_function("c._helpDialog?.dialog.open")
    page.keyboard.press("Escape")
    page.wait_for_function("!c._helpDialog.dialog.open && history.state.solarPilotUi.entry===c._uiHistory.constructor.bus.cursor")
    page.go_back()
    page.wait_for_function("c._view==='overview'")
    page.go_forward()
    page.wait_for_function("c._view==='loads'")
    page.evaluate("c._openHelp('device','priority','Fictieve navigatie-uitleg')")
    page.wait_for_function("c._helpDialog?.dialog.open")
    page.locator("solar-pilot-option-help-dialog >> dialog[open] >> .close").click()
    page.wait_for_function("!c._helpDialog.dialog.open && history.state.solarPilotUi.entry===c._uiHistory.constructor.bus.cursor")
    page.go_back()
    page.wait_for_function("c._view==='overview'")

    # All modal types participate; no writes are replayed on Forward.
    for open_method, field in (("_openPV()", "_pvDialog"), ("_openLearning()", "_learningDialog"), ("_openAnalysis()", "_analysisDialog"), ("_openDevices()", "_deviceManager"), ("_openHistory(c._last.attributes.devices[0])", "_historyDialog")):
        page.evaluate(f"c.{open_method}")
        page.wait_for_function(f"(c.{field}.dialog||c.{field}._dialog).open")
        page.go_back()
        page.wait_for_function(f"!(c.{field}.dialog||c.{field}._dialog).open")
        page.go_forward()
        page.wait_for_function(f"(c.{field}.dialog||c.{field}._dialog).open")
        page.evaluate(f"c.{field}.close()")
        page.wait_for_function(f"!(c.{field}.dialog||c.{field}._dialog).open && history.state.solarPilotUi.entry===c._uiHistory.constructor.bus.cursor")
    page.evaluate("c._openPriorities()")
    page.wait_for_function("c._priorityDialog.dialog.open && !c._priorityDialog._busy")
    priority = page.locator("solar-pilot-priority-dialog")
    priority.locator("select[data-power='device:fixture']").select_option("yes")
    answers.append(False)
    page.go_back()
    page.wait_for_function("history.state.solarPilotUi.entry===c._uiHistory.constructor.bus.cursor && c._priorityDialog.dialog.open")
    assert priority.locator("select[data-power='device:fixture']").input_value() == "yes"
    page.evaluate("c._priorityDialog._saving=true")
    page.go_back()
    page.wait_for_function("history.state.solarPilotUi.entry===c._uiHistory.constructor.bus.cursor && c._priorityDialog.dialog.open")
    page.evaluate("c._priorityDialog._saving=false")
    answers.append(True)
    page.go_back()
    page.wait_for_function("!c._priorityDialog.dialog.open")

    # More than one card: changing B must not reset A or close A's popup.
    page.evaluate("""() => {window.c2=document.createElement('solar-pilot-card');c2.setConfig({entity:c._entity});document.body.append(c2);c2.hass=c._hass;}""")
    page.evaluate("c._uiHistory.view('loads');c2._uiHistory.view('planning')")
    page.go_back()
    page.wait_for_function("c2._view==='overview' && c._view==='loads'")
    page.go_forward()
    page.wait_for_function("c2._view==='planning' && c._view==='loads'")
    page.evaluate("c2._openHelp('device','priority','Tweede fictieve kaart')")
    page.wait_for_function("c2._helpDialog.dialog.open")
    page.go_back()
    page.wait_for_function("!c2._helpDialog.dialog.open && c._view==='loads' && c2._view==='planning'")
    length_before = page.evaluate("history.length")
    state_before = page.evaluate("history.state")
    page.evaluate("c2.remove()")
    assert page.evaluate("history.length") == length_before
    assert page.evaluate("history.state") == state_before
    assert page.evaluate("c._uiHistory.constructor.bus.cards.size") == 1

    # Own navigation payload contains only an opaque session/entry marker.
    assert set(page.evaluate("history.state.solarPilotUi")) == {"session", "entry"}
    assert page.evaluate("history.state.hass.index===17 && history.state.foreignValue==='HA blijft intact'")
    assert page.evaluate("actuatorCalls.length") == 0
    assert page.evaluate("apiCalls.filter(x=>x.data?.confirm===true).length") == 0
    assert all(call.get("data", {}).get("device_id") is None for call in page.evaluate("apiCalls") if isinstance(call.get("data"), dict))
    # Responsive visible Back control and no overflow.
    page.evaluate("c._openOptions()")
    page.wait_for_selector("solar-pilot-options-dialog >> button[data-menu=energy_hub]")
    for width in (320, 390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 900})
        assert options.locator(".back").is_visible()
        assert options.locator("dialog").first.evaluate("el=>el.scrollWidth<=el.clientWidth+1"), width
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), width
    page.set_viewport_size({"width": 1440, "height": 1000})
    page.screenshot(path=str(OUT / "SolarPilot-navigatie-instellingen-voorbeeld.png"))
    options.locator("[data-menu=energy_hub]").click()
    options.locator("[data-menu=settings]").click()
    options.locator("[name=reserve_w]").fill("210")
    prompts_before = len(prompts)
    state_before = page.evaluate("history.state")
    length_before = page.evaluate("history.length")
    page.evaluate("c.remove()")
    assert len(prompts) == prompts_before
    assert page.evaluate("history.length") == length_before
    assert page.evaluate("history.state") == state_before
    assert page.evaluate("c._uiHistory.constructor.bus.listener===null")
    assert not errors, errors
    browser.close()

print("OK: echte Back/Forward, zichtbare instellingen-Terug, veilige menu-only flow, wijzigings-/opslaanbeveiliging, X/Escape zonder spookstappen, meerdere kaarten, HA-status behouden, 100 updates zonder geschiedenisgroei, 4 schermbreedtes, geen actuatoraanroepen.")
