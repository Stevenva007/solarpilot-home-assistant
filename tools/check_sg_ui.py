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
    browser = p.chromium.launch(executable_path=shutil.which('chromium'), headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, locale='nl-BE')
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.set_content((ROOT / 'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'), wait_until='load')
    page.wait_for_selector('solar-pilot-card >> h1')
    page.locator('solar-pilot-card >> button[data-action=view][data-value=comfort]').click()
    panel = page.locator('solar-pilot-card >> .heatpump-sg')
    panel.locator('details[data-ui-key="sg:comfort:details"] > summary').click()
    panel.locator('details[data-ui-key="sg:comfort:monitor"] > summary').click()
    assert panel.locator('[role=switch]').count() == 1
    assert panel.locator('input, select').count() == 0
    assert '50 °C' in panel.inner_text() and 'Koelen' in panel.inner_text()
    assert 'Panasonic-reactie niet afzonderlijk bevestigd' in panel.inner_text()
    assert 'gedeeltelijke meting' in panel.inner_text()
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
    for width in (320, 390, 768, 1280):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
        assert panel.evaluate('e=>e.scrollWidth<=e.clientWidth+1'), width
        assert host.locator('dialog').evaluate('e=>e.scrollWidth<=e.clientWidth+1'), width
        page.screenshot(path=str(OUT / f'SolarPilot-SG-help-{width}.png'))
    page.keyboard.press('Escape')
    # An unknown native measurement stays unknown; an ON policy is no relay proof.
    page.evaluate('''() => {const a=structuredClone(c._last.attributes);a.panasonic.power_w=null;
      a.panasonic.power_kind='unknown';a.sg_boost.relay_on=null;a.sg_boost.relay_confirmed=false;
      a.sg_boost.desired_on=true;a.sg_boost.panasonic_confirmed=null;
      a.sg_boost.reason='Wacht op betrouwbare contactstatus';
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}''')
    assert 'Vermogen nog niet bekend' in panel.inner_text()
    assert 'Nog niet bevestigd' in panel.inner_text() and 'Afzonderlijk bevestigd' not in panel.inner_text()
    assert page.evaluate('calls.length') == 0
    assert not errors, errors
    browser.close()
print('OK: SG disclosure and help survive 80 updates, only native monitoring, honest unknowns, 320/390/768/1280 browser layout, zero device calls. Fictitious data only.')
