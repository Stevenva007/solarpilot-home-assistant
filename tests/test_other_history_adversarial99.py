"""Independent read-only history/navigation probes against the shipped card.

These execute real JavaScript with isolated DOM doubles, without HA or devices.
"""
import json

import pytest

from test_audit_ui79 import execute


PRELUDE = r"""
globalThis.CustomEvent=class {constructor(type,options={}){this.type=type;Object.assign(this,options);}};
document.removeEventListener=()=>{};document.addEventListener=()=>{};
const pending=()=>{let resolve,reject;const promise=new Promise((a,b)=>{resolve=a;reject=b;});return {promise,resolve,reject};};
const catalogue=(kind='consumer',item='load',sources=[{role:'power',label:'Recorded power source',entity_id:'sensor.fictional_power'}])=>({
 schema:1,read_only:true,scope:'current_configured_sources',kind,...(kind==='wallbox'?{}:{item_id:item}),
 name:'Fictional source catalogue',sources,note:'Current bindings only.'});
const sourceDialog=(send)=>{
 const d=Object.create(SolarPilotSourceHistoryDialog.prototype),events=[];
 Object.assign(d,{_seq:0,_isOpen:false,_data:null,_busy:false,_body:{innerHTML:'',textContent:'',querySelectorAll:()=>[]},
  _statusEl:{textContent:''},_dialog:{open:false,showModal(){this.open=true;},close(){this.open=false;}},
  shadowRoot:{querySelector:()=>({focus:()=>{}})},dispatchEvent:e=>events.push(e)});
 const hass={user:{id:'fictional-user',is_admin:false},callWS:send,callService:()=>{throw Error('Actuator write');},
  callApi:()=>{throw Error('Unapproved API');},states:{'sensor.fictional_power':{state:'9876'}}};
 return {d,hass,events};
};
const consumerDialog=()=>{
 const d=Object.create(SolarPilotConsumerHistoryDialog.prototype),events=[];
 Object.assign(d,{_seq:0,_isOpen:true,_inflight:0,_lastFetch:0,_day:null,_entryId:'entry',_deviceId:'load',
  _body:{innerHTML:'',querySelector:()=>null,querySelectorAll:()=>[]},_scroll:{scrollTop:0},_input:{value:''},
  _device:{id:'load',reason:'CURRENT REASON',power_w:9876},_hass:{states:{'sensor.fictional_power':{state:'9876'}}},
  _status:()=>{},_renderData:()=>{},_syncScrub:()=>{},dispatchEvent:e=>events.push(e),
  shadowRoot:{querySelector:()=>({disabled:false,textContent:''})}});
 return {d,events};
};
const historyData=()=>({date:'2026-10-17',today:'2026-10-18',first_date:'2026-10-01',name:'Fictional historical load',
 timezone:'Europe/Brussels',day_start:1792188000,day_end:1792274400,day_seconds:86400,on_s:60,generated_at:'2026-10-18T10:00:00Z',
 sessions:[{id:9,start:'2026-10-17T09:00:00Z',segment_start:'2026-10-17T09:00:00Z',segment_end:'2026-10-17T09:01:00Z',
  duration_s:60,start_source:'unknown',stop_source:'unknown',start_confirmed:false,stop_confirmed:false,
  start_reason:'Retained uncertain start',stop_reason:'Observation interrupted',ongoing:false}],
 events:[{at:'2026-10-17T09:02:00Z',kind:'command',reason:'Request issued; execution not confirmed'}]});
"""


def probe(body):
    return execute(PRELUDE + body)


@pytest.mark.parametrize("change", [
    {"schema": 2}, {"read_only": False}, {"read_only": 1}, {"scope": "historical_sources"},
    {"kind": "battery"}, {"item_id": "another-load"}, {"sources": None},
    {"actuator": "switch.fictional"}, {"sources": [{}] * 41},
])
def test_untrusted_catalogue_envelope_cannot_authorize_a_source(change):
    probe("""
const {d}=sourceDialog();d._kind='consumer';d._itemId='load';
assert.throws(()=>d._validated({...catalogue(),...JSON.parse(%s)}));
assert.equal(d.permits('sensor.fictional_power'),false);
""" % json.dumps(json.dumps(change)))


def test_malformed_source_rows_do_not_hide_valid_neighbours_or_supply_current_values():
    probe(r"""
const {d,hass}=sourceDialog();d._kind='consumer';d._itemId='load';d._hass=hass;d._isOpen=true;d._identity=d._userKey();
const rows=[{role:'power',label:'Safe source',entity_id:'sensor.fictional_power'},null,
 {role:'power',label:'Bad link',entity_id:'javascript:alert(1)'},
 {role:'power',label:'Injected field',entity_id:'sensor.injected',current_value:9876},
 {role:false,label:'Malformed',entity_id:'sensor.malformed'},
 {role:'target',label:'<img src=x onerror=alert(1)>',entity_id:'number.fictional_target'}];
const before=JSON.stringify(rows);d._data=d._validated(catalogue('consumer','load',rows));d._render();
assert.equal(JSON.stringify(rows),before);assert.equal(d._data.sources.length,2);
assert.equal(d.permits('sensor.injected'),false);assert.equal(d.permits('sensor.fictional_power'),true);
assert.doesNotMatch(d._body.innerHTML,/<img|9876|current_value/);
assert.match(d._body.innerHTML,/&lt;img/);assert.match(d._body.innerHTML,/Recorder/);
assert.match(d._body.innerHTML,/target="_blank" rel="noopener noreferrer"/);
""")


def test_wallbox_catalogue_rejects_an_item_id_from_another_subject_namespace():
    probe("""
const {d}=sourceDialog();d._kind='wallbox';d._itemId=undefined;
assert.throws(()=>d._validated({...catalogue('wallbox'),item_id:'load'}));
assert.equal(d._validated(catalogue('wallbox')).kind,'wallbox');
""")


@pytest.mark.parametrize("kind,item", [("consumer", "load"), ("battery", "battery"), ("wallbox", None)])
def test_catalogue_request_has_only_read_scope_and_current_subject(kind, item):
    probe("""
const requests=[],kind=%s,item=%s;
const {d,hass,events}=sourceDialog(async msg=>{requests.push(msg);return catalogue(kind,item);});
d.open(hass,'entry',kind,item);while(d._busy)await Promise.resolve();
assert.deepEqual(requests,[{type:'solar_pilot/source_history',config_entry_id:'entry',kind,
 ...(kind==='wallbox'?{}:{item_id:item})}]);
assert.equal(events.length,0);assert.match(d._body.innerHTML,/geen toestelopdracht/);
d.close();assert.equal(d.permits('sensor.fictional_power'),false);
""" % (json.dumps(kind), json.dumps(item)))


@pytest.mark.parametrize("changed", ["entity", "role", "revoked"])
def test_selection_requires_freshly_revalidated_same_role_and_entity(changed):
    probe("""
const mode=%s,requests=[];let calls=0;
const {d,hass,events}=sourceDialog(async msg=>{requests.push(msg);calls++;
 if(calls===1)return catalogue();
 return catalogue('consumer','load',mode==='revoked'?[]:[{role:mode==='role'?'status':'power',label:'New binding',
 entity_id:mode==='entity'?'sensor.replacement':'sensor.fictional_power'}]);});
d.open(hass,'entry','consumer','load');while(d._busy)await Promise.resolve();
await d._fetch(0);assert.equal(requests.length,2);assert.equal(events.length,0);
assert.match(d._statusEl.textContent,/koppeling is gewijzigd/);
assert.equal(d.permits('sensor.replacement'),mode==='entity');
""" % json.dumps(changed))


@pytest.mark.parametrize("late_error", [False, True])
def test_reopened_catalogue_rejects_old_reply_and_cannot_unlock_new_request(late_error):
    probe("""
const old=pending(),current=pending(),requests=[];
const {d,hass,events}=sourceDialog(msg=>{requests.push(msg);return requests.length===1?old.promise:current.promise;});
d.open(hass,'entry','consumer','load');d.close();d.open(hass,'entry','battery','battery');
const newSeq=d._seq;assert.equal(d._busy,true);
if(%s)old.reject(Error('OLD ERROR'));else old.resolve(catalogue());
await Promise.resolve();await Promise.resolve();await Promise.resolve();
assert.equal(d._seq,newSeq);assert.equal(d._busy,true);assert.equal(d._data,null);
assert.notEqual(d._statusEl.textContent,'OLD ERROR');assert.equal(events.length,0);
current.resolve(catalogue('battery','battery'));while(d._busy)await Promise.resolve();
assert.equal(d._data.kind,'battery');assert.equal(d._data.item_id,'battery');
""" % str(late_error).lower())


@pytest.mark.parametrize("change", ["user", "admin", "entry", "disconnect"])
def test_context_change_or_detach_cannot_show_late_catalogue_or_authorize_old_source(change):
    probe("""
const request=pending(),mode=%s;const {d,hass,events}=sourceDialog(()=>request.promise);
d.open(hass,'entry','consumer','load');
if(mode==='disconnect')d.disconnectedCallback();
else d.updateContext({...hass,user:{...hass.user,...(mode==='user'?{id:'different'}:mode==='admin'?{is_admin:true}:{})}},mode==='entry'?'new-entry':'entry');
request.resolve(catalogue());await Promise.resolve();await Promise.resolve();await Promise.resolve();
assert.equal(d._isOpen,false);assert.equal(d._dialog.open,false);assert.equal(d._data,null);
assert.equal(d.permits('sensor.fictional_power'),false);assert.equal(events.length,0);
""" % json.dumps(change))


def test_selected_source_without_binding_change_dispatches_history_intent_only_once():
    probe("""
let calls=0;const refresh=pending();
const {d,hass,events}=sourceDialog(async()=>++calls===1?catalogue():refresh.promise);
d.open(hass,'entry','consumer','load');while(d._busy)await Promise.resolve();
const first=d._fetch(0);await d._fetch(0);assert.equal(calls,2);assert.equal(events.length,0);
refresh.resolve(catalogue());await first;
assert.equal(events.length,1);assert.equal(events[0].type,'source-history-open');
assert.deepEqual(events[0].detail,{entityId:'sensor.fictional_power',entryId:'entry',userKey:d._identity});
""")


def test_consumer_unknown_gap_and_recorded_command_never_borrow_current_power_or_execution():
    probe("""
const {d}=consumerDialog();d._data=historyData();
d._setScrub(Date.parse('2026-10-17T09:02:00Z')/1000,{snap:false});
let html=d._scrubReadoutHtml();assert.match(html,/Onbekend bij deze tijd/);assert.match(html,/bewijst geen UIT/);
assert.doesNotMatch(html,/9876|CURRENT REASON|AAN-periode geregistreerd|0 W/);
const event=d._data.events[0];d._historySelection={kind:'event',key:d._historyItemKey(event,'event')};
html=d._scrubReadoutHtml();assert.match(html,/Request issued; execution not confirmed/);
assert.match(html,/Geregistreerde gebeurtenis/);assert.doesNotMatch(html,/AAN-periode geregistreerd|9876/);
""")


def test_confirmed_stop_is_half_open_and_unconfirmed_end_stays_distinct_from_active_claim():
    probe("""
const {d}=consumerDialog();d._data=historyData();const row=d._data.sessions[0],end=Date.parse(row.segment_end)/1000;
row.stop_confirmed=true;assert.equal(d._consumerSessionAt(end),undefined);
row.stop_confirmed=false;assert.equal(d._consumerSessionAt(end),row);
d._setScrub(end,{snap:false});const html=d._scrubReadoutHtml();
assert.match(html,/Einde onbekend/);assert.match(html,/Observation interrupted/);
assert.doesNotMatch(html,/Stop waargenomen|Nog geen stop bevestigd|CURRENT REASON/);
""")


@pytest.mark.parametrize("late_error", [False, True])
def test_consumer_day_change_cannot_accept_old_result_or_clear_current_inflight(late_error):
    probe("""
const {d}=consumerDialog(),old=pending(),current=pending(),requests=[];
d._data=historyData();d._hass.callWS=msg=>{requests.push(msg);return requests.length===1?old.promise:current.promise;};
const first=d._fetch(true);d._selectDay('2026-10-16');const latest=d._inflight;
assert.equal(requests[1].date,'2026-10-16');
if(%s)old.reject(Error('OLD ERROR'));else old.resolve({...historyData(),date:'2026-10-17'});
await first;assert.equal(d._inflight,latest);assert.equal(d._day,'2026-10-16');
assert.equal(d._scrubBounds(),null);
current.resolve({...historyData(),date:'2026-10-16'});while(d._inflight)await Promise.resolve();
assert.equal(d._data.date,'2026-10-16');assert.equal(d._input.value,'2026-10-16');
""" % str(late_error).lower())


def test_consumer_close_and_device_switch_reject_old_request():
    probe("""
const {d}=consumerDialog(),old=pending(),current=pending();let calls=0;
d._hass.callWS=()=>++calls===1?old.promise:current.promise;const first=d._fetch(true);d._cleanup();
d._isOpen=true;d._deviceId='new-load';d._data=null;const second=d._fetch(true);
old.resolve(historyData());await first;assert.equal(d._data,null);assert.equal(d._deviceId,'new-load');
current.resolve({...historyData(),name:'New load'});await second;assert.equal(d._data.name,'New load');
""")


def test_consumer_keyboard_and_vertical_touch_keep_unknown_and_do_not_select_current_values():
    probe("""
const {d}=consumerDialog();d._data=historyData();const lane={getBoundingClientRect:()=>({left:0,width:864}),
 closest:()=>lane};const target={closest:()=>lane};let prevented=0;
d._scrubKeydown({target,key:'Home',preventDefault:()=>prevented++});
assert.equal(d._scrub.at,d._data.day_start);assert.match(d._scrubReadoutHtml(),/Onbekend bij deze tijd/);
d._scrubKeydown({target,key:'ArrowRight',shiftKey:true,preventDefault:()=>prevented++});
assert.equal(d._scrub.at,d._data.day_start+900);assert.equal(prevented,2);
const before=JSON.stringify(d._scrub);d._scrubPointerDown({target,button:0,isPrimary:true,pointerId:1,pointerType:'touch',clientX:20,clientY:10});
d._scrubPointerMove({target,pointerId:1,pointerType:'touch',clientX:21,clientY:30});
d._scrubPointerUp({target,pointerId:1,pointerType:'touch',clientX:21,clientY:30});
assert.equal(JSON.stringify(d._scrub),before);assert.equal(d._scrubPointer,null);
d._scrubPointerDown({target,button:0,isPrimary:true,pointerId:2,pointerType:'touch',clientX:30,clientY:10});
d._scrubPointerUp({target,pointerId:2,pointerType:'touch',clientX:30,clientY:10});
assert.match(d._scrubReadoutHtml(),/Onbekend bij deze tijd/);assert.doesNotMatch(d._scrubReadoutHtml(),/9876|0 W/);
""")


@pytest.mark.parametrize("changed", ["detach", "entry", "user", "new-catalogue", "new-modal", "newer-intent", "none"])
def test_native_history_wait_rechecks_identity_and_does_not_override_a_new_catalogue(changed):
    probe("""
const mode=%s,{d,hass}=sourceDialog(async msg=>catalogue(msg.kind,msg.item_id)),events=[],frames=[];
d._hass=hass;d._entryId='entry';d._kind='consumer';d._itemId='load';d._isOpen=true;
d._identity=d._userKey();d._data=catalogue();d._dialog.open=true;
const card=Object.create(SolarPilotCard.prototype);Object.assign(card,{isConnected:true,_hass:hass,
 _last:{attributes:{config_entry_id:'entry'}},_sourceHistoryDialog:d,_historyDialog:{close:()=>{}},
 _uiHistory:{layers:[],prepare:()=>{},track:()=>{}},dispatchEvent:event=>events.push(event)});
SolarPilotUiHistory.bus.pending={waiting:true};SolarPilotUiHistory.bus.moving=false;SolarPilotUiHistory.bus.applying=false;
globalThis.requestAnimationFrame=callback=>frames.push(callback);
const intent=card._openNativeSourceHistory({entityId:'sensor.fictional_power',entryId:'entry',userKey:d._identity});
assert.equal(d._isOpen,false);assert.equal(frames.length,1);assert.equal(events.length,0);
if(mode==='detach')card.isConnected=false;
else if(mode==='entry')card._last.attributes.config_entry_id='other-entry';
else if(mode==='user')hass.user.id='other-user';
else if(mode==='new-catalogue')card._openSourceHistory('battery','battery');
else if(mode==='new-modal')card._uiHistory.layers.push('newly-opened-dialog');
else if(mode==='newer-intent')card._nativeHistorySeq++;
SolarPilotUiHistory.bus.pending=null;frames.shift()();await intent;
assert.equal(events.length,mode==='none'?1:0);
if(mode==='none'){
 assert.equal(events[0].type,'hass-more-info');assert.deepEqual(events[0].detail,{entityId:'sensor.fictional_power',view:'history'});
 assert.equal(events[0].bubbles,true);assert.equal(events[0].composed,true);
}
if(mode==='new-catalogue'){while(d._busy)await Promise.resolve();assert.equal(d._isOpen,true);assert.equal(d._kind,'battery');}
""" % json.dumps(changed))


@pytest.mark.parametrize("changed", ["entry", "user", "not-permitted", "closed"])
def test_native_history_rejects_forged_or_no_longer_permitted_intents(changed):
    probe("""
const mode=%s,{d,hass}=sourceDialog(),events=[];d._hass=hass;d._isOpen=true;d._identity=d._userKey();d._data=catalogue();
const card=Object.create(SolarPilotCard.prototype);Object.assign(card,{isConnected:true,_hass:hass,
 _last:{attributes:{config_entry_id:'entry'}},_sourceHistoryDialog:d,dispatchEvent:e=>events.push(e)});
const detail={entityId:'sensor.fictional_power',entryId:'entry',userKey:d._identity};
if(mode==='entry')detail.entryId='other-entry';else if(mode==='user')detail.userKey='forged';
else if(mode==='not-permitted')detail.entityId='switch.unlisted';else d.close();
await card._openNativeSourceHistory(detail);assert.equal(events.length,0);
""" % json.dumps(changed))


def test_wallbox_interruption_keeps_unknown_end_without_current_power_status_or_cause_fallback():
    probe(r"""
const card=Object.create(SolarPilotCard.prototype);card._hass={config:{time_zone:'Europe/Brussels'}};
const event={observed_start_at:1792227600,start_confirmed:false,last_charging_report_at:1792227600,
 previous_power_w:1800,unavailable_observed_at:1792227660,stop_confirmed:false,cause_reported:false,
 power_w:null,stop_report_at:null,status_report_at:null,native_status:'',stop_reason:'Retained telemetry gap'};
const before=JSON.stringify(event),wb={power_w:9876,reported_mode:'CURRENT MODE',reason:'CURRENT POLICY',
 activity_details:{current:{known:true,native_status:'CURRENT STATUS',reason:'CURRENT REASON'},history:[event]}};
const html=card._wallboxPeriodHtml(event,'fictional');assert.equal(JSON.stringify(event),before);
assert.match(html,/Einde onbekend \/ meetonderbreking/);assert.match(html,/Bij eerste controle al aan het laden/);
assert.match(html,/Retained telemetry gap/);assert.match(html,/1,8 kW/);assert.match(html,/Niet bewaard/);
assert.doesNotMatch(html,/Stop waargenomen|CURRENT|9876|9,9 kW|0 W|kWh/);
assert.match(html,/geen continue vermogensreeks of berekend sessieverbruik/);
const all=card._wallboxExplanation(wb,{known:false,active:false},'fictional');
const historical=all.slice(all.indexOf('<details class="wb-stop-history"'));
assert.doesNotMatch(historical,/CURRENT|9876|9,9 kW/);assert.match(historical,/Retained telemetry gap/);
assert.equal(JSON.stringify(wb.activity_details.history[0]),before);
""")


@pytest.mark.parametrize("value", ["null", "false", "true", "'0'", "-1", "NaN", "Infinity", "{}", "[]"])
def test_malformed_wallbox_boundary_report_values_remain_unknown_without_epoch_or_fake_zero(value):
    probe(r"""
const card=Object.create(SolarPilotCard.prototype);card._hass={config:{time_zone:'Europe/Brussels'}};
const bad=%s,event={observed_start_at:bad,last_charging_report_at:bad,observed_stop_at:bad,stop_report_at:bad,
 status_report_at:bad,previous_power_w:bad,power_w:bad,stop_confirmed:false,start_confirmed:false};
const html=card._wallboxPeriodHtml(event);assert.match(html,/tijdstip onbekend/);
assert.doesNotMatch(html.replace(/<[^>]+>/g,''),/1970|0 W|NaN|Infinity/);assert.match(html,/<b>—<\/b>/);
""" % value)


def test_wallbox_actual_zero_at_confirmed_stop_is_distinct_from_missing_reports():
    probe("""
const card=Object.create(SolarPilotCard.prototype);card._hass={config:{time_zone:'Europe/Brussels'}};
const event={observed_start_at:1792227600,last_charging_report_at:1792227600,observed_stop_at:1792227660,
 stop_report_at:1792227659,status_report_at:null,previous_power_w:1800,power_w:0,stop_confirmed:true,
 start_confirmed:true,cause_reported:false,stop_reason:'No precise physical cause reported'};
const html=card._wallboxPeriodHtml(event);assert.match(html,/Stop waargenomen/);assert.match(html,/Begin waargenomen/);
assert.match(html,/0 W/);assert.match(html,/geen betrouwbare precieze stopoorzaak/);
assert.doesNotMatch(html,/SolarPilot heeft|herstart|kWh|1970/);
""")


def test_wallbox_repeated_dst_hour_preserves_distinct_report_offsets_and_escapes_retained_text():
    probe(r"""
const card=Object.create(SolarPilotCard.prototype);card._hass={config:{time_zone:'Europe/Brussels'}};
const event={observed_start_at:Date.parse('2026-10-25T02:30:00+02:00')/1000,
 last_charging_report_at:Date.parse('2026-10-25T02:30:00+02:00')/1000,
 observed_stop_at:Date.parse('2026-10-25T02:30:00+01:00')/1000,stop_confirmed:true,
 stop_reason:'<img src=x onerror=alert(1)>',native_status:'<script>evil()</script>'};
const before=JSON.stringify(event),html=card._wallboxPeriodHtml(event,'\" onmouseover=evil()');
assert.match(html,/02:30:00 GMT\+2/);assert.match(html,/02:30:00 GMT\+1/);
assert.doesNotMatch(html,/<img|<script|data-ui-key="" onmouseover=/);
assert.match(html,/&lt;img/);assert.match(html,/&lt;script/);assert.equal(JSON.stringify(event),before);
""")


@pytest.mark.parametrize("value", ["null", "false", "true", "''", "'unavailable'", "NaN", "Infinity", "{}", "[]"])
def test_unknown_tank_value_cannot_become_a_clickable_current_history_reading(value):
    probe("""
const html=spTankHistoryValue(%s,{entity:'water_heater.fictional_tank',source:'display_tank',role:'tank_temperature_entity'});
assert.equal(html,'—');assert.doesNotMatch(html,/<button|data-action/);
""" % value)


@pytest.mark.parametrize("binding", [
    None, {}, {"entity": "water_heater.fictional_tank", "source": "other", "role": "tank_temperature_entity"},
    {"entity": "water_heater.fictional_tank", "source": "display_tank", "role": "calculated_sg_goal"},
    {"entity": "water_heater.fictional_tank\" onmouseover=evil()", "source": "display_tank", "role": "tank_target_entity"},
    {"entity": "javascript:alert(1)", "source": "configured", "role": "tank_target_entity"},
])
def test_tank_history_link_requires_closed_role_source_and_valid_entity(binding):
    probe("""
const binding=JSON.parse(%s),before=JSON.stringify(binding),html=spTankHistoryValue(50,binding);
assert.equal(html,'50 °C');assert.doesNotMatch(html,/<button|data-action|onmouseover/);
assert.equal(JSON.stringify(binding),before);
""" % json.dumps(json.dumps(binding)))


@pytest.mark.parametrize("source,role", [("display_tank", "tank_temperature_entity"), ("configured", "tank_target_entity")])
def test_tank_history_button_retains_exact_current_binding_without_device_command(source, role):
    probe("""
const html=spTankHistoryValue(0,{entity:'water_heater.fictional_tank',source:%s,role:%s});
assert.match(html,/type="button"/);assert.match(html,/0 °C/);assert.match(html,/data-action="heatpump_source_history"/);
assert.match(html,/data-history-entity="water_heater.fictional_tank"/);
assert.ok(html.includes('data-history-source="'+%s+'"'));assert.ok(html.includes('data-history-role="'+%s+'"'));
assert.doesNotMatch(html,/callService|toggle|set_temperature/);
""" % (json.dumps(source), json.dumps(role), json.dumps(source), json.dumps(role)))


def test_tank_history_binding_follows_actual_display_precedence_and_source_freshness():
    probe("""
const now=1792227600;Date.now=()=>now*1000;
const card=Object.create(SolarPilotCard.prototype),p={source_stale_s:120,temperature_c:41,target_c:49,
 temperature_stamp:now-2,target_stamp:now-3,temperature_entity:'sensor.fictional_temperature',target_entity:'sensor.fictional_target',
 display_tank:{available:true,entity_id:'water_heater.fictional_tank',temperature_c:52,target_c:50,temperature_stamp:now-4,target_stamp:now-5}};
const c={panasonic:p},before=JSON.stringify(c);
assert.deepEqual(card._heatpumpTankObservation(c,'temperature_c'),{value:52,entity:'water_heater.fictional_tank',
 source:'display_tank',role:'tank_temperature_entity',reportedAt:now-4});
assert.deepEqual(card._heatpumpTankObservation(c,'target_c'),{value:50,entity:'water_heater.fictional_tank',
 source:'display_tank',role:'tank_target_entity',reportedAt:now-5});
assert.equal(JSON.stringify(c),before);
p.display_tank.temperature_stamp=now-1000;
assert.deepEqual(card._heatpumpTankObservation(c,'temperature_c'),{value:41,entity:'sensor.fictional_temperature',
 source:'configured',role:'tank_temperature_entity',reportedAt:now-2});
p.temperature_stamp=now-1000;assert.deepEqual(card._heatpumpTankObservation(c,'temperature_c'),{value:null});
card._last={state:'solar',attributes:{restored:true}};
assert.deepEqual(card._heatpumpTankObservation(c,'target_c'),{value:null});
""")


@pytest.mark.parametrize("source", ["display_tank", "configured"])
def test_boiler_direct_history_request_has_closed_source_scope_and_no_item_id(source):
    probe("""
const source=%s,requests=[],{d,hass,events}=sourceDialog(async msg=>{requests.push(msg);
 return {...catalogue('wallbox'),kind:'heatpump',sources:[{role:'tank_temperature_entity',label:'Temperature',entity_id:'water_heater.fictional_tank'}]};});
d.open(hass,'entry','heatpump',undefined,{source,role:'tank_temperature_entity',expectedEntity:'water_heater.fictional_tank'});
while(d._busy)await Promise.resolve();
assert.deepEqual(requests,[{type:'solar_pilot/source_history',config_entry_id:'entry',kind:'heatpump',source}]);
assert.equal(Object.hasOwn(requests[0],'item_id'),false);assert.equal(events.length,1);
assert.equal(events[0].type,'source-history-open');assert.equal(events[0].detail.entityId,'water_heater.fictional_tank');
assert.throws(()=>d._validated({...d._data,item_id:'injected-consumer'}));
""" % json.dumps(source))


@pytest.mark.parametrize("mode", ["rebound", "wrong-role", "revoked", "ambiguous", "malformed"])
def test_boiler_direct_intent_cannot_open_other_source_or_fallback_catalogue(mode):
    probe("""
const mode=%s,correct={role:'tank_temperature_entity',label:'Tank temperature',entity_id:'water_heater.fictional_tank'},
 other={role:'tank_target_entity',label:'Other safe role',entity_id:'water_heater.other_tank'};
let rows=mode==='revoked'?[other]:mode==='wrong-role'?[{...correct,role:'tank_target_entity'},other]:
 mode==='rebound'?[{...correct,entity_id:'water_heater.replacement'},other]:mode==='ambiguous'?[correct,{...correct,entity_id:'water_heater.replacement'}]:
 [{...correct,raw_temperature:52},other];
const {d,hass,events}=sourceDialog(async()=>({...catalogue('wallbox'),kind:'heatpump',sources:rows}));
d.open(hass,'entry','heatpump',undefined,{source:'display_tank',role:'tank_temperature_entity',expectedEntity:'water_heater.fictional_tank'});
while(d._busy)await Promise.resolve();assert.equal(events.length,0);assert.equal(d._data.sources.length,0);
assert.equal(d.permits('water_heater.other_tank'),false);assert.equal(d.permits('water_heater.replacement'),false);
assert.match(d._statusEl.textContent,/geen andere bron geopend/);assert.doesNotMatch(d._body.innerHTML,/href=|data-source-index/);
""" % json.dumps(mode))


@pytest.mark.parametrize("options", [
    {}, {"source": "auto", "role": "tank_temperature_entity", "expectedEntity": "water_heater.fictional_tank"},
    {"source": "display_tank", "role": "calculated_sg_goal", "expectedEntity": "water_heater.fictional_tank"},
    {"source": "configured", "role": "tank_target_entity", "expectedEntity": "javascript:alert(1)"},
])
def test_card_cannot_open_unbound_or_injected_boiler_history(options):
    probe("""
const card=Object.create(SolarPilotCard.prototype);let opens=0;
Object.assign(card,{_last:{attributes:{config_entry_id:'entry'}},_sourceHistoryDialog:{open:()=>opens++},
 _uiHistory:{prepare:()=>{throw Error('Unexpected navigation');},track:()=>{}},_nativeHistorySeq:7});
card._openSourceHistory('heatpump',undefined,JSON.parse(%s));assert.equal(opens,0);assert.equal(card._nativeHistorySeq,7);
""" % json.dumps(json.dumps(options)))


@pytest.mark.parametrize("late_error", [False, True])
def test_same_heatpump_kind_reopen_with_other_source_rejects_old_direct_intent(late_error):
    probe("""
const old=pending(),current=pending(),requests=[],{d,hass,events}=sourceDialog(msg=>{requests.push(msg);return requests.length===1?old.promise:current.promise;});
d.open(hass,'entry','heatpump',undefined,{source:'display_tank',role:'tank_temperature_entity',expectedEntity:'water_heater.old_tank'});
d.open(hass,'entry','heatpump',undefined,{source:'configured',role:'tank_temperature_entity',expectedEntity:'sensor.fictional_temperature'});
if(%s)old.reject(Error('OLD SOURCE ERROR'));else old.resolve({...catalogue('wallbox'),kind:'heatpump',sources:[{role:'tank_temperature_entity',label:'Old',entity_id:'water_heater.old_tank'}]});
await Promise.resolve();await Promise.resolve();await Promise.resolve();
assert.equal(d._busy,true);assert.equal(events.length,0);assert.equal(d._data,null);assert.notEqual(d._statusEl.textContent,'OLD SOURCE ERROR');
current.resolve({...catalogue('wallbox'),kind:'heatpump',sources:[{role:'tank_temperature_entity',label:'Current',entity_id:'sensor.fictional_temperature'}]});
while(d._busy)await Promise.resolve();assert.equal(events.length,1);assert.equal(events[0].detail.entityId,'sensor.fictional_temperature');
assert.equal(d.permits('water_heater.old_tank'),false);assert.equal(requests[0].source,'display_tank');assert.equal(requests[1].source,'configured');
""" % str(late_error).lower())


@pytest.mark.parametrize("mode", ["matching-current", "different-stamp", "different-value", "historical-day", "capture-expired", "source-expired"])
def test_heatpump_history_links_only_matching_current_reading_never_archived_or_scrub_values(mode):
    probe("""
const mode=%s,now=Date.parse('2026-10-17T09:00:00Z')/1000;Date.now=()=>now*1000;
const d=Object.create(SolarPilotHeatpumpHistoryDialog.prototype),point={current:true,captured_at:now,capture_stale_s:30,stale_s:120,
 temperature_c:52,ordinary_target_c:50,temperature_reported_at:now-3,ordinary_target_reported_at:now-5};
d._data={date:'2026-10-17',today:'2026-10-17',timezone:'Europe/Brussels',tank_temperature:{schema:1,current:point,points:[{...point,current:false}]}};
d._device={tank_sources:{temperature_c:{value:52,entity:'water_heater.fictional_tank',source:'display_tank',role:'tank_temperature_entity',reportedAt:now-3},
 target_c:{value:50,entity:'water_heater.fictional_tank',source:'display_tank',role:'tank_target_entity',reportedAt:now-5}}};
if(mode==='different-stamp'){d._device.tank_sources.temperature_c.reportedAt--;d._device.tank_sources.target_c.reportedAt--;}
else if(mode==='different-value'){d._device.tank_sources.temperature_c.value=53;d._device.tank_sources.target_c.value=51;}
else if(mode==='historical-day')d._data.today='2026-10-18';
else if(mode==='capture-expired')point.captured_at=now-1000;
else if(mode==='source-expired'){point.temperature_reported_at=now-1000;point.ordinary_target_reported_at=now-1000;}
const before=JSON.stringify(d._data),html=d._tankHistoryHtml();
assert.equal((html.match(/data-action="heatpump_source_history"/g)||[]).length,mode==='matching-current'?2:0);
assert.equal(JSON.stringify(d._data),before);
d._data.day_start=now-3600;d._data.day_end=now+82800;d._data.day_seconds=86400;
d._data.native_evidence={schema:1,read_only:true,points:[{captured_at:now,source_stale_s:120,
 tank:{temperature_c:52,ordinary_target_c:50,temperature_reported_at:now-3,ordinary_target_reported_at:now-5}}]};
d._scrub={date:d._data.date,at:now,pointAt:now};
const scrub=d._scrubReadoutHtml();assert.match(scrub,/52 °C/);assert.match(scrub,/50 °C/);
assert.doesNotMatch(scrub,/data-action="heatpump_source_history"|data-history-entity/);
""" % json.dumps(mode))


def test_calculated_sg_preview_never_inherits_real_tank_history_link():
    probe("""
const card=Object.create(SolarPilotCard.prototype),now=Date.now()/1000;
card._heatpumpCalculatedGoal=()=>({label:'SG-doel · berekend',value:57.5});card._heatpumpGoalSetup=()=>'';
const html=card._heatpumpTankSummary({panasonic:{source_stale_s:120,display_tank:{available:true,
 entity_id:'water_heater.fictional_tank',temperature_c:52,target_c:50,temperature_stamp:now-3,target_stamp:now-5}}});
assert.equal((html.match(/data-action="heatpump_source_history"/g)||[]).length,2);
const computed=html.slice(html.indexOf('SG-doel · berekend'));assert.match(computed,/57,5 °C/);
assert.doesNotMatch(computed,/<button|data-history-entity/);
""")
