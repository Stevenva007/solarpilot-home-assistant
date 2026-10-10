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
    assert "Wat regelen SolarPilot en de toestellen nu?" in page.locator("solar-pilot-card >> .overview-view").inner_text()
    assert "Lokale PV-voorspelling" in page.locator("solar-pilot-card >> .overview-view").inner_text()
    page.evaluate("""() => {const c=document.querySelector('solar-pilot-card');window.wallboxClean=structuredClone(c._last.attributes);
      const a=structuredClone(c._last.attributes);a.wallbox.power_w=0;a.wallbox.effective_mode='stopped';
      a.wallbox.activity_known=true;a.wallbox.demand=false;a.wallbox.connected=true;
      const state=c._hass.states[c._entity];c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{...state,attributes:a}}};}""")
    wallbox_tile=page.locator('solar-pilot-card >> .overview-view .tile').filter(has_text='Wallbox')
    assert 'AUTO LAADT NIET · 0 W' in wallbox_tile.inner_text()
    page.evaluate("""() => {const c=document.querySelector('solar-pilot-card');const state=c._hass.states[c._entity];
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{...state,attributes:window.wallboxClean}}};}""")

    # Managed loads + Wallbox are grouped together; Wallbox remains read-only.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="loads"]').click()
    assert page.locator("solar-pilot-card >> .device").count() == 3
    assert page.locator("solar-pilot-card >> .external").count() == 2
    assert page.locator("solar-pilot-card >> .external button").count() == 0
    assert "WALLBOX REGELT ZELF" in page.locator("solar-pilot-card >> .external:not(.wallbox-priority)").inner_text()
    assert "Volledig zonneladen" in page.locator("solar-pilot-card >> .external:not(.wallbox-priority)").inner_text()
    assert page.locator("solar-pilot-card >> .phasepill").count() == 2

    # Panasonic has one compact SG request panel; every native value is read-only.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="comfort"]').click()
    panel = page.locator("solar-pilot-card >> .heatpump-sg")
    assert panel.count() == 1
    assert "Warmtepomp — Panasonic-regeling" in panel.inner_text()
    assert "46,2 °C" in panel.inner_text()
    assert "SG-contact actief; Panasonic-reactie niet afzonderlijk bevestigd" in panel.inner_text()
    assert page.locator("solar-pilot-card >> [data-dhw-setting], solar-pilot-card >> [data-climate-setting]").count() == 0
    assert panel.locator('[role="switch"]').count() == 1
    assert panel.locator('[data-action="sg_boost_enabled"]').get_attribute('aria-checked') == 'true'
    panel.locator('details[data-ui-key="sg:comfort:details"] > summary').click()
    assert "Niet afzonderlijk bevestigd" in panel.inner_text()
    assert "50 °C" in panel.inner_text()
    assert "Alleen voeding 1 · gedeeltelijke meting" in panel.inner_text()
    panel.locator('details[data-ui-key="sg:comfort:monitor"] > summary').click()
    assert "Zone 1" in panel.inner_text() and "Zone 2" in panel.inner_text()
    # Native source/temperature rows offer no control; policy clicks use one virtual switch.
    page.evaluate("""() => {const c=document.querySelector('solar-pilot-card');window.cleanSg=structuredClone(c._last.attributes);
      window.sgCalls=[];c._hass.callService=async(domain,service,data)=>sgCalls.push({domain,service,data});}""")
    panel.locator('[data-action="sg_boost_enabled"]').click()
    page.wait_for_timeout(20)
    assert page.evaluate('sgCalls[0]') == {"domain":"switch", "service":"turn_off",
        "data":{"entity_id":"switch.example_sg_boost_enabled"}}
    assert panel.locator('[data-action="sg_boost_enabled"]').get_attribute('aria-checked') == 'true'
    page.evaluate("""() => {const c=document.querySelector('solar-pilot-card');const a=structuredClone(c._last.attributes);
      a.sg_boost.manual_hold=true;a.sg_boost.state='manual_hold';
      const state=c._hass.states[c._entity];c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{...state,attributes:a}}};}""")
    resume=panel.locator('[data-action="sg_boost_resume"]')
    assert resume.is_visible() and resume.is_enabled()
    resume.click();page.wait_for_timeout(20)
    assert page.evaluate('sgCalls[1]') == {"domain":"button", "service":"press",
        "data":{"entity_id":"button.example_sg_boost_resume"}}
    # Three honest display states; no Panasonic response is inferred from the relay.
    for phase in ('requested', 'contact', 'confirmed'):
        page.evaluate("""phase => {const c=document.querySelector('solar-pilot-card');const a=structuredClone(window.cleanSg);
          a.sg_boost.desired_on=true;a.sg_boost.relay_on=phase==='requested'?null:true;
          a.sg_boost.relay_confirmed=phase!=='requested';a.sg_boost.panasonic_confirmed=phase==='confirmed';
          const state=c._hass.states[c._entity];c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{...state,attributes:a}}};}""", phase)
        for width in (320,390,768,1280):
            page.set_viewport_size({"width":width,"height":1000})
            assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), (phase,width)
            assert panel.evaluate("e=>e.scrollWidth<=e.clientWidth+1"), (phase,width)
            panel.screenshot(path=str(output/f"SolarPilot-SG-{phase}-{width}.png"))
    page.evaluate("""() => {const c=document.querySelector('solar-pilot-card');const state=c._hass.states[c._entity];
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{...state,attributes:window.cleanSg}}};}""")
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

    # Battery page separates physical fleet from what-if analysis; the Wallbox remains under Devices.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="storage"]').click()
    storage_text = page.locator("solar-pilot-card >> .view").inner_text()
    assert "Batterijvloot" in storage_text and "Batterijscenario" in storage_text
    assert page.locator('solar-pilot-card >> button[data-value="storage"]').inner_text() == "Batterij"

    # Canonical guide has its own tab and the dedicated card still exists.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="guide"]').click()
    guide_text = page.locator("solar-pilot-card >> .guide").text_content()
    assert "Panasonic" in guide_text and "SG" in guide_text and "Logische interface" in guide_text and "migratie" in guide_text.lower()
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
    # The daily view is one complete stack: four fixed protections followed by
    # the five reorderable example rules.
    assert page.locator('solar-pilot-card >> .priority-stack .priority-row').count() == 6
    assert page.locator('solar-pilot-card >> .priority-stack .priority-row.fixed').count() == 1
    assert page.locator('solar-pilot-card >> .priority-stack').get_attribute('aria-label') == 'Volledige voorrangslijst'
    assert page.locator('solar-pilot-card >> .priority-stack').inner_text().count('Mag de auto minder laden?') == 6
    assert page.evaluate("window.calls.length") == 0
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="energy"]').click()
    page.locator('solar-pilot-card >> details.learning summary').click()
    learning_text=page.locator('solar-pilot-card >> details.learning').inner_text()
    assert 'Toestelvermogen en Wallbox-respons leren' in learning_text
    assert 'Apparaat-, lokale PV-, fase- en activiteitsleerdata wissen' in learning_text
    page.evaluate("window.confirmText='';window.confirm=msg=>{window.confirmText=msg;return false}")
    page.locator('solar-pilot-card >> button[data-action="reset_learning"]').click()
    assert 'bewaarde klimaatarchief' in page.evaluate('window.confirmText')
    assert page.evaluate("window.calls.length") == 0
    page.evaluate("window.confirm=()=>true")
    page.locator('solar-pilot-card >> button[data-action="learning"]').click()
    assert page.evaluate("window.calls[0]") == {"domain":"switch","service":"turn_off","data":{"entity_id":"switch.voorbeeld_lokaal_leren"}}

    # Planner settings also route through one validated SolarPilot service.
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="planning"]').click()
    page.evaluate("window.calls=[]; window.confirm=()=>true")
    planner_settings_shell = page.locator('solar-pilot-card >> .planning .settings-shell')
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
    assert "Actuele verdeling rond Auto laden" in page.locator("solar-pilot-card >> .wallbox-priority").inner_text()
    assert "Auto laden eerst" in page.locator("solar-pilot-card >> .device").first.inner_text()
    page.set_viewport_size({"width":1440,"height":1000})
    page.screenshot(path=str(output/"SolarPilot-wallbox-beta24-desktop.png"),full_page=True)

    # Untrusted strings remain text after switching to the loads view.
    page.evaluate("""() => {const c=document.querySelector('solar-pilot-card');const a=JSON.parse(JSON.stringify(c._last.attributes));const bad='<img src=x onerror="window.injected=true">';a.devices[0].name=bad;a.wallbox.name=bad;a.wallbox.reason=bad;a.sg_boost.reason=bad;a.panasonic.status=bad;c.hass={states:{'sensor.solarpilot_status':{state:'x',attributes:a},'sensor.solarpilot_actuele_uitleg':c._hass.states['sensor.solarpilot_actuele_uitleg']},callService:async()=>{}};}""")
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="loads"]').click()
    assert page.locator("solar-pilot-card >> img").count() == 0
    assert not page.evaluate("!!window.injected")

    assert not errors, errors
    browser.close()
print("Browser checks passed: compact Panasonic/SG + Planning tab, readonly native monitoring and SG policy controls, read-only Wallbox, responsive 320/390/768/1280, safe action routing and HTML escaping.")
