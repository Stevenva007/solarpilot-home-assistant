"""Bounded, local observations. No ML service and no self-modifying code.

Only the inter-command *stability* wait may be increased automatically. Never
relax electrical limits, import ceilings, handover deadlines or device locks.
Response observations include sensor/cloud latency, not just physical latency.
"""
from __future__ import annotations
from collections import deque
import hashlib
import json
import math


def percentile(values, fraction):
    data = sorted(values)
    return data[max(0, min(len(data) - 1, math.ceil(len(data) * fraction) - 1))] if data else None


def fingerprint(config):
    keys = ("kind", "control_entity", "number_entity", "power_entity", "start_script", "stop_script",
            "active_entity", "nominal_w", "watts_per_unit", "min_units", "max_units", "step_units")
    return hashlib.sha256(json.dumps({k: config.get(k) for k in keys}, sort_keys=True).encode()).hexdigest()[:20]


class LocalLearning:
    def __init__(self):
        self.enabled = True
        self.responses = deque(maxlen=40)
        self.profiles = {}
        self.last_sample = {}
        self.last_stamp = {}
        self.last_wallbox_stamp = None
        self.report_intervals = deque(maxlen=40)
        self.successes = 0
        self.failures = 0

    def reset(self):
        enabled = self.enabled
        self.__init__()
        self.enabled = enabled

    def snapshot(self):
        return {"enabled": self.enabled, "responses_s": list(self.responses),
                "profiles": self.profiles, "report_intervals_s": list(self.report_intervals),
                "successes": self.successes, "failures": self.failures}

    def restore(self, data, configs):
        if not isinstance(data, dict):
            return
        self.enabled = data.get("enabled", True) is True
        self.responses.extend(v for v in data.get("responses_s", [])[-40:]
                              if isinstance(v, (int, float)) and math.isfinite(v) and 0 < v <= 1800)
        self.report_intervals.extend(v for v in data.get("report_intervals_s", [])[-40:]
                                    if isinstance(v, (int, float)) and math.isfinite(v) and 1 <= v <= 1800)
        for i, c in configs.items():
            p = data.get("profiles", {}).get(i, {})
            if p.get("fingerprint") == fingerprint(c):
                values = [v for v in p.get("watts", [])[-120:]
                          if isinstance(v, (int, float)) and math.isfinite(v) and 0 < v <= 100000]
                self.profiles[i] = {"fingerprint": p["fingerprint"], "watts": values}
        self.successes = max(0, int(data.get("successes", 0)))
        self.failures = max(0, int(data.get("failures", 0)))

    def observe_report(self, stamp):
        if not self.enabled or not math.isfinite(stamp) or stamp <= 0:
            return
        if self.last_wallbox_stamp is not None and stamp > self.last_wallbox_stamp:
            delta = stamp - self.last_wallbox_stamp
            if 1 <= delta <= 1800:
                self.report_intervals.append(round(delta, 1))
        if self.last_wallbox_stamp is None or stamp > self.last_wallbox_stamp:
            self.last_wallbox_stamp = stamp

    def observe_device(self, i, cfg, watts, now, stamp):
        if not self.enabled or not cfg.get("power_entity") or not math.isfinite(watts) or watts <= 0:
            return
        if now - self.last_sample.get(i, -1e12) < 60 or stamp <= self.last_stamp.get(i, 0):
            return
        fp = fingerprint(cfg)
        if self.profiles.get(i, {}).get("fingerprint") != fp:
            self.profiles[i] = {"fingerprint": fp, "watts": []}
        p = self.profiles[i]
        p["watts"] = (p["watts"] + [round(watts, 1)])[-120:]
        self.last_sample[i], self.last_stamp[i] = now, stamp

    def record_handover(self, success, seconds):
        if not self.enabled:
            return
        if success:
            self.successes += 1
            if math.isfinite(seconds) and 0 < seconds <= 1800:
                self.responses.append(round(seconds, 1))
        else:
            self.failures += 1

    def effective_stable_s(self, configured):
        if not self.enabled or len(self.responses) < 5:
            return configured
        # Only increase this soft scheduling wait. The configured floor remains.
        suggestion = math.ceil((percentile(self.responses, .9) + 30) / 5) * 5
        return max(configured, min(600, suggestion))


    def conservative_power(self, i, cfg, min_samples=10, max_multiplier=2.0):
        """Return a planning estimate that may only rise from the configured value.

        The learned value is deliberately conservative: after enough dedicated
        meter samples it uses P90, capped by a multiple of the configured nominal
        power. It never reduces the configured estimate automatically.
        """
        configured = float(cfg.get("nominal_w", 0) or 0)
        if not self.enabled or configured <= 0:
            return configured
        p = self.profiles.get(i, {})
        values = p.get("watts", [])
        if len(values) < int(min_samples):
            return configured
        p90 = percentile(values, .9)
        if p90 is None:
            return configured
        return max(configured, min(float(p90), configured * max(1.0, float(max_multiplier))))

    def overview(self, configured):
        profiles = {}
        for i, p in self.profiles.items():
            values = p["watts"]
            profiles[i] = {"samples": len(values), "median_w": percentile(values, .5),
                           "p90_w": percentile(values, .9), "peak_observed_w": max(values) if values else None,
                           "status": "Beschikbaar voor conservatieve planningsschatting" if len(values) >= 10 else "Gegevens verzamelen"}
        return {"enabled": self.enabled, "local_only": True, "samples": len(self.responses),
                "successes": self.successes, "failures": self.failures,
                "response_p90_s": percentile(self.responses, .9),
                "reported_interval_median_s": percentile(self.report_intervals, .5),
                "configured_stable_s": configured, "effective_stable_s": self.effective_stable_s(configured),
                "status": "Uitgeschakeld; vaste instellingen" if not self.enabled else
                          "Begrensde aanpassing actief" if len(self.responses) >= 5 else "Leren; nog geen automatische aanpassing",
                "profiles": profiles,
                "note": "Reactietijden omvatten rapportvertraging. Vermogensprofielen mogen de planningsschatting alleen verhogen en zijn geen elektrische maximumwaarden."}
