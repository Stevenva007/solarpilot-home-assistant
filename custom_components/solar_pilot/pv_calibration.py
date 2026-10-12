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
EDGE_MAX_BINS = 1600
EDGE_MAX_DAYS = 45
EDGE_MAX_AGE_DAYS = 120


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
        self.settings=settings; self.bins={}; self.edge_evidence={}; self.history=deque(maxlen=2880)
        self.counts=Counter(); self.window=None; self.samples=[]; self.started=None
        self.last_observation=None; self.last_meter_stamp=None; self.binding=None
        self.last_reason="Wachten op meetgegevens"; self.revision=0
        self._unsupported_snapshot=None

    def _keys(self, dt, az, el):
        # Two-month season bands + sun position. Clock bins are fallback, not a
        # permanent 16:00 correction. Separate seasonal bins avoid mixing winter.
        season=(dt.month-1)//2
        clock=f"{season}:clock:{dt.hour*4+dt.minute//15}"
        az,el=finite(az),finite(el)
        return ([f"{season}:sun:{int(az//10)}:{int(el//5)}", clock]
                if az is not None and el is not None and 0<=az<360 and -90<=el<=90 else [clock])

    def _minimum_days(self):
        return max(int(self.settings.get("minimum_days",5)),PRESETS.get(self.settings.get("learning_preset"),PRESETS["normal"])[1])

    @staticmethod
    def _valid_edge_key(key):
        if not isinstance(key,str) or len(key)>80:
            return False
        parts=key.split(":")
        try:
            if int(parts[0]) not in range(6):return False
            if len(parts)==3 and parts[1]=="clock":
                return int(parts[2]) in range(96)
            if len(parts)==4 and parts[1]=="sun":
                return int(parts[2]) in range(36) and -18<=int(parts[3])<=18
        except (ValueError,TypeError,IndexError):
            return False
        return False

    @staticmethod
    def _clean_edge_record(record):
        if not isinstance(record,dict) or record.get("direction") not in ("drop","recovery"):
            return None
        result={key:finite(record.get(key)) for key in ("offset_s","before","after","value","samples","span_s","max_gap_s")}
        if any(value is None for value in result.values()):return None
        if not 0<result["offset_s"]<900 or any(not .15<=result[key]<=1.6 for key in ("before","after","value")):
            return None
        before,after=result["before"],result["after"]
        if abs(after-before)/max(before,after)<.2:return None
        if not min(before,after)-.03*max(before,after)<=result["value"]<=max(before,after)*1.03:return None
        if not (12<=result["samples"]<=20 and result["samples"].is_integer()
                and 660<=result["span_s"]<900 and 0<result["max_gap_s"]<=120):return None
        result["samples"]=int(result["samples"])
        direction="drop" if after<before else "recovery"
        if direction!=record["direction"]:return None
        return {**result,"direction":direction}

    def _edge_details(self, key, dt):
        records=[]
        for day,record in self.edge_evidence.get(key,{}).get("days",{}).items():
            try:age=(dt.date()-datetime.fromisoformat(day).date()).days
            except (ValueError,TypeError):continue
            cleaned=self._clean_edge_record(record)
            if cleaned is not None and 0<=age<=EDGE_MAX_AGE_DAYS:records.append(cleaned)
        minimum=self._minimum_days();count=len(records)
        result={"state":"none" if not count else "pending","days":count,
                "minimum_days_required":minimum,"trusted":False,"confidence":0.,
                "direction":None,"edge_offset_s":None,
                "reason":"Nog geen terugkerende overgang gemeten" if not count else "Nog onvoldoende verschillende vergelijkbare dagen"}
        if not records:return result
        directions={record["direction"] for record in records}
        phases=[record["offset_s"] for record in records]
        before=[record["before"] for record in records];after=[record["after"] for record in records]
        b,a=median(before),median(after)
        result.update(direction=next(iter(directions)) if len(directions)==1 else None,edge_offset_s=round(median(phases),1))
        # Do not cherry-pick a convenient subset of cloudy/random edges. Every
        # retained comparable day must agree on direction, phase and magnitude.
        consistent=(len(directions)==1 and max(phases)-min(phases)<=120
                    and all(abs(value-b)<=.15*b for value in before)
                    and all(abs(value-a)<=.15*a for value in after))
        if not consistent:
            result.update(state="inconsistent",reason="Overgangen verschillen in richting, tijdstip of verhouding; geen correctie geleerd")
            return result
        scatter=max(median([abs(value-b) for value in before])/b,
                    median([abs(value-a) for value in after])/a)
        confidence=min(.95,count/12)*max(0.,1-3*scatter)
        result["confidence"]=round(confidence,3)
        if count>=minimum and confidence>=.4:
            result.update(state="trusted",trusted=True,reason="Terugkerende stabiele overgang bevestigd in vergelijkbare seizoensvakken; oorzaak onbekend")
        return result

    @staticmethod
    def _factor_output(details):
        edge=details["edge_evidence"]
        key=details.get("key") or ""
        details.update(applied=abs(details["factor"]-1.)>1e-9,
                       profile_kind="global" if key=="global" else "sun" if ":sun:" in key else "clock" if ":clock:" in key else "none",
                       edge={"status":edge.get("state","none"),"candidate_days":edge.get("days",0),
                             "required_days":edge.get("minimum_days_required",details["minimum_days_required"]),
                             "direction":edge.get("direction"),"reason":edge.get("reason",details["reason"])})
        return details

    def factor_details(self, dt, az=None, el=None):
        minimum=self._minimum_days()
        details={"factor":1.,"confidence":0.,"days":0,"minimum_days_required":minimum,
                 "eligible":False,"validated_days":0,
                 "source":"Lokale kalibratie uit","reason":"Lokale kalibratie uit",
                 "key":None,"edge_candidate_days":0,"edge_candidate_state":"none",
                 "edge_evidence":{"state":"none","days":0,"trusted":False},
                 "fallback_used":False}
        if not self.settings.get("calibration_enabled"):
            return self._factor_output(details)
        keys=self._keys(dt,az,el) if self.settings.get("shadow_enabled",True) else ["global"]
        edge_states={key:self._edge_details(key,dt) for key in keys if key!="global"}
        strongest=max(edge_states.values(),key=lambda state:(state["trusted"],state["days"]),default=details["edge_evidence"])
        details.update(edge_evidence=strongest,edge_candidate_days=strongest["days"],edge_candidate_state=strongest["state"])
        noisy_geometry=None;pending_profile=None
        for key in keys:
            entry=self.bins.get(key,{})
            days=entry.get("days",{})
            vals=[median(v) for d,v in days.items() if v and 0 <= (dt.date()-datetime.fromisoformat(d).date()).days <= 120]
            m=median(vals) if vals else 0.;mad=median([abs(x-m) for x in vals]) if vals else 0.
            confidence=min(.95,len(vals)/12)*max(0.,1-3*mad/max(m,.1))
            if len(vals)<minimum:
                if vals and (pending_profile is None or len(vals)>pending_profile[1]):
                    pending_profile=(key,len(vals),confidence)
                continue
            if confidence<.4:
                # A noisy geometry bin only yields to clock fallback when the
                # *same seasonal quarter* has independently recurring stable
                # edge evidence, with more days and stronger confidence. Ordinary
                # clock samples never bypass the old geometry confidence guard.
                if ":sun:" in key and len(keys)>1:
                    clock_edge=edge_states.get(keys[-1],{})
                    if (clock_edge.get("trusted") and clock_edge.get("days",0)>len(vals)
                            and clock_edge.get("confidence",0)>confidence):
                        noisy_geometry=(confidence,len(vals));continue
                details.update(confidence=confidence,days=len(vals),key=key,
                               source="Vergelijkbare dagen te wisselend; ruwe forecast behouden",
                               reason="Vergelijkbare dagen te wisselend; ruwe forecast behouden")
                return self._factor_output(details)
            source="Zonnestand + seizoen" if ":sun:" in key else "Tijdvak + seizoen" if ":clock:" in key else "Globale kalibratie"
            if noisy_geometry is not None:
                source="Tijdvak + seizoen; sterker bewijs van terugkerende overgang"
            chosen_edge=edge_states.get(key,details["edge_evidence"])
            details.update(factor=entry.get("factor",1.),confidence=confidence,days=len(vals),key=key,
                           eligible=True,validated_days=len(vals),
                           source=source,reason=source,fallback_used=key!=keys[0],
                           edge_evidence=chosen_edge,edge_candidate_days=chosen_edge.get("days",0),
                           edge_candidate_state=chosen_edge.get("state","none"))
            return self._factor_output(details)
        reason="Nog onvoldoende vergelijkbare dagen; ruwe forecast behouden"
        if noisy_geometry is not None:
            reason="Sterker overgangsbewijs, maar nog geen voldoende betrouwbaar tijdvakmodel; ruwe forecast behouden"
        if pending_profile is not None:
            details.update(key=pending_profile[0],days=pending_profile[1],confidence=pending_profile[2],
                           fallback_used=pending_profile[0]!=keys[0])
        details.update(source=reason,reason=reason)
        return self._factor_output(details)

    def factor(self, dt, az=None, el=None):
        details=self.factor_details(dt,az,el)
        # Keep the legacy validated tuple contract. New diagnostics expose the
        # real 3/5 evidence count even though the old factor API withheld it
        # until the configured minimum was reached.
        if details["days"]<details["minimum_days_required"]:
            return details["factor"],0.,0,details["source"]
        return details["factor"],details["confidence"],details["days"],details["source"]

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
            self.bins={}; self.edge_evidence={}; self.binding=binding; self.samples=[]; self.window=None
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
        edge=None;edge_states={};edge_keys=[]
        if not reason:
            ratios=[r["actual"]/r["raw"] for r in good]
            m=median(ratios)
            jumps=[abs(b["actual"]-a["actual"])/max(a["actual"],b["actual"],400) for a,b in zip(good,good[1:])]
            if max(jumps,default=0)>.3 or (max(ratios)-min(ratios))/max(m,.1)>.3:
                reason="Snel wisselende bewolking; geen structurele correctie leren"
                if self.settings.get("calibration_enabled") and self.settings.get("shadow_enabled",True):
                    edge=self._stable_edge(good,ratios)
        finite_rows=[r for r in rows if r["actual"] is not None and r["raw"] is not None]
        mid=rows[len(rows)//2];dt=datetime.fromtimestamp(mid["ts"],tz)
        actual=median([r["actual"] for r in finite_rows]) if finite_rows else None
        raw=median([r["raw"] for r in finite_rows]) if finite_rows else None
        applied=median([r["factor"] for r in rows]); corrected=min(self.settings["inverter_limit_w"],raw*applied) if raw is not None else None
        if edge is not None:
            day=dt.date().isoformat();edge_keys=self._keys(dt,mid["az"],mid["el"])
            for key in edge_keys:
                entry=self.edge_evidence.setdefault(key,{"days":{}})
                # One piece of evidence per day/bin. A rerun cannot give the
                # current day extra votes or revise an earlier candidate.
                entry["days"].setdefault(day,edge)
                keep={old:record for old,record in entry["days"].items()
                      if 0<=(dt.date()-datetime.fromisoformat(old).date()).days<=EDGE_MAX_AGE_DAYS}
                entry["days"]={old:keep[old] for old in sorted(keep)[-EDGE_MAX_DAYS:]}
                edge_states[key]=self._edge_details(key,dt)
            if len(self.edge_evidence)>EDGE_MAX_BINS:
                for key in list(self.edge_evidence)[:len(self.edge_evidence)-EDGE_MAX_BINS]:del self.edge_evidence[key]
            proof_days=max((state["days"] for state in edge_states.values()),default=0)
            minimum=self._minimum_days()
            if any(state["trusted"] for state in edge_states.values()):
                reason=""
            else:
                consistent=all(state["state"]!="inconsistent" for state in edge_states.values())
                reason=(f"Stabiele overgang kandidaat: {proof_days}/{minimum} vergelijkbare dagen; nog niet toegepast"
                        if consistent else "Stabiele overgangen onvoldoende consistent; geen correctie geleerd")
        accepted=not reason
        if accepted:
            value=edge["value"] if edge is not None else median([r["actual"]/r["raw"] for r in good]);day=dt.date().isoformat()
            learning_keys=([key for key,state in edge_states.items() if state["trusted"]]
                           if edge is not None else [*self._keys(dt,mid["az"],mid["el"]),"global"])
            for key in learning_keys:
                entry=self.bins.setdefault(key,{"days":{},"factor":1.,"updated_day":None})
                if edge is not None:
                    # Pending real quarters become model evidence only once the
                    # repeated pattern is supported. Old history rows remain
                    # rejected, with their original factors and timestamps.
                    for old,record in self.edge_evidence[key]["days"].items():
                        entry["days"].setdefault(old,[record["value"]])
                vals=entry["days"].setdefault(day,[]);vals.append(value);del vals[:-8]
                for old in [d for d in sorted(entry["days"]) if (dt.date()-datetime.fromisoformat(d).date()).days>120] + sorted(entry["days"])[:-45]:
                    entry["days"].pop(old,None)
                rate,min_days=PRESETS.get(self.settings.get("learning_preset"),PRESETS["normal"])
                try:previous_day=datetime.fromisoformat(entry.get("updated_day")).date()
                except (ValueError,TypeError):previous_day=None
                if len(entry["days"])>=max(min_days,self.settings.get("minimum_days",5)) and (previous_day is None or dt.date()>previous_day):
                    target=max(.35,min(1.25,median([median(v) for v in entry["days"].values()])))
                    old=entry["factor"];entry["factor"]=max(old-rate,min(old+rate,target));entry["updated_day"]=day
            reason=("Gebruikt: herhaalde stabiele overgang met vergelijkbaar seizoenbewijs; oorzaak onbekend"
                    if edge is not None else "Gebruikt: rustig, volledig kwartier zonder clipping")
        self.counts["accepted" if accepted else "rejected"]+=1
        self.history.append({"time":dt.isoformat(),"raw_w":raw,"corrected_w":corrected,"actual_w":actual,
            "error_w":round(actual-raw,1) if actual is not None and raw is not None else None,
            "error_pct":round((actual-raw)/raw*100,1) if actual is not None and raw is not None and raw>=400 else None,
            "factor":round(applied,3),"accepted":accepted,"reason":reason,"samples":len(rows),
            **({"edge_candidate":True,"edge_candidate_days":max(state["days"] for state in edge_states.values()),
                 "edge_candidate_state":"trusted" if accepted else "pending" if all(state["state"]!="inconsistent" for state in edge_states.values()) else "inconsistent",
                 "edge_direction":edge["direction"],"edge_offset_s":round(edge["offset_s"],1)} if edge is not None else {})})
        cutoff=dt.timestamp()-min(30,max(1,int(self.settings.get("history_days",30))))*86400
        while self.history and datetime.fromisoformat(self.history[0]["time"]).timestamp()<cutoff:
            self.history.popleft()
        # Bound across seasonal bins; each bin retains at most 45 distinct days.
        if len(self.bins)>1600:
            for k in list(self.bins)[:len(self.bins)-1600]:del self.bins[k]
        self.last_reason=reason;self.revision+=1

    @staticmethod
    def _stable_edge(rows,ratios):
        """One sharp step between two calm plateaus; never alternating clouds."""
        if len(rows)<12:return None
        differences=[abs(b-a) for a,b in zip(ratios,ratios[1:])]
        split=1+max(range(len(differences)),key=lambda index:differences[index])
        if split<4 or len(rows)-split<4:return None
        left,right=ratios[:split],ratios[split:];before,after=median(left),median(right)
        if abs(after-before)/max(before,after)<.25:return None
        for plateau,center in ((left,before),(right,after)):
            if (max(plateau)-min(plateau))/center>.12:return None
            if median([abs(value-center) for value in plateau])/center>.04:return None
        for index,jump in enumerate(differences):
            if index!=split-1 and jump/max(ratios[index],ratios[index+1])>.08:return None
        quarter=math.floor(rows[0]["ts"]/900)*900
        offset=(rows[split-1]["ts"]+rows[split]["ts"])/2-quarter
        # A step's median can describe its lower plateau rather than the energy
        # of the whole quarter. Integrate measured and raw power over time. Only
        # short (<=2 min) uncovered endpoints may retain the nearest plateau;
        # the otherwise unchanged full-coverage checks bound the interior gaps.
        if rows[0]["ts"]-quarter>120 or quarter+900-rows[-1]["ts"]>120:return None
        points=[(quarter,rows[0]["actual"],rows[0]["raw"]),
                *[(row["ts"],row["actual"],row["raw"]) for row in rows],
                (quarter+900,rows[-1]["actual"],rows[-1]["raw"])]
        actual_energy=raw_energy=0.
        for left_point,right_point in zip(points,points[1:]):
            delta=right_point[0]-left_point[0]
            actual_energy+=delta*(left_point[1]+right_point[1])/2
            raw_energy+=delta*(left_point[2]+right_point[2])/2
        if raw_energy<=0:return None
        return PVCalibration._clean_edge_record({"direction":"drop" if after<before else "recovery",
            "offset_s":offset,"before":before,"after":after,"value":actual_energy/raw_energy,
            "samples":len(rows),"span_s":rows[-1]["ts"]-rows[0]["ts"],
            "max_gap_s":max(right_row["ts"]-left_row["ts"] for left_row,right_row in zip(rows,rows[1:]))})

    def snapshot(self):
        if self._unsupported_snapshot is not None:
            return deepcopy(self._unsupported_snapshot)
        return {"version":self.VERSION,"binding":self.binding,"bins":deepcopy(self.bins),"edge_evidence":deepcopy(self.edge_evidence),
                "history":deepcopy(list(self.history)),"counts":dict(self.counts),"revision":self.revision}

    def restore(self, data):
        if not isinstance(data,dict) or not data:
            return
        if isinstance(data.get("version"),bool) or data.get("version") != self.VERSION:
            # Preserve an unrecognised schema byte-for-value in private
            # snapshots rather than replacing it with empty current-version bins.
            self._unsupported_snapshot=deepcopy(data)
            self.bins={};self.edge_evidence={};self.history.clear();self.counts=Counter()
            self.binding=None;self.started=None;self.window=None;self.samples=[]
            self.last_observation=None;self.last_meter_stamp=None
            self.last_reason="Opgeslagen PV-modelversie niet ondersteund; oorspronkelijke opslag behouden"
            return
        self._unsupported_snapshot=None
        self.binding=data.get("binding") if isinstance(data.get("binding"),str) and len(data["binding"])<=256 else None
        self.bins={};self.edge_evidence={};self.history.clear()
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
        edges=data.get("edge_evidence",{})
        for key,entry in (list(edges.items())[-EDGE_MAX_BINS:] if isinstance(edges,dict) and self.binding else []):
            if not self._valid_edge_key(key) or not isinstance(entry,dict) or not isinstance(entry.get("days"),dict):continue
            days={}
            for day,record in list(entry["days"].items())[-EDGE_MAX_DAYS:]:
                if not isinstance(day,str):continue
                try:parsed=datetime.fromisoformat(day).date().isoformat()
                except (ValueError,TypeError):continue
                if day!=parsed or (datetime.fromisoformat(day).month-1)//2!=int(key.split(":")[0]):continue
                clean=self._clean_edge_record(record)
                if clean is not None:days[day]=clean
            if days:self.edge_evidence[key]={"days":days}
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
            if row.get("edge_candidate") is True:
                state=row.get("edge_candidate_state")
                direction=row.get("edge_direction")
                offset=finite(row.get("edge_offset_s"))
                if state in ("pending","inconsistent","trusted") and direction in ("drop","recovery") and offset is not None and 0<offset<900:
                    clean.update(edge_candidate=True,edge_candidate_state=state,edge_direction=direction,
                                 edge_candidate_days=max(0,min(EDGE_MAX_DAYS,int(finite(row.get("edge_candidate_days")) or 0))),
                                 edge_offset_s=offset)
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
                "storage_warning":"Opgeslagen PV-modelversie niet ondersteund; oorspronkelijke opslag blijft ongewijzigd bewaard" if self._unsupported_snapshot is not None else "",
                "last_reason":self.last_reason,"revision":self.revision,
                "mae_w":round(sum(errors)/len(errors),1) if errors else None,
                "bias_w":round(sum(biases)/len(biases),1) if biases else None,
                "error_samples":len(errors),"periods":periods,
                "minimum_days_required":self._minimum_days(),
                "recurring_edge_bins":len(self.edge_evidence),
                "recurring_edge_candidate_days":len({day for entry in self.edge_evidence.values() for day in entry.get("days",{})}),
                "recurring_edge_note":"Terugkerende overgangen vragen eigen bewijs per zonnestand/tijdvak en seizoen; geen vast 16:00-schema of bewezen boomoorzaak"}
