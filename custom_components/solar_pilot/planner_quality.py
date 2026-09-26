"""Compact planner accuracy and rolling replay data for SolarPilot."""
from __future__ import annotations

from datetime import datetime, timedelta
import math


def finite(value):
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except (TypeError, ValueError):
        return None


class PlanQualityTracker:
    """Store aggregated daily errors instead of raw high-frequency forecast traces."""
    def __init__(self, retention_days=45):
        self.retention_days = int(retention_days)
        self.days = {}
        self.last_sample_wall = 0.0

    def snapshot(self):
        return {"days": self.days, "last_sample_wall": self.last_sample_wall, "retention_days": self.retention_days}

    def restore(self, data):
        if not isinstance(data, dict):
            return
        raw = data.get("days", {})
        self.days = raw if isinstance(raw, dict) else {}
        self.last_sample_wall = max(0.0, float(data.get("last_sample_wall", 0) or 0))
        self.retention_days = max(7, int(data.get("retention_days", self.retention_days) or self.retention_days))

    def observe(self, *, wall_ts, local_now, predicted_pv_w, actual_pv_w,
                predicted_base_w=None, actual_base_w=None, predicted_net_w=None,
                actual_net_w=None, execution_total=0, execution_matches=0):
        if wall_ts - self.last_sample_wall < 300:
            return False
        self.last_sample_wall = float(wall_ts)
        key = local_now.date().isoformat()
        row = self.days.setdefault(key, {
            "count": 0, "pv_abs": 0.0, "pv_bias": 0.0, "base_count": 0,
            "base_abs": 0.0, "base_bias": 0.0, "net_count": 0,
            "net_abs": 0.0, "net_bias": 0.0, "exec_total": 0, "exec_matches": 0,
        })
        pp, ap = finite(predicted_pv_w), finite(actual_pv_w)
        if pp is not None and ap is not None:
            err = ap - pp
            row["pv_abs"] += abs(err); row["pv_bias"] += err; row["count"] += 1
        pb, ab = finite(predicted_base_w), finite(actual_base_w)
        if pb is not None and ab is not None:
            err = ab - pb
            row["base_abs"] += abs(err); row["base_bias"] += err; row["base_count"] += 1
        pn, an = finite(predicted_net_w), finite(actual_net_w)
        if pn is not None and an is not None:
            err = an - pn
            row["net_abs"] += abs(err); row["net_bias"] += err; row["net_count"] += 1
        row["exec_total"] += max(0, int(execution_total or 0))
        row["exec_matches"] += max(0, int(execution_matches or 0))
        cutoff = local_now.date() - timedelta(days=self.retention_days)
        for day in list(self.days):
            try:
                if datetime.fromisoformat(day).date() < cutoff:
                    del self.days[day]
            except ValueError:
                del self.days[day]
        return True

    def _aggregate(self, days):
        keys = sorted(self.days)
        if keys:
            try:
                latest = datetime.fromisoformat(keys[-1]).date()
                cutoff = latest - timedelta(days=max(0, int(days) - 1))
                keys = [k for k in keys if datetime.fromisoformat(k).date() >= cutoff]
            except ValueError:
                keys = keys[-int(days):]
        rows = [self.days[k] for k in keys]
        def sumk(k): return sum(float(r.get(k, 0) or 0) for r in rows)
        count = int(sumk("count")); bcount = int(sumk("base_count")); ncount = int(sumk("net_count"))
        exec_total = int(sumk("exec_total")); exec_match = int(sumk("exec_matches"))
        pv_mae = sumk("pv_abs") / count if count else None
        base_mae = sumk("base_abs") / bcount if bcount else None
        net_mae = sumk("net_abs") / ncount if ncount else None
        # Explainable quality score: it is deliberately conservative and not a statistical probability.
        penalties = []
        if pv_mae is not None: penalties.append(min(1.0, pv_mae / 1800.0))
        if base_mae is not None: penalties.append(min(1.0, base_mae / 900.0))
        if net_mae is not None: penalties.append(min(1.0, net_mae / 1800.0))
        if exec_total: penalties.append(1.0 - exec_match / exec_total)
        score = None if not penalties else max(0.0, 100.0 * (1.0 - sum(penalties) / len(penalties)))
        return {
            "days": len(rows), "samples": count,
            "pv_mae_w": None if pv_mae is None else round(pv_mae, 1),
            "pv_bias_w": None if not count else round(sumk("pv_bias") / count, 1),
            "base_mae_w": None if base_mae is None else round(base_mae, 1),
            "base_bias_w": None if not bcount else round(sumk("base_bias") / bcount, 1),
            "net_mae_w": None if net_mae is None else round(net_mae, 1),
            "net_bias_w": None if not ncount else round(sumk("net_bias") / ncount, 1),
            "execution_match_pct": None if not exec_total else round(100.0 * exec_match / exec_total, 1),
            "quality_score": None if score is None else round(score, 1),
        }

    def overview(self):
        seven = self._aggregate(7); thirty = self._aggregate(30)
        findings = []
        if seven["samples"] < 12:
            findings.append("Nog te weinig planreplay-data voor een betrouwbare kwaliteitsbeoordeling.")
        else:
            if seven["pv_mae_w"] is not None and seven["pv_mae_w"] > 700:
                findings.append("De PV-voorspelling wijkt recent vaak af; laat lokale schaduwcorrectie verder leren of verhoog tijdelijk de PV-reserve.")
            if seven["base_mae_w"] is not None and seven["base_mae_w"] > 400:
                findings.append("De basislastvoorspelling is nog onnauwkeurig; meer verschillende leerdagen kunnen helpen.")
            if seven["execution_match_pct"] is not None and seven["execution_match_pct"] < 80:
                findings.append("Het geplande apparaatgedrag wordt vaak door realtime voorwaarden overruled; controleer deadlines, vraagvoorwaarden en toestelbeschikbaarheid.")
            if not findings:
                findings.append("De recente plannerfouten zijn binnen de ingestelde waarschuwingsbanden.")
        return {"last_7d": seven, "last_30d": thirty, "findings": findings}


class ReplayBuffer:
    """Bounded 15-minute observations used for planner what-if comparisons."""
    def __init__(self, retention_days=14):
        self.retention_days = int(retention_days)
        self.samples = {}

    def snapshot(self):
        return {"retention_days": self.retention_days, "samples": self.samples}

    def restore(self, data):
        if not isinstance(data, dict):
            return
        self.retention_days = max(3, int(data.get("retention_days", self.retention_days) or self.retention_days))
        raw = data.get("samples", {})
        self.samples = raw if isinstance(raw, dict) else {}

    def observe(self, *, local_now, pv_w, base_w, grid_w, import_price, export_price, capacity_target_w=None):
        pv, base, grid = finite(pv_w), finite(base_w), finite(grid_w)
        if pv is None or base is None or grid is None:
            return False
        minute = (local_now.minute // 15) * 15
        stamp = local_now.replace(minute=minute, second=0, microsecond=0)
        key = stamp.isoformat()
        self.samples[key] = {
            "pv_w": round(max(0.0, pv), 1), "base_w": round(max(0.0, base), 1), "grid_w": round(grid, 1),
            "import_price": round(float(finite(import_price) or .30), 5),
            "export_price": round(float(finite(export_price) or .03), 5),
            "capacity_target_w": None if finite(capacity_target_w) is None else round(float(capacity_target_w), 1),
        }
        cutoff = local_now - timedelta(days=self.retention_days)
        for k in list(self.samples):
            try:
                dt = datetime.fromisoformat(k)
                if dt.tzinfo is None and local_now.tzinfo is not None:
                    dt = dt.replace(tzinfo=local_now.tzinfo)
                if dt < cutoff:
                    del self.samples[k]
            except ValueError:
                del self.samples[k]
        return True

    def rows(self):
        out=[]
        for k,v in self.samples.items():
            try: dt=datetime.fromisoformat(k)
            except ValueError: continue
            out.append((dt, v))
        out.sort(key=lambda x:x[0])
        return out

    def overview(self):
        rows=self.rows()
        days=len({dt.date() for dt,_ in rows})
        return {"samples":len(rows),"days":days,"retention_days":self.retention_days,
                "from":rows[0][0].isoformat() if rows else None,"to":rows[-1][0].isoformat() if rows else None}
