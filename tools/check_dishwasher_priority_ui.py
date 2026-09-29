"""Exercise the actual beta.32 priority UI; only fictitious HA API replies.

Optional local Playwright/Chromium tooling. No network or appliance commands.
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
    browser = p.chromium.launch(executable_path=shutil.which('chromium'), headless=True,
                                args=['--no-sandbox'])
    page = browser.new_page(viewport={'width':1440, 'height':1100}, locale='nl-BE',
                             timezone_id='Europe/Brussels')
    page.route('**/*', lambda route: route.abort())
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.set_content((ROOT/'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'), wait_until='load')
    page.wait_for_selector('solar-pilot-card >> h1')
    page.evaluate('''()=>{
      window.c=document.querySelector('solar-pilot-card'); window.calls=[];window.api=[];
      const a=structuredClone(c._last.attributes);a.config_entry_id='fictitious';a.mode='solar';
      a.integration_version='1.0.0-beta.32';a.pv_w=5500;a.grid_w=-50;
      a.devices=[{id:'dw',kind:'dishwasher',name:'AEG-afwasmachine · fictief voorbeeld',priority:10,
        mode:'auto',available:true,on:false,owned:false,estimated:true,power_w:0,history:{on_s:0},
        reason:'Startvertraging: 120 s',dishwasher_cancel_entity:'button.fictitious_cancel',
        dishwasher:{arming_mode:'app',ready:true,ticket_armed:true,app_request:true,program:'Eco',
          phase:'onbekend',profile_count:0,power_source:'Voorlopige schatting; geen exclusieve meter',
          app_message:'Via APP klaargezet; startdeadline vandaag',start_deadline:'2026-09-29T13:00:00+02:00',
          priority_policy:{configured:true,ev_solar_priority:true,conditional_ev_w:2500,
            unmetered_reserve_w:0,wallbox_response:{},ev_start_block:''}}},
        {id:'low',kind:'switch',name:'Ontvochtiger · fictief voorbeeld',priority:50,mode:'auto',
         available:true,on:true,owned:true,power_w:350,history:{on_s:1500},
         reason:'Afwasmachine krijgt voorrang na minimale looptijd'}];
      window.refresh=(patch={})=>{
        let next=structuredClone(c._last.attributes);Object.assign(next.devices[0].dishwasher.priority_policy,patch);
        c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:next}}};};
      c.hass={...c._hass,user:{is_admin:true},callService:async(...args)=>calls.push(args),
        states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}},
        callApi:async(method,path,data)=>{api.push({method,path,data});
          if(method==='delete')return{};
          if(path==='config/config_entries/options/flow')return{type:'form',flow_id:'demo',step_id:'dishwasher_states',errors:{},data_schema:[
            {name:'dishwasher_priority_enabled',required:true,selector:{boolean:{}},default:true},
            {name:'dishwasher_ev_solar_priority',required:true,selector:{boolean:{}},default:true}]};
          return{type:'create_entry',title:'Fictief opgeslagen',data:{}};}};
    }''')
    page.locator('solar-pilot-card >> button[data-action=view][data-value=loads]').click()
    card=page.locator('solar-pilot-card >> .dishwasher')
    assert 'Warmtepompcomfort eerst' in card.inner_text()
    assert 'tijdelijke netafname' in card.inner_text()
    assert '2,5 kW' in card.inner_text()
    assert card.locator('[data-action=dishwasher_arm],[data-action=manual_stop],[data-action=boost]').count()==0
    card.locator('details summary').click()
    page.evaluate('''()=>{for(let n=0;n<80;n++){const a=structuredClone(c._last.attributes);a.grid_w=-20-n;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}''')
    assert card.locator('details').get_attribute('open') is not None
    for width in (320,390,768,1440):
        page.set_viewport_size({'width':width,'height':1050})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        assert card.evaluate('e=>e.scrollWidth<=e.clientWidth+2'),width
    card.screenshot(path=str(OUT/'SolarPilot-beta32-afwasvoorrang.png'))
    page.evaluate("refresh({ev_solar_priority:false,conditional_ev_w:0})")
    assert 'alleen echt restoverschot' in card.inner_text()
    page.evaluate("refresh({ev_start_block:'<img src=x onerror=window.pwned=1>',wallbox_response:{reason:'Controle nodig; beurt blijft afwerken'},unmetered_reserve_w:2000})")
    assert 'extra ruimte gereserveerd' in card.inner_text()
    assert 'Controle nodig' in card.inner_text()
    assert card.locator('img').count()==0 and page.evaluate('window.pwned||0')==0
    page.evaluate("refresh({ev_solar_priority:true,conditional_ev_w:0,ev_start_block:'',wallbox_response:{}})")
    page.locator('solar-pilot-card >> button[data-action=configure]').first.click()
    host=page.locator('solar-pilot-options-dialog')
    page.wait_for_selector('solar-pilot-options-dialog >> [name=dishwasher_priority_enabled]')
    for key in ('dishwasher_priority_enabled','dishwasher_ev_solar_priority'):
        assert host.locator('[name='+key+']').is_checked()
        assert host.locator('button[data-help='+key+']').count()==1
    host.locator('[name=dishwasher_ev_solar_priority]').uncheck()
    host.locator('button[data-help=dishwasher_ev_solar_priority]').hover()
    host.locator('button[data-help=dishwasher_ev_solar_priority]').click()
    nested=host.locator('solar-pilot-option-help-dialog')
    assert nested.locator('dialog').is_visible()
    assert '15 minuten' in nested.locator('dialog').inner_text()
    page.evaluate('''()=>{for(let n=0;n<80;n++)refresh({conditional_ev_w:n});}''')
    assert not host.locator('[name=dishwasher_ev_solar_priority]').is_checked()
    assert nested.locator('dialog').is_visible()
    for width in (320,390,768,1440):
        page.set_viewport_size({'width':width,'height':1050})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        assert nested.locator('dialog').evaluate('e=>e.scrollWidth<=e.clientWidth+2'),width
    page.keyboard.press('Escape')
    host.locator('button[type=submit]').click()
    assert page.evaluate("api.some(x=>x.data&&x.data.dishwasher_priority_enabled===true&&x.data.dishwasher_ev_solar_priority===false)")
    assert page.evaluate('calls.length')==0
    assert not errors,errors
    browser.close()
print('OK: real beta32 priority card, default enabled preferences, explicit conditional EV/no-meter warnings, modal explanation, persisted form after 80 updates, widths 320/390/768/1440, safe escaping, zero device calls; fictitious API replies only.')
