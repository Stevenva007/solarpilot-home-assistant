"""Bounded read-only programme context; never a programme/result inference.

A point is a captured comparison, not a continuous interval. Native task
reports, normal tank target and individual meters keep their original times.
The current provider does not expose a verified effective hygiene target or
native completion result, so those two columns deliberately remain unknown.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
import math

MAX_POINTS = 8192
CONTEXT_INTERVAL_S = 300
PROGRAMMES = {"heating", "cooling", "auto", "dhw", "off"}
FUNCTIONS = {"space_heating", "space_cooling", "tapwater_heating", "sterilization"}
SOURCES = {"native_hvac_action", "aquarea_poll"}


def number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError, OverflowError):
        return None


def report(value):
    value = number(value)
    return value if value is not None and 0 < value <= 4102444800 else None


def fresh(value, now, stale):
    value, stale = report(value), number(stale)
    return value is not None and stale is not None and stale > 0 and -5 <= now-value <= stale


def enum(value, allowed):
    return value if isinstance(value, str) and value in allowed else None


class NativeProgrammeEvidence:
    def __init__(self, zone):
        self.zone = zone
        self.points = []
        self.trimmed_before = None
        self._last = None
        self._fingerprint = None
        self._last_prune_day = None

    def pause(self):
        self._last = self._fingerprint = None

    def observe(self, p, stamp, evidence, *, max_gap_s=30):
        native = p.get("native_task") if isinstance(p.get("native_task"), dict) else {}
        stale = number(p.get("source_stale_s", 120))
        native_stale = number(native.get("stale_s", stale))
        native_time = report(native.get("observed_at"))
        native_fresh = fresh(native_time, stamp, native_stale)
        confirmed = (evidence.get("tier") == "confirmed" and evidence.get("context") in FUNCTIONS
                     and native_fresh and enum(native.get("source"), SOURCES) is not None)
        # Native inactive may be scoped to the space circuit; it cannot prove
        # the tank is idle. Preserve the scope, without inventing completion.
        inactive = (native_fresh and native.get("inactive") is True
                    and enum(native.get("source"), SOURCES) is not None and native.get("conflict") is not True)
        function = evidence["context"] if confirmed else None
        global_off = (inactive and native.get("source") == "aquarea_poll" and native.get("verified_global_off") is True
                      and native.get("inactive_scope") == "global" and native.get("inactive_action") == "off"
                      and native.get("independent_tank_on", False) is False and native.get("conflict", False) is False
                      and native.get("function") is None)
        continuous = self._last is not None and 0 < stamp-self._last["captured_at"] <= max_gap_s
        previous = self._last.get("native", {}) if continuous else {}
        start = bool(confirmed and previous.get("global_off") is True and native_time > previous.get("reported_at"))
        tank = p.get("display_tank") if isinstance(p.get("display_tank"), dict) else {}
        def temperature(value, original):
            value, original = number(value), report(original)
            valid = value is not None and -20 <= value <= 100 and fresh(original, stamp, stale)
            return value if valid else None, original
        temp, temp_time = temperature(tank.get("temperature_c", p.get("temperature_c")),
                                      tank.get("temperature_stamp", p.get("temperature_stamp")))
        target, target_time = temperature(tank.get("target_c", p.get("target_c")),
                                          tank.get("target_stamp", p.get("target_stamp")))
        supplies = []
        for n in (1, 2):
            watts, original = number(p.get(f"power_supply{n}_w")), report(p.get(f"power_supply{n}_observed_at"))
            is_fresh = fresh(original, stamp, stale)
            valid = bool(p.get(f"power_supply{n}_valid") is True and watts is not None and 0 <= watts <= 100000 and is_fresh)
            supplies.append({"number": n, "watts": watts if valid else None, "valid": valid,
                             "fresh": is_fresh, "reported_at": original})
        point = {"captured_at": stamp, "continuity": continuous,
                 "source_stale_s": stale,
                 "selected_program": enum(p.get("program"), PROGRAMMES),
                 "native": {"function": function, "confirmed": confirmed,
                            "inactive_reported": bool(inactive), "global_off": bool(global_off),
                            "verified_global_off": native.get("verified_global_off") is True,
                            "conflict": native.get("conflict") is True,
                            "independent_tank_on": native.get("independent_tank_on", False) is not False,
                            "inactive_action": enum(native.get("inactive_action"), {"idle", "off"}),
                            "inactive_scope": enum(native.get("inactive_scope"), {"global", "space_circuit"}),
                            "source": enum(native.get("source"), SOURCES),
                            "reported_at": native_time, "stale_s": native_stale, "fresh": native_fresh, "start_observed": start},
                 "tank": {"temperature_c": temp, "temperature_reported_at": temp_time,
                          "ordinary_target_c": target, "ordinary_target_reported_at": target_time},
                 "effective_target": {"temperature_c": None, "reported_at": None, "status": "unknown"},
                 "completion": {"state": "unknown", "reported_at": None}, "supplies": supplies}
        fingerprint = (point["selected_program"], function, confirmed, bool(inactive), bool(global_off),
                       temp, target, tuple(row["valid"] for row in supplies))
        if (self._fingerprint != fingerprint or not continuous or start
                or not self.points or stamp-self.points[-1]["captured_at"] >= CONTEXT_INTERVAL_S):
            # A start retains the actual immediately preceding OFF sample too,
            # even when unchanged context had been coalesced for presentation.
            if start and self.points and self.points[-1]["captured_at"] < self._last["captured_at"]:
                self.points.append(deepcopy(self._last))
            self.points.append(point)
        self._last, self._fingerprint = point, fingerprint
        self.prune(stamp)

    def prune(self, stamp):
        day = datetime.fromtimestamp(stamp, self.zone).date()
        if day != self._last_prune_day:
            first = day-timedelta(days=29)
            index = 0
            while index < len(self.points) and datetime.fromtimestamp(self.points[index]["captured_at"], self.zone).date() < first:
                index += 1
            if index:
                # An observed native start requires its retained preceding
                # actual OFF. Do not retain an orphaned proof at the boundary.
                while index < len(self.points) and self.points[index]["native"]["start_observed"]:
                    self.trimmed_before = self.points[index]["captured_at"]
                    index += 1
                self.points = self.points[index:]
            self._last_prune_day = day
        if len(self.points) > MAX_POINTS:
            index = len(self.points)-MAX_POINTS
            while index < len(self.points) and self.points[index]["native"]["start_observed"]:
                index += 1
            self.trimmed_before = self.points[index-1]["captured_at"]
            self.points = self.points[index:]

    def detail(self, day):
        points = [deepcopy(row) for row in self.points if datetime.fromtimestamp(row["captured_at"], self.zone).date().isoformat() == day]
        truncated = self.trimmed_before is not None and datetime.fromtimestamp(self.trimmed_before, self.zone).date().isoformat() >= day
        return {"schema": 1, "read_only": True, "points": points, "points_truncated": truncated,
                "context_interval_s": CONTEXT_INTERVAL_S, "maximum_points": MAX_POINTS,
                "effective_target_available": False, "native_completion_available": False,
                "note": "Vergelijkingspunten met oorspronkelijke rapporttijden; geen continue programmameting. Het normale tankdoel, temperatuur en watts bewijzen geen sterilisatie of native voltooiing."}

    def snapshot(self):
        return {"schema": 1, "points": deepcopy(self.points), "trimmed_before": self.trimmed_before}

    def restore(self, data, stamp):
        if data is None:
            return
        if (not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != 1
                or not isinstance(data.get("points"), list) or len(data["points"]) > MAX_POINTS):
            raise ValueError("Warmtepomphistoriek bevat ongeldig programmabewijs")
        cleaned, previous = [], None
        for row in data["points"]:
            at = number(row.get("captured_at")) if isinstance(row, dict) else None
            if at is None or not 0 < at <= stamp+60 or previous is not None and at <= previous:
                raise ValueError("Warmtepomphistoriek bevat ongeldige programmatijden")
            # Only this closed field set may leave private storage. Rebuild it
            # rather than forwarding unknown keys, labels or entity identities.
            native, tank = row.get("native"), row.get("tank")
            if not isinstance(native, dict) or not isinstance(tank, dict) or not isinstance(row.get("supplies"), list):
                raise ValueError("Warmtepomphistoriek bevat ongeldig programmabewijs")
            booleans = ("confirmed", "inactive_reported", "global_off", "fresh", "start_observed", "verified_global_off", "conflict", "independent_tank_on")
            if type(row.get("continuity")) is not bool or any(type(native.get(key)) is not bool for key in booleans):
                raise ValueError("Warmtepomphistoriek bevat ongeldig programmabewijs")
            if (native.get("function") is not None and enum(native.get("function"), FUNCTIONS) is None) or (native.get("source") is not None and enum(native.get("source"), SOURCES) is None):
                raise ValueError("Warmtepomphistoriek bevat ongeldig programmabewijs")
            if (row.get("selected_program") is not None and enum(row.get("selected_program"), PROGRAMMES) is None) or native.get("inactive_scope") not in (None, "global", "space_circuit") or native.get("inactive_action") not in (None, "idle", "off"):
                raise ValueError("Warmtepomphistoriek bevat ongeldig programmabewijs")
            def retained_number(value, *, time=False):
                if value is None:
                    return None
                out = number(value)
                if out is None or time and not 0 < out <= 4102444800:
                    raise ValueError("Warmtepomphistoriek bevat ongeldige bronwaarden")
                return out
            native_clean = {key: native[key] for key in (*booleans, "function", "source", "inactive_scope", "inactive_action")}
            native_clean["reported_at"] = retained_number(native.get("reported_at"), time=True)
            native_clean["stale_s"] = retained_number(native.get("stale_s"))
            stale = retained_number(row.get("source_stale_s"))
            if native["fresh"] != fresh(native_clean["reported_at"], at, native_clean["stale_s"]):
                raise ValueError("Warmtepomphistoriek bevat tegenstrijdige native actualiteit")
            if (native["confirmed"] != (native["function"] is not None)
                    or native["confirmed"] and (not native["fresh"] or native["source"] not in SOURCES or native["inactive_reported"])
                    or native["inactive_reported"] and (not native["fresh"] or native["source"] not in SOURCES)
                    or native["global_off"] and (not native["inactive_reported"] or native["inactive_scope"] != "global"
                        or native["source"] != "aquarea_poll" or native["inactive_action"] != "off"
                        or native["verified_global_off"] is not True or native["independent_tank_on"] or native["conflict"])
                    or native["start_observed"] and (not native["confirmed"] or not cleaned
                        or not 0 < at-cleaned[-1]["captured_at"] <= 30
                        or cleaned[-1]["native"]["global_off"] is not True
                        or native_clean["reported_at"] <= cleaned[-1]["native"]["reported_at"])):
                raise ValueError("Warmtepomphistoriek bevat tegenstrijdig native bewijs")
            tank_clean = {key: retained_number(tank.get(key), time="reported_at" in key) for key in (
                "temperature_c", "temperature_reported_at", "ordinary_target_c", "ordinary_target_reported_at")}
            if (any(value is not None and not -20 <= value <= 100 for key, value in tank_clean.items() if key.endswith("_c"))
                    or tank_clean["temperature_c"] is not None and not fresh(tank_clean["temperature_reported_at"], at, stale)
                    or tank_clean["ordinary_target_c"] is not None and not fresh(tank_clean["ordinary_target_reported_at"], at, stale)):
                raise ValueError("Warmtepomphistoriek bevat ongeldige tankwaarden")
            supplies = []
            if len(row["supplies"]) != 2:
                raise ValueError("Warmtepomphistoriek bevat ongeldige voedingen")
            for n, supply in enumerate(row["supplies"], 1):
                if (not isinstance(supply, dict) or type(supply.get("number")) is not int or supply["number"] != n
                        or type(supply.get("valid")) is not bool or type(supply.get("fresh")) is not bool):
                    raise ValueError("Warmtepomphistoriek bevat ongeldige voedingen")
                watts = retained_number(supply.get("watts"))
                if watts is not None and not 0 <= watts <= 100000 or supply["valid"] != (watts is not None):
                    raise ValueError("Warmtepomphistoriek bevat ongeldige voedingen")
                original = retained_number(supply.get("reported_at"), time=True)
                if supply["fresh"] != fresh(original, at, stale) or supply["valid"] and not supply["fresh"]:
                    raise ValueError("Warmtepomphistoriek bevat tegenstrijdige voedingsactualiteit")
                supplies.append({"number": n, "watts": watts, "valid": supply["valid"], "fresh": supply["fresh"],
                                 "reported_at": original})
            cleaned.append({"captured_at": at, "continuity": row["continuity"], "source_stale_s": stale, "selected_program": row["selected_program"],
                            "native": native_clean, "tank": tank_clean, "supplies": supplies,
                            "effective_target": {"temperature_c": None, "reported_at": None, "status": "unknown"},
                            "completion": {"state": "unknown", "reported_at": None}})
            previous = at
        trimmed = data.get("trimmed_before")
        if trimmed is not None and (number(trimmed) is None or not 0 < trimmed <= stamp+60
                                   or cleaned and trimmed >= cleaned[0]["captured_at"]):
            raise ValueError("Warmtepomphistoriek bevat ongeldige bewaargrens")
        self.points, self.trimmed_before = cleaned, trimmed
        self._last_prune_day = None
        self.pause()
        self.prune(stamp)
