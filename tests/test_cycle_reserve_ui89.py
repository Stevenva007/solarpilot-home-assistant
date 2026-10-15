"""Render the shipped start explanation with fictitious allocation evidence.

These are display-contract checks. Actual allocation and electrical safety are
tested independently in the runtime suite; no appliance or HA writes occur.
"""
from copy import deepcopy
import json

import pytest

from test_audit_ui79 import execute
from test_overview_details60 import Markup


def device():
    allocation = {
        "available_w": 1548, "required_w": 520, "sufficient": True,
        "instant_free_w": 1555, "filtered_free_w": 1548, "smoothing_hold_w": 7,
        "protected_cycle_reserve_w": 1800, "solar_cycle_reserve_relief_w": 1800,
        "solar_cycle_reserve_w": 0, "comfort_and_cycle_reserve_w": 1800,
        "solar_applied_reserve_w": 0, "remaining_solar_w": 1548,
        "electrical_headroom_w": 5060, "remaining_cap_w": 3260,
    }
    return {
        "id": "fictional-flexible-load", "name": "Voorbeeldtoestel",
        "kind": "switch", "non_interruptible": False, "mode": "auto",
        "available": True, "on": False, "power_w": 0,
        "start_requirements": {
            "allocated_start_power": {"met": True, **allocation},
        },
        "start_diagnostics": {
            "summary": "Wacht op stabiel zonneoverschot", "missing": [],
            "power": {"measurement_valid": True, "required_start_w": 520,
                      "measured_free_w": 1555, "allocation": allocation},
            "stable_start": {"configured_s": 300, "remaining_s": 300},
        },
    }


def render(payload):
    return execute("""
const card=Object.create(SolarPilotCard.prototype);
card._last={state:'Zonnestroom',attributes:{}};let writes=0;
card._hass={callService:()=>{writes++;}};
const html=card._startExplanation(%s,'solar');
assert.equal(writes,0);process.stdout.write(JSON.stringify(html));
""" % json.dumps(payload))


def facts(html):
    result = {}
    for node in Markup(html).root.walk():
        if node.tag != "span":
            continue
        bold = [child for child in node.children if getattr(child, "tag", None) == "b"]
        if len(bold) == 1:
            value = bold[0].text().strip()
            text = node.text().strip()
            result[text[:-len(value)].strip()] = value
    return result


@pytest.mark.parametrize("kind", ["switch", "number", "script"])
def test_current_rest_surplus_does_not_include_the_electrical_peak_reserve(kind):
    payload = device()
    payload["kind"] = kind
    html = render(payload)
    shown = facts(html)
    assert shown["Reserve voor lopende beschermde cycli · elektrisch behouden"] == "1,8 kW"
    assert shown["Cyclusreserve afgetrokken van zonnestroom"] == "0 W"
    assert shown["Zonnebudget na reserves en eerdere toewijzingen"] == "1,55 kW"
    assert shown["Beschikbaar voor dit toestel"] == "1,55 kW"
    assert shown["Benodigd voor start"] == "520 W"
    assert shown["Elektrisch budget na reserves en eerdere toewijzingen"] == "3,26 kW"
    assert shown["Stabiel nodig"] == "nog 5m"
    assert "cycle-reserve-note" in html
    assert "Dit telt geen extra zonnestroom of elektrische ruimte bij" in html
    assert "Minimumlooptijden en beschermde cycli blijven gelden" in html


def test_final_electrical_guard_still_limits_the_reported_start_budget():
    payload = device()
    allocation = payload["start_diagnostics"]["power"]["allocation"]
    allocation.update(available_w=225, sufficient=False, remaining_cap_w=225)
    payload["start_requirements"]["allocated_start_power"] = {"met": False, **allocation}
    payload["start_diagnostics"].update(summary="Wacht op vermogen / hogere prioriteit",
                                         missing=["allocated_start_power"])
    html = render(payload)
    shown = facts(html)
    assert shown["Beschikbaar voor dit toestel"] == "225 W"
    assert shown["Zonnebudget na reserves en eerdere toewijzingen"] == "1,55 kW"
    assert shown["Elektrisch budget na reserves en eerdere toewijzingen"] == "225 W"
    assert "Na de reserves en hogere voorrangen is 225 W beschikbaar" in html
    assert "vrije zonnestroom nodig" not in html


def test_only_trusted_dishwasher_slice_is_excluded_from_solar_deduction():
    payload = device()
    payload["start_diagnostics"]["power"]["allocation"].update(
        protected_cycle_reserve_w=3600, solar_cycle_reserve_relief_w=1800,
        solar_cycle_reserve_w=1800, isolated_reserve_w=375,
        comfort_and_cycle_reserve_w=3975, solar_applied_reserve_w=2175,
        remaining_solar_w=-627, available_w=0, sufficient=False,
    )
    shown = facts(render(payload))
    assert shown["Reserve voor lopende beschermde cycli · elektrisch behouden"] == "3,6 kW"
    assert shown["Cyclusreserve afgetrokken van zonnestroom"] == "1,8 kW"
    assert shown["Reserve voor toestellen met onzekere metingen"] == "375 W"
    assert shown["Zonnebudget na reserves en eerdere toewijzingen"] == "-627 W"
    assert shown["Beschikbaar voor dit toestel"] == "0 W"


@pytest.mark.parametrize("patch", [
    {"solar_cycle_reserve_relief_w": None},
    {"solar_cycle_reserve_relief_w": False},
    {"solar_cycle_reserve_relief_w": ""},
    {"solar_cycle_reserve_relief_w": "unavailable"},
    {"solar_cycle_reserve_relief_w": "Infinity"},
    {"solar_cycle_reserve_relief_w": []},
    {"solar_cycle_reserve_relief_w": {}},
    {"solar_cycle_reserve_relief_w": -1},
    {"solar_cycle_reserve_relief_w": 0},
    {"solar_cycle_reserve_relief_w": 2100},
    {"solar_cycle_reserve_w": None},
    {"solar_cycle_reserve_w": False},
    {"solar_cycle_reserve_w": -1},
    {"solar_cycle_reserve_w": 2001},
    {"solar_cycle_reserve_w": 100},
    {"protected_cycle_reserve_w": 0},
])
def test_invalid_or_inconsistent_relief_does_not_invent_a_zero_solar_reserve(patch):
    payload = device()
    payload["start_diagnostics"]["power"]["allocation"].update(patch)
    html = render(payload)
    assert "cycle-reserve-note" not in html
    assert "Cyclusreserve afgetrokken van zonnestroom" not in html
    assert "elektrisch behouden" not in html
    assert "Reserve voor lopende beschermde cycli · komende pieken" in html or patch.get("protected_cycle_reserve_w") == 0


@pytest.mark.parametrize("field", ["solar_cycle_reserve_relief_w", "solar_cycle_reserve_w"])
def test_old_or_partial_backend_contract_keeps_the_existing_full_reserve(field):
    payload = device()
    del payload["start_diagnostics"]["power"]["allocation"][field]
    html = render(payload)
    assert facts(html)["Reserve voor lopende beschermde cycli · komende pieken"] == "1,8 kW"
    assert "Cyclusreserve afgetrokken van zonnestroom" not in html
    assert "cycle-reserve-note" not in html


@pytest.mark.parametrize("patch", [
    {"kind": "dishwasher"}, {"kind": "climate"}, {"kind": "battery"},
    {"kind": "water_heater"}, {"non_interruptible": True}, {"available": False},
])
def test_ineligible_device_never_claims_the_flexible_load_exception(patch):
    payload = device()
    payload.update(patch)
    html = render(payload)
    assert "cycle-reserve-note" not in html
    assert "Cyclusreserve afgetrokken van zonnestroom" not in html


@pytest.mark.parametrize("known", [False, None])
def test_missing_energy_evidence_never_claims_usable_current_surplus(known):
    payload = device()
    payload["start_diagnostics"]["power"]["measurement_valid"] = known
    html = render(payload)
    assert "cycle-reserve-note" not in html
    assert "Cyclusreserve afgetrokken van zonnestroom" not in html


def test_start_rest_and_higher_priority_explanations_survive_the_new_budget_rows():
    payload = device()
    payload["start_requirements"].update(
        minimum_rest={"met": False, "remaining_s": 60},
        wallbox_start_block={"met": False, "reason": "Voorbeeld: auto krijgt voorrang"},
    )
    payload["start_diagnostics"]["missing"] = ["minimum_rest", "wallbox_start_block"]
    html = render(payload)
    assert "Minimale rusttijd: nog 1m" in html
    assert "Voorbeeld: auto krijgt voorrang" in html
    assert facts(html)["Stabiel nodig"] == "nog 5m"
    assert "cycle-reserve-note" in html


def test_active_cycle_and_restored_snapshot_do_not_receive_new_start_claims():
    payload = device()
    payload["on"] = True
    html = render(payload)
    assert "Waarom dit toestel nu actief is" in html
    assert "cycle-reserve-note" not in html
    restored = execute("""
const card=Object.create(SolarPilotCard.prototype);
card._last={state:'Zonnestroom',attributes:{restored:true}};
process.stdout.write(JSON.stringify(card._startExplanation(%s,'solar')));
""" % json.dumps(deepcopy(device())))
    assert "Actuele SolarPilot-status ontbreekt" in restored
    assert "cycle-reserve-note" not in restored
