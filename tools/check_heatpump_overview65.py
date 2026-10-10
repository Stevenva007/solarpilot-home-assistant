"""Real browser check of independent warmtepomp/SG evidence, using fiction only.

Requires build_example.py and a Playwright Chromium. No network account,
Home Assistant instance, physical service call or hardware acceptance is used.
"""
import gzip
import json
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
        const stamp=Date.now()/1000,o={power1:1720,power2:0,complete:true,native:'unknown',sg:true,threshold:200,role1:'main',role2:'heater',...settings};
        const readings=[o.power1,o.power2],complete=o.complete&&readings.every(value=>typeof value==='number');
        const total=complete?readings[0]+readings[1]:null,active=complete?total>=o.threshold:readings.some(value=>typeof value==='number'&&value>=o.threshold);
        const contextStamp=o.contextStamp??stamp;
        const activity_kind=typeof o.power1==='number'&&o.power1>=o.threshold?
          (typeof o.power2==='number'&&o.power2>=o.threshold?'mixed':'main'):
          typeof o.power2==='number'&&o.power2>=o.threshold?'heater':'unknown';
        const functionName=activity_kind==='heater'?null:o.function??null;
        const power_activity={state:complete?(active?'active':total===0?'off':'basis'):'partial',active,
          label:'Fictieve vermogensafleiding',note:'Afgeleid uit gemeten verbruik',threshold_w:o.threshold,
          activity_kind,evidence:functionName?'metered_power_and_context':'metered_power',observed_at:functionName?Math.min(stamp,contextStamp):stamp,
          stale_s:120,total_w:total,complete,function:functionName,context_observed_at:functionName?contextStamp:null,
          function_kind:functionName?(o.functionKind??'native_action'):null,function_source:functionName?'aquarea_poll':null,
          supplies:readings.map((watts,index)=>({number:index+1,role:o['role'+(index+1)],role_assumed:true,
            label:'Fictieve voeding '+(index+1),watts,valid:typeof watts==='number',
            state:typeof watts!=='number'?'unknown':watts===0?'off':watts>=o.threshold?'active':'basis',
            observed_at:o['stamp'+(index+1)]??(typeof watts==='number'?stamp:null)}))};
        const labels={tapwater_heating:'Sanitair water opwarmen',space_heating:'Ruimte verwarmen',space_cooling:'Ruimte koelen'};
        const native_task=typeof o.nativeTask==='object'?o.nativeTask:o.nativeTask?{function:o.nativeTask,label:labels[o.nativeTask],
          note:'Panasonic meldt de actuele taak; dit bewijst geen compressor- of SG-effect.',source:'aquarea_poll',observed_at:o.taskStamp??stamp,stale_s:120}:null;
        const task_context=o.contextFunction?{function:o.contextFunction,label:o.contextLabel??(o.contextKind==='tank_route'?'Tankroute sanitair water':labels[o.contextFunction]),
          note:'Gekozen stand of route; een actuele actie is hiermee niet afzonderlijk bevestigd.',source:o.contextKind==='tank_route'?'aquarea_entity':'native_program',
          kind:o.contextKind??'selected_program',observed_at:o.contextStamp??stamp,stale_s:120}:null;
        qaApply(o.native,o.sg,{power_activity,native_task,task_context,defrost:o.defrost??null,power_w:total,power_kind:complete?'measured':'unknown',
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
    assert row.locator('[data-sg-stage=request]').count() == 0
    assert 'SolarPilot-aanvraag' in row.text_content() and 'Niet aangevraagd' in row.text_content()
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
    assert row.locator('[data-sg-stage]').count() == 2
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
            assert panel.locator('[data-sg-stage]').count() == 2
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
    # Absent response sources stay diagnostic; they never create an everyday
    # unknown-response row. Request is in Details and disagreement stays clear.
    for view in ('overview', 'comfort', 'loads'):
        page.locator(f'solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value={view}]').click()
        panel = row if view == 'overview' else page.locator('solar-pilot-card >> .heatpump-sg')
        page.evaluate("""() => {qaApply('active',true,{sg_status:'unknown',sg_status_confirmed:false,
          sg_status_observed_at:null,compressor_frequency_hz:null,compressor_frequency_observed_at:null});
          c._last.attributes.sg_boost.reason='SG-contact actief; Panasonic-reactie niet afzonderlijk bevestigd';c._render();}""")
        assert panel.locator('[data-sg-stage]').count() == 1
        assert panel.locator('[data-sg-stage=request],[data-sg-stage=received]').count() == 0
        assert panel.locator('[data-sg-stage=relay]').get_attribute('class') == 'sg-stage is-active'
        assert 'SolarPilot-aanvraag' in panel.text_content() and 'Aangevraagd' in panel.text_content()
        assert 'Panasonic-reactie niet afzonderlijk bevestigd' not in panel.text_content()
        assert 'compressorstatus onbekend' not in panel.text_content()
        page.evaluate("c._last.attributes.sg_boost.desired_on=false;c._render()")
        assert 'Geen zonneboost aangevraagd; het SG-contact is nog actief.' in panel.inner_text()
        page.evaluate("qaApply('active',true)")
        assert panel.locator('[data-sg-stage=received]').get_attribute('class') == 'sg-stage is-active'
    page.locator('solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value=overview]').click()

    # Metered activity is an explicitly separate display inference. It cannot
    # create compressor proof, received SG proof or device-control calls. The
    # fan may visualise fresh main-supply activity by the user's explicit choice.
    for view in ('overview', 'comfort', 'loads'):
        page.locator(f'solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value={view}]').click()
        panel = row if view == 'overview' else page.locator('solar-pilot-card >> .heatpump-sg')
        page.evaluate('qaMeter()')
        assert panel.get_attribute('data-activity') == 'active'
        assert 'Warmtepomp werkt' in panel.inner_text()
        assert 'Afgeleid uit gemeten elektrisch verbruik' in panel.inner_text()
        assert 'Actief verbruik vanaf 200 W' in panel.inner_text()
        assert panel.locator('.heatpump-operation').get_attribute('data-evidence') == 'metered_power'
        assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'sp-heatpump-turn'
        assert panel.locator('.heatpump-operation').get_attribute('data-compressor-running') == 'false'
        assert panel.locator('[data-supply-number="2"]').inner_text().endswith('0 W\nGeen verbruik')
        assert 'Elektrische ondersteuning' in panel.locator('[data-supply-number="2"]').inner_text()
        assert panel.locator('[data-sg-stage]').count() == 2
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
        assert panel.locator('.heatpump-operation strong').inner_text().startswith('Elektrische bijverwarming actief')
        assert panel.locator('.heatpump-operation').get_attribute('data-compressor-running') == 'false'
        assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
        assert 'regeling en pompen' in panel.locator('[data-supply-number="1"]').inner_text()
        assert 'Elektrische ondersteuning' in panel.locator('[data-supply-number="2"]').inner_text()
        for function,label in [('tapwater_heating','Sanitair water opwarmen'),('space_heating','Ruimte verwarmen'),('space_cooling','Ruimte koelen')]:
            page.evaluate('functionName=>qaMeter({native:"idle",power1:3700,power2:0,function:functionName})', function)
            assert panel.locator('.heatpump-operation strong').inner_text().startswith(label)
            assert 'Compressor staat stil' in panel.inner_text() and '0 Hz' in panel.inner_text()
            assert panel.locator('.heatpump-operation').get_attribute('data-compressor-running') == 'false'
            assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'sp-heatpump-turn'
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
        assert panel.locator('.heatpump-operation strong').inner_text().startswith('Actief verbruik op voeding 2')
        assert panel.get_attribute('data-activity') == 'active'
        assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
        assert panel.locator('.reason-power>b').inner_text() == 'Vermogen nog niet bekend'
        assert panel.locator('[data-supply-number="1"]').inner_text().endswith('Geen actuele meting')
        assert '700 W' in panel.locator('[data-supply-number="2"]').inner_text()
        assert 'Sanitair water opwarmen' not in panel.inner_text()
        assert 'Werking onbekend' not in panel.inner_text()

        # Task evidence and selected context are visible independently of power
        # coverage. A task report creates no electrical/compressor activity.
        for function,label in [('tapwater_heating','Sanitair water opwarmen'),('space_heating','Ruimte verwarmen'),('space_cooling','Ruimte koelen')]:
            page.evaluate('functionName=>qaMeter({power1:null,power2:null,complete:false,nativeTask:functionName})', function)
            assert panel.locator('[data-heatpump-task=native] strong').inner_text() == label
            assert 'Panasonic meldt' in panel.locator('[data-heatpump-task]').inner_text()
            assert panel.get_attribute('data-activity') == 'unknown'
            assert panel.locator('.heatpump-operation').count() == 0
            assert panel.locator('[data-heatpump-heater]').inner_text().find('Geen actuele meting') >= 0
            assert panel.locator('[data-sg-stage]').count() == 2
            page.evaluate('functionName=>qaMeter({native:"active",nativeTask:functionName})', function)
            assert panel.locator('.heatpump-operation strong').inner_text().startswith(label)
            assert panel.locator('.heatpump-operation').get_attribute('data-compressor-running') == 'true'

        # The screenshot's 2.17 kW main feed and 0 W heater shows useful task
        # context automatically, without presenting a selected route as action.
        page.evaluate("qaMeter({power1:2170,contextFunction:'tapwater_heating',contextKind:'tank_route'})")
        assert panel.locator('.heatpump-operation strong').inner_text().startswith('Warmtepomp werkt')
        assert panel.locator('[data-heatpump-task=context] strong').inner_text() == 'Tankroute sanitair water'
        assert 'geen afzonderlijke actiebevestiging' in panel.locator('[data-heatpump-task]').inner_text()
        assert panel.locator('[data-heatpump-heater]').get_attribute('data-heatpump-heater') == 'off'
        assert 'Geen verbruik' in panel.locator('[data-heatpump-heater]').inner_text()
        assert '0 W' in panel.locator('[data-heatpump-heater]').inner_text()
        assert 'aanname' in panel.locator('[data-heatpump-heater]').inner_text()
        page.evaluate("qaMeter({function:'tapwater_heating',functionKind:'tank_route',contextFunction:'tapwater_heating',contextKind:'tank_route'})")
        assert panel.locator('[data-heatpump-task=inferred] strong').inner_text() == 'Sanitair water opwarmen'
        assert 'tankroute' in panel.locator('[data-heatpump-task]').inner_text().lower()
        assert 'Afgeleid' in panel.locator('[data-heatpump-task]').inner_text()
        page.evaluate("qaMeter({contextFunction:'space_cooling',contextLabel:'Koelen gekozen'})")
        assert panel.locator('[data-heatpump-task=context] strong').inner_text() == 'Koelen gekozen'
        assert 'Gekozen stand' in panel.locator('[data-heatpump-task]').inner_text()
        assert 'Ruimte koelen' not in panel.locator('.heatpump-operation strong').inner_text()
        page.evaluate("qaMeter({nativeTask:'tapwater_heating',taskStamp:Date.now()/1000-121})")
        assert panel.locator('[data-heatpump-task=none]').count() == 1
        assert 'Sanitair water opwarmen' not in panel.locator('[data-heatpump-task]').inner_text()

        # On defrost, the separate native flag wins over heat-direction samples.
        page.evaluate("qaMeter({function:'space_heating',nativeTask:'space_heating',defrost:{state:'active',source:'aquarea_entity',observed_at:Date.now()/1000,stale_s:120}})")
        assert panel.locator('[data-heatpump-task=native] strong').inner_text() == 'Ontdooien'
        assert panel.locator('.heatpump-operation strong').inner_text().startswith('Ontdooien')
        assert 'Ruimte verwarmen' not in panel.locator('[data-heatpump-task]').inner_text()
        for special,label in [('inactive','Panasonic meldt rust'),('conflict','Panasonic-taak niet eenduidig')]:
            page.evaluate('''args=>qaMeter({function:'space_heating',nativeTask:{function:null,label:args[1],
              source:args[0]==='inactive'?'aquarea_poll':'none',[args[0]]:true,observed_at:Date.now()/1000,stale_s:120}})''', [special,label])
            assert panel.locator('[data-heatpump-task=native] strong').inner_text() == label
            assert panel.locator('.heatpump-operation strong').inner_text().startswith('Warmtepomp werkt')

        # Each heater meter ages independently and remains available in partial
        # coverage; watts alone cannot identify tank versus space support.
        for watts,state,label in [(0,'off','Geen verbruik'),(99,'basis','Basisverbruik'),(3700,'active','Bijverwarming aan · afgeleid')]:
            page.evaluate('watts=>qaMeter({power1:null,power2:watts,complete:false})', watts)
            heater = panel.locator('[data-heatpump-heater]')
            assert heater.get_attribute('data-heatpump-heater') == state
            assert label in heater.inner_text()
            assert 'geen aparte heater-terugmelding' in heater.inner_text()
            if watts >= 200:
                assert heater.locator('.heatpump-task-icon').evaluate('element=>getComputedStyle(element).animationName') == 'sp-device-activity'
                assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
            else:
                assert heater.locator('.heatpump-task-icon').evaluate('element=>getComputedStyle(element).animationName') == 'none'
        page.evaluate('qaMeter({power2:3700,stamp2:Date.now()/1000-121})')
        assert panel.locator('[data-heatpump-heater]').get_attribute('data-heatpump-heater') == 'unknown'
        assert 'Geen actuele meting' in panel.locator('[data-heatpump-heater]').inner_text()
        assert 'Actief verbruik op voeding 1' in panel.locator('.heatpump-operation strong').inner_text()
        assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'sp-heatpump-turn'
        assert panel.locator('.reason-power>b').inner_text() == 'Vermogen nog niet bekend'
        page.evaluate('''() => {qaMeter({power1:58,power2:3000,nativeTask:'tapwater_heating'});
          Object.assign(c._last.attributes.panasonic,{compressor_frequency_hz:null,compressor_frequency_observed_at:null,
            operation:{state:'active',label:'Panasonic meldt verwarmactie',evidence:'native_action',observed_at:Date.now()/1000,stale_s:120}});c._render();}''')
        assert panel.locator('.heatpump-operation').get_attribute('data-compressor-running') == 'false'
        assert panel.locator('.heatpump-operation').get_attribute('data-fan-active') == 'false'
        assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
        assert panel.locator('[data-heatpump-heater] .heatpump-task-icon').evaluate('element=>getComputedStyle(element).animationName') == 'sp-device-activity'

        # Explicit 0 Hz remains a stopped-compressor report. Animation of fresh
        # main-feed activity is clearly electrical inference, by user request.
        page.evaluate("qaMeter({native:'idle',power1:2170,power2:900})")
        assert 'Compressor staat stil' in panel.inner_text() and '0 Hz' in panel.inner_text()
        assert panel.locator('.heatpump-operation').get_attribute('data-compressor-running') == 'false'
        assert panel.locator('.heatpump-operation').get_attribute('data-fan-active') == 'true'
        assert 'dit bevestigt geen draaiende compressor' in panel.inner_text()
        page.emulate_media(reduced_motion='reduce')
        assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
        assert panel.locator('[data-heatpump-heater] .heatpump-task-icon').evaluate('element=>getComputedStyle(element).animationName') == 'none'
        page.emulate_media(reduced_motion='no-preference')
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
        assert panel.locator('[data-sg-stage]').count() == 2
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
    assert panel.locator('[data-sg-stage=request],[data-sg-stage=received]').count() == 0
    assert panel.locator('[data-sg-stage=relay]').get_attribute('class') == 'sg-stage is-unknown'
    assert panel.locator('.reason-power>b').inner_text() == 'Vermogen nog niet bekend'
    assert '47,5 °C' not in panel.inner_text() and '50 °C' not in panel.inner_text()
    assert page.evaluate('qaDraft===c.shadowRoot.activeElement && qaDraft.value==="27"')
    assert panel.locator('details[data-ui-key="sg:loads:details"]').get_attribute('open') is not None
    assert panel.locator('details[data-ui-key="sg:loads:monitor"]').get_attribute('open') is not None
    assert panel.locator('[data-action=option_help][data-help-key=enabled]').count() == 1
    page.evaluate('qaDraft.remove()')

    # Existing active ordinary loads, an external active programme and the
    # read-only Wallbox also animate, never creating an appliance command.
    page.evaluate('''() => {qaApply('active',true);const a=c._last.attributes;
      a.devices.push({id:'example_external_dishwasher',name:'Fictieve externe afwasmachine',kind:'dishwasher',
        available:true,on:true,owned:false,power_w:700,mode:'auto',dishwasher:{phase:'Running'}});
      Object.assign(a.wallbox,{enabled:true,activity_known:true,power_w:3000});c._render();}''')
    ordinary = page.locator('solar-pilot-card >> .device.on:not(.dishwasher) .icon').first
    external = page.locator('solar-pilot-card >> .device.dishwasher.on .icon').first
    wallbox = page.locator('solar-pilot-card >> .wallbox-device.on .icon')
    for icon in (ordinary,external,wallbox):
        assert icon.evaluate('element=>getComputedStyle(element).animationName') == 'sp-device-activity'
    page.emulate_media(reduced_motion='reduce')
    for icon in (ordinary,external,wallbox):
        assert icon.evaluate('element=>getComputedStyle(element).animationName') == 'none'
    page.emulate_media(reduced_motion='no-preference')
    page.evaluate("c._last.state='unavailable';c._refreshObservationDisplay()")
    for icon in (ordinary,external,wallbox):
        assert icon.evaluate('element=>getComputedStyle(element).animationName') == 'none'
    page.evaluate("qaApply('active',true)")

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

    # The analysis flow uses only explicitly requested read/export/report
    # operations. Its fixtures never contact a server or control an appliance.
    fictional_export = {"schema": "solarpilot.analysis_export", "fiction": True}
    export_bytes = list(gzip.compress(json.dumps(fictional_export).encode()))
    page.evaluate('''bytes => {
      qaApply('active',true);window.qaWS=[];window.qaFileReads=0;window.qaUnsafeExecuted=false;
      window.qaTemplate={schema:'solarpilot.analysis_feedback',schema_version:1,
        source_export:{export_id:'export_'+'a'.repeat(32),export_sha256:'b'.repeat(64),
          release:'1.0.0-beta.67',created_at:'2026-10-10T12:00:00Z'},
        analyzed_at:'2026-10-10T13:00:00Z',summary:'Fictief antwoord',question_answers:[],recommendations:[],limitations:[]};
      window.qaFeedback={report:null,association:{state:'unverified',reason:'Fictief voorbeeld'},
        current_release:'1.0.0-beta.67',source_release_matches_current:true,logic_updates:[],question_review:[]};
      const attributes=c._last.attributes;
      attributes.learning_insights={open_questions:1,findings:[{id:'fictional-finding',revision:'fixture',
        title:'Fictieve bevinding voor analyse',message:'Controleer de beschikbare meetpunten.'}]};
      c.hass={...c._hass,user:{id:'fictional-admin',is_admin:true},callWS:async message=>{
        qaWS.push(structuredClone(message));
        if(message.type==='solar_pilot/analysis_export')return {filename:'Fictieve-SolarPilot-analyse.json.gz',
          download_url:'/api/solar_pilot/analysis/fictional67',source_export:qaTemplate.source_export,
          feedback_template:qaTemplate,quality:{sample_count:2,requested_hours:168,collection_enabled:true}};
        if(message.type==='solar_pilot/analysis_feedback'){
          if(message.action==='import')qaFeedback={...qaFeedback,report:JSON.parse(message.content),
            association:{state:'unverified',reason:'Dit fictieve rapport is niet lokaal herkend.'},
            source_release_matches_current:false};
          if(message.action==='remove')qaFeedback={...qaFeedback,report:null};
          return structuredClone(qaFeedback);
        }
        if(message.type==='solar_pilot/learning'&&message.operation==='read')return {
          questions:[{title:'Oude interactieve vraag',choices:[{id:'apply',label:'Niet tonen'}]}],models:[]};
        throw new Error('Geen andere bewerkingen in deze test');
      },fetchWithAuth:async(path,options)=>{
        qaWS.push({path,method:options.method});
        return new Response(new Uint8Array(bytes),{status:200,headers:{'Content-Type':'application/gzip'}});
      }};c._view='overview';c._render();
    }''', export_bytes)
    assert 'Analyse nodig' in page.locator('solar-pilot-card >> .analysis-needed').inner_text()
    assert 'Leren & vragen' not in page.locator('solar-pilot-card').inner_text()
    with page.expect_download() as download_info:
        page.locator('solar-pilot-card >> .analysis-needed [data-action=analysis_download]').click()
    download = download_info.value
    assert download.suggested_filename == 'Fictieve-SolarPilot-analyse.json.gz'
    assert json.loads(gzip.decompress(Path(download.path()).read_bytes())) == fictional_export
    assert page.evaluate("qaWS.filter(x=>x.type==='solar_pilot/analysis_export')") == [
        {'type': 'solar_pilot/analysis_export', 'config_entry_id': 'offline-example',
         'hours': 168, 'include_names': False, 'download': True}]
    analysis = page.locator('solar-pilot-card >> solar-pilot-analysis-dialog-1-0-0-beta-67')
    assert not analysis.locator('.hours').is_visible() and not analysis.locator('.names').is_visible()
    assert analysis.locator('.template').is_visible()
    with page.expect_download() as template_info:
        analysis.locator('.template').click()
    assert json.loads(Path(template_info.value.path()).read_text()) == page.evaluate('qaTemplate')
    analysis.locator('.close').click()

    page.locator('solar-pilot-card >> .footer [data-action=learning_hub]').click()
    quality = page.locator('solar-pilot-card >> solar-pilot-learning-dialog-1-0-0-beta-67')
    page.wait_for_function('!c._learningDialog._busy')
    assert quality.locator('h2').inner_text() == 'Meetkwaliteit'
    assert 'Oude interactieve vraag' not in quality.locator('.body').inner_text()
    assert quality.locator('[data-question],[data-policy],[data-action=answer],[data-action=policy]').count() == 0
    assert page.evaluate("qaWS.filter(x=>x.type==='solar_pilot/learning').every(x=>x.operation==='read')")
    quality.locator('.close').click()

    page.locator('solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value=export]').click()
    page.wait_for_function("!c._analysisFeedbackBusy && c._analysisFeedbackLoadedEntry==='offline-example'")
    assert 'Fictieve bevinding voor analyse' in page.locator('solar-pilot-card >> .analysis-export').inner_text()
    assert page.locator('solar-pilot-card >> [data-question],[data-policy],[data-action=answer],[data-action=policy]').count() == 0
    page.evaluate('''async() => {await c._importAnalysisFeedback({size:1048577,text:async()=>{
      qaFileReads++;return '{}';}});}''')
    assert page.evaluate('qaFileReads') == 0
    assert 'maximaal 1 MiB' in page.locator('solar-pilot-card >> .analysis-feedback .error').inner_text()
    assert not page.evaluate("qaWS.some(x=>x.type==='solar_pilot/analysis_feedback'&&x.action==='import')")
    upload = page.locator('solar-pilot-card >> [data-analysis-feedback-file]')
    upload.set_input_files({'name': 'Fictief-ongeldig.json', 'mimeType': 'application/json', 'buffer': b'{broken'})
    page.wait_for_function('!c._analysisFeedbackReading')
    assert 'geen geldige JSON' in page.locator('solar-pilot-card >> .analysis-feedback .error').inner_text()
    unsafe_text = '<img src=x onerror="qaUnsafeExecuted=true"><script>qaUnsafeExecuted=true</script><a href="javascript:evil()">x</a>'
    feedback = page.evaluate('structuredClone(qaTemplate)')
    feedback.update(summary=unsafe_text, limitations=[unsafe_text],
                    question_answers=[{'question_id': 'fictional-finding', 'revision': 'fixture',
                                       'answer': unsafe_text, 'outcome': 'needs_more_data'}],
                    recommendations=[{'category': 'logic_update', 'proposal_id': 'fictitious-proposal',
                                      'text': unsafe_text, 'confidence': 'low', 'evidence': [unsafe_text],
                                      'limitations': [unsafe_text]}])
    upload.set_input_files({'name': 'Fictief-advies.json', 'mimeType': 'application/json',
                           'buffer': json.dumps(feedback).encode()})
    page.wait_for_function('!c._analysisFeedbackReading && !c._analysisFeedbackBusy && !!c._analysisFeedbackReport?.report')
    report = page.locator('solar-pilot-card >> .analysis-feedback-report')
    assert report.locator('img,script,a,input,button,select').count() == 0
    assert unsafe_text in report.inner_text()
    assert not page.evaluate('qaUnsafeExecuted')
    assert report.locator('[data-analysis-association]').get_attribute('data-analysis-association') == 'unverified'
    assert 'andere SolarPilot-versie' in report.inner_text()
    assert report.locator('[data-logic-update-status]').get_attribute('data-logic-update-status') == 'untracked'
    page.locator('solar-pilot-card >> [data-action=analysis_feedback_reload]').click()
    page.wait_for_function('!c._analysisFeedbackBusy')
    assert unsafe_text in report.inner_text()
    for width in (320, 390, 768):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), ('analysis', width)
        page.screenshot(path=str(OUT / f'SolarPilot-analyse67-{width}.png'), full_page=True)
    page.locator('solar-pilot-card >> [data-action=analysis_feedback_remove]').click()
    page.wait_for_function('!c._analysisFeedbackBusy && !c._analysisFeedbackReport?.report')
    assert report.count() == 0
    assert page.locator('solar-pilot-card >> [data-action=analysis_feedback_remove]').count() == 0
    page.evaluate("c.hass={...c._hass,user:{id:'fictional-viewer',is_admin:false}};window.qaWSBeforeViewer=qaWS.length")
    for action in ('analysis_download', 'analysis_feedback_upload', 'analysis_feedback_reload'):
        assert page.locator(f'solar-pilot-card >> .analysis-export [data-action={action}]').is_disabled()
    page.evaluate('''async() => {await c._analysisFeedbackAction('remove');
      await c._importAnalysisFeedback({size:100,text:async()=>{qaFileReads++;return '{}';}});}''')
    assert page.evaluate('qaWS.length===qaWSBeforeViewer && qaFileReads===0')
    assert page.evaluate('qaCalls.length') == 0
    assert not errors, errors
    browser.close()
print('OK: independent native/compact SG evidence, 3 views, responsive layout, reduced motion, clock expiry, draft/details preservation, partial/zero readings; one-click analysis/template, bounded escaped feedback, reload/removal/admin checks; zero device calls. Fiction only.')
