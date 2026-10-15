"""Render transient reachability as a wait, without issuing browser commands.

The shipped card runs in Node; backend retry scheduling and service dispatch
have separate runtime tests. All labels and devices here are fictitious.
"""
from copy import deepcopy
import json

import pytest

from test_audit_ui79 import execute


def device(**changes):
    value = {
        "id": "fictional-flexible-load", "name": "Voorbeeldtoestel",
        "kind": "switch", "mode": "auto", "available": False,
        "on": True, "owned": True, "power_w": 0, "estimated": False,
        "reason": "Wacht op actuele toestelstatus",
        "start_requirements": {
            "availability_and_fault": {
                "met": False, "available": False, "observed": True, "fault": "",
            },
            "minimum_rest": {"met": False, "remaining_s": 60},
        },
        "start_diagnostics": {
            "summary": "Wacht op actuele toestelstatus",
            "missing": ["availability_and_fault", "minimum_rest"],
        },
        "availability_retry": {
            "active": True, "state": "source_wait", "interval_s": 300,
            "next_check_wall": 2000000300, "remaining_s": 300,
            "reason": "Tijdelijk geen actuele toestelgegevens beschikbaar.",
        },
    }
    value.update(changes)
    return value


def render(payload, *, method="_deviceCard", restored=False, state="Zonnestroom"):
    return execute("""
const card=Object.create(SolarPilotCard.prototype);
Date.now=()=>2000000000000;
card._last={state:%s,attributes:{mode:'solar',restored:%s,devices:[%s]}};
let writes=0;
card._hass={states:{},callService:()=>{writes++;},callWS:()=>{writes++;}};
const input=%s;
const html=%s;
assert.equal(writes,0);process.stdout.write(JSON.stringify(html));
""" % (
        json.dumps(state), str(restored).lower(), json.dumps(payload),
        json.dumps(payload),
        "card._decisionBoard(card._ctx())" if method == "_decisionBoard"
        else "card._startExplanation(input,'solar')" if method == "_startExplanation"
        else "card._deviceCard(input,'solar')",
    ))


@pytest.mark.parametrize("kind", ["switch", "number", "script", "dishwasher"])
def test_temporary_source_unavailability_has_neutral_five_minute_wait(kind):
    html = render(device(kind=kind, dishwasher={"ready": False}))
    assert "Tijdelijk niet bereikbaar" in html
    assert "Opnieuw controleren over 5m" in html
    assert "SolarPilot controleert elke 5 minuten opnieuw" in html
    assert "op dat moment nodig en toegestaan" in html
    assert "Toestelfout:" not in html
    assert "Controle afronden" not in html
    assert "onbekend" in html
    assert ">0 W<" not in html


@pytest.mark.parametrize("method", ["_deviceCard", "_decisionBoard", "_startExplanation"])
def test_current_unconfirmed_command_remains_a_readback_wait(method):
    payload = device()
    payload["availability_retry"].update(
        state="command_wait", reason="De vorige opdracht is nog niet bevestigd.",
    )
    html = render(payload, method=method)
    assert "Wacht op terugmelding" in html
    assert "De vorige opdracht is nog niet bevestigd." in html
    assert "controleert elke 5 minuten opnieuw" in html
    assert "opnieuw starten" not in html
    assert "opnieuw verzonden" not in html
    assert "Opdrachtfout:" not in html


def test_overview_wait_keeps_unknown_power_history_and_ordinary_controls():
    payload = device(history={"last_change": {
        "at": 1999999900, "reason": "Eerdere status waargenomen",
        "confirmed": False,
    }})
    html = render(payload, method="_decisionBoard")
    assert "Vermogen nog niet bekend" in html
    assert "Eerdere status waargenomen" in html
    assert 'data-action="history"' in html
    assert "Opnieuw controleren over 5m" in html
    assert ">0 W<" not in html


def test_other_start_constraints_remain_explained_during_a_retry_wait():
    html = render(device(), method="_startExplanation")
    assert "Minimale rusttijd: nog 1m" in html
    assert "Tijdelijk geen actuele toestelgegevens beschikbaar." in html
    assert "Opnieuw controleren over 5m" in html


def test_current_tick_updates_readonly_countdown_and_does_not_claim_a_retry_ran():
    payload = device()
    payload["availability_retry"].update(next_check_wall=2000000037, remaining_s=37)
    html = render(payload)
    assert "Opnieuw controleren over 37 s" in html
    payload["availability_retry"].update(next_check_wall=1999999999, remaining_s=0)
    html = render(payload)
    assert "Nieuwe controle gepland; wacht op de volgende terugmelding." in html
    assert "opnieuw uitgevoerd" not in html
    assert "gelukt" not in html


def test_device_local_isolation_keeps_its_reserve_unknown_power_and_wait_label():
    html = render(device(isolated=True, isolation_reason="Actuele bron ontbreekt",
                         isolation_reserve_w=350))
    assert "Tijdelijk niet bereikbaar" in html
    assert "SolarPilot controleert elke 5 minuten opnieuw" in html
    assert "Veiligheidsreserve voor mogelijk verbruik" in html
    assert "Dit is geen gemeten verbruik." in html
    assert "De actuele activiteit is onbekend." in html
    assert "350 W" in html
    assert ">0 W<" not in html


@pytest.mark.parametrize("patch", [
    {"active": False}, {"active": "true"}, {"state": "fault"},
    {"interval_s": 60}, {"interval_s": "300"},
    {"next_check_wall": None}, {"next_check_wall": False},
    {"next_check_wall": "2000000300"}, {"next_check_wall": 0},
    {"remaining_s": None}, {"remaining_s": False}, {"remaining_s": -1},
    {"remaining_s": 301}, {"remaining_s": "300"},
])
def test_malformed_or_old_retry_data_does_not_invent_automatic_recovery(patch):
    payload = device()
    payload["availability_retry"].update(patch)
    html = render(payload)
    assert "SolarPilot controleert elke 5 minuten opnieuw" not in html
    assert "Opnieuw controleren over" not in html


@pytest.mark.parametrize("kind", ["climate", "water_heater", "battery", "sg_boost"])
def test_separate_controllers_do_not_inherit_ordinary_device_recovery_claims(kind):
    payload = device(kind=kind)
    html = render(payload, method="_startExplanation")
    assert "SolarPilot controleert elke 5 minuten opnieuw" not in html


@pytest.mark.parametrize("restored,state", [
    (True, "Zonnestroom"), (False, "unknown"), (False, "unavailable"),
])
def test_restored_or_unavailable_snapshot_does_not_advertise_live_rechecks(restored, state):
    html = render(device(), restored=restored, state=state)
    assert "SolarPilot controleert elke 5 minuten opnieuw" not in html
    assert "Opnieuw controleren over" not in html
    assert "Actuele SolarPilot-status ontbreekt" in html


def test_genuine_device_fault_is_not_hidden_by_a_conflicting_retry_payload():
    payload = device()
    payload["start_requirements"]["availability_and_fault"]["fault"] = (
        "Ongeldige koppeling vraagt controle"
    )
    html = render(payload)
    assert "Toestelfout: Ongeldige koppeling vraagt controle" in html
    assert "SolarPilot controleert elke 5 minuten opnieuw" not in html


def test_unknown_power_stays_unknown_after_command_error_without_retry_evidence():
    payload = device()
    del payload["availability_retry"]
    payload["reason"] = "Opdrachtfout: HomeAssistantError; controleer het toestel"
    payload["start_diagnostics"]["summary"] = payload["reason"]
    html = render(payload)
    assert payload["reason"] in html
    assert "onbekend" in html
    assert ">0 W<" not in html
    assert "SolarPilot controleert elke 5 minuten opnieuw" not in html


def test_retry_reason_is_escaped_in_cards_and_overview():
    payload = device()
    payload["availability_retry"]["reason"] = '<img src=x onerror="bad()"> bron wacht'
    for method in ("_deviceCard", "_decisionBoard", "_startExplanation"):
        html = render(deepcopy(payload), method=method)
        assert "<img" not in html
        assert "&lt;img" in html


def test_offline_wait_without_an_extra_reserve_uses_actual_net_surplus():
    payload = device(isolated=True, isolation_reason="Actuele bron ontbreekt",
                     isolation_reserve_w=0)
    html = render(payload)
    assert "geen extra verbruiksreserve afgetrokken" in html
    assert "De actuele netmeting bevat het werkelijke huisverbruik" in html
    assert "het toestelvermogen blijft onbekend" in html
    assert "Veiligheidsreserve voor mogelijk verbruik" not in html
    assert ">0 W<" not in html


def test_no_extra_isolation_reserve_is_not_presented_as_estimated_consumption():
    execute("""
const card=Object.create(SolarPilotCard.prototype);
card._last={state:'Zonnestroom',attributes:{mode:'solar',managed_w:0,
  isolated_devices:[{id:'fictional-flexible-load'}],isolated_reserve_w:0}};
card._hass={states:{}};
const html=card._overview(card._ctx());
assert.match(html,/Toestelgegevens deels onbekend; het actuele netoverschot blijft leidend/);
assert.doesNotMatch(html,/mogelijk verbruik wordt apart gereserveerd/);
""")


def test_genuine_fault_overview_uses_current_nonisolated_diagnostic_provenance():
    payload = device(
        isolated=False, isolation_reason="", availability_retry=None,
        reason="Opdrachtfout: ongeldige koppeling vraagt controle",
    )
    payload["start_diagnostics"]["summary"] = payload["reason"]
    payload["start_requirements"]["availability_and_fault"]["fault"] = (
        "Ongeldige koppeling vraagt controle"
    )
    html = render(payload, method="_decisionBoard")
    assert payload["reason"] in html
    assert "Tijdelijk niet bereikbaar" not in html
    assert "controleert elke 5 minuten opnieuw" not in html
