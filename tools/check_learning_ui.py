"""Real dashboard/browser code with fictitious learning API responses, never HA."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
OUT=Path(os.environ.get('SOLARPILOT_SCREENSHOT_DIR','/tmp/solarpilot-browser-tests'));OUT.mkdir(parents=True,exist_ok=True)
# Build fixture from the real model/hub and explicit HA doubles, not hand-invented UI structure.
fixture_script='''
import sys,json,time
from datetime import datetime,timedelta,timezone
sys.path.insert(0,"tests")
import conftest
from test_learning_hub30 import metered
r,h=metered();m=r.unified_planner.base_load
now=datetime.now(timezone.utc);start=now-timedelta(days=60)
for i in range(60):
 for hour in (8,9,10,11,12,13,14,15,16,17):
  day=(start+timedelta(days=i)).replace(hour=hour)
  m.last_sample_wall=0;m.observe(day.timestamp(),day,500 if i<38 else 750)
r.learning_hub.latest_sample={"valid":True,"watts":200,"code":"measured","reason":"Fictief: betrouwbare meting tijdens EV-laden en ontvochtigen."}
r.learning_hub.days={now.date().isoformat():{"accepted":24,"accepted_corrected":12,"consumer_source":2}}
for i in range(48):
 r.unified_planner.quality.observe(wall_ts=now.timestamp()-14400+i*300,local_now=now-timedelta(seconds=14400-i*300),predicted_pv_w=2000,actual_pv_w=1400,predicted_base_w=800,actual_base_w=1500)
data=r.learning_hub.refresh();data["contract"]="FICTIEVE VOORBEELDGEGEVENS — geen meting van jouw woning. "+data["contract"]
print(json.dumps(data))
'''
fixture=json.loads(subprocess.check_output([sys.executable,'-B','-c',fixture_script],cwd=ROOT,text=True))
errors=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium'),headless=True,args=['--no-sandbox'])
    page=browser.new_page(viewport={'width':1440,'height':1080},locale='nl-BE')
    page.on('pageerror',lambda e:errors.append(str(e)))
    page.set_content((ROOT/'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'),wait_until='load')
    page.evaluate('''data=>{
      window.learningData=data; window.learningCalls=[];window.deviceCalls=[];
      window.c=document.querySelector('solar-pilot-card');const a=structuredClone(c._last.attributes);
      a.config_entry_id='fictieve-entry';a.learning_insights={ready:true,open_questions:data.questions.length};
      c.hass={...c._hass,user:{is_admin:true},callService:async(...args)=>{deviceCalls.push(args);throw Error('No device control');},
      callWS:async msg=>{learningCalls.push(msg);if(window.rejectNext){window.rejectNext=false;throw Error('stale_question: voorwaarden veranderd');}
        if(msg.type!=='solar_pilot/learning')throw Error('Unexpected command');
        if(msg.operation==='policy')learningData.policy[msg.setting]=msg.value;
        if(msg.operation==='answer')learningData.questions=learningData.questions.filter(q=>q.id!==msg.question);
        return structuredClone(learningData);},states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};
    }''',fixture)
    page.locator('solar-pilot-card >> .footer button[data-action=learning_hub]').click()
    host=page.locator('solar-pilot-learning-dialog')
    assert host.locator('dialog').is_visible()
    assert host.locator('.question').count()>=2
    assert host.locator('.model').count()==7
    assert 'FICTIEVE VOORBEELDGEGEVENS' in host.locator('dialog').inner_text()
    for key in ('sampling','adaptation','notifications'):
        host.locator(f'button[data-learning-help={key}]').click()
        help_host=page.locator('solar-pilot-option-help-dialog');assert help_host.locator('dialog').is_visible()
        assert ('SolarPilot '+__import__('json').loads((ROOT/'custom_components/solar_pilot/manifest.json').read_text())['version']) in help_host.locator('dialog').inner_text()
        help_host.locator('.close').click()
    host.locator('details[data-key=coverage] summary').click()
    host.locator('details[data-key=model-base] summary').click()
    page.evaluate('''()=>{c._learningDialog._scroll.scrollTop=540;window.pos=c._learningDialog._scroll.scrollTop;window.openKeys=Array.from(c._learningDialog._body.querySelectorAll('details[open]'),d=>d.dataset.key);}''')
    page.evaluate('''()=>{for(let i=0;i<80;i++){const a=structuredClone(c._last.attributes);a.grid_w=-1000-i;c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}''')
    assert host.locator('dialog').is_visible()
    assert page.evaluate('Math.abs(c._learningDialog._scroll.scrollTop-window.pos)<2')
    assert page.evaluate("JSON.stringify(window.openKeys)===JSON.stringify(Array.from(c._learningDialog._body.querySelectorAll('details[open]'),d=>d.dataset.key))")
    before=page.evaluate('learningCalls.length')
    page.evaluate('()=>c._learningDialog._read(true)')
    assert page.evaluate('learningCalls.length')==before+1
    assert page.evaluate('Math.abs(c._learningDialog._scroll.scrollTop-window.pos)<2')
    assert host.locator('details[data-key=model-base]').get_attribute('open') is not None
    # Inputs survive ordinary telemetry; changes only submitted after explicit save.
    host.locator('select[data-policy=adaptation]').select_option('automatic')
    page.evaluate('''()=>{for(let i=0;i<80;i++){const a=structuredClone(c._last.attributes);a.grid_w=-2000-i;c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}}''')
    assert host.locator('select[data-policy=adaptation]').input_value()=='automatic'
    assert page.evaluate("learningCalls.filter(x=>x.operation==='policy').length")==0
    host.locator('.save-policy').click()
    assert page.evaluate("learningCalls.filter(x=>x.operation==='policy').length")==1
    assert page.evaluate("learningCalls.at(-1).setting==='adaptation' && learningCalls.at(-1).value==='automatic'")
    # Stale revision reply is not silently accepted and doesn't send a retry/write.
    page.evaluate('window.rejectNext=true')
    button=host.locator('button[data-question]').first
    button.click();assert 'stale_question' in host.locator('.status').inner_text()
    assert page.evaluate('deviceCalls.length')==0
    # Render malicious data as plain text, never inject it as HTML.
    page.evaluate('''async()=>{learningData.models[0].name='<img src=x onerror="window.injected=true">';await c._learningDialog._read(true);}''')
    assert host.locator('img').count()==0 and not page.evaluate('window.injected||false')
    page.evaluate("learningData.models[0].name='Huishoudelijk restverbruik';learningData.policy.adaptation='assisted';c._learningDialog._scroll.scrollTop=0")
    page.evaluate('()=>c._learningDialog._read(true)')
    for width in (320,390,768,1440):
        page.set_viewport_size({'width':width,'height':1080 if width>540 else 860})
        assert host.locator('dialog').evaluate('e=>e.getBoundingClientRect().right<=innerWidth && e.getBoundingClientRect().left>=0')
        assert host.locator('.body').evaluate('e=>e.scrollWidth<=e.clientWidth+2')
        if width in (390,1440):page.screenshot(path=str(OUT/f'SolarPilot-beta30-leren-{width}.png'))
    host.locator('.close').click();assert not host.locator('dialog').is_visible()
    assert page.evaluate('c._learningDialog._timer===null')
    page.locator('solar-pilot-card >> .footer button[data-action=learning_hub]').click()
    page.keyboard.press('Escape');assert not host.locator('dialog').is_visible()
    assert page.evaluate('deviceCalls.length')==0 and not errors,errors
    browser.close()
print('OK: echte Leren & vragen-popup, 7 modules, antwoorden en revisies, 3 vraagtekens, expliciete beleidsopslag, foutafhandeling, 80 telemetrieupdates, scroll/details/invoer behouden, XSS, 320/390/768/1440 px, Esc/polling-opruiming, nul actuatoraanroepen. Alleen fictieve API/apparaten.')
