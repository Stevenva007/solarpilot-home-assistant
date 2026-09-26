#!/usr/bin/env python3
"""Offline SolarPilot planner replay / setting comparison.

Examples:
  python tools/backtest_unified_planner.py history.csv output.json
  python tools/backtest_unified_planner.py history.csv output.json \
      --devices examples/backtest_devices.example.json
  python tools/backtest_unified_planner.py history.csv output.json \
      --devices examples/backtest_devices.example.json \
      --setting capacity_penalty_eur_kwh=1.0 --days 30

The tool uses measured historical PV + P1 as a common replay background and can
run the *same* UnifiedPlanner with a current and proposed setting. It is useful
for directional comparisons, not for claiming realised euro savings: historical
appliance readiness/occupancy/thermal state cannot be reconstructed perfectly.
"""
from __future__ import annotations

import argparse
from datetime import datetime
import importlib.util
import json
import math
from pathlib import Path
import statistics
import sys
import types

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]


def _load_planner_module():
    pkg_name = "solar_pilot_backtest"
    pkg = types.ModuleType(pkg_name)
    pkg.__path__ = [str(ROOT / "custom_components" / "solar_pilot")]
    sys.modules[pkg_name] = pkg
    for short in ("planner_quality", "unified_planner"):
        name = f"{pkg_name}.{short}"
        spec = importlib.util.spec_from_file_location(name, ROOT / "custom_components" / "solar_pilot" / f"{short}.py")
        mod = importlib.util.module_from_spec(spec)
        assert spec.loader is not None
        sys.modules[name] = mod
        spec.loader.exec_module(mod)
    return sys.modules[f"{pkg_name}.unified_planner"]


planner_mod = _load_planner_module()
UnifiedPlanner = planner_mod.UnifiedPlanner
DEFAULTS = planner_mod.UNIFIED_PLANNER_DEFAULTS


def _parse_value(raw: str):
    low = raw.strip().lower()
    if low in {"true", "on", "aan", "yes"}: return True
    if low in {"false", "off", "uit", "no"}: return False
    try:
        f = float(raw)
        return int(f) if f.is_integer() else f
    except ValueError:
        return raw


def _parse_setting(text: str):
    if "=" not in text:
        raise argparse.ArgumentTypeError("Gebruik sleutel=waarde, bv. capacity_penalty_eur_kwh=1.0")
    key, raw = text.split("=", 1)
    key = key.strip()
    if key not in planner_mod.PLANNER_SETTING_SPECS:
        raise argparse.ArgumentTypeError(f"Onbekende plannerinstelling: {key}")
    return key, _parse_value(raw)


def _entity_hourly(df, eid):
    g = df[df.entity_id.eq(eid)][["ts", "state"]].copy()
    g["v"] = pd.to_numeric(g.state, errors="coerce")
    return g.dropna(subset=["ts", "v"]).set_index("ts")["v"].resample("1h").mean()


def _load_devices(path):
    if not path:
        return [], {}
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(raw, list):
        return raw, {}
    if not isinstance(raw, dict):
        raise ValueError("Device-profiel moet een JSON-lijst of object zijn")
    return list(raw.get("devices") or []), dict(raw.get("planner_settings") or {})


def _device_for_day(d):
    power = max(1.0, float(d.get("power_w", d.get("nominal_w", 1000)) or 1000))
    req = max(
        0.0,
        float(d.get("daily_energy_goal_kwh", 0) or 0),
        float(d.get("min_daily_runtime_s", 0) or 0) * power / 3_600_000.0,
    )
    if d.get("contiguous_cycle"):
        req = max(req, float(d.get("cycle_energy_kwh", 0) or 0))
    return {**d, "enabled": bool(d.get("enabled", True)), "required_kwh": req, "power_w": power}


def _simulate(days, devices, settings, import_price, export_price, capacity_target_w=None):
    totals = {"days": 0, "import_kwh": 0.0, "export_kwh": 0.0, "cost_eur": 0.0,
              "peak_w": 0.0, "planned_kwh": 0.0, "unmet_kwh": 0.0}
    daily = []
    for day, frame in days:
        if len(frame) < 18:
            continue
        # Use measured hourly values as an oracle replay background. Missing hours
        # are interpolated only within the same day; edge gaps become zero PV and
        # the nearest available base-load estimate.
        idx = pd.date_range(pd.Timestamp(day, tz="UTC"), periods=24, freq="1h")
        frame = frame.reindex(idx)
        pv = frame["pv_w"].interpolate(limit_direction="both").fillna(0).clip(lower=0)
        base = frame["house_w"].interpolate(limit_direction="both").fillna(frame["house_w"].median() if frame["house_w"].notna().any() else 0).clip(lower=0)
        seed = {"base_load_profile": {"median_w_by_hour": {str(h): float(base.iloc[h]) for h in range(24)}}}
        p = UnifiedPlanner({**DEFAULTS, **settings, "horizon_h": 24, "slot_min": 60,
                            "replay_enabled": False, "quality_tracking": False}, seed)
        devs = [_device_for_day(d) for d in devices]
        plan = p.build(
            local_now=idx[0].to_pydatetime(),
            pv_hourly_w=[float(x) for x in pv],
            import_prices=[import_price] * 24,
            export_prices=[export_price] * 24,
            devices=devs,
            capacity_target_w=capacity_target_w,
            battery=None,
        )
        peak = max([max(0.0, s.net_after_plan_w) for s in plan.slots] or [0.0])
        planned = sum(x.planned_kwh for x in plan.devices.values())
        required = sum(x.required_kwh for x in plan.devices.values())
        row = {
            "date": str(day), "import_kwh": round(plan.predicted_import_kwh, 3),
            "export_kwh": round(plan.predicted_export_kwh, 3), "cost_eur": round(plan.predicted_cost_eur, 3),
            "peak_w": round(peak, 1), "planned_kwh": round(planned, 3), "unmet_kwh": round(max(0, required-planned), 3),
        }
        daily.append(row)
        totals["days"] += 1
        for k in ("import_kwh", "export_kwh", "cost_eur", "planned_kwh", "unmet_kwh"):
            totals[k] += row[k]
        totals["peak_w"] = max(totals["peak_w"], row["peak_w"])
    for k in ("import_kwh", "export_kwh", "cost_eur", "planned_kwh", "unmet_kwh"):
        totals[k] = round(totals[k], 3)
    totals["peak_w"] = round(totals["peak_w"], 1)
    return totals, daily


def main():
    ap = argparse.ArgumentParser(description="SolarPilot Unified Planner historische replay")
    ap.add_argument("history_csv", type=Path)
    ap.add_argument("output_json", type=Path)
    ap.add_argument("--devices", type=Path, help="JSON met expliciete flexlastprofielen")
    ap.add_argument("--setting", action="append", default=[], type=_parse_setting,
                    help="Voorgestelde plannerwijziging sleutel=waarde; mag meermaals")
    ap.add_argument("--days", type=int, default=30, help="Aantal recentste voldoende complete dagen")
    ap.add_argument("--import-price", type=float, default=.30)
    ap.add_argument("--export-price", type=float, default=.03)
    ap.add_argument("--capacity-target-w", type=float, default=None,
                    help="Optioneel kwartierpiekdoel voor de plannerreplay, bv. 3500")
    ap.add_argument("--pv-entity", default="sensor.pv_power", help="PV power entity_id in the CSV")
    ap.add_argument("--grid-entity", default="sensor.grid_power", help="Net power entity_id in the CSV")
    args = ap.parse_args()

    df = pd.read_csv(args.history_csv, low_memory=False)
    df["ts"] = pd.to_datetime(df["last_changed"], utc=True, errors="coerce")
    pv = _entity_hourly(df, args.pv_entity)
    grid = _entity_hourly(df, args.grid_entity)
    x = pd.concat([pv.rename("pv_w"), grid.rename("grid_w")], axis=1).dropna()
    if x.empty:
        raise SystemExit("Geen gezamenlijke PV/P1-historie gevonden")
    x["house_w"] = (x.pv_w + x.grid_w).clip(lower=0)
    grouped = [(d, g[["pv_w", "grid_w", "house_w"]]) for d, g in x.groupby(x.index.date)]
    complete = [(d, g) for d, g in grouped if len(g) >= 18]
    complete = complete[-max(2, int(args.days)):]

    devices, settings_from_file = _load_devices(args.devices)
    current_settings = {**DEFAULTS, **settings_from_file}
    proposed_settings = dict(current_settings)
    for key, value in args.setting:
        proposed_settings[key] = value

    current, current_daily = _simulate(complete, devices, current_settings, args.import_price, args.export_price, args.capacity_target_w)
    proposed = proposed_daily = None
    if args.setting:
        proposed, proposed_daily = _simulate(complete, devices, proposed_settings, args.import_price, args.export_price, args.capacity_target_w)

    profile = {
        "median_pv_w_by_hour": {str(int(k)): round(float(v), 1) for k, v in x.groupby(x.index.hour).pv_w.median().items()},
        "median_house_w_by_hour": {str(int(k)): round(float(v), 1) for k, v in x.groupby(x.index.hour).house_w.median().items()},
    }
    out = {
        "format": "solarpilot-unified-planner-backtest-v2",
        "source": args.history_csv.name,
        "period": {"from": x.index.min().isoformat(), "to": x.index.max().isoformat(), "replay_days": len(complete)},
        "devices_file": args.devices.name if args.devices else None,
        "devices": devices,
        "capacity_target_w": args.capacity_target_w,
        "profile": profile,
        "current": {"settings": {k: current_settings.get(k) for k in planner_mod.PLANNER_SETTING_SPECS}, "totals": current, "daily": current_daily},
        "limitations": [
            "Historische apparaat-vrijgave, bezetting en thermische toestand zijn niet volledig reconstrueerbaar.",
            "Gemeten huislast bevat historische echte verbruikers; toegevoegde flexprofielen zijn daarom een what-if bovenop dezelfde achtergrond.",
            "Oudere Home Assistant-data is hoofdzakelijk uurlijkse langetermijnhistorie; deze tool gebruikt daarom 60-minutenblokken.",
            "Resultaten zijn richtinggevend voor plannerinstellingen en geen gerealiseerde besparing of factuurgarantie.",
        ],
    }
    if proposed is not None:
        delta = {}
        for k in ("import_kwh", "export_kwh", "cost_eur", "planned_kwh", "unmet_kwh", "peak_w"):
            delta[k] = round(proposed[k] - current[k], 3)
        out["proposed"] = {
            "changes": {k: v for k, v in args.setting},
            "settings": {k: proposed_settings.get(k) for k in planner_mod.PLANNER_SETTING_SPECS},
            "totals": proposed, "delta_vs_current": delta, "daily": proposed_daily,
        }
    args.output_json.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    print(args.output_json)


if __name__ == "__main__":
    main()
