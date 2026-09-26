"""Bounded learning for non-interruptible appliance cycles.

SolarPilot stores compact per-program summaries, not raw high-frequency traces.
A learned cycle profile is advisory to the rolling planner; the realtime engine
still owns start permission and never interrupts a protected cycle.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
import statistics


def _finite(value):
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except (TypeError, ValueError):
        return None


def _pct(values, q, fallback=0.0):
    vals = sorted(float(v) for v in values if _finite(v) is not None)
    if not vals:
        return fallback
    if len(vals) == 1:
        return vals[0]
    pos = (len(vals) - 1) * q
    lo = int(math.floor(pos)); hi = int(math.ceil(pos))
    if lo == hi:
        return vals[lo]
    return vals[lo] * (hi-pos) + vals[hi] * (pos-lo)


@dataclass(frozen=True)
class CycleEstimate:
    energy_kwh: float
    duration_min: float
    peak_w: float
    average_w: float
    confidence: float
    cycles: int
    days: int
    source: str
    program: str

    def as_dict(self):
        return {
            "program": self.program,
            "energy_kwh": round(self.energy_kwh, 3),
            "duration_min": round(self.duration_min, 1),
            "peak_w": round(self.peak_w),
            "average_w": round(self.average_w),
            "confidence": round(self.confidence, 3),
            "cycles": self.cycles,
            "days": self.days,
            "source": self.source,
        }


class CycleEnergyModel:
    """Learn energy, duration and peak per device/program from complete cycles."""

    def __init__(self):
        self.profiles: dict[str, dict[str, list[dict]]] = {}
        self.active: dict[str, dict] = {}
        self.accepted = 0
        self.rejected = 0

    @staticmethod
    def _program(value):
        text = str(value or "standaard").strip()
        return text[:80] or "standaard"

    def snapshot(self):
        return {
            "profiles": self.profiles,
            "active": {},  # never restore half-observed cycles as complete evidence
            "accepted": self.accepted,
            "rejected": self.rejected,
        }

    def restore(self, data):
        if not isinstance(data, dict):
            return
        raw = data.get("profiles", {})
        self.profiles = raw if isinstance(raw, dict) else {}
        self.active = {}
        self.accepted = max(0, int(data.get("accepted", 0) or 0))
        self.rejected = max(0, int(data.get("rejected", 0) or 0))

    def begin(self, device_id, program, wall_ts, day):
        self.active[str(device_id)] = {
            "program": self._program(program),
            "start": float(wall_ts),
            "day": str(day),
            "energy_kwh": 0.0,
            "peak_w": 0.0,
            "samples": 0,
        }

    def observe(self, device_id, watts, dt_s):
        row = self.active.get(str(device_id))
        w = _finite(watts); dt = _finite(dt_s)
        if row is None or w is None or dt is None or dt <= 0 or dt > 120 or w < 0 or w > 100000:
            return False
        row["energy_kwh"] += w * dt / 3_600_000.0
        row["peak_w"] = max(row["peak_w"], w)
        row["samples"] += 1
        return True

    def finish(self, device_id, wall_ts, *, min_duration_s=180, min_energy_kwh=0.02, max_duration_s=86400):
        row = self.active.pop(str(device_id), None)
        if row is None:
            return None
        duration = max(0.0, float(wall_ts) - float(row["start"]))
        energy = max(0.0, float(row["energy_kwh"]))
        if duration < min_duration_s or duration > max_duration_s or energy < min_energy_kwh or row["samples"] < 2:
            self.rejected += 1
            return None
        sample = {
            "day": row["day"], "energy_kwh": round(energy, 5),
            "duration_min": round(duration / 60.0, 2), "peak_w": round(row["peak_w"], 1),
        }
        dev = self.profiles.setdefault(str(device_id), {})
        cycles = dev.setdefault(row["program"], [])
        cycles.append(sample)
        del cycles[:-24]
        # Bound number of remembered program labels per appliance.
        while len(dev) > 12:
            del dev[next(iter(dev))]
        self.accepted += 1
        return sample

    def estimate(self, device_id, program=None, *, fallback_energy_kwh=0.0, fallback_duration_min=0.0, fallback_peak_w=0.0):
        p = self._program(program)
        dev = self.profiles.get(str(device_id), {})
        rows = list(dev.get(p, []))
        if not rows and p != "standaard":
            rows = list(dev.get("standaard", []))
        if rows:
            energies = [r.get("energy_kwh") for r in rows]
            durations = [r.get("duration_min") for r in rows]
            peaks = [r.get("peak_w") for r in rows]
            energy = _pct(energies, .50)
            # Duration and peak use a conservative upper quantile for planning/headroom.
            duration = _pct(durations, .75)
            peak = _pct(peaks, .90)
            days = len({r.get("day") for r in rows if r.get("day")})
            confidence = min(.95, len(rows) / 8.0) * min(1.0, days / 4.0)
            avg = energy * 1000.0 / max(duration / 60.0, .05)
            return CycleEstimate(energy, duration, peak, avg, confidence, len(rows), days, "geleerd", p)
        energy = max(0.0, float(fallback_energy_kwh or 0.0))
        duration = max(0.0, float(fallback_duration_min or 0.0))
        peak = max(0.0, float(fallback_peak_w or 0.0))
        if energy <= 0 and duration > 0 and peak > 0:
            # Conservative first-cycle estimate: 55% average duty at configured peak.
            energy = peak * (duration / 60.0) * .55 / 1000.0
        avg = energy * 1000.0 / max(duration / 60.0, .05) if energy > 0 and duration > 0 else peak
        source = "ingestelde cycluswaarde" if energy > 0 or duration > 0 else "nog geen cyclusprofiel"
        return CycleEstimate(energy, duration, peak, avg, .15 if energy > 0 and duration > 0 else 0.0, 0, 0, source, p)

    def overview(self, device_configs=None):
        device_configs = device_configs or {}
        out = {"accepted_cycles": self.accepted, "rejected_cycles": self.rejected, "devices": {}}
        ids = set(self.profiles) | set(device_configs)
        for device_id in ids:
            cfg = device_configs.get(device_id, {})
            program = cfg.get("cycle_program", "standaard")
            est = self.estimate(
                device_id, program,
                fallback_energy_kwh=cfg.get("cycle_energy_kwh", 0),
                fallback_duration_min=cfg.get("cycle_duration_min", 0),
                fallback_peak_w=cfg.get("nominal_w", 0),
            )
            out["devices"][device_id] = est.as_dict()
        return out
