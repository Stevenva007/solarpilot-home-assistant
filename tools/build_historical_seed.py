#!/usr/bin/env python3
"""Build an aggregate SolarPilot historical bootstrap from exported CSV files.

Inputs are read-only. Output intentionally contains aggregate learning data only,
not the original high-resolution household history. The bootstrap is advisory;
realtime SolarPilot control never depends on it.
"""
from __future__ import annotations
import argparse, csv, json, math, statistics
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo


def finite(v):
    try:
        x=float(v); return x if math.isfinite(x) else None
    except (TypeError,ValueError): return None


def percentile(values, q):
    vals=sorted(float(x) for x in values if finite(x) is not None)
    if not vals: return None
    pos=(len(vals)-1)*q; lo=int(math.floor(pos)); hi=int(math.ceil(pos))
    return vals[lo] if lo==hi else vals[lo]+(vals[hi]-vals[lo])*(pos-lo)


def parse_iso(value):
    try:
        value=value.replace("Z","+00:00")
        return datetime.fromisoformat(value)
    except Exception: return None


def ha_profiles(path, pv_entity, forecast_entity, tz_name="Europe/Brussels", sunny_threshold_w=7000):
    tz=ZoneInfo(tz_name)
    hourly={pv_entity:defaultdict(list), forecast_entity:defaultdict(list)}
    start=end=None
    with open(path,newline="",encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            entity=row.get("entity_id")
            if entity not in hourly: continue
            x=finite(row.get("state")); dt=parse_iso(row.get("last_changed", ""))
            if x is None or dt is None: continue
            if dt.tzinfo is None: dt=dt.replace(tzinfo=ZoneInfo("UTC"))
            local=dt.astimezone(tz); key=local.replace(minute=0,second=0,microsecond=0)
            hourly[entity][key].append(x)
            start=dt if start is None or dt<start else start; end=dt if end is None or dt>end else end
    pv={k:statistics.fmean(v) for k,v in hourly[pv_entity].items() if v}
    fc={k:statistics.fmean(v) for k,v in hourly[forecast_entity].items() if v}
    daily=defaultdict(list)
    for dt,w in pv.items(): daily[dt.date()].append(w)
    peaks={d:max(vals) for d,vals in daily.items() if vals}
    sunny={d for d,p in peaks.items() if p>sunny_threshold_w}
    normalized=defaultdict(list); ratios=defaultdict(list)
    for dt,w in pv.items():
        peak=peaks.get(dt.date(),0)
        if dt.date() in sunny and peak>0: normalized[dt.hour].append(w/peak)
        f=fc.get(dt)
        if f is not None and f>=300 and 0<=w/f<10: ratios[dt.hour].append(w/f)
    return {
        "start": None if start is None else start.isoformat(), "end": None if end is None else end.isoformat(),
        "sunny_days":len(sunny),
        "normalized":{str(h):round(statistics.median(v)*100,2) for h,v in sorted(normalized.items())},
        "ratios":{str(h):round(statistics.median(v),3) for h,v in sorted(ratios.items())},
    }


def battery_sim(intervals, capacity, power, rte=.90):
    eta=math.sqrt(max(.5,min(1.0,rte))); soc=avoided=used=0.0
    for imp,exp,hours in intervals:
        limit=power*hours
        charge=min(exp,limit,max(0,(capacity-soc)/eta)); soc+=charge*eta; used+=charge
        discharge=min(imp,limit,max(0,soc*eta)); soc-=discharge/eta; avoided+=discharge
    return avoided,used


def homewizard(path, rte=.90):
    rows=[]
    with open(path,newline="",encoding="utf-8-sig") as f:
        for r in csv.DictReader(f):
            try: dt=datetime.strptime(r["time"],"%Y-%m-%d %H:%M")
            except Exception: continue
            vals={k:finite(r.get(k)) for k in ("Import T1 kWh","Import T2 kWh","Export T1 kWh","Export T2 kWh","L1 max W","L2 max W","L3 max W")}
            if any(vals[k] is None for k in ("Import T1 kWh","Import T2 kWh","Export T1 kWh","Export T2 kWh")): continue
            rows.append((dt,vals))
    rows.sort(key=lambda x:x[0])
    intervals=[]; phase_values={k:[] for k in ("L1 max W","L2 max W","L3 max W")}; heavy={k:0 for k in phase_values}
    total_imp=total_exp=0.0
    for idx,(dt,v) in enumerate(rows):
        for k in phase_values:
            if v[k] is not None: phase_values[k].append(v[k])
        if idx==0: continue
        pdt,pv=rows[idx-1]; hours=(dt-pdt).total_seconds()/3600
        if not 0<hours<=1: continue
        imp=max(0,(v["Import T1 kWh"]+v["Import T2 kWh"])-(pv["Import T1 kWh"]+pv["Import T2 kWh"]))
        exp=max(0,(v["Export T1 kWh"]+v["Export T2 kWh"])-(pv["Export T1 kWh"]+pv["Export T2 kWh"]))
        intervals.append((imp,exp,hours)); total_imp+=imp; total_exp+=exp
        vals=[v[k] for k in phase_values]
        if all(x is not None for x in vals):
            for i,k in enumerate(phase_values):
                if vals[i]>3000 and all(vals[j]<1000 for j in range(3) if j!=i): heavy[k]+=1
    phase_stats={}
    for k,vals in phase_values.items():
        pos=[x for x in vals if x>0]
        phase_stats[k]={"max_import_w":round(max(vals),1) if vals else None,
                        "p95_import_w":round(percentile(pos,.95),2) if pos else None,
                        "p99_import_w":round(percentile(pos,.99),2) if pos else None,
                        "median_positive_w":round(statistics.median(pos),1) if pos else None,
                        "max_export_w_abs":round(abs(min(vals)),1) if vals else None}
    scenarios=[]
    for cap in (5,10,15,20):
        for power in (3,5,10):
            avoided,used=battery_sim(intervals,cap,power,rte)
            scenarios.append({"capacity_kwh":cap,"power_kw":power,"avoided_import_kwh":round(avoided,1),"used_export_kwh":round(used,1)})
    days=(rows[-1][0]-rows[0][0]).total_seconds()/86400 if len(rows)>1 else 0
    return {"start":rows[0][0].isoformat() if rows else None,"end":rows[-1][0].isoformat() if rows else None,
            "days":round(days,2),"import_kwh":round(total_imp,3),"export_kwh":round(total_exp,3),
            "phase_stats":phase_stats,"heavy":heavy,"scenarios":scenarios}


def build(ha_path, hw_path, pv_entity, forecast_entity):
    ha=ha_profiles(ha_path, pv_entity, forecast_entity); hw=homewizard(hw_path)
    return {
        "format":"solarpilot-historical-analysis-v1",
        "source":{"ha_history_start":ha["start"],"ha_history_end":ha["end"],"homewizard_start":hw["start"],"homewizard_end":hw["end"],"sunny_days_used":ha["sunny_days"]},
        "pv_profile":{"median_normalized_pct_by_hour":ha["normalized"],"median_actual_to_forecast_ratio_by_hour":ha["ratios"],
                      "note":"Uurlijkse historische bootstrap; live SolarPilot leert later primair op zonnestand en verschillende dagen."},
        "grid":{"period_days":hw["days"],"import_kwh":hw["import_kwh"],"export_kwh":hw["export_kwh"],
                "avg_import_kwh_day":round(hw["import_kwh"]/hw["days"],2) if hw["days"] else None,
                "avg_export_kwh_day":round(hw["export_kwh"]/hw["days"],2) if hw["days"] else None},
        "phases":{"stats":hw["phase_stats"],"intervals_over_3kw_while_other_phases_under_1kw":hw["heavy"],
                  "note":"HomeWizard Lx max W is a 15-minute phase peak, not phase energy or average power."},
        "battery_upper_bound":{"round_trip_efficiency":.90,"scenarios":hw["scenarios"],
                               "note":"Technical what-if based on measured import/export; no financial or annual-return guarantee."}
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--ha-history",required=True); ap.add_argument("--homewizard",required=True); ap.add_argument("--output",required=True)
    ap.add_argument("--pv-entity", default="sensor.pv_power", help="PV power entity_id in the Home Assistant CSV")
    ap.add_argument("--forecast-entity", default="sensor.solar_forecast_power_now", help="Forecast power entity_id in the Home Assistant CSV")
    args=ap.parse_args(); data=build(args.ha_history,args.homewizard,args.pv_entity,args.forecast_entity)
    Path(args.output).write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    print(f"Wrote {args.output}: {data['source']['sunny_days_used']} sunny days, {data['grid']['period_days']} HomeWizard days")
if __name__=="__main__": main()
