"""Local per-device phase fingerprint learning.

The learner observes changes, not absolute phase load. It can identify which
phase a measured appliance most likely occupies without assuming that the rest
of the house is static. Only clean, isolated events are accepted; uncertain
events remain advisory and never create an electrical protection guarantee.
"""
from __future__ import annotations
import math
import statistics


def _finite(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _median(values):
    vals = [float(v) for v in values if _finite(v) is not None]
    return statistics.median(vals) if vals else None


class PhaseLearning:
    def __init__(self, settings=None):
        self.settings = settings or {}
        self.profiles = {}
        self.last_phase = None
        self.last_device_w = {}
        self.last_stamp = None
        self.pending = {}
        self.accepted = 0
        self.rejected = 0

    def reset(self):
        self.__init__(self.settings)

    def snapshot(self):
        return {"profiles": self.profiles, "accepted": self.accepted, "rejected": self.rejected}

    def restore(self, data, valid_ids=None):
        if not isinstance(data, dict): return
        valid_ids = set(valid_ids or [])
        profiles = data.get("profiles", {})
        if not isinstance(profiles, dict): profiles = {}
        for device_id, profile in list(profiles.items())[:100]:
            if (valid_ids and device_id not in valid_ids) or not isinstance(profile, dict): continue
            obs = []
            observations = profile.get("observations", [])
            if not isinstance(observations, list): continue
            for item in observations[-40:]:
                if not isinstance(item, dict): continue
                # Earlier controlled records did not check other appliance
                # meters. Their apparently strong phase attribution cannot be
                # repaired afterwards; keep independent passive evidence and
                # relearn only that unverified controlled contribution.
                if item.get("source") == "controlled" and item.get("isolated_meters") is not True:
                    continue
                shares = item.get("shares")
                if not isinstance(shares, list) or len(shares) != 3: continue
                delta = _finite(item.get("device_delta_w",0))
                weight = _finite(item.get("weight",1))
                if (delta is not None and weight is not None and weight > 0
                        and all(_finite(v) is not None and 0 <= float(v) <= 1 for v in shares)
                        and abs(sum(float(v) for v in shares)-1) <= .005):
                    obs.append({"shares":[round(float(v),4) for v in shares],
                                "device_delta_w":round(abs(delta),1),
                                "day":str(item.get("day","")), "source":str(item.get("source","passive")),
                                "weight":max(.5,min(3.0,weight)),
                                **({"isolated_meters": True} if item.get("source") == "controlled" else {})})
            if obs: self.profiles[device_id] = {"observations": obs}
        self.accepted = max(0, int(_finite(data.get("accepted",0)) or 0))
        self.rejected = max(0, int(_finite(data.get("rejected",0)) or 0))

    def begin_controlled(self, device_id, now, phase_values, device_w):
        if not self.settings.get("learning_enabled", True): return
        vals = tuple(_finite(v) for v in phase_values or ()); watts = _finite(device_w)
        if len(vals) != 3 or any(v is None for v in vals) or watts is None: return
        self.pending[device_id] = {"started":float(now), "phase":vals, "device_w":watts,
                                   "other_powers": {i: w for i, w in self.last_device_w.items()
                                                    if i != device_id}}

    def _record(self, device_id, device_delta, phase_delta, day, source="passive", weight=1.0):
        magnitude = abs(device_delta); min_delta = max(50.0,float(self.settings.get("learning_min_delta_w",250)))
        if magnitude < min_delta: self.rejected += 1; return False
        sign = 1.0 if device_delta > 0 else -1.0
        effects = [max(0.0, sign * float(v)) for v in phase_delta]; total = sum(effects)
        ratio = total / max(1.0,magnitude)
        if total < min_delta * .4 or not .35 <= ratio <= 1.75: self.rejected += 1; return False
        shares = [v/total for v in effects]
        profile = self.profiles.setdefault(device_id,{"observations":[]})
        profile["observations"].append({"shares":[round(v,4) for v in shares], "device_delta_w":round(magnitude,1),
                                         "day":str(day), "source":source, "weight":round(float(weight),2),
                                         **({"isolated_meters": True} if source == "controlled" else {})})
        del profile["observations"][:-40]; self.accepted += 1; return True

    def observe(self, *, now, day, phase_values, device_powers):
        if not self.settings.get("learning_enabled", True): return
        vals = tuple(_finite(v) for v in phase_values or ())
        if len(vals)!=3 or any(v is None for v in vals): return
        cleaned = {i:_finite(w) for i,w in (device_powers or {}).items()}; cleaned={i:w for i,w in cleaned.items() if w is not None and w>=-1}
        settle=max(2.0,float(self.settings.get("learning_settle_s",15))); max_window=max(settle+5,float(self.settings.get("learning_max_window_s",60)))
        finalized=set()
        for device_id,event in list(self.pending.items()):
            age=now-event["started"]
            if age>max_window: self.pending.pop(device_id,None); self.rejected+=1; continue
            # A command does not prove an isolated electrical transition. Other
            # measured appliances can change while this command settles, even
            # before its own consumption rises. Reject that entire observation
            # rather than learning their phase load as part of this appliance.
            baseline = event.get("other_powers", {})
            other_ids = (set(baseline) | set(cleaned)) - {device_id}
            missing = any(i not in baseline or i not in cleaned for i in other_ids)
            other_delta = sum(abs(cleaned[i] - baseline[i]) for i in other_ids
                              if i in baseline and i in cleaned)
            if missing or other_delta >= float(self.settings.get("learning_min_delta_w",250)):
                self.pending.pop(device_id,None); self.rejected+=1; finalized.add(device_id); continue
            if age<settle or device_id not in cleaned: continue
            device_delta=cleaned[device_id]-event["device_w"]; phase_delta=tuple(vals[n]-event["phase"][n] for n in range(3))
            if abs(device_delta)>=float(self.settings.get("learning_min_delta_w",250)):
                self._record(device_id,device_delta,phase_delta,day,"controlled",2.0); finalized.add(device_id); self.pending.pop(device_id,None)
        if self.last_phase is not None and self.last_stamp is not None:
            dt=now-self.last_stamp
            if 1<=dt<=max_window:
                changes=[]
                for device_id,value in cleaned.items():
                    if device_id in self.last_device_w:
                        delta=value-self.last_device_w[device_id]
                        if abs(delta)>=float(self.settings.get("learning_min_delta_w",250)): changes.append((device_id,delta))
                if len(changes)==1:
                    device_id,device_delta=changes[0]
                    if device_id not in finalized:
                        phase_delta=tuple(vals[n]-self.last_phase[n] for n in range(3)); self._record(device_id,device_delta,phase_delta,day,"passive",1.0)
        self.last_phase=vals; self.last_stamp=float(now); self.last_device_w=cleaned

    @staticmethod
    def _classify(shares):
        if not shares or len(shares)!=3: return "unknown"
        order=sorted(range(3),key=lambda i: shares[i],reverse=True); biggest,second,third=(shares[order[0]],shares[order[1]],shares[order[2]])
        if biggest>=.72: return f"L{order[0]+1}"
        if min(shares)>=.18 and max(shares)-min(shares)<=.28: return "3-fase"
        if biggest+second>=.84 and second>=.28:
            pair=sorted([order[0]+1,order[1]+1]); return f"L{pair[0]}+L{pair[1]}"
        return "unknown"

    def profile(self, device_id):
        obs=self.profiles.get(device_id,{}).get("observations",[])
        if not obs:
            return {"classification":"unknown","confidence":0.0,"samples":0,"distinct_days":0,"phase_shares":[0,0,0],"typical_delta_w":None,"status":"Nog geen bruikbare fasegebeurtenissen"}
        expanded=[]
        for item in obs:
            repeats=max(1,int(round(float(item.get("weight",1))))); expanded.extend([item]*repeats)
        shares=[_median([item["shares"][i] for item in expanded]) or 0.0 for i in range(3)]; total=sum(shares)
        if total>0: shares=[v/total for v in shares]
        classification=self._classify(shares); labels=[self._classify(item["shares"]) for item in obs]
        consistent=(sum(1 for label in labels if label==classification)/len(labels) if classification!="unknown" else 0.0)
        effective=sum(float(item.get("weight",1)) for item in obs); min_samples=max(1,int(self.settings.get("learning_min_samples",5)))
        evidence=min(1.0,effective/(min_samples*1.5)); confidence=min(.98,evidence*(.45+.55*consistent)) if classification!="unknown" else 0.0
        days=len({item.get("day") for item in obs if item.get("day")}); typical=_median([item.get("device_delta_w") for item in obs])
        return {"classification":classification,"confidence":round(confidence,3),"samples":len(obs),"effective_samples":round(effective,1),"distinct_days":days,
                "phase_shares":[round(v,3) for v in shares],"typical_delta_w":None if typical is None else round(typical,1),
                "status":(f"{classification} waarschijnlijk · vertrouwen {confidence:.0%}" if classification!="unknown" else "Fasepatroon nog niet eenduidig")}

    def overview(self, configs=None, extra_configs=None):
        configs={**(configs or {}), **(extra_configs or {})}; devices={}
        use_control = bool(self.settings.get("use_learned_device_map",False))
        threshold = float(self.settings.get("learning_min_confidence",.75))
        for device_id,cfg in configs.items():
            if cfg.get("power_entity"):
                profile = self.profile(device_id)
                reliable = profile.get("classification") != "unknown" and float(profile.get("confidence",0) or 0) >= threshold
                hint = cfg.get("phase_hint","auto")
                devices[device_id]={
                    "name":cfg.get("name",device_id), **profile, "hint":hint,
                    "learned": profile.get("classification") != "unknown",
                    "reliable": reliable,
                    "used_for_advice": reliable and str(hint).lower() == "auto",
                    "control_allowed": reliable and use_control and str(hint).lower() == "auto",
                }
        return {"enabled":bool(self.settings.get("learning_enabled",True)),"accepted_events":self.accepted,"rejected_events":self.rejected,
                "use_for_control":use_control,"minimum_confidence_for_control":threshold,
                "devices":devices,
                "note":"Geleerd en betrouwbaar zijn niet hetzelfde als regeltoestemming. Alleen expliciete fasevrijgave kan een betrouwbare geleerde fase voor regeling gebruiken; zekeringen en echte fasemetingen blijven leidend."}


def phase_allocation_from_hint(hint, learned_profile=None, minimum_confidence=.75):
    explicit={"l1":(1,0,0),"l2":(0,1,0),"l3":(0,0,1),"three_phase":(1/3,1/3,1/3),"l1_l2":(.5,.5,0),"l1_l3":(.5,0,.5),"l2_l3":(0,.5,.5)}
    hint=str(hint or "auto").lower()
    if hint in explicit: return explicit[hint],"handmatig"
    if hint=="unknown": return None,"onbekend"
    p=learned_profile or {}
    if float(p.get("confidence",0) or 0)<float(minimum_confidence): return None,"leren"
    classification=p.get("classification"); map_class={"L1":explicit["l1"],"L2":explicit["l2"],"L3":explicit["l3"],"3-fase":explicit["three_phase"],"L1+L2":explicit["l1_l2"],"L1+L3":explicit["l1_l3"],"L2+L3":explicit["l2_l3"]}
    return (map_class.get(classification),"geleerd") if classification in map_class else (None,"leren")


def phase_total_headroom_w(phase_values, guarded_limit_w, shares):
    if shares is None: return None
    vals=tuple(_finite(v) for v in phase_values or ())
    if len(vals)!=3 or any(v is None for v in vals): return None
    headrooms=[max(0.0,guarded_limit_w-max(0.0,v)) for v in vals]; allowed=[]
    for headroom,share in zip(headrooms,shares):
        if share>0: allowed.append(headroom/share)
    return min(allowed) if allowed else None
