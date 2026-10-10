"""Browser-check the compact SG card with fictitious measurements only.

Run build_example.py first. This check proves browser behavior, never live
Home Assistant access, Shelly timer acceptance or physical Panasonic response.
"""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR', '/tmp/solarpilot-browser-tests'))
OUT.mkdir(parents=True, exist_ok=True)
errors = []
with sync_playwright() as p:
    executable = os.environ.get('SOLARPILOT_CHROMIUM_PATH') or shutil.which('chromium')
    browser = p.chromium.launch(**({'executable_path': executable} if executable else {}),
                                headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, locale='nl-BE')
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.set_content((ROOT / 'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'), wait_until='load')
    page.wait_for_selector('solar-pilot-card >> h1')
    page.locator('solar-pilot-card >> button[data-action=view][data-value=comfort]').click()
    panel = page.locator('solar-pilot-card >> .heatpump-sg')
    page.screenshot(path=str(OUT / 'SolarPilot-SG-compact-390.png'), full_page=True)
    panel.locator('details[data-ui-key="sg:comfort:details"] > summary').click()
    panel.locator('details[data-ui-key="sg:comfort:monitor"] > summary').click()
    assert panel.locator('[role=switch]').count() == 1
    assert panel.locator('input, select').count() == 0
    assert '50 °C' in panel.inner_text() and 'Verwarmen' in panel.inner_text()
    assert 'Panasonic-reactie niet afzonderlijk bevestigd' in panel.inner_text()
    assert 'voeding 1 1,72 kW · voeding 2 0 W' in panel.inner_text()
    assert 'Totaal voeding 1 + voeding 2' in panel.inner_text()
    assert 'compressor draait · 33 Hz' in panel.inner_text()
    assert 'Ontvangen SG-status\nOnbekend' in panel.inner_text()
    assert 'SG-effect op verbruik\nNiet afzonderlijk bevestigd' in panel.inner_text()
    assert 'Algemene SG-boost' in panel.inner_text()
    assert 'Extra-koelbeveiliging\nNiet bevestigd' in panel.inner_text()
    page.evaluate('''() => {window.c=document.querySelector('solar-pilot-card');window.calls=[];
      c._hass.callService=async(...args)=>calls.push(args);
      window.before=[...c.shadowRoot.querySelectorAll('details')].map(d=>[d.dataset.uiKey,d.open]);
      for(let n=0;n<80;n++){const a=structuredClone(c._last.attributes);a.panasonic.temperature_c=46+n/100;
        c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}''')
    assert page.evaluate('JSON.stringify(before)===JSON.stringify([...c.shadowRoot.querySelectorAll("details")].map(d=>[d.dataset.uiKey,d.open]))')
    assert page.evaluate('calls.length') == 0
    q = panel.locator('[data-help-key=enabled]')
    q.click()
    host = page.locator('solar-pilot-option-help-dialog')
    assert host.locator('dialog').is_visible()
    assert 'SG' in host.locator('dialog').inner_text()
    # Opening help is also stable while backend reports keep arriving.
    page.evaluate('''() => {for(let n=0;n<80;n++){const a=structuredClone(c._last.attributes);
      a.panasonic.temperature_c=47+n/100;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}''')
    assert host.locator('dialog').is_visible()
    assert page.evaluate('JSON.stringify(before)===JSON.stringify([...c.shadowRoot.querySelectorAll("details")].map(d=>[d.dataset.uiKey,d.open]))')
    for width in (320, 390, 768, 1280):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
        assert panel.evaluate('e=>e.scrollWidth<=e.clientWidth+1'), width
        assert host.locator('dialog').evaluate('e=>e.scrollWidth<=e.clientWidth+1'), width
        page.screenshot(path=str(OUT / f'SolarPilot-SG-help-{width}.png'))
    page.keyboard.press('Escape')
    page.screenshot(path=str(OUT / 'SolarPilot-SG-details-1280.png'), full_page=True)
    # Receiving SG can be confirmed independently; caused extra consumption is
    # still not established by either compressor activity or received SG.
    page.evaluate('''() => {const a=structuredClone(c._last.attributes);
      a.panasonic.sg_status='active';a.panasonic.sg_status_confirmed=true;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}''')
    assert 'Ontvangen SG-status\nActief · afzonderlijk bevestigd' in panel.inner_text()
    assert 'SG-effect op verbruik\nNiet afzonderlijk bevestigd' in panel.inner_text()
    # A manually ON contact is not a SolarPilot lease, and a missing second
    # meter does not turn a partial value into a total.
    page.evaluate('''() => {const a=structuredClone(c._last.attributes);
      a.panasonic.power_supply2_w=null;a.panasonic.power_supply2_valid=false;
      a.panasonic.power_complete=false;a.panasonic.power_w=null;a.panasonic.power_kind='unknown';
      a.sg_boost.owner='manual';a.sg_boost.manual_hold=true;a.sg_boost.lease_confirmed=false;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}''')
    assert 'voeding 1 1,72 kW · voeding 2 onbekend' in panel.inner_text()
    assert 'Totaal onbekend · deelmeting onvolledig' in panel.inner_text()
    assert 'Bevestigde lokale toestemming\nNiet bevestigd' in panel.inner_text()
    # An unknown native measurement stays unknown; an ON policy is no relay proof.
    page.evaluate('''() => {const a=structuredClone(c._last.attributes);a.panasonic.power_w=null;
      a.panasonic.power_kind='unknown';a.sg_boost.relay_on=null;a.sg_boost.relay_confirmed=false;
      a.sg_boost.desired_on=true;a.sg_boost.panasonic_confirmed=null;
      a.panasonic.sg_status='unknown';a.panasonic.sg_status_confirmed=false;
      a.panasonic.compressor_running=null;a.panasonic.compressor_frequency_hz=null;
      a.sg_boost.reason='Wacht op betrouwbare contactstatus';
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}''')
    assert 'Vermogen nog niet bekend' in panel.inner_text()
    assert 'Nog niet bevestigd' in panel.inner_text() and 'Afzonderlijk bevestigd' not in panel.inner_text()
    assert 'compressorstatus onbekend' in panel.inner_text()
    assert page.evaluate('calls.length') == 0
    assert not errors, errors
    browser.close()
print('OK: SG details and help each survive 80 updates; independent compressor/received SG/uptake and split meter evidence; honest unknowns/manual lease; 320/390/768/1280 browser layout; zero device calls. Fictitious data only.')
