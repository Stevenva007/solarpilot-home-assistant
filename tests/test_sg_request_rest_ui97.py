"""A replaceable SG request wait is conditional, never a new start permission."""
from copy import deepcopy

import pytest

from test_overview_details60 import Markup
from test_sg_residual_ui86 import residual_wait
from test_sg_ui_platforms62 import execute


def request_rest():
    data = residual_wait()
    data["sg_boost"].update(
        rest_remaining_s=900, policy_hold_reason="response_unknown",
        rearm_wait={"request_rest_remaining_s": 900, "request_rest_replaceable": True,
                    "current_condition": "Verse echte restinjectie en actuele voorwaarden opnieuw controleren"},
    )
    return data


def rendered(data, view="comfort", **options):
    result = execute(data, view=view, **options)
    assert not result["calls"]
    root = Markup(result["initial"]).root
    waits = [node for node in root.walk() if "data-sg-wait" in node.attributes]
    return " ".join(node.text() for node in waits), root.text(), root


@pytest.mark.parametrize("view", ["board", "comfort"])
def test_five_minute_proof_can_run_during_request_rest_without_promising_a_start(view):
    wait, details, _ = rendered(request_rest(), view)
    assert "Actueel restoverschot: nog 4 min 10 s van 5 min" in wait
    assert "SG-herhaalwacht: nog 15 min" in wait
    assert "Kan eerder vervallen na 5 min verse echte restinjectie" in wait
    assert "een bevestigd open SG-contact en alle actuele voorwaarden" in wait
    assert "Daarna geldt de gewone startvertraging" in wait
    assert "Ingestelde startvertraging 2 min" in details
    assert "SG-contact Open" in details
    assert "SG-herhaalwacht nog 15m" in details
    assert "Rusttijd nog 15m" not in details
    assert "start toegestaan" not in wait.lower() and "contact actief" not in wait.lower()


def test_completed_confirmation_still_waits_for_final_fresh_report():
    data = request_rest()
    data["sg_boost"]["reassessment_remaining_s"] = 0
    data["sg_boost"]["reassessment_final_report_required"] = True
    wait, details, _ = rendered(data)
    assert "tijd verstreken · wacht op verse bevestiging" in wait
    assert "Kan eerder vervallen" in wait
    assert "gereed" not in wait and "SG-contact Open" in details


def test_ordinary_start_delay_remains_separate_after_backend_released_hold():
    data = request_rest()
    data["sg_boost"].update(
        completion_hold=False, state="waiting_surplus", rearm_wait=None,
        rest_remaining_s=0, start_remaining_s=120,
        start_valid_until=data["_test_clock"]+120,
    )
    wait, details, _ = rendered(data)
    assert "SG-startvertraging" in wait and "nog 2 min van 2 min" in wait
    assert "Kan eerder vervallen" not in wait and "herbevestigen" not in wait
    assert "SG-herhaalwacht gereed" in details
    assert "SG-contact Open" in details


@pytest.mark.parametrize("value", [False, None, "true", 1])
def test_only_explicit_backend_boolean_enables_conditional_replacement_label(value):
    data = request_rest()
    data["sg_boost"]["rearm_wait"]["request_rest_replaceable"] = value
    wait, details, _ = rendered(data)
    assert "Kan eerder vervallen" not in wait
    assert "SG-herhaalwacht nog 15m" in details


@pytest.mark.parametrize("value", [None, True, -1, "900", 1.5])
def test_malformed_nested_request_timer_does_not_claim_replaceability(value):
    data = request_rest()
    data["sg_boost"]["rearm_wait"]["request_rest_remaining_s"] = value
    wait, _, _ = rendered(data)
    assert "Kan eerder vervallen" not in wait


@pytest.mark.parametrize("reason", ["no_uptake", "native_completed", "session_limit", "profile_changed"])
def test_other_completion_reasons_do_not_inherit_the_early_residual_lane(reason):
    data = request_rest()
    data["sg_boost"]["policy_hold_reason"] = reason
    wait, _, _ = rendered(data)
    assert "Kan eerder vervallen" not in wait


def test_dhw_only_profile_never_receives_general_request_rest_explanation():
    data = request_rest()
    data["sg_boost"]["profile"] = "dhw_only"
    wait, _, _ = rendered(data)
    assert "Kan eerder vervallen" not in wait and "verse echte restinjectie" not in wait


@pytest.mark.parametrize("change", [
    {"relay_confirmed": False}, {"relay_on": True}, {"desired_on": True},
    {"manual_hold": True}, {"fault": "Uitgang vraagt controle"},
    {"relay_observed_at": 1}, {"observed_at": 1},
])
def test_unconfirmed_or_stale_contact_and_other_guards_cannot_advertise_replacement(change):
    data = request_rest()
    data["sg_boost"].update(change)
    wait, _, _ = rendered(data)
    assert "Kan eerder vervallen" not in wait


def test_restored_snapshot_never_advertises_current_replaceability():
    data = request_rest()
    data["restored"] = True
    wait, _, _ = rendered(data)
    assert "Kan eerder vervallen" not in wait


def test_client_countdown_expiry_never_releases_the_backend_hold():
    data = request_rest()
    data["sg_boost"].update(rest_remaining_s=1)
    data["sg_boost"]["rearm_wait"]["request_rest_remaining_s"] = 1
    before = deepcopy(data)
    wait, details, _ = rendered(data, now=data["_test_clock"]+2)
    assert "Kan eerder vervallen" not in wait
    assert "restoverschot herbevestigen" in wait
    assert "SG-contact Open" in details
    assert data == before and data["sg_boost"]["completion_hold"] is True


def test_backend_condition_remains_escaped_text_in_request_wait_details():
    data = request_rest()
    payload = '<img src=x onerror="bad()">'
    data["sg_boost"]["rearm_wait"]["current_condition"] = payload
    _, details, root = rendered(data)
    assert payload in details
    assert not any(node.tag == "img" for node in root.walk())
