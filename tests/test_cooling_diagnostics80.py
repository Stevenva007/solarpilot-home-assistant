"""Cooling explanations use configured fictional read sources, never authority."""
from copy import deepcopy
import json
from pathlib import Path
import shutil
import subprocess
import time
from types import SimpleNamespace

import pytest

from test_general_sg_policy64 import general_fixture, observe
from test_overview_details60 import Markup
from test_sg_observations64 import observed
from test_sg_ui_platforms62 import attributes


def monitor_fixture(mode="auto", action="idle", *, age=0, zones=None):
    runtime, hass = observed(zone_entities=zones or ["climate.fictional_room"])
    for eid in runtime.panasonic.settings["zone_entities"]:
        hass.states.set(eid, mode, {"hvac_action": action,
            "friendly_name": "Fictional room"}, reported_age=age)
    return runtime, hass


@pytest.mark.parametrize("case,expected", [
    ("no_zones", "no_configured_zones"),
    ("missing", "zone_source_missing"),
    ("unavailable", "zone_source_unavailable"),
    ("restored", "zone_source_unavailable"),
    ("estimated", "zone_source_unavailable"),
    ("stale", "zone_source_stale"),
    ("future", "zone_source_stale"),
    ("auto", "auto_program_unknown"),
    ("heat_cool", "auto_program_unknown"),
    ("cool", "cooling_present"),
    ("heat", "heating_only_confirmed"),
    ("off", "cooling_not_excluded"),
])
def test_specific_monitor_source_reason_with_unchanged_cooling_permission(case, expected):
    runtime, hass = monitor_fixture()
    eid = "climate.fictional_room"
    if case == "no_zones":
        runtime.panasonic.settings["zone_entities"] = []
    elif case == "missing":
        hass.states.data.pop(eid)
    elif case in ("unavailable", "heat_cool", "heat", "off", "cool"):
        hass.states.set(eid, case, {"hvac_action": "cooling" if case == "cool" else "idle"})
    elif case in ("restored", "estimated"):
        hass.states.set(eid, "heat", {case: True})
    elif case in ("stale", "future"):
        hass.states.set(eid, "heat", {}, reported_age=121 if case == "stale" else -6)
    before = deepcopy(runtime._snapshot())
    value = runtime.panasonic.overview()
    diagnostic = value["cooling_context_diagnostic"]
    assert diagnostic["code"] == expected
    assert diagnostic["schema"] == 1 and diagnostic["read_only"] is True
    assert value["cooling_possible"] is (case != "heat")
    assert runtime._snapshot() == before and not hass.services.calls


def test_source_rows_keep_raw_report_times_and_provider_reason_without_promoting_proof():
    runtime, hass = monitor_fixture(age=121)
    runtime.panasonic.native_program = SimpleNamespace(read=lambda eid: {
        "entity_id": eid, "program": "heating", "raw_mode": "AUTO_HEAT",
        "source": "aquarea_poll", "fresh": False, "observed_at": time.time() - 500,
        "reason": "Programme poll expired", "reason_code": "stale_poll", "stale_s": 90})
    first = runtime.panasonic.overview()
    second = runtime.panasonic.overview()
    row = first["cooling_context_diagnostic"]["sources"][0]
    assert row["observed_at"] == hass.states.get("climate.fictional_room").last_reported.timestamp()
    assert row["observed_at"] == second["cooling_context_diagnostic"]["sources"][0]["observed_at"]
    assert row["native_raw_mode"] == "AUTO_HEAT" and row["native_reason_code"] == "stale_poll"
    assert row["native_source"] == "aquarea_poll" and row["native_stale_s"] == 90
    assert row["fresh"] is False and row["native_fresh"] is False
    assert row["valid_until"] is None and row["native_valid_until"] is None
    assert first["cooling_possible"] is True and not hass.services.calls


@pytest.mark.parametrize("second,code", [("heating", "heating_only_confirmed"),
    ("cooling", "native_context_conflict"), ("unknown", "auto_program_unknown")])
def test_auto_requires_every_configured_source_and_reports_conflict(second, code):
    runtime, hass = monitor_fixture(zones=["climate.fictional_room", "climate.fictional_other"])
    stamp = hass.states.get("climate.fictional_room").last_reported.timestamp()
    runtime.panasonic.native_program = SimpleNamespace(read=lambda eid: {
        "entity_id": eid, "program": "heating" if eid.endswith("room") else second,
        "raw_mode": "AUTO_HEAT", "source": "aquarea_poll", "fresh": second != "unknown" or eid.endswith("room"),
        "observed_at": stamp, "stale_s": 120})
    value = runtime.panasonic.overview()
    assert value["cooling_context_diagnostic"]["code"] == code
    assert value["cooling_possible"] is (second != "heating")
    assert not hass.services.calls


@pytest.mark.parametrize("action", ["heating", "sterilization", "dhw"])
def test_tank_heat_sterilisation_and_watts_never_fill_missing_cooling_sources(action):
    runtime, hass = observed(tank_target_entity="water_heater.fictional_tank",
        power_entity="sensor.fictional_heatpump", power_scope="total")
    hass.states.set("water_heater.fictional_tank", "on", {"hvac_action": action,
        "temperature": 62, "temperature_unit": "°C"})
    hass.states.set("sensor.fictional_heatpump", 3000, {"unit_of_measurement": "W"})
    value = runtime.panasonic.overview()
    assert value["cooling_context_diagnostic"]["code"] == "no_configured_zones"
    assert value["cooling_possible"] is True
    assert not hass.services.calls


def test_diagnostic_source_rows_and_external_text_are_bounded():
    runtime, hass = monitor_fixture(zones=[f"climate.fictional_{index}" for index in range(20)])
    hass.states.set("climate.fictional_0", "auto", {"friendly_name": "x" * 1000})
    value = runtime.panasonic.overview()["cooling_context_diagnostic"]
    assert len(value["sources"]) == 16 and value["source_count"] == 20
    assert value["sources_truncated"] is True and len(value["sources"][0]["name"]) == 160
    assert not hass.services.calls


def test_missing_source_after_display_cap_still_has_exact_diagnostic_code():
    runtime, hass = monitor_fixture(mode="heat", zones=[f"climate.fictional_{index}" for index in range(20)])
    hass.states.data.pop("climate.fictional_19")
    value = runtime.panasonic.overview()
    assert value["cooling_context_diagnostic"]["code"] == "zone_source_missing"
    assert len(value["cooling_context_diagnostic"]["sources"]) == 16
    assert value["cooling_possible"] is True


@pytest.mark.parametrize("code,fragment", [
    ("no_configured_zones", "gekoppelde Panasonic-ruimtes"),
    ("zone_source_missing", "ontbrekende Panasonic-ruimtebron"),
    ("zone_source_unavailable", "beschikbare Panasonic-ruimtebron"),
    ("zone_source_stale", "actuele Panasonic-ruimtemeldingen"),
    ("native_context_conflict", "bronnen spreken elkaar tegen"),
    ("auto_program_unknown", "programma achter AUTO"),
    ("cooling_present", "Extra SG-koeling niet vrijgegeven"),
])
def test_sg_specific_reasons_cannot_grant_permission(code, fragment):
    manager, adapter, clock, runtime, row = general_fixture()
    row.update(cooling_possible=True, cooling_context_diagnostic={"schema": 1, "code": code})
    manager._native_observation = deepcopy(row)
    assert fragment in manager.cooling_block_reason()
    assert "beveiliging" in manager.cooling_block_reason()
    assert manager.cooling_block_reason(live=True) == manager.cooling_block_reason()
    assert not adapter.calls
    assert manager.settings["cooling_protection_confirmed"] is False


@pytest.mark.asyncio
@pytest.mark.parametrize("profile,confirmed,heating_proof,expected", [
    ("general", False, False, False), ("general", False, True, True),
    ("general", True, False, True), ("dhw_only", False, False, True),
])
async def test_diagnostics_leave_exact_existing_general_and_dhw_gate(profile, confirmed, heating_proof, expected):
    manager, adapter, clock, _, row = general_fixture(cooling_protection_confirmed=confirmed)
    manager.settings["profile"] = profile
    row.update(cooling_possible=not heating_proof,
        cooling_context_diagnostic={"schema": 1, "code": "heating_only_confirmed", "cooling_possible": False})
    await observe(manager, clock, row)
    clock.advance(120)
    await observe(manager, clock, row)
    assert bool(adapter.calls) is expected
    assert manager.settings["cooling_protection_confirmed"] is confirmed


def test_sg_context_expired_reason_does_not_use_stale_heating_diagnostic_as_permission():
    manager, adapter, clock, _, row = general_fixture()
    row["cooling_context_diagnostic"] = {"schema": 1, "code": "heating_only_confirmed"}
    manager._native_observation = deepcopy(row)
    clock.advance(121)
    assert "context verouderd" in manager.cooling_block_reason()
    assert not adapter.calls


def ui(data, view="comfort", elapsed=0):
    node = shutil.which("node")
    assert node, "Actual frontend execution requires Node"
    path = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot/frontend/solar-pilot-card.js"
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
let now=input.now;class FakeDate extends Date {static now(){return now;}}
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},input,Date:FakeDate};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
const result=vm.runInContext(`(()=>{const calls=[],card=Object.create(SolarPilotCard.prototype);card._last={attributes:input.data};card._busy=false;card._error='';card._hass={states:{},config:{time_zone:'Europe/Brussels'},callService:(...args)=>calls.push(args)};const c=card._ctx();return {html:input.view==='overview'?card._decisionBoard(c):input.view==='loads'?card._loads(c):card._comfort(c),state:card._sgCoolingState(c),signature:card._heatpumpDisplaySignature(c),calls};})()`,sandbox);
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run([node, "-e", script, str(path)],
        input=json.dumps({"data": data, "view": view, "now": (time.time() + elapsed) * 1000}),
        text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def ui_fixture(mode="heat"):
    runtime, _ = monitor_fixture(mode=mode)
    value = runtime.panasonic.overview()
    data = attributes(profile="general", cooling_protection_confirmed=False)
    data["panasonic"].update(value)
    data["sg_boost"]["cooling_diagnostic"] = deepcopy(value["cooling_context_diagnostic"])
    return data


@pytest.mark.parametrize("view", ["overview", "comfort", "loads"])
def test_same_readonly_diagnostics_and_safe_action_in_all_three_views(view):
    data = ui_fixture("auto")
    value = ui(data, view)
    root = Markup(value["html"]).root
    diagnostic = next(n for n in root.walk() if "data-sg-cooling-code" in n.attributes)
    assert diagnostic.attributes["data-sg-cooling-code"] == "auto_program_unknown"
    assert "Werkelijk Panasonic-programma" in diagnostic.text()
    assert "Laatste bronmelding" in diagnostic.text() and "Programmabron" in diagnostic.text()
    assert "SG-leesbronnen bekijken" in diagnostic.text()
    assert "Tankopwarming en sterilisatie wijzigen deze koelvoorwaarde niet" in diagnostic.text()
    assert not value["calls"]


def test_frontend_expiry_without_new_homeassistant_report_changes_refresh_signature():
    data = ui_fixture()
    original = deepcopy(data)
    current, expired = ui(data), ui(data, elapsed=121)
    assert current["state"]["code"] == "heating_only_confirmed"
    assert expired["state"]["code"] == "context_expired"
    assert "Koeling uitgesloten door actuele gekoppelde bronnen" not in expired["html"]
    assert "De Panasonic-koelcontext is verouderd" in expired["html"]
    assert expired["signature"] != current["signature"]
    assert data == original and not expired["calls"]


def test_frontend_escapes_every_source_name_and_external_programme_reason():
    data = ui_fixture("auto")
    value = data["sg_boost"]["cooling_diagnostic"]
    value["sources"][0].update(name='<img src=x onerror="attack()">',
        entity_id="climate.<script>attack()</script>", native_reason="<svg onload=attack()>")
    value.update(summary="<script>attack()</script>", action="<img src=x onerror=attack()>")
    rendered = ui(data)
    diagnostic = next(n for n in Markup(rendered["html"]).root.walk() if "data-sg-cooling-code" in n.attributes)
    assert not any(n.tag in ("script", "img", "svg") for n in diagnostic.walk())
    assert "<img" in diagnostic.text() and "<script>" in diagnostic.text()
    assert not rendered["calls"]


def test_confirmed_physical_protection_does_not_relabel_unknown_auto_as_heating_proof():
    data = ui_fixture("auto")
    data["sg_boost"]["cooling_protection_confirmed"] = True
    result = ui(data)
    assert result["state"]["code"] == "auto_program_unknown"
    assert result["state"]["condition"] == "Condens-/dauwpuntbeveiliging lokaal bevestigd"
    assert "Koeling uitgesloten door actuele gekoppelde bronnen" not in result["html"]
    assert not result["calls"]


@pytest.mark.parametrize("profile,confirmed,label", [
    (None, False, "SG-profiel nog niet bekend"), ("unsupported", True, "SG-profiel nog niet bekend"),
    ("dhw_only", False, "Tapwaterprofiel nog niet lokaal bevestigd"),
    ("dhw_only", True, "Koelvoorwaarde niet vereist voor het lokaal bevestigde tapwaterprofiel"),
])
def test_frontend_does_not_invent_a_confirmed_tapwater_profile(profile, confirmed, label):
    data = ui_fixture("auto")
    data["sg_boost"].update(profile=profile, profile_confirmed=confirmed)
    result = ui(data)
    assert result["state"]["condition"] == label and not result["calls"]
    if profile != "dhw_only" or not confirmed:
        assert "Niet vereist voor" not in result["html"]
