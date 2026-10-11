"""Conservative heat-pump activity classification and planning-only power learning.

This module never changes realtime electrical headroom.  It classifies clearly
observed Panasonic activity and learns an approximate electrical step from stable
P1+PV residual changes around starts/stops.  The estimate is evidence for
planning/diagnostics only; it is never a substitute for a physical W meter.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math
import statistics
import time


CONTEXT_NORMAL = "normal"
CONTEXT_HEATING = "space_heating"
CONTEXT_COOLING = "space_cooling"
CONTEXT_DHW = "tapwater_heating"
CONTEXT_HYGIENE = "sterilization"
CONTEXT_UNKNOWN = "heatpump_unknown"

ACTIVE_CONTEXTS = {CONTEXT_HEATING, CONTEXT_COOLING, CONTEXT_DHW, CONTEXT_HYGIENE}


def _finite(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _action(obj, stale_s=300):
    """Use reported activity only while its source is current and trustworthy."""
    if obj is None or str(getattr(obj, "state", "")).strip().casefold() in {"unknown", "unavailable", ""}:
        return None
    attrs = getattr(obj, "attributes", {}) or {}
    if attrs.get("restored"):
        return None
    stamp = getattr(obj, "last_reported", None)
    if stamp is None:
        stamp = getattr(obj, "last_updated", None)
    try:
        reported = stamp.timestamp()
        max_age = _finite(stale_s)
        if (isinstance(reported, bool) or not isinstance(reported, (int, float))
                or _finite(reported) is None or max_age is None or max_age < 0
                or not -5 <= time.time() - reported <= max_age):
            return None
    except (AttributeError, TypeError, ValueError, OSError, OverflowError):
        return None
    value = attrs.get("hvac_action")
    if value is None:
        return ""
    return str(value).strip().casefold()


def classify_heatpump(runtime, local_now):
    """Return the current task, independently of the selected programme."""
    evidence = classify_heatpump_evidence(runtime, local_now)
    return evidence["context"], evidence["reason"]


def classify_heatpump_evidence(runtime, local_now):
    """Keep reported tasks and meter-derived tasks in separate evidence tiers.

    The monitor's ``context`` remains the conservative SG/programme guard. It
    is deliberately not a statement of the current physical task and cannot
    turn a selected heating programme into a validated learning example.
    """
    monitor = getattr(runtime, "panasonic", None)
    if monitor is None:
        return {"context": CONTEXT_UNKNOWN, "reason": "Panasonic-bronnen niet gekoppeld",
                "tier": "unknown", "model_eligible": False}
    return classify_heatpump_observation(monitor.overview())


def classify_heatpump_observation(observed, *, now_wall=None):
    """Classify an existing source snapshot without rereading or changing it."""
    now = time.time() if now_wall is None else now_wall
    stale = _finite(observed.get("source_stale_s")) or 120.0

    def fresh(value, limit=None):
        stamp = None if isinstance(value, bool) else _finite(value)
        limit = _finite(limit) if limit is not None else stale
        return stamp is not None and limit is not None and limit > 0 and -5 <= now - stamp <= limit

    native = observed.get("native_task") or {}
    power = observed.get("power_activity") or {}
    task_context = observed.get("task_context") or {}
    defrost = observed.get("defrost") or {}
    result = {"context": CONTEXT_UNKNOWN, "reason": "Actuele warmtepomptaak niet bevestigd",
              "tier": "unknown", "model_eligible": False,
              "selected_program": observed.get("program"),
              "guard_context": observed.get("context", CONTEXT_UNKNOWN),
              "native_function": native.get("function"),
              "native_source": native.get("source", "none"),
              "native_observed_at": native.get("observed_at"),
              "derived_function": power.get("function"),
              "source": "none", "kind": "none", "observed_at": None}
    native_fresh = fresh(native.get("observed_at"), native.get("stale_s", stale))
    if ((native.get("conflict") and native_fresh)
            or (defrost.get("state") == "active" and fresh(defrost.get("observed_at"), defrost.get("stale_s", stale)))):
        return {**result, "reason": native.get("note") or "Ontdooien of tegenstrijdige native taken; geen eenduidige leercontext"}
    native_function = native.get("function")
    if (native_function in ACTIVE_CONTEXTS and native_fresh
            and native.get("inactive") is not True and native.get("verified_global_off") is not True
            and native.get("source") in ("native_hvac_action", "aquarea_poll")):
        return {**result, "context": native_function, "reason": native.get("label") or "Verse native bedrijfsactie",
                "tier": "confirmed", "model_eligible": True, "source": native["source"],
                "kind": "native_action", "observed_at": native["observed_at"]}
    native_inactive = native.get("inactive") is True and native_fresh
    scoped_tank_route = (native.get("source") == "aquarea_poll" and native.get("inactive_action") == "off"
                         and native.get("inactive_scope") == "space_circuit" and native.get("independent_tank_on") is True
                         and native.get("verified_global_off") is not True
                         and power.get("function_kind") == "tank_route" and power.get("function") == CONTEXT_DHW)
    native_veto = (native_fresh and native.get("verified_global_off") is True or
                   native_inactive and native.get("inactive_action") != "idle" and not scoped_tank_route)
    expected_sources = ("aquarea_entity",) if power.get("function_kind") == "tank_route" else ("native_program", "native_mode")
    supplies = power.get("supplies") or []
    fresh_supplies = (isinstance(supplies, list) and bool(supplies) and all(
        isinstance(row, dict) and row.get("valid") is True
        and _finite(row.get("watts")) is not None and _finite(row["watts"]) >= 0
        and fresh(row.get("observed_at"), power.get("stale_s", stale)) for row in supplies))
    threshold = _finite(power.get("threshold_w"))
    total = _finite(power.get("total_w"))
    active_main = (fresh_supplies and threshold is not None and threshold > 0
                   and total is not None and total >= threshold and power.get("activity_kind") in ("main", "mixed")
                   and any(row.get("role") == "main" and row.get("state") == "active"
                           and _finite(row.get("watts")) >= threshold for row in supplies))
    compatible_kind = (power.get("function_kind") == "tank_route" and power.get("function") == CONTEXT_DHW or
                       power.get("function_kind") == "selected_program" and power.get("function") in (CONTEXT_HEATING, CONTEXT_COOLING))
    if (not native_veto and power.get("complete") is True and power.get("active") is True
            and compatible_kind
            and active_main and fresh(power.get("observed_at"), power.get("stale_s", stale))
            and fresh(power.get("context_observed_at"), power.get("stale_s", stale))
            and task_context.get("function") == power.get("function")
            and task_context.get("kind") == power.get("function_kind")
            and task_context.get("source") == power.get("function_source")
            and task_context.get("source") in expected_sources
            and fresh(task_context.get("observed_at"), task_context.get("stale_s", stale))):
        return {**result, "context": power["function"], "reason": power.get("note") or "Taak afgeleid uit actuele meting en context",
                "tier": "derived", "source": power.get("function_source", "none"),
                "kind": power["function_kind"], "observed_at": power["observed_at"]}
    # Electrical uptake without a reliable function must not become ordinary
    # household demand, including heater-only or conflicting programme cases.
    if power.get("active") is True:
        return {**result, "reason": power.get("note") or "Elektrische activiteit zonder eenduidige taak"}
    if power.get("state") == "partial":
        return {**result, "reason": power.get("note") or "Warmtepompmeting onvolledig; normale basislast niet bevestigd"}
    # A complete inactive meter corroborates a fresh typed native idle or a
    # verified global OFF even while the selected programme remains heating.
    if (native_inactive
            and (native.get("inactive_action") == "idle" or
                 native.get("inactive_scope") == "global" and native.get("verified_global_off") is True)
            and power.get("complete") is True and power.get("active") is False
            and fresh(power.get("observed_at"), power.get("stale_s", stale))
            and power.get("state") in ("off", "basis")):
        return {**result, "context": CONTEXT_NORMAL, "reason": "Verse native rust en volledige inactieve vermogensmeting",
                "tier": "inactive", "model_eligible": True, "source": native.get("source", "none"),
                "kind": "native_action", "observed_at": min(native["observed_at"], power["observed_at"])}
    if native_inactive and native.get("inactive_scope") == "space_circuit":
        return {**result, "reason": "Inactieve ruimteactie bevestigt geen inactieve tank"}
    if (native_inactive and native.get("inactive_action") != "idle"
            and not (native.get("inactive_scope") == "global" and native.get("verified_global_off") is True)):
        return {**result, "reason": "Rustmelding zonder geverifieerd globaal UIT; normale basislast niet bevestigd"}
    # Diagnostic clients with an old pre-classified view retain the label,
    # without receiving validated model/planning eligibility.
    if "native_task" not in observed and observed.get("context") in ACTIVE_CONTEXTS:
        return {**result, "context": observed["context"], "reason": observed.get("status", "Oud contextbewijs zonder taakherkomst")}
    if observed.get("configured") is False:
        return {**result, "context": CONTEXT_NORMAL, "reason": "Geen warmtepompbronnen geconfigureerd",
                "tier": "inactive", "model_eligible": True}
    if (observed.get("context") == CONTEXT_NORMAL and observed.get("context_reliable") is True
            and fresh(observed.get("context_stamp"))):
        return {**result, "context": CONTEXT_NORMAL, "reason": observed.get("status", "Verse inactieve native bronnen"),
                "tier": "inactive", "model_eligible": True, "source": "native_inactive",
                "kind": "native_action", "observed_at": observed["context_stamp"]}
    return result


@dataclass(frozen=True)
class HeatPumpEstimate:
    context: str
    watts: float | None
    confidence: float
    samples: int
    days: int
    status: str


class HeatPumpActivityModel:
    """Learn bounded power steps around stable, explicit Panasonic transitions."""

    def __init__(self):
        self.samples = {key: [] for key in ACTIVE_CONTEXTS}
        self.days = {key: set() for key in ACTIVE_CONTEXTS}
        # Existing schema-1 samples stay intact. Their original records do not
        # distinguish chosen programmes from native actions; keep them as
        # historical evidence rather than silently relabelling them confirmed.
        self.confirmed_samples = {key: [] for key in ACTIVE_CONTEXTS}
        self.confirmed_days = {key: set() for key in ACTIVE_CONTEXTS}
        self.derived_observations = {key: 0 for key in ACTIVE_CONTEXTS}
        self.derived_examples = deque(maxlen=40)
        self.recent = deque(maxlen=36)  # ~3 minutes at a normal 5 s loop.
        self.pending = None
        self.last_context = None
        self.last_wall_ts = None
        self.unknown_observations = 0
        self.restore_note = ""

    def snapshot(self):
        return {
            "schema": 1,
            "samples": {k: list(v[-40:]) for k, v in self.samples.items()},
            "days": {k: sorted(v)[-60:] for k, v in self.days.items()},
            "unknown_observations": self.unknown_observations,
            "confirmed_samples": {k: list(v[-40:]) for k, v in self.confirmed_samples.items()},
            "confirmed_days": {k: sorted(v)[-60:] for k, v in self.confirmed_days.items()},
            "derived_observations": dict(self.derived_observations),
            "derived_examples": list(self.derived_examples),
        }

    def restore(self, data):
        if not data:
            return True
        if not isinstance(data, dict) or data.get("schema", 1) != 1:
            self.restore_note = "Warmtepompleermodel incompatibel; alleen dit model leert opnieuw."
            return False
        try:
            self.unknown_observations = max(0, min(1000000, int(data.get("unknown_observations", 0) or 0)))
            for key in ACTIVE_CONTEXTS:
                vals = []
                for value in (data.get("samples", {}) or {}).get(key, [])[-40:]:
                    number = _finite(value)
                    if number is not None and 150 <= number <= 15000:
                        vals.append(round(number, 1))
                self.samples[key] = vals
                raw_days = (data.get("days", {}) or {}).get(key, [])
                self.days[key] = {str(x)[:10] for x in raw_days[-60:] if isinstance(x, str)}
            self._restore_task_evidence(data)
            return True
        except (AttributeError, TypeError, ValueError):
            self.samples = {key: [] for key in ACTIVE_CONTEXTS}
            self.days = {key: set() for key in ACTIVE_CONTEXTS}
            self.confirmed_samples = {key: [] for key in ACTIVE_CONTEXTS}
            self.confirmed_days = {key: set() for key in ACTIVE_CONTEXTS}
            self.restore_note = "Warmtepompleermodel beschadigd; alleen dit model leert opnieuw."
            return False

    def _restore_task_evidence(self, data):
        """Optional new provenance cannot invalidate the older saved model."""
        def rows(field, key):
            mapping = data.get(field)
            values = mapping.get(key) if isinstance(mapping, dict) else None
            return values if isinstance(values, list) else []

        counters = data.get("derived_observations")
        for key in ACTIVE_CONTEXTS:
            self.confirmed_samples[key] = [round(value, 1) for raw in rows("confirmed_samples", key)[-40:]
                if (value := _finite(raw)) is not None and 150 <= value <= 15000]
            self.confirmed_days[key] = {x[:10] for x in rows("confirmed_days", key)[-60:] if isinstance(x, str)}
            count = _finite(counters.get(key)) if isinstance(counters, dict) else None
            self.derived_observations[key] = max(0, min(1000000, int(count or 0)))
        self.derived_examples.clear()
        examples = data.get("derived_examples")
        for row in examples[-40:] if isinstance(examples, list) else []:
            if not isinstance(row, dict) or row.get("context") not in ACTIVE_CONTEXTS or row.get("tier") != "derived":
                continue
            power, stamp = _finite(row.get("residual_w")), _finite(row.get("wall_ts"))
            if power is None or not 0 <= power <= 30000 or stamp is None:
                continue
            self.derived_examples.append({"wall_ts": stamp, "day": str(row.get("day", ""))[:10],
                "context": row["context"], "residual_w": round(power, 1), "tier": "derived",
                "source": str(row.get("source", "none"))[:40], "kind": str(row.get("kind", "none"))[:40],
                "observed_at": _finite(row.get("observed_at"))})

    def interrupt(self):
        """A source/provenance gap cannot be bridged into a learned transition."""
        self.recent.clear()
        self.pending = None
        self.last_context = None

    @staticmethod
    def _stable(rows, context, *, seconds=15, minimum=3):
        values = []
        for ts, ctx, watts in reversed(rows):
            if ctx != context or watts is None:
                break
            values.append((ts, watts))
        values.reverse()
        if len(values) < minimum or values[-1][0] - values[0][0] < seconds:
            return None
        tail = values[-6:]
        watts = [v for _, v in tail]
        med = statistics.median(watts)
        spread = max(watts) - min(watts)
        if spread > max(150.0, abs(med) * 0.12):
            return None
        return float(med)

    def observe(self, wall_ts, day, context, site_residual_w, *, evidence="confirmed", detail=None):
        """Observe measured residual; return True only when a transition is learned."""
        power = _finite(site_residual_w)
        if power is None or not 0 <= power <= 30000:
            self.interrupt()
            return False
        wall_ts = _finite(wall_ts)
        if wall_ts is None:
            self.interrupt()
            return False
        if self.last_wall_ts is not None and (wall_ts <= self.last_wall_ts or wall_ts-self.last_wall_ts > 120):
            self.interrupt()
        self.last_wall_ts = wall_ts
        context = context if context in ACTIVE_CONTEXTS | {CONTEXT_NORMAL, CONTEXT_UNKNOWN} else CONTEXT_UNKNOWN
        if evidence == "derived" and context in ACTIVE_CONTEXTS:
            self.derived_observations[context] = min(1000000, self.derived_observations[context] + 1)
            detail = detail or {}
            self.derived_examples.append({"wall_ts": wall_ts, "day": str(day)[:10], "context": context,
                "residual_w": round(power, 1), "tier": "derived", "source": detail.get("source", "none"),
                "kind": detail.get("kind", "none"), "observed_at": detail.get("observed_at")})
        if (evidence not in ("confirmed", "inactive") or context == CONTEXT_UNKNOWN
                or evidence == "inactive" and context != CONTEXT_NORMAL):
            # A gap in task proof interrupts both edges of a transition. A
            # derived example cannot later become a confirmed start/stop step.
            self.interrupt()
            if evidence != "derived":
                self.unknown_observations = min(1000000, self.unknown_observations + 1)
            return False

        previous_context = self.last_context
        if previous_context is not None and context != previous_context:
            self.pending = None
            before = self._stable(self.recent, previous_context)
            if before is not None and (
                previous_context == CONTEXT_NORMAL and context in ACTIVE_CONTEXTS
                or context == CONTEXT_NORMAL and previous_context in ACTIVE_CONTEXTS
            ):
                self.pending = {
                    "from": previous_context, "to": context, "before_w": before,
                    "started": wall_ts, "day": str(day)[:10],
                }
        self.last_context = context
        self.recent.append((wall_ts, context, power))

        pending = self.pending
        if not pending or context != pending["to"]:
            return False
        if wall_ts - float(pending["started"]) < 20:
            return False
        after = self._stable(self.recent, context, seconds=15, minimum=3)
        if after is None:
            return False

        if pending["from"] == CONTEXT_NORMAL:
            active_context = context
            delta = after - float(pending["before_w"])
        else:
            active_context = pending["from"]
            delta = float(pending["before_w"]) - after
        self.pending = None

        # Conservative: reject tiny steps, electric-resistance sized anomalies and
        # unstable/implausible transitions.  Household switching can still coincide,
        # so confidence grows only across repeated days.
        if active_context not in ACTIVE_CONTEXTS or not 250 <= delta <= 10000:
            return False
        self.samples[active_context] = (self.samples[active_context] + [round(delta, 1)])[-40:]
        self.days[active_context].add(str(day)[:10])
        self.confirmed_samples[active_context] = (self.confirmed_samples[active_context] + [round(delta, 1)])[-40:]
        self.confirmed_days[active_context].add(str(day)[:10])
        return True

    @staticmethod
    def _confidence(values, days):
        if not values:
            return 0.0
        sample_conf = min(1.0, len(values) / 6.0)
        day_conf = min(1.0, len(days) / 3.0)
        med = statistics.median(values)
        mad = statistics.median([abs(v - med) for v in values]) if len(values) > 1 else med
        consistency = max(0.25, 1.0 - mad / max(300.0, med))
        return min(0.92, (0.55 * sample_conf + 0.45 * day_conf) * consistency)

    @staticmethod
    def _status(confidence, samples):
        if not samples:
            return "Nog niet geleerd"
        if confidence < 0.35:
            return "Eerste metingen"
        if confidence < 0.75:
            return "Voorlopig"
        return "Betrouwbaar"

    def estimate(self, context):
        values = self.confirmed_samples.get(context, [])
        days = self.confirmed_days.get(context, set())
        conf = self._confidence(values, days)
        # Planning estimate uses the median rather than an optimistic low value.
        # It is deliberately unavailable until there is at least preliminary proof.
        watts = (statistics.median(values)
                 if len(values) >= 4 and len(days) >= 2 and conf >= 0.50 else None)
        status = self._status(conf, len(values))
        if not values and self.samples.get(context):
            status = "Historisch bewijs; actuele taakherkomst niet bevestigd"
        return HeatPumpEstimate(
            context, None if watts is None else round(float(watts), 1), round(conf, 3),
            len(values), len(days), status,
        )

    def overview(self):
        labels = {
            CONTEXT_HEATING: "Ruimteverwarming",
            CONTEXT_COOLING: "Ruimtekoeling",
            CONTEXT_DHW: "Tapwaterverwarming",
            CONTEXT_HYGIENE: "Legionella/sterilisatie",
        }
        return {
            "planning_only": True,
            "realtime_headroom_uses_estimate": False,
            "model_evidence": "confirmed_native_transitions",
            "historical_samples": {key: len(self.samples[key]) for key in ACTIVE_CONTEXTS},
            "derived": {"planning_eligible": False, "observations": dict(self.derived_observations),
                        "recent_examples": list(self.derived_examples)},
            "contexts": {
                **{
                    key: {"label": labels[key], **self.estimate(key).__dict__}
                    for key in (CONTEXT_HEATING, CONTEXT_COOLING, CONTEXT_DHW, CONTEXT_HYGIENE)
                },
                CONTEXT_UNKNOWN: {
                    "label": "Onbekende warmtepompactiviteit",
                    "context": CONTEXT_UNKNOWN,
                    "watts": None,
                    "confidence": 0.0,
                    "samples": self.unknown_observations,
                    "days": 0,
                    "status": "Classificatie onzeker" if self.unknown_observations else "Nog niet waargenomen",
                },
            },
            "note": (
                "Geschat warmtepompvermogen is uitsluitend classificatie/planningsbewijs. "
                "Realtime vrije netruimte gebruikt altijd de echte P1/PV-metingen en trekt deze schatting nooit af."
            ),
            "restore_note": self.restore_note,
        }
