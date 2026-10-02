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

from .dhw import hygiene_schedule_active

CONTEXT_NORMAL = "normal"
CONTEXT_HEATING = "space_heating"
CONTEXT_COOLING = "space_cooling"
CONTEXT_DHW = "tapwater_heating"
CONTEXT_HYGIENE = "sterilization"
CONTEXT_UNKNOWN = "heatpump_unknown"

ACTIVE_CONTEXTS = {CONTEXT_HEATING, CONTEXT_COOLING, CONTEXT_DHW, CONTEXT_HYGIENE}


def _finite(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def _action(obj):
    if obj is None or str(getattr(obj, "state", "")).casefold() in {"unknown", "unavailable", ""}:
        return None
    attrs = getattr(obj, "attributes", {}) or {}
    value = attrs.get("hvac_action")
    if value is None:
        return ""
    return str(value).strip().casefold()


def classify_heatpump(runtime, local_now):
    """Classify only states backed by current HA/Panasonic state information."""
    dhw = getattr(runtime, "dhw", None)
    if dhw is not None and getattr(dhw, "configured", False):
        try:
            if hygiene_schedule_active(dhw.settings, local_now):
                return CONTEXT_HYGIENE, "Panasonic-sterilisatievenster actief"
        except Exception:
            pass
        reading = getattr(dhw, "reading", None)
        protection = str(getattr(reading, "protection_reason", "") or "").casefold()
        if any(word in protection for word in ("hygiëne", "hygiene", "sterili", "legionella", "disinfect")):
            return CONTEXT_HYGIENE, "Panasonic-hygiëne/sterilisatie gemeld"
        if bool(getattr(reading, "protected", False)):
            return CONTEXT_UNKNOWN, "Warmtepomp/DHW is beschermd of handmatig actief; functie niet als huishoudelijke basislast leren"

    hass = getattr(runtime, "hass", None)
    states = getattr(hass, "states", None)
    get = getattr(states, "get", lambda _entity: None)

    # A direct DHW hvac_action is the strongest tank-heating evidence.
    if dhw is not None and getattr(dhw, "configured", False):
        entity_id = getattr(dhw, "config", {}).get("target_entity")
        obj = get(entity_id) if entity_id else None
        action = _action(obj)
        if action in {"heating", "preheating", "heat", "dhw", "hot_water"}:
            return CONTEXT_DHW, "Panasonic meldt actieve tapwaterverwarming"

    climate = getattr(runtime, "smart_climate", None)
    settings = getattr(climate, "settings", {}) if climate is not None else {}
    zone_ids = list(settings.get("zone_entities", []) or [])
    actions = []
    unavailable = False
    for entity_id in zone_ids:
        obj = get(entity_id)
        action = _action(obj)
        if action is None:
            unavailable = True
            continue
        actions.append(action)

    if any(a in {"cooling", "precooling"} for a in actions):
        return CONTEXT_COOLING, "Panasonic meldt actieve ruimtekoeling"
    if any(a in {"heating", "preheating"} for a in actions):
        return CONTEXT_HEATING, "Panasonic meldt actieve ruimteverwarming"
    if any(a in {"defrosting", "unknown"} for a in actions):
        return CONTEXT_UNKNOWN, "Warmtepomp actief maar functie niet eenduidig"
    if zone_ids and unavailable and not actions:
        return CONTEXT_UNKNOWN, "Panasonic-ruimteactiviteit niet betrouwbaar beschikbaar"

    # Some supported Panasonic adapter versions expose AUTO as heat_cool while hvac_action
    # temporarily remains idle/off during a reported PUMP task.  A separately
    # configured task-direction source protects the household baseline without
    # inventing whether the task is HEAT or COOL or claiming compressor watts.
    if dhw is not None and hasattr(dhw, "space_activity_status"):
        try:
            busy, reason, relevant, source = dhw.space_activity_status()
        except (AttributeError, KeyError, TypeError, ValueError):
            busy, reason, relevant, source = None, "", False, {}
        raw = str(source.get("state") or "").strip().casefold()
        inactive = {part.strip().casefold() for part in str(
            getattr(dhw, "settings", {}).get("space_activity_inactive_states", "IDLE;WATER")
        ).split(";") if part.strip()}
        if source.get("valid") and raw == "water" and raw in inactive:
            return CONTEXT_UNKNOWN, "Panasonic meldt WATER als taakrichting; dit is geen bewijs van compressoractiviteit of vermogen"
        if relevant and busy is not False:
            return CONTEXT_UNKNOWN, reason or "Panasonic-ruimteactiviteit niet betrouwbaar eenduidig"

    return CONTEXT_NORMAL, "Geen actieve Panasonic verwarmings-/koelactie gemeld"


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
            return True
        except (AttributeError, TypeError, ValueError):
            self.samples = {key: [] for key in ACTIVE_CONTEXTS}
            self.days = {key: set() for key in ACTIVE_CONTEXTS}
            self.restore_note = "Warmtepompleermodel beschadigd; alleen dit model leert opnieuw."
            return False

    @staticmethod
    def _stable(rows, context, *, seconds=15, minimum=3):
        values = [(ts, watts) for ts, ctx, watts in rows if ctx == context and watts is not None]
        if len(values) < minimum or values[-1][0] - values[0][0] < seconds:
            return None
        tail = values[-6:]
        watts = [v for _, v in tail]
        med = statistics.median(watts)
        spread = max(watts) - min(watts)
        if spread > max(150.0, abs(med) * 0.12):
            return None
        return float(med)

    def observe(self, wall_ts, day, context, site_residual_w):
        """Observe measured residual; return True only when a transition is learned."""
        power = _finite(site_residual_w)
        if power is None or not 0 <= power <= 30000:
            return False
        wall_ts = _finite(wall_ts)
        if wall_ts is None:
            return False
        if self.last_wall_ts is not None and (wall_ts <= self.last_wall_ts or wall_ts-self.last_wall_ts > 120):
            self.recent.clear()
            self.pending = None
            self.last_context = None
        self.last_wall_ts = wall_ts
        context = context if context in ACTIVE_CONTEXTS | {CONTEXT_NORMAL, CONTEXT_UNKNOWN} else CONTEXT_UNKNOWN
        if context == CONTEXT_UNKNOWN:
            self.unknown_observations = min(1000000, self.unknown_observations + 1)

        previous_context = self.last_context
        if previous_context is not None and context != previous_context:
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
        values = self.samples.get(context, [])
        days = self.days.get(context, set())
        conf = self._confidence(values, days)
        # Planning estimate uses the median rather than an optimistic low value.
        # It is deliberately unavailable until there is at least preliminary proof.
        watts = (statistics.median(values)
                 if len(values) >= 4 and len(days) >= 2 and conf >= 0.50 else None)
        return HeatPumpEstimate(
            context, None if watts is None else round(float(watts), 1), round(conf, 3),
            len(values), len(days), self._status(conf, len(values)),
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
