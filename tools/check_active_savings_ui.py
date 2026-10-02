"""Offline activity/value UI checks with fictitious data, zero hardware calls."""
import os
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR', '/tmp/solarpilot-browser-tests'))
OUT.mkdir(parents=True, exist_ok=True)
errors = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path=shutil.which('chromium'), headless=True,
                                         args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440,'height':1100}, locale='nl-BE')
    page.route('**/*', lambda route: route.abort())
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_content((ROOT/'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'))
    page.wait_for_selector('solar-pilot-card >> h1')
    page.evaluate('''() => {
      window.card=document.querySelector('solar-pilot-card');window.calls=[];
      card._hass.callService=async(...args)=>calls.push(args);
      window.demo=structuredClone(card._last.attributes);
      demo.mode='solar';demo.energy_estimated=true;
      demo.devices=[
        {id:'dw',kind:'dishwasher',name:'Afwasmachine · fictief voorbeeld',on:true,owned:true,
         mode:'auto',available:true,estimated:true,power_w:2000,reason:'Cyclus laten afwerken',
         dishwasher:{program:'Eco',phase:'Running',ticket_armed:false}},
        {id:'manual',kind:'switch',name:'Handmatig gestart toestel',on:true,owned:true,
         manual_forced:true,available:true,estimated:false,power_w:300},
        {id:'off',kind:'switch',name:'Uitgeschakeld toestel',on:false,owned:false,available:true,power_w:0},
        {id:'unknown',kind:'switch',name:'Toestel zonder actuele terugmelding',on:true,
         owned:true,available:false,power_w:9999}];
      Object.assign(demo.wallbox,{enabled:true,name:'Wallbox · fictief voorbeeld',power_w:2200,
        last_report_age_s:12,stale_s:120,demand:true,connected:true,activity_known:true,
        charging_threshold_w:50,effective_mode:'full_solar',session_confirmed:true});
      demo.ems.economy={enabled:true,import_eur_kwh:.30,export_eur_kwh:.03};
      demo.ems.savings={
        today:{estimated_benefit_eur:.27,solar_kwh:1,coverage_s:3600,power_estimated:true},
        available_period:{estimated_benefit_eur:.54,solar_kwh:2,coverage_s:7200,
          power_estimated:true,start_date:'2026-10-01',end_date:'2026-10-02',recorded_days:2},
        managed_reference:{today:{estimated_benefit_eur:.81,solar_kwh:3}},
        proven_savings_eur:null,baseline_available:false};
      window.refreshDemo=()=>card.hass={...card._hass,states:{...card._hass.states,
        [card._entity]:{state:'Solar',attributes:structuredClone(demo)}}};
      refreshDemo();card._view='overview';card._render();
    }''')
    active = page.locator('solar-pilot-card >> .active-loads')
    assert active.locator('.active-load').count() == 3
    assert 'Eco · Programma loopt' in active.inner_text()
    assert '≈ 2 kW' in active.inner_text() and 'geschat vermogen' in active.inner_text()
    assert 'ACTIEF · HANDMATIG' in active.inner_text()
    assert 'AUTO LAADT' in active.inner_text()
    assert 'Uitgeschakeld toestel' not in active.inner_text()
    assert 'Niet bevestigd' in active.inner_text()
    savings = page.locator('solar-pilot-card >> .savings-summary')
    assert '0,27' in savings.inner_text() and '0,54' in savings.inner_text()
    assert 'Nog niet vast te stellen' in savings.inner_text()
    savings.locator('summary').click()
    assert 'Handmatige starts en boosts tellen niet mee' in savings.inner_text()
    assert '0,81' in savings.inner_text() and 'ook handmatige bediening' in savings.inner_text()
    assert 'niet automatisch extra winst' in savings.inner_text()
    savings.locator('summary').click()
    for width in (320,390,768,1440):
        page.set_viewport_size({'width':width,'height':1100})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
        assert active.evaluate('el=>el.scrollWidth<=el.clientWidth+2'), width
        assert savings.evaluate('el=>el.scrollWidth<=el.clientWidth+2'), width
    page.set_viewport_size({'width':768,'height':1100})
    page.locator('solar-pilot-card >> .overview-view').screenshot(path=str(OUT/'SolarPilot-actief-en-voordeel-voorbeeld.png'))
    page.locator('solar-pilot-card >> button[data-action="view"][data-value="loads"]').click()
    wallbox = page.locator('solar-pilot-card >> .wallbox-device')
    assert ' on' in wallbox.get_attribute('class') and 'AUTO LAADT' in wallbox.inner_text()
    assert wallbox.locator('[data-action]').count() == 0
    assert 'Nog geen laadstop waargenomen' in wallbox.locator('.wb-stop').inner_text()
    page.evaluate("()=>{demo.wallbox.power_w=0;demo.wallbox.demand=true;refreshDemo();}")
    assert ' on' not in wallbox.get_attribute('class') and 'WACHT OP LAADSTROOM' in wallbox.inner_text()
    page.evaluate('''()=>{
      const event={observed_start_at:1790935200,start_confirmed:true,
        observed_stop_at:1790938800,stop_confirmed:true,cause_reported:true,
        native_status:'Waiting in queue by Eco-Smart',
        stop_reason:'Wallbox wacht op zonnestroom'};
      demo.wallbox.activity_details={current:{known:true,active:false,label:'Wacht op zonnestroom',native_status:event.native_status,
        reason:'Wallbox wacht op zonnestroom',waiting_for:'solar'},last_stop:event,history:[event]};
      refreshDemo();
    }''')
    assert 'Waarop wacht de Wallbox?' in wallbox.locator('.wb-wait').inner_text()
    assert 'WACHT OP ZONNESTROOM' in wallbox.inner_text()
    assert 'Wallbox wacht op zonnestroom' in wallbox.locator('.wb-wait').inner_text()
    assert 'niet automatisch de oorzaak' in wallbox.locator('.wb-wait').inner_text()
    assert 'Laadstop waargenomen:' in wallbox.locator('.wb-stop').inner_text()
    assert 'Wallbox meldde toen: Wallbox wacht op zonnestroom' in wallbox.locator('.wb-stop').inner_text()
    wallbox.locator('.wb-stop-history summary').click()
    assert 'Begin waargenomen:' in wallbox.locator('.wb-stop-history').inner_text()
    wallbox.locator('.wb-stop-history summary').click()
    for width in (320,390,768):
        page.set_viewport_size({'width':width,'height':1100})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), width
        assert wallbox.evaluate('el=>el.scrollWidth<=el.clientWidth+2'), width
    wallbox.screenshot(path=str(OUT/'SolarPilot-wallbox-wacht-en-stop-voorbeeld.png'))
    page.evaluate("()=>{demo.wallbox.power_w=2200;refreshDemo();}")
    assert 'Wallbox meldde toen: Wallbox wacht op zonnestroom' in wallbox.locator('.wb-stop').inner_text()
    assert 'De auto laadt nu' in wallbox.locator('.wb-wait').inner_text()
    page.evaluate('''()=>{const event={observed_start_at:1790935200,
      unavailable_observed_at:1790938800,stop_confirmed:false,cause_reported:false,
      stop_reason:'Wallbox-meting onderbroken; laadstop en exacte oorzaak niet bevestigd'};
      demo.wallbox.activity_details.last_stop=event;demo.wallbox.activity_details.history=[event];refreshDemo();}''')
    assert 'Laadstop niet bevestigd' in wallbox.locator('.wb-stop').inner_text()
    assert 'Laadstop waargenomen:' not in wallbox.locator('.wb-stop').inner_text()
    page.evaluate('''()=>{const event={observed_start_at:1790935200,
      observed_stop_at:1790938800,stop_confirmed:true,cause_reported:false,
      stop_reason:'Wallbox is gereed maar laadt niet; exacte stopoorzaak niet gemeld'};
      demo.wallbox.activity_details.last_stop=event;refreshDemo();}''')
    assert 'exacte oorzaak is niet doorgegeven' in wallbox.locator('.wb-stop').inner_text()
    page.evaluate("()=>{demo.wallbox.power_w=2200;demo.wallbox.activity_known=false;refreshDemo();}")
    assert ' on' not in wallbox.get_attribute('class') and 'LAADSTATUS ONBEKEND' in wallbox.inner_text()
    page.evaluate("()=>{demo.wallbox.activity_known=true;demo.wallbox.effective_mode='manual';refreshDemo();}")
    assert ' on' in wallbox.get_attribute('class') and 'AUTO LAADT' in wallbox.inner_text()
    # Missing report and prices are unknown, not a fabricated zero saving.
    page.evaluate("()=>{delete demo.ems.savings;demo.ems.economy.enabled=false;refreshDemo();card._view='overview';card._render();}")
    assert 'Nog geen afzonderlijke meetperiode' in savings.inner_text()
    assert '€ 0' not in savings.inner_text()
    assert page.evaluate('calls.length') == 0
    assert not errors, errors
    browser.close()
print('OK: actual/estimated active loads, charging/waiting/stale/manual Wallbox, native waiting reason and retained stop history versus unknown/gap, qualified auto savings and unknown baseline, 320/390/768/1440, zero actuator calls; fictitious data only.')
