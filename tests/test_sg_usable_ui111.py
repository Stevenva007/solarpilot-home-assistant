"""Render current SG/EV rearm evidence without turning conditional EV into export."""
from copy import deepcopy
from unittest.mock import patch

import pytest

from test_overview_details60 import Markup
from test_sg_ui_platforms62 import attributes, execute, text

NOW = 1_800_000_000.0


def usable():
    with patch("test_sg_ui_platforms62.time.time", return_value=NOW):
        data = attributes(profile="general", completion_hold=True, policy_hold_reason="session_limit",
            desired_on=False, relay_on=False, state="blocked", start_required_s=120,
            reason="Actueel bruikbaar zonnevermogen en UIT bevestigen",
            reassessment_kind="fresh_usable_solar", reassessment_state="confirming_fresh_usable_solar",
            reassessment_required_s=120, reassessment_remaining_s=60, reassessment_reports=2,
            reassessment_source_current=True, reassessment_valid_until=NOW+30,
            usable_reassessment_available=True, usable_reassessment_threshold_w=3000,
            usable_solar_w=4139, usable_solar_reported_at=NOW, usable_solar_valid_until=NOW+120,
            real_residual_surplus_w=39, residual_reassessment_threshold_w=3000,
            rearm_wait={"request_rest_remaining_s": 900, "request_rest_replaceable": True})
    data["ems"] = {"electrical_limits": {"source_valid": True, "source_observed_at": NOW,
        "source_stale_s": 120, "sg_solar_valid": True, "sg_solar_observed_at": NOW,
        "sg_eligible_solar_w": 4139, "sg_hp_solar_w": 2590, "sg_ev_solar_w": 1510,
        "sg_residual_solar_w": 39, "fixed_import_limit_w": 3500,
        "instantaneous_headroom_w": 2000, "sg_estimated_extra_w": 410,
        "sg_increment_observed_at": NOW, "sg_increment_valid_until": NOW+120,
        "sg_ev_credit_reason": "Actuele bevestigde autonome zonnelaadruimte"}}
    return data


def wait_text(result):
    return next(node.text() for node in Markup(result["initial"]).root.walk()
                if node.attributes.get("data-sg-wait") == "reassessment")


@pytest.mark.parametrize("view", ["comfort", "board"])
def test_usable_rearm_uses_joint_pool_and_one_configured_start_window(view):
    data = usable()
    before = deepcopy(data)
    result = execute(data, view=view)
    banner = wait_text(result)
    rendered = text(result["initial"])
    assert "Nieuwe SG-sessie · zonnebudget bevestigen" in banner
    assert "nog 1 min van 2 min" in banner
    assert "Bruikbaar zonnevermogen 4,14 kW · nodig 3 kW" in banner
    assert "warmtepomp- en Wallbox-zonnestroom" in banner
    assert "vrije injectie blijft apart" in banner
    assert "telt één keer als startstabiliteit" in banner
    assert "na 5 min" not in banner and "Daarna geldt de gewone startvertraging" not in banner
    for label in ("Warmtepompbijdrage aan startdrempel (afgeleid)", "Resterende vrije zonnestroom",
                  "Overdraagbare Wallbox-zonnestroom (voorwaardelijk)", "Geraamde bijkomende SG-opname nu"):
        assert label in rendered
    assert "39 W" in rendered and "1,51 kW" in rendered and "410 W" in rendered
    assert "Warmtepomp gebruikt zonnestroom vóór automatisch laden" in rendered
    assert 'data-wallbox-priority-target="dhw_extra"' not in result["initial"]
    assert data == before and not result["calls"]


def test_original_progress_deadline_counts_down_without_starting_a_second_window():
    data = usable()
    result = execute(data, now=NOW+15)
    assert "nog 45 s van 2 min" in wait_text(result)
    assert "telt één keer als startstabiliteit" in wait_text(result)
    assert not result["calls"]


@pytest.mark.parametrize("change", ["expired", "source_stale", "future", "missing_until", "invalid_until", "restored"])
def test_unusable_source_never_claims_current_rearm_time_or_joint_watts(change):
    data = usable()
    s = data["sg_boost"]
    now = NOW
    if change == "expired":
        now = NOW+120.01
    elif change == "source_stale":
        s["usable_solar_reported_at"] = NOW-121
    elif change == "future":
        s["usable_solar_reported_at"] = NOW+6
    elif change == "missing_until":
        s.pop("usable_solar_valid_until")
    elif change == "invalid_until":
        s["usable_solar_valid_until"] = True
    else:
        data["restored"] = True
    result = execute(data, now=now)
    banner = wait_text(result)
    assert "onbekend" in banner.lower()
    assert "4,14 kW" not in banner and "nog 1 min van 2 min" not in banner
    assert not result["calls"]


@pytest.mark.parametrize("value", [None, True, "4139", "NaN", "Infinity", -1])
def test_unproven_joint_watts_are_not_replaced_by_raw_export_or_zero(value):
    data = usable()
    data["sg_boost"]["usable_solar_w"] = value
    result = execute(data)
    banner = wait_text(result)
    assert "Bruikbaar zonnevermogen 4,14 kW" not in banner
    assert "Bruikbaar zonnevermogen 0 W" not in banner
    assert "Restoverschot 39 W · nodig 3 kW" not in banner
    assert not result["calls"]


def test_waiting_for_usable_budget_does_not_require_an_artificial_solar_reset():
    data = usable()
    data["sg_boost"].update(reassessment_kind=None, reassessment_state="waiting_new_evidence",
        reassessment_remaining_s=None)
    result = execute(data)
    banner = wait_text(result)
    assert "inclusief bevestigde Wallbox-zonnestroom" in banner
    assert "Een eerdere zonnedip is niet nodig" in banner
    assert not result["calls"]


@pytest.mark.parametrize("reason", ["Wallbox-laadvermogen is te oud", "Handmatig laden levert geen zonnecredit",
                                   '<img src=x onerror="bad()">'])
def test_current_ev_rejection_reason_is_visible_escaped_and_expires(reason):
    data = usable()
    limits = data["ems"]["electrical_limits"]
    limits.update(sg_ev_solar_w=0, sg_ev_credit_reason=reason)
    result = execute(data)
    assert reason in text(result["initial"])
    assert "<img src=x" not in result["initial"]
    stale = execute(data, now=NOW+121)
    assert reason not in text(stale["initial"])
    assert "1,51 kW" not in text(stale["initial"])
    assert not result["calls"] and not stale["calls"]


def test_zero_second_configuration_waits_for_a_new_confirming_report_without_claiming_on():
    data = usable()
    data["sg_boost"].update(reassessment_required_s=0, reassessment_remaining_s=0,
        reassessment_final_report_required=True)
    result = execute(data)
    assert "tijd verstreken · wacht op verse bevestiging" in wait_text(result)
    assert "SG-contact Open" in text(result["initial"])
    assert not result["calls"]


def test_restored_overview_never_revives_conditional_ev_or_joint_budget():
    data = usable()
    data["restored"] = True
    result = execute(data)
    rendered = text(result["initial"])
    assert "1,51 kW" not in rendered and "4,14 kW" not in rendered
    assert "Bruikbaar zonnevermogen onbekend" in wait_text(result)
    assert not result["calls"]


@pytest.mark.parametrize("order", [["wallbox", "device:fan", "dhw_extra"],
                                  ["dhw_extra", "wallbox", "device:fan"]])
def test_priority_editor_states_sg_exception_without_reordering_other_devices(order):
    import json
    from test_audit_ui79 import execute as execute_probe
    execute_probe("""
const order=%s,original=JSON.stringify(order),dialog=Object.create(SolarPilotPriorityDialog.prototype);
Object.assign(dialog,{_data:{rows:[{id:'wallbox',name:'Auto laden'},
 {id:'device:fan',name:'Voorbeeldtoestel'},{id:'dhw_extra',name:'SG-zonneboost'}],protected:[]},
 _order:order,_permissions:{'device:fan':true},content:{innerHTML:''},_controls:()=>{}});
dialog._renderDraft();
assert.match(dialog.content.innerHTML,/SG heeft vaste voorrang op bevestigde Wallbox-zonnestroom, onafhankelijk van deze lijst/);
assert.doesNotMatch(dialog.content.innerHTML,/Alleen restoverschot; Auto laden staat hoger/);
assert.equal(JSON.stringify(dialog._order),original);
""" % json.dumps(order))


def test_non_finite_browser_memory_value_cannot_show_a_live_usable_confirmation():
    import json
    from test_audit_ui79 import execute as execute_probe
    data = usable()
    execute_probe("""
Date.now=()=>1800000000000;
const data=%s,card=Object.create(SolarPilotCard.prototype),context={a:data,sgBoost:data.sg_boost};
for(const value of [NaN,Infinity,-Infinity]){
 data.sg_boost.usable_solar_w=value;
 const progress=card._sgWaitProgress(context);
 assert.equal(progress.remaining,null);
 assert.match(progress.label,/Bruikbaar zonnevermogen onbekend/);
 assert.doesNotMatch(progress.label,/Bruikbaar zonnevermogen 0 W/);
}
""" % json.dumps(data))


def test_confirmation_clock_expires_at_candidate_gap_before_sources_go_stale():
    data = usable()
    result = execute(data, now=NOW+31)
    assert "Bruikbaar zonnevermogen onbekend" in wait_text(result)
    assert "nog 29 s" not in wait_text(result)
    # Original source evidence can still be recent, but cannot renew the
    # separate confirmation window while backend reports are absent.
    assert "4,14 kW" in text(result["initial"])
    assert not result["calls"]
