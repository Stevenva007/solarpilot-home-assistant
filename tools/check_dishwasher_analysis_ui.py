"""Real card code + fictitious HA replies, no real appliance or server."""
import json,os,shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR','/tmp/solarpilot-browser-tests'));OUT.mkdir(exist_ok=True,parents=True)
errors=[]
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':1440,'height':1050},locale='nl-BE',accept_downloads=True)
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content((ROOT/'SolarPilot-voorbeeld.html').read_text(),wait_until='load')
 page.wait_for_selector('solar-pilot-card >> h1')
 page.evaluate('''() => {window.c=document.querySelector('solar-pilot-card');window.writes=[];window.wsCalls=[];window.approve=false;
 window.confirm=()=>approve;
 window.update=(patch={})=>{let a=structuredClone(c._last.attributes);a.config_entry_id='fictitious';a.devices=[{id:'dw',kind:'dishwasher',name:'Afwasmachine (voorbeeld)',mode:'auto',available:true,on:false,owned:false,power_w:0,priority:50,reason:'Klaarzetten voor één automatische afwasbeurt',non_interruptible:true,history:{on_s:0},mode_entity:'select.example_dw',dishwasher_arm_entity:'button.example_dw_prepare',dishwasher_cancel_entity:'button.example_dw_cancel',dishwasher:{ready:true,attempted:false,ticket_armed:false,program:'Eco',phase:'Idle',profile_count:0,power_source:'Handmatige vermogensschatting; geen meting',profile_note:'Nog geen volledig gemeten cyclus; fasen zijn onbekend, niet 0 W'},...patch}];c.hass={...c._hass,callService:async(...x)=>writes.push(x),callWS:async x=>{wsCalls.push(x);return {filename:'SolarPilot-analyse-voorbeeld.json',content:JSON.stringify({schema:'solarpilot.analysis',schema_version:1,example:true,requested_hours:x.hours,privacy:{entity_names_included:x.include_names},telemetry:{samples:[]}})}},states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};};update();
 }''')
 page.locator('solar-pilot-card >> button[data-action=view][data-value=loads]').click()
 card=page.locator('solar-pilot-card >> .dishwasher')
 assert 'NIET KLAARGEZET' in card.inner_text()
 assert card.locator('[data-action=boost],[data-action=manual_start],[data-action=manual_stop]').count()==0
 card.locator('[data-action=dishwasher_arm]').click();assert page.evaluate('writes.length')==0
 page.evaluate('approve=true');card.locator('[data-action=dishwasher_arm]').click()
 assert page.evaluate('writes')==[['button','press',{'entity_id':'button.example_dw_prepare'}]]
 page.evaluate('''update({on:true,owned:true,power_w:8,reason:'Beschermd afwasprogramma actief',dishwasher:{ready:false,ticket_armed:false,phase:'Drying',program:'Eco',power_source:'Shelly/toestelmeter',profile_count:0}})''')
 assert 'PROGRAMMA ACTIEF' in card.inner_text() and card.locator('[data-action=dishwasher_arm]').is_disabled()
 page.evaluate("update({available:false,reason:'Afwasmachine offline'})")
 assert 'ONBEKEND' in card.inner_text()
 page.evaluate('''update({dishwasher:{ready:true,program:'Eco',phase:'Idle',profile_count:1,power_source:'Shelly/toestelmeter',profile_note:'Volledig gemeten',last_measured_profile:{program:'Eco',energy_kwh:0.94,duration_s:3900,stages:{Washing:{seconds:2100,kwh:0.9,peak_w:1870},Drying:{seconds:1800,kwh:0.04,peak_w:120}}}}})''')
 card.locator('summary').click();assert '1870' not in card.inner_text() or 'Piek' in card.inner_text()
 assert 'Spoelen 0 W' not in card.inner_text()
 for width in (320,390,768,1440):
  page.set_viewport_size({'width':width,'height':1050})
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
  assert card.evaluate('e=>e.scrollWidth<=e.clientWidth+2'),width
 page.set_viewport_size({'width':1440,'height':1050});card.screenshot(path=str(OUT/'SolarPilot-beta29-afwasmachine-voorbeeld.png'))
 # Opened export and form state persist through 80 main-card updates.
 page.locator('solar-pilot-card >> .nav button[data-value=export]').click()
 page.locator('solar-pilot-card >> button[data-action=analysis_export]').click()
 dialog=page.locator('solar-pilot-analysis-dialog >> dialog')
 assert dialog.is_visible();assert page.evaluate('wsCalls.length')==0
 page.locator('solar-pilot-analysis-dialog >> .hours').select_option('168')
 page.locator('solar-pilot-analysis-dialog >> details summary').click()
 page.evaluate('''()=>{window.originalDialog=c._analysisDialog._dialog;for(let n=0;n<80;n++){let a=structuredClone(c._last.attributes);a.grid_w=-2000-n;c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}''')
 assert page.evaluate('originalDialog===c._analysisDialog._dialog && originalDialog.open')
 assert page.locator('solar-pilot-analysis-dialog >> .hours').input_value()=='168'
 assert page.locator('solar-pilot-analysis-dialog >> details').get_attribute('open') is not None
 for width in (320,390,768,1440):
  page.set_viewport_size({'width':width,'height':1050})
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
  assert dialog.evaluate('e=>e.scrollWidth<=e.clientWidth+2'),width
 page.set_viewport_size({'width':1440,'height':1050});dialog.screenshot(path=str(OUT/'SolarPilot-beta29-analyse-popup-voorbeeld.png'))
 with page.expect_download() as download:
  page.locator('solar-pilot-analysis-dialog >> .download').click()
 file=OUT/'analyse-ui-fictief.json';download.value.save_as(file)
 report=json.loads(file.read_text());assert report['example'] and report['requested_hours']==168 and not report['privacy']['entity_names_included']
 assert page.evaluate('writes.length')==1
 assert page.evaluate('wsCalls[0].type')=='solar_pilot/analysis_export'
 page.keyboard.press('Escape');assert not dialog.is_visible()
 # Literal markup in names must remain text and must not execute.
 page.evaluate("update({name:'<img src=x onerror=window.pwned=1>'})")
 assert card.locator('img').count()==0 and page.evaluate('window.pwned||0')==0
 assert not errors,errors
 browser.close()
print('OK: actual AEG card, confirmed one-load preparation, no pause/stop/plug controls, running at low W, unknown phase, measured profile, export download payload, pseudonyms default, 80 updates, 320/390/768/1440 layout, Esc, HTML escaping. All HA responses fictitious.')
