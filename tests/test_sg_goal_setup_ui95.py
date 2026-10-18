"""Explain missing calculated goals without changing native targets or permissions."""
from test_audit_ui79 import execute


def test_missing_sg_goal_is_explained_in_summary_and_main_heatpump_view():
    execute("""
const c=Object.create(SolarPilotCard.prototype);
let writes=0;const reportedAt=Date.now()/1000;
c._hass={config:{time_zone:'Europe/Brussels'},callService:()=>writes++};
c._heatpumpCalculatedGoal=()=>null;
for(const name of ['_heatpumpGraphic','_heatpumpBusiness','_sgStatusStrip',
 '_heatpumpPower','_heatpumpReason','_wallboxPriorityControl','_heatpumpHistoryButton',
 '_sgDetails'])c[name]=()=>'';
c._heatpumpPresentation=()=>({state:'inactive',known:true,active:false});
const context={sgBoost:{},panasonic:{source_stale_s:120,display_tank:{available:true,
 entity_id:'water_heater.fictional_tank',temperature_c:52,target_c:50,
 temperature_stamp:reportedAt,target_stamp:reportedAt},sg_tank_goal:{read_only:true,
 reason:'profile_unconfirmed',calculated_c:null}}};
for(const html of [c._heatpumpTankSummary(context),c._heatpump(context)]){
 assert.match(html,/50 °C/);assert.match(html,/data-sg-goal-setup/);
 assert.match(html,/Tapwaterpercentage en tankbron nog bevestigen/);
 assert.match(html,/normale Panasonic-doel/);
 assert.match(html,/data-config-step="sg_sources"/);
 assert.doesNotMatch(html,/57,5 °C/);
 const historyButtons=Array.from(html.matchAll(/<button[^>]*data-action="heatpump_source_history"[^>]*>/g),m=>m[0]);
 assert.equal(historyButtons.length,2);
 assert.ok(historyButtons.every(button=>button.includes('data-history-entity="water_heater.fictional_tank"')&&button.includes('data-history-source="display_tank"')));
 assert.deepEqual(new Set(historyButtons.map(button=>button.match(/data-history-role="([^"]+)"/)[1])),
  new Set(['tank_temperature_entity','tank_target_entity']),'A calculated SG goal is not an entity source');
}
context.panasonic.sg_tank_goal.reason='normal_target_unavailable';
assert.match(c._heatpumpGoalSetup(context),/normale boilerdoel ontbreekt of is niet actueel/);
context.panasonic.sg_tank_goal.reason='<img src=x onerror="bad()">';
assert.doesNotMatch(c._heatpumpGoalSetup(context),/<img/);
assert.equal(writes,0);
""")


def test_confirmed_goal_and_older_payload_do_not_require_new_setup():
    execute("""
const c=Object.create(SolarPilotCard.prototype);
c._heatpumpCalculatedGoal=()=>({value:57.5,label:'SG-doel bij AAN · berekend'});
assert.equal(c._heatpumpGoalSetup({panasonic:{sg_tank_goal:{read_only:true}}}),'');
c._heatpumpCalculatedGoal=()=>null;
assert.equal(c._heatpumpGoalSetup({panasonic:{}}),'');
""")
