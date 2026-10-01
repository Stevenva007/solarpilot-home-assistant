"""Browser-check the real SolarPilot Control Center card in offline example HTML."""
from pathlib import Path
import shutil
import os
from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
output=Path(os.environ.get("SOLARPILOT_SCREENSHOT_DIR", "/tmp/solarpilot-browser-tests"))
output.mkdir(parents=True,exist_ok=True)
browser_path = shutil.which("chromium") or shutil.which("google-chrome")
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=browser_path, headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width":390,"height":844}, device_scale_factor=1)
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content((root/"SolarPilot-voorbeeld.html").read_text(encoding="utf-8"), wait_until="load")
    page.wait_for_selector("solar-pilot-card >> h1")

    assert page.locator("solar-pilot-card >> .nav button").count() == 9
    assert page.locator("solar-pilot-card >> .overview-view").count() == 1
    assert "Wat doet het EMS nu?" in page.locator("solar-pilot-card >> .overview-view").inner_text()
    assert "Lokale PV-voorspelling" in page.locator("solar-pilot-card >> .overview-view").inner_text()

    # Managed loads + Wallbox are grouped together; Wallbox remains read-only.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="loads"]').click()
    assert page.locator("solar-pilot-card >> .device").count() == 3
    assert page.locator("solar-pilot-card >> .external").count() == 2
    assert page.locator("solar-pilot-card >> .external button").count() == 0
    assert "ALLEEN LEZEN" in page.locator("solar-pilot-card >> .external:not(.wallbox-priority)").inner_text()
    assert page.locator("solar-pilot-card >> .phasepill").count() == 2

    # Comfort is one logical page containing DHW + the complete climate Control Center.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="comfort"]').click()
    assert page.locator("solar-pilot-card >> .dhw").count() == 1
    assert page.locator("solar-pilot-card >> .climate").count() == 1
    assert "46,2 °C" in page.locator("solar-pilot-card >> .dhw").inner_text()
    page.locator("solar-pilot-card >> details.dhw-rules summary").click()
    assert page.locator("solar-pilot-card >> input[data-dhw-setting]").count() == 9
    climate_text = page.locator("solar-pilot-card >> .climate").text_content()
    for label in ("Meldingen", "Bevindingen & leren", "Instellingen", "Uitleg", "Lokale weerscorrectie", "Coast-evaluatie"):
        assert label in climate_text, label
    assert page.locator("solar-pilot-card >> [data-climate-setting]").count() == 43
    assert "Advies:" in climate_text and "Lager:" in climate_text and "Hoger:" in climate_text
    assert "geen raam/deursensoren" in climate_text.lower()
    page.set_viewport_size({"width":1280,"height":1100})
    page.screenshot(path=str(output/"SolarPilot-Klimaat-dashboard.png"), full_page=False)
    # Focused climate Control Center: collapse findings, open settings and capture the climate block itself.
    findings = page.locator('solar-pilot-card >> .climate-findings')
    if findings.get_attribute('open'):
        findings.locator(':scope > summary').click()
    settings_shell = page.locator('solar-pilot-card >> .climate-settings-shell')
    if not settings_shell.get_attribute('open'):
        settings_shell.locator(':scope > summary').click()
    page.locator('solar-pilot-card >> .climate').screenshot(path=str(output/"SolarPilot-Klimaat-instellingen.png"))
    page.set_viewport_size({"width":390,"height":844})

    # Planning has its own page: joint horizon, device targets, timeline and editable settings.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="planning"]').click()
    planning_text = page.locator("solar-pilot-card >> .planning").inner_text()
    for label in ("Planning", "Basislastvertrouwen", "Dagdoelen", "Tijdlijn", "Plannerkwaliteit", "What-if", "Plannerinstellingen", "Hoe wordt gekozen?"):
        assert label in planning_text, label
    assert page.locator("solar-pilot-card >> [data-planner-setting]").count() == 15
    assert "Lokale namiddagschaduw" in planning_text
    assert "92%" in planning_text
    assert "82%" not in planning_text  # geen losse misleidende totaalscore meer
    assert "beschermde cyclus" in planning_text.lower() and "Eco" in planning_text

    # Daily cost is separate from forecast and own PV is not subtracted twice.
    cost = page.locator("solar-pilot-card >> .electricity-today")
    assert "2,82" in cost.inner_text()
    assert "1,50" in cost.inner_text()
    assert "6 kWh" in cost.inner_text()
    assert "niet nogmaals aftrekken" in cost.inner_text()
    horizon = page.locator("solar-pilot-card >> .planned-cost")
    if horizon.count():
        horizon.locator("summary").click()
    # Keep open sections stable across ordinary 5-second telemetry deliveries.
    page.evaluate("""() => { const c=document.querySelector('solar-pilot-card');
      c.shadowRoot.querySelectorAll('details').forEach(d=>d.open=true);
      window.openBefore=Array.from(c.shadowRoot.querySelectorAll('details')).map(d=>d.open);
      const a=JSON.parse(JSON.stringify(c._last.attributes));a.grid_w=-1234;
      c.hass={...c._hass,states:{...c._hass.states,'sensor.solarpilot_status':{state:'Zonnestroom',attributes:a}}};
    }""")
    assert page.evaluate("""() => JSON.stringify(window.openBefore) === JSON.stringify(
        Array.from(document.querySelector('solar-pilot-card').shadowRoot.querySelectorAll('details')).map(d=>d.open))""")
    # No clipped cost tiles at mobile widths or desktop width.
    for width in (320,390,768,1440):
        page.set_viewport_size({"width":width,"height":1000})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), width
    page.set_viewport_size({"width":1440,"height":1050})
    page.evaluate("document.body.style.maxWidth='none'")
    page.screenshot(path=str(output/"SolarPilot-kosten-beta24-desktop.png"),full_page=True)
    page.set_viewport_size({"width":390,"height":844})
    cost.screenshot(path=str(output/"SolarPilot-kosten-beta24-mobiel.png"))

    # Energy page groups forecast, phase, capacity and learning; planner summary remains compact.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="energy"]').click()
    energy_text = page.locator("solar-pilot-card >> .ems").inner_text()
    for label in ("Kwartierpiek","Fasebewaking","Zonnevoorspelling","Lokale PV-correctie","Planner","Faseverdeling","Leren & modelkwaliteit"):
        assert label in energy_text, label
    assert "L3" in energy_text and "P95" in energy_text

    # Storage page separates physical battery fleet from what-if analysis.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="storage"]').click()
    storage_text = page.locator("solar-pilot-card >> .view").inner_text()
    assert "Batterijvloot" in storage_text and "Batterijscenario" in storage_text

    # Canonical guide has its own tab and the dedicated card still exists.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="guide"]').click()
    guide_text = page.locator("solar-pilot-card >> .guide").text_content()
    assert "Sanitair warm water: rustig normaal doel" in guide_text and "Logische interface" in guide_text and "migratie" in guide_text.lower()
    page.evaluate("""() => {const main=document.querySelector('solar-pilot-card');const guide=document.createElement('solar-pilot-guide-card');guide.setConfig({});guide.hass=main._hass;document.body.appendChild(guide);}""")
    assert "Actuele werking" in page.locator("solar-pilot-guide-card >> ha-card").inner_text()

    # Responsive: internal navigation may scroll, the page may not.
    for width in (320,390,768,1280):
        page.set_viewport_size({"width":width,"height":1000})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth"), width
    page.set_viewport_size({"width":390,"height":844})

    page.evaluate("""() => {const c=document.querySelector('solar-pilot-card');
      c.shadowRoot.querySelectorAll('details').forEach(d=>d.open=false); c._uiState={};}""")
    # Action routing: priority navigation sends nothing; learning only touches SolarPilot virtual entities.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="loads"]').click()
    page.evaluate("""() => {const c=document.querySelector('solar-pilot-card');window.calls=[];c._hass.callService=async(domain,service,data)=>window.calls.push({domain,service,data});}""")
    page.locator('solar-pilot-card >> .policy button[data-value="priorities"]').click()
    assert page.locator('solar-pilot-card >> .priority-row').count() == 5
    assert page.evaluate("window.calls.length") == 0
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="energy"]').click()
    page.locator('solar-pilot-card >> details.learning summary').click()
    page.locator('solar-pilot-card >> button[data-action="learning"]').click()
    assert page.evaluate("window.calls[0]") == {"domain":"switch","service":"turn_off","data":{"entity_id":"switch.voorbeeld_lokaal_leren"}}

    # DHW number binding remains direct and scoped to SolarPilot number entities.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="comfort"]').click()
    page.locator("solar-pilot-card >> details.dhw-rules summary").click()
    page.locator('solar-pilot-card >> input[data-dhw-setting="pv_threshold_w"]').fill('1200')
    page.locator('solar-pilot-card >> input[data-dhw-setting="pv_threshold_w"]').press('Tab')
    assert page.evaluate("window.calls[1]") == {"domain":"number","service":"set_value","data":{"entity_id":"number.voorbeeld_boiler_pv_threshold_w","value":1200}}

    # Every climate setting is editable and routes through one validated SolarPilot service.
    page.evaluate("window.calls=[]; window.confirm=()=>true")
    shell = page.locator('solar-pilot-card >> .climate-settings-shell')
    if not shell.get_attribute('open'):
        shell.locator(':scope > summary').click()
    planning = page.locator('solar-pilot-card >> .climate-settings details').filter(has_text='Comfort & planning')
    if not planning.get_attribute('open'):
        planning.locator('summary').click()
    soft = page.locator('solar-pilot-card >> input[data-climate-setting="soft_band_c"]')
    soft.fill('0.6')
    soft.dispatch_event('change')
    page.wait_for_timeout(20)
    call = page.evaluate("window.calls[0]")
    assert call["domain"] == "solar_pilot" and call["service"] == "set_climate_setting"
    assert call["data"]["setting"] == "soft_band_c" and call["data"]["value"] == 0.6

    # Planner settings also route through one validated SolarPilot service.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="planning"]').click()
    page.evaluate("window.calls=[]; window.confirm=()=>true")
    planner_settings_shell = page.locator('solar-pilot-card >> .planning .climate-settings-shell')
    if not planner_settings_shell.get_attribute('open'):
        planner_settings_shell.locator(':scope > summary').click()
    pset = page.locator('solar-pilot-card >> input[data-planner-setting="horizon_h"]')
    pset.fill('42')
    pset.dispatch_event('change')
    page.wait_for_timeout(20)
    pcall = page.evaluate("window.calls[0]")
    assert pcall["domain"] == "solar_pilot" and pcall["service"] == "set_planner_setting"
    assert pcall["data"]["setting"] == "horizon_h" and pcall["data"]["value"] == 42

    # Final screenshot: compact overview using the clean example state.
    page.evaluate("document.querySelectorAll('solar-pilot-guide-card').forEach(el => el.remove())")
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="overview"]').click()
    page.screenshot(path=str(output/"SolarPilot-EMS-voorbeeld.png"), full_page=True)

    page.locator('solar-pilot-card >> button[data-action="view"][data-value="loads"]').click()
    assert "Wallbox-voorrang per verbruiker" in page.locator("solar-pilot-card >> .wallbox-priority").inner_text()
    assert "Wallbox eerst" in page.locator("solar-pilot-card >> .device").first.inner_text()
    page.set_viewport_size({"width":1440,"height":1000})
    page.screenshot(path=str(output/"SolarPilot-wallbox-beta24-desktop.png"),full_page=True)

    # Untrusted strings remain text after switching to the loads view.
    page.evaluate("""() => {const c=document.querySelector('solar-pilot-card');const a=JSON.parse(JSON.stringify(c._last.attributes));const bad='<img src=x onerror="window.injected=true">';a.devices[0].name=bad;a.wallbox.name=bad;a.wallbox.reason=bad;a.dhw.status=bad;a.dhw.reason=bad;c.hass={states:{'sensor.solarpilot_status':{state:'x',attributes:a},'sensor.solarpilot_actuele_uitleg':c._hass.states['sensor.solarpilot_actuele_uitleg']},callService:async()=>{}};}""")
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="loads"]').click()
    assert page.locator("solar-pilot-card >> img").count() == 0
    assert not page.evaluate("!!window.injected")

    assert not errors, errors
    browser.close()
print("Browser checks passed: unified Control Center + Planning tab, editable climate/planner settings with advice/consequences, read-only Wallbox, responsive 320/390/768/1280, safe action routing and HTML escaping.")
