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


def prominent_text(panel):
    """Read the compact content independently of expanded technical details."""
    return panel.evaluate("""element => {
        const copy=element.cloneNode(true);
        copy.querySelectorAll('details').forEach(details=>details.remove());
        return copy.textContent;
    }""")


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
          function_kind:functionName?(o.functionKind??'native_action'):null,
          function_source:functionName?(o.functionSource??(o.functionKind==='tank_route'?'aquarea_entity':o.functionKind==='selected_program'?'native_program':'aquarea_poll')):null,
          supplies:readings.map((watts,index)=>({number:index+1,role:o['role'+(index+1)],role_assumed:true,
            label:'Fictieve voeding '+(index+1),watts,valid:typeof watts==='number',
            state:typeof watts!=='number'?'unknown':watts===0?'off':watts>=o.threshold?'active':'basis',
            observed_at:o['stamp'+(index+1)]??(typeof watts==='number'?stamp:null)}))};
        const labels={tapwater_heating:'Boiler opwarmen',space_heating:'Verwarmen',space_cooling:'Koelen'};
        const native_task=typeof o.nativeTask==='object'?o.nativeTask:o.nativeTask?{function:o.nativeTask,label:labels[o.nativeTask],
          note:'Panasonic meldt de actuele taak; dit bewijst geen compressor- of SG-effect.',source:'aquarea_poll',observed_at:o.taskStamp??stamp,stale_s:120}:null;
        const task_context=o.contextFunction?{function:o.contextFunction,label:o.contextLabel??(o.contextKind==='tank_route'?'Tankroute sanitair water':labels[o.contextFunction]),
          note:'Gekozen stand of route; een actuele actie is hiermee niet afzonderlijk bevestigd.',source:o.contextSource??(o.contextKind==='tank_route'?'aquarea_entity':'native_program'),
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
    assert '33 Hz' in row.locator('[data-heatpump-provenance]').text_content() and '0 W' in row.inner_text()
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
        assert 'Afgeleid' in panel.locator('.heatpump-operation').inner_text()
        assert 'Afgeleid uit gemeten elektrisch verbruik' in panel.locator('[data-heatpump-provenance]').text_content()
        assert 'Actief verbruik vanaf' in panel.locator('[data-heatpump-provenance]').text_content()
        assert '200 W' in panel.locator('[data-heatpump-provenance]').text_content()
        assert panel.locator('.heatpump-operation').get_attribute('data-evidence') == 'metered_power'
        assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'sp-heatpump-turn'
        assert panel.locator('.heatpump-operation').get_attribute('data-compressor-running') == 'false'
        assert panel.locator('[data-supply-number="2"]').inner_text().endswith('0 W\nGeen verbruik')
        assert 'elektrische bijverwarming' in panel.locator('[data-supply-number="2"]').inner_text().lower()
        assert panel.locator('[data-sg-stage]').count() == 2
        for function,label in [('tapwater_heating','Boiler opwarmen'),('space_heating','Verwarmen'),('space_cooling','Koelen')]:
            page.evaluate('functionName=>qaMeter({function:functionName})', function)
            assert label in panel.inner_text()
            assert 'Afgeleid' in panel.locator('.heatpump-operation').inner_text()
            assert 'Afgeleid uit gemeten verbruik' in panel.locator('[data-heatpump-provenance]').text_content()
            assert panel.locator('.heatpump-operation').get_attribute('data-evidence') == 'metered_power_and_context'
        # An expired context removes only the inferred function, retaining fresh
        # generic electrical activity from the independently current meters.
        page.evaluate("qaMeter({function:'tapwater_heating',contextStamp:Date.now()/1000-121})")
        assert 'Boiler opwarmen' not in panel.inner_text()
        assert 'Warmtepomp werkt' in panel.inner_text()
        assert panel.get_attribute('data-activity') == 'active'
        # Idle compressor plus high electrical support is reported honestly;
        # a static fan and explicit 0 Hz prevent a false compressor claim.
        page.evaluate("qaMeter({native:'idle',power1:0,power2:3700,role1:'main',role2:'heater'})")
        assert 'Compressor staat stil' in panel.locator('[data-heatpump-provenance]').text_content()
        assert '0 Hz' in panel.locator('[data-heatpump-provenance]').text_content()
        assert panel.locator('.heatpump-operation strong').inner_text().startswith('Elektrische bijverwarming actief')
        assert panel.locator('.heatpump-operation').get_attribute('data-compressor-running') == 'false'
        assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
        assert 'regeling en pompen' in panel.locator('[data-heatpump-provenance]').text_content()
        assert 'elektrische bijverwarming' in panel.locator('[data-supply-number="2"]').inner_text().lower()
        for function,label in [('tapwater_heating','Boiler opwarmen'),('space_heating','Verwarmen'),('space_cooling','Koelen')]:
            page.evaluate('functionName=>qaMeter({native:"idle",power1:3700,power2:0,function:functionName})', function)
            assert panel.locator('.heatpump-operation strong').inner_text().startswith(label)
            assert 'Compressor staat stil' in panel.locator('[data-heatpump-provenance]').text_content()
            assert '0 Hz' in panel.locator('[data-heatpump-provenance]').text_content()
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
        assert 'Boiler opwarmen' not in panel.inner_text()
        assert 'Werking onbekend' not in panel.inner_text()

        # Actual task evidence stays visible independently of power coverage;
        # selected context belongs in Details and supplies no activity proof.
        for function,label in [('tapwater_heating','Boiler opwarmen'),('space_heating','Verwarmen'),('space_cooling','Koelen')]:
            page.evaluate('functionName=>qaMeter({power1:null,power2:null,complete:false,nativeTask:functionName})', function)
            assert panel.locator('[data-heatpump-task=native] strong').inner_text() == label
            assert 'Panasonic meldt' in panel.locator('[data-heatpump-provenance]').text_content()
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
        assert panel.locator('[data-heatpump-task=activity] strong').inner_text() == 'Warmtepomp werkt'
        assert 'Tankroute sanitair water' in panel.locator('[data-heatpump-provenance]').text_content()
        assert 'actuele actie is hiermee niet afzonderlijk bevestigd' in panel.locator('[data-heatpump-provenance]').text_content()
        assert panel.locator('[data-heatpump-heater]').get_attribute('data-heatpump-heater') == 'off'
        assert 'Geen verbruik' in panel.locator('[data-heatpump-heater]').inner_text()
        assert '0 W' in panel.locator('[data-heatpump-heater]').inner_text()
        assert 'aanname' in panel.locator('[data-heatpump-provenance]').text_content()
        page.evaluate("qaMeter({function:'tapwater_heating',functionKind:'tank_route',contextFunction:'tapwater_heating',contextKind:'tank_route'})")
        assert panel.locator('[data-heatpump-task=inferred] strong').inner_text() == 'Boiler opwarmen'
        assert 'tankroute' in panel.locator('[data-heatpump-provenance]').text_content().lower()
        assert panel.locator('.heatpump-operation small').inner_text() == 'Afgeleid'
        page.evaluate("qaMeter({contextFunction:'space_cooling',contextLabel:'Koelen gekozen'})")
        assert panel.locator('[data-heatpump-task=activity] strong').inner_text() == 'Warmtepomp werkt'
        assert 'Koelen gekozen' in panel.locator('[data-heatpump-provenance]').text_content()
        assert 'Koelen' not in panel.locator('.heatpump-operation strong').inner_text()
        page.evaluate("qaMeter({nativeTask:'tapwater_heating',taskStamp:Date.now()/1000-121})")
        assert panel.locator('[data-heatpump-task=activity] strong').inner_text() == 'Warmtepomp werkt'
        assert 'Boiler opwarmen' not in panel.locator('[data-heatpump-task]').inner_text()

        # On defrost, the separate native flag wins over heat-direction samples.
        page.evaluate("qaMeter({function:'space_heating',nativeTask:'space_heating',defrost:{state:'active',source:'aquarea_entity',observed_at:Date.now()/1000,stale_s:120}})")
        assert panel.locator('[data-heatpump-task=native] strong').inner_text() == 'Ontdooien'
        assert panel.locator('.heatpump-operation strong').inner_text().startswith('Ontdooien')
        assert 'Verwarmen' not in panel.locator('[data-heatpump-task]').inner_text()
        for special,label in [('inactive','Panasonic meldt rust'),('conflict','Panasonic-taak niet eenduidig')]:
            page.evaluate('''args=>qaMeter({function:'space_heating',nativeTask:{function:null,label:args[1],
              source:args[0]==='inactive'?'aquarea_poll':'none',[args[0]]:true,observed_at:Date.now()/1000,stale_s:120}})''', [special,label])
            assert panel.locator('[data-heatpump-task=activity] strong').inner_text() == 'Warmtepomp werkt'
            assert label in panel.locator('[data-heatpump-provenance]').text_content()
            assert panel.locator('.heatpump-operation strong').inner_text().startswith('Warmtepomp werkt')

        # Each heater meter ages independently and remains available in partial
        # coverage; watts alone cannot identify tank versus space support.
        for watts,state,label in [(0,'off','Geen verbruik'),(99,'basis','Basisverbruik'),(3700,'active','Aan')]:
            page.evaluate('watts=>qaMeter({power1:null,power2:watts,complete:false})', watts)
            heater = panel.locator('[data-heatpump-heater]')
            assert heater.get_attribute('data-heatpump-heater') == state
            assert label in heater.inner_text()
            assert 'Panasonic stuurt haar zelfstandig' in panel.locator('[data-heatpump-provenance]').text_content()
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
        assert 'Compressor staat stil' in panel.locator('[data-heatpump-provenance]').text_content()
        assert '0 Hz' in panel.locator('[data-heatpump-provenance]').text_content()
        assert panel.locator('.heatpump-operation').get_attribute('data-compressor-running') == 'false'
        assert panel.locator('.heatpump-operation').get_attribute('data-fan-active') == 'true'
        assert 'bevestigen geen draaiende compressor' in panel.locator('[data-heatpump-provenance]').text_content()
        page.emulate_media(reduced_motion='reduce')
        assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
        assert panel.locator('[data-heatpump-heater] .heatpump-task-icon').evaluate('element=>getComputedStyle(element).animationName') == 'none'
        page.emulate_media(reduced_motion='no-preference')
    page.locator('solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value=overview]').click()

    # Reproduce the user's 1.36 kW main feed / 0 W heater screenshot. A fresh
    # typed IDLE report is retained in Details while the current main meter and
    # matching selected context supply a qualified, consistent dynamic task.
    tasks = [('space_heating', 'Verwarmen', 'selected_program', 'native_program'),
             ('space_cooling', 'Koelen', 'selected_program', 'native_program'),
             ('tapwater_heating', 'Boiler opwarmen', 'tank_route', 'aquarea_entity')]
    for view in ('overview', 'comfort', 'loads'):
        page.locator(f'solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value={view}]').click()
        panel = row if view == 'overview' else page.locator('solar-pilot-card >> .heatpump-sg')
        for function, label, kind, source in tasks:
            page.evaluate('''args => qaMeter({power1:1360,power2:0,native:'idle',
              function:args[0],functionKind:args[2],functionSource:args[3],
              contextFunction:args[0],contextKind:args[2],contextSource:args[3],contextLabel:args[1]+' gekozen',
              nativeTask:{function:null,label:'Panasonic meldt rust',source:'aquarea_poll',
                inactive:true,inactive_action:'idle',observed_at:Date.now()/1000,stale_s:120}})''',
                          [function, label, kind, source])
            assert panel.locator('.heatpump-operation strong').inner_text() == label
            assert panel.locator('[data-heatpump-task=inferred] strong').inner_text() == label
            assert panel.locator('.heatpump-operation small').inner_text() == 'Afgeleid'
            assert panel.get_attribute('data-activity') == 'active'
            assert panel.locator('.heatpump-operation').get_attribute('data-compressor-running') == 'false'
            assert panel.locator('.heatpump-operation').get_attribute('data-fan-active') == 'true'
            assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'sp-heatpump-turn'
            assert '1,36 kW' in panel.locator('[data-supply-number="1"]').inner_text()
            assert '0 W' in panel.locator('[data-supply-number="2"]').inner_text()
            if view == 'overview':
                assert panel.locator('.row > .badge').inner_text() == label
            assert page.evaluate('c._ctx().panasonic.native_task.inactive_action') == 'idle'
            technical = panel.locator('[data-heatpump-provenance]').text_content()
            assert 'Panasonic meldt rust' in technical and label + ' gekozen' in technical
            assert '0 Hz' in technical and 'Actief verbruik vanaf' in technical
            compact = prominent_text(panel)
            for excluded in ('Panasonic meldt rust', ' gekozen', 'Actief verbruik vanaf',
                             'compressorbedrijf en SG-reactie', 'Panasonic-voedingsprofiel',
                             'bevestigen geen draaiende compressor', '0 Hz'):
                assert excluded not in compact, (view, function, excluded)
        for width in (320, 390, 768, 1280):
            page.set_viewport_size({'width': width, 'height': 1000})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), ('dynamic-task', view, width)
            assert panel.evaluate('element=>element.scrollWidth<=element.clientWidth+1'), ('dynamic-task', view, width)
            assert panel.locator('.heatpump-supply>span:last-child').evaluate_all('''values=>values.every(value=>{
              const style=getComputedStyle(value);
              return style.wordBreak==='normal'&&style.overflowWrap==='normal'&&value.scrollWidth<=value.clientWidth+1;
            })'''), ('supply-value-wrapping', view, width)
            page.screenshot(path=str(OUT / f'SolarPilot-warmtepomp-taak68-{view}-{width}.png'), full_page=True)
        # A new stale or incompatible context cannot retain the cached inferred
        # function; current meter activity and animation remain independent.
        page.evaluate('c._last.attributes.panasonic.task_context.observed_at=Date.now()/1000-121;c._render()')
        assert panel.locator('.heatpump-operation strong').inner_text() == 'Warmtepomp werkt'
        assert panel.locator('[data-heatpump-task=inferred]').count() == 0
        assert panel.locator('.heatpump-operation').get_attribute('data-fan-active') == 'true'
        page.emulate_media(reduced_motion='reduce')
        assert panel.locator('.heatpump-fan').evaluate('element=>getComputedStyle(element).animationName') == 'none'
        page.emulate_media(reduced_motion='no-preference')
        # Unknown meter copy may wrap at spaces but must not overflow, and a
        # known 0 W / Geen verbruik must retain normal complete-word wrapping.
        page.set_viewport_size({'width': 320, 'height': 1000})
        page.evaluate('qaMeter({power1:1360,power2:null,complete:false})')
        assert panel.locator('[data-supply-number="2"]>span:last-child').inner_text() == 'Geen actuele meting'
        assert panel.locator('.heatpump-supply>span:last-child').evaluate_all('''values=>values.every(value=>{
          const style=getComputedStyle(value);
          return style.wordBreak==='normal'&&style.overflowWrap==='normal'&&value.scrollWidth<=value.clientWidth+1;
        })'''), ('missing-supply-wrapping', view)
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), ('missing-supply', view)
        assert panel.evaluate('element=>element.scrollWidth<=element.clientWidth+1'), ('missing-supply', view)
    page.locator('solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value=overview]').click()

    # beta.69 keeps main-operation OFF separate from the tank's independent
    # ON/WATER report from the same provider poll. Fictional complete meters
    # support only a read-only tank-route inference, never SG/control proof.
    page.evaluate('''() => {
      window.qaIndependentTank=()=>{
        const stamp=Date.now()/1000;
        qaMeter({native:'unknown',sg:false,power1:1840,power2:0,
          function:'tapwater_heating',functionKind:'tank_route',functionSource:'aquarea_entity',
          contextFunction:'tapwater_heating',contextKind:'tank_route',contextSource:'aquarea_entity',
          contextLabel:'Panasonic meldt tankroute',nativeTask:{function:null,
            label:'Panasonic meldt ruimtebedrijf uit',source:'aquarea_poll',observed_at:stamp,stale_s:120,
            inactive:true,inactive_action:'off',inactive_scope:'space_circuit',
            independent_tank_on:true,verified_global_off:false,
            raw_evidence:[{entity_id:'climate.fictional_room',source:'aquarea_poll',raw_action:'OFF',
              action:'off',operation_status:'OFF',has_tank:true,tank_operation_status:'ON',direction:'WATER',
              observed_at:stamp,inactive_scope:'space_circuit'}],
            inactive_zones:[{entity_id:'climate.fictional_room',action:'off',observed_at:stamp,scope:'zone'}]}});
      };
    }''')
    for view in ('overview', 'comfort', 'loads'):
        page.locator(f'solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value={view}]').click()
        panel = row if view == 'overview' else page.locator('solar-pilot-card >> .heatpump-sg')
        for width in (320, 390, 768, 1280):
            page.set_viewport_size({'width': width, 'height': 1000})
            page.evaluate('qaIndependentTank()')
            assert panel.locator('[data-heatpump-task=inferred] strong').inner_text() == 'Boiler opwarmen'
            assert panel.locator('.heatpump-operation strong').inner_text() == 'Boiler opwarmen'
            assert panel.locator('.heatpump-operation small').inner_text() == 'Afgeleid'
            assert panel.locator('.heatpump-operation').get_attribute('data-compressor-running') == 'false'
            assert panel.locator('[data-sg-stage=relay]').inner_text().endswith('Open')
            technical = panel.locator('[data-heatpump-provenance]').text_content()
            assert 'OFF' in technical and 'tank afzonderlijk actief' in technical
            assert 'OFF' not in prominent_text(panel)
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), ('independent-tank69', view, width)
            assert panel.evaluate('element=>element.scrollWidth<=element.clientWidth+1'), ('independent-tank69', view, width)
            page.screenshot(path=str(OUT / f'SolarPilot-warmtepomp-tank69-{view}-{width}.png'), full_page=True)
        # Even a cached inference cannot override global OFF, unknown scope,
        # or a missing independent ON report. Keep its fresh measured uptake.
        for change in ({'inactive_scope': 'global', 'verified_global_off': True,
                        'independent_tank_on': False},
                       {'inactive_scope': 'unknown'}, {'independent_tank_on': False},
                       {'verified_global_off': True}):
            page.evaluate('change=>{qaIndependentTank();Object.assign(c._last.attributes.panasonic.native_task,change);c._render();}', change)
            assert panel.locator('[data-heatpump-task=inferred]').count() == 0
            assert panel.locator('.heatpump-operation strong').inner_text() == 'Warmtepomp werkt'
            assert 'OFF' in panel.locator('[data-heatpump-provenance]').text_content()
        page.evaluate('''() => {qaIndependentTank();
          c._last.attributes.panasonic.task_context.observed_at=Date.now()/1000-121;c._render();}''')
        assert panel.locator('[data-heatpump-task=inferred]').count() == 0
        assert panel.locator('.heatpump-operation strong').inner_text() == 'Warmtepomp werkt'

    # A theoretical remaining quarter budget is not physical room. Already
    # measured HP solar, real residual export and hard electrical room stay
    # distinct in Details, and all three views show the exact same values.
    page.evaluate('''() => {window.qaElectrical=()=>{
      qaApply('unknown',false);const a=c._last.attributes,stamp=Date.now()/1000;
      a.ems={...(a.ems||{}),electrical_limits:{observed_at:stamp,source_valid:true,
        source_observed_at:stamp,source_stale_s:2,fixed_import_limit_w:3500,
        instantaneous_headroom_w:500,quarter_enabled:true,quarter_valid:true,
        quarter_theoretical_headroom_w:100000,sg_solar_valid:true,sg_solar_observed_at:stamp,
        sg_eligible_solar_w:4000,sg_hp_solar_w:3500,sg_residual_solar_w:500}};
      // Make every other observation already expired so only electrical
      // freshness changes during the later no-HA-event clock regression.
      for(const key of ['power_observed_at','power_supply1_observed_at','power_supply2_observed_at',
        'temperature_stamp','target_stamp','compressor_frequency_observed_at','sg_status_observed_at','context_stamp'])a.panasonic[key]=stamp-121;
      a.panasonic.operation.observed_at=stamp-121;
      for(const zone of a.panasonic.zones)zone.observed_at=stamp-121;
      a.sg_boost.observed_at=a.sg_boost.relay_observed_at=stamp-121;
      c._render();
    };}''')
    for view in ('overview', 'comfort', 'loads'):
        page.locator(f'solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value={view}]').click()
        panel = row if view == 'overview' else page.locator('solar-pilot-card >> .heatpump-sg')
        page.evaluate('qaElectrical()')
        details_key = 'overview:sg:why' if view == 'overview' else f'sg:{view}:details'
        details = panel.locator(f'details[data-ui-key="{details_key}"]')
        if details.get_attribute('open') is None:
            details.locator(':scope > summary').click()
        assert details.get_attribute('open') is not None, (view, 'electrical Details should be open')
        facts = panel.locator('.start-facts>span')
        hp_credit_label = 'Warmtepompbijdrage aan startdrempel (afgeleid)'

        def assert_electrical_fact(label, expected):
            fact = facts.filter(has_text=label).locator('b')
            assert fact.count() == 1, (view, label, 'expected one electrical fact', fact.count())
            assert fact.is_visible(), (view, label, 'electrical fact should be visible')
            actual = fact.inner_text()
            assert actual == expected, (view, label, f'expected {expected!r}, got {actual!r}')

        for label, expected in (
            ('Elektrische ruimte nu', '500 W'),
            ('Theoretisch kwartierbudget', '100 kW'),
            ('Zonnevermogen voor SG-drempel', '4 kW'),
            (hp_credit_label, '3,5 kW'),
            ('Resterende vrije zonnestroom', '500 W'),
        ):
            assert_electrical_fact(label, expected)
        assert 'verruimt de vaste net- en fasegrenzen nooit' in panel.text_content()
        assert '100 kW' not in prominent_text(panel)
        page.evaluate('''() => {
          window.qaStateBeforeBudgetExpiry=c._last;
          window.qaElectricalBeforeExpiry=structuredClone(c._last.attributes.ems.electrical_limits);
          qaClockMs+=3000;c._refreshObservationDisplay();
        }''')
        assert page.evaluate('c._last===qaStateBeforeBudgetExpiry')
        assert page.evaluate('JSON.stringify(c._last.attributes.ems.electrical_limits)===JSON.stringify(qaElectricalBeforeExpiry)')
        assert details.get_attribute('open') is not None, (view, 'electrical Details should remain open after clock expiry')
        for label in ('Elektrische ruimte nu', 'Zonnevermogen voor SG-drempel', hp_credit_label, 'Resterende vrije zonnestroom'):
            assert_electrical_fact(label, '—')
        assert panel.locator('[data-heatpump-task=inferred]').count() == 0
        # Restore the fixture's collapsed state for subsequent Details tests.
        details.locator(':scope > summary').click()
        assert details.get_attribute('open') is None, (view, 'electrical Details should close on request')
    page.locator('solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value=overview]').click()

    # beta74: fresh OFF on space circuits cannot certify the entire heat pump
    # is inactive when the main meter is invalid and the tank is separately ON.
    page.evaluate('''()=>{window.qaScope=(global=false,age=0)=>{
      const stamp=Date.now()/1000,native_task={function:null,inactive:true,inactive_action:'off',
        inactive_scope:global?'global':'unknown',verified_global_off:global,independent_tank_on:false,
        source:'aquarea_poll',conflict:false,observed_at:stamp-age,stale_s:120,
        label:global?'Panasonic meldt uit':'Panasonic meldt rust'};
      qaMeter({power1:null,power2:0,complete:false,native:'unknown',sg:true,nativeTask:native_task});
      Object.assign(c._last.attributes.panasonic,{operation:{state:'idle',label:'Panasonic meldt rust',
        evidence:'native_action',observed_at:stamp,stale_s:120},
        zones:[{name:'Fictieve ruimte',mode:'heat',action:'off',available:true,observed_at:stamp}],
        display_tank:{available:true,mode:'on',action:null,temperature_c:49,target_c:50,
          observed_at:stamp,temperature_stamp:stamp,target_stamp:stamp}});c._render();
    };}''')
    for view in ('overview', 'comfort', 'loads'):
        page.locator(f'solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value={view}]').click()
        panel = row if view == 'overview' else page.locator('solar-pilot-card >> .heatpump-sg')
        page.evaluate('qaScope()')
        assert panel.get_attribute('data-activity') == 'unknown', (view, 'zone OFF and invalid main do not prove whole heat pump inactivity', panel.inner_text())
        assert panel.locator('[data-heatpump-task],[data-heatpump-operation]').count() == 0, (view, 'unknown scope hides the incorrect Niet actief task/animation')
        details_key = 'overview:sg:why' if view == 'overview' else f'sg:{view}:details'
        details = panel.locator(f'details[data-ui-key="{details_key}"]')
        if details.get_attribute('open') is None:
            details.locator(':scope > summary').click()
        actual = panel.locator('[data-heatpump-provenance]').inner_text()
        assert 'OFF · bereik niet vastgesteld' in actual, (view, 'raw action and unknown circuit scope remain inspectable', actual)
        for width in (320, 390, 768, 1280):
            page.set_viewport_size({'width': width, 'height': 844 if width < 540 else 1000})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), (view, width, 'scope-aware history/SG panel overflows viewport')
            assert panel.evaluate('element=>element.scrollWidth<=element.clientWidth+1'), (view, width, 'scope diagnostics overflow the heat pump panel')
        page.evaluate('qaScope(true)')
        actual = panel.locator('[data-heatpump-task]').inner_text()
        assert panel.get_attribute('data-activity') == 'inactive' and 'Niet actief' in actual, (view, 'fresh typed verified global OFF remains visible', actual)
        page.evaluate('''()=>{c._last.attributes.panasonic.native_task.independent_tank_on=true;c._render();}''')
        assert panel.get_attribute('data-activity') == 'unknown', (view, 'contradictory independently ON tank cannot certify whole-device OFF')
        page.evaluate('qaScope(true,119)')
        page.evaluate('''()=>{qaClockMs+=2000;c._refreshObservationDisplay();}''')
        assert panel.get_attribute('data-activity') == 'unknown', (view, 'own global-OFF proof expires before current operation overview')
        assert panel.locator('[data-heatpump-task],[data-heatpump-operation]').count() == 0, (view, 'clock expiry cannot keep a false whole heat pump idle claim')
        page.evaluate('''()=>{c._last.attributes.panasonic.operation.observed_at=Date.now()/1000;c._render();}''')
        assert panel.get_attribute('data-activity') == 'unknown', (view, 'new overview cannot revive expired global-OFF source')
        page.evaluate('''()=>{qaScope(true);c._last.attributes.restored=true;c._render();}''')
        assert panel.get_attribute('data-activity') == 'unknown', (view, 'reload/restored display grants no current whole heat pump proof')
        page.evaluate("qaMeter({power1:null,power2:0,complete:false,native:'idle',sg:true})")
        actual = panel.locator('[data-heatpump-task]').inner_text()
        assert 'Compressor staat stil' in actual and 'Niet actief' not in actual, (view, 'zero Hz is a specific compressor status', actual)
        assert details.get_attribute('open') is not None, (view, 'scope/source refresh preserves Details')
        details.locator(':scope > summary').click()
        assert page.evaluate('qaCalls.length===0'), (view, 'scope presentation must send no device writes')
    page.locator('solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value=overview]').click()

    # beta71: the independent five-minute session rearm is visible even when
    # ordinary rest is ready. Zero time awaits backend confirmation, and the
    # actual candidate's source deadline expires before a still-fresh overview.
    page.evaluate('''() => {window.qaWait=(extra={})=>{
      qaApply('unknown',false);const stamp=Date.now()/1000,s=c._last.attributes.sg_boost;
      Object.assign(s,{profile:'general',completion_hold:true,state:'completion_hold',
        rest_remaining_s:0,start_required_s:120,reassessment_required_s:300,
        reassessment_state:'confirming_new_solar_period',reassessment_kind:'new_solar_period',
        reassessment_remaining_s:250,reassessment_reports:2,reassessment_source_current:true,
        reassessment_valid_until:stamp+120,reassessment_final_report_required:false,
        start_remaining_s:null,start_valid_until:null},extra);c._render();
    };}''')
    for view in ('overview', 'comfort', 'loads'):
        page.locator(f'solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value={view}]').click()
        panel = row if view == 'overview' else page.locator('solar-pilot-card >> .heatpump-sg')
        for _later_report in range(3):
            page.evaluate("qaWait({reassessment_state:'waiting_new_evidence',reassessment_kind:null,reassessment_remaining_s:null,reassessment_valid_until:null,reassessment_reports:0,reassessment_final_report_required:false})")
            actual = panel.locator('[data-sg-wait]').inner_text()
            assert 'Wacht op nieuwe zonneperiode of gewijzigde Panasonic-context' in actual, (view, 'already-confirmed reset waits for a new episode', actual)
            assert 'resetten' not in actual and 'nog ' not in actual and 'gereed' not in actual, (view, 'later low/normal reports cannot display another reset timer', actual)
        page.evaluate("qaWait({reassessment_state:'waiting_new_evidence',reassessment_kind:null,reassessment_remaining_s:null,reassessment_valid_until:null,reassessment_source_current:false})")
        actual = panel.locator('[data-sg-wait]').inner_text()
        assert 'Herbevestiging onbekend' in actual, (view, 'unknown/stale evidence after a confirmed reset grants no timer', actual)
        page.evaluate('qaWait()')
        wait = panel.locator('[data-sg-wait]')
        actual = wait.inner_text()
        assert 'Nieuw zonneoverschot: nog 4 min 10 s van 5 min' in actual, (view, 'actual rearm countdown', actual)
        assert 'gereed' not in actual, (view, 'rearm cannot inherit rest-ready label', actual)
        details_key = 'overview:sg:why' if view == 'overview' else f'sg:{view}:details'
        details = panel.locator(f'details[data-ui-key="{details_key}"]')
        if details.get_attribute('open') is None:
            details.locator(':scope > summary').click()
        facts = panel.locator('.start-facts>span')
        for label, expected in (('SG-herhaalwacht', 'gereed'), ('Ingestelde startvertraging', '2 min'), ('Vereiste herbevestiging', '5 min')):
            actual = facts.filter(has_text=label).locator('b').inner_text()
            assert actual == expected, (view, label, f'expected {expected!r}, got {actual!r}')

        # beta97: request rest may overlap proven residual reassessment. The
        # conditional label comes from the backend, never from elapsed time.
        page.evaluate("""qaWait({rest_remaining_s:900,policy_hold_reason:'response_unknown',
          desired_on:false,relay_on:false,relay_confirmed:true,relay_observed_at:Date.now()/1000,
          reassessment_kind:'fresh_residual_surplus',reassessment_state:'confirming_fresh_residual_surplus',
          rearm_wait:{request_rest_remaining_s:900,request_rest_replaceable:true}})""")
        actual = wait.inner_text()
        assert 'SG-herhaalwacht: nog 15 min' in actual and 'Kan eerder vervallen na 5 min' in actual, (view, 'conditional overlapping request wait', actual)
        assert 'Daarna geldt de gewone startvertraging' in actual, (view, 'ordinary start delay remains separate', actual)
        assert panel.locator('[data-sg-stage=relay] strong').inner_text() == 'Open', (view, 'request reassessment never implies active contact')
        page.evaluate("""()=>{c._last.attributes.sg_boost.rearm_wait.request_rest_replaceable=false;c._render();}""")
        assert 'Kan eerder vervallen' not in wait.inner_text(), (view, 'missing backend approval cannot promise early replacement')

        page.evaluate('qaWait({reassessment_remaining_s:1})')
        page.evaluate('''()=>{window.qaWaitState=c._last;qaClockMs+=2000;c._refreshObservationDisplay();}''')
        actual = wait.inner_text()
        assert 'wacht op verse bevestiging' in actual and 'gereed' not in actual, (view, 'zero rearm awaits new final report', actual)
        assert page.evaluate('c._last===qaWaitState && c._last.attributes.sg_boost.reassessment_remaining_s===1'), (view, 'clock-only progress cannot mutate backend state')
        assert details.get_attribute('open') is not None, (view, 'wait refresh keeps open Details')
        assert panel.locator('[data-sg-stage=relay] strong').inner_text() == 'Open', (view, 'time expiry cannot close SG contact')

        page.evaluate('qaWait({reassessment_valid_until:Date.now()/1000+2})')
        page.evaluate('''()=>{qaClockMs+=3000;c._refreshObservationDisplay();}''')
        actual = wait.inner_text()
        assert 'Herbevestiging onbekend' in actual and 'nog 4 min' not in actual, (view, 'real source expires before overview', actual)

        page.evaluate("qaWait({completion_hold:false,state:'waiting_surplus',start_remaining_s:77,start_valid_until:Date.now()/1000+120})")
        actual = wait.inner_text()
        assert 'SG-startvertraging' in actual and 'nog 1 min 17 s van 2 min' in actual, (view, 'ordinary start delay is separate', actual)
        page.evaluate("qaWait({completion_hold:false,state:'waiting_surplus',start_remaining_s:1,start_valid_until:Date.now()/1000+120})")
        page.evaluate('''()=>{qaClockMs+=2000;c._refreshObservationDisplay();}''')
        actual = wait.inner_text()
        assert 'wacht op actuele beoordeling' in actual and 'verse bevestiging' not in actual and 'gereed' not in actual, (view, 'ordinary zero waits for existing assessment', actual)
        page.evaluate("qaWait({completion_hold:false,state:'waiting_surplus',start_remaining_s:77,start_valid_until:Date.now()/1000+2})")
        page.evaluate('''()=>{qaClockMs+=3000;c._refreshObservationDisplay();}''')
        actual = wait.inner_text()
        assert 'startvertraging onbekend' in actual, (view, 'ordinary source expiry', actual)
        if details.get_attribute('open') is not None:
            details.locator(':scope > summary').click()
        assert page.evaluate('qaCalls.length===0'), (view, 'wait presentation never writes to devices')
    page.locator('solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value=overview]').click()

    # beta72: the SG minimum is a request-duration policy, independently of
    # native compressor activity. Its clock cannot release the contact, extend
    # an expired lease or claim a 20-minute compressor run.
    page.evaluate('''()=>{window.qaMinimum=(extra={})=>{
      qaApply('idle',true);const stamp=Date.now()/1000,s=c._last.attributes.sg_boost;
      Object.assign(s,{state:'active',remaining_s:1800,min_session_s:1200,
        effective_min_session_s:1200,minimum_limited_by_max:false,minimum_active:true,
        minimum_remaining_s:1120,minimum_valid_until:stamp+120,minimum_import_hold:false},extra);
      c._render();
    };}''')
    for view in ('overview', 'comfort', 'loads'):
        page.locator(f'solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value={view}]').click()
        panel = row if view == 'overview' else page.locator('solar-pilot-card >> .heatpump-sg')
        page.evaluate('qaMinimum()')
        minimum = panel.locator('[data-sg-minimum]')
        actual = minimum.inner_text()
        assert 'Minimum SG-aanvraagduur · 20 min' in actual and 'Nog 18 min 40 s · alleen de SG-aanvraag' in actual, (view, 'confirmed SG request minimum', actual)
        assert 'Na het minimum kan SG doorgaan' in actual and 'Panasonic bepaalt zelf de compressorlooptijd' in actual, (view, 'minimum is not compressor duration or fixed stop', actual)
        assert panel.locator('[data-heatpump-operation]').get_attribute('data-compressor-running') == 'false', (view, 'SG minimum may coexist with idle native compressor')
        details_key = 'overview:sg:why' if view == 'overview' else f'sg:{view}:details'
        details = panel.locator(f'details[data-ui-key="{details_key}"]')
        if details.get_attribute('open') is None:
            details.locator(':scope > summary').click()
        for label in ('Ingesteld SG-minimum', 'Effectief SG-minimum'):
            actual = panel.locator('.start-facts>span').filter(has_text=label).locator('b').inner_text()
            assert actual == '20 min', (view, label, 'expected20 min', actual)
        for width in (320, 390, 768, 1280):
            page.set_viewport_size({'width': width, 'height': 844 if width < 540 else 1000})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), (view, width, 'minimum content overflows viewport')
            assert panel.evaluate('element=>element.scrollWidth<=element.clientWidth+1'), (view, width, 'minimum content overflows heatpump panel')
        page.evaluate('qaMinimum({minimum_remaining_s:1})')
        page.evaluate('''()=>{window.qaMinimumState=c._last;qaClockMs+=2000;c._refreshObservationDisplay();}''')
        actual = minimum.inner_text()
        assert 'Minimum verstreken' in actual and 'actuele regeling bepaalt het vrijgeven' in actual, (view, 'minimum zero is not stop authority', actual)
        assert panel.locator('[data-sg-stage=relay] strong').inner_text() == 'Actief', (view, 'minimum expiry may not release SG contact')
        assert page.evaluate('c._last===qaMinimumState && c._last.attributes.sg_boost.minimum_remaining_s===1 && c._last.attributes.sg_boost.desired_on===true'), (view, 'minimum clock must not mutate request state')
        assert details.get_attribute('open') is not None, (view, 'minimum clock refresh preserves Details')
        page.evaluate('qaMinimum({minimum_valid_until:Date.now()/1000+2})')
        page.evaluate('''()=>{qaClockMs+=3000;c._refreshObservationDisplay();}''')
        actual = minimum.inner_text()
        assert 'Resterende minimumduur onbekend' in actual and 'Nog 18 min' not in actual, (view, 'minimum original proof expiry', actual)
        page.evaluate('qaMinimum({relay_valid_until:Date.now()/1000+2})')
        page.evaluate('''()=>{qaClockMs+=3000;c._refreshObservationDisplay();}''')
        assert 'Resterende minimumduur onbekend' in minimum.inner_text(), (view, 'lease expiry cannot retain minimum authority', minimum.inner_text())
        page.evaluate('qaMinimum({effective_min_session_s:900,minimum_limited_by_max:true,minimum_remaining_s:800})')
        actual = minimum.inner_text()
        assert 'Minimum SG-aanvraagduur · 15 min' in actual and 'maximale sessieduur begrenst het minimum' in actual, (view, 'existing lower hard max stays visible', actual)
        page.evaluate('qaMinimum({effective_min_session_s:299.3,minimum_limited_by_max:true,minimum_remaining_s:300})')
        actual = minimum.inner_text()
        assert 'Nog 5 min · alleen de SG-aanvraag' in actual, (view, 'backend ceiling remains valid with fractional acknowledgement delay', actual)
        page.evaluate('qaMinimum({minimum_import_hold:true})')
        assert 'Tijdelijke netafname' in minimum.inner_text(), (view, 'soft import hold remains explicit')
        if details.get_attribute('open') is not None:
            details.locator(':scope > summary').click()
        assert page.evaluate('qaCalls.length===0'), (view, 'minimum presentation must send no actuator writes')
    page.locator('solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value=overview]').click()

    # beta73: a cloud buffer is separate from the twenty-minute minimum and
    # cannot gain fresh source/lease authority from rendering a newer snapshot.
    page.evaluate('''()=>{window.qaCloud=(extra={})=>{
      qaMinimum();const stamp=Date.now()/1000,s=c._last.attributes.sg_boost;
      Object.assign(s,{minimum_remaining_s:0,minimum_active:false,minimum_import_hold:false,
        import_threshold_w:600,stop_delay_s:300,cloud_active:true,cloud_import_hold:true,
        cloud_remaining_s:250,cloud_valid_until:stamp+120},extra);c._render();
    };}''')
    for view in ('overview', 'comfort', 'loads'):
        page.locator(f'solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value={view}]').click()
        panel = row if view == 'overview' else page.locator('solar-pilot-card >> .heatpump-sg')
        page.evaluate('qaCloud()')
        cloud = panel.locator('[data-sg-cloud]')
        actual = cloud.inner_text()
        assert 'Wolkenbuffer · 600 W / 5 min' in actual and 'Netafname boven 600 W · nog 4 min 10 s' in actual, (view, 'effective cloud policy after SG minimum', actual)
        assert 'lopen tegelijk' in actual, (view, 'cloud buffer must not add five minutes after the minimum', actual)
        assert 'Minimum verstreken' in panel.locator('[data-sg-minimum]').inner_text(), (view, 'twenty-minute minimum remains a separate clock')
        assert panel.locator('[data-heatpump-operation]').get_attribute('data-compressor-running') == 'false', (view, 'cloud buffer never claims native compressor runtime')
        details_key = 'overview:sg:why' if view == 'overview' else f'sg:{view}:details'
        details = panel.locator(f'details[data-ui-key="{details_key}"]')
        if details.get_attribute('open') is None:
            details.locator(':scope > summary').click()
        for label, expected in (('Drempel netafname wolkenbuffer', '600 W'), ('Aaneengesloten bufferduur', '5 min')):
            actual = panel.locator('.start-facts>span').filter(has_text=label).locator('b').inner_text()
            assert actual == expected, (view, label, expected, actual)
        for width in (320, 390, 768, 1280):
            page.set_viewport_size({'width': width, 'height': 844 if width < 540 else 1000})
            assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), (view, width, 'cloud buffer overflows viewport')
            assert panel.evaluate('element=>element.scrollWidth<=element.clientWidth+1'), (view, width, 'cloud buffer overflows heatpump panel')
        page.evaluate('qaCloud({cloud_remaining_s:1,minimum_remaining_s:480,minimum_active:true})')
        page.evaluate('''()=>{window.qaCloudState=c._last;qaClockMs+=2000;c._refreshObservationDisplay();}''')
        actual = cloud.inner_text()
        assert 'Wolkenbuffer verstreken · actuele regeling bepaalt het vrijgeven' in actual, (view, 'cloud zero is not stop authority', actual)
        assert 'Nog 7 min 58 s' in panel.locator('[data-sg-minimum]').inner_text(), (view, 'remaining minimum continues independently')
        assert panel.locator('[data-sg-stage=relay] strong').inner_text() == 'Actief', (view, 'cloud clock cannot release the contact')
        assert page.evaluate('c._last===qaCloudState && c._last.attributes.sg_boost.cloud_remaining_s===1 && c._last.attributes.sg_boost.desired_on===true'), (view, 'cloud clock must not mutate request state')
        assert details.get_attribute('open') is not None, (view, 'cloud refresh preserves Details')
        page.evaluate('qaCloud({cloud_valid_until:Date.now()/1000+2})')
        page.evaluate('''()=>{qaClockMs+=3000;c._refreshObservationDisplay();}''')
        actual = cloud.inner_text()
        assert 'Resterende wolkenbuffer onbekend' in actual and 'nog 4 min' not in actual, (view, 'original grid source expiry without HA event', actual)
        page.evaluate('qaCloud({cloud_valid_until:Date.now()/1000-1})')
        assert 'Resterende wolkenbuffer onbekend' in cloud.inner_text(), (view, 'fresh overview cannot revive old cloud proof', cloud.inner_text())
        page.evaluate('qaCloud({relay_valid_until:Date.now()/1000+2})')
        page.evaluate('''()=>{qaClockMs+=3000;c._refreshObservationDisplay();}''')
        assert 'Resterende wolkenbuffer onbekend' in cloud.inner_text(), (view, 'lease expiry invalidates cloud time', cloud.inner_text())
        page.evaluate('qaCloud({cloud_active:false,cloud_remaining_s:null})')
        assert 'Geen lopende importbuffer' in cloud.inner_text(), (view, 'idle cloud state requires original current sources', cloud.inner_text())
        page.evaluate('qaCloud({cloud_active:false,cloud_remaining_s:null,cloud_valid_until:Date.now()/1000-1})')
        assert 'Resterende wolkenbuffer onbekend' in cloud.inner_text() and 'Geen lopende importbuffer' not in cloud.inner_text(), (view, 'stale idle sources remain unknown', cloud.inner_text())
        page.evaluate('qaCloud({import_threshold_w:450,stop_delay_s:90,cloud_remaining_s:60,hysteresis_w:900})')
        actual = cloud.inner_text()
        assert 'Wolkenbuffer · 450 W / 1 min 30 s' in actual and '900 W' not in actual, (view, 'custom import policy differs from solar-reset hysteresis', actual)
        if details.get_attribute('open') is not None:
            details.locator(':scope > summary').click()
        assert page.evaluate('qaCalls.length===0'), (view, 'cloud presentation must send no device writes')
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
      Object.assign(a.wallbox,{enabled:true,activity_known:true,power_w:3000,last_report_age_s:0,
        activity_details:{current:{known:true,active:true,report_timestamp:Date.now()/1000}}});
      c._render();}''')
    ordinary = page.locator('solar-pilot-card >> .device.on:not(.dishwasher) .icon').first
    external = page.locator('solar-pilot-card >> .device.dishwasher.on .icon').first
    wallbox_row = page.locator('solar-pilot-card >> .wallbox-device')
    wallbox = wallbox_row.locator('.icon')
    assert 'on' in wallbox_row.get_attribute('class').split()
    for icon in (ordinary,external,wallbox):
        assert icon.evaluate('element=>getComputedStyle(element).animationName') == 'sp-device-activity'
    page.emulate_media(reduced_motion='reduce')
    for icon in (ordinary,external,wallbox):
        assert icon.evaluate('element=>getComputedStyle(element).animationName') == 'none'
    page.emulate_media(reduced_motion='no-preference')
    page.evaluate("c._last.state='unavailable';c._refreshObservationDisplay()")
    assert 'on' not in wallbox_row.get_attribute('class').split()
    assert 'LAADSTATUS ONBEKEND' in wallbox_row.inner_text()
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
      const attack='<img src=x onerror="qaUnsafeExecuted=true"><script>qaUnsafeExecuted=true</script>';
      window.qaInvestigation={schema:1,read_only:true,updated_at:Date.now()/1000,
        notice:'Lokale analyse met gekoppelde bronnen; voorstellen blijven advies.',items:[
          {id:'heatpump-meter',title:'Warmtepompmeting',status:'check_needed',summary:'De totaalmeting blijft onbekend.',
            next_action:'Controleer de bestaande bron bij een bekende belasting.',evidence:['Een negatieve deelmeting.'],
            hypotheses:['Richting of nulpunt kan afwijken; niet bewezen.'],metrics:{complete_samples:0},
            proposals:[{id:'fictional-check',kind:'measurement_check',text:'Vergelijk de gekoppelde bron.'}]},
          {id:'wallbox',title:'Wallbox',status:'observed_ok',summary:'Geen afwijking in deze meetpunten.'},
          {id:'pv',title:'Zonnevoorspelling',status:'collecting',summary:'Meer vergelijkbare daglichtmetingen nodig.'},
          {id:'dishwasher',title:'Afwasmachine',status:'not_configured',summary:'Geen eigen vermogensbron gekoppeld.'},
          {id:'sg',title:'SG-sessies '+attack,status:'collecting',summary:attack,next_action:attack,
            evidence:[attack],hypotheses:[attack],metrics:{fictional_note:attack},
            proposals:[{id:'fictional-software',kind:'software_proposal',text:attack}]}]};
      const attributes=c._last.attributes;
      attributes.learning_insights={open_questions:1,investigation:qaInvestigation,findings:[{id:'fictional-finding',revision:'fixture',
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
        if(message.type==='solar_pilot/learning'&&message.operation==='read'){
          qaInvestigation.updated_at=Date.now()/1000;
          return {ready:true,investigation:structuredClone(qaInvestigation),
            questions:[{title:'Oude interactieve vraag',choices:[{id:'apply',label:'Niet tonen'}]}],models:[]};
        }
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
    analysis = page.locator('solar-pilot-card >> ' + page.evaluate('c._analysisDialog.localName'))
    assert not analysis.locator('.hours').is_visible() and not analysis.locator('.names').is_visible()
    assert analysis.locator('.template').is_visible()
    with page.expect_download() as template_info:
        analysis.locator('.template').click()
    assert json.loads(Path(template_info.value.path()).read_text()) == page.evaluate('qaTemplate')
    analysis.locator('.close').click()
    # Closing a tracked modal also settles the asynchronous browser-history
    # transition. Wait for that transition before opening another surface.
    page.wait_for_function('''() => {const bus=c._uiHistory.constructor.bus;
      return !c._analysisDialog._dialog.open && !bus.pending && !bus.moving && !bus.applying;}''')
    assert not analysis.locator('dialog').is_visible()

    page.locator('solar-pilot-card >> .footer [data-action=learning_hub]').click()
    quality = page.locator('solar-pilot-card >> ' + page.evaluate('c._learningDialog.localName'))
    page.wait_for_function('!c._learningDialog._busy && !!c._learningDialog._data')
    assert quality.locator('h2').inner_text() == 'Meetkwaliteit'
    assert 'Oude interactieve vraag' not in quality.locator('.body').inner_text()
    assert quality.locator('[data-question],[data-policy],[data-action=answer],[data-action=policy]').count() == 0
    assert page.evaluate("qaWS.filter(x=>x.type==='solar_pilot/learning')") == [
        {'type': 'solar_pilot/learning', 'config_entry_id': 'offline-example', 'operation': 'read'}]
    investigation = quality.locator('.automatic-investigation')
    assert investigation.count() == 1
    assert investigation.get_attribute('data-investigation-current') == 'current'
    assert investigation.locator('[data-investigation-id]').count() == 5
    assert investigation.locator('[data-investigation-status]').all_text_contents() == [
        'Controle nodig', 'Geen afwijking in deze metingen', 'Meer meetgegevens nodig',
        'Bron of functie niet ingesteld', 'Meer meetgegevens nodig']
    assert investigation.locator('img,script,a,input,button,select').count() == 0
    assert not page.evaluate('qaUnsafeExecuted')
    investigation.locator('details').first.evaluate('element=>element.open=true')
    page.evaluate('qaClockMs+=181000;c._learningDialog._refreshInvestigationDisplay()')
    assert investigation.get_attribute('data-investigation-current') == 'stale'
    assert investigation.locator('[data-investigation-status=observed_ok]').count() == 0
    assert investigation.locator('details').first.evaluate('element=>element.open')
    quality.locator('.refresh').click()
    page.wait_for_function("!c._learningDialog._busy && c._learningDialog._body.querySelector('.automatic-investigation').dataset.investigationCurrent==='current'")
    assert page.evaluate("qaWS.filter(x=>x.type==='solar_pilot/learning').length") == 2
    for width in (320, 390, 768, 1100):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert quality.locator('dialog').evaluate('element=>element.scrollWidth<=element.clientWidth'), ('local research dialog', width)
    quality.locator('.close').click()
    page.wait_for_function('''() => {const bus=c._uiHistory.constructor.bus;
      return !c._learningDialog._dialog.open && !c._learningDialog._isOpen &&
        !bus.pending && !bus.moving && !bus.applying;}''')
    assert not quality.locator('dialog').is_visible()
    # The retained popup DOM is expected. Scope subsequent checks to Export,
    # instead of treating every research section under the card as one node.
    assert quality.locator('.automatic-investigation').count() == 1

    page.locator('solar-pilot-card >> .nav > button[role=tab][data-action=view][data-value=export]').click()
    page.wait_for_function("!c._analysisFeedbackBusy && c._analysisFeedbackEntry==='offline-example' && c._analysisFeedbackReport?.current_release==='1.0.0-beta.67'")
    assert page.evaluate("qaWS.filter(x=>x.type==='solar_pilot/analysis_feedback')") == [
        {'type': 'solar_pilot/analysis_feedback', 'config_entry_id': 'offline-example', 'action': 'status'}]
    export_view = page.locator('solar-pilot-card >> .analysis-export')
    assert export_view.count() == 1
    assert 'Fictieve bevinding voor analyse' in export_view.inner_text()
    investigation = export_view.locator('.automatic-investigation')
    assert investigation.count() == 1
    assert investigation.get_attribute('data-investigation-current') == 'current'
    assert investigation.locator('[data-investigation-id]').count() == 5
    assert investigation.locator('img,script,a,input,button,select').count() == 0
    investigation.locator('details').first.evaluate('element=>element.open=true')
    page.evaluate('qaClockMs+=181000;c._refreshObservationDisplay()')
    assert investigation.get_attribute('data-investigation-current') == 'stale'
    assert investigation.locator('[data-investigation-status=observed_ok]').count() == 0
    assert investigation.locator('details').first.evaluate('element=>element.open')
    page.evaluate('''() => {qaInvestigation.updated_at=Date.now()/1000;
      c._last.attributes.restored=true;c._render();}''')
    assert investigation.get_attribute('data-investigation-current') == 'stale'
    page.evaluate('c._last.attributes.restored=false;c._render()')
    assert investigation.get_attribute('data-investigation-current') == 'current'
    assert 'staat los van een eerder geüpload adviesrapport' in investigation.inner_text()
    for width in (320, 390, 768, 1100):
        page.set_viewport_size({'width': width, 'height': 1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), ('local research export', width)
        page.screenshot(path=str(OUT / f'SolarPilot-onderzoek75-{width}.png'), full_page=True)
    assert not quality.locator('dialog').is_visible()
    assert page.evaluate("qaWS.filter(x=>x.type==='solar_pilot/learning').length") == 2
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
                                      'limitations': [unsafe_text]},
                                     {'category': 'solarpilot_setting', 'text': unsafe_text,
                                      'confidence': 'low', 'evidence': [], 'limitations': []},
                                     {'category': 'observation', 'text': unsafe_text,
                                      'confidence': 'low', 'evidence': [], 'limitations': []}])
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
    assert report.locator('[data-recommendation-kind] > b').all_text_contents() == [
        'Advies over instellingen', 'Waarneming · geen softwarewijziging']
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
    assert page.evaluate("qaWS.filter(x=>x.type==='solar_pilot/analysis_feedback').map(x=>x.action)") == ['status', 'import', 'status', 'remove']
    page.evaluate("c.hass={...c._hass,user:{id:'fictional-viewer',is_admin:false}};window.qaWSBeforeViewer=qaWS.length")
    for action in ('analysis_download', 'analysis_feedback_upload', 'analysis_feedback_reload'):
        assert page.locator(f'solar-pilot-card >> .analysis-export [data-action={action}]').is_disabled()
    page.evaluate('''async() => {await c._analysisFeedbackAction('remove');
      await c._importAnalysisFeedback({size:100,text:async()=>{qaFileReads++;return '{}';}});}''')
    assert page.evaluate('qaWS.length===qaWSBeforeViewer && qaFileReads===0')
    assert page.evaluate('qaCalls.length') == 0
    assert not errors, errors
    browser.close()
print('OK: independent native/compact SG evidence, typed main OFF versus tank ON/WATER, global/unknown OFF vetoes, circuit inactivity versus verified global OFF, zero-Hz compressor scope, once-confirmed reset without repeated timer, 3 views and 4 widths, separate theoretical/electrical/HP-solar/residual budgets, source expiry without HA events, SG minimum and cloud-buffer clocks with original source/lease expiry and no revived authority, reduced motion, draft/details preservation, partial/zero readings; one-click analysis/template, bounded escaped feedback, reload/removal/admin checks; 5 local research items with explicit statuses, escaped evidence/hypotheses/proposals, 4 widths, read-only refresh and expiry without HA events, restored-source veto and details preservation; zero device calls. Fiction only.')
