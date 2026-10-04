"""Versioned, bounded 15-minute PV calibration, separate from realtime dispatch.

A factor is an empirical forecast correction, NOT proof of structural shadow.
Only repeated comparable, calm, non-clipped days support a correction.
"""
from __future__ import annotations
from collections import deque, Counter
from copy import deepcopy
from datetime import datetime, timezone
from statistics import median
import math
import calendar
from .pv_forecast_source import finite

PRESETS = {"slow": (.025, 7), "normal": (.05, 5), "responsive": (.075, 5)}


def solar_position(dt, latitude, longitude):
    """NOAA fractional-year approximation; sufficient for coarse learning bins.

    No location network request, no atmospheric-refraction promise. HA coordinates
    stay internal. Tests also allow explicit solar azimuth/elevation instead.
    """
    lat, lon = finite(latitude), finite(longitude)
    if lat is None or lon is None or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        return None, None
    utc=dt.astimezone(timezone.utc); hour=utc.hour+utc.minute/60+utc.second/3600
    g=2*math.pi/(366 if calendar.isleap(utc.year) else 365)*(utc.timetuple().tm_yday-1+(hour-12)/24)
    eq=229.18*(.000075+.001868*math.cos(g)-.032077*math.sin(g)-.014615*math.cos(2*g)-.040849*math.sin(2*g))
    dec=.006918-.399912*math.cos(g)+.070257*math.sin(g)-.006758*math.cos(2*g)+.000907*math.sin(2*g)-.002697*math.cos(3*g)+.00148*math.sin(3*g)
    ha=math.radians(((hour*60+eq+4*lon)%1440)/4-180); phi=math.radians(lat)
    cosz=max(-1,min(1,math.sin(phi)*math.sin(dec)+math.cos(phi)*math.cos(dec)*math.cos(ha)))
    el=90-math.degrees(math.acos(cosz))
    az=(math.degrees(math.atan2(math.sin(ha),math.cos(ha)*math.sin(phi)-math.tan(dec)*math.cos(phi)))+180)%360
    return az,el


class PVCalibration:
    VERSION=1
    def __init__(self, settings):
        self.settings=settings; self.bins={}; self.history=deque(maxlen=2880)
        self.counts=Counter(); self.window=None; self.samples=[]; self.started=None
        self.last_observation=None; self.last_meter_stamp=None; self.binding=None
        self.last_reason="Wachten op meetgegevens"; self.revision=0

    def _keys(self, dt, az, el):
        # Two-month season bands + sun position. Clock bins are fallback, not a
        # permanent 16:00 correction. Separate seasonal bins avoid mixing winter.
        season=(dt.month-1)//2
        clock=f"{season}:clock:{dt.hour*4+dt.minute//15}"
        az,el=finite(az),finite(el)
        return ([f"{season}:sun:{int(az//10)}:{int(el//5)}", clock]
                if az is not None and el is not None and 0<=az<360 and -90<=el<=90 else [clock])

    def factor(self, dt, az=None, el=None):
        if not self.settings.get("calibration_enabled"):
            return 1.,0.,0,"Lokale kalibratie uit"
        keys=self._keys(dt,az,el) if self.settings.get("shadow_enabled",True) else ["global"]
        for key in keys:
            entry=self.bins.get(key,{})
            days=entry.get("days",{})
            vals=[median(v) for d,v in days.items() if v and 0 <= (dt.date()-datetime.fromisoformat(d).date()).days <= 120]
            minimum=max(int(self.settings.get("minimum_days",5)),PRESETS.get(self.settings.get("learning_preset"),PRESETS["normal"])[1])
            if len(vals)<minimum:
                continue
            m=median(vals); mad=median([abs(x-m) for x in vals])
            confidence=min(.95,len(vals)/12)*max(0.,1-3*mad/max(m,.1))
            if confidence<.4:
                return 1.,confidence,len(vals),"Vergelijkbare dagen te wisselend; ruwe forecast behouden"
            return entry.get("factor",1.),confidence,len(vals),"Zonnestand + seizoen" if ":sun:" in key else "Tijdvak + seizoen" if ":clock:" in key else "Globale kalibratie"
        return 1.,0.,0,"Nog onvoldoende vergelijkbare dagen; ruwe forecast behouden"

    def observe(self, *, now, actual_w, raw_w, meter_stamp, azimuth=None, elevation=None, binding=""):
        ts=now.timestamp()
        meter_stamp=finite(meter_stamp)
        if self.started is None or ts<self.started:
            self.started=ts; self.window=None; self.samples=[]
            self.last_observation=None; self.last_meter_stamp=None
        if self.binding is None:
            self.binding=binding
        elif binding != self.binding:
            # Changed physical/forecast binding must not apply incompatible factors.
            self.bins={}; self.binding=binding; self.samples=[]; self.window=None
            self.counts["source_changed"]+=1; self.revision+=1
        bucket=int(ts//900)
        if self.window is not None and bucket!=self.window:
            self._finish(now.tzinfo)
            self.samples=[]
        self.window=bucket
        if self.last_observation is not None and 0<=ts-self.last_observation<55:
            return
        self.last_observation=ts
        actual,raw=finite(actual_w),finite(raw_w)
        reason=""
        if not self.settings.get("calibration_enabled"):
            reason="Kalibratie uitgeschakeld"
        elif ts-self.started<600:
            reason="Opstartstabilisatie (10 minuten)"
        elif actual is None or raw is None or actual<0 or raw<0:
            reason="Ontbrekende of ongeldige PV-/forecastmeting"
        elif (meter_stamp is None or not -5 <= ts-meter_stamp <= 120
              or (self.last_meter_stamp is not None and meter_stamp<=self.last_meter_stamp)):
            reason="Geen verse onafhankelijke PV-meting"
        elif actual>float(self.settings["inverter_limit_w"])*1.1:
            reason="Vermogen boven fysieke omvormergrens; outlier"
        elif max(actual,raw)>=float(self.settings["inverter_limit_w"])*.98:
            reason="Omvormerbegrenzing/clipping; niet als schaduw leren"
        elif raw<400 or (finite(elevation) is not None and elevation<3):
            reason="Te weinig zon voor betrouwbare verhouding"
        elif not .15 <= actual/raw <= 1.6:
            reason="Afwijkende verhouding; outlier of dichte bewolking"
        if (meter_stamp is not None and -5<=ts-meter_stamp<=120
                and (self.last_meter_stamp is None or meter_stamp>self.last_meter_stamp)):
            self.last_meter_stamp=meter_stamp
        factor,_,_,_=self.factor(now,azimuth,elevation)
        self.samples.append({"ts":ts,"actual":actual,"raw":raw,"factor":factor,"az":finite(azimuth),"el":finite(elevation),"reason":reason})
        self.samples=self.samples[-20:]
        self.last_reason=reason or "Kwartiermetingen verzamelen"

    def _finish(self, tz):
        rows=self.samples
        if not rows:
            return
        good=[r for r in rows if not r["reason"]]
        reasons=Counter(r["reason"] for r in rows if r["reason"])
        reason=""
        if reasons:
            # A clipped/cloudy/missing part cannot be selected away to cherry-pick
            # the calm tail of a quarter. The whole interval is rejected.
            reason=reasons.most_common(1)[0][0]
        elif len(good)<12 or good[-1]["ts"]-good[0]["ts"]<660 or any(b["ts"]-a["ts"]>120 for a,b in zip(good,good[1:])):
            reason="Onvoldoende kwartierdekking (minimaal 12 verse metingen)"
        if not reason:
            ratios=[r["actual"]/r["raw"] for r in good]
            m=median(ratios)
            jumps=[abs(b["actual"]-a["actual"])/max(a["actual"],b["actual"],400) for a,b in zip(good,good[1:])]
            if max(jumps,default=0)>.3 or (max(ratios)-min(ratios))/max(m,.1)>.3:
                reason="Snel wisselende bewolking; geen structurele correctie leren"
        finite_rows=[r for r in rows if r["actual"] is not None and r["raw"] is not None]
        mid=rows[len(rows)//2];dt=datetime.fromtimestamp(mid["ts"],tz)
        actual=median([r["actual"] for r in finite_rows]) if finite_rows else None
        raw=median([r["raw"] for r in finite_rows]) if finite_rows else None
        applied=median([r["factor"] for r in rows]); corrected=min(self.settings["inverter_limit_w"],raw*applied) if raw is not None else None
        accepted=not reason
        if accepted:
            value=median([r["actual"]/r["raw"] for r in good]);day=dt.date().isoformat()
            for key in [*self._keys(dt,mid["az"],mid["el"]),"global"]:
                entry=self.bins.setdefault(key,{"days":{},"factor":1.,"updated_day":None})
                vals=entry["days"].setdefault(day,[]);vals.append(value);del vals[:-8]
                for old in [d for d in sorted(entry["days"]) if (dt.date()-datetime.fromisoformat(d).date()).days>120] + sorted(entry["days"])[:-45]:
                    entry["days"].pop(old,None)
                rate,min_days=PRESETS.get(self.settings.get("learning_preset"),PRESETS["normal"])
                if len(entry["days"])>=max(min_days,self.settings.get("minimum_days",5)) and entry["updated_day"]!=day:
                    target=max(.35,min(1.25,median([median(v) for v in entry["days"].values()])))
                    old=entry["factor"];entry["factor"]=max(old-rate,min(old+rate,target));entry["updated_day"]=day
            reason="Gebruikt: rustig, volledig kwartier zonder clipping"
        self.counts["accepted" if accepted else "rejected"]+=1
        self.history.append({"time":dt.isoformat(),"raw_w":raw,"corrected_w":corrected,"actual_w":actual,
            "error_w":round(actual-raw,1) if actual is not None and raw is not None else None,
            "error_pct":round((actual-raw)/raw*100,1) if actual is not None and raw is not None and raw>=400 else None,
            "factor":round(applied,3),"accepted":accepted,"reason":reason,"samples":len(rows)})
        cutoff=dt.timestamp()-min(30,max(1,int(self.settings.get("history_days",30))))*86400
        while self.history and datetime.fromisoformat(self.history[0]["time"]).timestamp()<cutoff:
            self.history.popleft()
        # Bound across seasonal bins; each bin retains at most 45 distinct days.
        if len(self.bins)>1600:
            for k in list(self.bins)[:len(self.bins)-1600]:del self.bins[k]
        self.last_reason=reason;self.revision+=1

    def snapshot(self):
        return {"version":self.VERSION,"binding":self.binding,"bins":deepcopy(self.bins),
                "history":deepcopy(list(self.history)),"counts":dict(self.counts),"revision":self.revision}

    def restore(self, data):
        if not isinstance(data,dict) or data.get("version") != self.VERSION:
            return
        self.binding=data.get("binding") if isinstance(data.get("binding"),str) else None
        self.bins={};self.history.clear()
        bins=data.get("bins",{})
        for k,e in (list(bins.items())[-1600:] if isinstance(bins,dict) else []):
            if not isinstance(e,dict) or not isinstance(e.get("days"),dict):continue
            days={}
            for d,vals in list(e["days"].items())[-45:]:
                try:
                    day=datetime.fromisoformat(str(d)).date().isoformat()
                except (ValueError,TypeError):continue
                if isinstance(vals,list):
                    clean=[v for x in vals[-8:] if (v:=finite(x)) is not None and .15<=v<=1.6]
                    if clean:days[day]=clean
            self.bins[str(k)[:80]]={"days":days,"factor":max(.35,min(1.25,finite(e.get("factor")) or 1.)),"updated_day":str(e.get("updated_day",""))[:10]}
        history=data.get("history",[])
        for row in (history[-2880:] if isinstance(history,list) else []):
            if not isinstance(row,dict):continue
            try:
                dt=datetime.fromisoformat(str(row.get("time")))
                if dt.tzinfo is None:continue
            except (ValueError,TypeError):continue
            clean={k:finite(row.get(k)) for k in ("raw_w","corrected_w","actual_w","error_w","error_pct","factor")}
            clean.update(time=dt.isoformat(),accepted=row.get("accepted") is True,
                reason=str(row.get("reason",""))[:240],samples=max(0,min(20,int(finite(row.get("samples")) or 0))))
            self.history.append(clean)
        self.history=deque(sorted(self.history,key=lambda x:datetime.fromisoformat(x["time"]).timestamp()),maxlen=2880)
        counts=data.get("counts",{})
        self.counts=Counter({str(k)[:64]:max(0,min(10**12,int(v))) for k,x in (counts.items() if isinstance(counts,dict) else []) if (v:=finite(x)) is not None})
        self.revision=max(0,int(finite(data.get("revision")) or 0));self.started=None;self.window=None;self.samples=[]
        self.last_observation=None;self.last_meter_stamp=None

    def summary(self):
        days=set()
        for e in self.bins.values():days.update(e.get("days",{}))
        valid=[r for r in self.history
               if r.get("actual_w") is not None and r.get("corrected_w") is not None and (r.get("raw_w") or 0)>=400]
        errors=[abs(r["actual_w"]-r["corrected_w"]) for r in valid]
        biases=[r["actual_w"]-r["corrected_w"] for r in valid]
        periods={}
        for key,lo,hi in (("ochtend",0,11),("middag",11,15),("namiddag",15,24)):
            rows=[]
            for row in valid:
                try: hour=datetime.fromisoformat(row["time"]).hour
                except (ValueError,TypeError,KeyError): continue
                if lo<=hour<hi: rows.append(row)
            diffs=[x["actual_w"]-x["corrected_w"] for x in rows]
            periods[key]={
                "samples":len(rows),
                "mae_w":round(sum(abs(x) for x in diffs)/len(diffs),1) if diffs else None,
                "bias_w":round(sum(diffs)/len(diffs),1) if diffs else None,
                "accepted":sum(1 for x in rows if x.get("accepted") is True),
                "rejected":sum(1 for x in rows if x.get("accepted") is not True),
            }
        return {"days":len(days),"accepted":self.counts["accepted"],"rejected":self.counts["rejected"],
                "last_reason":self.last_reason,"revision":self.revision,
                "mae_w":round(sum(errors)/len(errors),1) if errors else None,
                "bias_w":round(sum(biases)/len(biases),1) if biases else None,
                "error_samples":len(errors),"periods":periods,
                "minimum_days_required":max(int(self.settings.get("minimum_days",5)),PRESETS.get(self.settings.get("learning_preset"),PRESETS["normal"])[1])}
