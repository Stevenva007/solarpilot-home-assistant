"""Daily variable electricity cost: import cost minus export revenue, once.

Own PV is already absent from net import. Its avoided purchase cost is shown
separately and MUST NOT be subtracted from the net cost a second time. This is
meter-based estimation, not an invoice or a production-LCOE calculation.
"""
from __future__ import annotations
from datetime import datetime
import math


def finite(value):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (ValueError, TypeError, OverflowError):
        return None


def positive_linear_area(a, b, seconds):
    """Integrate positive part of a line, without netting import against export."""
    if a >= 0 and b >= 0:
        return (a + b) * .5 * seconds
    if a <= 0 and b <= 0:
        return 0.0
    if a > 0:
        return .5 * a * seconds * a / (a-b)
    return .5 * b * seconds * b / (b-a)


class DailyElectricityCost:
    numeric = ("import_kwh", "export_kwh", "pv_kwh", "direct_pv_kwh", "import_cost_eur",
               "export_revenue_eur", "pv_avoided_cost_eur", "coverage_s", "pv_coverage_s", "priced_s")

    def __init__(self):
        self.data = self._new("")
        self.previous = None  # Never bridge an offline/restart period with invented readings.
        self.imported = False
        self.cached = {}

    @classmethod
    def _new(cls, day):
        return {"date": day, **{k: 0.0 for k in cls.numeric}, "storage_seen": False,
                "legacy_price_estimate": False, "first_sample": None, "last_sample": None}

    def snapshot(self):
        return {"version": 1, "data": dict(self.data)}

    def restore(self, payload):
        d = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(d, dict) or not isinstance(d.get("date"), str):
            return
        self.data = self._new(d["date"])
        for k in self.numeric:
            v = finite(d.get(k))
            if v is not None:
                self.data[k] = v if k.endswith("_eur") else max(0.0, v)
        for k in ("storage_seen", "legacy_price_estimate"):
            self.data[k] = d.get(k) is True
        for k in ("first_sample", "last_sample"):
            self.data[k] = finite(d.get(k))
        self.previous = None
        self.imported = True

    def seed_legacy(self, stats, now, import_price, export_price, storage_present=False):
        """Carry forward existing daily totals; old price history is not available."""
        if self.imported:
            return
        self.imported = True
        self.data = self._new(now.date().isoformat())
        if not isinstance(stats, dict) or stats.get("date") != self.data["date"]:
            return
        for old, new in (("site_import_kwh", "import_kwh"), ("site_export_kwh", "export_kwh"),
                         ("pv_kwh", "pv_kwh"), ("pv_self_used_kwh", "direct_pv_kwh"),
                         ("samples_s", "coverage_s")):
            self.data[new] = max(0.0, finite(stats.get(old)) or 0.0)
        self.data["storage_seen"] = bool(storage_present)
        imp, exp = finite(import_price), finite(export_price)
        if imp is not None and exp is not None:
            self.data["import_cost_eur"] = self.data["import_kwh"] * imp
            self.data["export_revenue_eur"] = self.data["export_kwh"] * exp
            self.data["pv_avoided_cost_eur"] = self.data["direct_pv_kwh"] * imp
            self.data["priced_s"] = self.data["coverage_s"]
            self.data["legacy_price_estimate"] = self.data["coverage_s"] > 0
        # Historical PV availability cannot be recovered from these old counters.
        if self.data["pv_kwh"] > 0:
            self.data["pv_coverage_s"] = self.data["coverage_s"]
        if self.data["coverage_s"]:
            self.data["first_sample"] = max(now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp(), now.timestamp()-self.data["coverage_s"])
            self.data["last_sample"] = now.timestamp()

    def update(self, *, now: datetime, grid_w, pv_w, import_price, export_price,
               storage_present=False, max_gap_s=120):
        stamp = now.timestamp()
        day = now.date().isoformat()
        old = self.previous
        sample = {"stamp": stamp, "grid": finite(grid_w), "pv": finite(pv_w),
                  "import_price": finite(import_price), "export_price": finite(export_price),
                  "storage": bool(storage_present)}
        if sample["pv"] is not None and sample["pv"] < 0:
            sample["pv"] = None
        self.previous = sample
        dt = stamp-old["stamp"] if old else 0.0
        valid = old is not None and 0 < dt <= max_gap_s and sample["grid"] is not None and old["grid"] is not None
        if self.data["date"] != day:
            # Discard the previous day's accumulated cost. Only today's part of a
            # valid midnight-straddling interval is counted in today's total.
            self.data = self._new(day)
        midnight = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
        if valid:
            begin = max(old["stamp"], midnight)
            seconds = stamp-begin
            fraction = (begin-old["stamp"]) / dt
            ga = old["grid"] + (sample["grid"]-old["grid"]) * fraction
            gb = sample["grid"]
            factor = 1/3_600_000.0
            imp = positive_linear_area(ga, gb, seconds)*factor
            exp = positive_linear_area(-ga, -gb, seconds)*factor
            d = self.data
            d["import_kwh"] += imp
            d["export_kwh"] += exp
            d["coverage_s"] += seconds
            d["storage_seen"] = d["storage_seen"] or old["storage"] or sample["storage"]
            if d["first_sample"] is None:
                d["first_sample"] = begin
            d["last_sample"] = stamp
            # Price in force during the preceding interval: changing a tariff
            # must not retroactively reprice energy already counted today.
            ip, ep = old["import_price"], old["export_price"]
            if ip is not None and ep is not None:
                d["import_cost_eur"] += imp*ip
                d["export_revenue_eur"] += exp*ep
                d["priced_s"] += seconds
            if old["pv"] is not None and sample["pv"] is not None:
                pa = old["pv"]+(sample["pv"]-old["pv"])*fraction
                pb = sample["pv"]
                d["pv_kwh"] += (pa+pb)*.5*seconds*factor
                d["pv_coverage_s"] += seconds
                if not old["storage"] and not sample["storage"]:
                    # Direct PV at each endpoint, bounded by production. Crossing
                    # grid zero is split so export and self-use are not netted.
                    points = [(0.0, ga, pa), (1.0, gb, pb)]
                    if ga*gb < 0:
                        t = ga/(ga-gb)
                        points.insert(1, (t, 0.0, pa+(pb-pa)*t))
                    direct = 0.0
                    for (ta, g1, p1), (tb, g2, p2) in zip(points, points[1:]):
                        s1 = max(0.0, p1-max(0.0, -g1))
                        s2 = max(0.0, p2-max(0.0, -g2))
                        direct += (s1+s2)*.5*(tb-ta)*seconds*factor
                    d["direct_pv_kwh"] += direct
                    if ip is not None:
                        d["pv_avoided_cost_eur"] += direct*ip
        self.cached = self.overview(now)
        return self.cached

    def overview(self, now):
        d = self.data
        elapsed = max(0.0, now.timestamp()-now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp())
        coverage = min(elapsed, d["coverage_s"])
        enough = d["coverage_s"] > 0
        priced = enough and d["priced_s"] >= d["coverage_s"]-.01
        direct_known = d["pv_coverage_s"] > 0 and not d["storage_seen"]
        partial = elapsed > coverage+120
        result = {"date": d["date"], "reset_timestamp": now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp(), "basis": "gemeten tot nu toe", "partial": partial,
                  "coverage_s": round(coverage, 1), "coverage_pct": round(100*coverage/elapsed, 1) if elapsed else 0.0,
                  "first_sample": d["first_sample"], "last_sample": d["last_sample"],
                  "import_kwh": round(d["import_kwh"], 6) if enough else None,
                  "export_kwh": round(d["export_kwh"], 6) if enough else None,
                  "pv_kwh": round(d["pv_kwh"], 6) if d["pv_coverage_s"] else None,
                  "direct_pv_kwh": round(d["direct_pv_kwh"], 6) if direct_known else None,
                  "import_cost_eur": round(d["import_cost_eur"], 6) if priced else None,
                  "export_revenue_eur": round(d["export_revenue_eur"], 6) if priced else None,
                  "net_cost_eur": round(d["import_cost_eur"]-d["export_revenue_eur"], 6) if priced else None,
                  "pv_avoided_cost_eur": round(d["pv_avoided_cost_eur"], 6) if priced and direct_known else None,
                  "legacy_price_estimate": d["legacy_price_estimate"], "storage_present": d["storage_seen"],
                  "pv_partial": d["pv_coverage_s"] < d["coverage_s"]-.01,
                  "note": "Netafnamekost min injectievergoeding; eigen zon niet nogmaals aftrekken. Exclusief vaste kosten en capaciteitstarief."}
        result["coverage_note"] = ("Nog geen bruikbare meetperiode" if not enough else
                                   f"Meetdekking {result['coverage_pct']:.1f}% van vandaag; ontbrekende perioden niet geschat" if partial else
                                   "Vandaag tot nu toe; geschat uit vermogensmetingen")
        if d["storage_seen"]:
            result["solar_note"] = "Met thuisbatterij is rechtstreeks zonneverbruik niet apart bewezen; netkost blijft op P1 gebaseerd."
        elif result["pv_partial"]:
            result["solar_note"] = "Rechtstreekse zon alleen over perioden met bruikbare PV-metingen."
        else:
            result["solar_note"] = "Vermeden netaankoop dankzij direct zonneverbruik; informatief, al verrekend in lagere netafname."
        return result
