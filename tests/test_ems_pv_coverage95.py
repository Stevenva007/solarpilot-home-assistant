"""PV gaps qualify daily figures without creating energy or actuator rights."""
from copy import deepcopy
from datetime import datetime, timedelta
import json
from pathlib import Path
import shutil
import subprocess
from zoneinfo import ZoneInfo

import pytest

from custom_components.solar_pilot.ems import (
    accounting_step, fresh_daily_stats, pv_accounting_overview, pv_coverage_details,
)
from custom_components.solar_pilot.electricity_cost import DailyElectricityCost
from test_runtime import build

DAY = "2026-10-17"
NOW = datetime(2026, 10, 17, 14, tzinfo=ZoneInfo("Europe/Brussels"))
CARD = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot/frontend/solar-pilot-card.js"


def step(stats=None, pv=1000, **overrides):
    args = dict(day=DAY, dt_s=60, grid_w=100, pv_w=pv, managed_w=300,
                battery_discharge_w=0, import_price_eur_kwh=.30, export_price_eur_kwh=.03)
    args.update(overrides)
    return accounting_step(stats or {}, **args)


def legacy():
    stats = step()
    stats.pop("pv_coverage")
    stats["private_neighbor"] = {"keep": [1, 2]}
    return stats


def test_measured_missing_and_genuine_zero_have_distinct_coverage_and_no_invented_sun():
    first = step(); before = deepcopy(first)
    missing = step(first, None)
    assert first == before
    assert missing["pv_kwh"] == first["pv_kwh"]
    assert missing["pv_self_used_kwh"] == first["pv_self_used_kwh"]
    assert missing["managed_solar_kwh"] == first["managed_solar_kwh"]
    assert missing["estimated_value_eur"] == first["estimated_value_eur"]
    assert missing["managed_unattributed_kwh"] == pytest.approx(200*60/3_600_000)
    result = step(missing, 0)
    assert result["pv_coverage"] == {"version":1, "measured_s":120, "missing_s":60, "legacy_unknown_s":0}
    assert result["samples_s"] == 180
    assert result["managed_kwh"] == pytest.approx(sum(result[key] for key in (
        "managed_grid_kwh", "managed_battery_kwh", "managed_solar_kwh", "managed_unattributed_kwh")))
    quality = pv_accounting_overview(result)
    assert quality["pv_partial"] and quality["pv_coverage_pct"] == 66.7
    assert quality["pv_coverage_status"] == "partial"


@pytest.mark.parametrize("bad", [None, True, False, float("nan"), float("inf"), -1, "nan", []])
def test_invalid_pv_does_not_become_measured_zero(bad):
    stats = step(pv=bad)
    assert stats["pv_coverage"]["measured_s"] == 0
    assert stats["pv_coverage"]["missing_s"] == 60
    assert stats["pv_kwh"] == stats["managed_solar_kwh"] == 0
    assert stats["managed_unattributed_kwh"] > 0
    assert pv_accounting_overview(stats)["pv_partial"]


def test_zero_and_complete_coverage_refer_only_to_recorded_ems_periods():
    stats = step(pv=0)
    result = pv_accounting_overview(stats)
    assert result["pv_coverage_s"] == 60 and result["pv_coverage_pct"] == 100
    assert result["pv_coverage_status"] == "complete" and result["pv_partial"] is False
    assert result["self_consumption_pct"] is None
    assert "geregistreerde EMS-meetperioden" in result["pv_coverage_note"]


@pytest.mark.parametrize("override", [{"dt_s":0}, {"dt_s":121}, {"dt_s":True},
    {"grid_w":None}, {"grid_w":float("nan")}, {"managed_w":None}])
def test_rejected_intervals_neither_add_coverage_nor_migrate_legacy(override):
    old = legacy(); before = deepcopy(old)
    assert step(old, **override) == before
    assert old == before


def test_legacy_time_becomes_unknown_once_and_survives_restart_without_touching_totals():
    old = legacy(); before = deepcopy(old)
    read = pv_accounting_overview(old)
    assert old == before and read["pv_legacy_unknown_s"] == 60
    assert read["pv_coverage_status"] == "legacy_unknown" and read["pv_partial"]
    assert read["pv_coverage_pct"] is None  # unknown history is not measured 0% coverage
    new = step(old)
    assert new["private_neighbor"] == before["private_neighbor"]
    assert new["pv_coverage"] == {"version":1, "measured_s":60, "missing_s":0, "legacy_unknown_s":60}
    restored = json.loads(json.dumps(new, allow_nan=False))
    restored = step(restored)
    assert restored["pv_coverage"] == {"version":1, "measured_s":120, "missing_s":0, "legacy_unknown_s":60}
    assert restored["samples_s"] == 180 and old == before
    assert restored["pv_kwh"] == pytest.approx(old["pv_kwh"]*3)


@pytest.mark.parametrize("extension", [
    {"version":99, "private_payload":{"keep":"opaque"}},
    {"version":True, "private_payload":"opaque"},
    {"version":1, "measured_s":60, "missing_s":1, "legacy_unknown_s":0},
    {"version":1, "measured_s":True, "missing_s":0, "legacy_unknown_s":0},
    {"version":1, "measured_s":float("nan"), "missing_s":0, "legacy_unknown_s":0},
    "private_payload",
])
def test_unknown_or_malformed_proof_is_preserved_privately_and_never_repaired_to_complete(extension):
    old = step(); old["pv_coverage"] = deepcopy(extension)
    new = step(old)
    assert new["pv_coverage"] is old["pv_coverage"]
    assert new["samples_s"] == 120 and new["pv_kwh"] > old["pv_kwh"]
    quality = pv_accounting_overview(new)
    assert quality["pv_coverage_status"] == "unknown" and quality["pv_partial"]
    assert quality["pv_coverage_s"] is quality["pv_coverage_pct"] is None
    assert "private_payload" not in json.dumps(quality, allow_nan=False)


def test_known_neighbor_fields_remain_private_and_day_rollover_does_not_rewrite_old_record():
    old = step(); old["pv_coverage"]["private_payload"] = {"keep":[1]}
    before = deepcopy(old)
    new = step(old)
    assert new["pv_coverage"]["private_payload"] == before["pv_coverage"]["private_payload"]
    assert "private_payload" not in json.dumps(pv_accounting_overview(new))
    tomorrow = step(old, day="2026-10-18")
    assert tomorrow["pv_coverage"] == {"version":1,"measured_s":60,"missing_s":0,"legacy_unknown_s":0}
    assert old == before


def test_runtime_overview_and_analysis_export_report_quality_without_mutating_private_stats():
    runtime, hass = build(); runtime.ems_stats = step(step(), None)
    before = deepcopy(runtime.ems_stats); calls = list(hass.services.calls)
    today = runtime.ems_overview()["today"]
    exported = runtime.analysis.build(include_names=True)["components"]["energy_planning_climate"]["today"]
    assert today["pv_partial"] and today["pv_coverage_s"] == today["pv_missing_s"] == 60
    assert exported["pv_coverage_status"] == today["pv_coverage_status"]
    assert exported["pv_coverage_note"] == today["pv_coverage_note"]
    assert runtime.ems_stats == before and hass.services.calls == calls


@pytest.mark.asyncio
async def test_runtime_accepts_p1_accounting_while_pv_is_missing_then_records_real_zero():
    runtime, hass = build(settings={"pv_entity":"sensor.pv"})
    hass.states.set("sensor.pv", "unavailable", {"unit_of_measurement":"W"})
    runtime.last_tick -= 60
    await runtime.tick()
    first = deepcopy(runtime.ems_stats)
    assert first["samples_s"] >= 60 and first["site_export_kwh"] > 0
    assert first["pv_coverage"]["missing_s"] == first["samples_s"]
    assert first["pv_coverage"]["measured_s"] == 0
    hass.states.set("sensor.pv", 0, {"unit_of_measurement":"W"})
    runtime.last_tick -= 60
    await runtime.tick()
    proof = pv_coverage_details(runtime.ems_stats)
    assert proof["measured_s"] >= 60 and proof["missing_s"] == first["samples_s"]
    assert runtime.ems_overview()["today"]["pv_partial"]
    assert hass.services.calls == []


def test_real_card_shows_partial_coverage_note_alongside_existing_percentage():
    node = shutil.which("node")
    if not node: pytest.skip("Node required for actual card rendering")
    today = pv_accounting_overview(step(step(), None))
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),today=JSON.parse(fs.readFileSync(0,'utf8'));
const s={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},today};
vm.createContext(s);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),s);
const html=vm.runInContext(`(()=>{const card=Object.create(SolarPilotCard.prototype);
for(const name of ['_energyTile','_wallboxPriorityControl','_decisionBoard','_activeLoads','_savings'])card[name]=()=>'';
return card._overview({a:{},panasonic:{},sgBoost:{},wb:{},cap:{},forecast:{},localPv:{},batteryFleet:{},batteryAnalysis:{},phase:{},today,planner:{},ems:{}});})()`,s);
process.stdout.write(html);
"""
    result = subprocess.run([node,"-e",script,str(CARD)], input=json.dumps(today), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    assert "Zelfconsumptie vandaag" in result.stdout
    assert "Onvolledige PV-meetdekking: 50.0%" in result.stdout


@pytest.mark.parametrize("kind", ["legacy", "known_partial", "unknown_extension"])
def test_electricity_seed_preserves_totals_without_inventing_pv_coverage(kind):
    stats = legacy() if kind == "legacy" else step(step(), None)
    if kind == "unknown_extension": stats["pv_coverage"] = {"version":99,"private_payload":"keep"}
    before = deepcopy(stats); ledger = DailyElectricityCost()
    ledger.seed_legacy(stats, NOW, .30, .03)
    proof = pv_coverage_details(stats)
    assert ledger.data["pv_coverage_s"] == (proof["measured_s"] if proof else 0)
    assert ledger.data["pv_kwh"] == stats["pv_kwh"]
    assert ledger.data["direct_pv_kwh"] == stats["pv_self_used_kwh"]
    result = ledger.overview(NOW)
    assert result["pv_partial"] and result["pv_kwh"] == pytest.approx(stats["pv_kwh"], abs=1e-6)
    assert result["legacy_pv_coverage_unknown"] == (kind != "known_partial")
    if kind != "known_partial": assert "eerdere PV-meetdekking onbekend" in result["solar_note"]
    assert stats == before
    restored = DailyElectricityCost(); restored.restore(ledger.snapshot())
    assert restored.snapshot() == ledger.snapshot()


def test_complete_new_ems_seed_and_existing_valid_cost_restore_keep_their_proof():
    stats = step(pv=0); ledger = DailyElectricityCost(); ledger.seed_legacy(stats,NOW,.30,.03)
    assert ledger.data["pv_coverage_s"] == 60
    assert ledger.overview(NOW)["pv_partial"] is False
    ledger.update(now=NOW,grid_w=1000,pv_w=2000,import_price=.30,export_price=.03)
    ledger.update(now=NOW+timedelta(seconds=60),grid_w=1000,pv_w=2000,import_price=.30,export_price=.03)
    saved = ledger.snapshot(); restored = DailyElectricityCost(); restored.restore(saved)
    restored.seed_legacy(legacy(),NOW,.30,.03)
    assert restored.snapshot() == saved


def test_unknown_cost_version_stays_opaque_when_ems_seed_or_new_readings_arrive():
    opaque = {"version":99,"private_payload":{"keep":[1]}}
    ledger = DailyElectricityCost(); ledger.restore(opaque)
    ledger.seed_legacy(legacy(),NOW,.30,.03)
    ledger.update(now=NOW,grid_w=1000,pv_w=2000,import_price=.30,export_price=.03)
    assert ledger.snapshot() == opaque
