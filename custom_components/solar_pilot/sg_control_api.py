"""Strict native SG policy commands; all physical authority stays in SGBoostManager."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN

SERVICE_SG_MANUAL_CONTROL = "sg_manual_control"
SG_MANUAL_OPTIONS = ("auto", "on_30", "on_60", "off_30", "off_60")


def validate_manual_control(mode, duration_s=None):
    """Accept only the finite, reviewed policy choices, without coercion."""
    if type(mode) is not str or mode not in ("auto", "on", "off"):
        raise vol.Invalid("Kies automatisch, aan of uit voor de SG-boost.")
    if mode == "auto":
        if duration_s is not None:
            raise vol.Invalid("Automatisch heeft geen tijdsduur.")
    elif type(duration_s) is not int or duration_s not in (1800, 3600):
        raise vol.Invalid("Kies 1800 of 3600 seconden voor tijdelijke SG-bediening.")
    return mode, duration_s


def validate_service_data(data):
    """Reject stale/unreviewed service payloads before entering the controller."""
    if set(data) - {"config_entry_id", "mode", "duration_s"} or "mode" not in data:
        raise vol.Invalid("Ongeldige SG-bedieningsopdracht.")
    if "config_entry_id" in data and type(data["config_entry_id"]) is not str:
        raise vol.Invalid("De configuratie-ID moet tekst zijn.")
    if data["mode"] == "auto" and "duration_s" in data:
        raise vol.Invalid("Laat de tijdsduur weg bij automatisch.")
    validate_manual_control(data["mode"], data.get("duration_s"))
    return data


SG_MANUAL_SERVICE_SCHEMA = vol.All(
    vol.Schema({
        vol.Optional("config_entry_id"): str,
        vol.Required("mode"): str,
        # Exact integer validation happens below; no vol.Coerce or bool-as-int.
        vol.Optional("duration_s"): object,
    }),
    validate_service_data,
)


def _current_runtime(runtime):
    """A retired entity or a queued callback never gains the replacement epoch."""
    entry = getattr(runtime, "entry", None)
    if (getattr(runtime, "_closed", True) or entry is None
            or getattr(entry, "runtime_data", None) is not runtime):
        raise HomeAssistantError("SolarPilot-configuratie niet geladen; vernieuw de bediening.")


async def async_set_sg_manual_control(runtime, mode, duration_s=None, *, context=None):
    """Authorize the native entity path and recheck its captured runtime after auth."""
    validate_manual_control(mode, duration_s)
    _current_runtime(runtime)
    user_id = getattr(context, "user_id", None)
    if user_id:
        user = await runtime.hass.auth.async_get_user(user_id)
        if user is None or not user.is_admin:
            raise HomeAssistantError("Alleen een Home Assistant-beheerder mag de SG-boost bedienen.")
        _current_runtime(runtime)
    # The serialized controller repeats epoch/permission checks after its lock
    # wait. OFF invalidates any outstanding ON before waiting for that lock.
    await runtime.sg_boost.set_manual_control(mode, duration_s)


async def async_handle_sg_manual_control(hass, call):
    """Dispatch one loaded entry; multiple installations need an explicit ID."""
    data = validate_service_data(call.data)
    entry_id = data.get("config_entry_id", "")
    entries = [entry for entry in hass.config_entries.async_entries(DOMAIN)
               if not entry_id or entry.entry_id == entry_id]
    if len(entries) != 1:
        raise HomeAssistantError("Kies één geladen SolarPilot-configuratie.")
    runtime = getattr(entries[0], "runtime_data", None)
    if runtime is None:
        raise HomeAssistantError("SolarPilot-configuratie niet geladen.")
    await async_set_sg_manual_control(
        runtime, data["mode"], data.get("duration_s"), context=getattr(call, "context", None)
    )
