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
    """Return (allowed, long_runtime_allowed, explanation) without changing rights."""
    policy = config.get("wallbox_power_policy", "priority")
    if policy not in RECLAIM_POLICIES or policy == "never":
        return False, False, "Alleen werkelijk vrij overschot: overname uitgezet"
    if not before_wallbox:
        return False, False, "Wallbox heeft voorrang op dit toestel"
    if blocked:
        return False, False, "Vorige overname vraagt controle"
    if config.get("kind", "switch") == "dishwasher":
        return False, False, "Afwasmachine gebruikt de afzonderlijke beschermde-cyclusroute"
    if config.get("non_interruptible") or config.get("kind", "switch") not in ("switch", "number"):
        return False, False, "Geen generieke vermogensovername voor een beschermde of onbevestigde scriptcyclus"
    if not dedicated_meter:
        return False, False, "Een eigen actuele vermogensmeter is vereist voor bevestiging"
    if policy == "legacy":
        return bool(config.get("allow_wallbox_reclaim")), False, "Oude expliciete overnamekeuze en korte minimumlooptijd gelden"
    return True, True, "Voorrang volgen: gemeten zonnestroom van Wallbox mag worden benut; minimumlooptijd blijft gelden"
