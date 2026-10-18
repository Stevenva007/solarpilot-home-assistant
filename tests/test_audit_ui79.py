"""Execute the shipped frontend in Node against isolated fictitious surfaces.

These probes exercise asynchronous control-flow races and renderer input
contracts; no Home Assistant, browser network or physical services are used.
"""
from pathlib import Path
import json
import shutil
import subprocess

import pytest

ROOT = Path(__file__).resolve().parents[1]
FRONTEND = ROOT / "custom_components/solar_pilot/frontend"


def execute(body, *, options=False, old_aliases=False, include_helpers=False):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to execute the shipped frontend")
    prelude = """
const assert=require('node:assert/strict');
globalThis.HTMLElement=class {};
globalThis.window={customCards:[]};
const definitions=new Map();
globalThis.customElements={get:key=>definitions.get(key),define:(key,value)=>definitions.set(key,value)};
globalThis.document={visibilityState:'visible'};
"""
    if old_aliases:
        prelude += """
for(const tag of ['solar-pilot-pv-dialog','solar-pilot-consumer-history-dialog','solar-pilot-priority-dialog',
  'solar-pilot-option-help-dialog','solar-pilot-options-dialog','solar-pilot-device-manager-dialog'])
  definitions.set(tag,class OldDialog extends HTMLElement{static solarPilotRelease='old-release';});
"""
    source = (FRONTEND / ("option-help.js" if options else "solar-pilot-card.js")).read_text()
    if include_helpers:
        source += "\n" + (FRONTEND / "option-help.js").read_text()
    probe = prelude + source + "\n(async()=>{\n" + body + "\n})().catch(error=>{console.error(error);process.exitCode=1;});"
    result = subprocess.run([node], input=probe, text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stdout + result.stderr
    return json.loads(result.stdout) if result.stdout.strip() else None


@pytest.mark.parametrize("invalid", [None, False, True, "", "  ", "unavailable", "Infinity", [], {}])
def test_unknown_and_non_numeric_metrics_are_not_zero(invalid):
    execute("""
const value=JSON.parse(%s);
for(const format of [spPower,spTemp,spEuro,spKwh,spPct,spDuration])assert.equal(format(value),'—');
""" % json.dumps(json.dumps(invalid)))


def test_non_finite_durations_and_metrics_remain_unknown():
    execute("""
for(const value of [NaN,Infinity,-Infinity])
  for(const format of [spPower,spTemp,spEuro,spKwh,spPct,spDuration])assert.equal(format(value),'—');
assert.equal(spPower(0),'0 W');assert.equal(spPower('0'),'0 W');
assert.equal(spPower(1200),'1,2 kW');assert.equal(spTemp(0),'0 °C');
assert.equal(spDuration(3660),'1u 1m');assert.equal(spDuration(-10),'0m');
assert.equal(SolarPilotConsumerHistoryDialog.prototype._duration(Infinity),'—');
assert.equal(SolarPilotCard.prototype._remainingTime(false),'nog niet bekend');
""")


def test_options_catalog_from_closed_entry_cannot_start_a_flow_after_reopen():
    execute("""
let resolveOld;
globalThis.SOLAR_PILOT_HELP_DATA=new Promise(resolve=>resolveOld=resolve);
const calls=[];
const dialog=Object.create(SolarPilotOptionsDialog.prototype);
Object.assign(dialog,{_open:false,_busy:false,_seq:0,content:{innerHTML:''},error:{textContent:''},
  dialog:{open:false,showModal(){this.open=true;},close(){this.open=false;}},
  _request:async function(path,data){calls.push(data.handler);this.flow={flow_id:'flow-'+data.handler,type:'menu'};}});
const hass={user:{is_admin:true},callApi:async()=>({})};
const first=dialog.open(hass,'entry-old');
await dialog.close(true);
globalThis.SOLAR_PILOT_HELP_DATA={entries:{},steps:{}};
await dialog.open(hass,'entry-current');
resolveOld({entries:{},steps:{}});await first;
assert.deepEqual(calls,['entry-current']);
assert.equal(dialog.flow.flow_id,'flow-entry-current');
assert.equal(dialog.entryId,'entry-current');
""", options=True)


def test_old_help_error_does_not_overwrite_new_help_after_reopen():
    execute("""
let rejectOld;
globalThis.SOLAR_PILOT_HELP_DATA=new Promise((_,reject)=>rejectOld=reject);
const nodes={h2:{textContent:''},'.body':{textContent:'',innerHTML:''}};
const dialog=Object.create(SolarPilotOptionHelpDialog.prototype);
Object.assign(dialog,{shadowRoot:{querySelector:key=>nodes[key]},
  dialog:{open:false,showModal(){this.open=true;},close(){this.open=false;}}});
const first=dialog.open('old','field','Old');dialog.close();
globalThis.SOLAR_PILOT_HELP_DATA={version:'fixture',entries:{'current.field':{title:'Current',paragraphs:['Current evidence']}}};
await dialog.open('current','field','Current');
rejectOld(new Error('Old request failed'));await first;
assert.equal(nodes.h2.textContent,'Current');
assert.notEqual(nodes['.body'].textContent,'Old request failed');
assert.match(nodes['.body'].innerHTML,/Current evidence/);
""", options=True)


@pytest.mark.parametrize("late_error", [False, True])
def test_old_options_request_after_disconnect_cannot_unlock_current_request(late_error):
    execute("""
globalThis.SOLAR_PILOT_HELP_DATA={entries:{},steps:{}};
for(const Dialog of [customElements.get('solar-pilot-options-dialog'),customElements.get(SP_BOUND_OPTIONS_TAG)]){
let resolveOld,rejectOld,resolveCurrent;const cleanups=[];
const oldHass={user:{id:'fixture',is_admin:true},callApi:async(method,path)=>
  method==='delete'?cleanups.push(['old',path]):new Promise((resolve,reject)=>{resolveOld=resolve;rejectOld=reject;})};
const newHass={user:{id:'fixture',is_admin:true},callApi:async(method,path)=>
  method==='delete'?cleanups.push(['current',path]):new Promise(resolve=>resolveCurrent=resolve)};
const dialog=Object.create(Dialog.prototype);
Object.assign(dialog,{_open:false,_busy:false,_seq:0,_controls:()=>{},_render:()=>{},
  content:{innerHTML:''},error:{textContent:''},
  dialog:{open:false,isModal:false,showModal(){
    if(this.open&&!this.isModal)throw new DOMException('Already open as non-modal','InvalidStateError');
    this.open=true;this.isModal=true;
  },close(){this.open=false;this.isModal=false;}}});
const old=dialog.open(oldHass,'entry-old');
await Promise.resolve();await Promise.resolve();assert.equal(dialog._busy,true);
// Native removal clears is-modal without removing the open attribute.
dialog.dialog.isModal=false;
dialog.disconnectedCallback();
assert.equal(dialog.dialog.open,false);assert.equal(dialog._busy,true);
const current=dialog.open(newHass,'entry-current');
await Promise.resolve();await Promise.resolve();assert.equal(dialog._busy,true);
assert.equal(dialog.dialog.open,true);assert.equal(dialog.dialog.isModal,true);
if(%s)rejectOld(new Error('Old request failed'));else resolveOld({flow_id:'old-flow',type:'menu'});
await old;assert.equal(dialog._busy,true);assert.notEqual(dialog.error.textContent,'Old request failed');
assert.equal(dialog.flow,null);
assert.equal(dialog.dialog.open,true);assert.equal(dialog.dialog.isModal,true);
resolveCurrent({flow_id:'current-flow',type:'menu'});await current;
assert.equal(dialog.flow.flow_id,'current-flow');assert.equal(dialog._busy,false);
assert.deepEqual(cleanups,%s?[]:[['old','config/config_entries/options/flow/old-flow']]);
}
""" % (str(late_error).lower(), str(late_error).lower()), options=True)


def test_old_back_delete_cannot_replace_reopened_options_flow():
    execute("""
globalThis.SOLAR_PILOT_HELP_DATA={entries:{},steps:{}};
let releaseDelete;const posts=[];
const hass={user:{id:'fixture',is_admin:true},callApi:async(method,path,data)=>{
  if(method==='delete')return new Promise(resolve=>releaseDelete=resolve);
  posts.push(data);return {flow_id:'current-flow',step_id:'init',type:'menu',menu_options:[]};}};
const dialog=Object.create(SolarPilotOptionsDialog.prototype);
Object.assign(dialog,{_open:true,_busy:false,_seq:0,_openEpoch:1,_menuPath:['energy_hub'],
  _formParent:[],_dirty:false,_draftStarted:false,hass,entryId:'entry-old',
  flow:{flow_id:'old-flow',step_id:'energy_hub',type:'menu'},_controls:()=>{},_render:()=>{},
  content:{innerHTML:''},error:{textContent:''},
  dialog:{open:true,showModal(){this.open=true;},close(){this.open=false;}}});
const back=dialog._back();assert.equal(dialog._busy,true);
dialog.disconnectedCallback();await dialog.open(hass,'entry-current');
assert.equal(dialog.flow.flow_id,'current-flow');
releaseDelete({});await back;
assert.deepEqual(posts,[{handler:'entry-current'}]);
assert.equal(dialog.flow.flow_id,'current-flow');
""", options=True)


def test_expired_overview_energy_is_refreshed_without_new_hass_state():
    execute("""
const stamp=Date.now()/1000;
const card=Object.create(SolarPilotCard.prototype);
const replacements=[];
const tiles={pv:{replaceWith(node){replacements.push(['pv',node.html]);}},grid:{replaceWith(node){replacements.push(['grid',node.html]);}}};
globalThis.document={visibilityState:'visible',createElement:()=>({
  set innerHTML(value){this.firstElementChild={html:value};},get innerHTML(){return ''},
  querySelector(){return null;}})};
Object.assign(card,{isConnected:true,_view:'overview',_last:{state:'fixture',attributes:{
  energy_display:{stale_s:120,inverter_limit_w:5000,pv:{value_w:800,reported_at:stamp},grid:{value_w:250,reported_at:stamp}}}},
  shadowRoot:{querySelector:()=>({setAttribute(){}})},
  _content:{querySelector:key=>key==='[data-energy="pv"]'?tiles.pv:key==='[data-energy="grid"]'?tiles.grid:null},
  _captureUiState:()=>null,_restoreUiState:()=>{},_heatpumpDisplaySignature:()=> 'same',
  _decisionBoard:()=>'',_ctx(){return {a:this._last.attributes}}});
card._observationSignature='same';
assert.match(card._energyTile('pv',card._last.attributes),/800 W/);
const clock=Date.now;Date.now=()=>Math.floor((stamp+121)*1000);
card._refreshObservationDisplay();Date.now=clock;
assert.equal(replacements.length,2);
for(const [,html] of replacements)assert.match(html,/Actuele meting ontbreekt/);
""")


def test_learning_quality_uses_current_profile_days_instead_of_global_days():
    execute(r"""
const dialog=Object.create(SolarPilotLearningDialog.prototype);
Object.assign(dialog,{_hass:{config:{time_zone:'Europe/Brussels'}},_scroll:{scrollTop:0},
  _body:{innerHTML:'',querySelectorAll:()=>[]}});
dialog._render({models:[{id:'pv',evidence:{forecast_calibration:{model:{days:12,minimum_days_required:5},
  calibration:{days:2,minimum_days_required:5,reason:'Current quarter needs more days'},confidence:0.2}}}]});
assert.match(dialog._body.innerHTML,/2\/5 passende dagen/);
assert.match(dialog._body.innerHTML,/12 leerdagen totaal/);
assert.doesNotMatch(dialog._body.innerHTML,/12\/5 geldige dagen/);
""")


def test_wallbox_profile_labels_match_sg_is_extra_lower_priority_policy():
    execute("""
const card=Object.create(SolarPilotCard.prototype);card._question=()=>'';
const text=card._wallboxProfile({charging_profile:{phases:1,max_current_a:10,maximum_power_w:2300}});
assert.doesNotMatch(text,/extra SG-zonneboost houdt voorrang voor de Wallbox/);
assert.match(text,/SG-zonneboost gebruikt alleen/);
""")


def test_unknown_power_is_not_rendered_as_measured_zero():
    execute("""
const card=Object.create(SolarPilotCard.prototype);
for(const value of [null,false,true,'',[],{},Infinity])
  assert.match(card._knownPower(value),/Vermogen nog niet bekend/);
assert.match(card._knownPower(0),/0 W/);
""")


def test_wallbox_activity_expires_from_original_power_report():
    execute("""
const card=Object.create(SolarPilotCard.prototype);card._last={state:'fixture',attributes:{}};
const stamp=Date.now()/1000,wb={activity_known:true,power_w:1800,stale_s:120,
  activity_details:{current:{known:true,report_timestamp:stamp}}};
assert.equal(card._wallboxActivity(wb).active,true);
const clock=Date.now;Date.now=()=>Math.floor((stamp+121)*1000);
assert.deepEqual(card._wallboxActivity(wb),{known:false,active:false,label:'LAADSTATUS ONBEKEND'});
Date.now=clock;
""")


@pytest.mark.parametrize("state,restored", [("unknown", False), ("unavailable", False), ("fixture", True)])
def test_explicitly_unavailable_or_restored_snapshot_does_not_confirm_device_activity(state, restored):
    execute("""
const card=Object.create(SolarPilotCard.prototype);
card._last={state:%s,attributes:{restored:%s}};
const device=card._deviceActivity({available:true,on:true});
assert.equal(device.known,false);assert.equal(device.active,false);assert.equal(device.label,'STATUS ONBEKEND');
assert.doesNotMatch(card._startExplanation({available:true,on:true},'solar'),/Waarom dit toestel nu actief is/);
const wallbox=card._wallboxActivity({activity_known:true,power_w:1800});
assert.equal(wallbox.known,false);assert.equal(wallbox.active,false);
""" % (json.dumps(state), str(restored).lower()))


def test_current_bundle_uses_current_dialogs_when_old_stable_aliases_remain():
    execute("""
const created=[];
globalThis.document={createElement:tag=>{
  created.push(tag);return {_dialog:{open:false},dialog:{open:false},open(){this._dialog.open=true;this.dialog.open=true;},
    close(){},addEventListener(){},dataset:{}};
}};
const card=Object.create(SolarPilotCard.prototype);
Object.assign(card,{_hass:{user:{is_admin:true}},_last:{attributes:{config_entry_id:'fixture'}},isConnected:true,
  shadowRoot:{appendChild(){},append(){}},_uiHistory:{prepare(){},track(){}}});
card._openPV();card._openHistory({id:'fixture-device'});card._openPriorities();
await card._openHelp('settings','reserve_w');await card._openDevices();await card._openOptions();
assert.equal(created.length,6);
for(const tag of created){assert.match(tag,new RegExp(SP_DIALOG_RELEASE+'$'));
  assert.equal(customElements.get(tag).solarPilotRelease,SP_CARD_VERSION);}
for(const tag of ['solar-pilot-option-help-dialog','solar-pilot-options-dialog','solar-pilot-device-manager-dialog'])
  assert.equal(customElements.get(tag).solarPilotRelease,'old-release');
const history=Object.create(SolarPilotUiHistory.prototype);
history.modals=new Map([['fixture',{element:{localName:SP_OPTIONS_DIALOG_TAG,_busy:true,dialog:{open:true}}}]]);
assert.equal(history._canClose(['fixture']),false);
""", old_aliases=True, include_helpers=True)


@pytest.mark.parametrize("class_name,open_field", [("SolarPilotConsumerHistoryDialog", "_isOpen"), ("SolarPilotPVDialog", "_open")])
def test_queued_native_close_event_does_not_cancel_reopened_dialog(class_name, open_field):
    execute("""
const callbacks=new Map(),dialog={open:true,addEventListener:(type,fn)=>callbacks.set(type,fn)};
const node={addEventListener(){},textContent:'',innerHTML:''};
document.createElement=()=>({textContent:''});
HTMLElement.prototype.attachShadow=function(){this.shadowRoot={innerHTML:'',addEventListener(){},
  append(){},querySelector:key=>key==='dialog'?dialog:node};};
HTMLElement.prototype.dispatchEvent=()=>{};
document.removeEventListener=()=>{};globalThis.CustomEvent=class {};
const popup=new %s();popup.%s=true;popup._seq=7;
callbacks.get('close')();
assert.equal(popup.%s,true);assert.equal(popup._seq,7);
""" % (class_name, open_field, open_field))


def test_final_start_allocation_is_not_replaced_by_optimistic_solar_pool():
    execute(r"""
const card=Object.create(SolarPilotCard.prototype);card._last={state:'fixture',attributes:{}};
const allocation={available_w:0,required_w:380,sufficient:false,filtered_free_w:2500,
  instant_free_w:2700,smoothing_hold_w:200,protected_cycle_reserve_w:2100,higher_allocated_w:400,
  remaining_solar_w:0,remaining_cap_w:4800};
const device={kind:'switch',mode:'auto',available:true,on:false,start_requirements:{allocated_start_power:{met:false,...allocation}},
  start_diagnostics:{summary:'Wacht op vermogen / hogere prioriteit',missing:['allocated_start_power'],
    power:{measurement_valid:true,required_start_w:380,measured_free_w:2700,allocation,
      solar_start_pool:{available_solar_w:3000,wallbox_solar_w:300,lower_loads_releasable_w:0}}}};
const html=card._startExplanation(device,'solar');
assert.match(html,/Beschikbaar voor dit toestel <b>0 W<\/b>/);
assert.match(html,/Toegelaten zonnepot vóór eindtoewijzing <b>3 kW<\/b>/);
assert.match(html,/Reserve voor lopende beschermde cycli/);assert.match(html,/2,1 kW/);
assert.match(html,/Tijdelijk achtergehouden door vermogensfilter/);assert.match(html,/200 W/);
assert.doesNotMatch(html,/Nog ongeveer 380 W (vrije zonnestroom|zonnevermogen)/);
""")


def test_reported_power_shortfall_after_reservations_is_not_called_missing_sun():
    execute("""
const card=Object.create(SolarPilotCard.prototype);card._last={state:'fixture',attributes:{}};
const device={kind:'switch',mode:'auto',available:true,on:false,
  start_diagnostics:{summary:'Wacht op vermogen / hogere prioriteit',power:{measurement_valid:true,
    required_start_w:500,measured_free_w:2900,allocation:{available_w:180,required_w:500,sufficient:false,
      filtered_free_w:2700,protected_cycle_reserve_w:2300,remaining_cap_w:180}}}};
const html=card._startExplanation(device,'solar');
assert.doesNotMatch(html,/Nog ongeveer 320 W vrije zonnestroom nodig/);
assert.match(html,/Nog ongeveer 320 W beschikbaar startvermogen nodig/);
assert.match(html,/Elektrisch budget na reserves en eerdere toewijzingen/);
""")
