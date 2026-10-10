"""Real browser check of independent warmtepomp/SG evidence, using fiction only.

Requires build_example.py and a Playwright Chromium. No network account,
Home Assistant instance, physical service call or hardware acceptance is used.
"""
import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR', '/tmp/solarpilot-browser-tests'))
OUT.mkdir(parents=True, exist_ok=True)
errors = []
with sync_playwright() as playwright:
    executable = os.environ.get('SOLARPILOT_CHROMIUM_PATH') or shutil.which('chromium')
    browser = playwright.chromium.launch(**({'executable_path': executable} if executable else {}),
                                         headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, locale='nl-BE')
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_content((ROOT / 'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'), wait_until='load')
    page.wait_for_selector('solar-pilot-card >> h1')
    page.evaluate('''() => {
      window.c=document.querySelector('solar-pilot-card');window.qaCalls=[];
      window.qaClockMs=Date.now();Date.now=()=>qaClockMs;
      window.qaBase=structuredClone(c._last.attributes);
      window.qaApply=(state='active',sg=false,extra={})=>{
        const a=structuredClone(qaBase),stamp=Date.now()/1000;
        a.panasonic={configured:true,source_stale_s:120,temperature_c:47.5,target_c:50,
          power_w:1720,power_kind:'measured',power_scope:'split',power_complete:true,
          power_supply1_w:1720,power_supply2_w:0,power_supply1_valid:true,power_supply2_valid:true,
          compressor_running:state==='active'?true:state==='idle'?false:null,
          compressor_frequency_hz:state==='active'?33:state==='idle'?0:null,
          operation:{state,label:state==='active'?'Compressor draait':state==='idle'?'Compressor staat stil':'Werking onbekend',
            evidence:state==='unknown'?'none':'compressor_frequency',observed_at:stamp,stale_s:120},
          context:'space_heating',context_reliable:true,program:'heating',status:'Panasonic meldt ruimteverwarming',
          sg_status:sg?'active':'inactive',sg_status_confirmed:true,
          zones:[{name:'Voorbeeldzone',mode:'heat',action:'heating',target_c:21,temperature_c:20.8,
            available:true,observed_at:stamp}]};
        for(const key of ['power_observed_at','power_supply1_observed_at','power_supply2_observed_at',
          'temperature_stamp','target_stamp','compressor_frequency_observed_at','sg_status_observed_at','context_stamp'])a.panasonic[key]=stamp;
        Object.assign(a.panasonic,extra);
        a.sg_boost={configured:true,enabled:true,desired_on:sg,relay_on:sg,relay_confirmed:true,
          owner:sg?'solarpilot':'none',lease_confirmed:sg,lease_remaining_s:180,
          remaining_s:1200,rest_remaining_s:0,observed_at:stamp,relay_observed_at:stamp,relay_stale_s:120,relay_valid_until:sg?stamp+180:null,
          reason:sg?'SG-contact actief; Panasonic-reactie afzonderlijk gemeld.':'Panasonic regelt zelfstandig; geen SG-aanvraag.',
          enabled_entity:'switch.example_sg_enabled',profile:'general',profile_confirmed:true,
          start_threshold_w:3000,estimated_power_w:3200};
        const old=c._hass.states[c._entity];
        c.hass={...c._hass,callService:async(...args)=>qaCalls.push(args),
          states:{...c._hass.states,[c._entity]:{...old,state:'Zonnestroom',attributes:a}}};
      };
      qaApply();
      const style=document.createElement('style');style.textContent=`body{max-width:1100px;background:#111;color:#eee}
        solar-pilot-card{--card-background-color:#1e1e1e;--ha-card-background:#1e1e1e;--secondary-background-color:#282828;
          --primary-text-color:#eee;--secondary-text-color:#aaa;--divider-color:#444;--primary-color:#009ec2}`;
      document.head.append(style);
    }''')
    row = page.locator('solar-pilot-card >> [data-reason-key="overview:sg"]')
    assert row.count() == 1
    assert row.get_attribute('data-activity') == 'active'
    assert row.locator('[data-sg-stage=request]').inner_text().endswith('Niet aangevraagd')
    assert row.locator('[data-sg-stage=relay]').inner_text().endswith('Open')
    assert row.locator('[data-sg-stage=received]').inner_text().endswith('Niet actief · afzonderlijk bevestigd')
    assert '33 Hz' in row.inner_text() and '0 W' in row.inner_text()
    assert row.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'sp-heatpump-turn'
    page.screenshot(path=str(OUT / 'SolarPilot-warmtepomp-overview65-active.png'), full_page=True)
    page.emulate_media(reduced_motion='reduce')
    assert row.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
    page.emulate_media(reduced_motion='no-preference')

    # SG may be received even while the compressor is stopped; only SG pills
    # receive their signal border, never the ordinary active-device border.
    page.evaluate("qaApply('idle',true)")
    assert row.get_attribute('data-activity') == 'inactive'
    assert row.locator('[data-sg-stage=relay]').get_attribute('class') == 'sg-stage is-active'
    assert row.locator('[data-sg-stage=received]').get_attribute('class') == 'sg-stage is-active'
    assert row.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
    page.evaluate("qaApply('unknown',true,{power_w:5000})")
    assert row.get_attribute('data-activity') == 'unknown'
    assert '5 kW' in row.inner_text()

    # Missing supply 2 preserves the known part but never fabricates a total.
    page.evaluate("qaApply('active',false,{power_w:null,power_kind:'unknown',power_complete:false,power_supply2_w:null,power_supply2_valid:false})")
    assert 'Voeding 1: 1,72 kW · Voeding 2: onbekend' in row.inner_text()
    assert 'Totaal onbekend · deelmeting onvolledig' in row.inner_text()
    assert row.locator('.reason-power>b').inner_text() == 'Vermogen nog niet bekend'
    # A measured zero is not lost through truthiness.
    page.evaluate("qaApply('idle',false,{power_w:0,power_supply1_w:0})")
    assert row.locator('.reason-power>b').inner_text() == '0 W'

    # All three views keep a heatpump block and fit narrow and wide displays.
    page.evaluate("qaApply('active',true)")
    for view in ('overview', 'comfort', 'loads'):
        page.locator(f'solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value={view}]').click()
        panel = row if view == 'overview' else page.locator('solar-pilot-card >> .heatpump-sg')
        assert panel.count() == 1
        assert panel.locator('[data-sg-stage]').count() == 3
        assert panel.locator('[data-dhw-setting],[data-climate-setting]').count() == 0
        for width in (320, 390, 768, 1280):
            page.set_viewport_size({'width': width, 'height': 1000})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), (view, width)
            assert panel.evaluate('element=>element.scrollWidth<=element.clientWidth+1'), (view, width)
            page.screenshot(path=str(OUT / f'SolarPilot-warmtepomp-{view}65-{width}.png'), full_page=True)

    # Clock expiry changes the read-only fragment, without waiting for another
    # HA state update, closing open details or replacing a focused draft field.
    page.set_viewport_size({'width': 390, 'height': 844})
    page.evaluate("qaApply('active',true)")
    panel = page.locator('solar-pilot-card >> .heatpump-sg')
    panel.locator('details[data-ui-key="sg:loads:details"]>summary').click()
    panel.locator('details[data-ui-key="sg:loads:monitor"]>summary').click()
    page.evaluate('''() => {
      const draft=document.createElement('input');draft.dataset.qaDraft='true';draft.value='27';
      c._content.append(draft);draft.focus();window.qaDraft=draft;
      qaClockMs+=121000;c._refreshObservationDisplay();
    }''')
    assert panel.get_attribute('data-activity') == 'unknown'
    assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
    for stage in ('request', 'relay', 'received'):
        assert panel.locator(f'[data-sg-stage={stage}]').get_attribute('class') == 'sg-stage is-unknown'
    assert panel.locator('.reason-power>b').inner_text() == 'Vermogen nog niet bekend'
    assert '47,5 °C' not in panel.inner_text() and '50 °C' not in panel.inner_text()
    assert page.evaluate('qaDraft===c.shadowRoot.activeElement && qaDraft.value==="27"')
    assert panel.locator('details[data-ui-key="sg:loads:details"]').get_attribute('open') is not None
    assert panel.locator('details[data-ui-key="sg:loads:monitor"]').get_attribute('open') is not None
    assert panel.locator('[data-action=option_help][data-help-key=enabled]').count() == 1
    page.evaluate('qaDraft.remove()')

    # Expired local permission is unknown contact state, never an invented OFF;
    # independent fresh compressor evidence may still show native operation.
    page.evaluate('''() => {qaApply('active',true);c._last.attributes.sg_boost.lease_remaining_s=1;c._last.attributes.sg_boost.relay_valid_until=Date.now()/1000+1;
      c._render();qaClockMs+=2000;c._refreshObservationDisplay();}''')
    assert panel.get_attribute('data-activity') == 'active'
    assert panel.locator('[data-sg-stage=relay]').get_attribute('class') == 'sg-stage is-unknown'
    assert 'Open' not in panel.locator('[data-sg-stage=relay]').inner_text()
    # A new backend snapshot after lease expiry cannot refresh an old ON
    # readback into fresh permission merely by serializing it again.
    page.evaluate('''() => {qaApply('active',true);Object.assign(c._last.attributes.sg_boost,
      {lease_confirmed:false,lease_remaining_s:0,owner:'solarpilot',relay_valid_until:Date.now()/1000-1});c._render();}''')
    assert panel.get_attribute('data-activity') == 'active'
    assert panel.locator('[data-sg-stage=relay]').get_attribute('class') == 'sg-stage is-unknown'
    # A lost SolarPilot state suppresses all stale activity indications.
    page.evaluate("c._last.state='unavailable';c._refreshObservationDisplay()")
    assert panel.get_attribute('data-activity') == 'unknown'
    assert page.evaluate('qaCalls.length') == 0
    assert not errors, errors
    browser.close()
print('OK: independent native/SG evidence, all 3 views, 320/390/768/1280 layout, reduced motion, clock expiry, focused draft/details preservation, partial/zero readings; zero device calls. Fiction only.')
