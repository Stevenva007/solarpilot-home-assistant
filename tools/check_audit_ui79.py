"""Real frontend probes for audit regressions against fictional offline data.

No Home Assistant installation, server saves, exports or device commands.
"""
from pathlib import Path
import json
import shutil

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
errors = []

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=shutil.which("chromium"), headless=True,
                               args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 1000}, locale="nl-BE",
                            timezone_id="Europe/Brussels")
    page.route("**/*", lambda route: route.abort())
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content((ROOT / "SolarPilot-voorbeeld.html").read_text(), wait_until="load")
    page.wait_for_selector("solar-pilot-card >> h1")
    page.evaluate("""() => {
      window.c=document.querySelector('solar-pilot-card');window.actuatorCalls=[];
      const a=structuredClone(c._last.attributes),stamp=Date.now()/1000;
      a.config_entry_id='fixture-audit';a.energy_display={inverter_limit_w:5000,stale_s:120,
        pv:{value_w:800,reported_at:stamp},grid:{value_w:250,reported_at:stamp}};
      Object.assign(a.wallbox,{enabled:true,activity_known:true,power_w:1800,stale_s:120,
        last_report_age_s:0,activity_details:{current:{known:true,active:true,report_timestamp:stamp}}});
      c.hass={...c._hass,user:{id:'fixture-admin',is_admin:true},
        callService:async(...args)=>{actuatorCalls.push(args);throw Error('No physical services');},
        callApi:async(method,path)=>method==='delete'?{}:{type:'form',step_id:'settings',flow_id:'fixture-flow',
          errors:{},data_schema:[{name:'reserve_w',required:true,default:150,selector:{number:{min:0,max:5000,step:10}}}]},
        states:{...c._hass.states,[c._entity]:{state:'Fixture',attributes:a}}};
      window.fixtureStamp=stamp;
    }""")
    card = page.locator("solar-pilot-card")
    assert card.locator('[data-energy="pv"] strong').inner_text() == "800 W"
    assert card.locator('[data-energy="grid"] strong').inner_text() == "afname 250 W"
    assert "AUTO LAADT" in card.locator('[data-reason-key="overview:wallbox"]').inner_text()
    card.locator('[data-ui-key="overview:technical"] > summary').click()
    page.evaluate("c._openOptions()")
    options = page.locator("solar-pilot-options-dialog")
    page.wait_for_selector("solar-pilot-options-dialog >> [name=reserve_w]")
    options.locator('[name="reserve_w"]').fill("170")
    page.evaluate("""() => {
      window.originalClock=Date.now;window.savedState=c._last;
      Date.now=()=>Math.floor((fixtureStamp+121)*1000);
      c._refreshObservationDisplay();
    }""")
    assert card.locator('[data-energy="pv"] strong').inner_text() == "—"
    assert card.locator('[data-energy="grid"] strong').inner_text() == "—"
    assert card.locator('[data-energy="pv"] small').inner_text() == "Actuele meting ontbreekt"
    assert "LAADSTATUS ONBEKEND" in card.locator('[data-reason-key="overview:wallbox"]').inner_text()
    assert "Vermogen nog niet bekend" in card.locator('[data-reason-key="overview:wallbox"]').inner_text()
    assert page.evaluate("c._last===savedState")  # Expired without a new HA state.
    assert card.locator('[data-ui-key="overview:technical"]').get_attribute("open") is not None
    assert options.locator('[name="reserve_w"]').input_value() == "170"
    assert options.locator("dialog").first.is_visible()
    page.evaluate("Date.now=originalClock;c._optionsDialog.close(true)")

    # The measured injection and an eligible solar input pool are different
    # from the final start budget after protected future peaks and allocations.
    page.evaluate("""() => {
      const a=structuredClone(c._last.attributes),allocation={available_w:0,required_w:380,sufficient:false,
        instant_free_w:2700,filtered_free_w:2500,smoothing_hold_w:200,protected_cycle_reserve_w:2100,
        higher_allocated_w:400,remaining_solar_w:0,remaining_cap_w:4800};
      a.devices=[{id:'fixture-dehumidifier',name:'Fictional flexible appliance',kind:'switch',mode:'auto',
        on:false,available:true,power_w:0,reason:'Wacht op vermogen / hogere prioriteit',
        start_requirements:{allocated_start_power:{met:false,...allocation}},
        start_diagnostics:{summary:'Wacht op vermogen / hogere prioriteit',missing:['allocated_start_power'],
          power:{measurement_valid:true,required_start_w:380,measured_free_w:2700,allocation,
            solar_start_pool:{available_solar_w:3000,wallbox_solar_w:300,lower_loads_releasable_w:0}},
          stable_start:{configured_s:120,remaining_s:120}}}];
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Fixture',attributes:a}}};
    }""")
    budget_row = card.locator('[data-reason-key="overview:device:fixture-dehumidifier"]')
    budget_row.locator(".reason-details > summary").click()
    budget_text = budget_row.inner_text()
    assert "Vrije zonnestroom na huisreserve\n2,7 kW" in budget_text
    assert "Toegelaten zonnepot vóór eindtoewijzing\n3 kW" in budget_text
    assert "Beschikbaar voor dit toestel\n0 W" in budget_text
    assert "Reserve voor lopende beschermde cycli · komende pieken\n2,1 kW" in budget_text
    assert "Tijdelijk achtergehouden door vermogensfilter\n200 W" in budget_text
    assert "vrije zonnestroom nodig" not in budget_text
    assert page.evaluate("document.documentElement.scrollWidth<=innerWidth")
    assert budget_row.evaluate("el=>el.scrollWidth<=el.clientWidth+1")
    page.evaluate("""() => {const a=structuredClone(c._last.attributes);a.free_w=2800;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Fixture',attributes:a}}};}""")
    assert budget_row.locator(".reason-details").get_attribute("open") is not None
    assert page.evaluate("actuatorCalls.length") == 0

    # A closed slow-help open must not create an old entry's options flow after reopen.
    page.evaluate("""async() => {
      window.helpFixture=globalThis.SOLAR_PILOT_HELP_DATA;
      globalThis.SOLAR_PILOT_HELP_DATA=new Promise(resolve=>window.releaseOldCatalog=resolve);
      window.probe=document.createElement('solar-pilot-options-dialog');document.body.append(probe);
      window.flowPosts=[];
      window.probeHass={user:{id:'fixture-admin',is_admin:true},callApi:async(method,path,data)=>{
        if(method==='delete')return {};
        flowPosts.push(data);return {type:'form',step_id:'settings',flow_id:'flow-'+data.handler,
          errors:{},data_schema:[{name:'reserve_w',required:true,default:150,selector:{number:{min:0,max:5000,step:10}}}]};}};
      window.oldOpen=probe.open(probeHass,'entry-old');
      await probe.close(true);globalThis.SOLAR_PILOT_HELP_DATA=helpFixture;
      await probe.open(probeHass,'entry-current');
      probe.content.querySelector('[name=reserve_w]').value='190';
      releaseOldCatalog(helpFixture);await oldOpen;
    }""")
    assert page.evaluate("JSON.stringify(flowPosts)") == '[{"handler":"entry-current"}]'
    assert page.evaluate("probe.flow.flow_id") == "flow-entry-current"
    assert page.evaluate("probe.content.querySelector('[name=reserve_w]').value") == "190"
    page.evaluate("probe.close(true);probe.remove()")

    # An old API result after detach cannot unlock or overwrite the current flow.
    # Exercise both the stable alias and the constructor bound to this release.
    for tag in ("solar-pilot-options-dialog", page.evaluate("SP_OPTIONS_DIALOG_TAG")):
        page.evaluate("""async tag => {
          window.probe=document.createElement(tag);document.body.append(probe);
          window.cleanupCalls=[];
          const user={id:'fixture-admin',is_admin:true};
          const oldStarted=new Promise(resolve=>window.oldRequestStarted=resolve);
          const currentStarted=new Promise(resolve=>window.currentRequestStarted=resolve);
          window.oldHass={user,callApi:async(method,path)=>{
            if(method==='delete')return cleanupCalls.push(path);
            oldRequestStarted();return new Promise(resolve=>window.releaseOldFlow=resolve);
          }};
          window.currentHass={user,callApi:async(method,path)=>{
            if(method==='delete')return {};
            currentRequestStarted();return new Promise(resolve=>window.releaseCurrentFlow=resolve);
          }};
          window.oldOpen=probe.open(oldHass,'entry-old');
          await oldStarted;
          probe.remove();
          if(probe.dialog.open)throw Error('Detached pending options dialog retained native open state');
          document.body.append(probe);
          window.currentOpen=probe.open(currentHass,'entry-current');
          // Wait for the actual request boundary, rather than guessing the number
          // of catalog microtasks. An open() rejection must fail this probe itself.
          await Promise.race([currentStarted,currentOpen]);
          if(!probe._busy||!probe._open||probe.flow!==null)
            throw Error('Reopened request not pending: '+JSON.stringify({busy:probe._busy,open:probe._open,
              flow:probe.flow,nativeOpen:probe.dialog.open,entry:probe.entryId}));
          releaseOldFlow({type:'menu',step_id:'init',flow_id:'flow-old',menu_options:[]});await oldOpen;
        }""", tag)
        assert page.evaluate("probe._busy && probe._open && probe.flow===null && probe.dialog.matches(':modal')")
        assert page.evaluate("JSON.stringify(cleanupCalls)") == '["config/config_entries/options/flow/flow-old"]'
        page.evaluate("""async() => {
          releaseCurrentFlow({type:'form',step_id:'settings',flow_id:'flow-current',errors:{},data_schema:[]});
          await currentOpen;
        }""")
        assert page.evaluate("!probe._busy && probe.flow.flow_id==='flow-current'")
        page.evaluate("async()=>{await probe.close(true);probe.remove();}")
    assert page.evaluate("actuatorCalls.length") == 0
    assert not errors, errors

    # An old stable constructor may survive loading a new sidebar release. Load
    # the actual new card and import the actual current helper module on demand.
    mixed = browser.new_page(viewport={"width": 390, "height": 1000}, locale="nl-BE")
    mixed.on("pageerror", lambda error: errors.append(str(error)))
    helper_urls = []

    def serve_fixture(route):
        url = route.request.url
        if url == "http://solarpilot.example.test/audit":
            route.fulfill(status=200, content_type="text/html", body="<solar-pilot-card></solar-pilot-card>")
        elif url.startswith("http://solarpilot.example.test/solar_pilot_static/option-help.js?v="):
            helper_urls.append(url)
            route.fulfill(status=200, content_type="text/javascript",
                          body=(ROOT / "custom_components/solar_pilot/frontend/option-help.js").read_text())
        else:
            route.abort()

    mixed.route("**/*", serve_fixture)
    mixed.goto("http://solarpilot.example.test/audit", wait_until="load")
    mixed.evaluate("""help => {
      globalThis.SOLAR_PILOT_HELP_DATA=help;
      for(const tag of ['solar-pilot-pv-dialog','solar-pilot-consumer-history-dialog','solar-pilot-priority-dialog',
        'solar-pilot-option-help-dialog','solar-pilot-options-dialog','solar-pilot-device-manager-dialog'])
        customElements.define(tag,class OldDialog extends HTMLElement {static solarPilotRelease='old-release';});
    }""", json.loads((ROOT / "custom_components/solar_pilot/frontend/option-help.json").read_text()))
    mixed.add_script_tag(content=(ROOT / "custom_components/solar_pilot/frontend/solar-pilot-card.js").read_text())
    mixed.evaluate("""() => {
      window.c=document.querySelector('solar-pilot-card');c.setConfig({});window.calls=[];
      c.hass={user:{id:'fixture-admin',is_admin:true},config:{time_zone:'Europe/Brussels'},
        states:{'sensor.fixture':{state:'Fixture',attributes:{solar_pilot:true,mode:'observe',config_entry_id:'fixture',devices:[]}}},
        callService:async(...args)=>{calls.push(args);throw Error('No physical services');},
        callApi:async(method,path)=>method==='delete'?{}:{type:'form',step_id:'settings',flow_id:'fixture-current',errors:{},data_schema:[]},
        callWS:async msg=>msg.type==='solar_pilot/pv_diagnostics'?{history:[],summary:{}}:
          msg.type==='solar_pilot/priority_board'?{revision:'fixture',order:[],rows:[],wallbox_power:{}}:
          {date:'2026-01-02',first_date:'2026-01-01',today:'2026-01-02',timezone:'Europe/Brussels',
           day_seconds:86400,days:[],sessions:[],events:[],has_data:false}};
      c._uiHistory={prepare(){},track(){}};
    }""")
    mixed.evaluate("""async() => {
      c._openPV();c._pvDialog.close();
      c._openHistory({id:'fixture',name:'Fictional consumer'});c._historyDialog.close();
      c._openPriorities();c._priorityDialog.close(true);
      await c._openHelp('settings','reserve_w');c._helpDialog.close();
      await c._openDevices();c._deviceManager.close();await c._openOptions();
    }""")
    assert mixed.evaluate("""() => [c._pvDialog,c._historyDialog,c._priorityDialog,c._helpDialog,c._deviceManager,c._optionsDialog]
      .every(d=>d.constructor.solarPilotRelease===SP_CARD_VERSION&&d.localName.endsWith(SP_DIALOG_RELEASE))""")
    assert len(helper_urls) == 1
    assert helper_urls[0].endswith("?v=" + mixed.evaluate("SP_CARD_VERSION"))
    assert mixed.evaluate("calls.length") == 0
    assert mixed.evaluate("customElements.get('solar-pilot-options-dialog').solarPilotRelease") == "old-release"
    mixed.evaluate("""async() => {
      await c._optionsDialog.close(true);
      c._openPV();c._pvDialog.close();c._openPV();
      await new Promise(resolve=>setTimeout(resolve,30));
    }""")
    assert mixed.evaluate("c._pvDialog._open && c._pvDialog._dialog.open")
    mixed.evaluate("""async() => {
      c._pvDialog.close();c._openHistory({id:'fixture',name:'Fictional consumer'});
      c._historyDialog.close();c._openHistory({id:'fixture',name:'Fictional consumer'});
      await new Promise(resolve=>setTimeout(resolve,30));
    }""")
    assert mixed.evaluate("c._historyDialog._isOpen && c._historyDialog._dialog.open && c._historyDialog._timer!=null")
    assert not errors, errors
    browser.close()

print("Audit UI: P1/PV/Wallbox expiry, details/draft preservation, catalog reopen, detached request isolation and old/current popup constructors: OK")
