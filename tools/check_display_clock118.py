"""Real Chromium regression: SG presentation survives a skewed screen clock.

Only fictitious in-page data and a mocked read-only time response are used.
No Home Assistant, source integration or physical device is contacted.
"""
import os
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR', '/tmp/solarpilot-browser-tests'))
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as playwright:
    executable = os.environ.get('SOLARPILOT_CHROMIUM_PATH') or shutil.which('chromium')
    browser = playwright.chromium.launch(**({'executable_path': executable} if executable else {}),
                                         headless=True, args=['--no-sandbox'])
    for width, offset in ((390, -5.4), (1280, -3600), (390, 3600)):
        page = browser.new_page(viewport={'width': width, 'height': 900}, locale='nl-BE')
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.set_content((ROOT/'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'), wait_until='load')
        page.wait_for_selector('solar-pilot-card >> h1')
        page.locator('solar-pilot-card >> button[role=tab][data-value=comfort]').click()
        result = page.evaluate('''async offset=>{
          const c=document.querySelector('solar-pilot-card'),wall=Date.now()/1000,mono=performance.now()/1000;
          let elapsed=0;const advance=seconds=>elapsed+=seconds;
          Date.now=()=>1000*(wall+elapsed+offset);
          Object.defineProperty(performance,'now',{configurable:true,value:()=>1000*(mono+elapsed)});
          const calls=[],connection={connected:true},source=structuredClone(c._last.attributes);
          source.display_clock={schema:1,read_only:true};source.mode='solar';
          Object.assign(source.sg_boost,{enabled:true,configured:true,desired_on:false,relay_on:false,relay_stale_s:120,
            relay_confirmed:true,relay_valid_until:null,manual_hold:false,fault:'',owner:'none',
            manual_control:{mode:'auto',active:false,duration_s:null,expires_at:null,remaining_s:null,reason:''}});
          const hass={...c._hass,user:{id:'fictional-reader',is_admin:false},connection,
            callService:async()=>{throw new Error('A display refresh must not send a service');},
            callWS:async msg=>{calls.push(msg);return {schema:1,read_only:true,
              config_entry_id:source.config_entry_id,server_time:wall+elapsed};}};
          const update=()=>{source.sg_boost.observed_at=wall+elapsed;source.sg_boost.relay_observed_at=wall+elapsed;
            c.hass={...hass,states:{...hass.states,[c._entity]:{state:'Zonnestroom',attributes:structuredClone(source)}}};};
          update();await new Promise(resolve=>setTimeout(resolve,0));
          const rows=[];for(let i=0;i<151;i++){
            update();await c._syncDisplayClock();c._refreshObservationDisplay();
            const control=c.shadowRoot.querySelector('[data-sg-manual-control]');
            rows.push({mode:control.dataset.sgManualControl,
              selected:control.querySelector('[data-sg-mode=auto]').getAttribute('aria-pressed'),
              contact:c.shadowRoot.querySelector('[data-sg-stage=relay]').textContent.trim()});advance(1);
          }
          window.clockProbe={c,hass,source,advance,wall,update,calls};
          return {rows,calls};
        }''', offset)
        assert all(row['mode'] == 'auto' and row['selected'] == 'true' for row in result['rows']), result['rows']
        assert all('Open' in row['contact'] for row in result['rows'])
        assert len(result['calls']) <= 6 and all(row['type'] == 'solar_pilot/display_clock' for row in result['calls'])
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), width
        page.screenshot(path=str(OUT/f'SolarPilot-clock-{width}-{offset}.png'), full_page=True)
        # A new time reference is not a new appliance/source report.
        page.evaluate('''async()=>{
          const {c,hass,source,advance,wall}=clockProbe;advance(181);
          c._displayClockAttempt=null;await c._syncDisplayClock();
          c._refreshObservationDisplay();
        }''')
        control = page.locator('solar-pilot-card >> [data-sg-manual-control]')
        assert control.get_attribute('data-sg-manual-control') == 'unknown', control.inner_text()
        assert 'Bedieningskeuze onbekend' in control.inner_text()
        assert 'Actief' not in page.locator('solar-pilot-card >> [data-sg-stage=relay]').inner_text()
        page.evaluate('''async()=>{
          const {c,source,update}=clockProbe;update();await c._syncDisplayClock();c._refreshObservationDisplay();
        }''')
        assert control.get_attribute('data-sg-manual-control') == 'auto'
        assert not errors, errors
        page.close()
    browser.close()
print('OK: Chromium clock skew, 453 live SG updates, stale evidence, no device commands, mobile layout')
