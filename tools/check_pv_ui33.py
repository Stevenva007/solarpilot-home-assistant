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
view_now=NOW+timedelta(days=9)
r.pv_forecast._last_local_now=view_now
r.pv_forecast.position=lambda dt:(190,35)
r.pv_forecast.cached={"available":True,"enabled":True,"status":"FICTIEVE VOORBEELDGEGEVENS · Forecast.Solar tijdreeks",
 "note":"Softwareproef, geen meting van jouw installatie.","updated":NOW.isoformat(),"model":m.summary(),"factor":.8,"confidence":.75,"comparable_days":9,
 "inverter_limit_w":10000,"panel_peak_wp":13800,"native_raw_now_w":3500,"curve_method":"Lineair geïnterpoleerde broncurve",
 "horizon":[{"hours":h,"raw_w":3500-h*400,"corrected_w":(3500-h*400)*.8,"factor":.8} for h in range(4)],
 "raw_remaining_today_kwh":9.5,"corrected_remaining_today_kwh":7.6,"corrected_tomorrow_kwh":15.4,
 "energy_methods":{"remaining_today":"Geïntegreerde vermogenscurve"}}
for row in r.pv_forecast.cached["horizon"]:
 row["calibration"]=r.pv_forecast.factor_details(view_now+timedelta(hours=row["hours"]),190,35)
r.pv_forecast.cached["calibration"]=r.pv_forecast.factor_details(view_now,190,35)
print(json.dumps(r.pv_forecast.diagnostics()))
'''
fixture=json.loads(subprocess.check_output([sys.executable,'-B','-c',fixture_script],cwd=ROOT,text=True))
# Explicit fictional UI evidence. This does not claim provider issue times or
# turn the model's current-error population into forward forecast accuracy.
fixture["forecast_evidence"] = {"version": 1, "summary": {
 "ahead_comparisons": 24, "distinct_days": 4,
 "by_recorded_lead": [{"label": "1–3 uur", "samples": 24, "distinct_days": 4, "mae_w": 900}],
 "planning_margin_comparison": {"status": "comparison_only", "margin_w": 500,
   "applied": False, "reason": "Fictieve vergelijking op een apart bewaarde laatste dag"}}}
latest_day = max(str(row["time"])[:10] for row in fixture["history"])
proof_quarter = next(row for row in reversed(fixture["history"]) if str(row["time"])[:10] == latest_day)
proof_quarter.update(accepted=False, reason="Fictief geweigerd: één ongeldige deelmeting",
 actual_w=580, raw_w=1700, corrected_w=1360, error_w=-1120, error_pct=-1120/1700*100,
 observation_evidence={"version": 1, "valid_observations": 8, "rejected_observations": 1,
  "rejection_reasons": [{"reason": "invalid", "count": 1}],
  "original_reports": {"distinct": 9, "max_gap_s": 30},
  "coverage_note": 'Fictief bronbewijs <img src=x onerror="window.proofInjected=true">'})
fixture["browser_fixture_quarter_time"] = proof_quarter["time"]
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
 assert host.locator('.pv-quarter-profile tbody tr').count()==12
 assert '16:00' in host.locator('.pv-quarter-profile').inner_text()
 assert 'Waarom deze factor?' in host.locator('.pv-quarter-profile').inner_text()
 assert 'Leerdagen totaal' in host.locator('dialog').inner_text()
 assert host.locator('svg').count()==1
 assert '10 kW' in host.locator('dialog').inner_text() and '13,8 kWp' in host.locator('dialog').inner_text()
 assert page.evaluate('deviceCalls.length')==0
 source_details = host.locator('details[data-pv-key="sources"]')
 assert source_details.count() == 1
 source_details.locator(':scope > summary').click()
 ahead_details = host.locator('details[data-pv-key="ahead"]')
 assert ahead_details.count() == 1
 ahead_details.locator(':scope > summary').click()
 assert '24 vergelijkingen uit 4 dagen' in ahead_details.inner_text()
 assert 'uitgiftetijd van de oorspronkelijke provider is onbekend' in ahead_details.inner_text()
 assert 'Niet toegepast' in ahead_details.inner_text() and '500 W' in ahead_details.inner_text()
 quarter_key = "quarter:" + fixture["browser_fixture_quarter_time"]
 quarter_details = host.locator(f'details[data-quarter-proof][data-pv-key="{quarter_key}"]')
 assert quarter_details.count() == 1
 assert quarter_details.get_attribute('data-pv-key') == quarter_key
 quarter_details.locator(':scope > summary').click()
 assert '8 geldig · 1 afgewezen · 9 verschillende bronrapporten' in quarter_details.inner_text()
 assert 'Ongeldige meting: 1' in quarter_details.inner_text()
 assert '30 s' in quarter_details.inner_text()
 assert '<img src=x' in quarter_details.inner_text(), 'original quarter proof must remain inert text'
 assert host.locator('img').count() == 0 and page.evaluate('window.proofInjected||false') is False
 page.evaluate('''()=>{c._pvDialog._scroll.scrollTop=650;window.oldScroll=c._pvDialog._scroll.scrollTop;window.oldDay=c._pvDialog._days.value;
  for(let i=0;i<80;i++){let a=structuredClone(c._last.attributes);a.grid_w=-300-i;c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}''')
 assert host.locator('dialog').is_visible()
 assert page.evaluate('Math.abs(c._pvDialog._scroll.scrollTop-oldScroll)<2 && c._pvDialog._days.value===oldDay')
 assert source_details.get_attribute('open') is not None
 assert ahead_details.get_attribute('open') is not None
 assert quarter_details.get_attribute('open') is not None
 assert page.evaluate('pvCalls.length')==1 # no periodic history fetch from 5s updates
 for width in (320,390,768,1440):
  page.set_viewport_size({'width':width,'height':1120})
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'),width
  assert host.locator('dialog').evaluate('e=>e.scrollWidth<=e.clientWidth+2'),width
 page.evaluate('c._pvDialog._scroll.scrollTop=0')
 host.locator('dialog').screenshot(path=str(OUT/'SolarPilot-beta33-PV-diagnose.png'))
 # Day changing and refresh preserve selected date/details.
 second=host.locator('select option').nth(1).get_attribute('value');host.locator('select').select_option(second)
 before_quarters = host.locator('table.history tbody tr').count()
 assert page.evaluate('''day=>{let removed=false;pvData.history=pvData.history.filter(row=>{
  if(!removed&&String(row.time).slice(0,10)===day){removed=true;return false;}return true;});return removed;}''', second)
 host.locator('button[data-action=refresh]').click();page.wait_for_timeout(100)
 assert host.locator('table.history tbody tr').count() == before_quarters-1, 'a changing quarter set must not move the source-details open state'
 assert host.locator('select').input_value()==second
 assert source_details.get_attribute('open') is not None, 'source details keep their own open state when quarter count changes'
 assert ahead_details.get_attribute('open') is not None, 'ahead evidence remains separate from day-specific quarters'
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
print('PV UI: modal, curve/history, semantic source details, ahead issue unknown, rejected original quarter proof, day selection, 320/390/768/1440, 80 updates, no repeated history polling, escaping, errors, confirmed reset, stale responses, real option help: OK')
