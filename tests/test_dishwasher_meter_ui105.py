"""Run the actual JS class methods with an inert DOM, never HA services."""
import json
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT=Path(__file__).parents[1]

@pytest.mark.skipif(shutil.which('node') is None, reason='Node is required for actual frontend method checks')
def test_meter_frontend_readonly_cloud_independent_and_stale():
    code=r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const classes=new Map();
const ctx={console,Date,Intl,window:{},HTMLElement:class{},customElements:{get:n=>classes.get(n),define:(n,c)=>classes.set(n,c)}};
vm.createContext(ctx);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),ctx);
const c=Object.create(classes.get('solar-pilot-card').prototype);
c._last={state:'running',attributes:{}};
const now=Date.now()/1000;
const meter={active:true,source:'meter',power_valid:true,power_w:1800,observed_at:now,power_reported_at:now,stale_s:120,energy_valid:true,energy_total_kwh:10,energy_today_kwh:.3,energy_reported_at:now};
const d={id:'fixture',kind:'dishwasher',name:'Test dishwasher',available:false,isolated:true,on:false,history:{meter},dishwasher:{ready:false,attempted:false}};
assert.equal(c._deviceActivity(d).active,true);assert.equal(c._dishwasherMeter(d).power_w,1800);
c._deviceAvailabilityRetry=()=>({label:'Tijdelijk niet bereikbaar'});c._startExplanation=()=>'';c._sourceHistoryButton=()=>'';
const html=c._dishwasherCard(d,'solar');
assert.ok(html.includes('ACTIVITEIT GEMETEN'));assert.ok(html.includes('eigen meter'));
assert.match(html,/data-action="dishwasher_arm"[^>]*disabled/);
assert.ok(!html.includes('data-action="manual_stop"'));
let invalid={...meter,power_reported_at:now-121};
assert.equal(c._dishwasherMeter({...d,history:{meter:invalid}}),null);
assert.equal(c._deviceActivity({...d,history:{meter:invalid}}).active,false);
c._last.attributes.restored=true;assert.equal(c._dishwasherMeter(d),null);
c._last={state:'unavailable',attributes:{}};assert.equal(c._dishwasherMeter(d),null);
c._last={state:'running',attributes:{}};
assert.equal(c._dishwasherMeter({...d,kind:'switch'}),null);
assert.equal(c._dishwasherMeter({...d,history:{meter:{...meter,power_w:true}}}),null);
assert.equal(c._dishwasherMeter({...d,history:{meter:{...meter,power_w:NaN}}}),null);
assert.equal(c._dishwasherMeter({...d,history:{meter:{...meter,observed_at:now+60}}}),null);
console.log('Meter frontend cases passed');
'''
    result=subprocess.run(['node','-e',code,str(ROOT/'custom_components/solar_pilot/frontend/solar-pilot-card.js')],capture_output=True,text=True)
    assert result.returncode==0,result.stdout+'\n'+result.stderr
