"""Local learning evidence and a bounded, explicit decision inbox.

No device services, credentials, arbitrary entity discovery or code generation.
This module changes predictions only; comfort, permissions and safety stay owned
by the existing modules. Model approvals are not permissions to start appliances.
"""
from __future__ import annotations

from collections import deque
from copy import deepcopy
from datetime import datetime, timedelta
import hashlib
import json
import math
import time

from .heatpump_learning import (
    ACTIVE_CONTEXTS, CONTEXT_NORMAL, CONTEXT_UNKNOWN, classify_heatpump,
)


def number(value):
    if isinstance(value, bool):
        return None
    try:
        out = float(value)
    except (ValueError, TypeError):
        return None
    return out if math.isfinite(out) else None


def local_time(runtime):
    from zoneinfo import ZoneInfo
    zone = getattr(getattr(runtime.hass, "config", None), "time_zone", "Europe/Brussels")
    try:
        return datetime.now(ZoneInfo(zone))
    except (ValueError, KeyError):
        return datetime.now().astimezone()


def measured_baseline(r, local_now, monotonic):
    """Return a synchronous, measurement-backed residual, or an explicit unknown.

    Only already modelled owned loads/EV are subtracted. Ungrouped heat-pump or
    household demand remains residual, not silently subtracted or replaced with
    an inferred wattage. Energy (kWh) counters cannot be substituted for power.
    """
    refs, stamps, parts = [], [], {}

    def fail(code, message):
        return {"valid": False, "watts": None, "code": code, "reason": message,
                "sources": list(refs), "parts": dict(parts), "context": "unknown"}

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
    owned = 0.0
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
        if getattr(state, "last_on", 0) and monotonic-getattr(state, "last_on", 0) < 120:
            return fail("settling", "Nieuwe last nog aan het stabiliseren; twee minuten geen basislastmeting.")
    parts["owned_w"] = owned
    if getattr(r, "pending", None) or getattr(r, "handover", None):
        return fail("settling", "Een opdracht of vermogensoverdracht wacht nog op terugmelding.")
    if max(stamps)-min(stamps) > 120:
        return fail("source_alignment", "Bronrapporten liggen meer dan twee minuten uiteen.")
    base = grid + pv + battery - ev - owned
    if not 0 <= base <= 20000:
        return fail("balance", "De gemeten energiebalans is niet plausibel. Controleer bronkoppelingen/eenheden; geen negatief verbruik als nul leren.")
    context, context_reason = classify_heatpump(r, local_now)
    return {"valid": True, "watts": round(base, 1), "code": "measured",
            "reason": "Gemeten restlast uit net + PV + batterijontlading − gemeten beheerde lasten − gemeten Wallbox.",
            "sources": refs, "parts": parts, "context": context,
            "context_reason": context_reason,
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
        self.latest_sample = {"valid": False, "watts": None, "code": "initializing", "reason": "Eerste meetcontrole afwachten."}
        self.cached = {"models": [], "questions": [], "ready": False, "policy": dict(self.policy)}
        self.active_candidates = set()
        self.error = ""

    def snapshot(self):
        return {"schema": 1, "policy": dict(self.policy), "answers": deepcopy(self.answers),
                "audit": list(self.audit), "days": deepcopy(self.days), "last_attempt": self.last_attempt,
                "last_notification": self.last_notification, "notification_signature": self.notification_signature,
                "active_candidates": sorted(self.active_candidates)}

    def restore(self, data):
        if not isinstance(data, dict):
            return
        for k, allowed in (("sampling", ("metered", "quiet")), ("adaptation", ("assisted", "automatic")), ("notifications", (False, True))):
            value = data.get("policy", {}).get(k)
            if type(value) is type(allowed[0]) and value in allowed:
                self.policy[k] = value
        raw = data.get("answers", {})
        self.answers = {str(k)[:160]: v for k, v in list(raw.items())[-100:] if isinstance(v, dict)} if isinstance(raw, dict) else {}
        self.audit = deque([v for v in data.get("audit", [])[-150:] if isinstance(v, dict)], maxlen=150)
        raw = data.get("days", {})
        if isinstance(raw, dict):
            for k, v in sorted(raw.items())[-60:]:
                if isinstance(v, dict):
                    self.days[k] = {str(c)[:40]: max(0, min(1000000, int(n))) for c, n in v.items() if number(n) is not None}
        self.active_candidates = set(str(x)[:32] for x in data.get("active_candidates", [])[:48])
        self.last_notification = number(data.get("last_notification")) or 0
        self.notification_signature = str(data.get("notification_signature", ""))[:64]
        self.r.unified_planner.base_load.adaptive_enabled = self.policy["adaptation"] == "automatic"

    def observe(self, local_now, monotonic):
        r = self.r
        sample = measured_baseline(r, local_now, monotonic)
        self.latest_sample = sample
        stamp = time.time()
        model = r.unified_planner.base_load
        model.adaptive_enabled = self.policy["adaptation"] == "automatic"

        # Classify heat-pump activity every normal rule cycle. The learned watts
        # remain planning/diagnostic evidence and never change realtime headroom.
        if sample.get("valid"):
            context = sample.get("context", CONTEXT_UNKNOWN)
            if context in ACTIVE_CONTEXTS | {CONTEXT_NORMAL, CONTEXT_UNKNOWN}:
                r.heatpump_learning.observe(
                    stamp, local_now.date().isoformat(), context, sample["watts"])
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

        if stamp-self.last_attempt < 900:
            return sample
        self.last_attempt = stamp
        code = sample["code"]
        if not r.planner_settings.get("base_load_learning", True):
            code = "learning_disabled"
        elif sample.get("context") != CONTEXT_NORMAL:
            code = "heatpump_" + str(sample.get("context") or CONTEXT_UNKNOWN)
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

    def _event(self, what, detail):
        self.audit.append({"time": datetime.now().astimezone().isoformat(), "event": what, "details": detail})
        self.r.analysis.event("learning", what + ": " + str(detail))

    def refresh(self, force=False):
        stamp = time.time()
        if not force and stamp-self.last_refresh < 60:
            return self.cached
        self.last_refresh = stamp
        r = self.r
        local = local_time(r)
        base = r.unified_planner.base_load.coverage(local, r.planner_settings.get("base_load_min_days", 4))
        quality = r.unified_planner.quality.overview()
        pv = r.local_pv.overview()
        thermal = r.smart_climate.overview()
        dhw = r.dhw.overview()
        power = r.learning.overview(r.wallbox_settings.get("stable_s", 180))
        phase = r.phase_learning.overview(r.configs)
        heatpump = r.heatpump_learning.overview()
        q = quality.get("last_7d", {})
        models = [
            {"id": "base", "name": "Huishoudelijk restverbruik", "enabled": r.planner_settings.get("enabled", True) and r.planner_settings.get("base_load_learning", True),
             "state": f'{base["live_buckets"]}/48 uur/dagtype-vakken met genoeg live dagen',
             "evidence": {**base, "heatpump_separation": heatpump},
             "effect": "Gewone huishoudlast voor de planner. Duidelijke ruimteverwarming, koeling, tapwater en sterilisatie worden niet als normale basislast geleerd; actuele vrije netruimte blijft uitsluitend gemeten."},
            {"id": "heatpump", "name": "Warmtepompactiviteit", "enabled": r.dhw.configured or r.smart_climate.configured,
             "state": "Afzonderlijke activiteit en planningsschatting",
             "evidence": heatpump,
             "effect": "Schattingen uit stabiele compressorstarts/stops zijn alleen voor planning en classificatie; nooit voor realtime netruimte."},
            {"id": "pv", "name": "Zonnepanelen en lokale schaduw", "enabled": pv.get("enabled"),
             "state": pv.get("reason", "Leren"), "evidence": {**pv, "forecast_calibration": r.pv_forecast.cached},
             "effect": "Lokale correctie van zonnevoorspellingen binnen bestaande drempels; geen virtueel overschot."},
            {"id": "climate", "name": "Woning en vloerverwarming", "enabled": thermal.get("enabled"),
             "state": thermal.get("decision", {}).get("reason", "Niet gekoppeld"),
             "evidence": {"confidence": thermal.get("model_confidence"), "profiles": thermal.get("profiles", {}),
                          "weather_bias": thermal.get("weather_bias", {}), "coast_feedback": thermal.get("coast_feedback", {})},
             "effect": "Bestaande leerfuncties en grenzen blijven gelden. Geen nieuwe AUTO/OFF-vrijgave of HEAT/COOL-keuze door deze pagina."},
            {"id": "tank", "name": "Boiler en nachtvoorraad", "enabled": dhw.get("configured"),
             "state": "Normaal doel en comfortgrens veranderen niet door leren",
             "evidence": dhw.get("tank_learning", {}),
             "effect": "Afkoeling/opwarming voorspellen; zonnevoorraad binnen je plafond. Geen herstelboost naar 52 °C of Force DHW."},
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
        context = {"sources": {k: r.settings.get(k) for k in ("grid_entity", "pv_entity", "battery_power_entity")},
                   "devices": {i: (c.get("kind"), c.get("power_entity")) for i, c in r.configs.items()},
                   "dhw_meter": r.dhw.config.get("power_entity"),
                   "wallbox_session":r.wallbox_settings.get("session_mode_entity"),
                   "pv_sources":r.pv_forecast.source.refs, "pv_settings":r.pv_forecast.settings}
        context_hash = hashlib.sha256(json.dumps(context, sort_keys=True).encode()).hexdigest()[:16]

        def ask(key, title, message, choices, severity="choice"):
            revision = hashlib.sha256((key+context_hash+(self.policy["adaptation"] if key == "adaptation" else "")).encode()).hexdigest()[:16]
            answer = self.answers.get(key, {})
            if answer.get("revision") == revision and (answer.get("action") == "keep" or answer.get("until", 0) > stamp):
                return
            findings.append({"id": key, "revision": revision, "title": title, "message": message,
                             "severity": severity, "choices": choices})

        if r.wallbox_settings.get("enabled") and r._wallbox_reading().mode == "unknown":
            ask("wallbox_session", "Welke laadsessie is werkelijk actief?",
                "De instelling Full Solar kan blijven staan tijdens manueel laden. Koppel onder Opslag & laden → Wallbox een gecontroleerde effectieve sessiesensor. Tot dan gebruikt SolarPilot alleen echte restinjectie; comfort blijft werken. Geen antwoord geeft geen overnametoestemming.",
                [{"id":"configure","label":"Wallbox-koppeling bekijken"},{"id":"keep","label":"Alleen restoverschot gebruiken"},{"id":"later","label":"Morgen vragen"}], "attention")
        if r.pv_forecast.settings.get("enabled") and (r.pv_forecast.source.warning or len(r.pv_forecast.source.candidates)>1 and not r.pv_forecast.source.entry_id):
            ask("pv_source", "Forecast.Solar-bron vraagt een keuze", r.pv_forecast.source.warning or "Kies één bron in Zon & voorspelling. Metingen blijven leidend; niets wordt dubbel opgeteld.",
                [{"id":"configure","label":"PV-koppelingen bekijken"},{"id":"keep","label":"Voorlopig zo laten"},{"id":"later","label":"Morgen vragen"}])
        if self.policy["adaptation"] == "assisted":
            ask("adaptation", "Mag een aantoonbaar beter recent verbruiksprofiel gebruikt worden?",
                "SolarPilot vergelijkt een 14-dagenmodel met het bestaande profiel op latere, vooraf niet meegeleerde dagen. Alleen na minstens vier vergelijkingsdagen, minstens 10% en 20 W minder fout, maximaal ±25% bijsturen. Bij slechter bewijs terug naar het basisprofiel. Dit wijzigt geen comfort-, net- of toestelbeveiliging.",
                [{"id": "auto", "label": "Begrensd automatisch"}, {"id": "keep", "label": "Alleen advies"}, {"id": "later", "label": "Morgen vragen"}])
        if not self.latest_sample.get("valid") and self.latest_sample.get("code") != "initializing":
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
        if thermal.get("fault"):
            ask("thermal_fault", "Ruimteklimaat vraagt controle", str(thermal["fault"]) + " De leermodule verruimt geen comfortband en verandert geen Panasonic-stand om de melding te laten verdwijnen.",
                [{"id": "configure", "label": "Klimaatinstellingen bekijken"}, {"id": "export", "label": "Analyse-export"}, {"id": "later", "label": "Morgen beoordelen"}], "attention")
        if dhw.get("configured") and not dhw.get("own_meter_available") and (number(q.get("base_mae_w")) or 0) > 400:
            ask("heatpump_meter", "Warmtepompvermogen wordt nog bijgeleerd", "SolarPilot houdt duidelijke ruimteverwarming, koeling, tapwater en sterilisatie nu uit de gewone huishoudelijke basislast. Zonder onafhankelijke W-meter leert het alleen een conservatieve planningsschatting uit stabiele starts/stops. Die schatting wordt nooit van realtime P1-netruimte afgetrokken.",
                [{"id": "configure", "label": "Beschikbare meters bekijken"}, {"id": "keep", "label": "Nog geen aparte meter"}, {"id": "later", "label": "Later bekijken"}])
        no_meter = [c.get("name", i) for i, c in r.configs.items() if not c.get("power_entity")]
        if no_meter:
            ask("consumer_meters", "Nog geschat toestelvermogen", "Nog geen eigen vermogensbron voor: " + ", ".join(no_meter[:10]) + ". Een nieuwe Shelly eerst expliciet koppelen; nooit automatisch het relais gaan bedienen. Ontbrekende programmafasen blijven onbekend.",
                [{"id": "configure", "label": "Meter koppelen"}, {"id": "keep", "label": "Voorlopig schatten"}, {"id": "later", "label": "Morgen vragen"}])
        if self.policy["adaptation"] == "assisted":
            for finding in findings:
                if finding["id"] == "adaptation":
                    finding["message"] += f' Nu zijn {base["eligible_candidates"]} uur/dagtype-vakken geschikt volgens die vergelijking. Dit is geen gemeten energiebesparing.'
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
        self.cached = {"ready": True, "updated_at": stamp, "policy": dict(self.policy), "models": models,
                       "questions": findings, "open_questions": len(findings), "quality": quality,
                       "sampling": {"last": deepcopy(self.latest_sample), "attempts_7d": totals, "days": deepcopy(self.days)},
                       "audit": list(self.audit), "error": self.error,
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
        self.refresh()
        questions = self.cached.get("questions", [])
        if not self.policy["notifications"] or not questions:
            if self.notification_signature and self.r.hass.services.has_service("persistent_notification", "dismiss"):
                await self.r.hass.services.async_call("persistent_notification", "dismiss", {
                    "notification_id": "solar_pilot_learning_" + self.r.entry.entry_id}, blocking=False)
                self.notification_signature = ""
                if self.r.data_loaded:
                    self.r.store.async_delay_save(self.r._snapshot, 60)
            return
        signature = hashlib.sha256(json.dumps([(x["id"], x["revision"]) for x in questions]).encode()).hexdigest()[:32]
        stamp = time.time()
        if not questions or signature == self.notification_signature or stamp-self.last_notification < 86400:
            return
        services = self.r.hass.services
        if services.has_service("persistent_notification", "create"):
            await services.async_call("persistent_notification", "create", {
                "notification_id": "solar_pilot_learning_" + self.r.entry.entry_id,
                "title": "SolarPilot · Leren & vragen",
                "message": f'{len(questions)} vragen of bevindingen. Open SolarPilot → Leren & vragen. Er zijn geen comfort- of veiligheidsinstellingen gewijzigd.'}, blocking=False)
            self.last_notification = stamp
            self.notification_signature = signature
            self.r.store.async_delay_save(self.r._snapshot, 60)

    def summary(self):
        return {"ready": self.cached.get("ready", False), "open_questions": self.cached.get("open_questions", 0),
                "updated_at": self.cached.get("updated_at"), "adaptation": self.policy["adaptation"], "error": self.error}
