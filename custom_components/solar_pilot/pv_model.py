"""Bounded local photovoltaic correction and shade/recovery model.

The model learns correction factors versus an external solar forecast. It is
not a weather model and it never replaces the real PV or grid meters used for
control. Samples are grouped by solar position and by distinct day so a cloudy
minute cannot outweigh a recurring site-specific shadow pattern.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
import statistics

LOCAL_PV_DEFAULTS = {
    "enabled": True, "forecast_power_entity": "sensor.power_production_now", "sun_entity": "sun.sun",
    "seed_enabled": True, "sample_interval_s": 300, "min_forecast_w": 400.0, "min_elevation_deg": 3.0,
    "azimuth_bin_deg": 5.0, "elevation_bin_deg": 4.0, "min_days": 5, "min_confidence": 0.55,
    "factor_min": 0.20, "factor_max": 1.80, "shadow_factor": 0.72, "shadow_drop": 0.20,
    "recovery_delta": 0.18, "horizon_min": 120, "projection_step_min": 15, "max_days_per_bin": 45,
}


def _finite(value):
    try:
        value=float(value); return value if math.isfinite(value) else None
    except (TypeError,ValueError): return None

def _median(values):
    vals=[float(v) for v in values if _finite(v) is not None]; return statistics.median(vals) if vals else None

def _percentile(values,q):
    vals=sorted(float(v) for v in values if _finite(v) is not None)
    if not vals: return None
    idx=max(0,min(len(vals)-1,math.ceil(len(vals)*q)-1)); return vals[idx]

def _hour_float(dt): return dt.hour+dt.minute/60+dt.second/3600

def _interpolate_hourly(profile,hour):
    pairs=sorted((float(k),float(v)) for k,v in profile.items() if _finite(k) is not None and _finite(v) is not None)
    if not pairs: return None
    if hour<=pairs[0][0]: return pairs[0][1]
    if hour>=pairs[-1][0]: return pairs[-1][1]
    for (h0,v0),(h1,v1) in zip(pairs,pairs[1:]):
        if h0<=hour<=h1:
            if h1==h0:return v0
            f=(hour-h0)/(h1-h0); return v0+(v1-v0)*f
    return None

@dataclass(frozen=True)
class PVPrediction:
    factor: float=1.0; confidence: float=0.0; source: str="geen lokaal profiel"
    corrected_power_w: float|None=None; corrected_current_hour_kwh: float|None=None; corrected_next_hour_kwh: float|None=None
    next_factor: float=1.0; next_confidence: float=0.0; state: str="unknown"; event_eta_min: int|None=None
    reason: str="Nog onvoldoende lokale leerdata"

class LocalPVModel:
    def __init__(self, settings=None, seed=None):
        self.settings={**LOCAL_PV_DEFAULTS,**(settings or {})}; self.enabled=bool(self.settings["enabled"]); self.seed=seed or {}
        self.bins={}; self.az_bins={}; self.clock_bins={}; self.last_sample_wall=0.0; self.sun_history=deque(maxlen=24)
        self.samples=0; self.accepted_days=set(); self.last_prediction=PVPrediction()
    def reset_live(self):
        self.bins={}; self.az_bins={}; self.clock_bins={}; self.last_sample_wall=0.0; self.sun_history.clear(); self.samples=0; self.accepted_days=set(); self.last_prediction=PVPrediction()
    def snapshot(self):
        def compact(src):
            out={}; max_days=int(self.settings["max_days_per_bin"])
            for key,value in src.items():
                kept=list(value.get("days",{}).items())[-max_days:]; out[key]={"days":{d:list(v)[-12:] for d,v in kept}}
            return out
        return {"bins":compact(self.bins),"az_bins":compact(self.az_bins),"clock_bins":compact(self.clock_bins),"samples":self.samples}
    def restore(self,data):
        if not isinstance(data,dict):return
        for attr in ("bins","az_bins","clock_bins"):
            raw=data.get(attr,{})
            if not isinstance(raw,dict):continue
            cleaned={}
            for key,entry in raw.items():
                if not isinstance(entry,dict):continue
                days={}
                for day,values in entry.get("days",{}).items():
                    vals=[round(float(v),4) for v in values[-12:] if _finite(v) is not None and .02<=float(v)<=4]
                    if vals:days[str(day)]=vals
                if days:cleaned[str(key)]={"days":days}
            setattr(self,attr,cleaned)
        self.samples=max(0,int(data.get("samples",0)))
    def _az_key(self,azimuth):
        step=max(1.0,float(self.settings["azimuth_bin_deg"])); return str(int(round(float(azimuth)/step)*step))
    def _el_key(self,elevation):
        step=max(1.0,float(self.settings["elevation_bin_deg"])); return str(int(round(float(elevation)/step)*step))
    def _clock_key(self,local_now):
        minutes=local_now.hour*60+local_now.minute; return str(int(round(minutes/15)*15))
    def note_sun(self,wall_stamp,azimuth,elevation):
        az,el=_finite(azimuth),_finite(elevation)
        if az is None or el is None or wall_stamp<=0:return
        if self.sun_history and wall_stamp<=self.sun_history[-1][0]:return
        self.sun_history.append((float(wall_stamp),az,el))
    def _record(self,target,key,day,ratio):
        entry=target.setdefault(str(key),{"days":{}}); days=entry.setdefault("days",{}); vals=days.setdefault(str(day),[])
        vals.append(round(ratio,4)); del vals[:-12]; max_days=int(self.settings["max_days_per_bin"])
        while len(days)>max_days:del days[next(iter(days))]
    def observe(self,*,wall_stamp,local_now,actual_w,forecast_w,azimuth,elevation):
        if not self.enabled:return False
        actual,forecast=_finite(actual_w),_finite(forecast_w); az,el=_finite(azimuth),_finite(elevation)
        if az is not None and el is not None:self.note_sun(wall_stamp,az,el)
        if actual is None or forecast is None or az is None or el is None or forecast<float(self.settings["min_forecast_w"]) or el<float(self.settings["min_elevation_deg"]):return False
        if wall_stamp-self.last_sample_wall<float(self.settings["sample_interval_s"]):return False
        self.last_sample_wall=wall_stamp; ratio=max(.05,min(3.0,actual/max(1.0,forecast))); day=local_now.date().isoformat()
        self._record(self.bins,f"{self._az_key(az)}:{self._el_key(el)}",day,ratio); self._record(self.az_bins,self._az_key(az),day,ratio); self._record(self.clock_bins,self._clock_key(local_now),day,ratio)
        self.samples+=1; self.accepted_days.add(day); return True
    def _factor_from_entry(self,entry,*,confidence_cap=.95):
        if not entry:return None
        day_values=[]
        for vals in entry.get("days",{}).values():
            med=_median(vals)
            if med is not None:day_values.append(med)
        if not day_values:return None
        med=_median(day_values); p20=_percentile(day_values,.2); p80=_percentile(day_values,.8); days=len(day_values); min_days=max(1,int(self.settings["min_days"]))
        sample_conf=min(1.0,days/max(1.0,min_days*1.5)); spread=0.0 if med in (None,0) or p20 is None or p80 is None else (p80-p20)/max(.1,med)
        consistency=max(.2,min(1.0,1.0-spread/1.5)); confidence=min(confidence_cap,sample_conf*consistency)
        factor=max(float(self.settings["factor_min"]),min(float(self.settings["factor_max"]),med)); return factor,confidence,days
    def _seed_factor(self,local_now):
        if not self.settings.get("seed_enabled",True):return None
        profile=self.seed.get("pv_profile",{}).get("median_actual_to_forecast_ratio_by_hour",{}); factor=_interpolate_hourly(profile,_hour_float(local_now))
        if factor is None:return None
        factor=max(float(self.settings["factor_min"]),min(float(self.settings["factor_max"]),factor)); sunny_days=int(self.seed.get("source",{}).get("sunny_days_used",0) or 0)
        confidence=min(.45,.18+sunny_days/500); return factor,confidence,sunny_days
    def factor_for(self,local_now,azimuth=None,elevation=None):
        az,el=_finite(azimuth),_finite(elevation)
        if az is not None and el is not None:
            exact=self._factor_from_entry(self.bins.get(f"{self._az_key(az)}:{self._el_key(el)}"))
            if exact and exact[2]>=int(self.settings["min_days"]):return exact[0],exact[1],"live zonnestand 2D",exact[2]
            azonly=self._factor_from_entry(self.az_bins.get(self._az_key(az)),confidence_cap=.82)
            if azonly and azonly[2]>=int(self.settings["min_days"]):return azonly[0],azonly[1],"live zonneazimut",azonly[2]
        clock=self._factor_from_entry(self.clock_bins.get(self._clock_key(local_now)),confidence_cap=.65)
        if clock and clock[2]>=int(self.settings["min_days"]):return clock[0],clock[1],"live tijdvakfallback",clock[2]
        seed=self._seed_factor(local_now)
        if seed:return seed[0],seed[1],"historische bootstrap",seed[2]
        return 1.0,0.0,"geen lokaal profiel",0
    def _sun_rates(self):
        if len(self.sun_history)<2:return None,None
        a,b=self.sun_history[0],self.sun_history[-1]; dt=b[0]-a[0]
        if dt<60:return None,None
        az_delta=b[1]-a[1]
        if az_delta<-180:az_delta+=360
        elif az_delta>180:az_delta-=360
        return max(-.02,min(.02,az_delta/dt)),max(-.01,min(.01,(b[2]-a[2])/dt))
    def _project_position(self,azimuth,elevation,minutes):
        az,el=_finite(azimuth),_finite(elevation)
        if az is None or el is None:return None,None
        az_rate,el_rate=self._sun_rates()
        if az_rate is None:az_rate=15/3600
        if el_rate is None:el_rate=0.0
        seconds=minutes*60; return (az+az_rate*seconds)%360,el+el_rate*seconds
    def prediction(self,*,local_now,forecast_power_w=None,current_hour_kwh=None,next_hour_kwh=None,azimuth=None,elevation=None):
        if not self.enabled:
            self.last_prediction=PVPrediction(reason="Lokaal PV-model uitgeschakeld"); return self.last_prediction
        factor,confidence,source,_=self.factor_for(local_now,azimuth,elevation); naz,nel=self._project_position(azimuth,elevation,60); next_dt=local_now+timedelta(hours=1)
        next_factor,next_conf,next_source,_=self.factor_for(next_dt,naz,nel); raw_power=_finite(forecast_power_w); cur_kwh=_finite(current_hour_kwh); nxt_kwh=_finite(next_hour_kwh)
        corrected_power=None if raw_power is None else raw_power*factor; corrected_cur=None if cur_kwh is None else cur_kwh*factor; corrected_next=None if nxt_kwh is None else nxt_kwh*next_factor
        state="normal"; eta=None; reason=f"Lokale factor {factor:.2f} ({source}, vertrouwen {confidence:.0%})"
        shadow_factor=float(self.settings["shadow_factor"]); drop=float(self.settings["shadow_drop"]); recovery=float(self.settings["recovery_delta"]); min_conf=float(self.settings["min_confidence"]); step=max(5,int(self.settings["projection_step_min"])); horizon=max(step,int(self.settings["horizon_min"]))
        if confidence>=min_conf:
            if factor<=shadow_factor:state="shadow"; reason=f"Lokaal schaduwprofiel actief; forecastcorrectie ×{factor:.2f}"
            for minutes in range(step,horizon+1,step):
                paz,pel=self._project_position(azimuth,elevation,minutes); pf,pc,_,_=self.factor_for(local_now+timedelta(minutes=minutes),paz,pel)
                if min(confidence,pc)<min_conf:continue
                if factor>shadow_factor and pf<=min(shadow_factor,factor-drop):state,eta="shadow_expected",minutes; reason=f"Lokale schaduwval verwacht over ongeveer {minutes} min (factor {factor:.2f}→{pf:.2f})"; break
                if factor<=shadow_factor and pf>=factor+recovery:state,eta="recovery_expected",minutes; reason=f"Herstel na lokale schaduw verwacht over ongeveer {minutes} min (factor {factor:.2f}→{pf:.2f})"; break
        elif source!="geen lokaal profiel":state="learning"; reason=f"Lokaal profiel beschikbaar maar vertrouwen nog laag ({confidence:.0%}); forecast niet hard corrigeren"
        self.last_prediction=PVPrediction(factor=factor,confidence=confidence,source=source,corrected_power_w=corrected_power,corrected_current_hour_kwh=corrected_cur,corrected_next_hour_kwh=corrected_next,next_factor=next_factor,next_confidence=next_conf,state=state,event_eta_min=eta,reason=reason); return self.last_prediction
    def overview(self):
        p=self.last_prediction; live_days=set()
        for source in (self.bins,self.az_bins,self.clock_bins):
            for entry in source.values():live_days.update(entry.get("days",{}).keys())
        return {"enabled":self.enabled,"samples":self.samples,"distinct_live_days":len(live_days),"factor":round(p.factor,3),"confidence":round(p.confidence,3),"source":p.source,
                "corrected_power_w":None if p.corrected_power_w is None else round(p.corrected_power_w,1),"corrected_current_hour_kwh":None if p.corrected_current_hour_kwh is None else round(p.corrected_current_hour_kwh,3),
                "corrected_next_hour_kwh":None if p.corrected_next_hour_kwh is None else round(p.corrected_next_hour_kwh,3),"next_factor":round(p.next_factor,3),"next_confidence":round(p.next_confidence,3),
                "state":p.state,"event_eta_min":p.event_eta_min,"reason":p.reason,"seed_days":int(self.seed.get("source",{}).get("sunny_days_used",0) or 0),"control_note":"Adviserend correctiemodel. Actuele P1/PV-metingen blijven altijd leidend."}
