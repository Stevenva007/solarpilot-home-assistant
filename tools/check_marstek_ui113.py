"""Real Chromium Marstek monitor behavior with fictitious sources and no writes.

Build SolarPilot-voorbeeld.html before running this fixture. Screenshots are
kept outside the repository, alongside the existing frontend browser gates.
"""
import os
import json
from pathlib import Path
import shutil

from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("SOLARPILOT_SCREENSHOT_DIR", "/tmp/solarpilot-browser-tests"))
OUT.mkdir(parents=True, exist_ok=True)
errors = []


def assert_monitor_only(panel):
    assert "Alleen monitoren · Marstek regelt zelf" in panel.inner_text()
    assert panel.locator("input,select,[role=switch]").count() == 0
    assert panel.locator("button:not([data-action=source_history]):not([data-action=configure])").count() == 0
    for forbidden in ("Advies", "bestuurbaar", "BEDIENING TOEGESTAAN", "Batterijscenario", "doelvermogen"):
        assert forbidden not in panel.inner_text(), forbidden


with sync_playwright() as playwright:
    executable = os.environ.get("SOLARPILOT_CHROMIUM_PATH") or shutil.which("chromium")
    browser = playwright.chromium.launch(
        **({"executable_path": executable} if executable else {}),
        headless=True, args=["--no-sandbox"],
    )
    page = browser.new_page(viewport={"width": 390, "height": 844}, locale="nl-BE")
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.route("**/*", lambda route: route.abort())
    page.clock.install()
    page.set_content((ROOT / "SolarPilot-voorbeeld.html").read_text(encoding="utf-8"), wait_until="load")
    page.wait_for_selector("solar-pilot-card >> h1")
    page.evaluate("help=>{window.SOLAR_PILOT_HELP_DATA=help;}", json.loads(
        (ROOT / "custom_components/solar_pilot/frontend/option-help.json").read_text()))
    page.evaluate("""() => {
      window.c=document.querySelector('solar-pilot-card');
      window.controlWrites=[];window.sourceReads=[];window.nativeHistoryViews=[];
      c.addEventListener('hass-more-info',e=>nativeHistoryViews.push(e.detail));
      window.monitorSourceRead=async message=>{
        sourceReads.push(message);
        if(message.type!=='solar_pilot/source_history'||message.kind!=='battery'||
           message.item_id!=='fictional-monitor'||message.config_entry_id!=='fictional-battery-entry')
          throw Error('Unexpected read '+JSON.stringify(message));
        return {schema:1,read_only:true,scope:'current_configured_sources',kind:'battery',
          item_id:'fictional-monitor',name:'Fictieve batterijbronnen',sources:[
            {role:'power_entity',label:'Vermogen netaansluiting',entity_id:'sensor.fictional_battery_ac'},
            {role:'soc_entity',label:'Batterijniveau',entity_id:'sensor.fictional_battery_soc'}]};
      };
      window.applyMonitor=(changes={},mixed=false,secondMonitor=null)=>{
        const a=structuredClone(c._last.attributes),now=Date.now()/1000;
        a.config_entry_id='fictional-battery-entry';a.integration_version=window.SOLAR_PILOT_HELP_DATA.version;
        a.restored=false;
        const battery={id:'fictional-monitor',name:'Marstek Venus E3 · fictief',profile:'marstek_venus_e3',
          monitor_only:true,control_kind:'read_only',control_enabled:false,controllable:false,
          valid:false,power_valid:true,soc_valid:false,power_w:-420,soc_pct:null,
          power_stamp:now,soc_stamp:null,stale_s:120,...changes};
        a.ems.battery_fleet={enabled:true,control_enabled:true,
          aggregate:{valid:true,soc_pct:57,power_w:battery.power_w,capacity_kwh:5.12},
          recommendation_w:9999,reason:'Advies alleen voor de generieke batterij',faults:{},batteries:[battery]};
        if(mixed)a.ems.battery_fleet.batteries.push({id:'fictional-generic',name:'Generieke batterij · fictief',
          profile:'generic',valid:true,soc_pct:60,power_w:250,phase_hint:'L2',controllable:true,
          control_enabled:true,exclusive_control_confirmed:true,control_kind:'number'});
        if(secondMonitor)a.ems.battery_fleet.batteries.push({...battery,id:'fictional-second-monitor',
          name:'Tweede Marstek · fictief',...secondMonitor});
        c.hass={...c._hass,user:{id:'fictional-battery-user',is_admin:false},callWS:monitorSourceRead,
          callService:async(...args)=>controlWrites.push(args),
          states:{...c._hass.states,[c._entity]:{state:'ready',attributes:a}}};
      };
      applyMonitor();
    }""")
    card = page.locator("solar-pilot-card")
    overview = card.locator('[data-reason-key="overview:battery:fictional-monitor"]')
    assert overview.locator(".badge").inner_text() == "Laden"
    overview.locator("summary").click()
    assert "Laadniveau\nOnbekend" in overview.inner_text()
    assert "420 W" in overview.inner_text()
    assert "Advies" not in overview.inner_text()
    assert overview.locator("input,select,[role=switch]").count() == 0
    page.evaluate("applyMonitor({power_w:250})")
    assert overview.locator("details").evaluate("element=>element.open")
    assert overview.locator(".badge").inner_text() == "Ontladen"
    assert "250 W" in overview.inner_text()

    # Expiry without a HA update changes the actual visible DOM, including an
    # open explanation. The original source timestamps remain unchanged.
    source_stamp = page.evaluate("c._last.attributes.ems.battery_fleet.batteries[0].power_stamp")
    page.clock.fast_forward(131_000)
    assert overview.locator(".badge").inner_text() == "Onbekend"
    assert overview.locator("details").evaluate("element=>element.open")
    assert "Laden\nOnbekend" in overview.inner_text()
    assert "Ontladen\nOnbekend" in overview.inner_text()
    assert page.evaluate("c._last.attributes.ems.battery_fleet.batteries[0].power_stamp") == source_stamp
    card.locator('[data-ui-key="overview:technical"] > summary').click()
    assert card.locator(".battery-summary strong").inner_text() == "Laadniveau onbekend · Onbekend"
    page.evaluate("applyMonitor({power_w:-420})")
    overview.locator('[data-action=view][data-value=storage]').click()
    panel = card.locator("[data-marstek-monitor]")
    assert_monitor_only(panel)

    for power, state, fact in ((-420, "Laden", "Laden\n420 W"),
                               (250, "Ontladen", "Ontladen\n250 W"),
                               (0, "Rust", "Ontladen\n0 W")):
        page.evaluate("value=>applyMonitor({power_w:value})", power)
        assert panel.locator(".badge").inner_text() == state
        assert fact in panel.inner_text()
        assert "Laadniveau\nOnbekend" in panel.inner_text()
        assert_monitor_only(panel)

    page.evaluate("applyMonitor({power_w:-420,soc_valid:true,soc_pct:58,soc_stamp:Date.now()/1000-121})")
    assert panel.locator(".badge").inner_text() == "Laden"
    assert "Laadniveau\nOnbekend" in panel.inner_text()
    page.clock.fast_forward(131_000)
    assert panel.locator(".badge").inner_text() == "Onbekend"
    assert "Laden\nOnbekend" in panel.inner_text()
    assert "420 W" not in panel.inner_text()

    for changes in ({"power_w": None}, {"power_valid": False}, {"power_stamp": None},
                    {"power_w": True}, {"power_stamp": page.evaluate("Date.now()/1000+60")}):
        page.evaluate("changes=>applyMonitor(changes)", changes)
        assert panel.locator(".badge").inner_text() == "Onbekend", changes
        assert "Ontladen\nOnbekend" in panel.inner_text()

    # A still-published zero and valid SoC must not conceal an unconfirmed or
    # incorrectly selected AC source. The repair action opens only settings.
    page.evaluate("""applyMonitor({power_w:0,power_valid:false,soc_valid:true,soc_pct:11,
      soc_stamp:Date.now()/1000,source_code:'ac_unconfirmed',
      reason:'AC-meetdekking nog niet bevestigd. Bewerk de Marstek-monitor.'})""")
    assert "11%" in panel.inner_text()
    assert "AC-meetdekking nog niet bevestigd" in panel.inner_text()
    assert panel.locator("[data-action=configure]").inner_text() == "Batterijbron controleren"
    assert_monitor_only(panel)
    page.evaluate("""applyMonitor({power_w:0,power_valid:false,soc_valid:true,soc_pct:11,
      soc_stamp:Date.now()/1000,source_code:'native_source_scope',
      reason:'Verkeerde Marstek-meetbron. Kies Vermogen netaansluiting (AC OnGrid).'})""")
    assert "Verkeerde Marstek-meetbron" in panel.inner_text()
    assert "AC-meetdekking nog niet bevestigd" not in panel.inner_text()
    page.evaluate("""() => {
      window.settingsRequests=[];window.batterySettingsSaved=null;
      const values={name:'Fictieve Marstek-monitor',power_entity:'sensor.fictional_battery_ac',
        power_sign:'discharge_positive',ac_power_confirmed:false};
      const marstekForm=(input={},errors={})=>{
        const v={...values,...input};return{type:'form',flow_id:'fictional-source-flow',
          step_id:'battery_marstek',errors,data_schema:[
            {name:'name',required:true,selector:{text:{}},default:v.name},
            {name:'power_entity',required:true,selector:{entity:{domain:'sensor'}},default:v.power_entity},
            {name:'power_sign',required:true,selector:{select:{options:[
              {value:'discharge_positive',label:'Positief = ontladen naar huis'},
              {value:'charge_positive',label:'Positief = laden'}]}},default:v.power_sign},
            {name:'ac_power_confirmed',required:true,selector:{boolean:{}},default:v.ac_power_confirmed}]};
      };
      c.hass={...c._hass,user:{id:'fictional-battery-user',is_admin:true},
        states:{...c._hass.states,'sensor.fictional_battery_ac':{state:'0',attributes:{unit_of_measurement:'W'}},
          'sensor.fictional_battery_dc':{state:'0',attributes:{unit_of_measurement:'W'}}},
        callApi:async(method,path,data)=>{
          settingsRequests.push({method,path,data});
          if(method==='delete')return{};
          if(path==='config/config_entries/options/flow')return{type:'menu',flow_id:'fictional-source-flow',step_id:'init',menu_options:['storage_hub']};
          if(data.next_step_id==='storage_hub')return{type:'menu',flow_id:'fictional-source-flow',step_id:'storage_hub',menu_options:['battery']};
          if(data.next_step_id==='battery')return{type:'menu',flow_id:'fictional-source-flow',step_id:'battery',menu_options:['battery_edit']};
          if(data.next_step_id==='battery_edit')return{type:'form',flow_id:'fictional-source-flow',step_id:'battery_edit',errors:{},data_schema:[
            {name:'battery_id',required:true,selector:{select:{options:[{value:'fictional-monitor',label:'Fictieve Marstek'}]}},default:'fictional-monitor'}]};
          if(data.battery_id)return marstekForm();
          if(data.ac_power_confirmed!==true)return marstekForm(data,{ac_power_confirmed:'battery_ac_confirmation'});
          if(data.power_entity!=='sensor.fictional_battery_ac')return marstekForm(data,{power_entity:'battery_native_scope'});
          if(data.power_sign!=='discharge_positive')return marstekForm(data,{power_sign:'battery_native_sign'});
          batterySettingsSaved=data;return{type:'create_entry',title:'Opgeslagen',data:{}};
        }};
    }""")
    panel.locator("[data-action=configure]").click()
    options = card.locator("solar-pilot-options-dialog")
    options.locator("[data-menu=battery_edit]").click()
    options.locator("button[type=submit]").click()
    options.locator("[name=ac_power_confirmed]").wait_for()
    assert not options.locator("[name=ac_power_confirmed]").is_checked()

    def submit_source_error(submitted, expected_text):
        # A previous inline error remains visible until the asynchronous flow
        # response replaces the form. Assert this submission's exact payload,
        # then wait for its mapped error rather than reading that older text.
        requests_before = page.evaluate("settingsRequests.length")
        options.locator("button[type=submit]").click()
        page.wait_for_function("count=>settingsRequests.length>count", arg=requests_before)
        assert page.evaluate("settingsRequests.length") == requests_before + 1
        assert page.evaluate("settingsRequests.at(-1)") == {
            "method": "post", "path": "config/config_entries/options/flow/fictional-source-flow",
            "data": submitted,
        }
        expect(options.locator(".inline-error")).to_contain_text(expected_text)
        assert page.evaluate("batterySettingsSaved") is None

    values = {"name": "Fictieve Marstek-monitor", "power_entity": "sensor.fictional_battery_ac",
              "power_sign": "discharge_positive", "ac_power_confirmed": False}
    submit_source_error(values, "Zonder bevestiging wordt de monitor niet opgeslagen")
    options.locator("[name=ac_power_confirmed]").check()
    options.locator("[name=power_entity]").fill("sensor.fictional_battery_dc")
    submit_source_error({**values, "power_entity": "sensor.fictional_battery_dc", "ac_power_confirmed": True},
                        "Kies Vermogen netaansluiting")
    options.locator("[name=power_entity]").fill("sensor.fictional_battery_ac")
    options.locator("[name=power_sign]").select_option("charge_positive")
    submit_source_error({**values, "power_sign": "charge_positive", "ac_power_confirmed": True},
                        "Positief = ontladen naar huis")
    options.locator("[name=power_sign]").select_option("discharge_positive")
    options.locator("button[type=submit]").click()
    page.wait_for_function("batterySettingsSaved!==null")
    assert page.evaluate("batterySettingsSaved.ac_power_confirmed") is True
    assert page.evaluate("settingsRequests.slice(0,3).map(r=>r.data)") == [
        {"handler": "fictional-battery-entry"}, {"next_step_id": "storage_hub"}, {"next_step_id": "battery"}]
    options.locator("[data-close]").click()
    assert page.evaluate("controlWrites") == []

    # Every monitor action is a read-only source-history action. Opening it and
    # receiving new readings must not invoke any Home Assistant service.
    page.evaluate("applyMonitor({soc_valid:true,soc_pct:58,soc_stamp:Date.now()/1000})")
    panel.locator("button[data-action=source_history]").click()
    history = card.locator("[data-source-history-dialog]")
    assert history.locator("dialog").is_visible()
    history.get_by_text("Vermogen netaansluiting", exact=True).wait_for()
    assert "Vermogen netaansluiting" in history.locator("dialog").inner_text()
    page.evaluate("applyMonitor({power_w:500})")
    assert history.locator("dialog").is_visible()
    history.locator("[data-source-index='0']").click()
    page.wait_for_function("nativeHistoryViews.length===1")
    assert page.evaluate("nativeHistoryViews.length") == 1
    assert page.evaluate("nativeHistoryViews[0].entityId") == "sensor.fictional_battery_ac"
    assert not history.locator("dialog").is_visible()

    # Partial aggregate.valid=true means a usable subset, not proof that every
    # battery contributed. Unknown/expired monitors must not leave false totals.
    page.evaluate("applyMonitor({power_w:500,soc_valid:true,soc_pct:58,soc_stamp:Date.now()/1000},true)")
    totals = card.locator(".battery-fleet-totals")
    assert totals.locator("strong").nth(0).inner_text() == "57%"
    assert totals.locator("strong").nth(1).inner_text() == "500 W"
    page.clock.fast_forward(131_000)
    assert totals.locator("strong").nth(0).inner_text() == "Onbekend"
    assert totals.locator("strong").nth(1).inner_text() == "Onbekend"
    assert "bestuurbaar" in card.locator(".batteryrow").inner_text()
    assert "60% · 250 W" in card.locator(".batteryrow").inner_text()
    card.locator('[role=tab][data-value=overview]').click()
    technical = card.locator('[data-ui-key="overview:technical"]')
    if not technical.evaluate("element=>element.open"):
        technical.locator(":scope > summary").click()
    assert card.locator(".battery-summary strong").inner_text() == "Onvolledige meting"
    assert "Vermogen nog niet bekend" in card.locator('[data-reason-key="overview:battery"]').inner_text()

    page.evaluate("""applyMonitor({soc_valid:true,soc_pct:58,soc_stamp:Date.now()/1000},false,
      {power_valid:false,power_w:700})""")
    second = card.locator('[data-reason-key="overview:battery:fictional-second-monitor"]')
    assert overview.locator(".badge").inner_text() == "Laden"
    assert second.locator(".badge").inner_text() == "Onbekend"
    assert card.locator(".battery-summary strong").inner_text() == "Onvolledige meting"
    page.evaluate("""applyMonitor({soc_valid:true,soc_pct:58,soc_stamp:Date.now()/1000},false,
      {power_valid:true,power_w:700})""")
    assert second.locator(".badge").inner_text() == "Ontladen"
    assert "Onvolledige" not in card.locator(".battery-summary strong").inner_text()
    page.clock.fast_forward(131_000)
    assert overview.locator(".badge").inner_text() == "Onbekend"
    assert second.locator(".badge").inner_text() == "Onbekend"
    assert card.locator(".battery-summary strong").inner_text() == "Onvolledige meting"
    card.locator('[role=tab][data-value=storage]').click()

    for width in (320, 390, 768, 1280):
        page.set_viewport_size({"width": width, "height": 1000})
        for mixed in (False, True):
            page.evaluate("mixed=>applyMonitor({},mixed)", mixed)
            assert_monitor_only(panel)
            assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), width
            assert panel.evaluate("element=>element.scrollWidth<=element.clientWidth+1"), width
            if mixed:
                generic = card.locator(".batteryrow")
                assert generic.count() == 1
                assert "Generieke batterij · fictief" in generic.inner_text()
                assert "bestuurbaar" in generic.inner_text()
                assert "60% · 250 W" in generic.inner_text()
                assert "BEDIENING TOEGESTAAN" in card.locator("section.view").inner_text()
                assert "Advies alleen voor de generieke batterij" in card.locator("section.view").inner_text()
            else:
                assert card.locator(".batteryrow,.scenario").count() == 0
                assert "Advies" not in card.locator("section.view").inner_text()
            page.screenshot(path=str(OUT / f"SolarPilot-Marstek-{'mixed' if mixed else 'monitor'}-{width}.png"), full_page=True)
    assert page.evaluate("controlWrites") == []
    assert page.evaluate("sourceReads.length") == 2
    browser.close()

assert not errors, errors
print("Marstek Chromium: source repair forms, native scope/sign errors, fresh/expired power, independent SoC, read-only history, mixed batteries and four widths passed")
