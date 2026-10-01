"""Effective EV-session policy; never sends an EV command.

A configured Full Solar setting is not evidence that a manual override is absent.
The optional effective-session source is an explicit, user-verified HA entity.
"""
from __future__ import annotations
from dataclasses import dataclass
from .wallbox import state_set

SESSION_DEFAULTS = {
    "session_mode_entity": "",
    "session_solar_states": "Zonne-auto · laden;Zonne-auto · wacht op overschot",
    "session_manual_states": "Manueel laden;Manueel laden · klaar;Manueel / solar uit",
    "session_stopped_states": "Laden gestopt",
    "trust_solar_setting": False,
    "manual_suspend_extra_dhw": True,
}
RECLAIM_POLICIES = ("priority", "never", "legacy")


def discover_session_candidate(hass, config):
    """Return one strongly evidenced same-Wallbox session entity, never a guess."""
    try:
        from homeassistant.helpers import entity_registry as er
        registry = er.async_get(hass)
        lookup = getattr(registry, "async_get", lambda _entity: None)
        reference = next(
            (lookup(config.get(key)) for key in ("power_entity", "status_entity", "mode_entity")
             if config.get(key) and lookup(config.get(key)) is not None),
            None,
        )
        device_id = getattr(reference, "device_id", None)
        if not device_id:
            return ""
        rows = getattr(registry, "entities", {})
        rows = list(rows.values()) if hasattr(rows, "values") else []
        known_groups = [
            state_set(config.get("session_solar_states", SESSION_DEFAULTS["session_solar_states"])),
            state_set(config.get("session_manual_states", SESSION_DEFAULTS["session_manual_states"])),
            state_set(config.get("session_stopped_states", SESSION_DEFAULTS["session_stopped_states"])),
        ]
        hits = []
        for row in rows:
            if getattr(row, "device_id", None) != device_id or getattr(row, "disabled_by", None):
                continue
            entity_id = str(getattr(row, "entity_id", "") or "")
            if entity_id.split(".")[0] not in ("sensor", "select"):
                continue
            obj = hass.states.get(entity_id)
            options = {
                str(value).strip().casefold()
                for value in ((getattr(obj, "attributes", {}) or {}).get("options", []) if obj is not None else [])
            }
            current = str(getattr(obj, "state", "") or "").strip().casefold()
            evidence_groups = sum(bool(options & group) for group in known_groups)
            current_known = any(current in group for group in known_groups)
            identity = " ".join(filter(None, [
                entity_id,
                str(getattr(row, "translation_key", "") or ""),
                str((getattr(obj, "attributes", {}) or {}).get("friendly_name", "") if obj is not None else ""),
            ])).casefold()
            name_evidence = any(token in identity for token in ("session", "laadsessie", "charging mode", "charging_mode"))
            if evidence_groups >= 2 or (current_known and name_evidence):
                hits.append(entity_id)
        return hits[0] if len(hits) == 1 else ""
    except (AttributeError, ImportError, TypeError):
        return ""


@dataclass(frozen=True)
class Session:
    mode: str
    reason: str
    confirmed: bool = False


def classify_session(config, raw_mode, session_value):
    """Exact, configurable matching; unavailable/mismatching input grants no credit."""
    raw = str(raw_mode or "").strip().casefold()
    solar = raw in state_set(config.get("full_solar_states", "full_solar;Full solar;Full green"))
    value = str(session_value or "").strip().casefold()
    if config.get("session_mode_entity"):
        if value in state_set(config.get("session_manual_states", SESSION_DEFAULTS["session_manual_states"])):
            return Session("manual", "Manueel laden: EV-vermogen blijft gereserveerd voor de auto", True)
        if value in state_set(config.get("session_stopped_states", SESSION_DEFAULTS["session_stopped_states"])):
            return Session("stopped", "Laden gestopt; alleen werkelijk restoverschot gebruiken", True)
        if value in state_set(config.get("session_solar_states", SESSION_DEFAULTS["session_solar_states"])) and solar:
            return Session(str(raw_mode).strip(), "Effectieve zonnelaadsessie bevestigd", True)
        return Session("unknown", "Effectieve laadsessie onbekend of strijdig; geen EV-vermogen overnemen")
    if solar and config.get("trust_solar_setting", False) is True:
        return Session(str(raw_mode).strip(), "Full Solar-instelling vertrouwd op expliciete toestemming; handmatige overrides niet afzonderlijk zichtbaar", True)
    if raw in {"off", "disabled", "manual", "manueel"}:
        return Session("manual", "Geen autonome zonneregeling; EV-vermogen niet overneembaar", True)
    if not raw:
        return Session("unknown", "Full Solar-instelling niet beschikbaar; geen EV-vermogen overnemen")
    return Session("unknown", "Koppel de effectieve Wallbox-laadsessie; Full Solar-instelling alleen is geen bevestiging")


def reclaim_permission(config, *, before_wallbox, dedicated_meter, blocked=False):
    """Return (allowed, long_runtime_allowed, explanation) without changing rights.

    In the central beta.36 board the position and the per-device permission are
    deliberately independent: a lower-priority load may be allowed to ask the
    autonomous solar charger to give back measured solar power.  This never
    creates electrical headroom and still requires a confirmed solar session.
    """
    policy = config.get("wallbox_power_policy", "priority")
    central = "_priority_board_wallbox_power" in config
    central_permission = config.get("_priority_board_wallbox_power") is True
    if policy not in RECLAIM_POLICIES or policy == "never" or (central and not central_permission):
        return False, False, "Alleen werkelijk vrij zonneoverschot: Wallbox-terugname staat uit"
    if not central and not before_wallbox:
        return False, False, "Wallbox heeft volgens de oude regeling voorrang op dit toestel"
    if blocked:
        return False, False, "Vorige Wallbox-overname vraagt eerst controle"
    if config.get("kind", "switch") == "dishwasher":
        return False, False, "Afwasmachine gebruikt de afzonderlijke beschermde-cyclusroute"
    if config.get("non_interruptible") or config.get("kind", "switch") not in ("switch", "number"):
        return False, False, "Geen generieke vermogensovername voor een beschermde of onbevestigde scriptcyclus"
    if not dedicated_meter:
        return False, False, "Een eigen actuele vermogensmeter is vereist voor bevestiging"
    if policy == "legacy" and not central:
        return bool(config.get("allow_wallbox_reclaim")), False, "Oude expliciete overnamekeuze en korte minimumlooptijd gelden"
    if central and before_wallbox:
        return True, True, "Hoger dan Wallbox en expliciet toegestaan: gemeten zonnelaadvermogen mag veilig worden benut"
    if central:
        return True, True, "Lager dan Wallbox, maar expliciet toegestaan: Wallbox mag alleen met bevestigde zonnelaadsessie veilig terugregelen"
    return True, True, "Voorrang volgen: gemeten zonnestroom van Wallbox mag worden benut; minimumlooptijd blijft gelden"
