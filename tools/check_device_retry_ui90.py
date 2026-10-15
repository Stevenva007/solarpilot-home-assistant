"""Chromium acceptance for device-local five-minute reachability recovery.

All data are fictitious. Network requests are blocked. The only allowed service
is an explicitly clicked global mode choice; device commands fail the probe.
Run tools/build_example.py for this exact release before this script.
"""
import os
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("SOLARPILOT_SCREENSHOT_DIR", "/tmp/solarpilot-browser-tests"))
OUT.mkdir(parents=True, exist_ok=True)
errors = []

SETUP = """() => {
 window.c=document.querySelector('solar-pilot-card');window.retryCalls=[];
 const a=structuredClone(c._last.attributes);a.mode='paused';
 a.config_entry_id='fictional-retry-entry';a.mode_entity='select.fictional_solar_mode';
 a.problem='Wacht op actuele toestelgegevens';a.problem_kind='source_wait';
 a.restart_recovery_pending=true;a.restart_blocking=false;
 a.restart_recovery_devices=['Voorbeeld ontvochtiger'];
 a.isolated_reserve_w=0;
 a.isolated_devices=[{id:'fictional-offline',name:'Voorbeeld ontvochtiger',
   reason:'Actuele schakelstatus ontbreekt',reserve_w:0}];
 window.retryRecord=state=>({active:true,state,interval_s:300,
   next_check_wall:Date.now()/1000+300,remaining_s:300,
   reason:state==='source_wait'?'Tijdelijk geen actuele toestelgegevens beschikbaar.':
     'De vorige opdracht is nog niet bevestigd.'});
 window.retryOffline={id:'fictional-offline',name:'Voorbeeld ontvochtiger',
   kind:'switch',mode:'auto',available:false,on:true,owned:true,power_w:0,
   isolated:true,isolation_reason:'Actuele schakelstatus ontbreekt',isolation_reserve_w:0,
   reason:'Wacht op actuele toestelstatus',availability_retry:retryRecord('source_wait'),
   start_requirements:{availability_and_fault:{met:false,observed:true,available:false,fault:''}},
   start_diagnostics:{summary:'Wacht op actuele toestelstatus',missing:['availability_and_fault']},
   history:{last_change:{at:Date.now()/1000-600,reason:'Eerdere status waargenomen',confirmed:false}}};
 window.retryCommand={...structuredClone(retryOffline),id:'fictional-pending',
   name:'Voorbeeld toestel met open terugmelding',isolated:false,isolation_reason:'',
   availability_retry:retryRecord('command_wait')};
 window.retryFault={...structuredClone(retryOffline),id:'fictional-fault',
   name:'Voorbeeld toestel met technische fout',isolated:false,isolation_reason:'',availability_retry:null,
   reason:'Opdrachtfout: ongeldige koppeling vraagt controle'};
 retryFault.start_diagnostics.summary=retryFault.reason;
 retryFault.start_requirements.availability_and_fault.fault='Ongeldige koppeling vraagt controle';
 a.devices=[retryOffline,retryCommand,retryFault,{id:'fictional-healthy',
   name:'Voorbeeld bereikbaar toestel',kind:'switch',mode:'auto',available:true,
   on:false,owned:false,power_w:0,reason:'Wacht op zonneoverschot'}];
 window.retryAttributes=a;
 window.publishRetry=()=>{
   retryAttributes.devices[0]=retryOffline;retryAttributes.devices[1]=retryCommand;
   retryAttributes.devices[2]=retryFault;
   const next=structuredClone(retryAttributes);
   c.hass={...c._hass,user:{id:'fictional-admin',is_admin:true},
     callService:async(domain,service,data)=>{
       retryCalls.push({domain,service,data});
       if(domain!=='select'||service!=='select_option'||
          data.entity_id!=='select.fictional_solar_mode'||data.option!=='solar')
         throw Error('Unexpected device or unrelated service call');
       retryAttributes.mode='solar';publishRetry();
     },
     callWS:async data=>{retryCalls.push({websocket:data});throw Error('Unexpected RPC');},
     states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:next}}};
 };
 c._view='overview';publishRetry();
} """

with sync_playwright() as p:
    executable = os.environ.get("SOLARPILOT_CHROMIUM_PATH") or shutil.which("chromium")
    browser = p.chromium.launch(**({"executable_path": executable} if executable else {}),
                                headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 1000}, locale="nl-BE",
                            timezone_id="Europe/Brussels")
    page.route("**/*", lambda route: route.abort())
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("dialog", lambda dialog: dialog.accept())
    page.set_content((ROOT / "SolarPilot-voorbeeld.html").read_text(), wait_until="load")
    page.wait_for_selector("solar-pilot-card >> h1")
    page.evaluate(SETUP)
    card = page.locator("solar-pilot-card")

    def row(device_id):
        return card.locator(f'[data-reason-key="overview:device:{device_id}"]')

    offline = row("fictional-offline")
    pending = row("fictional-pending")
    fault = row("fictional-fault")
    offline.locator(".reason-details > summary").click()
    assert offline.locator(".badge").inner_text() == "Tijdelijk niet bereikbaar"
    assert pending.locator(".badge").inner_text() == "Wacht op terugmelding"
    assert "Opnieuw controleren over" in offline.inner_text()
    assert "controleert elke 5 minuten opnieuw" in offline.inner_text()
    assert "op dat moment nodig en toegestaan" in offline.inner_text()
    assert offline.locator(".reason-power > b").inner_text() == "Vermogen nog niet bekend"
    assert pending.locator(".reason-power > b").inner_text() == "Vermogen nog niet bekend"
    assert "geen extra verbruiksreserve afgetrokken" in offline.inner_text()
    assert "het toestelvermogen blijft onbekend" in offline.inner_text()
    assert "Veiligheidsreserve voor mogelijk verbruik" not in offline.inner_text()
    assert "Toestelfout:" not in offline.inner_text()
    assert "Opdrachtfout: ongeldige koppeling vraagt controle" in fault.inner_text()
    assert "Toestelgegevens deels onbekend; het actuele netoverschot blijft leidend." in card.locator("ha-card").inner_text()
    assert page.evaluate("retryCalls.length") == 0

    for width in (320, 360, 390, 768):
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), width
        for visible in (offline, pending, fault):
            assert visible.evaluate("e=>e.scrollWidth<=e.clientWidth+1"), width
        page.screenshot(path=str(OUT / f"SolarPilot-toestelherstel-{width}.png"),
                        full_page=True)

    # Only telemetry changes the displayed deadline. The card does not schedule
    # commands, grant control, infer OFF, or invent successful recovery.
    page.evaluate("""() => {retryOffline.availability_retry.next_check_wall=Date.now()/1000+65;
      retryOffline.availability_retry.remaining_s=65;publishRetry();}""")
    assert "Opnieuw controleren over 1m" in offline.inner_text()
    page.evaluate("""() => {retryOffline.availability_retry.next_check_wall=Date.now()/1000+10;
      retryOffline.availability_retry.remaining_s=10;publishRetry();}""")
    assert "Opnieuw controleren over 10 s" in offline.inner_text()
    page.evaluate("""() => {retryOffline.availability_retry.next_check_wall=Date.now()/1000-1;
      retryOffline.availability_retry.remaining_s=0;publishRetry();}""")
    assert "Nieuwe controle gepland; wacht op de volgende terugmelding." in offline.inner_text()
    assert page.evaluate("retryCalls.length") == 0

    # Current telemetry preserves the actual open help dialog, keyboard focus,
    # and the expanded explanation. Help and observation refresh are read only.
    page.evaluate("c._openHelp('dashboard','priority_board','Voorrang')")
    help_tag = page.evaluate("c._helpDialog.localName")
    help_dialog = card.locator(help_tag)
    assert help_dialog.locator("dialog").is_visible()
    close = help_dialog.locator(".close")
    close.focus()
    page.evaluate("""() => {window.retryHelpNode=c._helpDialog.dialog;
      for(let n=0;n<30;n++){retryAttributes.free_w=1100+n;publishRetry();}}""")
    assert page.evaluate("c._helpDialog.dialog===retryHelpNode")
    assert close.evaluate("e=>e===e.getRootNode().activeElement")
    assert help_dialog.locator("dialog").is_visible()
    assert offline.locator(".reason-details").get_attribute("open") is not None
    assert page.evaluate("retryCalls.length") == 0
    close.click()

    # A global automatic-mode choice is available while a device is offline and
    # recovering. This fake responder accepts that choice, never a device call.
    automatic = card.locator('button[data-action="mode"][data-value="solar"]')
    assert automatic.is_enabled()
    automatic.click()
    assert page.evaluate("retryCalls") == [{
        "domain": "select", "service": "select_option",
        "data": {"entity_id": "select.fictional_solar_mode", "option": "solar"},
    }]
    assert card.locator('button[data-action="mode"][data-value="solar"]').get_attribute("class") == "active"
    assert offline.locator(".badge").inner_text() == "Tijdelijk niet bereikbaar"
    assert pending.locator(".badge").inner_text() == "Wacht op terugmelding"
    assert "Andere beschikbare toestellen kunnen automatisch verder" in card.locator("ha-card").inner_text()

    # Genuine actionable faults still receive the existing visible review
    # banner; an unrelated source wait cannot remove or reset that protection.
    page.evaluate("""() => {retryAttributes.restart_recovery_pending=false;
      retryAttributes.problem_kind='command_fault';
      retryAttributes.problem='Voorbeeld echte opdrachtfout vraagt controle';
      retryAttributes.reset_entity='button.fictional_review';publishRetry();}""")
    assert "Aandacht nodig" in card.locator("ha-card").inner_text()
    assert "Voorbeeld echte opdrachtfout vraagt controle" in card.locator("ha-card").inner_text()
    assert card.locator('button[data-action="reset"]').count() == 1
    assert "Opdrachtfout: ongeldige koppeling vraagt controle" in fault.inner_text()
    assert page.evaluate("retryCalls.length") == 1
    assert not errors, errors
    print("Device retry browser validation: source and uncertain-command waits, five-minute check deadlines, actual-net-surplus policy, unknown power, open details/help focus, global automatic mode with one offline device, true-fault visibility and four widths passed; fictitious data, one explicit mode choice and zero device commands.")
    browser.close()
