"""Check start explanations with fictitious data, never a live HA connection."""
import os
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR', '/tmp/solarpilot-browser-tests'))
OUT.mkdir(parents=True, exist_ok=True)
errors = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=shutil.which('chromium'), headless=True,
                                args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 1050}, locale='nl-BE')
    page.route('**/*', lambda route: route.abort())
    page.on('pageerror', lambda err: errors.append(str(err)))
    page.set_content((ROOT/'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'))
    page.wait_for_selector('solar-pilot-card >> h1')
    page.evaluate('''() => {
      window.card = document.querySelector('solar-pilot-card');
      window.calls = [];
      card._hass.callService = async (...args) => calls.push(args);
      const a = structuredClone(card._last.attributes);
      a.mode = 'solar';
      a.devices = [{id:'dw', kind:'dishwasher', name:'Afwasmachine · fictieve controle',
        mode:'auto', available:true, on:false, power_w:0,
        dishwasher:{arming_mode:'app',ticket_armed:true, app_request:true, program:'Eco', phase:'Ready To Start'},
        start_requirements:{demand_or_time_window:{met:true}},
        start_diagnostics:{summary:'Wacht op vermogen / hogere prioriteit', missing:[],
          power:{required_start_w:2100, measured_free_w:500, measurement_valid:true,
            solar_start_pool:{available_solar_w:1500, wallbox_solar_w:1000,
              lower_loads_releasable_w:0}}, stable_start:{configured_s:300}}}];
      window.refreshStart = (patch={}) => {
        const next = structuredClone(a); Object.assign(next.devices[0],patch);
        card.hass = {...card._hass,states:{...card._hass.states,
          [card._entity]:{state:'Zonnestroom',attributes:next}}};
      };
      refreshStart();
    }''')
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="loads"]').click()
    row = page.locator('solar-pilot-card >> .dishwasher')
    explanation = row.locator('.start-explanation')
    text = explanation.inner_text()
    assert 'Van autoladen beschikbaar' in text and '1,5 kW' in text
    assert 'Nog ongeveer 600 W zonnevermogen voor dit toestel nodig.' in text
    assert '1,6 kW' not in text and 'vrije injectie nodig' not in text
    for width in (320, 390, 768, 1440):
        page.set_viewport_size({'width':width, 'height':1050})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
        assert row.evaluate('e => e.scrollWidth <= e.clientWidth+2'), width
    row.screenshot(path=str(OUT/'SolarPilot-startvermogen-voorbeeld.png'))
    page.evaluate('''() => refreshStart({available:false,
      dishwasher:{arming_mode:'app',ticket_armed:true,app_request:true,gates:{connection:false},
        connection_report:{state:'Connected',age_s:1080,maximum_age_s:300,current:false}},
      start_requirements:{demand_or_time_window:{met:false}},
      start_diagnostics:{summary:'Afwasmachine offline of verbindingsterugmelding te oud',
        missing:['demand_or_time_window'],power:{required_start_w:2100,
          measured_free_w:500,measurement_valid:true,solar_start_pool:null}}})''')
    text = explanation.inner_text()
    assert 'APP-startvraag ontvangen; wacht op bevestigde toestelstatus.' in text
    assert 'Het toestel meldt nog geen startvraag.' not in text
    assert '18m oud; maximaal 5m' in text
    assert 'Nog ongeveer' not in text and 'Van autoladen beschikbaar' not in text
    page.evaluate('''() => refreshStart({start_diagnostics:{summary:'Energietelemetrie ontbreekt',
      missing:[],power:{required_start_w:2100,measured_free_w:null,
        measurement_valid:false,solar_start_pool:null}}})''')
    assert 'niet betrouwbaar' in explanation.inner_text()
    page.evaluate("() => refreshStart({on:true,dishwasher:{ticket_armed:false,app_request:false}})")
    text = explanation.inner_text()
    assert 'Een lopende afwasbeurt wordt niet opnieuw gestart' in text
    assert 'Nog nodig' not in text and 'Benodigd voor start' not in text
    assert 'Eén beurt vrijgegeven' not in text and '5m vereist' not in text
    assert page.evaluate('calls.length') == 0
    assert not errors, errors
    browser.close()
print('OK: correct Wallbox/start-pool shortfall, honest stale APP request, invalid-meter state, widths 320/390/768/1440, zero appliance calls; fictitious data only.')
