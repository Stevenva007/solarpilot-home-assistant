"""Exercise the actual beta31 card with fictitious HA telemetry; no live calls."""
import json, os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR','/tmp/solarpilot-browser-tests'));OUT.mkdir(parents=True,exist_ok=True)
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1000},locale='nl-BE',timezone_id='Europe/Brussels')
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content((ROOT/'SolarPilot-voorbeeld.html').read_text(),wait_until='load')
    page.wait_for_selector('solar-pilot-card >> h1')
    page.evaluate('''()=>{window.c=document.querySelector('solar-pilot-card');window.calls=[];
    window.updateApp=(extra={},device={})=>{let a=structuredClone(c._last.attributes);a.mode='solar';
      a.devices=[{id:'dish',kind:'dishwasher',name:'AEG-afwasmachine (voorbeeld)',mode:'auto',available:true,on:false,owned:false,power_w:0,priority:50,
        reason:'Klaargezet na deadline; wacht op volgende dag 2026-09-30',history:{on_s:0},dishwasher_cancel_entity:'button.example_cancel',
        dishwasher:{arming_mode:'app',ready:true,ticket_armed:true,app_request:true,program:'Eco',phase:'onbekend',profile_count:0,
          app_message:'Via APP klaargezet; wacht op zon morgen',start_deadline:'2026-09-30T13:00:00+02:00',
          power_source:'Handmatige schatting; geen meter',...extra},...device}];
      c.hass={...c._hass,callService:async(...x)=>calls.push(x),states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};};updateApp();}''')
    page.locator('solar-pilot-card >> button[data-action=view][data-value=loads]').click()
    card=page.locator('solar-pilot-card >> .dishwasher')
    assert '13:00' in card.inner_text() and '30/09' in card.inner_text()
    assert card.locator('[data-action=dishwasher_arm]').count()==0
    assert card.locator('[data-action=dishwasher_cancel]').count()==1
    assert card.locator('[data-action=manual_stop],[data-action=boost]').count()==0
    card.locator('details summary').click()
    for width in (320,390,768,1440):
        page.set_viewport_size({'width':width,'height':1000})
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
        assert card.evaluate('e=>e.scrollWidth<=e.clientWidth+2'),width
    page.evaluate('''()=>{for(let n=0;n<80;n++){let a=structuredClone(c._last.attributes);a.grid_w=-500-n;c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}''')
    assert card.locator('details').get_attribute('open') is not None
    card.screenshot(path=str(OUT/'SolarPilot-beta31-app-planning.png'))
    page.evaluate("updateApp({app_request:false,ticket_armed:false,airdry:true,phase:'Ado Drying',cycle_status:'running',start_deadline:null},{on:true,owned:true,reason:'Programma loopt; laat nadrogen',power_w:8})")
    assert 'AIRDRY — NADROGEN' in card.inner_text()
    assert card.locator('[data-action=dishwasher_arm],[data-action=dishwasher_cancel]').count()==0
    page.evaluate("updateApp({app_request:false,ticket_armed:false,cycle_status:'completed',start_deadline:null,completion:{confirmed:true,ended_at_local:'2026-09-30T06:57:44+02:00'}},{on:false,available:false,reason:'Toestel uit na bevestigde afronding'})")
    assert 'KLAAR' in card.inner_text() and '06:57' in card.inner_text()
    assert 'leeggemaakt' in card.inner_text() and 'ONBEKEND' not in card.inner_text()
    card.screenshot(path=str(OUT/'SolarPilot-beta31-klaar.png'))
    page.evaluate("updateApp({app_request:false,ticket_armed:false,cycle_status:'end_unconfirmed',completion:null},{on:false,available:false})")
    assert 'Einde niet bevestigd' in card.inner_text()
    # Help catalogue has actual new options and defaults in the documented labels.
    help_data=page.evaluate('globalThis.SOLAR_PILOT_HELP_DATA')
    for key in ['dishwasher_arming_mode','dishwasher_start_deadline','dishwasher_after_deadline','dishwasher_deadline_grid_allowed','dishwasher_deadline_grace_min','dishwasher_alert_mode']:
        assert 'dishwasher_states.'+key in help_data['entries']
    page.evaluate("updateApp({app_message:'<img src=x onerror=window.pwned=1>'})")
    assert not card.locator('img').count() and page.evaluate('window.pwned||0')==0
    assert page.evaluate('calls.length')==0
    assert not errors,errors
    browser.close()
print('OK: actual APP card, no extra prepare button, tomorrow date + deadline, AirDry busy, end latch visible while offline, unknown end, 80 updates, responsive 320/390/768/1440, new field help, escaping, zero device calls. Fictitious HA telemetry only.')
