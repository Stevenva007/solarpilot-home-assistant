"""Chromium regression of mobile options drafts and native flow confirmation.

The keyboard is represented by a reduced visual viewport. Sources, users and
entries are fictitious; all requests stay inside the fixture and no services run.
"""
import json
import os
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("SOLARPILOT_SCREENSHOT_DIR", "/tmp/solarpilot-browser-tests"))
OUT.mkdir(parents=True, exist_ok=True)
errors = []

with sync_playwright() as playwright:
    executable = os.environ.get("SOLARPILOT_CHROMIUM_PATH") or shutil.which("chromium")
    browser = playwright.chromium.launch(
        **({"executable_path": executable} if executable else {}),
        headless=True, args=["--no-sandbox"],
    )
    page = browser.new_page(viewport={"width": 390, "height": 844}, locale="nl-BE")
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.route("**/*", lambda route: route.abort())
    page.set_content((ROOT / "SolarPilot-voorbeeld.html").read_text(encoding="utf-8"), wait_until="load")
    page.wait_for_selector("solar-pilot-card >> h1")
    page.evaluate("help=>{window.SOLAR_PILOT_HELP_DATA=help;}", json.loads(
        (ROOT / "custom_components/solar_pilot/frontend/option-help.json").read_text()))
    page.evaluate("""() => {
      window.c=document.querySelector('solar-pilot-card');window.requests=[];window.serviceCalls=[];
      window.saved=null;window.pending=null;window.rejectFirst=true;window.flowCount=0;
      window.sourceId='sensor.fixture_venus_ac_power_with_extra_long_entity_id';
      const states={...c._hass.states};
      for(let i=0;i<300;i++)states['sensor.fixture_'+i]={state:'1',attributes:{friendly_name:'AAA Testbron '+i,device_class:'power'}};
      states[sourceId]={state:'-400',attributes:{friendly_name:'Marstek · Vermogen netaansluiting',device_class:'power'}};
      states['sensor.fictional_other_ac']={state:'20',attributes:{friendly_name:'Marstek · Vermogen netaansluiting',device_class:'power'}};
      states['sensor.fictional_soc']={state:'55',attributes:{friendly_name:'Marstek · Batterijniveau',device_class:'battery'}};
      window.nativeForm=(errors={})=>{const v=saved||{name:'Marstek Venus E3',power_entity:'',power_sign:'',
        ac_power_confirmed:false,soc_entity:'sensor.fictional_soc',phase_hint:'unknown'};
        return{type:'form',flow_id:'fixture-flow-'+flowCount,step_id:'battery_marstek',errors,data_schema:[
          {name:'name',required:true,selector:{text:{}},default:v.name},
          {name:'power_entity',required:true,selector:{entity:{filter:{domain:'sensor',device_class:'power'}}},default:v.power_entity},
          {name:'power_sign',required:true,selector:{select:{options:[
            {value:'discharge_positive',label:'Positief = ontladen naar huis'},
            {value:'charge_positive',label:'Positief = laden'}]}},default:v.power_sign},
          {name:'ac_power_confirmed',required:true,selector:{boolean:{}},default:v.ac_power_confirmed},
          {name:'soc_entity',required:false,selector:{entity:{filter:{domain:'sensor',device_class:'battery'}}},default:v.soc_entity},
          {name:'phase_hint',required:false,selector:{select:{options:[
            {value:'unknown',label:'Onbekend'},{value:'L1',label:'L1'}]}},default:v.phase_hint}]};};
      window.fakeApi=async(method,path,data)=>{
        requests.push({method,path,data:structuredClone(data)});if(method==='delete')return{};
        if(path==='config/config_entries/options/flow'){flowCount++;return{type:'menu',flow_id:'fixture-flow-'+flowCount,step_id:'init',menu_options:['storage_hub']};}
        if(data.next_step_id==='storage_hub')return{type:'menu',flow_id:'fixture-flow-'+flowCount,step_id:'storage_hub',menu_options:['battery']};
        if(data.next_step_id==='battery')return{type:'menu',flow_id:'fixture-flow-'+flowCount,step_id:'battery',menu_options:['battery_marstek']};
        if(data.next_step_id==='battery_marstek')return nativeForm();
        if('name' in data){
          if(rejectFirst){rejectFirst=false;return nativeForm({base:'fixture_error'});}
          pending=data;return{type:'form',flow_id:'fixture-flow-'+flowCount,step_id:'apply_changes',errors:{},data_schema:[
            {name:'confirm',required:true,selector:{boolean:{}},default:false}]};
        }
        if(data.confirm!==true)return{type:'form',flow_id:'fixture-flow-'+flowCount,step_id:'apply_changes',errors:{confirm:'fixture_confirmation'},data_schema:[
          {name:'confirm',required:true,selector:{boolean:{}},default:false}]};
        saved=structuredClone(pending);return{type:'create_entry',title:'Opgeslagen',data:{}};
      };
      c.hass={...c._hass,user:{id:'fixture-mobile-user',is_admin:true},states,callApi:fakeApi,
        callService:async(...args)=>serviceCalls.push(args)};
      window.updateCard=()=>{const a=structuredClone(c._last.attributes);a.last_update=Date.now()/1000;
        c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'ready',attributes:a}}};};
      c._openOptions('battery');
    }""")
    card = page.locator("solar-pilot-card")
    options = card.locator("solar-pilot-options-dialog")
    options.locator("[data-menu=battery_marstek]").click()
    power = options.locator("[name=power_entity]")
    assert options.locator("button[type=submit]").inner_text() == "Verder"
    assert options.locator("datalist,input[list]").count() == 0
    assert page.evaluate("requests.slice(0,3).map(r=>r.data)") == [
        {"handler": page.evaluate("c._last.attributes.config_entry_id")},
        {"next_step_id": "storage_hub"}, {"next_step_id": "battery"}]

    # The duplicate visible names cannot accidentally choose the first sensor.
    power.fill("Marstek")
    assert power.evaluate("el=>el.dataset.entityValue") == ""
    assert options.locator(".entity-options:not([hidden]) [data-entity-choice]").count() == 2
    first_list = options.locator(".entity-options:not([hidden])")
    assert first_list.evaluate("el=>getComputedStyle(el).backgroundColor") != "rgba(0, 0, 0, 0)"
    power.press("Escape")
    assert options.locator("dialog").is_visible()
    assert power.get_attribute("aria-expanded") == "false"
    power.press("ArrowDown")
    power.press("ArrowDown")
    chosen = page.evaluate("sourceId")
    # Pick the full ID through a touch-compatible pointer click, never a fuzzy label.
    options.locator("[data-entity-choice]").filter(has_text=chosen).click()
    assert power.input_value() == "Marstek · Vermogen netaansluiting"
    assert power.evaluate("el=>el.dataset.entityValue") == chosen
    assert power.get_attribute("aria-expanded") == "false"
    assert options.locator(".entity-selection").first.inner_text() == "Gekozen: " + chosen
    options.locator("[name=power_sign]").select_option("discharge_positive")
    options.locator("[name=ac_power_confirmed]").check()
    options.locator("[name=soc_entity]").fill("")
    options.locator("[name=name]").fill("Fictional Venus edited")

    # A keyboard-sized viewport and repeated HA updates retain the very same DOM
    # node, its unsent query, focus and caret; the list stays inside the modal.
    power.fill("Testbron")
    power.evaluate("el=>{window.focusedInput=el;el.setSelectionRange(3,6);}")
    page.set_viewport_size({"width": 390, "height": 390})
    page.evaluate("() => {for(let i=0;i<8;i++)updateCard();}")
    page.wait_for_function("focusedInput.getBoundingClientRect().top>0")
    assert power.evaluate("el=>el===focusedInput")
    assert power.input_value() == "Testbron"
    assert power.evaluate("el=>[el.getRootNode().activeElement===el,el.selectionStart,el.selectionEnd]") == [True, 3, 6]
    assert options.locator(".entity-options:not([hidden]) [data-entity-choice]").count() == 50
    geometry = options.evaluate("""el=>{const s=el.shadowRoot,d=s.querySelector('dialog'),body=s.querySelector('.body'),list=s.querySelector('.entity-options:not([hidden])');
      return{dialog:d.getBoundingClientRect().toJSON(),body:body.getBoundingClientRect().toJSON(),list:list.getBoundingClientRect().toJSON(),overflow:d.scrollWidth>d.clientWidth,listScrollable:list.scrollHeight>list.clientHeight};}""")
    assert geometry["dialog"]["bottom"] <= 390
    assert geometry["list"]["height"] <= 222
    assert geometry["list"]["bottom"] <= geometry["body"]["bottom"] + 1
    assert not geometry["overflow"]
    assert geometry["listScrollable"]
    first_list.evaluate("el=>el.scrollTop=el.scrollHeight")
    assert first_list.evaluate("el=>el.scrollTop") > 0
    page.screenshot(path=str(OUT / "options-mobile115-keyboard.png"))

    # A filter query is not a sensor binding and cannot reach the native flow.
    before = page.evaluate("requests.length")
    options.locator("form").evaluate("form=>form.requestSubmit()")
    assert page.evaluate("requests.length") == before
    power.fill(chosen)
    power.press("Escape")
    # Deliberately stale server defaults after an error must not erase any local
    # field, including a checked confirmation and a cleared optional sensor.
    options.locator("[name=name]").focus()
    options.locator("[name=name]").evaluate("el=>el.setSelectionRange(2,8)")
    options.locator("form").evaluate("form=>form.requestSubmit()")
    options.get_by_text("fixture_error", exact=True).wait_for()
    assert options.locator("[name=name]").input_value() == "Fictional Venus edited"
    assert options.locator("[name=name]").evaluate("el=>[el.getRootNode().activeElement===el,el.selectionStart,el.selectionEnd]") == [True, 2, 8]
    assert power.evaluate("el=>el.dataset.entityValue") == chosen
    assert options.locator("[name=ac_power_confirmed]").is_checked()
    assert options.locator("[name=soc_entity]").input_value() == ""
    assert options.locator("[name=power_sign]").input_value() == "discharge_positive"
    assert page.evaluate("requests.at(-1).data.power_entity") == chosen
    assert "soc_entity" not in page.evaluate("requests.at(-1).data")
    assert page.evaluate("saved") is None
    page.screenshot(path=str(OUT / "options-mobile115-error-retained.png"))
    options.locator("button[type=submit]").click()
    options.locator("[name=confirm]").wait_for()
    assert options.locator("button[type=submit]").inner_text() == "Wijzigingen opslaan"
    assert not options.locator("[name=confirm]").is_checked()
    assert page.evaluate("saved") is None
    options.locator("button[type=submit]").click()
    options.get_by_text("fixture_confirmation", exact=True).wait_for()
    assert page.evaluate("saved") is None
    options.locator("[name=confirm]").check()
    options.locator("button[type=submit]").click()
    options.get_by_text("Instellingen opgeslagen zonder volledige herlading.", exact=False).wait_for()
    assert page.evaluate("saved.power_entity") == chosen
    assert page.evaluate("saved.ac_power_confirmed") is True
    options.locator("[data-close]").click()
    page.evaluate("c._openOptions('battery')")
    options.locator("[data-menu=battery_marstek]").click()
    assert power.evaluate("el=>el.dataset.entityValue") == chosen
    assert power.input_value() == "Marstek · Vermogen netaansluiting"
    assert options.locator("[name=ac_power_confirmed]").is_checked()
    assert options.locator("[name=power_sign]").input_value() == "discharge_positive"
    # The saved source sorts after 300 other choices. Merely focusing it and
    # pressing Enter must keep that binding, while explicit arrow selection works.
    power.focus()
    assert options.locator(".entity-option[aria-selected=true]").get_attribute("data-entity-choice") == chosen
    power.press("Enter")
    assert power.evaluate("el=>el.dataset.entityValue") == chosen
    assert power.get_attribute("aria-expanded") == "false"
    power.press("ArrowDown")
    power.press("ArrowDown")
    power.press("Enter")
    assert power.evaluate("el=>el.dataset.entityValue") != chosen
    power.fill("  " + chosen + "  ")
    assert power.input_value() == chosen
    assert power.evaluate("el=>el.dataset.entityValue") == chosen
    power.press("Escape")
    page.set_viewport_size({"width": 390, "height": 844})
    page.screenshot(path=str(OUT / "options-mobile115-reopened.png"))

    # No old user's idle draft or flow may cross a card account switch.
    options.locator("[name=name]").fill("Privé concept oude gebruiker")
    page.evaluate("c.hass={...c._hass,user:{id:'other-fixture-admin',is_admin:true}}")
    assert not options.locator("dialog").is_visible()
    assert "Privé concept" not in options.inner_text()
    page.wait_for_function("requests.some(r=>r.method==='delete')")
    assert page.evaluate("serviceCalls") == []
    assert not errors, errors
    browser.close()

print("Mobile options115: bounded opaque selectors, keyboard viewport, exact IDs, retained drafts, final confirmation, reopen and account isolation passed")
