"""Real frontend; local model fixture. No network or device calls."""
from pathlib import Path
import os,json,shutil,subprocess,sys
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR','/tmp/solarpilot-browser-tests'));OUT.mkdir(parents=True,exist_ok=True)
fixture_script='''
import sys,json
from datetime import datetime,timedelta,timezone
sys.path.insert(0,"tests")
import conftest
from test_runtime import build
from test_pv_forecast33 import quarter,settings,NOW
from custom_components.solar_pilot.pv_calibration import PVCalibration
r,h=build();m=PVCalibration(settings())
for d in range(9):
 for q in range(28):
  dt=(NOW+timedelta(days=d)).replace(hour=9,minute=0)+timedelta(minutes=q*15)
  quarter(m,dt,actual=2800 if q<22 else 2100,raw=3500)
r.pv_forecast.model=m
r.pv_forecast.cached={"available":True,"enabled":True,"status":"FICTIEVE VOORBEELDGEGEVENS · Forecast.Solar tijdreeks",
 "note":"Softwareproef, geen meting van jouw installatie.","updated":NOW.isoformat(),"model":m.summary(),"factor":.8,"confidence":.75,"comparable_days":9,
 "inverter_limit_w":10000,"panel_peak_wp":13800,"native_raw_now_w":3500,"curve_method":"Lineair geïnterpoleerde broncurve",
 "horizon":[{"hours":h,"raw_w":3500-h*400,"corrected_w":(3500-h*400)*.8,"factor":.8} for h in range(4)],
 "raw_remaining_today_kwh":9.5,"corrected_remaining_today_kwh":7.6,"corrected_tomorrow_kwh":15.4,
 "energy_methods":{"remaining_today":"Geïntegreerde vermogenscurve"}}
print(json.dumps(r.pv_forecast.diagnostics()))
'''
fixture=json.loads(subprocess.check_output([sys.executable,'-B','-c',fixture_script],cwd=ROOT,text=True))
errors=[]
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
 page=b.new_page(viewport={'width':1440,'height':1120},locale='nl-BE',timezone_id='Europe/Brussels')
 page.route('**/*',lambda route:route.abort())
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.set_content((ROOT/'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'),wait_until='load')
 page.evaluate('''data=>{
  window.pvData=data;window.pvCalls=[];window.deviceCalls=[];window.c=document.querySelector('solar-pilot-card');
  let a=structuredClone(c._last.attributes);a.config_entry_id='fictief';a.ems.pv_forecast=data.summary;
  c.hass={...c._hass,user:{is_admin:true},callService:async(...args)=>{deviceCalls.push(args);throw Error('No actuators');},
   states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}},
   callWS:async msg=>{pvCalls.push(msg);if(window.pendingPV)return new Promise(resolve=>window.resolvePV=resolve);
     if(window.rejectPV)throw Error('Fictieve offline fout <img>');
     return structuredClone(pvData);}};
 }''',fixture)
 page.locator('solar-pilot-card >> [data-action=view][data-value=planning]').click()
 assert page.locator('solar-pilot-card >> .pv-summary').is_visible()
 page.locator('solar-pilot-card >> .pv-summary [data-action=pv_diagnostics]').click()
 host=page.locator('solar-pilot-pv-dialog');page.wait_for_selector('solar-pilot-pv-dialog >> .metrics')
 assert 'FICTIEVE' in host.locator('dialog').inner_text()
 assert host.locator('table.history tbody tr').count()>20
 assert host.locator('svg').count()==1
 assert '10 kW' in host.locator('dialog').inner_text() and '13,8 kWp' in host.locator('dialog').inner_text()
 assert page.evaluate('deviceCalls.length')==0
 host.locator('details summary').click()
 page.evaluate('''()=>{c._pvDialog._scroll.scrollTop=650;window.oldScroll=c._pvDialog._scroll.scrollTop;window.oldDay=c._pvDialog._days.value;
  for(let i=0;i<80;i++){let a=structuredClone(c._last.attributes);a.grid_w=-300-i;c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}''')
 assert host.locator('dialog').is_visible()
 assert page.evaluate('Math.abs(c._pvDialog._scroll.scrollTop-oldScroll)<2 && c._pvDialog._days.value===oldDay')
 assert host.locator('details').get_attribute('open') is not None
 assert page.evaluate('pvCalls.length')==1 # no periodic history fetch from 5s updates
 for width in (320,390,768,1440):
  page.set_viewport_size({'width':width,'height':1120})
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
  assert host.locator('dialog').evaluate('e=>e.scrollWidth<=e.clientWidth+2'),width
 page.evaluate('c._pvDialog._scroll.scrollTop=0')
 host.locator('dialog').screenshot(path=str(OUT/'SolarPilot-beta33-PV-diagnose.png'))
 # Day changing and refresh preserve selected date/details.
 second=host.locator('select option').nth(1).get_attribute('value');host.locator('select').select_option(second)
 host.locator('button[data-action=refresh]').click();page.wait_for_timeout(100)
 assert host.locator('select').input_value()==second
 # Malicious raw messages stay text.
 page.evaluate("pvData.summary.warning='<img src=x onerror=window.pwned=1>';pvData.history[0].reason='<script>window.pwned=1</script>'")
 host.locator('button[data-action=refresh]').click();page.wait_for_timeout(100)
 assert host.locator('.warning').inner_text().startswith('<img') and host.locator('img').count()==0
 assert page.evaluate('window.pwned||0')==0
 # Errors must not close dialog or blank prior evidence.
 page.evaluate('window.rejectPV=true');host.locator('button[data-action=refresh]').click();page.wait_for_timeout(100)
 assert 'offline' in host.locator('.status').inner_text() and host.locator('dialog').is_visible()
 page.evaluate('window.rejectPV=false')
 page.once('dialog',lambda d:d.dismiss());host.locator('button[data-action=reset]').click()
 assert page.evaluate('pvCalls.some(x=>x.reset_confirm===true)') is False
 page.once('dialog',lambda d:d.accept());host.locator('button[data-action=reset]').click();page.wait_for_timeout(100)
 assert page.evaluate('pvCalls.some(x=>x.reset_confirm===true)') is True
 # Late response after close must not reopen/overwrite.
 page.evaluate('window.pendingPV=true');host.locator('button[data-action=refresh]').click();page.wait_for_timeout(100)
 host.locator('button[data-action=close]').click();page.evaluate('resolvePV(structuredClone(pvData))');page.wait_for_timeout(100)
 assert not host.locator('dialog').is_visible()
 page.evaluate('window.pendingPV=false');page.locator('solar-pilot-card >> .pv-summary [data-action=pv_diagnostics]').click()
 page.wait_for_selector('solar-pilot-pv-dialog >> .metrics');page.keyboard.press('Escape')
 assert not host.locator('dialog').is_visible()
 # New form uses same help popup and keeps edits over live updates.
 page.evaluate('''()=>{c.hass={...c._hass,callApi:async(method,path,data)=>{if(method==='delete')return{};
 if(path==='config/config_entries/options/flow')return{type:'form',flow_id:'pv-flow',step_id:'pv_forecast',data_schema:[
 {name:'inverter_limit_w',required:true,selector:{number:{min:100,max:1000000,step:100}},default:10000},
 {name:'calibration_enabled',required:true,selector:{boolean:{}},default:true},
 {name:'learning_preset',required:true,selector:{select:{options:[{value:'normal',label:'Normaal'},{value:'slow',label:'Rustig'},{value:'responsive',label:'Vlotter'}]}},default:'normal'}]};
 return{type:'create_entry',title:'Fictief opgeslagen'};}};}''')
 page.locator('solar-pilot-card >> [data-action=configure]').first.click()
 form=page.locator('solar-pilot-options-dialog');page.wait_for_selector('solar-pilot-options-dialog >> [name=inverter_limit_w]')
 assert form.locator('[name=inverter_limit_w]').input_value()=='10000'
 form.locator('[name=calibration_enabled]').uncheck()
 form.locator('button[data-help=inverter_limit_w]').click()
 popup=form.locator('solar-pilot-option-help-dialog');assert popup.locator('dialog').is_visible()
 assert '13.800' not in popup.locator('dialog').inner_text() or '10.000' in popup.locator('dialog').inner_text()
 assert '98%' in popup.locator('dialog').inner_text()
 page.evaluate('''()=>{for(let i=0;i<80;i++){let a=structuredClone(c._last.attributes);a.grid_w=-500-i;c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}''')
 assert not form.locator('[name=calibration_enabled]').is_checked()
 assert popup.locator('dialog').is_visible()
 assert page.evaluate('deviceCalls.length')==0
 assert not errors,errors
 b.close()
print('PV UI: modal, curve/history, day selection, 320/390/768/1440, 80 updates, no repeated history polling, escaping, errors, confirmed reset, stale responses, real option help: OK')
