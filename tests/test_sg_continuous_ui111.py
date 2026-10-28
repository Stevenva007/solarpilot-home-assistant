"""Current solar continuation never becomes an unlimited relay permission."""
from copy import deepcopy
import json
from unittest.mock import patch

import pytest

from test_audit_ui79 import execute as probe
from test_sg_transfer_ui108 import transfer
from test_sg_ui_platforms62 import attributes, execute, text

NOW = 1_800_000_000.0


def continuous():
    with patch("test_sg_ui_platforms62.time.time", return_value=NOW):
        return attributes(profile="general", state="boost_requested", desired_on=True,
            relay_on=True, owner="solarpilot", lease_confirmed=True,
            lease_remaining_s=300, relay_valid_until=NOW+120,
            remaining_s=None, continuous_solar=True, continuous_solar_valid_until=NOW+30,
            manual_control={"mode": "auto"}, session_elapsed_s=7500,
            active_session_provenance={"owner": "solarpilot", "started_at": NOW-7500},
            reason="SG-contact actief; zonnevoorwaarden blijven voldaan")


@pytest.mark.parametrize("view", ["comfort", "board"])
def test_automatic_solar_stays_current_after_two_hours_with_bounded_local_permission(view):
    data = continuous()
    before = deepcopy(data)
    result = execute(data, view=view)
    rendered = text(result["initial"])
    assert "Lopende automatische zonneboost" in rendered
    assert "Blijft actief zolang zonnevoorwaarden kloppen" in rendered
    assert "Automatische zonneboost Blijft actief zolang zonnevoorwaarden kloppen" in rendered
    assert "Resterende sessie" not in rendered
    assert "SG-contact Actief" in rendered and "SolarPilot-aanvraag Aangevraagd" in rendered
    assert "Bevestigde lokale toestemming nog 5m" in rendered
    assert "Nieuwe SG-sessie" not in rendered and "Herbevestiging onbekend" not in rendered
    assert data == before and not result["calls"]


@pytest.mark.parametrize("change", [
    {"continuous_solar": False}, {"continuous_solar": "true"},
    {"continuous_solar_valid_until": None}, {"continuous_solar_valid_until": True},
    {"continuous_solar_valid_until": NOW}, {"continuous_solar_valid_until": NOW+121},
    {"continuous_solar_valid_until": NOW+10**9},
    {"observed_at": NOW-121}, {"observed_at": NOW+6},
    {"lease_remaining_s": None}, {"lease_remaining_s": True},
    {"lease_remaining_s": 0}, {"lease_remaining_s": 601},
    {"lease_confirmed": False}, {"relay_confirmed": False}, {"relay_on": False},
    {"relay_observed_at": NOW-121}, {"relay_valid_until": NOW},
    {"owner": "manual"}, {"owner": "external"},
    {"manual_hold": True}, {"completion_hold": True}, {"fault": "transport"},
    {"desired_on": False}, {"enabled": False}, {"profile": "dhw_only"},
    {"manual_control": {"mode": "on", "duration_s": 3600,
        "expires_at": NOW+3600, "remaining_s": 3600}},
    {"manual_control": {"mode": "off", "duration_s": 1800,
        "expires_at": NOW+1800, "remaining_s": 1800}},
    {"remaining_s": 0}, {"remaining_s": 300},
])
def test_missing_expired_manual_or_contradictory_evidence_never_promises_continuation(change):
    data = continuous()
    data["sg_boost"].update(change)
    result = execute(data)
    assert "data-sg-continuous" not in result["initial"]
    assert "Blijft actief zolang zonnevoorwaarden kloppen" not in text(result["initial"])
    assert not result["calls"]


@pytest.mark.parametrize("change", [{"restored": True}, {"mode": "paused"}, {"mode": "observe"}])
def test_restored_or_non_solar_overview_is_no_current_solar_authority(change):
    data = continuous()
    data.update(change)
    result = execute(data)
    assert "data-sg-continuous" not in result["initial"]
    assert not result["calls"]


def test_source_expiry_removes_continuation_promise_without_inventing_a_contact_off():
    data = continuous()
    result = execute(data, now=NOW+31)
    rendered = text(result["initial"])
    assert "data-sg-continuous" not in result["initial"]
    assert "Wacht op actuele voortzettingsvoorwaarden" in rendered
    assert "SG-contact Actief" in rendered and "SolarPilot-aanvraag Aangevraagd" in rendered
    assert "Bevestigde lokale toestemming nog 4m" in rendered
    assert not result["calls"]
    expired = execute(data, now=NOW+301)
    assert "SG-contact Actief" not in text(expired["initial"])
    assert "data-sg-continuous" not in expired["initial"]
    assert not expired["calls"]


def test_minimum_cloud_and_four_minute_transfer_keep_their_own_clocks_after_an_hour():
    data = continuous()
    data["sg_boost"].update(min_session_s=1200, effective_min_session_s=1200,
        minimum_remaining_s=0, minimum_active=False, minimum_valid_until=NOW+120,
        cloud_active=True, cloud_import_hold=True, cloud_remaining_s=250,
        cloud_valid_until=NOW+120, import_threshold_w=600, stop_delay_s=300)
    data["ems"] = transfer()["ems"]
    result = execute(data, now=NOW+10)
    rendered = text(result["initial"])
    assert "Minimum verstreken · actuele regeling bepaalt het vrijgeven" in rendered
    assert "Netafname boven 600 W · nog 4 min" in rendered
    assert "Nog 3 min 50 s reactietijd voor de Wallbox" in rendered
    assert "SG-contact Actief" in rendered
    assert not result["calls"]


def test_live_continuation_expiry_changes_the_observation_signature_without_new_backend_data():
    # Keep all other clocks in the same ten-second display bucket, so this
    # change can only be detected by the continuation-proof signature entry.
    data = continuous()
    data["sg_boost"]["continuous_solar_valid_until"] = NOW+1
    probe("""
const data=%s,card=Object.create(SolarPilotCard.prototype);
card._last={attributes:data};Date.now=()=>1800000000000;
const context=card._ctx(),before=card._heatpumpDisplaySignature(context);
assert.equal(card._sgContinuousSolar(context),true);
Date.now=()=>1800000002000;
assert.equal(card._sgContinuousSolar(context),false);
assert.notEqual(card._heatpumpDisplaySignature(context),before);
assert.equal(data.sg_boost.active_session_provenance.started_at,1799992500);
""" % json.dumps(data))


def test_non_finite_browser_memory_cannot_grant_continuous_permission():
    data = continuous()
    probe("""
const data=%s,card=Object.create(SolarPilotCard.prototype);
card._last={attributes:data};Date.now=()=>1800000000000;
const context=card._ctx();
for(const field of ['continuous_solar_valid_until','lease_remaining_s','relay_valid_until','observed_at']){
 const original=data.sg_boost[field];
 for(const value of [NaN,Infinity,-Infinity]){
  data.sg_boost[field]=value;assert.equal(card._sgContinuousSolar(context),false);
 }
 data.sg_boost[field]=original;
}
""" % json.dumps(data))


def test_continuation_uses_original_relay_proof_bound_with_supported_clock_tolerance():
    data = continuous()
    data["sg_boost"].update(relay_observed_at=NOW+3,
        relay_valid_until=NOW+300, continuous_solar_valid_until=NOW+123)
    result = execute(data)
    assert "Lopende automatische zonneboost" in text(result["initial"])
    assert not result["calls"]


def deficit(**changes):
    data = continuous()
    data["sg_boost"].update(stop_delay_s=300, import_threshold_w=600,
        cloud_active=False, cloud_remaining_s=None, cloud_valid_until=NOW+120,
        joint_solar_deficit_active=True, joint_solar_deficit_remaining_s=250,
        joint_solar_deficit_valid_until=NOW+30, min_session_s=1200,
        effective_min_session_s=1200, minimum_active=True, minimum_remaining_s=480,
        minimum_valid_until=NOW+120, session_elapsed_s=720,
        active_session_provenance={"owner": "solarpilot", "started_at": NOW-720})
    data["sg_boost"].update(changes)
    return data


@pytest.mark.parametrize("view", ["comfort", "board"])
def test_solar_deficit_has_a_bounded_buffer_even_without_high_grid_import(view):
    data = deficit()
    before = deepcopy(data)
    result = execute(data, view=view, now=NOW+10)
    rendered = text(result["initial"])
    assert "Wolkenbuffer voor te weinig zonnestroom" in rendered
    assert "Te weinig bruikbare zonnestroom · nog 4 min wolkenbuffer" in rendered
    assert "Geen lopende importbuffer" in rendered
    assert "Deze klok loopt naast de netafnamebuffer en de minimumduur" in rendered
    assert "geen extra buffer achteraf" in rendered
    assert "Nog 7 min 50 s · alleen de SG-aanvraag" in rendered
    assert data == before and not result["calls"]


@pytest.mark.parametrize("change", [
    {"joint_solar_deficit_remaining_s": None}, {"joint_solar_deficit_remaining_s": True},
    {"joint_solar_deficit_remaining_s": -1}, {"joint_solar_deficit_remaining_s": 301},
    {"joint_solar_deficit_valid_until": None}, {"joint_solar_deficit_valid_until": True},
    {"joint_solar_deficit_valid_until": NOW}, {"joint_solar_deficit_valid_until": NOW+121},
    {"observed_at": NOW-121}, {"lease_confirmed": False}, {"lease_remaining_s": 0},
    {"lease_remaining_s": 601}, {"relay_confirmed": False}, {"relay_on": False},
    {"relay_valid_until": NOW}, {"owner": "manual"},
])
def test_unproven_joint_deficit_cannot_advertise_a_live_buffer(change):
    result = execute(deficit(**change))
    rendered = text(result["initial"])
    assert "data-sg-solar-deficit" not in result["initial"] or "Resterende zonnebuffer onbekend" in rendered
    assert "nog 4 min 10 s wolkenbuffer" not in rendered
    assert not result["calls"]


def test_elapsed_solar_deficit_buffer_does_not_promise_a_stop_before_existing_minimum():
    result = execute(deficit(joint_solar_deficit_remaining_s=0))
    rendered = text(result["initial"])
    assert "Zonnebuffer verstreken · minimumduur en actuele voorwaarden bepalen het vrijgeven" in rendered
    assert "Nog 8 min · alleen de SG-aanvraag" in rendered
    assert "SG-contact Actief" in rendered
    assert "wordt uitgeschakeld" not in rendered
    assert not result["calls"]


def test_joint_deficit_proof_expires_without_becoming_infinite_on_permission():
    result = execute(deficit(), now=NOW+31)
    rendered = text(result["initial"])
    assert "Resterende zonnebuffer onbekend" in rendered
    assert "nog 3 min 39 s wolkenbuffer" not in rendered
    assert "data-sg-continuous" not in result["initial"]
    assert "SG-contact Actief" in rendered and not result["calls"]
