"""Local learning evidence and a bounded, explicit decision inbox.

No device services, credentials, arbitrary entity discovery or code generation.
This module changes predictions only; comfort, permissions and safety stay owned
by the existing modules. Model approvals are not permissions to start appliances.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from datetime import date, datetime, timedelta
import hashlib
import json
import logging
import math
import time

from .heatpump_learning import (
    ACTIVE_CONTEXTS, CONTEXT_NORMAL, CONTEXT_UNKNOWN, classify_heatpump_evidence,
)
from .const import VERSION
from .investigation import LocalInvestigation


BASELINE_SETTLING_S = 120.0
_LOGGER = logging.getLogger(__name__)


def number(value):
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (ValueError, TypeError, OverflowError):
        return None
    return out if math.isfinite(out) else None


def local_time(runtime):
    from zoneinfo import ZoneInfo
    zone = getattr(getattr(runtime.hass, "config", None), "time_zone", "Europe/Brussels")
    try:
        return datetime.now(ZoneInfo(zone))
    except (ValueError, KeyError):
        return datetime.now().astimezone()


def wallbox_session_question(runtime, now):
    """Explain the existing session proof failure without changing its policy."""
    entity = runtime.wallbox_settings.get("session_mode_entity")
    if not entity:
        return "missing_binding", (
            "De instelling Full Solar kan blijven staan tijdens manueel laden. Koppel onder Opslag & laden → Wallbox een gecontroleerde effectieve sessiesensor. "
            "Tot dan gebruikt SolarPilot alleen echte restinjectie; comfort blijft werken. Geen antwoord geeft geen overnametoestemming.")
    obj = runtime.hass.states.get(entity)
    if obj is None:
        cause, explanation = "missing_source", "De effectieve sessiesensor is al gekoppeld, maar de gekoppelde bron ontbreekt in Home Assistant."
    elif (str(obj.state).strip().casefold() in ("unknown", "unavailable", "")
            or (getattr(obj, "attributes", {}) or {}).get("restored")):
        cause, explanation = "unavailable", "De effectieve sessiesensor is al gekoppeld, maar meldt onbekend, onbeschikbaar of alleen een herstelde waarde."
    else:
        source_stamp = runtime._reported_wall(obj)
        stale = runtime.wallbox_settings.get("stale_s", 300)
        if source_stamp is None:
            cause, explanation = "timestamp_unknown", "De effectieve sessiesensor is al gekoppeld, maar heeft geen betrouwbaar rapporttijdstip."
        elif now - source_stamp > stale:
            cause, explanation = "stale", f"De effectieve sessiesensor is al gekoppeld, maar het laatste rapport is ouder dan de ingestelde grens van {stale:g} seconden."
        else:
            cause, explanation = "unrecognized_or_conflicting", (
                "De effectieve sessiesensor is al gekoppeld en actueel, maar de sessiemelding wordt niet herkend of is strijdig met de ingestelde laadstand.")
    return cause, (
        explanation + " Controleer onder Opslag & laden → Wallbox de bestaande bron, haar actualiteit en de ingestelde statuslijsten. "
        "De instelling Full Solar alleen bevestigt geen effectieve zonnelaadsessie. Tot er betrouwbare sessiegegevens zijn, gebruikt SolarPilot alleen echte restinjectie; "
        "comfort blijft werken. Geen antwoord geeft geen overnametoestemming.")


def measured_baseline(r, local_now, monotonic):
    """Return a synchronous, measurement-backed residual, or an explicit unknown.

    Only already modelled owned loads/EV are subtracted. Ungrouped heat-pump or
    household demand remains residual, not silently subtracted or replaced with
    an inferred wattage. Energy (kWh) counters cannot be substituted for power.
    """
    refs, stamps, parts = [], [], {}
    checked_at = local_now.timestamp()

    def fail(code, message, **detail):
        return {"valid": False, "watts": None, "code": code, "reason": message,
                "sources": list(refs), "parts": dict(parts), "context": "unknown",
                "checked_at": checked_at, **detail}

    def power(entity, limit=120):
        if not entity or entity in refs:
            return None
        obj = r.hass.states.get(entity)
        if obj is None:
            return None
        attrs = obj.attributes
        # Exclude declared estimates and known template sources, not merely
        # values that happen to disagree with our model.
        if attrs.get("restored") or attrs.get("estimated") is True or attrs.get("is_estimated") is True:
            return None
        if any(x in str(attrs.get("friendly_name", "")).casefold() for x in ("geschat", "estimated")):
            return None
        try:
            from homeassistant.helpers import entity_registry as er
            entry = getattr(er.async_get(r.hass), "async_get", lambda _: None)(entity)
            if getattr(entry, "platform", None) in ("template", "integration", "statistics", "derivative"):
                return None
        except (AttributeError, ImportError):
            pass
        value, stamp = r._power(entity, limit)
        if number(value) is None or stamp <= 0:
            return None
        refs.append(entity); stamps.append(stamp)
        return value

    grid = power(r.settings.get("grid_entity"))
    pv = power(r.settings.get("pv_entity"))
    if grid is None or pv is None or pv < 0:
        return fail("site_source", "Net/PV-bron ontbreekt, is te oud, dubbel of geen echte W/kW-meting.")
    if r.settings.get("grid_sign") == "separate":
        exp = power(r.settings.get("export_entity"))
        if exp is None or exp < 0 or grid < 0:
            return fail("site_source", "Gescheiden import/export-bronnen niet beide betrouwbaar.")
        grid -= exp
    elif r.settings.get("grid_sign") == "export_positive":
        grid = -grid
    parts.update(grid_w=grid, pv_w=pv)
    battery = 0.0
    if r.battery_fleet.settings.get("enabled") and r.battery_fleet.configured:
        # Multiple storage units need consistent, separately validated signed
        # readings. Keep the sample unknown rather than credit partial totals.
        return fail("battery_fleet", "Basislastcorrectie voor een batterijvloot nog niet gevalideerd; geen gedeeltelijk gemeten batterij aftrekken.")
    if r.settings.get("battery_power_entity"):
        value = power(r.settings.get("battery_power_entity"))
        if value is None:
            return fail("battery_source", "Batterijmeting ontbreekt voor de energiebalans.")
        battery = value if r.settings.get("battery_sign") == "discharge_positive" else -value
    parts["battery_discharge_signed_w"] = battery
    ev = 0.0
    if r.wallbox_settings.get("enabled"):
        ev = power(r.wallbox_settings.get("power_entity"))
        if ev is None or ev < 0:
            return fail("wallbox_source", "Wallboxmeting niet actueel/eenduidig; geen nul invullen en niet blind aftrekken.")
    parts["wallbox_w"] = ev
    owned, settling_since = 0.0, None
    for device_id, state in r.states.items():
        if not state.owned or not state.on:
            continue
        cfg = r.configs[device_id]
        if not state.available or state.fault or not r._dedicated_meter(device_id):
            return fail("consumer_source", "Beheerde last zonder betrouwbare exclusieve vermogensmeter; geen schatting als basislastmeting leren.")
        value = power(cfg.get("power_entity"))
        if value is None or value < 0:
            return fail("consumer_source", "Vermogen beheerde last onbekend/dubbel; basislastmeting overgeslagen.")
        owned += value
        last_on = number(getattr(state, "last_on", None))
        if last_on is not None and 0 <= monotonic-last_on < BASELINE_SETTLING_S:
            # All active meters still need validation. If several loads were
            # recognised, the most recent transition owns the latest end time.
            settling_since = max(settling_since, last_on) if settling_since is not None else last_on
    parts["owned_w"] = owned
    if settling_since is not None:
        elapsed = monotonic-settling_since
        started_at = checked_at-elapsed
        return fail("settling", "Last na inschakeling of herstel nog aan het stabiliseren; twee minuten geen basislastmeting.",
                    settling={"kind": "load_settling", "started_at": started_at,
                              "ends_at": started_at+BASELINE_SETTLING_S,
                              "remaining_s": math.ceil(BASELINE_SETTLING_S-elapsed)})
    if getattr(r, "pending", None) or getattr(r, "handover", None):
        # Feedback has no promised completion time. Do not present an actuator
        # timeout as a guaranteed end to the learning exclusion.
        starts = []
        pending = getattr(r, "pending", None)
        handover = getattr(r, "handover", None)
        for issued in (pending.get("issued") if isinstance(pending, dict) else None,
                       getattr(handover, "issued", None)):
            issued = number(issued)
            if issued is not None and issued <= monotonic:
                starts.append(checked_at-(monotonic-issued))
        return fail("settling", "Een opdracht of vermogensoverdracht wacht nog op terugmelding.",
                    settling={"kind": "command_feedback", "started_at": min(starts) if starts else None,
                              "ends_at": None, "remaining_s": None})
    if max(stamps)-min(stamps) > 120:
        return fail("source_alignment", "Bronrapporten liggen meer dan twee minuten uiteen.")
    base = grid + pv + battery - ev - owned
    if not 0 <= base <= 20000:
        return fail("balance", "De gemeten energiebalans is niet plausibel. Controleer bronkoppelingen/eenheden; geen negatief verbruik als nul leren.")
    context_evidence = classify_heatpump_evidence(r, local_now)
    context, context_reason = context_evidence["context"], context_evidence["reason"]
    return {"valid": True, "watts": round(base, 1), "code": "measured",
            "reason": "Gemeten restlast uit net + PV + batterijontlading − gemeten beheerde lasten − gemeten Wallbox.",
            "sources": refs, "parts": parts, "context": context, "checked_at": checked_at,
            "context_reason": context_reason,
            "context_evidence": context_evidence,
            "old_rule_would_skip": bool(ev > 100 or owned > 100),
            "note": "Warmtepompactiviteit wordt afzonderlijk geclassificeerd. Een geleerd warmtepompvermogen is alleen planningsbewijs en wordt nooit van realtime vrije netruimte afgetrokken."}


class LearningHub:
    """Persistent questions, model provenance and opt-in validated adaptation."""
    def __init__(self, runtime):
        self.r = runtime
        self.policy = {"sampling": "metered", "adaptation": "assisted", "notifications": False}
        self.answers = {}
        self.audit = deque(maxlen=150)
        self.days = {}
        self.last_attempt = 0.0
        self.last_refresh = 0.0
        self.last_notification = 0.0
        self.notification_signature = ""
        self._legacy_notice_pending = False
        self._notification_cleanup_dirty = False
        self._notification_cleanup_failed = False
        self.latest_sample = {"valid": False, "watts": None, "code": "initializing", "reason": "Eerste meetcontrole afwachten."}
        self.cached = {"models": [], "questions": [], "ready": False, "policy": dict(self.policy)}
        self.active_candidates = set()
        self.current_findings = []
        self.error = ""
        self.investigation = LocalInvestigation(runtime)
        self._unsupported_snapshot = None
        self._sampling_state_key = None
        self._sampling_state_since = None

    def snapshot(self):
        if self._unsupported_snapshot is not None:
            return deepcopy(self._unsupported_snapshot)
        return {"schema": 1, "policy": dict(self.policy), "answers": deepcopy(self.answers),
                "audit": list(self.audit), "days": deepcopy(self.days), "last_attempt": self.last_attempt,
                "last_notification": self.last_notification, "notification_signature": self.notification_signature,
                "active_candidates": sorted(self.active_candidates),
                "investigation": self.investigation.snapshot()}

    def restore(self, data):
        if not isinstance(data, dict):
            return
        if type(data.get("schema", 1)) is not int or data.get("schema", 1) != 1:
            self._unsupported_snapshot = deepcopy(data)
            self.error = "Opgeslagen leerversie niet ondersteund; oorspronkelijke opslag blijft ongewijzigd bewaard"
            return
        self._unsupported_snapshot = None
        self.investigation.restore(data.get("investigation"))
        policy = data.get("policy")
        policy = policy if isinstance(policy, dict) else {}
        for k, allowed in (("sampling", ("metered", "quiet")), ("adaptation", ("assisted", "automatic")), ("notifications", (False, True))):
            value = policy.get(k)
            if type(value) is type(allowed[0]) and value in allowed:
                self.policy[k] = value
        raw = data.get("answers", {})
        self.answers = {}
        for key, value in list(raw.items())[-100:] if isinstance(raw, dict) else []:
            if not isinstance(key, str) or not isinstance(value, dict):
                continue
            # A malformed optional expiry must not crash a future comparison.
            until = number(value.get("until"))
            self.answers[key[:160]] = {**value, "until": max(0, until or 0)}
        audit = data.get("audit")
        self.audit = deque([v for v in audit[-150:] if isinstance(v, dict)] if isinstance(audit, list) else [], maxlen=150)
        raw = data.get("days", {})
        if isinstance(raw, dict):
            for k, v in sorted((k, v) for k, v in raw.items() if isinstance(k, str))[-60:]:
                try:
                    if date.fromisoformat(k).isoformat() != k:
                        continue
                except ValueError:
                    continue
                if isinstance(v, dict):
                    self.days[k] = {str(c)[:40]: min(1000000, int(value)) for c, n in v.items()
                        if (value := number(n)) is not None and value >= 0 and value.is_integer()}
        candidates = data.get("active_candidates")
        self.active_candidates = {x[:32] for x in candidates[:48] if isinstance(x, str)} if isinstance(candidates, list) else set()
        self.last_notification = number(data.get("last_notification")) or 0
        self.notification_signature = str(data.get("notification_signature", ""))[:64]
        self._legacy_notice_pending = bool(self.notification_signature or self.last_notification
                                          or self.policy["notifications"])
        self.r.unified_planner.base_load.adaptive_enabled = self.policy["adaptation"] == "automatic"

    def observe(self, local_now, monotonic):
        r = self.r
        previous = self.latest_sample
        sample = measured_baseline(r, local_now, monotonic)
        self.latest_sample = sample
        stamp = time.time()
        model = r.unified_planner.base_load
        model.adaptive_enabled = self.policy["adaptation"] == "automatic"

        # Classify heat-pump activity every normal rule cycle. The learned watts
        # remain planning/diagnostic evidence and never change realtime headroom.
        if sample.get("valid"):
            context = sample.get("context", CONTEXT_UNKNOWN)
            if context == CONTEXT_NORMAL:
                predicted, confidence, _source = model.estimate(
                    local_now, r.planner_settings.get("base_load_min_days", 4))
                excess = float(sample["watts"]) - float(predicted)
                if confidence >= 0.25 and excess > max(900.0, float(predicted)):
                    sample["context"] = CONTEXT_UNKNOWN
                    sample["context_reason"] = (
                        f"Onverklaarde restlastpiek {excess:.0f} W boven het gewone profiel; "
                        "niet als huishoudelijke basislast geleerd"
                    )
                    sample["context_evidence"] = {**sample.get("context_evidence", {}),
                        "context": CONTEXT_UNKNOWN, "reason": sample["context_reason"],
                        "tier": "unknown", "model_eligible": False}
            context = sample.get("context", CONTEXT_UNKNOWN)
            if context in ACTIVE_CONTEXTS | {CONTEXT_NORMAL, CONTEXT_UNKNOWN}:
                detail = sample.get("context_evidence", {})
                r.heatpump_learning.observe(
                    stamp, local_now.date().isoformat(), context, sample["watts"],
                    evidence=detail.get("tier", "unknown"), detail=detail)
        else:
            r.heatpump_learning.interrupt()

        # A change in sampling state must also remove obsolete source findings
        # immediately; the normal 60-second presentation cache is too slow at a
        # short wait boundary. Countdown ticks alone do not rebuild all models.
        if any(previous.get(key) != sample.get(key) for key in
               ("valid", "code", "context", "reason", "context_reason")):
            self.last_refresh = 0
        self._sampling_status(stamp)

        if stamp-self.last_attempt < 900:
            return sample
        self.last_attempt = stamp
        code = sample["code"]
        if not r.planner_settings.get("base_load_learning", True):
            code = "learning_disabled"
        elif sample.get("valid") and sample.get("context") != CONTEXT_NORMAL:
            prefix = "heatpump_derived_" if sample.get("context_evidence", {}).get("tier") == "derived" else "heatpump_"
            code = prefix + str(sample.get("context") or CONTEXT_UNKNOWN)
        elif self.policy["sampling"] == "quiet" and sample.get("old_rule_would_skip"):
            code = "quiet_policy"
        elif sample["valid"]:
            accepted = model.observe(stamp, local_now, sample["watts"], contaminated=False)
            code = "accepted_corrected" if accepted and sample.get("old_rule_would_skip") else "accepted" if accepted else "sample_interval"
        day = local_now.date().isoformat()
        counters = self.days.setdefault(day, {})
        counters[code] = counters.get(code, 0) + 1
        cutoff = (local_now-timedelta(days=60)).date().isoformat()
        self.days = {d: x for d, x in self.days.items() if cutoff <= d <= day}
        if r.data_loaded:
            r.store.async_delay_save(r._snapshot, 60)
        return sample

    def _sampling_status(self, stamp):
        """Explain the current learning gate, without granting model eligibility."""
        sample = self.latest_sample
        code, reason = sample.get("code", "initializing"), sample.get("reason", "")
        state, severity, scope = "ready", "info", "baseline"
        detail = {}
        if not self.r.planner_settings.get("base_load_learning", True):
            state, code, reason = "disabled", "learning_disabled", "Basislastleren is uitgeschakeld."
        elif code == "initializing":
            state = "initializing"
        elif not sample.get("valid"):
            state = "transient_wait" if code == "settling" else "source_unusable"
            severity = "info" if code == "settling" else "attention"
            detail = sample.get("settling", {})
        elif sample.get("context") != CONTEXT_NORMAL:
            state, scope = "excluded", "heatpump_context"
            prefix = "heatpump_derived_" if sample.get("context_evidence", {}).get("tier") == "derived" else "heatpump_"
            code = prefix + str(sample.get("context") or CONTEXT_UNKNOWN)
            reason = sample.get("context_reason") or "Warmtepompcontext nog niet bruikbaar voor gewone basislast."
        elif self.policy["sampling"] == "quiet" and sample.get("old_rule_would_skip"):
            state, code = "excluded", "quiet_policy"
            reason = "Rustig-meetbeleid slaat dit meetmoment met actieve Wallbox of beheerde last over."
        key = (state, code, reason, detail.get("kind"))
        if key != self._sampling_state_key:
            self._sampling_state_key, self._sampling_state_since = key, sample.get("checked_at") or stamp
        started_at = detail.get("started_at") or self._sampling_state_since
        ends_at = number(detail.get("ends_at"))
        return {"state": state, "severity": severity, "scope": scope, "code": code,
                "reason": reason, "kind": detail.get("kind"),
                "started_at": started_at, "ends_at": ends_at,
                "remaining_s": max(0, math.ceil(ends_at-stamp)) if ends_at is not None else None,
                "last_checked_at": sample.get("checked_at"),
                "basis": "Actuele meetcontrole; leerpogingen worden afzonderlijk per kwartier geteld."}

    def _event(self, what, detail):
        self.audit.append({"time": datetime.now().astimezone().isoformat(), "event": what, "details": detail})
        self.r.analysis.event("learning", what + ": " + str(detail))

    def refresh(self, force=False):
        stamp = time.time()
        if not force and stamp-self.last_refresh < 60:
            self.cached["investigation"] = self.investigation.overview(stamp)
            if "sampling" in self.cached:
                self.cached["sampling"]["last"] = deepcopy(self.latest_sample)
                self.cached["sampling"]["status"] = self._sampling_status(stamp)
            return self.cached
        self.last_refresh = stamp
        r = self.r
        local = local_time(r)
        base = r.unified_planner.base_load.coverage(local, r.planner_settings.get("base_load_min_days", 4))
        quality = r.unified_planner.quality.overview()
        pv = r.local_pv.overview()
        native = r.panasonic.overview()
        previous_investigation = self.investigation.snapshot()
        investigation = self.investigation.refresh(stamp, native=native, pv=pv, quality=quality)
        if previous_investigation != self.investigation.snapshot() and r.data_loaded:
            r.store.async_delay_save(r._snapshot, 60)
        # Old thermal models remain private diagnosis evidence. This page has
        # no current Panasonic control model or delayed comfort command.
        archive = getattr(r, "panasonic_archive", {})
        backup = archive.get("backup_store", {}) if isinstance(archive, dict) else {}
        old_thermal = backup.get("smart_climate", {}) if isinstance(backup, dict) else {}
        old_thermal = old_thermal if isinstance(old_thermal, dict) else {}
        old_profiles = old_thermal.get("profiles", {})
        old_profiles = old_profiles if isinstance(old_profiles, dict) else {}
        power = r.learning.overview(r.wallbox_settings.get("stable_s", 180))
        phase = r.phase_learning.overview(r.configs)
        heatpump = r.heatpump_learning.overview()
        q = quality.get("last_7d", {})
        models = [
            {"id": "base", "name": "Huishoudelijk restverbruik", "enabled": r.planner_settings.get("enabled", True) and r.planner_settings.get("base_load_learning", True),
             "state": f'{base["live_buckets"]}/48 uur/dagtype-vakken met genoeg live dagen',
             "evidence": {**base, "heatpump_separation": heatpump},
             "effect": "Gewone huishoudlast voor de planner. Duidelijke ruimteverwarming, koeling, tapwater en sterilisatie worden niet als normale basislast geleerd; actuele vrije netruimte blijft uitsluitend gemeten."},
            {"id": "heatpump", "name": "Warmtepompactiviteit", "enabled": bool(native.get("configured")),
             "state": "Afzonderlijke activiteit en planningsschatting",
             "evidence": heatpump,
             "effect": "Schattingen uit bevestigde native taakovergangen zijn alleen voor planning en classificatie; nooit voor realtime netruimte."},
            {"id": "pv", "name": "Zonnepanelen en lokale schaduw", "enabled": pv.get("enabled"),
             "state": pv.get("reason", "Leren"), "evidence": {**pv, "forecast_calibration": r.pv_forecast.cached},
             "effect": "Lokale correctie van zonnevoorspellingen binnen bestaande drempels; geen virtueel overschot."},
            {"id": "climate", "name": "Bestaande woningmetingen", "enabled": False,
             "state": "Alleen-lezen archief; Panasonic regelt de ruimtes",
             "evidence": {"archived_profile_count": len(old_profiles), "archived": bool(old_profiles)},
             "effect": "Bestaande leerdata blijft in de privé-opslag en analyse-export behouden. Geen AUTO/UIT- of temperatuursturing door dit model."},
            {"id": "tank", "name": "Warmtepompmetingen", "enabled": bool(native.get("configured")),
             "state": "Uitlezen van native temperatuur en bedrijfsinformatie",
             "evidence": native,
             "effect": "Panasonic beheert het tankdoel, comfort en sterilisatie. SolarPilot maakt geen nachtvoorraadplan of temperatuurwijziging."},
            {"id": "devices", "name": "Verbruikers en Wallbox-reactie", "enabled": power.get("enabled"),
             "state": f'{len(power.get("profiles", {}))} vermogensprofielen; {power.get("samples", 0)} gemeten overdrachten',
             "evidence": power, "effect": "Alleen echte gekoppelde meters leren vermogen. Bekende schattingen zijn geen nieuwe metingen; bestaande minimumtijden blijven staan."},
            {"id": "phase", "name": "Faseherkenning", "enabled": r.phase_settings.get("enabled", False) and phase.get("enabled"),
             "state": f'{phase.get("accepted_events", 0)} geaccepteerde vermogensgebeurtenissen', "evidence": phase,
             "effect": "Adviserend totdat de bestaande afzonderlijke vrijgave is bevestigd. Geen wijziging van hoofdzekering, fasekeuze of 25 A-laadlimiet."},
            {"id": "battery", "name": "Batterijscenario’s", "enabled": r.battery_analysis_settings.get("enabled", True),
             "state": "What-if, geen bewezen gedrag van een fysieke batterij", "evidence": {"physical_battery_configured": r.battery_fleet.configured},
             "effect": "Gebruik gemeten energiestromen voor vergelijking; scenarioaannames en 20% round-tripverlies worden niet als meetbewijs geleerd."},
        ]
        findings = []
        context = {"release": VERSION,
                   "sources": {k: r.settings.get(k) for k in ("grid_entity", "pv_entity", "battery_power_entity")},
                   "devices": {i: (c.get("kind"), c.get("power_entity")) for i, c in r.configs.items()},
                   "heatpump_meter": r.sg_boost.config.get("power_entity"),
                   "heatpump_supplies": {k: r.sg_boost.config.get(k) for k in ("power_supply1_entity", "power_supply2_entity", "power_supply_profile", "power_supply1_role", "power_supply2_role")},
                   "wallbox_session":r.wallbox_settings.get("session_mode_entity"),
                   "pv_sources":r.pv_forecast.source.refs, "pv_settings":r.pv_forecast.settings}
        context_hash = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()[:16]
        wallbox_question = None
        if r.wallbox_settings.get("enabled"):
            wallbox_reading = r._wallbox_reading()
            if wallbox_reading.mode == "unknown":
                wallbox_question = wallbox_session_question(r, stamp)

        def ask(key, title, message, choices, severity="choice"):
            # Reopen an analysed finding for changed causes, wiring or meaningful
            # quality bands, rather than for each new sample or small float drift.
            facts = {}
            if key == "adaptation":
                eligible = base["eligible_candidates"]
                facts = {"policy": self.policy["adaptation"], "eligible_band": 0 if eligible == 0 else 1 if eligible < 12 else 2}
            elif key == "base_error":
                facts = {"error_band": min(20, int((number(q.get("base_mae_w")) or 0) // 200))}
            elif key == "pv_error":
                facts = {"error_band": min(20, int((number(q.get("pv_daylight_mae_w")) or 0) // 350))}
            elif key == "heatpump_meter":
                facts = {"power_kind": native.get("power_kind")}
            elif key == "base_disabled":
                facts = {"enabled": r.planner_settings.get("enabled", True), "learning": r.planner_settings.get("base_load_learning", True)}
            elif key.startswith("source_"):
                facts = {"reason": self.latest_sample.get("reason")}
            elif key == "pv_source":
                facts = {"warning": r.pv_forecast.source.warning}
            elif key == "wallbox_session":
                facts = {"cause": wallbox_question[0], "message": message}
            revision = hashlib.sha256(json.dumps([key, context_hash, facts], sort_keys=True).encode()).hexdigest()[:16]
            answer = self.answers.get(key, {})
            if answer.get("revision") == revision and (answer.get("action") == "keep" or answer.get("until", 0) > stamp):
                return
            findings.append({"id": key, "revision": revision, "title": title, "message": message,
                             "severity": severity, "choices": choices})

        if wallbox_question is not None:
            ask("wallbox_session", "Welke laadsessie is werkelijk actief?",
                wallbox_question[1],
                [{"id":"configure","label":"Wallbox-koppeling bekijken"},{"id":"keep","label":"Alleen restoverschot gebruiken"},{"id":"later","label":"Morgen vragen"}], "attention")
        if r.pv_forecast.settings.get("enabled") and (r.pv_forecast.source.warning or len(r.pv_forecast.source.candidates)>1 and not r.pv_forecast.source.entry_id):
            ask("pv_source", "Forecast.Solar-bron vraagt een keuze", r.pv_forecast.source.warning or "Kies één bron in Zon & voorspelling. Metingen blijven leidend; niets wordt dubbel opgeteld.",
                [{"id":"configure","label":"PV-koppelingen bekijken"},{"id":"keep","label":"Voorlopig zo laten"},{"id":"later","label":"Morgen vragen"}])
        if self.policy["adaptation"] == "assisted":
            ask("adaptation", "Mag een aantoonbaar beter recent verbruiksprofiel gebruikt worden?",
                "SolarPilot vergelijkt een 14-dagenmodel met het bestaande profiel op latere, vooraf niet meegeleerde dagen. Alleen na minstens vier vergelijkingsdagen, minstens 10% en 20 W minder fout, maximaal ±25% bijsturen. Bij slechter bewijs terug naar het basisprofiel. Dit wijzigt geen comfort-, net- of toestelbeveiliging.",
                [{"id": "auto", "label": "Begrensd automatisch"}, {"id": "keep", "label": "Alleen advies"}, {"id": "later", "label": "Morgen vragen"}])
        if not self.latest_sample.get("valid") and self.latest_sample.get("code") not in ("initializing", "settling"):
            ask("source_"+self.latest_sample.get("code", "unknown"), "Een leerbron is nog niet bruikbaar", self.latest_sample["reason"] + " Langer wachten verhelpt een verkeerde koppeling niet. Geen nulwaarden invullen om de score op te krikken.",
                [{"id": "configure", "label": "Koppelingen bekijken"}, {"id": "keep", "label": "Voorlopig zo laten"}, {"id": "later", "label": "Morgen vragen"}], "attention")
        if not r.planner_settings.get("enabled", True) or not r.planner_settings.get("base_load_learning", True):
            ask("base_disabled", "Restverbruik wordt niet bijgeleerd", "De planner of zijn basislast-leeroptie staat uit. Wil je die instelling bekijken? Deze vraag schakelt niet zelf een apparaat in.",
                [{"id": "configure", "label": "Instelling bekijken"}, {"id": "keep", "label": "Uit laten"}])
        if (number(q.get("base_mae_w")) or 0) > 400 and q.get("samples", 0) >= 12:
            ask("base_error", "Het voorspelde restverbruik wijkt nog af", f'Gemiddelde absolute afwijking {q["base_mae_w"]:g} W in de beschikbare meetperiode. Kijk naar brondekking en bijzondere verbruikers. Het is geen extra verbruik; een oorzaak is niet bewezen.',
                [{"id": "export", "label": "Analyse-export openen"}, {"id": "keep", "label": "Blijf verzamelen"}, {"id": "later", "label": "Morgen beoordelen"}])
        if (number(q.get("pv_daylight_mae_w")) or 0) > 700 and q.get("pv_daylight_samples", 0) >= 12:
            ask("pv_error", "De zonnevoorspelling overdag wijkt af", f'Gemiddelde absolute fout bij zon {q["pv_daylight_mae_w"]:g} W. De richting en dekking staan onder meetkwaliteit. Wolken, schaduw en bronverschillen zijn mogelijke verklaringen; deze score bewijst geen oorzaak. Nieuwe zonnecorrecties mogen nooit een gemeten tekort vervangen.',
                [{"id": "export", "label": "Zongegevens exporteren"}, {"id": "configure", "label": "Bronnen bekijken"}, {"id": "later", "label": "Morgen beoordelen"}])
        if native.get("configured") and native.get("power_kind") != "measured" and (number(q.get("base_mae_w")) or 0) > 400:
            ask("heatpump_meter", "Warmtepompmeting vraagt controle", "Zonder onafhankelijke betrouwbare totaalmeting blijft het warmtepompverbruik geheel of gedeeltelijk onbekend. Een planningsschatting wordt nooit als actuele netruimte gebruikt. Controleer ook of de meter het hele toestel of slechts één voeding omvat.",
                [{"id": "configure", "label": "Beschikbare meters bekijken"}, {"id": "keep", "label": "Nog geen aparte meter"}, {"id": "later", "label": "Later bekijken"}])
        no_meter = [c.get("name", i) for i, c in r.configs.items() if not c.get("power_entity")]
        if no_meter:
            ask("consumer_meters", "Nog geschat toestelvermogen", "Nog geen eigen vermogensbron voor: " + ", ".join(no_meter[:10]) + ". Een nieuwe Shelly eerst expliciet koppelen; nooit automatisch het relais gaan bedienen. Ontbrekende programmafasen blijven onbekend.",
                [{"id": "configure", "label": "Meter koppelen"}, {"id": "keep", "label": "Voorlopig schatten"}, {"id": "later", "label": "Morgen vragen"}])
        if self.policy["adaptation"] == "assisted":
            for finding in findings:
                if finding["id"] == "adaptation":
                    finding["message"] += f' Nu zijn {base["eligible_candidates"]} uur/dagtype-vakken geschikt volgens die vergelijking. Dit is geen gemeten energiebesparing.'
        self.current_findings = deepcopy(findings)
        reviewed = []
        pending = []
        feedback = getattr(r, "analysis_feedback", None)
        for finding in findings:
            review = feedback.question_review(finding["id"], finding["revision"]) if feedback else None
            if review and review["outcome"] == "reviewed":
                reviewed.append({"id": finding["id"], "revision": finding["revision"], "title": finding["title"], "answer_note": review["answer"]})
                continue
            if review:
                finding["answer_note"] = review["answer"]
                finding["analysis_outcome"] = "needs_more_data"
            pending.append(finding)
        findings = pending
        candidates = {x["bucket"] for x in base["buckets"] if x["candidate_applied"]}
        if candidates != self.active_candidates:
            self._event("adaptatie_gebruik", {"actieve_vakken": sorted(candidates), "vorige_vakken": sorted(self.active_candidates)})
            self.active_candidates = candidates
            if r.data_loaded:
                r.store.async_delay_save(r._snapshot, 60)
        totals = {}
        cutoff = (local-timedelta(days=6)).date().isoformat()
        for day, counts in self.days.items():
            if cutoff <= day <= local.date().isoformat():
                for key, n in counts.items(): totals[key] = totals.get(key, 0) + n
        unknown_attempts = totals.get("heatpump_"+CONTEXT_UNKNOWN, 0)
        heatpump_attempts = sum(n for key, n in totals.items() if key.startswith("heatpump_"))
        exclusions = {"settling_attempts": totals.get("settling", 0),
                      "heatpump_unknown_attempts": unknown_attempts,
                      "other_heatpump_context_attempts": heatpump_attempts-unknown_attempts,
                      "note": "Kwartierpogingen, geen gemeten uren. Een tijdelijke stabilisatie en ontbrekende warmtepompcontext zijn afzonderlijke leeruitsluitingen; onbekende waarden worden niet als nul aangevuld."}
        self.cached = {"ready": True, "updated_at": stamp, "policy": dict(self.policy), "models": models,
                       "questions": findings, "open_questions": len(findings), "pending_findings": len(findings),
                       "reviewed_findings": reviewed, "analysis_needed": bool(findings), "analysis_action": "export_7d", "quality": quality,
                       "sampling": {"last": deepcopy(self.latest_sample), "status": self._sampling_status(stamp),
                                    "attempts_7d": totals, "exclusions_7d": exclusions, "days": deepcopy(self.days)},
                       "audit": list(self.audit), "error": self.error,
                       "investigation": investigation,
                       "contract": "Geen perfecte voorkennis van jouw huis. Modelzekerheid is geen kans op een juiste fysieke actie. Alleen expliciet gekoppelde bronnen, geen automatische camerabeelden/aanwezigheidsprofielen of cloud-AI. Bediening blijft door bestaande vrijgaven, actuele meters, prioriteiten en grenzen bepaald."}
        return self.cached

    async def _persist(self, previous):
        try:
            await self.r.store.async_save(self.r._snapshot())
        except Exception:
            self.restore(previous)
            self.r.unified_planner.base_load._detail_cache.clear()
            self.r.unified_planner.last_plan_wall = 0
            self.last_refresh = 0
            self.r.analysis.event("learning", "Bewaren leerkeuze mislukt; vorige leerkeuze hersteld.")
            raise

    async def answer(self, key, revision, action):
        previous = deepcopy(self.snapshot())
        data = self.refresh(force=True)
        question = next((q for q in data["questions"] if q["id"] == key), None)
        if question is None or question["revision"] != revision:
            raise ValueError("stale_question")
        if action not in {x["id"] for x in question["choices"]}:
            raise ValueError("invalid_choice")
        if action == "auto" and key == "adaptation":
            self.policy["adaptation"] = "automatic"
            self.r.unified_planner.base_load.adaptive_enabled = True
            self.r.unified_planner.base_load._detail_cache.clear()
            self.r.unified_planner.last_plan_wall = 0
        else:
            self.answers[key] = {"revision": revision, "action": action,
                                 "until": time.time() + (86400 if action == "later" else 3600 if action in ("configure", "export") else 0)}
        while len(self.answers) > 100:
            self.answers.pop(next(iter(self.answers)))
        self._event("antwoord", {"vraag": key, "keuze": action})
        await self._persist(previous)
        self.last_refresh = 0
        result = deepcopy(self.refresh(force=True))
        result["navigation"] = action if action in ("configure", "export") else None
        return result

    async def set_policy(self, key, value):
        previous = deepcopy(self.snapshot())
        allowed = {"adaptation": ("assisted", "automatic"), "sampling": ("metered", "quiet"), "notifications": (True, False)}
        if key not in allowed or type(value) is not type(allowed[key][0]) or value not in allowed[key]:
            raise ValueError("invalid_policy")
        old = self.policy[key]
        self.policy[key] = value
        if key == "adaptation":
            self.answers.pop("adaptation", None)
        self.r.unified_planner.base_load.adaptive_enabled = self.policy["adaptation"] == "automatic"
        self.r.unified_planner.base_load._detail_cache.clear()
        self.r.unified_planner.last_plan_wall = 0
        self._event("leerbeleid", {"instelling": key, "oud": old, "nieuw": value})
        await self._persist(previous)
        return deepcopy(self.refresh(force=True))

    async def tick(self):
        """Keep findings local; retire only our old non-urgent analysis notice.

        Finding revisions and the legacy opt-in never establish urgency. Actual
        controller faults and proven provider breaks have their own reporters.
        Retain the old policy/receipt schema so upgrades preserve stored data.
        """
        self.refresh()
        try:
            if self.notification_signature or self._legacy_notice_pending:
                services = self.r.hass.services
                if not services.has_service("persistent_notification", "dismiss"):
                    return
                await services.async_call("persistent_notification", "dismiss", {
                    "notification_id": "solar_pilot_learning_" + self.r.entry.entry_id}, blocking=False)
                self.notification_signature = ""
                self.last_notification = 0.0
                self._legacy_notice_pending = False
                self._notification_cleanup_dirty = True
            if self._notification_cleanup_dirty and self.r.data_loaded:
                self.r.store.async_delay_save(self.r._snapshot, 60)
                self._notification_cleanup_dirty = False
        except Exception:
            # Delivery/persistence failure is not a controller or learner fault.
            # Retry dismissal until accepted; retry storage without dismissing
            # again after an accepted call.
            if not self._notification_cleanup_failed:
                _LOGGER.warning("Oude SolarPilot-analysemelding kon niet worden opgeruimd; "
                                "volgende cyclus probeert opnieuw", exc_info=True)
            self._notification_cleanup_failed = True
            return
        self._notification_cleanup_failed = False

    def summary(self):
        return {"ready": self.cached.get("ready", False), "open_questions": self.cached.get("open_questions", 0),
                "pending_findings": self.cached.get("open_questions", 0), "analysis_needed": bool(self.cached.get("open_questions", 0)),
                "analysis_action": "export_7d", "findings": [{key: row[key] for key in ("id", "revision", "title", "message", "answer_note") if key in row}
                    for row in self.cached.get("questions", [])[:100]],
                "updated_at": self.cached.get("updated_at"), "adaptation": self.policy["adaptation"], "error": self.error,
                "investigation": self.investigation.overview(time.time())}
