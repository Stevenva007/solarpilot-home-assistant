"""Explainable rolling-horizon planner for SolarPilot.

The planner is deliberately advisory. It proposes *when* flexible loads are most
useful to run. The realtime engine remains the only place that may decide if a
physical command is allowed at that instant.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
import math
import statistics

from .planner_quality import PlanQualityTracker, ReplayBuffer

UNIFIED_PLANNER_DEFAULTS = {
    "enabled": True,
    "horizon_h": 36,
    "slot_min": 15,
    "replan_min": 15,
    "pv_reserve_w": 150.0,
    "base_load_learning": True,
    "base_load_min_days": 4,
    "price_optimisation": True,
    "capacity_penalty_enabled": True,
    "capacity_penalty_eur_kwh": 0.50,
    "battery_advisory": True,
    "max_timeline_slots": 48,
    "quality_tracking": True,
    "quality_retention_days": 45,
    "replay_enabled": True,
    "replay_retention_days": 14,
    # Compatibility with beta.6-12 keys. They remain accepted but are no longer
    # the primary planning algorithm.
    "forecast_deferral_enabled": True,
    "forecast_gain_kwh": 0.50,
    "forecast_sufficiency_factor": 1.25,
    "max_deferral_s": 3600,
    "deadline_guard_s": 600,
    "early_grid_enabled": False,
    "cheap_grid_limit_eur_kwh": 0.15,
    "early_grid_requires_forecast_shortfall": True,
    "adaptive_power_guard": True,
    "adaptive_power_min_samples": 10,
    "adaptive_power_max_multiplier": 2.0,
}


def finite(value):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None


def _median(values):
    vals = [float(v) for v in values if finite(v) is not None]
    return statistics.median(vals) if vals else None


class BaseLoadModel:
    """Small bounded profile learner; no ML dependency and no raw-history hoard."""
    def __init__(self, seed=None):
        seed = seed or {}
        profile = seed.get("base_load_profile", {})
        self.seed_hour = {int(k): float(v) for k, v in (profile.get("median_w_by_hour", {}) or {}).items()}
        self.seed_daytype = {
            str(dt): {int(k): float(v) for k, v in rows.items()}
            for dt, rows in (profile.get("median_w_by_daytype_hour", {}) or {}).items()
        }
        self.bins = {}
        self.last_sample_wall = 0.0
        self.accepted = 0

    def snapshot(self):
        return {"bins": self.bins, "accepted": self.accepted, "last_sample_wall": self.last_sample_wall}

    def restore(self, data):
        if not isinstance(data, dict):
            return
        raw = data.get("bins", {})
        self.bins = raw if isinstance(raw, dict) else {}
        self.accepted = max(0, int(data.get("accepted", 0) or 0))
        self.last_sample_wall = max(0.0, float(data.get("last_sample_wall", 0) or 0))

    @staticmethod
    def _key(dt):
        return f"{'weekday' if dt.weekday() < 5 else 'weekend'}:{dt.hour}"

    def observe(self, wall_ts, local_now, load_w, *, contaminated=False):
        v = finite(load_w)
        if contaminated or v is None or v < 50 or v > 20000 or wall_ts - self.last_sample_wall < 900:
            return False
        self.last_sample_wall = wall_ts
        key = self._key(local_now)
        rows = self.bins.setdefault(key, {"days": {}})["days"]
        day = local_now.date().isoformat()
        vals = rows.setdefault(day, [])
        vals.append(round(v, 1))
        del vals[:-8]
        while len(rows) > 60:
            del rows[next(iter(rows))]
        self.accepted += 1
        return True

    def estimate(self, dt, min_days=4):
        key = self._key(dt)
        entry = self.bins.get(key, {})
        daily = [_median(v) for v in entry.get("days", {}).values()]
        daily = [v for v in daily if v is not None]
        if len(daily) >= int(min_days):
            spread = (statistics.quantiles(daily, n=4)[2] - statistics.quantiles(daily, n=4)[0]) if len(daily) >= 4 else 0
            med = _median(daily)
            confidence = min(.92, len(daily) / max(6.0, float(min_days) * 2)) * max(.35, 1 - spread / max(500.0, med or 500))
            return max(0.0, med or 0.0), confidence, f"live {len(daily)} dagen"
        daytype = "weekday" if dt.weekday() < 5 else "weekend"
        if dt.hour in self.seed_daytype.get(daytype, {}):
            return max(0.0, self.seed_daytype[daytype][dt.hour]), .35, "historische bootstrap dagtype"
        if dt.hour in self.seed_hour:
            return max(0.0, self.seed_hour[dt.hour]), .25, "historische bootstrap uur"
        return 800.0, .10, "conservatieve fallback"


@dataclass
class PlannedSlot:
    start: datetime
    pv_w: float
    base_w: float
    import_price: float
    export_price: float
    planned_load_w: float = 0.0
    devices: list[str] = field(default_factory=list)
    battery_w: float = 0.0  # + charge, - discharge advisory

    @property
    def net_without_flex_w(self):
        return self.base_w - self.pv_w

    @property
    def net_after_plan_w(self):
        return self.net_without_flex_w + self.planned_load_w + self.battery_w


@dataclass
class DevicePlan:
    id: str
    name: str
    required_kwh: float
    planned_kwh: float
    selected_slots: list[int]
    reason: str
    cheap_grid_slots: list[int] = field(default_factory=list)
    contiguous_cycle: bool = False
    cycle_program: str = ""
    cycle_confidence: float = 0.0
    cycle_duration_min: float = 0.0


@dataclass
class UnifiedPlan:
    generated_at: datetime
    horizon_h: int
    slot_min: int
    slots: list[PlannedSlot]
    devices: dict[str, DevicePlan]
    warnings: list[str]
    findings: list[str]
    confidence: float
    predicted_import_kwh: float
    predicted_export_kwh: float
    predicted_cost_eur: float
    predicted_self_use_kwh: float

    def current_device_state(self, device_id, local_now):
        dp = self.devices.get(device_id)
        if not dp or not self.slots:
            return False, False, "Geen gepland slot"
        slot_seconds = self.slot_min * 60
        idx = int(max(0, (local_now - self.slots[0].start).total_seconds()) // slot_seconds)
        idx = min(idx, len(self.slots) - 1)
        selected = idx in dp.selected_slots
        grid = idx in dp.cheap_grid_slots
        if selected:
            return True, grid, "Gepland in huidig rolling-horizonblok"
        future = [x for x in dp.selected_slots if x > idx]
        if future:
            eta = (self.slots[future[0]].start - local_now).total_seconds() / 60
            return False, False, f"Planner wacht op gunstiger blok over ongeveer {max(0, round(eta))} min"
        return False, False, dp.reason

    def overview(self, max_slots=24):
        return {
            "generated_at": self.generated_at.isoformat(), "horizon_h": self.horizon_h, "slot_min": self.slot_min,
            "confidence": round(self.confidence, 3), "predicted_import_kwh": round(self.predicted_import_kwh, 3),
            "predicted_export_kwh": round(self.predicted_export_kwh, 3), "predicted_cost_eur": round(self.predicted_cost_eur, 3),
            "predicted_self_use_kwh": round(self.predicted_self_use_kwh, 3), "warnings": list(self.warnings),
            "findings": list(self.findings),
            "devices": {k: {"name": v.name, "required_kwh": round(v.required_kwh, 3), "planned_kwh": round(v.planned_kwh, 3),
                              "selected_slots": list(v.selected_slots), "cheap_grid_slots": list(v.cheap_grid_slots), "reason": v.reason,
                              "contiguous_cycle": v.contiguous_cycle, "cycle_program": v.cycle_program,
                              "cycle_confidence": round(v.cycle_confidence,3), "cycle_duration_min": round(v.cycle_duration_min,1)}
                        for k, v in self.devices.items()},
            "timeline": [{"start": s.start.isoformat(), "pv_w": round(s.pv_w), "base_w": round(s.base_w),
                          "planned_load_w": round(s.planned_load_w), "battery_w": round(s.battery_w),
                          "net_w": round(s.net_after_plan_w), "devices": list(s.devices),
                          "import_price": round(s.import_price, 4), "export_price": round(s.export_price, 4)}
                         for s in self.slots[:max_slots]],
        }


class UnifiedPlanner:
    def __init__(self, settings=None, seed=None):
        self.settings = {**UNIFIED_PLANNER_DEFAULTS, **(settings or {})}
        self.base_load = BaseLoadModel(seed)
        self.plan = None
        self.last_plan_wall = 0.0
        self.plan_runs = 0
        self.last_pv_mae_w = None
        self.last_base_mae_w = None
        self.quality = PlanQualityTracker(self.settings.get("quality_retention_days", 45))
        self.replay = ReplayBuffer(self.settings.get("replay_retention_days", 14))
        # Dashboard reads can be frequent. What-if replay is intentionally heavier
        # than normal status rendering, so cache its advisory result for a short
        # interval and invalidate it when replay data / settings / device planning
        # inputs change. This never affects the live dispatch plan.
        self._replay_cache = None
        self._replay_cache_wall = 0.0
        self._replay_cache_key = None

    def snapshot(self):
        return {"base_load": self.base_load.snapshot(), "plan_runs": self.plan_runs,
                "last_pv_mae_w": self.last_pv_mae_w, "last_base_mae_w": self.last_base_mae_w,
                "quality": self.quality.snapshot(), "replay": self.replay.snapshot()}

    def restore(self, data):
        if not isinstance(data, dict): return
        self.base_load.restore(data.get("base_load", {}))
        self.plan_runs = max(0, int(data.get("plan_runs", 0) or 0))
        self.last_pv_mae_w = finite(data.get("last_pv_mae_w"))
        self.last_base_mae_w = finite(data.get("last_base_mae_w"))
        self.quality.restore(data.get("quality", {}))
        self.replay.restore(data.get("replay", {}))

    def due(self, wall_ts):
        return self.plan is None or wall_ts - self.last_plan_wall >= max(60, int(self.settings["replan_min"]) * 60)

    @staticmethod
    def _within_window(dt, cfg):
        if not cfg.get("time_window_enabled"):
            return True
        start = str(cfg.get("time_window_start", "00:00:00"))[:5]
        end = str(cfg.get("time_window_end", "23:59:00"))[:5]
        hm = dt.strftime("%H:%M")
        return (start <= hm < end) if start <= end else (hm >= start or hm < end)

    @staticmethod
    def _deadline_ok(dt, cfg):
        deadline = str(cfg.get("daily_deadline", "23:59:00"))[:5]
        return dt.strftime("%H:%M") <= deadline

    def build(self, *, local_now, pv_hourly_w, import_prices, export_prices, devices,
              capacity_target_w=None, battery=None):
        c = self.settings
        slot_min = max(5, int(c["slot_min"])); horizon_h = max(6, int(c["horizon_h"]))
        n = max(1, int(horizon_h * 60 / slot_min)); slot_h = slot_min / 60.0
        # Align planning to a slot boundary so repeated runs are stable.
        minute = (local_now.minute // slot_min) * slot_min
        start = local_now.replace(minute=minute, second=0, microsecond=0)
        pv_hours = list(pv_hourly_w or [])
        warnings=[]; findings=[]; slots=[]; base_conf=[]
        for i in range(n):
            dt = start + timedelta(minutes=i * slot_min)
            hidx = min(len(pv_hours)-1, max(0, int((dt-start).total_seconds()//3600))) if pv_hours else -1
            pv = max(0.0, finite(pv_hours[hidx]) or 0.0) if hidx >= 0 else 0.0
            base, conf, source = self.base_load.estimate(dt, c.get("base_load_min_days", 4)); base_conf.append(conf)
            imp = import_prices[i] if i < len(import_prices) else import_prices[-1] if import_prices else .30
            exp = export_prices[i] if i < len(export_prices) else export_prices[-1] if export_prices else .03
            slots.append(PlannedSlot(dt, pv, base, float(imp), float(exp)))
        if not pv_hours: warnings.append("Geen bruikbare PV-horizon; planner blijft conservatief")
        if base_conf and statistics.mean(base_conf) < .3: warnings.append("Basislastprofiel heeft nog weinig vertrouwen")

        plans={}
        # A protected cycle that is already running is no longer an optional
        # future start. Reserve its learned/configured remaining average load in
        # the horizon so the planner does not schedule another flex load into
        # energy that is already committed. Realtime measurement remains the
        # authority if the cycle consumes more/less than its learned average.
        for d in devices:
            if not d.get("fixed_active_cycle"):
                continue
            power=max(1.0,float(d.get("active_cycle_average_w") or d.get("power_w") or 1.0))
            remaining=max(0.0,float(d.get("active_cycle_remaining_min") or 0.0))
            count=max(1,math.ceil(remaining/slot_min)) if remaining>0 else 1
            count=min(len(slots),count)
            for idx in range(count):
                slots[idx].planned_load_w += power
                slots[idx].devices.append(d["id"])
            planned=power*count*slot_h/1000.0
            plans[d["id"]]=DevicePlan(d["id"],d.get("name",d["id"]),planned,planned,list(range(count)),
                "Lopende beschermde cyclus gereserveerd in de horizon",[],True,str(d.get("cycle_program") or ""),
                float(d.get("cycle_confidence") or 0.0),float(d.get("cycle_duration_min") or 0.0))
            if remaining<=0:
                warnings.append(f"{d.get('name',d['id'])}: lopende cyclus zonder resterend duurprofiel; alleen huidig planblok gereserveerd")

        # High priority first; scheduling cost still chooses the best slots inside each deadline.
        for d in sorted(devices, key=lambda x:(int(x.get("priority",50)), str(x.get("id")))):
            if d.get("fixed_active_cycle"):
                continue
            if not d.get("enabled", True) or not d.get("forecast_deferrable", False):
                continue
            required=max(0.0, finite(d.get("required_kwh")) or 0.0)
            if required <= .001:
                plans[d["id"]]=DevicePlan(d["id"],d.get("name",d["id"]),0,0,[],"Geen resterend dagdoel")
                continue
            power=max(1.0, finite(d.get("power_w")) or 1.0)
            energy_per_slot=power*slot_h/1000.0
            slots_needed=max(1, math.ceil(required/max(.001,energy_per_slot)))
            eligible=[]
            for idx,s in enumerate(slots):
                if not self._within_window(s.start,d) or not self._deadline_ok(s.start,d): continue
                net_before=s.net_after_plan_w
                expected_surplus=max(0.0,-net_before-float(c.get("pv_reserve_w",150)))
                grid_needed=max(0.0, power-expected_surplus)
                cheap_allowed=bool(d.get("cheap_grid_allowed") and d.get("deadline_grid_allowed") and c.get("early_grid_enabled"))
                solar_enough=expected_surplus >= min(power, max(150.0,power*.35))
                if not solar_enough and not cheap_allowed:
                    continue
                marginal=((grid_needed/1000.0)*s.import_price + (min(power,expected_surplus)/1000.0)*s.export_price) if c.get("price_optimisation",True) else (grid_needed/1000.0)
                if capacity_target_w and c.get("capacity_penalty_enabled"):
                    over=max(0.0, net_before+power-float(capacity_target_w))
                    marginal += (over/1000.0)*float(c.get("capacity_penalty_eur_kwh",.5))
                # Earlier slots get a tiny stability preference, but price/PV dominate.
                marginal += idx*1e-5
                eligible.append((marginal,idx,solar_enough,grid_needed))
            eligible.sort(key=lambda x:x[0])
            cheap=[]
            contiguous=bool(d.get("contiguous_cycle"))
            cycle_program=str(d.get("cycle_program") or "")
            cycle_conf=float(d.get("cycle_confidence") or 0.0)
            cycle_duration=max(0.0,float(d.get("cycle_duration_min") or 0.0))
            if contiguous:
                # Protected cycles are scheduled as one contiguous block. Energy is
                # represented by an average cycle power; a separate conservative
                # peak is used for capacity-penalty scoring. Realtime headroom still
                # decides whether the cycle may actually start. A missing duration
                # is not guessed from peak power: that could understate a dishwasher
                # or washer cycle dramatically. Learn one or configure a fallback.
                if cycle_duration <= 0:
                    chosen=[]; planned=0.0
                    reason="Beschermde cyclus heeft nog geen betrouwbare duur; eerst leren of een fallback instellen"
                    plans[d["id"]]=DevicePlan(d["id"],d.get("name",d["id"]),required,planned,chosen,reason,[],True,cycle_program,cycle_conf,cycle_duration)
                    warnings.append(f"{d.get('name',d['id'])}: beschermde cyclus heeft nog geen duurprofiel")
                    continue
                duration_slots=max(1, math.ceil(cycle_duration/slot_min))
                avg_power=max(1.0, float(d.get("cycle_average_w") or (required*1000/max(duration_slots*slot_h,.001))))
                peak_power=max(avg_power, float(d.get("cycle_peak_w") or power))
                candidates=[]
                cheap_allowed=bool(d.get("cheap_grid_allowed") and d.get("deadline_grid_allowed") and c.get("early_grid_enabled"))
                for start_idx in range(0, max(0,len(slots)-duration_slots+1)):
                    run=range(start_idx,start_idx+duration_slots)
                    if any(not self._within_window(slots[j].start,d) or not self._deadline_ok(slots[j].start,d) for j in run):
                        continue
                    total_cost=0.0; solar_kwh=0.0; grid_slots=[]
                    for j in run:
                        s=slots[j]; net_before=s.net_after_plan_w
                        surplus=max(0.0,-net_before-float(c.get("pv_reserve_w",150)))
                        solar=min(avg_power,surplus); grid=max(0.0,avg_power-solar)
                        solar_kwh += solar*slot_h/1000.0
                        total_cost += grid*slot_h/1000.0*s.import_price + solar*slot_h/1000.0*s.export_price
                        if capacity_target_w and c.get("capacity_penalty_enabled"):
                            over=max(0.0, net_before+peak_power-float(capacity_target_w))
                            total_cost += (over/1000.0)*float(c.get("capacity_penalty_eur_kwh",.5))
                        if grid>avg_power*.65: grid_slots.append(j)
                    # Without explicit grid permission, require meaningful predicted
                    # PV contribution across the whole cycle rather than every slot.
                    if not cheap_allowed and solar_kwh < required*.35:
                        continue
                    total_cost += start_idx*1e-5
                    candidates.append((total_cost,start_idx,list(run),grid_slots))
                if candidates:
                    _,_,chosen,grid_slots=min(candidates,key=lambda x:x[0]); cheap=list(grid_slots)
                    for idx in chosen:
                        slots[idx].planned_load_w += avg_power; slots[idx].devices.append(d["id"])
                    planned=min(required, avg_power*len(chosen)*slot_h/1000.0)
                    reason=f"Beschermde cyclus aaneengesloten ingepland ({cycle_program or 'standaardprogramma'})"
                else:
                    chosen=[]; planned=0.0; reason="Beschermde cyclus niet veilig/aaneengesloten planbaar binnen venster en deadline"
            else:
                chosen=sorted(x[1] for x in eligible[:slots_needed])
                for idx in chosen:
                    s=slots[idx]; s.planned_load_w += power; s.devices.append(d["id"])
                    expected_surplus=max(0.0,-(s.base_w-s.pv_w)-float(c.get("pv_reserve_w",150)))
                    if expected_surplus < power*.35: cheap.append(idx)
                planned=len(chosen)*energy_per_slot
                reason=("Dagdoel volledig ingepland" if planned+1e-6>=required else
                        f"Slechts {planned:.2f} van {required:.2f} kWh planbaar binnen voorwaarden")
            if planned+1e-6 < required: warnings.append(f"{d.get('name',d['id'])}: dagdoel/cyclus niet volledig planbaar")
            plans[d["id"]]=DevicePlan(d["id"],d.get("name",d["id"]),required,planned,chosen,reason,cheap,contiguous,cycle_program,cycle_conf,cycle_duration)

        # Battery remains advisory: absorb predicted surplus, then shave expensive deficits.
        if c.get("battery_advisory") and battery and battery.get("available_kwh",0)>0:
            cap=max(0.0,float(battery.get("available_kwh",0))); p=max(0.0,float(battery.get("power_w",0)))
            if p>0 and cap>0:
                soc_energy=cap*max(0,min(1,float(battery.get("soc_pct",50))/100))
                max_e=cap*max(0,min(1,float(battery.get("max_soc_pct",95))/100))
                min_e=cap*max(0,min(1,float(battery.get("min_soc_pct",20))/100))
                for s in slots:
                    surplus=max(0.0,-s.net_after_plan_w-float(c.get("pv_reserve_w",150)))
                    charge=min(p,surplus,max(0,(max_e-soc_energy)/slot_h*1000))
                    if charge>0: s.battery_w=charge; soc_energy += charge*slot_h/1000
                # expensive deficits first among future slots, but preserve chronological SOC feasibility approximately
                threshold=statistics.median([x.import_price for x in slots]) if slots else .3
                for s in slots:
                    deficit=max(0.0,s.net_after_plan_w)
                    if deficit>0 and s.import_price>=threshold and soc_energy>min_e:
                        discharge=min(p,deficit,max(0,(soc_energy-min_e)/slot_h*1000))
                        s.battery_w=-discharge; soc_energy -= discharge*slot_h/1000
                findings.append("Batterijadvies is alleen what-if; realtime batterijguard blijft eigenaar van fysieke setpoints")

        imp_kwh=exp_kwh=cost=selfuse=0.0
        for s in slots:
            net=s.net_after_plan_w
            if net>=0:
                imp_kwh += net*slot_h/1000; cost += net*slot_h/1000*s.import_price
            else:
                exp_kwh += -net*slot_h/1000; cost -= (-net)*slot_h/1000*s.export_price
            selfuse += max(0.0,min(s.pv_w,s.base_w+s.planned_load_w+max(0,s.battery_w)))*slot_h/1000
        confidence=min(.95,max(.1,statistics.mean(base_conf) if base_conf else .1))
        self.plan_runs += 1; self.last_plan_wall=datetime.now().timestamp()
        self.plan=UnifiedPlan(start,horizon_h,slot_min,slots,plans,warnings,findings,confidence,imp_kwh,exp_kwh,cost,selfuse)
        return self.plan

    def current_slot(self, local_now):
        if not self.plan or not self.plan.slots:
            return None
        slot_s=self.plan.slot_min*60
        idx=int(max(0,(local_now-self.plan.slots[0].start).total_seconds())//slot_s)
        if idx<0 or idx>=len(self.plan.slots):
            return None
        return self.plan.slots[idx]

    def observe_actual(self, *, wall_ts, local_now, actual_pv_w, actual_base_w, actual_grid_w,
                       import_price=.30, export_price=.03, capacity_target_w=None,
                       execution_total=0, execution_matches=0):
        slot=self.current_slot(local_now)
        if slot and self.settings.get("quality_tracking",True):
            self.quality.observe(wall_ts=wall_ts,local_now=local_now,predicted_pv_w=slot.pv_w,actual_pv_w=actual_pv_w,
                                 predicted_base_w=slot.base_w,actual_base_w=actual_base_w,predicted_net_w=slot.net_after_plan_w,
                                 actual_net_w=actual_grid_w,execution_total=execution_total,execution_matches=execution_matches)
            q=self.quality.overview().get("last_7d",{})
            self.last_pv_mae_w=q.get("pv_mae_w"); self.last_base_mae_w=q.get("base_mae_w")
        if self.settings.get("replay_enabled",True) and actual_base_w is not None:
            self.replay.observe(local_now=local_now,pv_w=actual_pv_w,base_w=actual_base_w,grid_w=actual_grid_w,
                                import_price=import_price,export_price=export_price,capacity_target_w=capacity_target_w)

    def replay_scenarios(self, devices):
        """Compare a few planner strategies on recent measured 15-minute inputs.

        This is a planner replay, not a physical appliance simulator: it assumes
        configured daily goals/windows were available on replay days and therefore
        never claims euro-exact realised savings.
        """
        import time
        rows=self.replay.rows()
        latest = rows[-1][0].isoformat() if rows else ""
        # Only planner-relevant device fields take part in the cache key. A live
        # status text or measured display wattage should not re-run a multi-day
        # what-if simulation on every dashboard refresh.
        dev_key = tuple(sorted((
            str(d.get("id") or ""), bool(d.get("enabled", True)), bool(d.get("forecast_deferrable", False)),
            int(d.get("priority", 50) or 50), round(float(d.get("daily_energy_goal_kwh", 0) or 0), 4),
            int(d.get("min_daily_runtime_s", 0) or 0), str(d.get("daily_deadline", "23:59:00")),
            bool(d.get("time_window_enabled", False)), str(d.get("time_window_start", "00:00:00")),
            str(d.get("time_window_end", "23:59:00")), bool(d.get("cheap_grid_allowed", False)),
            bool(d.get("deadline_grid_allowed", False)), bool(d.get("contiguous_cycle", False)),
            round(float(d.get("cycle_energy_kwh", 0) or 0), 4),
            round(float(d.get("cycle_duration_min", 0) or 0), 1), round(float(d.get("power_w", 0) or 0), 1),
        ) for d in devices))
        setting_key = tuple((k, self.settings.get(k)) for k in (
            "slot_min", "pv_reserve_w", "base_load_min_days", "price_optimisation",
            "capacity_penalty_enabled", "capacity_penalty_eur_kwh", "early_grid_enabled"))
        cache_key = (len(rows), latest, dev_key, setting_key)
        now_wall = time.monotonic()
        if (self._replay_cache is not None and cache_key == self._replay_cache_key
                and now_wall - self._replay_cache_wall < 900):
            return self._replay_cache
        by_day={}
        for dt,row in rows:
            by_day.setdefault(dt.date(),[]).append((dt,row))
        days=[(d,sorted(v,key=lambda x:x[0])) for d,v in sorted(by_day.items()) if len(v)>=48]
        if len(days)<2:
            result={"ready":False,"reason":"Minstens twee voldoende volledige replaydagen nodig","buffer":self.replay.overview(),"scenarios":[]}
            self._replay_cache=result; self._replay_cache_key=cache_key; self._replay_cache_wall=now_wall
            return result
        current=dict(self.settings)
        variants=[
            ("Huidig",current),
            ("Meer PV benutten",{**current,"pv_reserve_w":max(0.0,float(current.get("pv_reserve_w",150))-150)}),
            ("Piek strenger",{**current,"capacity_penalty_enabled":True,"capacity_penalty_eur_kwh":max(1.0,float(current.get("capacity_penalty_eur_kwh",.5))*2)}),
            ("Prijs niet meewegen",{**current,"price_optimisation":False}),
        ]
        results=[]
        for label,settings in variants:
            totals={"import_kwh":0.0,"export_kwh":0.0,"cost_eur":0.0,"peak_w":0.0,"planned_kwh":0.0,"days":0}
            for _,samples in days[-7:]:
                first=samples[0][0]
                # Hourly PV from measured replay; base profile is seeded from measured hour medians.
                hours={}
                for dt,row in samples:
                    hours.setdefault(dt.hour,[]).append(row)
                pv_hour=[statistics.mean([x["pv_w"] for x in hours.get(h,[])]) if hours.get(h) else 0.0 for h in range(24)]
                seed={"base_load_profile":{"median_w_by_hour":{str(h):statistics.median([x["base_w"] for x in vals]) for h,vals in hours.items()}}}
                p=UnifiedPlanner({**settings,"horizon_h":24,"replay_enabled":False,"quality_tracking":False},seed)
                n=max(1,int(24*60/max(15,int(settings.get("slot_min",15)))))
                imp=[]; exp=[]
                sample_rows=[x[1] for x in samples]
                for i in range(n):
                    src=sample_rows[min(len(sample_rows)-1,int(i*len(sample_rows)/n))]
                    imp.append(float(src.get("import_price",.30))); exp.append(float(src.get("export_price",.03)))
                devs=[]
                for d in devices:
                    if not d.get("forecast_deferrable",False) or not d.get("enabled",True): continue
                    power=max(1.0,float(d.get("power_w",d.get("nominal_w",1000)) or 1000))
                    req=max(0.0,float(d.get("daily_energy_goal_kwh",0) or 0),float(d.get("min_daily_runtime_s",0) or 0)*power/3_600_000)
                    if d.get("contiguous_cycle") and float(d.get("cycle_energy_kwh",0) or 0)>0: req=max(req,float(d.get("cycle_energy_kwh")))
                    devs.append({**d,"required_kwh":req,"power_w":power})
                capvals=[finite(x.get("capacity_target_w")) for _,x in samples]; capvals=[x for x in capvals if x is not None]
                pl=p.build(local_now=first.replace(hour=0,minute=0,second=0,microsecond=0),pv_hourly_w=pv_hour,import_prices=imp,export_prices=exp,devices=devs,capacity_target_w=statistics.median(capvals) if capvals else None,battery=None)
                totals["import_kwh"]+=pl.predicted_import_kwh; totals["export_kwh"]+=pl.predicted_export_kwh; totals["cost_eur"]+=pl.predicted_cost_eur
                totals["peak_w"]=max(totals["peak_w"],max([max(0,s.net_after_plan_w) for s in pl.slots] or [0]))
                totals["planned_kwh"]+=sum(x.planned_kwh for x in pl.devices.values()); totals["days"]+=1
            results.append({"label":label,**{k:round(v,3) if isinstance(v,float) else v for k,v in totals.items()}})
        base=results[0] if results else {}
        for row in results[1:]:
            row["delta_import_kwh"]=round(row["import_kwh"]-base.get("import_kwh",0),3)
            row["delta_export_kwh"]=round(row["export_kwh"]-base.get("export_kwh",0),3)
            row["delta_cost_eur"]=round(row["cost_eur"]-base.get("cost_eur",0),3)
            row["delta_peak_w"]=round(row["peak_w"]-base.get("peak_w",0),1)
        result={"ready":True,"reason":"Plannerreplay op recente gemeten PV/basislast; geen fysieke appliance-simulatie",
                "buffer":self.replay.overview(),"scenarios":results}
        self._replay_cache=result; self._replay_cache_key=cache_key; self._replay_cache_wall=now_wall
        return result

    def overview(self, devices=None):
        base={"enabled": bool(self.settings.get("enabled")), "plan_runs": self.plan_runs,
              "base_load_samples": self.base_load.accepted, "last_pv_mae_w": self.last_pv_mae_w,
              "last_base_mae_w": self.last_base_mae_w, "quality": self.quality.overview(),
              "replay": self.replay_scenarios(devices or []) if self.settings.get("replay_enabled",True) else {"ready":False,"reason":"Replay uitgeschakeld","scenarios":[]},
              **(self.plan.overview(int(self.settings.get("max_timeline_slots",48))) if self.plan else {
                  "warnings": ["Nog geen rolling-horizonplan berekend"], "findings": [], "timeline": [], "devices": {}, "confidence": 0.0})}
        return base

PLANNER_SETTING_SPECS = {
    "enabled": {"label":"Unified Planner", "type":"boolean", "default":True,
                "description":"Berekent één gezamenlijk rolling-horizonplan voor flexibele lasten.",
                "recommendation":"Aan laten. Zet alleen uit voor foutzoeken of pure realtime overschotregeling.",
                "on_effect":"Flexibele dagdoelen worden vooruit gepland.", "off_effect":"Toestellen reageren alleen op realtime regels en deadlines."},
    "horizon_h": {"label":"Planningshorizon", "type":"number", "unit":"uur", "min":12, "max":72, "step":1, "default":36,
                  "description":"Hoe ver SolarPilot vooruit kijkt.", "recommendation":"36 uur is voor jouw PV-schaduw, boiler en toekomstige batterij een goede balans.",
                  "lower_effect":"Sneller en eenvoudiger, maar minder zicht op morgen.", "higher_effect":"Meer vooruitzicht, maar verder weg gelegen forecasts zijn onzekerder."},
    "slot_min": {"label":"Planblokgrootte", "type":"number", "unit":"min", "min":15, "max":60, "step":15, "default":15,
                 "description":"Tijdresolutie waarmee het energieplan wordt opgebouwd.", "recommendation":"15 minuten sluit aan op je HomeWizard-data en capaciteitstarief.",
                 "lower_effect":"Fijnere planning en meer rekenwerk.", "higher_effect":"Rustiger plan, maar minder precies rond schaduw en pieken."},
    "replan_min": {"label":"Herplannen elke", "type":"number", "unit":"min", "min":15, "max":60, "step":15, "default":15,
                   "description":"Hoe vaak nieuwe metingen en forecasts in een nieuw plan worden verwerkt.", "recommendation":"15 minuten. Dit betekent niet dat toestellen elke 15 minuten schakelen.",
                   "lower_effect":"Reageert sneller op afwijkingen.", "higher_effect":"Plan verandert minder vaak maar reageert trager."},
    "pv_reserve_w": {"label":"PV-reserve", "type":"number", "unit":"W", "min":0, "max":3000, "step":50, "default":150,
                    "description":"Vermogen dat de planner niet vooraf toewijst, als buffer voor meetfouten en gewone huislast.", "recommendation":"150 W is een bruikbaar startpunt.",
                    "lower_effect":"Meer zonne-energie wordt gepland, met meer kans op korte netafname.", "higher_effect":"Conservatiever en rustiger, maar iets meer injectie kan ongebruikt blijven."},
    "base_load_learning": {"label":"Basislast leren", "type":"boolean", "default":True,
                           "description":"Leert hoeveel niet-stuurbaar huisverbruik per uur/dagtype normaal aanwezig is.", "recommendation":"Aan laten; vervuilde perioden met Wallbox/eigen flexlast worden geweerd.",
                           "on_effect":"Planning houdt steeds beter rekening met je echte huisprofiel.", "off_effect":"Alleen historische bootstrap/fallback wordt gebruikt."},
    "base_load_min_days": {"label":"Minimum leerdagen basislast", "type":"number", "unit":"dagen", "min":2, "max":30, "step":1, "default":4,
                           "description":"Aantal verschillende dagen nodig voordat live basislast een uurprofiel mag vervangen.", "recommendation":"4–7 dagen. Meer dagen geeft meer zekerheid maar leert trager.",
                           "lower_effect":"Sneller persoonlijk, maar gevoeliger voor uitzonderlijke dagen.", "higher_effect":"Robuuster, maar trager aangepast aan veranderingen."},
    "price_optimisation": {"label":"Prijsoptimalisatie", "type":"boolean", "default":True,
                           "description":"Laat prijsverschillen meewegen als een bruikbare dynamische prijsreeks beschikbaar is.", "recommendation":"Aan mag; zonder dynamische reeks valt SolarPilot veilig terug op vaste prijzen.",
                           "on_effect":"Goedkopere blokken krijgen voorkeur wanneer andere regels dat toelaten.", "off_effect":"Planning focust vooral op PV, deadlines en pieken."},
    "capacity_penalty_enabled": {"label":"Kwartierpiek meewegen", "type":"boolean", "default":True,
                                 "description":"Maakt voorspelde blokken boven het ingestelde piekdoel minder aantrekkelijk.", "recommendation":"Aan laten als je capaciteitstarief wilt beperken.",
                                 "on_effect":"Planner vermijdt waar mogelijk nieuwe pieken.", "off_effect":"Alleen de realtime piekguard grijpt nog in."},
    "capacity_penalty_eur_kwh": {"label":"Gewicht kwartierpiek", "type":"number", "unit":"€/kWh virtueel", "min":0, "max":5, "step":0.05, "default":0.5,
                                 "description":"Interne planningsstraf; dit is geen echte energieprijs.", "recommendation":"0,50 als startpunt. Pas pas aan na backtesting.",
                                 "lower_effect":"Planner accepteert makkelijker een hogere kwartierpiek.", "higher_effect":"Planner spreidt lasten sterker, mogelijk ten koste van zonnebenutting."},
    "battery_advisory": {"label":"Batterij adviserend meeplannen", "type":"boolean", "default":True,
                         "description":"Tekent toekomstige batterijlaad/ontlaadruimte mee in het plan zonder daarmee batterijbediening vrij te geven.", "recommendation":"Aan laten; fysieke batterijbediening blijft apart vergrendeld.",
                         "on_effect":"Plan kan batterijscenario en flexlasten samen bekijken.", "off_effect":"Batterijruimte wordt niet meegenomen in de planning."},
    "quality_tracking": {"label":"Plannerkwaliteit meten", "type":"boolean", "default":True,
                         "description":"Vergelijkt voorspelde PV, basislast, netresultaat en geplande starts achteraf met de werkelijkheid.",
                         "recommendation":"Aan laten. Er worden alleen compacte dagaggregaten bewaard.",
                         "on_effect":"Je ziet 7/30-dagenfouten en planbetrouwbaarheid.", "off_effect":"Geen nieuwe kwaliteitsmetingen; planning zelf blijft werken."},
    "quality_retention_days": {"label":"Kwaliteitshistorie bewaren", "type":"number", "unit":"dagen", "min":7, "max":90, "step":1, "default":45,
                         "description":"Hoeveel dagen geaggregeerde plannerfouten worden bijgehouden.", "recommendation":"45 dagen geeft genoeg trend zonder veel opslag.",
                         "lower_effect":"Minder historie en sneller reagerende trends.", "higher_effect":"Meer seizoenscontext, maar veranderingen vallen trager op."},
    "replay_enabled": {"label":"Plannerreplay / what-if", "type":"boolean", "default":True,
                         "description":"Bewaar een begrensde 15-minutenreplay om instellingen op recente gemeten PV en basislast te vergelijken.",
                         "recommendation":"Aan laten tijdens finetuning; het is adviserend en stuurt niets.",
                         "on_effect":"Planning-tab vergelijkt alternatieve strategieën op recente data.", "off_effect":"Geen nieuwe replaydata en geen scenariovergelijking."},
    "replay_retention_days": {"label":"Replayperiode", "type":"number", "unit":"dagen", "min":3, "max":30, "step":1, "default":14,
                         "description":"Aantal dagen 15-minuteninputs voor what-ifvergelijkingen.", "recommendation":"14 dagen is een goede balans; voor seizoensanalyse gebruik de offline backtesttool.",
                         "lower_effect":"Sneller aangepast aan recente omstandigheden maar minder representatief.", "higher_effect":"Meer context maar grotere kans dat oud weer/gebruik de vergelijking beïnvloedt."},
}


def planner_settings_catalog(settings):
    out=[]
    for key,spec in PLANNER_SETTING_SPECS.items():
        row={"key":key,**spec,"value":settings.get(key,spec.get("default"))}
        out.append(row)
    return out
