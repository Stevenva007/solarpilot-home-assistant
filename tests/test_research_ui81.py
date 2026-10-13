"""Exercise shipped read-only proof rendering with wholly fictional evidence."""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from test_heatpump_history_ui70 import history_fixture, render_history
from test_investigation_ui75 import investigation, execute, NOW
from test_overview_details60 import Markup

CARD = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot/frontend/solar-pilot-card.js"


def test_native_columns_keep_effective_goal_completion_unknown_and_scope_explicit():
    data = history_fixture()
    data["native_evidence"] = {"schema": 1, "read_only": True, "points": [{
        "captured_at": NOW, "continuity": False,
        "native": {"confirmed": False, "inactive_reported": True, "inactive_scope": "space_circuit",
                   "reported_at": NOW-5, "fresh": True},
        "tank": {"temperature_c": 57, "temperature_reported_at": NOW-4,
                 "ordinary_target_c": 50, "ordinary_target_reported_at": NOW-7},
        "effective_target": {"temperature_c": 62, "status": "confirmed"},
        "completion": {"state": "succeeded"},
        "supplies": [{"valid": False, "watts": None, "reported_at": NOW-1},
                     {"valid": True, "watts": 0, "reported_at": NOW-2}],
        "private_entity": "sensor.do_not_forward"}]}
    text = Markup(render_history(data)["html"]).root.text()
    assert "Native ruimtekring in rust" in text and "57 °C" in text and "50 °C" in text
    assert "Effectief doel" in text and "Native voltooiing" in text
    assert "62 °C" not in text and "succeeded" not in text and "do_not_forward" not in text
    assert "0 W" in text and "onbruikbaar / ontbreekt" in text


def test_short_electrical_intervals_do_not_modify_raw_main_counts():
    data = history_fixture()
    data["electrical_activity"] = {"has_data": True, "starts": 2, "stops": 1,
        "sessions": [dict(data["sessions"][0], duration_s=5, short_observed_period=True,
                          stop_confirmed=False), dict(data["sessions"][0], duration_s=50,
                          short_observed_period=False, stop_confirmed=True)]}
    root = Markup(render_history(data)["html"]).root
    text = root.text()
    assert "1 van maximaal 30 s" in text and "≤ 30 s" in text
    assert "2 ruwe startovergangen" in text and "1 ruwe stopovergangen" in text
    assert "Geen perioden samengevoegd" in text and "5 s" in text
    assert next(n for n in root.walk() if "data-starts" in n.attributes).text() == "1"


def report(role, at=NOW-5, **extra):
    return {"role": role, "reported_wall": at, "fresh": True, **extra}


def test_template_verified_dependency_is_distinct_from_configured_comparison():
    data = investigation()
    data["items"][1].update(id="wallbox_source", metrics={"source_dossier": {
        "schema": 1, "read_only": True, "session": report("session", NOW-18000, value="laden gestopt", fresh=False, platform="template"),
        "known_sources": [report("status", value="ready"), report("mode", value="full_solar"), report("power", watts=0)],
        "dependency_relation": "verified_state_template_dependencies", "dependency_coverage": "last_successful_render_only",
        "dependencies": [report("dependency_1", matches_configured_roles=["power"], entity_id="sensor.private_ignore")]}})
    _, root = execute(data)
    text = root.text()
    assert "Afhankelijkheden van de laatste geslaagde templateverwerking" in text
    assert "Native vermogen" in text and "0 W" in text and "verouderd / ontbreekt" in text
    assert "uitsluitend de afhankelijkheden" in text and "private_ignore" not in text


def test_template_unknown_and_partial_dependencies_remain_distinct():
    for relation, coverage in (("unknown", "unknown"), ("verified_state_template_dependencies", "partial")):
        data = investigation()
        data["items"][1]["metrics"] = {"source_dossier": {"schema": 1, "read_only": True,
            "session": report("session"), "dependency_relation": relation, "dependency_coverage": coverage,
            "dependencies": [], "known_sources": []}}
        _, root = execute(data)
        if relation == "unknown":
            assert "afhankelijkheidsrelatie zijn onbekend" in root.text()
        else:
            assert "begrensd of gebruikt brede luistervoorwaarden" in root.text()


def test_separate_grid_import_export_and_pv_original_reports_remain_visible():
    data = investigation()
    data["items"].append({"id": "solar_balance", "metrics": {"proof": {
        "grid_w": -6100, "pv_w": 2600, "source_skew_s": 13, "time_aligned": False,
        "source_reports": [report("grid"), report("grid_export"), report("pv", NOW-18)],
        "coverage": {"producer_inventory": "unknown", "storage_inventory": "unknown"}}}})
    _, root = execute(data)
    text = root.text()
    assert "Netrapport" in text and "Injectierapport" in text and "PV-rapport" in text
    assert "13 s" in text and "niet passend" in text and "dekking van productie en opslag is onbekend" in text


@pytest.mark.parametrize("phase,label", [("not_sent", "Niet verzonden"), ("send_uncertain", "Verzending onzeker"),
                                         ("accepted_readback_unconfirmed", "Geaccepteerd, terugmelding niet bevestigd")])
def test_interrupted_research_never_looks_completed_or_borrows_controller_contact_transport(phase, label):
    data = investigation()
    data["items"][4].update(id="sg_policy", metrics={"recent_sessions": [{
        "started_at": NOW-1000, "ended_at": None, "last_observed_at": NOW-900,
        "interrupted": True, "interruption": "restart", "comparable": False,
        "controller_stop": {"ended_at": NOW-850, "reason": "Softstop <img src=x>"},
        "contact_end": {"state": None, "reported_at": None},
        "transport": {"operation": "off", "phase": phase, "category": "timeout"},
        "private_binding": "sensor.never_render"}]})
    _, root = execute(data)
    text = root.text()
    assert "einde onbekend" in text and "niet vergelijkbaar" in text and label in text
    assert "Softstop <img src=x>" in text and "Gemeld SG-contact" in text
    assert not any(n.tag == "img" for n in root.walk()) and "never_render" not in text


def render_pv(data):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for real frontend rendering")
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},input};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
const result=vm.runInContext(`(()=>{const d=Object.create(SolarPilotPVDialog.prototype);
d._data=input;d._days={value:'2026-01-05'};d._scroll={scrollTop:0};d._body={innerHTML:'',querySelectorAll:()=>[]};
d._renderData();return d._body.innerHTML;})()`,sandbox);process.stdout.write(JSON.stringify(result));
"""
    completed = subprocess.run([node, "-e", script, str(CARD)], input=json.dumps(data), capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr
    return Markup(json.loads(completed.stdout)).root


def test_pv_original_quarter_rejection_and_archived_ahead_accuracy_stay_separate():
    data = {"forecast_evidence": {"version": 1, "summary": {"ahead_comparisons": 24, "distinct_days": 4,
        "by_recorded_lead": [{"label": "1–3 uur", "samples": 24, "distinct_days": 4, "mae_w": 900}],
        "planning_margin_comparison": {"status": "comparison_only", "margin_w": 500, "applied": False}}},
        "history": [{"time": "2026-01-05T12:00:00+01:00", "reason": "Ongeldige meting", "actual_w": 580,
            "raw_w": 1700, "accepted": False, "observation_evidence": {"version": 1, "valid_observations": 8,
                "rejected_observations": 1, "rejection_reasons": [{"reason": "invalid", "count": 1}],
                "original_reports": {"distinct": 9, "max_gap_s": 30}, "coverage_note": "<img src=x>"}}]}
    root = render_pv(data)
    text = root.text()
    assert "24 vergelijkingen uit 4 dagen" in text and "uitgiftetijd van de oorspronkelijke provider is onbekend" in text
    assert "Niet toegepast" in text and "8 geldig · 1 afgewezen · 9 verschillende" in text
    assert "30 s" in text and "Ongeldige meting: 1" in text
    assert not any(n.tag == "img" for n in root.walk())


def test_old_pv_quarters_never_receive_new_part_measurement_proof():
    root = render_pv({"history": [{"time": "2026-01-05T12:00:00+01:00", "reason": "Oude registratie"}]})
    assert "Oud kwartier zonder oorspronkelijk deelmeetbewijs" in root.text()
    assert "Vooruit geregistreerd voorspelbewijs is nog niet beschikbaar" in root.text()


def test_live_sg_details_keep_failed_stop_separate_from_later_successful_read():
    from test_heatpump_ui65 import sample
    from test_sg_ui_platforms62 import execute as render_card
    data = sample()
    data["sg_boost"]["last_session"] = {"ended_at": NOW-100, "duration_s": 1500,
        "reason": "Aanhoudende netafname <img src=x>", "transport": {
            "operation": "off", "phase": "send_uncertain", "category": "timeout", "observed_at": NOW-99}}
    data["sg_boost"]["transport_evidence"] = {
        "operation": "read", "phase": "confirmed", "category": "none", "observed_at": NOW-5}
    rendered = render_card(data, view="comfort")
    root = Markup(rendered["initial"]).root
    text = root.text()
    assert "SG-stopbesluit en transport" in text and "Transport bij die stop" in text
    assert "UIT · Verzending onzeker · time-out" in text and "Lezen · Bevestigd" in text
    assert "Aanhoudende netafname <img src=x>" in text and "latere geslaagde lezing" in text
    assert not any(n.tag == "img" for n in root.walk()) and not rendered["calls"]
