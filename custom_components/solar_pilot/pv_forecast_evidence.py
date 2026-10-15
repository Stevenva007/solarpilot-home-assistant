"""Bounded read-only forecasts recorded before their comparison target.

Local capture proves that a value was available ahead of a target. It cannot
prove the original upstream issue time, or turn concurrent/revised forecasts
into out-of-sample planning accuracy. Nothing here changes a planner or factor.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from datetime import datetime, timezone
from math import ceil

from .pv_forecast_source import finite, stamp

MAX_SNAPSHOTS = 96
MAX_TARGETS = 48
MAX_COMPARISONS = 2880
# Additive versioned research storage; the old single-forecast series remains
# readable and keeps its original meaning. Three horizons may share one actual.
MAX_COHORT_PENDING = MAX_SNAPSHOTS * MAX_TARGETS
MAX_COHORT_COMPARISONS = MAX_COMPARISONS * 3
COHORT_VERSION = 1
COHORT_SELECTION_RULE = "first_observed_in_band_v1"
LEAD_BANDS = (("5m_1h", "5–60 min", 300, 3600),
              ("1h_3h", "1–3 uur", 3600, 10800),
              ("3h_12h", "3–12 uur", 10800, 43201))
CONDITION_LABELS = {"daylight": "Daglicht: zon boven horizon", "night": "Nacht: zon onder horizon",
                    "other_zero": "Nulpunten zonder oorspronkelijk zonbewijs", "unknown": "Overig / onbekend"}


def iso(ts):
    return datetime.fromtimestamp(ts, timezone.utc).isoformat()


def solar_proof(elevation, reported, observed, meter_reported):
    """Keep only original near-target sun reports, never infer night from watts."""
    height, source_time = finite(elevation), finite(reported)
    valid = (height is not None and -90 <= height <= 90 and source_time is not None
             and 0 < source_time <= 32503680000 and -5 <= observed-source_time <= 120
             and abs(meter_reported-source_time) <= 120)
    return {"elevation_deg": height if valid else None,
            "reported_at": iso(source_time) if valid else None,
            "origin": "original_sun_report" if valid else "unknown"}


def condition(row):
    proof = row.get("solar_context")
    elevation = finite(proof.get("elevation_deg")) if isinstance(proof, dict) else None
    if isinstance(proof, dict) and proof.get("origin") == "original_sun_report" and elevation is not None:
        if elevation > 0:
            return "daylight"
        if elevation < 0:
            return "night"
    if row["raw_w"] == row["corrected_w"] == row["actual_w"] == 0:
        return "other_zero"
    return "unknown"


def comparison_metrics(rows):
    errors = [row["corrected_error_w"] for row in rows]
    return {"samples": len(rows), "unique_targets": len({(row["binding"], row["target_at"]) for row in rows}),
            "mae_w": sum(abs(error) for error in errors)/len(errors) if errors else None,
            "bias_w": sum(errors)/len(errors) if errors else None,
            "clipped": sum(row["clipped"] for row in rows),
            "distinct_days": len({row["actual_reported_at"][:10] for row in rows})}


def lead_band(ahead):
    if not 300 <= ahead <= 43200:
        return None
    return next((name for name, _, lower, upper in LEAD_BANDS if lower <= ahead < upper), None)


def cohort_key(row):
    return row["target_at"], row["binding"], row["lead_band"]


def cohort_metrics(rows):
    daylight = [row for row in rows if condition(row) == "daylight"]
    return {**comparison_metrics(rows),
            "unique_original_reports": len({(row["binding"], row["actual_reported_at"]) for row in rows}),
            "daylight_targets": len({(row["binding"], row["target_at"]) for row in daylight}),
            "daylight_days": len({row["actual_reported_at"][:10] for row in daylight}),
            "source_bindings": len({row["binding"] for row in rows})}


def comparison_row(snapshot, target, observed, actual, reported, binding, limit, sun):
    """All horizons of a target receive this same original measurement."""
    target_ts = stamp(target["target_at"])
    proof = snapshot["source_context"]
    return {"actual_reported_at": iso(reported), "observed_at": iso(observed),
            "target_at": target["target_at"], "time_offset_s": reported-target_ts,
            "actual_w": actual, "raw_w": target["raw_w"], "corrected_w": target["corrected_w"],
            "raw_error_w": actual-target["raw_w"], "corrected_error_w": actual-target["corrected_w"],
            "factor": target["factor"], "calibration": deepcopy(target["calibration"]),
            "captured_at": snapshot["captured_at"], "issued_at": None, "issue_time_status": "unknown",
            "source_reported_at": proof["source_reported_at"], "local_data_observed_at": proof["local_data_observed_at"],
            "source_metadata": deepcopy(proof["source_metadata"]),
            "original_issue_horizon_s": None, "recorded_ahead_s": target["recorded_ahead_s"],
            "solar_context": deepcopy(sun),
            "source_context_id": proof["source_context_id"], "binding": binding,
            "clipped": target["corrected_w"] + 1e-9 < target["raw_w"] * target["factor"],
            "actual_clipped": actual >= limit*.98}


def context(value):
    """Only bounded typed provenance fields may enter durable evidence."""
    if not isinstance(value, dict):
        return None
    ident = value.get("source_context_id")
    if not isinstance(ident, str) or len(ident) != 64 or any(c not in "0123456789abcdef" for c in ident):
        return None
    result = {"source_context_id": ident, "provider": "forecast_solar",
              "issued_at": None, "issue_time_status": "unknown",
              "original_issue_horizon_s": None,
              "issue_time_reason": "Oorspronkelijke forecastuitgiftetijd niet door de bronadapter geleverd"}
    for name in ("source_reported_at", "local_data_observed_at"):
        number = stamp(value.get(name))
        result[name] = iso(number) if number is not None and 0 <= number <= 32503680000 else None
    result["value_origin"] = value.get("value_origin") if value.get("value_origin") in ("curve", "scalar") else "unknown"
    metadata=value.get("source_metadata")
    result["source_metadata"]={"inverter_size":None,"damping_morning":None,"damping_evening":None,"planes":[]}
    if isinstance(metadata,dict):
        for key in ("inverter_size","damping_morning","damping_evening"):
            number=finite(metadata.get(key))
            result["source_metadata"][key]=number if number is not None and 0<=number<=1000000 else None
        planes=metadata.get("planes")
        result["source_metadata"]["planes"]=[]
        for plane in planes[:8] if isinstance(planes,list) else []:
            if not isinstance(plane,dict):continue
            clean={}
            for key,lower,upper in (("modules_power",0,1000000),("declination",-90,90),("azimuth",-360,360)):
                number=finite(plane.get(key));clean[key]=number if number is not None and lower<=number<=upper else None
            result["source_metadata"]["planes"].append(clean)
    # This adapter deliberately has no original-issue-time contract. In
    # particular a storage edit cannot promote a local timestamp to issue proof.
    return result


def profile(value):
    if not isinstance(value, dict):
        return {}
    result = {name: value.get(name) is True for name in ("eligible", "applied", "fallback_used")}
    for name in ("days", "validated_days", "minimum_days_required"):
        number = finite(value.get(name))
        result[name] = int(number) if number is not None and 0 <= number <= 3650 and number.is_integer() else 0
    confidence = finite(value.get("confidence"))
    result["confidence"] = confidence if confidence is not None and 0 <= confidence <= 1 else 0.
    result["reason"] = str(value.get("reason", ""))[:240]
    result["profile_kind"] = value.get("profile_kind") if value.get("profile_kind") in ("global", "sun", "clock", "none") else "none"
    return result


def restored_comparison(row, cutoff):
    if not isinstance(row, dict):
        return None
    reported, observed, captured, target = (stamp(row.get(k)) for k in ("actual_reported_at", "observed_at", "captured_at", "target_at"))
    actual, raw, corrected, factor = (finite(row.get(k)) for k in ("actual_w", "raw_w", "corrected_w", "factor"))
    proof = context(row); binding = row.get("binding")
    if (None in (reported, observed, captured, target, actual, raw, corrected, factor) or proof is None
            or not isinstance(binding, str) or len(binding) != 64 or any(c not in "0123456789abcdef" for c in binding)
            or not 0 <= captured < reported <= cutoff or not 0<=observed<=cutoff or not -5 <= observed-reported <= 120
            or not 300 <= target-captured <= 43200 or abs(reported-target) > 60
            or any(not 0 <= v <= 1000000 for v in (actual, raw, corrected)) or not .15 <= factor <= 1.6): return None
    if any(stamp(proof[key]) is not None and stamp(proof[key]) > captured+5
           for key in ("source_reported_at", "local_data_observed_at")):
        return None
    return {"actual_reported_at": iso(reported), "observed_at": iso(observed),
        "target_at": iso(target), "time_offset_s": reported-target, "actual_w": actual,
        "raw_w": raw, "corrected_w": corrected, "raw_error_w": actual-raw,
        "corrected_error_w": actual-corrected, "factor": factor,
        "calibration": profile(row.get("calibration")), "captured_at": iso(captured),
        "source_reported_at":proof["source_reported_at"],"local_data_observed_at":proof["local_data_observed_at"],
        "source_metadata":deepcopy(proof["source_metadata"]),
        **({"solar_context":solar_proof(
            row["solar_context"].get("elevation_deg") if row["solar_context"].get("origin")=="original_sun_report" else None,
            stamp(row["solar_context"].get("reported_at")) if row["solar_context"].get("origin")=="original_sun_report" else None,
            observed,reported)} if isinstance(row.get("solar_context"),dict) else {}),
        "issued_at": None, "issue_time_status": "unknown", "original_issue_horizon_s": None,
        "recorded_ahead_s": target-captured, "source_context_id": proof["source_context_id"], "binding": binding,
        "clipped": corrected + 1e-9 < raw*factor, "actual_clipped": row.get("actual_clipped") is not False}


class ForecastEvidence:
    VERSION = 1

    def __init__(self):
        self.snapshots = deque(maxlen=MAX_SNAPSHOTS)
        self.comparisons = deque(maxlen=MAX_COMPARISONS)
        self.last_capture = None
        self.last_context = None
        self.last_report = None
        self.revision = 0
        self._unsupported = None
        self.cohort_pending = deque(maxlen=MAX_COHORT_PENDING)
        self.cohort_comparisons = deque(maxlen=MAX_COHORT_COMPARISONS)
        self._unsupported_cohorts = None
        self.cohort_capacity_reached = False
        self.cohort_errors = {}

    def _capture_cohorts(self, snapshot, ts):
        if self._unsupported_cohorts is not None:
            return
        # Selection is made while the forecast is captured, before any outcome.
        # A report may arrive 120s late and be 60s after its target. Keep
        # 180s of grace even though capture runs before compare in an update.
        # Expired unmatched forecasts are not converted into historical proof.
        self.cohort_pending = deque((row for row in self.cohort_pending
                                    if stamp(row["target_at"]) >= ts-180), maxlen=MAX_COHORT_PENDING)
        if self.cohort_capacity_reached:
            return
        selected = {cohort_key(row) for row in self.cohort_pending}
        selected.update(cohort_key(row) for row in self.cohort_comparisons)
        for target in snapshot["predictions"]:
            band = lead_band(target["recorded_ahead_s"])
            key = (target["target_at"], snapshot["binding"], band)
            if band is None or key in selected:
                continue
            if len(self.cohort_pending) >= MAX_COHORT_PENDING:
                # Never evict an earlier unobserved selection and silently pick
                # its revised replacement. Preserve collected evidence and make
                # exceptional storage saturation explicit instead.
                self.cohort_capacity_reached = True
                break
            self.cohort_pending.append({**deepcopy(target),
                "captured_at": snapshot["captured_at"], "source_context": deepcopy(snapshot["source_context"]),
                "binding": snapshot["binding"], "lead_band": band, "selection_rule": COHORT_SELECTION_RULE})
            selected.add(key)

    def _compare_cohorts(self, ts, actual, reported, source_context_id, binding, limit, sun):
        if self._unsupported_cohorts is not None:
            return
        completed = {(row["target_at"], row["binding"]) for row in self.cohort_comparisons}
        candidates = [row for row in self.cohort_pending
            if row["binding"] == binding and row["source_context"]["source_context_id"] == source_context_id
            and stamp(row["captured_at"]) < reported and abs(stamp(row["target_at"])-reported) <= 60
            and (row["target_at"], binding) not in completed]
        if not candidates:
            return
        # A scalar source can have nearby relative targets. Select just one
        # target by a fixed temporal rule, never by the observed forecast error.
        target_at = min(candidates, key=lambda row: (abs(stamp(row["target_at"])-reported), row["target_at"]))["target_at"]
        for row in candidates:
            if row["target_at"] != target_at:
                continue
            compared = comparison_row(row, row, ts, actual, reported, binding, limit, sun)
            self.cohort_comparisons.append({**compared, "lead_band": row["lead_band"],
                                           "selection_rule": COHORT_SELECTION_RULE})
        # Close the whole target after its one original actual; later reports
        # cannot fill missing horizons or replace the original measurement.
        self.cohort_pending = deque((row for row in self.cohort_pending
            if (row["target_at"], row["binding"]) != (target_at, binding)), maxlen=MAX_COHORT_PENDING)
        self.revision += 1

    def capture(self, now, source, corrected, factor_details, binding):
        """Capture immutable future targets at most once per quarter/context."""
        ts = now.timestamp()
        proof = context(source.evidence(ts, ts))
        if (self._unsupported is not None or not source.valid or proof is None
                or not isinstance(binding, str) or len(binding) != 64 or any(c not in "0123456789abcdef" for c in binding)
                or any(stamp(proof[key]) is not None and stamp(proof[key]) > ts+5
                       for key in ("source_reported_at", "local_data_observed_at"))):
            return
        ident = (proof["source_context_id"], binding)
        if self.last_capture is not None and ident == self.last_context and 0 <= ts - self.last_capture < 900:
            return
        targets = []
        start = (int(ts // 900) + 1) * 900
        for index in range(MAX_TARGETS):
            target = start + index * 900
            raw = finite(source.raw_at(target, ts))
            if raw is None or not 0 <= raw <= 1000000:
                continue
            detail = factor_details(datetime.fromtimestamp(target, now.tzinfo))
            value = finite(corrected(target, raw, now.tzinfo))
            factor = finite(detail.get("factor"))
            if value is None or not 0 <= value <= 1000000 or factor is None or not .15 <= factor <= 1.6:
                continue
            targets.append({"target_at": iso(target), "raw_w": raw, "corrected_w": value,
                            "factor": factor, "calibration": profile(detail),
                            "recorded_ahead_s": target - ts, "original_issue_horizon_s": None})
        # Scalar +1h forecasts have a relative exact target rather than a full
        # curve. Keep that evidence without interpolating a missing horizon.
        if not targets:
            target = ts + 3600
            raw = finite(source.raw_at(target, ts))
            if raw is not None and 0 <= raw <= 1000000:
                detail = factor_details(datetime.fromtimestamp(target, now.tzinfo))
                value = finite(corrected(target, raw, now.tzinfo))
                factor = finite(detail.get("factor"))
                if value is not None and 0 <= value <= 1000000 and factor is not None and .15 <= factor <= 1.6:
                    targets.append({"target_at": iso(target), "raw_w": raw, "corrected_w": value,
                                    "factor": factor, "calibration": profile(detail),
                                    "recorded_ahead_s": 3600., "original_issue_horizon_s": None})
        if not targets:
            return
        snapshot = {"captured_at": iso(ts), "source_context": proof, "binding": binding, "predictions": targets}
        self.snapshots.append(snapshot)
        try:
            self._capture_cohorts(snapshot, ts)
            self.cohort_errors.pop("capture", None)
        except Exception as err:
            # Optional additional research cannot interrupt the original series.
            self.cohort_errors["capture"] = type(err).__name__
        self.last_capture = ts; self.last_context = ident; self.revision += 1

    def compare(self, now, actual_w, meter_stamp, source_context_id, binding, inverter_limit_w,
                *, solar_elevation=None, solar_reported_at=None):
        ts = now.timestamp(); actual = finite(actual_w); reported = finite(meter_stamp)
        limit = finite(inverter_limit_w)
        if (self._unsupported is not None or limit is None or not 0 < limit <= 1000000
                or actual is None or not 0 <= actual <= limit*1.1 or reported is None
                or not -5 <= ts - reported <= 120 or self.last_report is not None and reported <= self.last_report):
            return
        self.last_report = reported
        sun = solar_proof(solar_elevation, solar_reported_at, ts, reported)
        try:
            self._compare_cohorts(ts, actual, reported, source_context_id, binding, limit, sun)
            self.cohort_errors.pop("compare", None)
        except Exception as err:
            self.cohort_errors["compare"] = type(err).__name__
        candidates = []
        for snapshot in self.snapshots:
            proof = snapshot["source_context"]
            captured = stamp(snapshot["captured_at"])
            if proof["source_context_id"] != source_context_id or snapshot["binding"] != binding or captured is None or captured >= reported:
                continue
            for target in snapshot["predictions"]:
                target_ts = stamp(target["target_at"])
                # A bounded near-target comparison keeps the actual skew visible.
                # Never substitute a newer forecast after the target was observed.
                if (target_ts is not None and abs(reported - target_ts) <= 60 and target_ts - captured >= 300
                        and not any(r["binding"] == binding and r["target_at"] == target["target_at"] for r in self.comparisons)):
                    candidates.append((captured, abs(reported-target_ts), snapshot, target))
        if not candidates:
            return
        # Earliest retained forecast wins; later revisions do not retrospectively
        # improve the evidence. One unique original meter report gives one row;
        # adjacent targets are not statistically independent trials.
        _, _, snapshot, target = min(candidates, key=lambda item: (item[0], item[1]))
        self.comparisons.append(comparison_row(snapshot, target, ts, actual, reported, binding, limit, sun))
        self.revision += 1

    def summary(self):
        rows = list(self.comparisons)
        buckets = []
        for label, lower, upper in (("5–60 min", 300, 3600), ("1–3 uur", 3600, 10800), ("3–12 uur", 10800, 43201)):
            selected = [r for r in rows if lower <= r["recorded_ahead_s"] < upper]
            buckets.append({"label": label, **comparison_metrics(selected),
                "conditions": [{"condition": name, "label": description,
                                **comparison_metrics([row for row in selected if condition(row) == name])}
                               for name, description in CONDITION_LABELS.items()]})
        # A margin can only be examined on a single source/binding and a
        # chronological train/holdout split; no tuned-in-sample benefit claim.
        margin = {"status": "insufficient", "margin_w": None, "baseline_mae_w": None,
                  "hypothetical_mae_w": None, "applied": False,
                  "reason": "Nog onvoldoende oorspronkelijke vooruit vastgelegde vergelijkingen op verschillende dagen"}
        margin_rows = [r for r in rows if not r["actual_clipped"] and not r["clipped"] and r["raw_w"] >= 400]
        groups = {(r["source_context_id"], r["binding"]) for r in margin_rows}
        days = sorted({r["actual_reported_at"][:10] for r in margin_rows})
        if len(margin_rows) >= 24 and len(days) >= 4 and len(groups) == 1:
            train = [r for r in margin_rows if r["actual_reported_at"][:10] in days[:-1]]
            held = [r for r in margin_rows if r["actual_reported_at"][:10] == days[-1]]
            if len(train) >= 12 and len(held) >= 6:
                over = sorted(max(0., -r["corrected_error_w"]) for r in train)
                candidate = over[max(0, ceil(.9*len(over))-1)]
                margin.update(status="comparison_only", margin_w=candidate,
                    baseline_mae_w=sum(abs(r["corrected_error_w"]) for r in held)/len(held),
                    hypothetical_mae_w=sum(abs(r["actual_w"]-max(0.,r["corrected_w"]-candidate)) for r in held)/len(held),
                    training_samples=len(train), holdout_samples=len(held), holdout_day=days[-1],
                    reason="P90 van overschatting op eerdere dagen, alleen vergeleken op laatste dag; geen plannerwijziging of bewezen besparing")
        return {"ahead_comparisons": len(rows), "distinct_days": len({r["actual_reported_at"][:10] for r in rows}),
                "unique_targets":len({(row["binding"],row["target_at"]) for row in rows}),
                "day_basis":"UTC_original_meter_report", "condition_labels":dict(CONDITION_LABELS),
                "known_original_issue_times": 0, "by_recorded_lead": buckets,
                "planning_margin_comparison": margin,
                "comparison_kind": "locally_recorded_ahead_near_target",
                "current_error_is_ahead_accuracy": False,
                "lead_cohort_evidence": self.cohort_summary()}

    def cohort_summary(self):
        rows = list(self.cohort_comparisons)
        metrics = cohort_metrics(rows)
        return {"version": COHORT_VERSION, "selection_rule": COHORT_SELECTION_RULE,
                "identity": ["target_at", "binding", "lead_band"],
                "selection_reason": "Eerste lokaal vastgelegde geldige voorspelling binnen elke vaste band; nadien onveranderlijk",
                "historical_backfill": False, "pending_selections": len(self.cohort_pending),
                "status": "unsupported_storage" if self._unsupported_cohorts is not None or self._unsupported is not None else
                          "research_error" if self.cohort_errors else
                          "capacity_reached" if self.cohort_capacity_reached else "collecting",
                "research_errors": dict(self.cohort_errors),
                "collection_capacity_reached": self.cohort_capacity_reached,
                "retention_bounds": {"pending": MAX_COHORT_PENDING, "comparisons": MAX_COHORT_COMPARISONS},
                **metrics,
                "day_basis": "UTC_original_meter_report", "known_original_issue_times": 0,
                "oldest_retained_capture_at": min((row["captured_at"] for row in [*self.cohort_pending, *rows]), default=None),
                "by_recorded_lead": [{"lead_band": name, "label": label, "lower_s": lower,
                    "upper_s": min(upper, 43200), "upper_inclusive": upper == 43201,
                    **cohort_metrics([row for row in rows if row["lead_band"] == name]),
                    "pending_selections": sum(row["lead_band"] == name for row in self.cohort_pending),
                    "conditions": [{"condition": kind, "label": description,
                        **cohort_metrics([row for row in rows if row["lead_band"] == name and condition(row) == kind])}
                        for kind, description in CONDITION_LABELS.items()]}
                    for name, label, lower, upper in LEAD_BANDS],
                "shared_measurement_rows": len(rows)-metrics["unique_original_reports"],
                "statistically_independent": False,
                "dependency_reason": "Banden delen per doel dezelfde oorspronkelijke meterwaarneming; naburige kwartieren en dagen zijn onderling afhankelijk. Rijenaantal is geen aantal onafhankelijke proeven",
                "applied": False}

    def snapshot(self):
        if self._unsupported is not None:
            return deepcopy(self._unsupported)
        return {"version": self.VERSION, "snapshots": deepcopy(list(self.snapshots)),
                "comparisons": deepcopy(list(self.comparisons)), "revision": self.revision,
                "lead_cohorts": deepcopy(self._unsupported_cohorts) if self._unsupported_cohorts is not None else {
                    "version": COHORT_VERSION, "selection_rule": COHORT_SELECTION_RULE,
                    "collection_capacity_reached": self.cohort_capacity_reached,
                    "pending": deepcopy(list(self.cohort_pending)),
                    "comparisons": deepcopy(list(self.cohort_comparisons))}}

    def restore(self, data, now=None):
        cutoff=(now or datetime.now(timezone.utc)).timestamp()+5
        self.snapshots.clear(); self.comparisons.clear(); self.last_capture = None
        self.last_context = None; self.last_report = None; self.revision = 0; self._unsupported = None
        self.cohort_pending.clear(); self.cohort_comparisons.clear(); self._unsupported_cohorts = None
        self.cohort_capacity_reached = False; self.cohort_errors.clear()
        if not isinstance(data, dict) or not data:
            return
        if type(data.get("version")) is not int or data["version"] != self.VERSION:
            self._unsupported = deepcopy(data)
            return
        saved = data.get("snapshots")
        for snapshot in saved[-MAX_SNAPSHOTS:] if isinstance(saved, list) else []:
            if not isinstance(snapshot, dict): continue
            captured = stamp(snapshot.get("captured_at")); proof = context(snapshot.get("source_context")); binding = snapshot.get("binding")
            if (captured is None or not 0 <= captured <= cutoff or proof is None
                    or not isinstance(binding, str) or len(binding) != 64 or any(c not in "0123456789abcdef" for c in binding)): continue
            if any(stamp(proof[key]) is not None and stamp(proof[key])>captured+5
                   for key in ("source_reported_at","local_data_observed_at")): continue
            predictions = []
            stored = snapshot.get("predictions")
            for target in stored[:MAX_TARGETS] if isinstance(stored, list) else []:
                if not isinstance(target, dict): continue
                target_ts = stamp(target.get("target_at"))
                raw, corrected, factor = (finite(target.get(k)) for k in ("raw_w", "corrected_w", "factor"))
                if (target_ts is None or not 0 < target_ts-captured <= 43200 or raw is None or corrected is None
                        or not 0 <= raw <= 1000000 or not 0 <= corrected <= 1000000 or factor is None or not .15 <= factor <= 1.6): continue
                predictions.append({"target_at": iso(target_ts), "raw_w": raw, "corrected_w": corrected,
                    "factor": factor, "calibration": profile(target.get("calibration")),
                    "recorded_ahead_s": target_ts-captured, "original_issue_horizon_s": None})
            if predictions:
                self.snapshots.append({"captured_at": iso(captured), "source_context": proof, "binding": binding, "predictions": predictions})
        self.snapshots = deque(sorted(self.snapshots, key=lambda r: stamp(r["captured_at"])), maxlen=MAX_SNAPSHOTS)
        saved = data.get("comparisons")
        seen = set(); seen_targets = set()
        for row in saved[-MAX_COMPARISONS:] if isinstance(saved, list) else []:
            if not isinstance(row, dict): continue
            clean = restored_comparison(row, cutoff)
            if clean is None: continue
            key = (clean["binding"], clean["actual_reported_at"])
            target_key = (clean["binding"], clean["target_at"])
            if key in seen or target_key in seen_targets: continue
            seen.add(key); seen_targets.add(target_key)
            self.comparisons.append(clean)
        self.comparisons = deque(sorted(self.comparisons, key=lambda r: stamp(r["actual_reported_at"])), maxlen=MAX_COMPARISONS)
        self._restore_cohorts(data.get("lead_cohorts"), cutoff)
        # Persisted forecasts cannot be replayed as active observations. Keep a
        # dedup cursor only, with no freshness or controller permission.
        reports = [stamp(rows[-1]["actual_reported_at"]) for rows in (self.comparisons, self.cohort_comparisons) if rows]
        if reports: self.last_report = max(reports)
        if self.snapshots:
            self.last_capture = stamp(self.snapshots[-1]["captured_at"])
            self.last_context = (self.snapshots[-1]["source_context"]["source_context_id"], self.snapshots[-1]["binding"])
        value = finite(data.get("revision"))
        self.revision = int(value) if value is not None and 0 <= value <= 10**12 else 0

    def _restore_cohorts(self, data, cutoff):
        # Missing additive extension is genuinely missing evidence. Never derive
        # a new cohort from the legacy snapshots or one-vote comparisons.
        if data is None:
            return
        if (not isinstance(data, dict) or type(data.get("version")) is not int
                or data["version"] != COHORT_VERSION or data.get("selection_rule") != COHORT_SELECTION_RULE):
            self._unsupported_cohorts = deepcopy(data)
            return
        self.cohort_capacity_reached = data.get("collection_capacity_reached") is True
        saved = data.get("comparisons")
        seen = set(); actuals = {}; report_targets = {}
        rows = []
        for row in saved[-MAX_COHORT_COMPARISONS:] if isinstance(saved, list) else []:
            if not isinstance(row, dict) or row.get("selection_rule") != COHORT_SELECTION_RULE:
                continue
            clean = restored_comparison(row, cutoff)
            if clean is None or row.get("lead_band") != lead_band(clean["recorded_ahead_s"]):
                continue
            clean.update(lead_band=row["lead_band"], selection_rule=COHORT_SELECTION_RULE)
            key = cohort_key(clean); target_key = key[:2]
            # Same target must keep the exact same actual and sun observation
            # across horizons. One report cannot become several nearby targets.
            measurement = (clean["actual_reported_at"], clean["observed_at"], clean["actual_w"],
                           clean.get("solar_context"), clean["source_context_id"])
            report_key = (clean["binding"], clean["actual_reported_at"])
            if (key in seen or target_key in actuals and actuals[target_key] != measurement
                    or report_key in report_targets and report_targets[report_key] != target_key):
                continue
            seen.add(key); actuals[target_key] = measurement; report_targets[report_key] = target_key
            rows.append(clean)
        self.cohort_comparisons = deque(sorted(rows, key=lambda row: row["actual_reported_at"]),
                                        maxlen=MAX_COHORT_COMPARISONS)
        saved = data.get("pending")
        choices = []
        if isinstance(saved, list) and len(saved) > MAX_COHORT_PENDING:
            self.cohort_capacity_reached = True
        for row in saved[:MAX_COHORT_PENDING] if isinstance(saved, list) else []:
            if not isinstance(row, dict) or row.get("selection_rule") != COHORT_SELECTION_RULE:
                continue
            captured, target = stamp(row.get("captured_at")), stamp(row.get("target_at"))
            raw, corrected, factor = (finite(row.get(key)) for key in ("raw_w", "corrected_w", "factor"))
            proof = context(row.get("source_context")); binding = row.get("binding")
            if (None in (captured, target, raw, corrected, factor) or proof is None
                    or not isinstance(binding, str) or len(binding) != 64 or any(c not in "0123456789abcdef" for c in binding)
                    or not 0 <= captured <= cutoff or not 300 <= target-captured <= 43200
                    or row.get("lead_band") != lead_band(target-captured)
                    or any(not 0 <= value <= 1000000 for value in (raw, corrected)) or not .15 <= factor <= 1.6
                    or any(stamp(proof[key]) is not None and stamp(proof[key]) > captured+5
                           for key in ("source_reported_at", "local_data_observed_at"))):
                continue
            choices.append({"target_at": iso(target), "raw_w": raw, "corrected_w": corrected, "factor": factor,
                "calibration": profile(row.get("calibration")), "recorded_ahead_s": target-captured,
                "original_issue_horizon_s": None, "captured_at": iso(captured), "source_context": proof,
                "binding": binding, "lead_band": row["lead_band"], "selection_rule": COHORT_SELECTION_RULE})
        selected = set(seen)
        for row in sorted(choices, key=lambda item: item["captured_at"]):
            key = cohort_key(row)
            if key in selected or key[:2] in actuals:
                continue
            selected.add(key); self.cohort_pending.append(row)

    def diagnostics(self):
        result = self.snapshot() if self._unsupported is None else {"version": self.VERSION, "snapshots": [], "comparisons": []}
        if self._unsupported_cohorts is not None:
            result["lead_cohorts"] = {"version": COHORT_VERSION, "selection_rule": COHORT_SELECTION_RULE,
                                      "pending": [], "comparisons": []}
        result["summary"] = self.summary()
        result["cohort_storage_warning"] = "Onbekende cohortopslag privé behouden; geen nieuw cohortbewijs" if self._unsupported_cohorts is not None else ""
        result["storage_warning"] = "Onbekende forecast-evidenceversie privé behouden; geen actueel bewijs" if self._unsupported is not None else ""
        result["limitations"] = ["Oorspronkelijke upstream forecastuitgiftetijd blijft onbekend",
            "Lokale vastlegging vóór doel is apart van oorspronkelijke uitgifte en concurrente foutmeting",
            "Vergelijkingen gebruiken oorspronkelijke meterberichten binnen 60 s van een vastgelegd doel; tijdverschil blijft zichtbaar",
            "Dag/nacht vereist een nabij oorspronkelijk zonhoogterapport; nulvermogen alleen bewijst geen nacht. Oudere vergelijkingen krijgen geen achteraf berekende zonhoogte",
            "Nieuwe leadcohorten kiezen vóór het doel de eerste voorspelling binnen iedere vaste band; ontbrekende oude cohorten worden niet aangevuld",
            "Dezelfde oorspronkelijke meting wordt tussen banden gedeeld en is geen extra onafhankelijke proef",
            "Unieke doelen en oorspronkelijke meterberichten zijn geen statistisch onafhankelijke proeven; dagenaantallen gebruiken UTC-brondagen",
            "Onzekerheidsmarge is alleen een uitleesbare chronologische vergelijking; planner en elektrische grenzen blijven ongewijzigd"]
        return result
