"""Chromium display acceptance for flexible loads and protected cycle reserves.

All appliance data are fictitious, all network requests are blocked and all
service calls fail the test. Run tools/build_example.py for this exact release.
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
 window.c=document.querySelector('solar-pilot-card');window.reserveWrites=[];
 const a=structuredClone(c._last.attributes);a.mode='solar';a.config_entry_id='fictional-reserve-entry';
 const old=(a.devices||[]).find(d=>d.kind==='switch')||{};
 window.reserveAllocation={available_w:1548,required_w:520,sufficient:true,
   instant_free_w:1555,filtered_free_w:1548,smoothing_hold_w:7,
   protected_cycle_reserve_w:1800,solar_cycle_reserve_relief_w:1800,
   solar_cycle_reserve_w:0,comfort_and_cycle_reserve_w:1800,solar_applied_reserve_w:0,
   remaining_solar_w:1548,electrical_headroom_w:5060,remaining_cap_w:3260};
 window.reserveDevice={...old,id:'fictional-flexible-load',name:'Voorbeeld ontvochtiger',
   kind:'switch',non_interruptible:false,mode:'auto',available:true,on:false,power_w:0,
   reason:'Wacht op stabiel zonneoverschot',start_requirements:{},
   start_diagnostics:{summary:'Wacht op stabiel zonneoverschot',missing:[],
     power:{measurement_valid:true,required_start_w:520,measured_free_w:1555},
     stable_start:{configured_s:300,remaining_s:300}}};
 a.devices=[{id:'fictional-dishwasher',name:'Voorbeeld afwasmachine',kind:'dishwasher',
   mode:'auto',available:true,on:true,power_w:1800,estimated:true,owned:false,
   reason:'Extern actief; niet overnemen',dishwasher:{request_status:'running'}},reserveDevice];
 window.reserveAttributes=a;
 window.publishReserve=()=>{
   reserveDevice.start_diagnostics.power.allocation=structuredClone(reserveAllocation);
   reserveDevice.start_requirements.allocated_start_power={...reserveAllocation,met:reserveAllocation.sufficient};
   const next=structuredClone(reserveAttributes);
   c.hass={...c._hass,user:{id:'fictional-admin',is_admin:true},
     callService:async(...args)=>{reserveWrites.push(args);throw Error('No physical or policy writes allowed');},
     states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:next}}};
 };
 c._view='overview';publishReserve();
} """

with sync_playwright() as p:
    executable = os.environ.get("SOLARPILOT_CHROMIUM_PATH") or shutil.which("chromium")
    browser = p.chromium.launch(**({"executable_path": executable} if executable else {}),
                                headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 1000}, locale="nl-BE",
                            timezone_id="Europe/Brussels")
    page.route("**/*", lambda route: route.abort())
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content((ROOT / "SolarPilot-voorbeeld.html").read_text(), wait_until="load")
    page.wait_for_selector("solar-pilot-card >> h1")
    page.evaluate(SETUP)
    card = page.locator("solar-pilot-card")
    row = card.locator('[data-reason-key="overview:device:fictional-flexible-load"]')
    row.locator(".reason-details > summary").click()

    def assert_fact(label, value):
        matching = row.locator(".start-facts > span").filter(has_text=label)
        assert matching.count() == 1, label
        assert matching.locator("b").inner_text() == value, label

    assert_fact("Reserve voor lopende beschermde cycli · elektrisch behouden", "1,8 kW")
    assert_fact("Cyclusreserve afgetrokken van zonnestroom", "0 W")
    assert_fact("Benodigd voor start", "520 W")
    assert_fact("Zonnebudget na reserves en eerdere toewijzingen", "1,55 kW")
    assert_fact("Beschikbaar voor dit toestel", "1,55 kW")
    assert_fact("Elektrisch budget na reserves en eerdere toewijzingen", "3,26 kW")
    assert_fact("Stabiel nodig", "nog 5m")
    assert "Dit telt geen extra zonnestroom of elektrische ruimte bij" in row.inner_text()
    assert "Minimumlooptijden en beschermde cycli blijven gelden" in row.inner_text()
    for width in (320, 360, 390, 768):
        page.set_viewport_size({"width": width, "height": 1000})
        assert page.evaluate("document.documentElement.scrollWidth<=innerWidth"), width
        assert row.evaluate("e=>e.scrollWidth<=e.clientWidth+1"), width
        assert row.locator(".start-facts").evaluate("e=>e.scrollWidth<=e.clientWidth+1"), width
        page.screenshot(path=str(OUT / f"SolarPilot-cyclusreserve-{width}.png"), full_page=True)

    # Telemetry updates preserve an open explanation and a read-only help modal,
    # including keyboard focus. Opening help never writes a policy or setting.
    page.evaluate("c._openHelp('dashboard','priority_board','Voorrang')")
    help_tag = page.evaluate("SP_OPTION_HELP_TAG")
    help_dialog = card.locator(help_tag)
    assert help_dialog.locator("dialog").is_visible()
    close = help_dialog.locator(".close")
    close.focus()
    page.evaluate("""() => {window.reserveHelpNode=c._helpDialog.dialog;
      for(let n=0;n<30;n++){reserveAttributes.free_w=1555+n;publishReserve();}}""")
    assert page.evaluate("c._helpDialog.dialog===reserveHelpNode")
    assert close.evaluate("e=>e===e.getRootNode().activeElement")
    assert help_dialog.locator("dialog").is_visible()
    assert row.locator(".reason-details").get_attribute("open") is not None
    assert page.evaluate("reserveWrites.length") == 0
    close.click()

    # The visible final allocation remains authoritative even when electrical
    # headroom is lower than the otherwise usable solar surplus.
    page.evaluate("""() => {
      Object.assign(reserveAllocation,{available_w:225,sufficient:false,remaining_cap_w:225});
      reserveDevice.reason=reserveDevice.start_diagnostics.summary='Wacht op vermogen / hogere prioriteit';
      reserveDevice.start_diagnostics.missing=['allocated_start_power'];publishReserve();
    }""")
    assert_fact("Zonnebudget na reserves en eerdere toewijzingen", "1,55 kW")
    assert_fact("Beschikbaar voor dit toestel", "225 W")
    assert_fact("Elektrisch budget na reserves en eerdere toewijzingen", "225 W")
    assert "Na de reserves en hogere voorrangen is 225 W beschikbaar" in row.inner_text()
    assert "vrije zonnestroom nodig" not in row.inner_text()

    # Old or incomplete backend snapshots never acquire the new zero-deduction
    # claim from frontend guesses. The original full reserve is still shown.
    page.evaluate("""() => {
      delete reserveAllocation.solar_cycle_reserve_relief_w;
      delete reserveAllocation.solar_cycle_reserve_w;
      Object.assign(reserveAllocation,{available_w:0,sufficient:false,remaining_solar_w:-252});
      publishReserve();
    }""")
    assert_fact("Reserve voor lopende beschermde cycli · komende pieken", "1,8 kW")
    assert_fact("Zonnebudget na reserves en eerdere toewijzingen", "-252 W")
    assert_fact("Beschikbaar voor dit toestel", "0 W")
    assert row.locator(".cycle-reserve-note").count() == 0
    assert "Cyclusreserve afgetrokken van zonnestroom" not in row.inner_text()
    page.evaluate("""() => {Object.assign(reserveAllocation,
      {solar_cycle_reserve_relief_w:2100,solar_cycle_reserve_w:0});publishReserve();}""")
    assert row.locator(".cycle-reserve-note").count() == 0
    assert "Cyclusreserve afgetrokken van zonnestroom" not in row.inner_text()
    assert row.locator(".reason-details").get_attribute("open") is not None
    assert page.evaluate("reserveWrites.length") == 0
    assert not errors, errors
    print("Cycle reserve browser validation: electrical versus solar reservation, actual final budgets, old and malformed snapshots, stable-start wait, help focus, open details and four widths passed; fictitious data only, zero writes.")
    browser.close()
