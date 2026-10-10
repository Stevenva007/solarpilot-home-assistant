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
      window.qaMeter=(settings={})=>{
        const stamp=Date.now()/1000,o={power1:1720,power2:0,complete:true,native:'unknown',sg:true,threshold:200,...settings};
        const readings=[o.power1,o.power2],complete=o.complete&&readings.every(value=>typeof value==='number');
        const total=complete?readings[0]+readings[1]:null,active=complete?total>=o.threshold:readings.some(value=>typeof value==='number'&&value>=o.threshold);
        const contextStamp=o.contextStamp??stamp;
        const power_activity={state:complete?(active?'active':total===0?'off':'basis'):'partial',active,
          label:'Fictieve vermogensafleiding',note:'Afgeleid uit gemeten verbruik',threshold_w:o.threshold,
          evidence:o.function?'metered_power_and_context':'metered_power',observed_at:o.function?Math.min(stamp,contextStamp):stamp,
          stale_s:120,total_w:total,complete,function:o.function??null,context_observed_at:o.function?contextStamp:null,
          supplies:readings.map((watts,index)=>({number:index+1,role:o['role'+(index+1)]??'unknown',
            label:'Fictieve voeding '+(index+1),watts,valid:typeof watts==='number',
            state:typeof watts!=='number'?'unknown':watts===0?'off':watts>=o.threshold?'active':'basis',
            observed_at:o['stamp'+(index+1)]??(typeof watts==='number'?stamp:null)}))};
        qaApply(o.native,o.sg,{power_activity,power_w:total,power_kind:complete?'measured':'unknown',
          power_complete:complete,power_supply1_w:o.power1,power_supply2_w:o.power2,
          power_supply1_valid:typeof o.power1==='number',power_supply2_valid:typeof o.power2==='number'});
      };
      qaApply();
      const style=document.createElement('style');style.textContent=`body{max-width:1100px;background:#111;color:#eee}
        solar-pilot-card{--card-background-color:#1e1e1e;--ha-card-background:#1e1e1e;--secondary-background-color:#282828;
          --primary-text-color:#eee;--secondary-text-color:#aaa;--divider-color:#444;--primary-color:#009ec2}`;
      document.head.append(style);
    }''')
    row = page.locator('solar-pilot-card >> [data-reason-key="overview:sg"]')
    assert row.count() == 1
    assert 'Bevestigd actief of afgeleid uit verbruik' in page.locator('solar-pilot-card >> .activity-legend').inner_text()
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
    assert 'Werking onbekend' not in row.inner_text()
    assert row.locator('.row > .badge').count() == 0
    assert row.locator('.heatpump-operation,.heatpump-fan').count() == 0
    assert row.locator('[data-sg-stage]').count() == 3
    assert row.locator('[data-sg-stage=relay]').get_attribute('class') == 'sg-stage is-active'

    # Unknown, absent and expired operation observations do not insert another
    # large status placeholder. All views retain their measurements, SG rails,
    # reason and diagnostic details without inferring operation from watts.
    for view in ('overview', 'comfort', 'loads'):
        page.locator(f'solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value={view}]').click()
        panel = row if view == 'overview' else page.locator('solar-pilot-card >> .heatpump-sg')
        for observation in ('unknown', 'missing', 'expired'):
            page.evaluate('''kind => {
              const operation=kind==='missing'?null:kind==='expired'?{state:'active',label:'Compressor draait',
                evidence:'compressor_frequency',observed_at:Date.now()/1000-121,stale_s:120}:
                {state:'unknown',label:'Werking onbekend',evidence:'none',observed_at:Date.now()/1000,stale_s:120};
              qaApply('unknown',true,{operation,power_w:5000});
            }''', observation)
            assert panel.get_attribute('data-activity') == 'unknown'
            assert panel.locator('.heatpump-operation,.heatpump-fan').count() == 0
            assert 'Werking onbekend' not in panel.inner_text()
            assert 'Actuele compressor- of toestelactie ontbreekt' not in panel.inner_text()
            assert panel.locator('.reason-power>b').inner_text() == '5 kW'
            assert panel.locator('[data-sg-stage]').count() == 3
            assert panel.locator('[data-sg-stage=relay]').get_attribute('class') == 'sg-stage is-active'
            assert panel.locator('details').count() >= 1
            assert 'SG-contact actief; Panasonic-reactie afzonderlijk gemeld.' in panel.inner_text()
            assert page.evaluate('c._heatpumpActivity(c._ctx()).state') == 'unknown'
            assert page.evaluate('c._heatpumpActivity(c._ctx()).evidence') == 'none'
            if view == 'overview':
                assert panel.locator('.row > .badge').count() == 0
        # Positive evidence keeps its operation graphic and native status.
        for operation in ('active', 'idle'):
            page.evaluate('state=>qaApply(state,true)', operation)
            assert panel.locator('.heatpump-operation').count() == 1
            assert panel.get_attribute('data-activity') == ('active' if operation == 'active' else 'inactive')
            if view == 'overview':
                assert panel.locator('.row > .badge').count() == 1
    page.locator('solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value=overview]').click()

    # Metered activity is an explicitly separate display inference. It cannot
    # create compressor movement, received SG proof or device-control calls.
    for view in ('overview', 'comfort', 'loads'):
        page.locator(f'solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value={view}]').click()
        panel = row if view == 'overview' else page.locator('solar-pilot-card >> .heatpump-sg')
        page.evaluate('qaMeter()')
        assert panel.get_attribute('data-activity') == 'active'
        assert 'Warmtepomp werkt' in panel.inner_text()
        assert 'Afgeleid uit gemeten elektrisch verbruik' in panel.inner_text()
        assert 'Actief verbruik vanaf 200 W' in panel.inner_text()
        assert panel.locator('.heatpump-operation').get_attribute('data-evidence') == 'metered_power'
        assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
        assert panel.locator('[data-supply-number="2"]').inner_text().endswith('0 W\nGeen verbruik')
        assert 'Elektrische ondersteuning' not in panel.locator('[data-supply-number="2"]').inner_text()
        assert panel.locator('[data-sg-stage]').count() == 3
        for function,label in [('tapwater_heating','Sanitair water opwarmen'),('space_heating','Ruimte verwarmen'),('space_cooling','Ruimte koelen')]:
            page.evaluate('functionName=>qaMeter({function:functionName})', function)
            assert label in panel.inner_text()
            assert 'Afgeleid uit gemeten verbruik' in panel.inner_text()
            assert panel.locator('.heatpump-operation').get_attribute('data-evidence') == 'metered_power_and_context'
        # An expired context removes only the inferred function, retaining fresh
        # generic electrical activity from the independently current meters.
        page.evaluate("qaMeter({function:'tapwater_heating',contextStamp:Date.now()/1000-121})")
        assert 'Sanitair water opwarmen' not in panel.inner_text()
        assert 'Warmtepomp werkt' in panel.inner_text()
        assert panel.get_attribute('data-activity') == 'active'
        # Idle compressor plus high electrical support is reported honestly;
        # a static fan and explicit 0 Hz prevent a false compressor claim.
        page.evaluate("qaMeter({native:'idle',power1:0,power2:3700,role1:'main',role2:'heater'})")
        assert 'Compressor staat stil' in panel.inner_text()
        assert '0 Hz' in panel.inner_text()
        assert panel.locator('.heatpump-operation strong').inner_text().startswith('Warmtepomp werkt')
        assert panel.locator('.heatpump-operation').get_attribute('data-compressor-running') == 'false'
        assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
        assert 'regeling en pompen' in panel.locator('[data-supply-number="1"]').inner_text()
        assert 'Elektrische ondersteuning' in panel.locator('[data-supply-number="2"]').inner_text()
        for function,label in [('tapwater_heating','Sanitair water opwarmen'),('space_heating','Ruimte verwarmen'),('space_cooling','Ruimte koelen')]:
            page.evaluate('functionName=>qaMeter({native:"idle",power1:0,power2:3700,function:functionName})', function)
            assert panel.locator('.heatpump-operation strong').inner_text().startswith(label)
            assert 'Compressor staat stil' in panel.inner_text() and '0 Hz' in panel.inner_text()
            assert panel.locator('.heatpump-operation').get_attribute('data-compressor-running') == 'false'
            assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
        for watts,label in [(0,'Geen elektrisch verbruik'),(99,'Basisverbruik')]:
            page.evaluate('watts=>qaMeter({power1:watts,power2:0})', watts)
            assert panel.get_attribute('data-activity') == 'inactive'
            assert label in panel.inner_text()
        page.evaluate('qaMeter({power1:900,power2:null,complete:false})')
        assert 'Actief verbruik op voeding 1' in panel.inner_text()
        assert panel.locator('.reason-power>b').inner_text() == 'Vermogen nog niet bekend'
        assert panel.locator('[data-supply-number="2"]').inner_text().endswith('Geen actuele meting')
        for watts in (0,99):
            page.evaluate('watts=>qaMeter({power1:watts,power2:null,complete:false})', watts)
            assert panel.locator('.heatpump-operation').count() == 0
            assert panel.get_attribute('data-activity') == 'unknown'
        # Stale supporting supply cannot keep an old complete-total or function
        # inference active. The other current supply retains its measured value.
        page.evaluate("qaMeter({function:'tapwater_heating',power1:1000,power2:700,stamp1:Date.now()/1000-121})")
        assert panel.locator('.heatpump-operation').count() == 0
        assert panel.get_attribute('data-activity') == 'unknown'
        assert panel.locator('.reason-power>b').inner_text() == 'Vermogen nog niet bekend'
        assert panel.locator('[data-supply-number="1"]').inner_text().endswith('Geen actuele meting')
        assert '700 W' in panel.locator('[data-supply-number="2"]').inner_text()
        assert 'Sanitair water opwarmen' not in panel.inner_text()
        assert 'Werking onbekend' not in panel.inner_text()
    page.locator('solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value=overview]').click()

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
    assert panel.locator('.heatpump-operation,.heatpump-fan').count() == 0
    assert 'Werking onbekend' not in panel.inner_text()
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
    assert panel.locator('.heatpump-operation,.heatpump-fan').count() == 0
    assert 'Werking onbekend' not in panel.inner_text()
    assert page.evaluate('qaCalls.length') == 0
    assert not errors, errors
    browser.close()
print('OK: independent native/SG evidence, all 3 views, 320/390/768/1280 layout, reduced motion, clock expiry, focused draft/details preservation, partial/zero readings; zero device calls. Fiction only.')
