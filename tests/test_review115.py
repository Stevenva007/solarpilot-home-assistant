"""Independent options-routing and context probes with fictitious surfaces."""
import ast
import json
from pathlib import Path

import pytest

from test_audit_ui79 import execute


ROOT = Path(__file__).resolve().parents[1]


def backend_menus():
    """Read the shipped outer menu graph instead of duplicating it in a fixture."""
    tree = ast.parse((ROOT / "custom_components/solar_pilot/config_flow.py").read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "SolarPilotOptions")
    result = {}
    for method in cls.body:
        if not isinstance(method, ast.AsyncFunctionDef):
            continue
        for node in ast.walk(method):
            if (not isinstance(node, ast.Call)
                    or not isinstance(node.func, ast.Attribute)
                    or node.func.attr != "async_show_menu"):
                continue
            args = {item.arg: item.value for item in node.keywords}
            if isinstance(args.get("menu_options"), ast.List):
                result[ast.literal_eval(args["step_id"])] = ast.literal_eval(args["menu_options"])
    return result


@pytest.mark.parametrize("step,expected", [
    (None, []),
    ("battery", ["storage_hub", "battery"]),
    ("wallbox", ["storage_hub", "wallbox"]),
    ("battery_analysis", ["storage_hub", "battery_analysis"]),
    ("sg_boost", ["comfort_hub", "sg_boost"]),
    ("sg_sources", ["comfort_hub", "sg_sources"]),
    ("sg_advanced", ["comfort_hub", "sg_advanced"]),
    ("manage_device", ["loads_hub", "manage_device"]),
    ("edit", ["loads_hub", "edit"]),
    ("water", ["water"]),
])
def test_card_shortcuts_follow_the_actual_backend_menu_graph(step, expected):
    execute("""
const menus=%s,expected=%s,step=%s;
const calls=[];
const options={open:async(hass,entry,route)=>{
  assert.equal(entry,'fictional-entry');
  let current='init';
  for(const item of route){
    assert.ok(menus[current]?.includes(item.next_step_id),
      `Backend menu ${current} has no ${item.next_step_id} entry`);
    current=item.next_step_id;
  }
  calls.push(route.map(item=>item.next_step_id));
}};
const card=Object.create(SolarPilotCard.prototype);
Object.assign(card,{isConnected:true,_optionsDialog:options,
  _hass:{user:{id:'fictional-admin',is_admin:true}},
  _last:{attributes:{config_entry_id:'fictional-entry'}},
  _uiHistory:{prepare(){},track(){}},_loadOptionHelpers:async()=>{},
  _render(){throw Error('A valid shortcut must not fall back after a route error');}});
await card._openOptions(step);
assert.deepEqual(calls,[expected]);
""" % (json.dumps(backend_menus()), json.dumps(expected), json.dumps(step)))


@pytest.mark.parametrize("change", ["user", "permission", "entry", "entry_missing"])
def test_options_context_is_invalidated_before_hass_identity_is_replaced(change):
    execute("""
const change=%s,calls=[];
const oldUser={id:'fictional-admin-a',is_admin:true};
const previous={state:'current',attributes:{config_entry_id:'fictional-entry-a'}};
const oldHass={user:oldUser,states:{'sensor.fictional':previous}};
const nextState={state:'updated',attributes:{config_entry_id:change==='entry'?'fictional-entry-b':'fictional-entry-a'}};
if(change==='entry_missing')delete nextState.attributes.config_entry_id;
const newHass={user:change==='user'?{id:'fictional-admin-b',is_admin:true}:
  change==='permission'?{id:oldUser.id,is_admin:false}:oldUser,
  states:{'sensor.fictional':nextState}};
let optionHass=oldHass;
const options={invalidateContext(){
  assert.equal(optionHass,oldHass,'Old flow must be invalidated under its original context');
  calls.push('invalidate');
},set hass(value){optionHass=value;calls.push('hass');}};
const card=Object.create(SolarPilotCard.prototype);
Object.assign(card,{_hass:oldHass,_entity:'sensor.fictional',_last:previous,_config:{},
  _optionsDialog:options,shadowRoot:{activeElement:null},
  _invalidateSgManualRequest(){},_invalidateWallboxPriorityRequest(){},
  _anchorWallboxPriorityClock(){},_viewRenderSignature(){return '';},_render(){}});
card.hass=newHass;
assert.deepEqual(calls,['invalidate','hass']);
assert.equal(optionHass,newHass);
""" % json.dumps(change))


def test_ordinary_telemetry_update_keeps_the_open_form_context():
    execute("""
const user={id:'fictional-admin',is_admin:true},calls=[];
const previous={state:'current',attributes:{config_entry_id:'fictional-entry'}};
const next={state:'updated',attributes:{config_entry_id:'fictional-entry'}};
const options={invalidateContext(){calls.push('invalidate');},set hass(value){calls.push('hass');}};
const card=Object.create(SolarPilotCard.prototype);
Object.assign(card,{_hass:{user,states:{'sensor.fictional':previous}},
  _entity:'sensor.fictional',_last:previous,_config:{},_optionsDialog:options,
  shadowRoot:{activeElement:null},_invalidateSgManualRequest(){},_invalidateWallboxPriorityRequest(){},
  _anchorWallboxPriorityClock(){},_viewRenderSignature(){return '';},_render(){}});
card.hass={user,states:{'sensor.fictional':next}};
assert.deepEqual(calls,['hass']);
""")


def test_reconfiguring_card_invalidates_an_old_options_context():
    execute("""
const calls=[],card=Object.create(SolarPilotCard.prototype);
Object.assign(card,{_optionsDialog:{invalidateContext(){calls.push('invalidate');}},
  _invalidateSgManualRequest(){},_invalidateWallboxPriorityRequest(){}});
card.setConfig({entity:'sensor.fictional-new'});
assert.deepEqual(calls,['invalidate']);
assert.equal(card._entity,'sensor.fictional-new');
""")


@pytest.mark.parametrize("busy", [False, True])
def test_invalidating_options_clears_draft_and_uses_the_original_flow_account(busy):
    execute("""
const deletes=[],oldHass={user:{id:'fictional-old-admin',is_admin:true},callApi:async(method,path)=>{
  assert.equal(method,'delete');deletes.push(path);
}};
const newHass={user:{id:'fictional-new-admin',is_admin:true},callApi:async()=>{
  throw Error('An invalidated draft cannot use the replacement account');
}};
window.confirm=()=>{throw Error('Context invalidation must not offer to keep another context draft');};
const dialog=Object.create(SolarPilotOptionsDialog.prototype);
Object.assign(dialog,{hass:newHass,_flowHass:oldHass,entryId:'fictional-old-entry',
  _open:true,_busy:%s,_seq:12,_openEpoch:3,_dirty:true,_draftStarted:true,
  flow:{flow_id:'fictional-old-flow',step_id:'battery_marstek'},
  _entityChoices:new Map([['power_entity',[{id:'sensor.fictional_old',label:'Old choice'}]]]),
  _menuPath:['storage_hub','battery'],_formParent:['storage_hub','battery'],
  content:{innerHTML:'private draft'},error:{textContent:'private error'},
  dialog:{open:true,close(){this.open=false;}},_stopViewport(){},
  helpDialog:{close(){}}});
dialog.invalidateContext();
assert.equal(dialog._open,false);assert.equal(dialog._busy,false);assert.equal(dialog.dialog.open,false);
assert.equal(dialog._dirty,false);assert.equal(dialog._draftStarted,false);
assert.equal(dialog._seq,13);assert.equal(dialog._openEpoch,4);assert.equal(dialog.flow,null);
assert.equal(dialog._entityChoices.size,0);assert.equal(dialog._flowHass,null);
assert.deepEqual(dialog._menuPath,[]);assert.deepEqual(dialog._formParent,[]);
assert.equal(dialog.content.innerHTML,'');assert.equal(dialog.error.textContent,'');
await dialog._request('config/config_entries/options/flow',{handler:'fictional-old-entry'});
await Promise.resolve();await Promise.resolve();
assert.deepEqual(deletes,['config/config_entries/options/flow/fictional-old-flow']);
""" % str(busy).lower(), options=True)


@pytest.mark.parametrize("late_error", [False, True])
def test_late_old_options_reply_cannot_restore_a_context_after_invalidation(late_error):
    execute("""
globalThis.SOLAR_PILOT_HELP_DATA={entries:{},steps:{}};
let resolveOld,rejectOld,resolveNew;const rendered=[],posts=[],deletes=[];
const oldHass={user:{id:'fictional-old',is_admin:true},callApi:async(method,path,data)=>{
  if(method==='delete'){deletes.push(path);return {};}
  posts.push(data);return new Promise((resolve,reject)=>{resolveOld=resolve;rejectOld=reject;});
}};
const newHass={user:{id:'fictional-new',is_admin:true},callApi:async(method,path,data)=>{
  assert.equal(method,'post');posts.push(data);return new Promise(resolve=>resolveNew=resolve);
}};
const dialog=Object.create(SolarPilotOptionsDialog.prototype);
Object.assign(dialog,{_open:false,_busy:false,_seq:0,_controls(){},_captureDraft(){return null;},
  _viewport(){},_stopViewport(){},_render(){rendered.push(this.flow.flow_id);},
  content:{innerHTML:''},error:{textContent:''},
  dialog:{open:false,showModal(){this.open=true;},close(){this.open=false;}}});
const old=dialog.open(oldHass,'fictional-old-entry');
await Promise.resolve();await Promise.resolve();assert.equal(dialog._busy,true);
dialog.invalidateContext();
const current=dialog.open(newHass,'fictional-new-entry');
await Promise.resolve();await Promise.resolve();assert.equal(dialog._busy,true);
if(%s)rejectOld(new Error('Old context error'));else resolveOld({flow_id:'fictional-old-flow',type:'menu'});
await old;
assert.equal(dialog._busy,true);assert.equal(dialog.flow,null);
assert.notEqual(dialog.error.textContent,'Old context error');
resolveNew({flow_id:'fictional-new-flow',type:'menu'});await current;
assert.deepEqual(rendered,['fictional-new-flow']);assert.equal(dialog.flow.flow_id,'fictional-new-flow');
assert.deepEqual(posts,[{handler:'fictional-old-entry'},{handler:'fictional-new-entry'}]);
assert.deepEqual(deletes,%s?[]:['config/config_entries/options/flow/fictional-old-flow']);
""" % (str(late_error).lower(), str(late_error).lower()), options=True)


def test_enter_on_existing_entity_does_not_replace_it_with_an_alphabetical_neighbor():
    execute(r"""
const stored='sensor.fictional_60',attrs={};
const list={hidden:true,innerHTML:'',querySelectorAll(){
  return [...this.innerHTML.matchAll(/<button\b([^>]*)>[\s\S]*?<\/button>/g)].map(match=>{
    const attributes=Object.fromEntries([...match[1].matchAll(/([\w-]+)="([^"]*)"/g)].map(a=>[a[1],a[2]]));
    return {dataset:{entityChoice:attributes['data-entity-choice']},
      getAttribute:name=>attributes[name]??null,setAttribute:(name,value)=>attributes[name]=value};
  });
}};
const picker={querySelector:()=>list};
const input={id:'option-0',name:'power_entity',disabled:false,value:'Fictional 60',
  dataset:{kind:'entity',entityValue:stored},closest:()=>picker,
  setAttribute:(name,value)=>attrs[name]=value,getAttribute:name=>attrs[name]??null,
  removeAttribute:name=>delete attrs[name]};
const choices=Array.from({length:65},(_,i)=>({id:`sensor.fictional_${String(i).padStart(2,'0')}`,
  label:`Fictional ${String(i).padStart(2,'0')}`}));
const dialog=Object.create(SolarPilotOptionsDialog.prototype);
Object.assign(dialog,{_busy:false,_entityChoices:new Map([['power_entity',choices]]),
  content:{querySelectorAll:()=>[input]},_sizeEntities(){},
  _chooseEntity(button){input.dataset.entityValue=button.dataset.entityChoice;}});
dialog._showEntities(input);
dialog._entityKey({target:input,key:'Enter',preventDefault(){},stopPropagation(){}});
assert.equal(input.dataset.entityValue,stored,
  'Inspecting a stored source and pressing Enter must keep that source, even beyond the first 50 options');
""", options=True)
