"""Bounded read-only programme context; never a programme/result inference.

A point is a captured comparison, not a continuous interval. Native task
reports, normal tank target and individual meters keep their original times.
The current provider does not expose a verified effective hygiene target or
native completion result, so those two columns deliberately remain unknown.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import math
from .sg_target_display import contact_observation, retained_sg_goal
from .operation_source_evidence import contract_evidence, retained_contract_evidence

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


def captured_power(p, stamp, validated_watts):
    """Describe only the whole-pump meter already validated by the model."""
    stale = number(p.get("source_stale_s", 120))
    stale = stale if stale is not None and 0 < stale <= 600 else None
    original = report(p.get("power_observed_at", p.get("power_stamp")))
    scope = enum(p.get("power_scope"), {"total", "split"})
    kind = enum(p.get("power_kind"), {"measured"})
    watts = number(validated_watts)
    valid = (watts is not None and 0 <= watts <= 100000 and kind == "measured"
             and scope is not None and p.get("power_complete") is True and fresh(original, stamp, stale))
    times = [original]
    if scope == "split" or any(p.get(f"power_supply{n}_entity") for n in (1, 2)):
        times += [report(p.get(f"power_supply{n}_observed_at")) for n in (1, 2)]
    valid = bool(valid and all(fresh(value, stamp, stale) for value in times))
    # The total cannot be newer than its oldest actual contributing report.
    original = min(times) if valid else original
    expiry = report(original+stale) if valid else None
    valid = valid and expiry is not None
    return {"schema": 1, "total_w": watts if valid else None, "reported_at": original,
            "valid_until": expiry if valid else None, "stale_s": stale,
            "source_scope": scope, "complete": bool(valid), "kind": kind}


def retained_power(value, stamp, supplies, source_stale_s):
    """Validate optional recorded power without inventing legacy meter data."""
    if (not isinstance(value, dict) or type(value.get("schema")) is not int or value["schema"] != 1
            or type(value.get("complete")) is not bool
            or value.get("source_scope") not in (None, "total", "split")
            or value.get("kind") not in (None, "measured")):
        raise ValueError("Warmtepomphistoriek bevat ongeldig vermogensbewijs")
    clean = {"schema": 1, "complete": value["complete"],
             "source_scope": value.get("source_scope"), "kind": value.get("kind")}
    for key in ("total_w", "reported_at", "valid_until", "stale_s"):
        raw = value.get(key)
        normalized = report(raw) if key in ("reported_at", "valid_until") else number(raw)
        if raw is not None and normalized is None:
            raise ValueError("Warmtepomphistoriek bevat ongeldige vermogenswaarden")
        clean[key] = normalized
    watts, stale, original, expiry = (clean[key] for key in ("total_w", "stale_s", "reported_at", "valid_until"))
    expected_stale = source_stale_s if source_stale_s is not None and 0 < source_stale_s <= 600 else None
    if (stale != expected_stale or stale is not None and not 0 < stale <= 600
            or watts is not None and not 0 <= watts <= 100000
            or clean["complete"] != (watts is not None)
            or not clean["complete"] and expiry is not None):
        raise ValueError("Warmtepomphistoriek bevat tegenstrijdig vermogensbewijs")
    if clean["complete"]:
        if (clean["kind"] != "measured" or clean["source_scope"] is None
                or not fresh(original, stamp, stale) or expiry is None
                or not stamp <= expiry <= original+stale):
            raise ValueError("Warmtepomphistoriek bevat verlopen vermogensbewijs")
        if clean["source_scope"] == "split":
            if (not all(row["valid"] for row in supplies)
                    or abs(sum(row["watts"] for row in supplies)-watts) > max(0.1, watts*0.00001)
                    or any(original > row["reported_at"] for row in supplies)
                    or any(expiry > row["reported_at"]+stale for row in supplies)):
                raise ValueError("Warmtepomphistoriek bevat tegenstrijdige vermogensvoedingen")
    return clean


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

    def observe(self, p, stamp, evidence, *, sg=None, max_gap_s=30, power_w=None):
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
        source_contract = contract_evidence(p.get("source_contract"), stamp, stale)
        goal = p.get("sg_tank_goal")
        if isinstance(goal, dict):
            goal = retained_sg_goal({**goal, **contact_observation(sg, stamp)}, captured_at=stamp,
                stale_s=stale, normal_target_c=target, normal_target_reported_at=target_time)
        else:
            goal = None
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
                 "sg_goal": goal,
                 "source_contract": source_contract,
                 "effective_target": {"temperature_c": None, "reported_at": None, "status": "unknown"},
                 "completion": {"state": "unknown", "reported_at": None}, "supplies": supplies,
                 "power": captured_power(p, stamp, power_w)}
        fingerprint = (point["selected_program"], function, confirmed, bool(inactive), bool(global_off),
                       temp, target, tuple(row["valid"] for row in supplies),
                       goal.get("profile_percent") if goal else None,
                       goal.get("profile_confirmed_at") if goal else None,
                       goal.get("contact_state") if goal else None,
                       goal.get("reason") if goal else None)
        if source_contract is not None:
            fingerprint += (source_contract["contract_id"], source_contract["action_semantics"],
                tuple(source_contract["provider"].items()), source_contract["verified"], source_contract["fresh"],
                source_contract["reason_code"], source_contract["raw_device_action"],
                source_contract["pump"]["state"], source_contract["pump"]["fresh"],
                source_contract["direction"]["state"], source_contract["direction"]["fresh"],
                source_contract["program"]["state"], source_contract["program"]["raw_mode"],
                source_contract["tank"]["enabled"], source_contract["tank"]["fresh"],
                tuple((row["number"], row["enabled"], row["state"], row["fresh"])
                      for row in source_contract["zones"]))
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

    def temperature_detail(self, day, stamp, *, max_gap_s=30):
        """Expose actual retained readings and a separately bounded live view.

        Temperature points are never interpolated, shifted to capture time or
        backfilled from today's tank. Restoration deliberately has no live
        continuity anchor, even when its final stored point is recent.
        """
        detail = self.detail(day)
        points, previous = [], None
        for row in detail["points"]:
            tank = row["tank"]
            points.append({"captured_at": row["captured_at"], **deepcopy(tank),
                           "sg_goal": deepcopy(row.get("sg_goal")),
                           "stale_s": row["source_stale_s"],
                           "continuous_from_previous": bool(previous is not None and row["continuity"]
                               and 0 < row["captured_at"]-previous <= max_gap_s)})
            previous = row["captured_at"]
        last = self._last
        current = bool(last is not None and 0 <= stamp-last["captured_at"] <= max_gap_s)
        stale = last["source_stale_s"] if last is not None else None
        tank = last["tank"] if last is not None else {}
        values = {key: tank.get(key) for key in ("temperature_c", "temperature_reported_at",
                                               "ordinary_target_c", "ordinary_target_reported_at")}
        for key, original in (("temperature_c", "temperature_reported_at"),
                              ("ordinary_target_c", "ordinary_target_reported_at")):
            if not current or not fresh(values[original], stamp, stale):
                values[key] = None
        goal = deepcopy(last.get("sg_goal")) if last is not None else None
        if goal is not None:
            if not current or not fresh(goal.get("normal_target_reported_at"), stamp, goal.get("stale_s")):
                goal.update(normal_target_c=None, calculated_c=None, valid_until=None, reason="normal_target_unavailable")
            if (not current or not fresh(goal.get("contact_reported_at"), stamp, goal.get("contact_stale_s"))
                    or goal.get("contact_valid_until") is None or stamp > goal["contact_valid_until"]):
                goal.update(contact_state="unknown", contact_valid_until=None)
        return {"schema": 1, "current": {**values, "captured_at": last["captured_at"] if last else None,
                    "sg_goal": goal,
                    "current": current, "stale_s": stale, "capture_stale_s": max_gap_s},
                "points": points, "points_truncated": detail["points_truncated"],
                "ordinary_target_only": not any((row.get("sg_goal") or {}).get("calculated_c") is not None for row in points),
                "calculated_sg_target_available": any((row.get("sg_goal") or {}).get("calculated_c") is not None for row in points),
                "note": "Oorspronkelijke tankmetingen en normaal ingesteld doel. Het SG-doel is alleen berekend met het toen lokaal bevestigde percentage; geen interpolatie of voltooiingsbewijs."}

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
            goal = retained_sg_goal(row.get("sg_goal"), captured_at=at, stale_s=stale,
                normal_target_c=tank_clean["ordinary_target_c"],
                normal_target_reported_at=tank_clean["ordinary_target_reported_at"])
            source_contract = retained_contract_evidence(row.get("source_contract"), at, stale)
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
                            "native": native_clean, "tank": tank_clean, "supplies": supplies, "sg_goal": goal,
                            "source_contract": source_contract,
                            "effective_target": {"temperature_c": None, "reported_at": None, "status": "unknown"},
                            "completion": {"state": "unknown", "reported_at": None}})
            if "power" in row:
                cleaned[-1]["power"] = retained_power(row["power"], at, supplies, stale)
            previous = at
        trimmed = data.get("trimmed_before")
        if trimmed is not None and (number(trimmed) is None or not 0 < trimmed <= stamp+60
                                   or cleaned and trimmed >= cleaned[0]["captured_at"]):
            raise ValueError("Warmtepomphistoriek bevat ongeldige bewaargrens")
        self.points, self.trimmed_before = cleaned, trimmed
        self._last_prune_day = None
        self.pause()
        self.prune(stamp)


class SGContactEvidence:
    """Bounded actual contact ON/OFF intervals, distinct from request intent.

    Existing contact sessions still supply retained historical ON evidence.
    An old aggregate of known seconds cannot reconstruct where OFF occurred.
    """

    def __init__(self, zone):
        self.zone = zone
        self.spans = []
        self.trimmed_before = None
        self._last = None

    def pause(self):
        self._last = None

    def observe(self, state, stamp, reported_at, expiry, *, stale_s=120, max_gap_s=30):
        if state is not None and type(state) is not bool:
            raise ValueError("SG-contactbewijs vereist een bevestigde contacttoestand")
        original, expiry, stale = report(reported_at), report(expiry), number(stale_s)
        valid = (type(state) is bool and original is not None and expiry is not None
                 and fresh(original, stamp, stale) and stamp <= expiry <= original+stale)
        last = self._last
        if valid and last is not None and 0 < stamp-last["captured_at"] <= max_gap_s:
            right = min(stamp, last["valid_until"])
            if right > last["captured_at"]:
                span = {"start": last["captured_at"], "end": right, "on": last["on"],
                        "reported_at": last["reported_at"], "valid_until": last["valid_until"], "source_stale_s": last["source_stale_s"]}
                previous = self.spans[-1] if self.spans else None
                # Adjacent equal states may share the first actual source
                # report only within its unchanged original expiry. New HA
                # reports cannot renew that earlier evidence's deadline.
                if (previous is not None and previous["end"] == span["start"]
                        and previous["on"] == span["on"] and right <= previous["valid_until"]):
                    previous["end"] = right
                else:
                    self.spans.append(span)
        self._last = {"captured_at": stamp, "on": state, "reported_at": original,
                      "valid_until": expiry, "source_stale_s": stale} if valid else None
        self.prune(stamp)

    def prune(self, stamp):
        first = datetime.fromtimestamp(stamp, self.zone).date()-timedelta(days=29)
        boundary = datetime.combine(first, datetime.min.time(), self.zone).timestamp()
        self.spans = [row for row in self.spans if row["end"] > boundary]
        if len(self.spans) > MAX_POINTS:
            self.trimmed_before = self.spans[-MAX_POINTS-1]["end"]
            self.spans = self.spans[-MAX_POINTS:]

    def detail(self, day, stamp, bounds, contact):
        self.prune(stamp)
        left, day_end = bounds
        until = max(left, min(stamp, day_end))
        # Legacy retained ON sessions are still actual contact evidence. OFF is
        # included solely from this feature's explicit observed interval store.
        candidates = [{**row, "legacy": False} for row in self.spans if row["end"] > left and row["start"] < until]
        for session in contact.get("sessions", ()):
            start = datetime.fromisoformat(session["segment_start"]).timestamp()
            end = datetime.fromisoformat(session["segment_end"]).timestamp()
            if end > start:
                candidates.append({"start": start, "end": end, "on": True,
                                   "reported_at": None, "valid_until": None, "legacy": True})
        events = {left: {"start": [], "end": []}, until: {"start": [], "end": []}}
        for ident, row in enumerate(candidates):
            start, end = max(left, row["start"]), min(until, row["end"])
            if end <= start:
                continue
            events.setdefault(start, {"start": [], "end": []})["start"].append(ident)
            events.setdefault(end, {"start": [], "end": []})["end"].append(ident)
        boundaries = sorted(events)
        active = {}
        segments, known, on = [], 0.0, 0.0
        for start, end in zip(boundaries, boundaries[1:]):
            for ident in events[start]["end"]:
                active.pop(ident, None)
            for ident in events[start]["start"]:
                active[ident] = candidates[ident]
            covering = list(active.values())
            explicit = [row for row in covering if not row["legacy"]]
            proof = explicit[0] if explicit else covering[0] if covering else None
            conflict = len({row["on"] for row in covering}) > 1
            state = "unknown" if proof is None or conflict else "on" if proof["on"] else "off"
            duration = end-start
            if duration <= 0:
                continue
            if state != "unknown":
                known += duration
                on += duration if state == "on" else 0
            segment = {"state": state, "segment_start": datetime.fromtimestamp(start, timezone.utc).isoformat(timespec="seconds"),
                       "segment_end": datetime.fromtimestamp(end, timezone.utc).isoformat(timespec="seconds"),
                       "duration_s": round(duration, 1), "left_pct": round(100*(start-left)/(day_end-left), 5),
                       "width_pct": round(100*duration/(day_end-left), 5),
                       "reported_at": proof["reported_at"] if proof is not None and not conflict else None}
            if segments and segments[-1]["state"] == state and segments[-1]["reported_at"] == segment["reported_at"]:
                segments[-1].update(segment_end=segment["segment_end"],
                    duration_s=round(segments[-1]["duration_s"]+duration, 1),
                    width_pct=round(segments[-1]["width_pct"]+segment["width_pct"], 5))
            else:
                segments.append(segment)
        last = self._last
        current = last is not None and 0 <= stamp-last["captured_at"] <= 30 and stamp <= last["valid_until"]
        return {"schema": 1, "label": "SG-contact", "state": "on" if current and last["on"] else "off" if current else "unknown",
                "reported_at": last["reported_at"] if last is not None else None,
                "captured_at": last["captured_at"] if last is not None else None,
                "valid_until": last["valid_until"] if last is not None else None, "capture_stale_s": 30,
                "known_s": round(known, 1), "on_s": round(on, 1) if known > 0 else None,
                "unknown_s": round(max(0, until-left-known), 1), "segments": segments,
                "segments_truncated": bool(contact.get("sessions_truncated") or self.trimmed_before is not None and self.trimmed_before >= left),
                "note": "Bevestigd contact apart van SG-aanvraag; grijs is ontbrekend contactbewijs. Oude UIT-perioden worden niet uit dagtotalen gereconstrueerd."}

    def snapshot(self):
        return {"schema": 1, "spans": deepcopy(self.spans), "trimmed_before": self.trimmed_before}

    def restore(self, data, stamp):
        if data is None:
            return
        if (not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != 1
                or not isinstance(data.get("spans"), list) or len(data["spans"]) > MAX_POINTS):
            raise ValueError("Warmtepomphistoriek bevat ongeldig SG-contactbewijs")
        cleaned, previous = [], None
        for row in data["spans"]:
            if not isinstance(row, dict) or type(row.get("on")) is not bool:
                raise ValueError("Warmtepomphistoriek bevat ongeldig SG-contactbewijs")
            values = {key: report(row.get(key)) for key in ("start", "end", "reported_at", "valid_until")}
            stale = number(row.get("source_stale_s"))
            if (any(value is None for value in values.values()) or not values["start"] < values["end"] <= stamp+60
                    or previous is not None and values["start"] < previous
                    or stale is None or stale <= 0 or not fresh(values["reported_at"], values["start"], stale)
                    or not values["end"] <= values["valid_until"] <= values["reported_at"]+stale):
                raise ValueError("Warmtepomphistoriek bevat ongeldige SG-contacttijden")
            cleaned.append({**values, "on": row["on"], "source_stale_s": stale})
            previous = values["end"]
        trimmed = data.get("trimmed_before")
        if trimmed is not None and (report(trimmed) is None or trimmed > stamp+60
                                   or cleaned and trimmed > cleaned[0]["start"]):
            raise ValueError("Warmtepomphistoriek bevat een ongeldige SG-contactbewaargrens")
        self.spans, self.trimmed_before = cleaned, trimmed
        self.pause()
        self.prune(stamp)
