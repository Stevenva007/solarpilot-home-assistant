"""Bounded local investigations of explicit sources; no control permissions.

Counters describe distinct source reports, never polling cycles. Stored counters
and report cursors survive restart, but current source validity does not. Advice
does not discover entities, repair bindings or change settings and actuators.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
import time

from .heatpump_budget import heatpump_power
from .sg_investigation import SGSessionResearch, assessment as sg_assessment


TOPICS = ("heatpump_meter", "wallbox_source", "pv_forecast", "consumer_meters")
MAX_SOURCES = 32
MAX_NEGATIVE_REPORTS = 64
MAX_COUNT = 1_000_000
NOTICE = ("SolarPilot onderzoekt lokaal de al gekoppelde meetbronnen en bewaart begrensd meetbewijs. "
          "Voorstellen veranderen geen instelling of apparaat. Een oorzaak of reparatie is pas bevestigd met passend meetbewijs; "
          "nieuwe software vraagt een afzonderlijke geteste update.")


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _count(value):
    value = _number(value)
    return max(0, min(MAX_COUNT, int(value))) if value is not None else 0


def _dict(value):
    return value if isinstance(value, dict) else {}


def _fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, default=str).encode()).hexdigest()[:32]


def _cursor_role(topic, role):
    """Only machine roles or opaque consumer identities may be dictionary keys."""
    if not isinstance(role, str):
        return False
    if topic == "consumer_meters":
        return (role.startswith("consumer_") and len(role) == 41
                and all(char in "0123456789abcdef" for char in role[9:]))
    return role in {"heatpump_meter": ("total", "supply1", "supply2"),
                    "wallbox_source": ("session",), "pv_forecast": ("actual_pv",)}.get(topic, ())


def _fresh(stamp, now, stale):
    stamp, stale = _number(stamp), _number(stale)
    return bool(stamp is not None and stamp > 0 and stale is not None
                and stale > 0 and -5 <= now - stamp <= stale)


def _item(topic, title, status, summary, next_action, *, evidence=(), hypotheses=(), proposals=(), metrics=None):
    return {"id": topic, "title": title, "status": status, "summary": summary,
            "next_action": next_action, "evidence": list(evidence)[:12],
            "hypotheses": list(hypotheses)[:6], "proposals": list(proposals)[:6],
            "metrics": metrics or {}}


def _proposal(topic, suffix, text, kind="measurement_check"):
    return {"id": topic + "." + suffix, "text": text, "kind": kind}


class LocalInvestigation:
    """Evaluate current diagnostics at most once per minute, including exports."""

    def __init__(self, runtime):
        self.r = runtime
        self.sg_research = SGSessionResearch()
        self.records = {}
        self.last_refresh = None
        self.valid_until = {}
        self.cached_context = {}
        self.cached = {"schema": 1, "read_only": True, "updated_at": None,
                       "items": [], "notice": NOTICE}

    def snapshot(self):
        return {"schema": 1, "records": deepcopy(self.records), "sg_sessions": self.sg_research.snapshot()}

    def restore(self, data):
        self.records = {}
        self.sg_research = SGSessionResearch()
        self.last_refresh = None
        self.valid_until = {}
        self.cached_context = {}
        self.cached = {"schema": 1, "read_only": True, "updated_at": None,
                       "items": [], "notice": NOTICE}
        if not isinstance(data, dict) or type(data.get("schema")) is not int or data["schema"] != 1:
            return
        self.sg_research.restore(data.get("sg_sessions"))
        for topic in TOPICS:
            raw = _dict(_dict(data.get("records")).get(topic))
            context = raw.get("context")
            if not isinstance(context, str) or len(context) != 32 or any(c not in "0123456789abcdef" for c in context):
                continue
            cursors = {}
            for role, value in list(_dict(raw.get("cursors")).items())[:MAX_SOURCES]:
                stamp = _number(value)
                if _cursor_role(topic, role) and stamp is not None and 0 < stamp <= time.time() + 5:
                    cursors[role] = stamp
            counts = {key: _count(_dict(raw.get("counts")).get(key))
                      for key in ("reports", "valid_reports", "negative_reports")}
            counts["valid_reports"] = min(counts["reports"], counts["valid_reports"])
            counts["negative_reports"] = min(counts["reports"], counts["negative_reports"])
            negatives = []
            for row in (raw.get("negatives") if isinstance(raw.get("negatives"), list) else [])[-MAX_NEGATIVE_REPORTS:]:
                row = _dict(row)
                value = _number(row.get("watts"))
                stamp = _number(row.get("stamp"))
                if value is not None and -100000 <= value < 0 and stamp is not None and 0 < stamp <= time.time() + 5:
                    negatives.append({"watts": value, "stamp": stamp})
            self.records[topic] = {"context": context, "cursors": cursors,
                                   "counts": counts, "negatives": negatives}

    def _contexts(self):
        r = self.r
        hp = _dict(getattr(getattr(r, "panasonic", None), "settings", None))
        wb = _dict(getattr(r, "wallbox_settings", None))
        forecast = getattr(r, "pv_forecast", None)
        settings = _dict(getattr(r, "settings", None))
        configs = _dict(getattr(r, "configs", None))
        meters = {key: value.get("power_entity") for key, value in configs.items() if isinstance(value, dict)}
        reserved = [{key: settings.get(key) for key in ("grid_entity", "pv_entity", "export_entity", "battery_power_entity")},
                    meters, wb.get("power_entity"),
                    {key: value.get("power_entity") for key, value in
                     _dict(getattr(getattr(r, "battery_fleet", None), "configs", None)).items() if isinstance(value, dict)}]
        return {
            "heatpump_meter": _fingerprint([{key: hp.get(key) for key in
                ("power_entity", "power_scope", "power_supply1_entity", "power_supply2_entity",
                 "split_power_confirmed", "power_supply_profile", "power_supply1_role", "power_supply2_role", "stale_s")}, reserved]),
            "wallbox_source": _fingerprint(wb),
            "pv_forecast": _fingerprint([settings.get("pv_entity"),
                getattr(getattr(forecast, "source", None), "refs", {}),
                getattr(getattr(forecast, "source", None), "entry_id", None),
                getattr(forecast, "settings", {})]),
            "consumer_meters": _fingerprint([meters, reserved, hp, wb.get("enabled"), settings.get("stale_s")]),
        }

    def _record(self, topic, context):
        if self.records.get(topic, {}).get("context") != context:
            self.records[topic] = {"context": context, "cursors": {},
                                   "counts": {"reports": 0, "valid_reports": 0, "negative_reports": 0}, "negatives": []}
        return self.records[topic]

    def _observe(self, record, role, stamp, now, stale, *, valid=False, negative=None):
        """A real, fresh source report can advance one diagnostic cursor once."""
        if not _fresh(stamp, now, stale) or not isinstance(role, str):
            return
        stamp = float(stamp)
        cursors = record["cursors"]
        if stamp <= cursors.get(role, 0) or role not in cursors and len(cursors) >= MAX_SOURCES:
            return
        cursors[role] = stamp
        for key, include in (("reports", True), ("valid_reports", valid is True),
                             ("negative_reports", negative is not None)):
            if include:
                record["counts"][key] = min(MAX_COUNT, record["counts"][key] + 1)
        if negative is not None:
            record["negatives"] = (record["negatives"] + [{"watts": negative, "stamp": stamp}])[-MAX_NEGATIVE_REPORTS:]

    def _source(self, entity, now, stale):
        """Read exactly one selected W/kW source without inventing freshness."""
        obj = self.r.hass.states.get(entity) if isinstance(entity, str) and entity else None
        attrs = _dict(getattr(obj, "attributes", None))
        if obj is None or any(attrs.get(k) for k in ("restored", "estimated", "is_estimated")):
            return None, None
        if any(word in str(attrs.get("friendly_name", "")).casefold() for word in ("geschat", "estimated")):
            return None, None
        value = _number(getattr(obj, "state", None))
        unit = attrs.get("unit_of_measurement")
        stamp = self.r._reported_wall(obj)
        if value is None or unit not in ("W", "kW") or not _fresh(stamp, now, stale):
            return None, None
        value *= 1000 if unit == "kW" else 1
        if not math.isfinite(value) or not 0 <= value <= 100000:
            return None, None
        return value, stamp

    def _heatpump(self, now, record, native):
        topic = "heatpump_meter"
        cfg = _dict(getattr(getattr(self.r, "panasonic", None), "settings", None))
        configured = any(cfg.get(k) for k in ("power_entity", "power_supply1_entity", "power_supply2_entity"))
        power = heatpump_power(self.r, now_wall=now)
        sources = power.get("supplies") or {"total": power}
        stale = _number(cfg.get("stale_s")) or 120
        current_negative = False
        for role, reading in sources.items():
            # Negative raw watts are diagnostic evidence only. Restored,
            # estimated, unsupported-unit and stale reports cannot contribute.
            rejection = reading.get("rejection_reason")
            diagnostic = rejection in (None, "negative")
            watts = _number(reading.get("source_watts"))
            negative = watts if diagnostic and watts is not None and -100000 <= watts < 0 else None
            if diagnostic:
                current_negative = current_negative or (negative is not None and _fresh(reading.get("source_reported_wall"), now, stale))
                self._observe(record, role, reading.get("source_reported_wall"), now, stale,
                              valid=reading.get("valid") is True, negative=negative)
        complete = power.get("valid") is True and power.get("complete") is True
        if complete:
            self.valid_until[topic] = min(row["measured_wall"] + stale for row in sources.values())
        metrics = {**record["counts"], "complete_current": complete,
                   "current_w": power.get("watts") if complete else None,
                   "source_count": len(sources), "current_reason": power.get("reason", "")}
        evidence = [f'{record["counts"]["reports"]} verschillende actuele bronrapporten onderzocht; '
                    f'{record["counts"]["negative_reports"]} rapporten met negatief vermogen.']
        for role, reading in list(sources.items())[:3]:
            value = _number(reading.get("source_watts"))
            evidence.append(f'{role}: ' + (f'bronwaarde {value:g} W; ' if value is not None else '') +
                            (reading.get("reason") or "actuele geldige deelmeting"))
        hypotheses = []
        proposals = []
        recent_negatives = [row for row in record["negatives"] if 0 <= now-row["stamp"] <= 7*86400]
        negative_values = [row["watts"] for row in recent_negatives]
        if current_negative and len(negative_values) >= 5 and all(-20 <= value < 0 for value in negative_values):
            metrics.update(negative_min_w=min(negative_values), negative_max_w=max(negative_values))
            metrics.update(negative_first_reported_at=min(row["stamp"] for row in recent_negatives),
                           negative_last_reported_at=max(row["stamp"] for row in recent_negatives))
            hypotheses.append("Een kleine meetafwijking bij laag vermogen is mogelijk. Dit bewijst geen offset, stroomrichting of aansluitfout.")
            proposals.append(_proposal(topic, "low_power_comparison", "Vergelijk de bestaande meter bij laag en bij duidelijk positief verbruik met een onafhankelijke meting; pas geen tekenomkering, absolute waarde of nulcorrectie toe."))
        if not configured:
            return _item(topic, "Warmtepompmeting", "not_configured", "Geen warmtepompvermogensbron gekoppeld.",
                         "Koppel en bevestig de dekking van een eigen meter als die beschikbaar is.", evidence=evidence,
                         proposals=[_proposal(topic, "coverage", "Controleer welke gekoppelde meter het volledige toestel of afzonderlijke voedingen omvat; geen automatische bronkeuze.")], metrics=metrics)
        if complete:
            return _item(topic, "Warmtepompmeting", "observed_ok", "Het huidige volledige warmtepompverbruik is actueel gemeten.",
                         "Blijf nieuwe bronrapporten vergelijken; deze waarneming bevestigt geen fysieke reparatie of compressorwerking.",
                         evidence=evidence, hypotheses=hypotheses, proposals=proposals, metrics=metrics)
        proposals.append(_proposal(topic, "source_check", "Controleer actualiteit, W/kW-eenheid, meetrichting en dekking van de reeds gekoppelde warmtepompbronnen; ontbrekende delen blijven onbekend."))
        return _item(topic, "Warmtepompmeting", "check_needed", "Het huidige volledige warmtepompverbruik is niet betrouwbaar bekend.",
                     "Controleer de bestaande meetbron; langer verzamelen herstelt een onjuiste koppeling niet.",
                     evidence=evidence, hypotheses=hypotheses, proposals=proposals, metrics=metrics)

    def _wallbox(self, now, record, reading):
        from .learning_hub import wallbox_session_question
        topic = "wallbox_source"
        cfg = _dict(getattr(self.r, "wallbox_settings", None))
        if cfg.get("enabled") is not True or not cfg.get("session_mode_entity"):
            return _item(topic, "Wallbox-sessiebron", "not_configured", "Wallbox-onderzoek staat uit of de effectieve sessiebron ontbreekt.",
                         "Controleer de expliciete Wallbox-koppeling als de regeling gebruikt wordt.",
                         proposals=[_proposal(topic, "binding", "Koppel een gecontroleerde effectieve sessiebron; de laadstand Full Solar alleen bevestigt geen actieve zonnelaadsessie.")],
                         metrics=dict(record["counts"]))
        reading = reading if reading is not None else self.r._wallbox_reading()
        entity = cfg["session_mode_entity"]
        obj = self.r.hass.states.get(entity)
        attrs = _dict(getattr(obj, "attributes", None))
        stamp = self.r._reported_wall(obj)
        stale = _number(cfg.get("stale_s")) or 300
        usable = (reading.session_confirmed is True and reading.mode != "unknown"
                  and not any(attrs.get(k) for k in ("restored", "estimated", "is_estimated"))
                  and _fresh(stamp, now, stale))
        if not any(attrs.get(k) for k in ("restored", "estimated", "is_estimated")):
            self._observe(record, "session", stamp, now, stale, valid=usable)
        if usable:
            self.valid_until[topic] = stamp + stale
            cause, summary = "current_session", "De huidige gekoppelde sessiebron is actueel en de melding wordt herkend."
        else:
            if any(attrs.get(k) for k in ("estimated", "is_estimated")):
                cause, summary = "estimated", "De gekoppelde sessiebron is als schatting gemarkeerd; geen bevestigde werkelijke sessiemelding."
            else:
                cause, summary = wallbox_session_question(self.r, now)
        return _item(topic, "Wallbox-sessiebron", "observed_ok" if usable else "check_needed", summary,
                     "Blijf nieuwe bronrapporten volgen; dit bewijst alleen de huidige sessiemelding." if usable else
                     "Controleer de bestaande bron en haar statuslijsten; een oude melding krijgt geen extra geldigheid.",
                     evidence=[f'{record["counts"]["reports"]} verschillende actuele sessierapporten onderzocht; '
                               f'{record["counts"]["valid_reports"]} herkende meldingen.', f"Actuele bronbeoordeling: {cause}."],
                     proposals=[] if usable else [_proposal(topic, "source_check", "Vergelijk de reeds gekoppelde sessiesensor met werkelijk laden, stoppen en manueel laden; controleer tijdstip en herkenning van iedere melding.")],
                     metrics={**record["counts"], "cause": cause, "current_session_confirmed": usable})

    def _pv(self, now, record, quality, pv):
        topic = "pv_forecast"
        forecast = getattr(self.r, "pv_forecast", None)
        cfg = _dict(getattr(forecast, "settings", None))
        cached = _dict(getattr(forecast, "cached", None))
        q = _dict(quality.get("last_7d"))
        model = _dict(cached.get("model"))
        entity = _dict(getattr(self.r, "settings", None)).get("pv_entity")
        stale = _dict(getattr(self.r, "settings", None)).get("stale_s", 120)
        value, stamp = self._source(entity, now, stale)
        self._observe(record, "actual_pv", stamp, now, stale, valid=value is not None)
        samples = _count(q.get("pv_daylight_samples"))
        mae, bias = _number(q.get("pv_daylight_mae_w")), _number(q.get("pv_daylight_bias_w"))
        warning = str(cached.get("warning") or getattr(getattr(forecast, "source", None), "warning", ""))[:600]
        metrics = {**record["counts"], "daylight_samples_7d": samples,
                   "daylight_mae_w": mae, "daylight_bias_w": bias,
                   "calibration_enabled": cfg.get("calibration_enabled") is True,
                   "calibration_accepted": _count(model.get("accepted")),
                   "calibration_rejected": _count(model.get("rejected")),
                   "comparable_days": _count(cached.get("comparable_days")),
                   "current_actual_w": value}
        evidence = [f"{samples} daglichtvergelijkingen in de bestaande meetkwaliteit van zeven dagen."]
        if samples and mae is not None:
            evidence.append(f"Gemiddelde absolute afwijking {mae:g} W; " +
                            (f"gemeten min voorspeld gemiddeld {bias:g} W." if bias is not None else "richting onbekend."))
            evidence.append("Deze bestaande historische score kan meerdere broncontexten bevatten; een nieuwe koppeling is hiermee niet afzonderlijk getoetst.")
        if warning:
            evidence.append("Bestaande forecastbronmelding: " + warning)
        proposals = [_proposal(topic, "comparisons", "Vergelijk ruwe en gecorrigeerde voorspelling met gemeten PV op overeenkomende tijdstippen en dagdelen; beoordeel brondekking voordat een extra correctie wordt voorgesteld.", "data_review")]
        if not entity or cfg.get("enabled") is not True:
            status, summary = "not_configured", "PV-meting of voorspelling is niet ingeschakeld en gekoppeld voor dit onderzoek."
        elif warning or samples >= 12 and mae is not None and mae > 700:
            status, summary = "check_needed", "De beschikbare PV-vergelijking of forecastbron vraagt verder onderzoek."
        else:
            status, summary = "collecting", "Nieuwe PV-metingen en bestaande daglichtvergelijkingen worden gevolgd."
        return _item(topic, "PV-voorspelling", status, summary,
                     "Blijf vergelijken met echte daglichtmetingen; pas geen vaste factor toe op basis van deze score alleen.",
                     evidence=evidence, hypotheses=["Wolken, schaduw en bronverschillen zijn mogelijke verklaringen; de foutscore onderscheidt hun oorzaak niet."]
                     if samples and mae is not None and mae > 700 else [], proposals=proposals, metrics=metrics)

    def _consumers(self, now, record):
        topic = "consumer_meters"
        configs = _dict(getattr(self.r, "configs", None))
        missing, invalid, valid, stamps = [], [], [], []
        stale = _number(_dict(getattr(self.r, "settings", None)).get("stale_s")) or 120
        for key, cfg in list(configs.items())[:MAX_SOURCES]:
            if not isinstance(cfg, dict):
                continue
            name = str(cfg.get("name") or key)[:100]
            entity = cfg.get("power_entity")
            if not entity:
                missing.append(name)
                continue
            value, stamp = self._source(entity, now, stale)
            dedicated = self.r._reclaim_meter(key)
            if not dedicated:
                value, stamp = None, None
            # Export anonymization handles known entity/consumer fields, not
            # arbitrary dict keys. Use a stable source-specific opaque role so
            # private consumer IDs never enter the persisted cursor map.
            role = "consumer_" + _fingerprint([str(key), entity])
            self._observe(record, role, stamp, now, stale, valid=value is not None)
            if value is None:
                invalid.append(name)
            else:
                valid.append(name)
                stamps.append(stamp)
        unexamined = max(0, len(configs)-MAX_SOURCES)
        if configs and not unexamined and not missing and not invalid and valid:
            self.valid_until[topic] = min(stamps) + stale
        status = "not_configured" if not configs or missing else "check_needed" if invalid else "collecting" if unexamined else "observed_ok"
        evidence = [f"{len(valid)} actuele eigen meters; {len(missing)} ontbrekende en {len(invalid)} onbruikbare gekoppelde meters."]
        if missing:
            evidence.append("Geen eigen meter: " + ", ".join(missing[:10]) + ".")
        if invalid:
            evidence.append("Gekoppelde meter niet bruikbaar: " + ", ".join(invalid[:10]) + ".")
        if unexamined:
            evidence.append(f"{unexamined} verbruikers vallen buiten de begrensde lokale onderzoekslijst; geen volledige meetdekking bevestigd.")
        return _item(topic, "Verbruikersmetingen", status,
                     "De onderzochte gekoppelde verbruikersmeters zijn nu bruikbaar." if status == "observed_ok" else
                     "Werkelijk verbruik blijft onbekend waar een eigen betrouwbare meter ontbreekt.",
                     "Blijf nieuwe meterrapporten volgen." if status == "observed_ok" else
                     "Koppel een beschikbare eigen meter expliciet of controleer de bestaande koppeling.",
                     evidence=evidence, proposals=[] if status == "observed_ok" else
                     [_proposal(topic, "dedicated", "Controleer per toestel een eigen niet-overlappende W/kW-meter. Geschat nominaal vermogen is geen gemeten energie of programmafase.")],
                     metrics={**record["counts"], "valid_meters": len(valid), "missing_meters": len(missing), "invalid_meters": len(invalid),
                              "configured_count": len(configs), "examined_count": min(MAX_SOURCES, len(configs)), "unexamined_count": unexamined})

    def _current_valid(self, topic, now):
        """Revoke a cached source claim when its current source becomes invalid."""
        if topic == "heatpump_meter":
            power = heatpump_power(self.r, now_wall=now)
            return power.get("valid") is True and power.get("complete") is True
        if topic == "wallbox_source":
            cfg = _dict(getattr(self.r, "wallbox_settings", None))
            entity = cfg.get("session_mode_entity")
            obj = self.r.hass.states.get(entity) if entity else None
            attrs = _dict(getattr(obj, "attributes", None))
            reading = self.r._wallbox_reading()
            return bool(cfg.get("enabled") is True and reading.session_confirmed is True
                        and reading.mode != "unknown" and not any(attrs.get(k) for k in ("restored", "estimated", "is_estimated"))
                        and _fresh(self.r._reported_wall(obj), now, cfg.get("stale_s", 300)))
        if topic == "consumer_meters":
            configs = _dict(getattr(self.r, "configs", None))
            if not configs or len(configs) > MAX_SOURCES:
                return False
            stale = _dict(getattr(self.r, "settings", None)).get("stale_s", 120)
            return all(isinstance(cfg, dict) and self.r._reclaim_meter(key)
                       and self._source(cfg.get("power_entity"), now, stale)[0] is not None
                       for key, cfg in configs.items())
        return False

    def overview(self, now=None):
        """Cached presentation expires; it never regains validity after restore."""
        result = deepcopy(self.cached)
        now = _number(now)
        now = now if now is not None and now > 0 else time.time()
        contexts = self._contexts()
        for item in result["items"]:
            topic = item.get("id")
            if topic not in TOPICS:
                continue
            if item.get("status") == "observed_ok" and (now > self.valid_until.get(topic, 0)
                    or contexts.get(topic) != self.cached_context.get(topic) or not self._current_valid(topic, now)):
                item.update(status="collecting", summary="De eerdere geldige bronwaarneming is niet meer actueel bevestigd.",
                            next_action="Wacht op de volgende actuele broncontrole; oude meetgegevens blijven alleen historisch bewijs.")
                if topic == "heatpump_meter":
                    item["metrics"].update(complete_current=False, current_w=None)
                if topic == "wallbox_source":
                    item["metrics"]["current_session_confirmed"] = False
        if result["updated_at"] is not None:
            result["items"].append(sg_assessment(self.r, now, research=self.sg_research))
        return result

    def refresh(self, now, native=None, pv=None, quality=None, wallbox_reading=None):
        now = _number(now)
        if now is None or now <= 0:
            return self.overview()
        if self.last_refresh is not None and 0 <= now - self.last_refresh < 60:
            return self.overview(now)
        self.last_refresh = now
        self.valid_until = {}
        contexts = self._contexts()
        records = {topic: self._record(topic, contexts[topic]) for topic in TOPICS}
        items = [self._heatpump(now, records["heatpump_meter"], _dict(native)),
                 self._wallbox(now, records["wallbox_source"], wallbox_reading),
                 self._pv(now, records["pv_forecast"], _dict(quality), _dict(pv)),
                 self._consumers(now, records["consumer_meters"])]
        self.cached_context = contexts
        self.cached = {"schema": 1, "read_only": True, "updated_at": now, "items": items, "notice": NOTICE}
        return self.overview(now)
