"""Local observed heat-pump/SG history, without control or inferred SG savings.

Actual task reports, electrical uptake and the three SG layers retain their
own evidence. Short intervals between complete fresh watt readings give an
electrical energy integral, not delivered heat or a compressor runtime meter.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import math

from .consumer_history import ConsumerHistory, MAX_SESSIONS
from .heatpump_learning import ACTIVE_CONTEXTS, classify_heatpump_observation
from .heatpump_history_evidence import NativeProgrammeEvidence

SCHEMA_VERSION = 1
MAX_GAP_S = 30
MAX_TASK_SESSIONS = MAX_SESSIONS
MAX_POWER_W = 100000
LABELS = {"space_heating": "Ruimte verwarmen", "space_cooling": "Ruimte koelen",
          "tapwater_heating": "Sanitair water opwarmen", "sterilization": "Sterilisatie",
          "electrical_support": "Elektrische ondersteuning", "defrost": "Ontdooien gemeld",
          "heatpump_unknown": "Taak onbekend"}
LANES = {"heatpump": "Warmtepomp", "sg_request": "SG-aanvraag",
         "sg_contact": "SG-contact", "sg_received": "Ontvangen SG-status"}
TASKS = [(task, tier) for task in sorted(ACTIVE_CONTEXTS) for tier in ("confirmed", "derived")]
TASKS += [("electrical_support", "derived"), ("defrost", "confirmed"), ("heatpump_unknown", "unknown")]


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _fresh(stamp, now, stale=120):
    stamp, stale = _number(stamp), _number(stale)
    return stamp is not None and stale is not None and stale > 0 and -5 <= now-stamp <= stale


def _iso(stamp):
    return datetime.fromtimestamp(stamp, timezone.utc).isoformat(timespec="seconds")


class HeatpumpHistory:
    """Bounded 30-day history; UTC intervals are split at HA-local midnight."""

    def __init__(self, timezone_name="Europe/Brussels"):
        self.lanes = ConsumerHistory(timezone_name)
        self.tasks = ConsumerHistory(self.lanes.timezone_name)
        self.electrical = ConsumerHistory(self.lanes.timezone_name)
        self.native_evidence = NativeProgrammeEvidence(self.lanes.zone)
        self.timezone_name = self.lanes.timezone_name
        self.energy_days = {}
        self.binding = ""
        self.revision = 0
        self._last_stamp = None
        self._last_energy = None
        self._current_task = None
        self._expiries = {}

    @staticmethod
    def _task_id(task, tier):
        return task + ":" + tier

    def _config(self, name, binding=None):
        return {"name": name, "kind": "heatpump_history", "control_entity": self.binding if binding is None else binding}

    def _ensure(self, when):
        for lane, name in LANES.items():
            self.lanes.ensure(lane, self._config(name), when)
        self.electrical.ensure("electrical_activity", self._config("Gemeten elektrische activiteit"), when)
        for task, tier in TASKS:
            self.tasks.ensure(self._task_id(task, tier), self._config(LABELS[task]), when)

    @staticmethod
    def _meter(p, now):
        """Use raw measurement timestamps, independent of task context age."""
        watts = _number(p.get("power_w"))
        stale = p.get("source_stale_s", 120)
        if (p.get("power_kind") != "measured" or p.get("power_complete") is not True
                or p.get("power_scope") not in ("total", "split")
                or watts is None or not 0 <= watts <= MAX_POWER_W
                or not _fresh(p.get("power_observed_at", p.get("power_stamp")), now, stale)):
            return None
        # A split aggregate cannot make one old/invalid feed current. Legacy
        # complete total meters have no supply bindings and need no fake feeds.
        split = p.get("power_scope") == "split" or any(p.get(f"power_supply{n}_entity") for n in (1, 2))
        if split:
            values = []
            for n in (1, 2):
                value = _number(p.get(f"power_supply{n}_w"))
                if (p.get(f"power_supply{n}_valid") is not True or value is None or value < 0
                        or not _fresh(p.get(f"power_supply{n}_observed_at"), now, stale)):
                    return None
                values.append(value)
            if abs(sum(values)-watts) > max(0.1, watts*0.00001):
                return None
        return watts

    @staticmethod
    def _state(p, now, watts):
        evidence = classify_heatpump_observation(p, now_wall=now)
        power = p.get("power_activity") or {}
        defrost = p.get("defrost") or {}
        defrost_on = (defrost.get("state") == "active" and defrost.get("source") in ("aquarea_entity", "aquarea_poll")
                      and _fresh(defrost.get("observed_at"), now, defrost.get("stale_s", p.get("source_stale_s", 120))))
        native = evidence.get("tier") == "confirmed" and evidence.get("context") in ACTIVE_CONTEXTS
        threshold = _number(power.get("threshold_w"))
        metered = watts is not None and threshold is not None and threshold > 0
        supplies = power.get("supplies") if isinstance(power.get("supplies"), list) else []
        partial_active = (power.get("state") == "partial" and power.get("active") is True
            and threshold is not None and threshold > 0 and any(
                isinstance(row, dict) and row.get("valid") is True and _number(row.get("watts")) is not None
                and _number(row["watts"]) >= threshold
                and _fresh(row.get("observed_at"), now, power.get("stale_s", p.get("source_stale_s", 120)))
                for row in supplies))
        raw_partial_w = _number(p.get("power_w"))
        partial_active = partial_active or (power.get("state") == "partial" and power.get("active") is True
            and p.get("power_kind") == "measured" and threshold is not None and threshold > 0
            and raw_partial_w is not None and threshold <= raw_partial_w <= MAX_POWER_W
            and _fresh(p.get("power_observed_at", p.get("power_stamp")), now, p.get("source_stale_s", 120)))
        if defrost_on or native:
            active = True
        elif metered:
            active = watts >= threshold
        elif partial_active:
            active = True
        elif p.get("configured") is True and evidence.get("tier") == "inactive":
            active = False
        else:
            active = None
        task = None
        if active:
            if defrost_on:
                task = ("defrost", "confirmed")
            elif native:
                # A native task names the reported action; it never implies
                # that the compressor produced the observed electrical uptake.
                task = (evidence["context"], "confirmed")
            elif metered and power.get("activity_kind") == "heater":
                task = ("electrical_support", "derived")
            elif evidence.get("context") in ACTIVE_CONTEXTS and evidence.get("tier") in ("confirmed", "derived"):
                task = (evidence["context"], evidence["tier"])
            else:
                task = ("heatpump_unknown", "unknown")
        return active, task, evidence

    @staticmethod
    def _source_expiry(stamp, now, stale=120):
        return _number(stamp)+_number(stale) if _fresh(stamp, now, stale) else None

    def _current_expiries(self, p, sg, stamp, watts, task, evidence):
        """Currentness ends at the original source deadline or polling gap."""
        stale = p.get("source_stale_s", 120)
        native, power, defrost = p.get("native_task") or {}, p.get("power_activity") or {}, p.get("defrost") or {}
        meter = self._source_expiry(p.get("power_observed_at", p.get("power_stamp")), stamp, stale) if watts is not None else None
        if meter is not None and (p.get("power_scope") == "split" or any(p.get(f"power_supply{n}_entity") for n in (1, 2))):
            meter = min(meter, *(self._source_expiry(p.get(f"power_supply{n}_observed_at"), stamp, stale) for n in (1, 2)))
        native_expiry = (self._source_expiry(native.get("observed_at"), stamp, native.get("stale_s", stale))
                         if evidence.get("tier") == "confirmed" else None)
        defrost_expiry = (self._source_expiry(defrost.get("observed_at"), stamp, defrost.get("stale_s", stale))
                          if defrost.get("state") == "active" and defrost.get("source") in ("aquarea_entity", "aquarea_poll") else None)
        threshold = _number(power.get("threshold_w"))
        electrical = [meter if watts is not None and threshold is not None and threshold > 0 and watts >= threshold else None]
        if power.get("state") == "partial":
            rows = power.get("supplies") if isinstance(power.get("supplies"), list) else []
            for row in rows:
                if (isinstance(row, dict) and row.get("valid") is True and threshold is not None and threshold > 0
                        and _number(row.get("watts")) is not None and _number(row["watts"]) >= threshold):
                    electrical.append(self._source_expiry(row.get("observed_at"), stamp, power.get("stale_s", stale)))
            raw_w = _number(p.get("power_w"))
            if (p.get("power_kind") == "measured" and threshold is not None and threshold > 0
                    and raw_w is not None and threshold <= raw_w <= MAX_POWER_W):
                electrical.append(self._source_expiry(p.get("power_observed_at", p.get("power_stamp")), stamp, stale))
        activity_expiry = max([value for value in [native_expiry, defrost_expiry, *electrical] if value is not None] or [stamp])
        expiries = {"heatpump": min(stamp+MAX_GAP_S, activity_expiry),
            "sg_request": self._source_expiry(sg.get("observed_at"), stamp, sg.get("relay_stale_s", 120)),
            "sg_contact": self._source_expiry(sg.get("relay_observed_at"), stamp, sg.get("relay_stale_s", 120)),
            "sg_received": self._source_expiry(p.get("sg_status_observed_at", p.get("sg_status_stamp")), stamp, stale)}
        deadline = _number(sg.get("relay_valid_until"))
        if sg.get("relay_on") is True and deadline is not None and expiries["sg_contact"] is not None:
            expiries["sg_contact"] = min(expiries["sg_contact"], deadline)
        if task:
            key, tier = task
            if key == "defrost":
                task_expiry = defrost_expiry
            elif tier == "confirmed":
                task_expiry = native_expiry
            elif key == "heatpump_unknown":
                task_expiry = activity_expiry
            elif key == "electrical_support":
                task_expiry = meter
            else:
                context = p.get("task_context") or {}
                values = [meter, self._source_expiry(power.get("observed_at"), stamp, power.get("stale_s", stale)),
                          self._source_expiry(context.get("observed_at"), stamp, context.get("stale_s", stale))]
                task_expiry = min(value for value in values if value is not None)
            expiries[self._task_id(*task)] = min(stamp+MAX_GAP_S, task_expiry if task_expiry is not None else stamp)
        return expiries

    @staticmethod
    def _sg(p, sg, now):
        request = None
        if sg.get("configured") is True and _fresh(sg.get("observed_at"), now, sg.get("relay_stale_s", 120)):
            request = sg.get("desired_on") if isinstance(sg.get("desired_on"), bool) else None
        contact = None
        if (sg.get("configured") is True and sg.get("relay_confirmed") is True
                and _fresh(sg.get("relay_observed_at"), now, sg.get("relay_stale_s", 120))
                and isinstance(sg.get("relay_on"), bool)):
            contact = sg["relay_on"]
            valid_until = _number(sg.get("relay_valid_until"))
            if contact and valid_until is not None and valid_until <= now:
                contact = None
        received = None
        if (p.get("sg_status_entity") and p.get("sg_status_confirmed") is True
                and _fresh(p.get("sg_status_observed_at", p.get("sg_status_stamp")), now, p.get("source_stale_s", 120))):
            received = True if p.get("sg_status") == "active" else False if p.get("sg_status") == "inactive" else None
        return request, contact, received

    @staticmethod
    def _describe(model, lane, name, active, stamp, *, request=False):
        row = model.devices[lane]
        session = row["sessions"][-1] if row["sessions"] else None
        if not session:
            return
        if active and session["start"] == stamp:
            session["start_reason"] = (name + " waargenomen" if session["start_confirmed"] else
                                       name + " al actief bij begin/hervatten registratie; eerdere starttijd onbekend")
            if request and session["start_confirmed"]:
                session["start_source"] = "solarpilot"
        elif active is False and session.get("end") == stamp and session.get("stop_confirmed"):
            session["stop_reason"] = name + " niet meer actief gemeld"
            if request:
                session["stop_source"] = "solarpilot"

    def observe(self, panasonic_snapshot, sg_snapshot, when, *, binding=""):
        stamp = self.lanes._stamp(when)
        if self._last_stamp is not None and stamp <= self._last_stamp:
            return  # Duplicate/reversed controller time cannot double-count.
        binding = str(binding or "")[:256]
        if binding != self.binding:
            self.pause_recording("Bronkoppeling gewijzigd; geen interval over verschillende bronnen")
            self.binding = binding
        self._ensure(when)
        p = panasonic_snapshot if isinstance(panasonic_snapshot, dict) else {}
        sg = sg_snapshot if isinstance(sg_snapshot, dict) else {}
        watts = self._meter(p, stamp)
        active, task, evidence = self._state(p, stamp, watts)
        self._expiries = self._current_expiries(p, sg, stamp, watts, task, evidence)
        threshold = _number((p.get("power_activity") or {}).get("threshold_w"))
        electrical_active = watts >= threshold if watts is not None and threshold is not None and threshold > 0 else None
        self.electrical.observe("electrical_activity", self._config("Gemeten elektrische activiteit"), electrical_active, when, max_gap_s=MAX_GAP_S)
        self._describe(self.electrical, "electrical_activity", "Gemeten elektrische activiteit", electrical_active, stamp)
        self._expiries["electrical_activity"] = self._source_expiry(p.get("power_observed_at", p.get("power_stamp")), stamp, p.get("source_stale_s", 120))
        self.native_evidence.observe(p, stamp, evidence, max_gap_s=MAX_GAP_S)
        request, contact, received = self._sg(p, sg, stamp)
        for lane, value in zip(LANES, (active, request, contact, received)):
            self.lanes.observe(lane, self._config(LANES[lane]), value, when, max_gap_s=MAX_GAP_S)
            self._describe(self.lanes, lane, LANES[lane], value, stamp, request=lane == "sg_request")
        for key in TASKS:
            lane = self._task_id(*key)
            value = None if active is None else bool(active and key == task)
            self.tasks.observe(lane, self._config(LABELS[key[0]]), value, when, max_gap_s=MAX_GAP_S)
            self._describe(self.tasks, lane, LABELS[key[0]], value, stamp)
        last = self._last_energy
        if watts is not None and last is not None and 0 < stamp-last[0] <= MAX_GAP_S:
            left, before = last
            elapsed = stamp-left
            for day, seconds in self.lanes._split(left, stamp):
                right = left+seconds
                # Linear interpolation allocates a crossing-midnight interval
                # to the real 23/24/25-hour local days without double counting.
                first_w = before+(watts-before)*(left-last[0])/elapsed
                last_w = before+(watts-before)*(right-last[0])/elapsed
                agg = self.energy_days.setdefault(day, {"energy_kwh": 0.0, "energy_known_s": 0.0})
                agg["energy_kwh"] += (first_w+last_w)*0.5*seconds/3600000
                agg["energy_known_s"] += seconds
                left = right
        self._last_energy = (stamp, watts) if watts is not None else None
        self._last_stamp, self._current_task = stamp, task
        self.revision += 1
        self._prune(stamp)

    def _prune(self, stamp):
        self.native_evidence.prune(stamp)
        first = (datetime.fromtimestamp(stamp, self.lanes.zone).date()-timedelta(days=29)).isoformat()
        self.energy_days = {day: value for day, value in self.energy_days.items() if first <= day <= self.lanes._day(stamp)}
        sessions = [(s["start"], lane, s["id"]) for lane, row in self.tasks.devices.items() for s in row["sessions"]]
        if len(sessions) > MAX_TASK_SESSIONS:
            keep = {(lane, ident) for _, lane, ident in sorted(sessions)[-MAX_TASK_SESSIONS:]}
            for lane, row in self.tasks.devices.items():
                removed = [s for s in row["sessions"] if (lane, s["id"]) not in keep]
                if removed:
                    row["trimmed_before"] = max(s.get("end") or s["observed_until"] for s in removed)
                    row["sessions"] = [s for s in row["sessions"] if (lane, s["id"]) in keep]

    def _energy(self, day):
        agg = self.energy_days.get(day, {})
        known = max(0.0, agg.get("energy_known_s", 0))
        return {"energy_kwh": round(max(0.0, agg.get("energy_kwh", 0)), 6) if known > 0 else None,
                "energy_known_s": round(known, 1)}

    def brief(self, when):
        stamp = self.lanes._stamp(when)
        result = self.lanes.brief("heatpump", when)
        result.update(self._energy(result["date"]))
        current = self._last_stamp is not None and 0 <= stamp-self._last_stamp <= MAX_GAP_S
        activity_current = current and stamp <= self._expiries.get("heatpump", stamp)
        task_current = current and self._current_task and stamp <= self._expiries.get(self._task_id(*self._current_task), stamp)
        result.update(revision=self.revision, ongoing=bool(activity_current and result.get("ongoing")),
                      task=self._current_task[0] if task_current else None,
                      tier=self._current_task[1] if task_current else None)
        return result

    def _nullable_detail(self, value, stamp):
        if not value["has_data"]:
            value["on_s"] = None
        # A stopped controller can leave an open stored interval. Its last
        # endpoint is still history, but a later read cannot claim it runs now.
        for item in value["sessions"]:
            observed = datetime.fromisoformat(item["observed_until"]).timestamp()
            expiry = self._expiries.get(value["device_id"])
            stale = stamp-observed > MAX_GAP_S or expiry is not None and stamp > expiry
            if item.get("ongoing") and stale:
                _, boundary = self.lanes._bounds(value["date"])
                item.update(end=item["observed_until"], ongoing=False,
                    continues_next_day=observed > boundary,
                    stop_reason="Geen recente waarneming; actuele toestand en werkelijke stoptijd onbekend",
                    stop_source="unknown", stop_confirmed=False)
        return value

    def detail(self, day, when):
        self._ensure(when)
        stamp = self.lanes._stamp(when)
        self._prune(stamp)
        result = self._nullable_detail(self.lanes.detail("heatpump", day, when), stamp)
        result.update(self._energy(result["date"]))
        for row in result["days"]:
            row.update(self._energy(row["date"]))
        sessions, totals, task_truncated = [], [], False
        for task, tier in TASKS:
            detail = self._nullable_detail(self.tasks.detail(self._task_id(task, tier), day, when), stamp)
            task_truncated = task_truncated or detail["sessions_truncated"]
            if detail["on_s"] is not None and detail["on_s"] > 0:
                totals.append({"task": task, "label": LABELS[task], "tier": tier, "on_s": detail["on_s"]})
            sessions += [{**item, "task": task, "label": LABELS[task], "tier": tier} for item in detail["sessions"]]
        result["task_sessions"] = sorted(sessions, key=lambda item: (item["segment_start"], item["task"], item["tier"]))
        result["task_totals"] = totals
        electrical = self._nullable_detail(self.electrical.detail("electrical_activity", day, when), stamp)
        for item in electrical["sessions"]:
            # This is an explicit duration band for display only, not a debounce or
            # compressor-cycle definition. No raw event or interval is merged.
            item["short_observed_period"] = item["duration_s"] <= MAX_GAP_S
        electrical.update(presentation_short_threshold_s=MAX_GAP_S,
                          note="Afzonderlijke gemeten elektrische perioden; korte perioden blijven zichtbaar. Starts/stops en meetgaten zijn onveranderd en bewijzen geen compressorstarts.")
        result["electrical_activity"] = electrical
        result["native_evidence"] = self.native_evidence.detail(result["date"])
        result["task_sessions_truncated"] = task_truncated
        result["sg"] = {key: self._nullable_detail(self.lanes.detail("sg_"+key, day, when), stamp)
                        for key in ("request", "contact", "received")}
        result["note"] = ("Actieve tijd is waargenomen native activiteit of elektrisch verbruik boven de ingestelde meetdrempel. "
                          "Dit meet geen continue compressorwerking. kWh is de integraal van volledige actuele vermogensmetingen; "
                          "SG-aanvraag, contact en ontvangen status staan afzonderlijk en bewijzen geen extra warmte of besparing.")
        return result

    def pause_recording(self, reason="Registratie onderbroken bij herladen/afsluiten; geen uitschakeling bevestigd"):
        self.lanes.pause_recording(reason)
        self.tasks.pause_recording(reason)
        self.electrical.pause_recording(reason)
        self.native_evidence.pause()
        self._last_energy = self._last_stamp = self._current_task = None
        self._expiries = {}
        self.revision += 1

    def snapshot(self):
        return {"version": SCHEMA_VERSION, "timezone": self.timezone_name, "binding": self.binding,
                "lanes": self.lanes.snapshot(), "tasks": self.tasks.snapshot(), "energy_days": deepcopy(self.energy_days),
                "electrical": self.electrical.snapshot(), "native_evidence": self.native_evidence.snapshot()}

    def restore(self, data, when):
        """Restore finite retained evidence, never a live continuity anchor."""
        if data is None or data == {}:
            return True
        if not isinstance(data, dict) or data.get("version") != SCHEMA_VERSION:
            raise ValueError("Warmtepomphistoriek heeft een onbekende opslagversie")
        if data.get("timezone") != self.timezone_name:
            raise ValueError("Tijdzone van warmtepomphistoriek verschilt; bewaarde dagtotalen niet opnieuw geïnterpreteerd")
        stamp = self.lanes._stamp(when)
        models = []
        for field, configs in (("lanes", LANES), ("tasks", {self._task_id(*key): LABELS[key[0]] for key in TASKS})):
            raw = data.get(field)
            if (not isinstance(raw, dict) or raw.get("version") != 1 or raw.get("timezone") != self.timezone_name
                    or not isinstance(raw.get("devices"), dict)):
                raise ValueError("Warmtepomphistoriek bevat ongeldige intervallen")
            for lane, row in raw["devices"].items():
                if lane not in configs or not isinstance(row, dict) or not isinstance(row.get("days"), dict) or not isinstance(row.get("sessions"), list):
                    raise ValueError("Warmtepomphistoriek bevat een ongeldige reeks")
                self._validate_row(row, stamp)
            model = ConsumerHistory(self.timezone_name)
            model.restore(raw, {lane: self._config(name, str(data.get("binding", ""))[:256]) for lane, name in configs.items()}, when)
            if set(raw["devices"]) != set(model.devices):
                raise ValueError("Warmtepomphistoriek kon niet volledig worden hersteld")
            models.append(model)
        energy = data.get("energy_days")
        if not isinstance(energy, dict):
            raise ValueError("Warmtepomphistoriek bevat ongeldige energietotalen")
        cleaned = {}
        for day, agg in energy.items():
            try:
                parsed = date.fromisoformat(day)
                if parsed.isoformat() != day or not isinstance(agg, dict):
                    raise ValueError
                kwh, known = _number(agg.get("energy_kwh")), _number(agg.get("energy_known_s"))
                start, end = self.lanes._bounds(day)
                if kwh is None or known is None or not 0 <= known <= end-start or not 0 <= kwh <= known*MAX_POWER_W/3600000 + 0.000001:
                    raise ValueError
                cleaned[day] = {"energy_kwh": kwh, "energy_known_s": known}
            except (ValueError, TypeError, OverflowError):
                raise ValueError("Warmtepomphistoriek bevat ongeldige energietotalen") from None
        electrical = ConsumerHistory(self.timezone_name)
        raw_electrical = data.get("electrical")
        if raw_electrical is not None:
            if (not isinstance(raw_electrical, dict) or type(raw_electrical.get("version")) is not int
                    or raw_electrical["version"] != 1 or raw_electrical.get("timezone") != self.timezone_name
                    or not isinstance(raw_electrical.get("devices"), dict)
                    or set(raw_electrical["devices"])-{"electrical_activity"}):
                raise ValueError("Warmtepomphistoriek bevat ongeldige elektrische activiteit")
            for row in raw_electrical["devices"].values():
                if not isinstance(row, dict) or not isinstance(row.get("days"), dict) or not isinstance(row.get("sessions"), list):
                    raise ValueError("Warmtepomphistoriek bevat ongeldige elektrische activiteit")
                self._validate_row(row, stamp)
            electrical.restore(raw_electrical, {"electrical_activity": self._config("Gemeten elektrische activiteit", str(data.get("binding", ""))[:256])}, when)
        native_evidence = NativeProgrammeEvidence(self.lanes.zone)
        native_evidence.restore(data.get("native_evidence"), stamp)
        self.lanes, self.tasks = models
        self.electrical, self.native_evidence = electrical, native_evidence
        self.energy_days = cleaned
        self.binding = str(data.get("binding", ""))[:256]
        self._last_energy = self._last_stamp = self._current_task = None
        self._expiries = {}
        self.revision += 1
        self._prune(stamp)
        return True

    def _validate_row(self, row, stamp):
        """Reject corrupt nonempty data instead of overwriting retained proof."""
        try:
            for day, agg in row["days"].items():
                parsed = date.fromisoformat(day)
                left, right = self.lanes._bounds(day)
                on, known = _number(agg.get("on_s")), _number(agg.get("known_s"))
                if parsed.isoformat() != day or on is None or known is None or not 0 <= on <= known <= right-left+0.001:
                    raise ValueError
                for field in ("starts", "stops"):
                    value = agg.get(field)
                    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                        raise ValueError
            for session in row["sessions"]:
                left, right = _number(session.get("start")), _number(session.get("observed_until"))
                if left is None or right is None or not 0 <= left <= right <= stamp+60:
                    raise ValueError
                end = session.get("end")
                if end is not None and (_number(end) is None or not left <= _number(end) <= right):
                    raise ValueError
        except (ValueError, TypeError, AttributeError, OverflowError):
            raise ValueError("Warmtepomphistoriek bevat beschadigde meetintervallen") from None
