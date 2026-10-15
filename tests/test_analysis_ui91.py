"""Execute new analysis renderers with fictitious evidence and no device calls."""
from pathlib import Path
import json

import pytest

from test_audit_ui79 import execute


@pytest.mark.parametrize("state", ["transient_wait", "excluded", "source_unusable"])
def test_sampling_status_is_separate_from_counted_exclusions_and_escaped(state):
    execute("""
const d=Object.create(SolarPilotLearningDialog.prototype);
const samplingState=%s;
Object.assign(d,{_scroll:{scrollTop:17},_hass:{config:{time_zone:'Europe/Brussels'}},
 _body:{innerHTML:'',querySelectorAll:()=>[]}});
let calls=0;d._hass.callService=()=>calls++;
d._render({ready:true,models:[],sampling:{last:{reason:'Old generic reason'},
 status:{state:samplingState,reason:'Fictieve leerwacht <img src=x onerror="bad()">',
   started_at:2000000000,ends_at:2000000120,remaining_s:100},
 exclusions_7d:{settling_attempts:3,heatpump_unknown_attempts:488,
   other_heatpump_context_attempts:11,note:'Kwartierpogingen, geen gemeten uren.'}}});
const html=d._body.innerHTML;
assert.ok(html.includes('data-sampling-state="'+samplingState+'"'));
assert.match(html,/stabilisatiewacht: 3/);assert.match(html,/warmtepompcontext: 488/);
assert.match(html,/overige warmtepompcontext: 11/);
assert.doesNotMatch(html,/<img/);assert.match(html,/&lt;img/);
assert.doesNotMatch(html,/Langer wachten verhelpt/);
if(samplingState==='transient_wait')assert.match(html,/100 s resterend/);
if(samplingState==='excluded')assert.match(html,/staat los van een korte stabilisatiewacht/);
assert.equal(calls,0);assert.equal(d._scroll.scrollTop,17);
""" % json.dumps(state))


def test_pv_lead_cohorts_keep_daylight_unique_targets_and_dependency_separate():
    execute("""
const d=Object.create(SolarPilotPVDialog.prototype);
const html=d._forecastEvidenceHtml({version:1,summary:{ahead_comparisons:173,
 unique_targets:100,distinct_days:2,by_recorded_lead:[{label:'3–12 uur',samples:173}],
 lead_cohort_evidence:{version:1,unique_targets:60,distinct_days:2,pending_selections:8,
  selection_reason:'Eerste bron <img src=x onerror="bad()">',
  dependency_reason:'Reeksen delen dezelfde oorspronkelijke meetkwartieren.',
  by_recorded_lead:[{label:'0–1 uur',samples:13,unique_targets:13,distinct_days:2,
   mae_w:500,bias_w:-90,conditions:[{condition:'daylight',samples:7,
     unique_targets:7,distinct_days:2,mae_w:900,bias_w:-300}]}]}}});
assert.match(html,/data-pv-lead-cohorts/);
assert.match(html,/60 unieke doelkwartieren/);assert.match(html,/8 vastgelegde voorspellingen/);
assert.match(html,/Daglicht/);assert.match(html,/Unieke doelen/);
assert.match(html,/Reeksen delen dezelfde oorspronkelijke meetkwartieren/);
assert.match(html,/niet achteraf ingevuld/);assert.doesNotMatch(html,/<img/);
assert.match(html,/&lt;img/);assert.doesNotMatch(html,/globaal optimum|bewezen besparing/);
""")


def test_sg_rearm_details_keep_original_stop_and_current_gate_escaped():
    execute("""
const c=Object.create(SolarPilotCard.prototype);c._hass={config:{time_zone:'Europe/Brussels'}};
for(const name of ['_sgConfirmation','_sgTransportDetails','_heatpumpTechnicalDetails',
 '_sgCoolingDetails','_sgObservation'])c[name]=()=>'';
for(const name of ['_sgWaitProgress','_sgMinimumProgress','_sgCloudProgress',
 '_electricalLimits','_heatpumpTankValue'])c[name]=()=>null;
c._sgDisplayStates=()=>({});c._panasonicSourceFresh=()=>false;
const html=c._sgDetails({sgBoost:{profile:'general',rearm_wait:{
 original_stop_reason:'Oude stop na netafname <img>',
 current_condition:'Nieuwe sessie wacht op voldoende actuele zon'}},panasonic:{}});
assert.match(html,/Oorspronkelijke stopreden/);assert.match(html,/Oude stop na netafname &lt;img&gt;/);
assert.match(html,/Actuele herstartvoorwaarde/);assert.match(html,/Nieuwe sessie wacht/);
assert.doesNotMatch(html,/<img/);
""")


GOAL_PROBE = """
Date.now=()=>2000000000000;
const now=2000000000,goal={read_only:true,source:'local_confirmed_profile',
 normal_target_c:50,calculated_c:57.5,profile_percent:115,
 profile_confirmed_at:now-100,normal_target_reported_at:now-7,valid_until:now+113,
 contact_state:'unknown',contact_reported_at:null,contact_valid_until:null};
"""


def test_current_confirmed_goal_is_visible_with_unknown_contact_but_never_implies_on():
    execute(GOAL_PROBE + """
const c=Object.create(SolarPilotCard.prototype);c._hass={config:{time_zone:'Europe/Brussels'}};
c._sgDisplayStates=()=>({relay:{state:'unknown'}});
const context={panasonic:{source_stale_s:120,sg_tank_goal:goal,
 display_tank:{available:true,target_c:50,target_stamp:now-7}}};
const value=c._heatpumpCalculatedGoal(context);
assert.equal(value.value,57.5);assert.equal(value.label,'SG-doel bij AAN · berekend');
context.panasonic.sg_tank_goal={...goal,source:'none'};
assert.equal(c._heatpumpCalculatedGoal(context),null);
context.panasonic.sg_tank_goal={...goal,valid_until:now-1};
assert.equal(c._heatpumpCalculatedGoal(context),null);
""")


def test_historical_confirmed_goal_uses_capture_time_with_unknown_contact():
    execute(GOAL_PROBE + """
const d=Object.create(SolarPilotHeatpumpHistoryDialog.prototype);
Date.now=()=>(now+1000)*1000;
const value=d._historyCalculatedGoal({captured_at:now,sg_goal:goal});
assert.equal(value.value,57.5);assert.equal(value.contactState,'unknown');
assert.equal(value.label,'SG-doel bij AAN · berekend');
assert.equal(d._historyCalculatedGoal({captured_at:now,sg_goal:{...goal,
 profile_confirmed_at:now+100}}),null);
assert.equal(d._historyCalculatedGoal({captured_at:now,sg_goal:{...goal,
 normal_target_reported_at:now-121}}),null);
assert.equal(d._historyCalculatedGoal({captured_at:now,sg_goal:null}),null);
""")


def test_unconfirmed_goal_offers_display_sources_route_through_comfort_hub():
    execute("""
const c=Object.create(SolarPilotCard.prototype);let route;
Object.assign(c,{_uiHistory:{prepare(){},track(){}},isConnected:true,
 _loadOptionHelpers:async()=>{},_last:{attributes:{config_entry_id:'fictional-entry'}},
 _hass:{},_optionsDialog:{open:async(h,e,r)=>{route=r;}}});
await c._openOptions('sg_sources');
assert.deepEqual(route,[{next_step_id:'comfort_hub'},{next_step_id:'sg_sources'}]);
c._heatpumpCalculatedGoal=()=>null;c._heatpumpTankValue=()=>null;
assert.match(c._heatpumpTankSummary({panasonic:{sg_tank_goal:{read_only:true}}}),
 /data-config-step="sg_sources"/);
""")


def test_browser_gate_is_in_release_validation():
    root = Path(__file__).resolve().parents[1]
    assert "python tools/check_analysis_ui91.py" in (root / ".github/workflows/validate.yml").read_text()
