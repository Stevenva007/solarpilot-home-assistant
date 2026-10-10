"""Restricted native Shelly transport for the single commissioned SG contact.

The loaded Home Assistant Shelly integration owns connection/authentication.
No generic switch service, HTTP fallback, toggle or firmware/config write is
available here. RPC acknowledgement is followed by actual relay/timer readback;
this is software evidence, not proof of Panasonic's physical SG response.

Protocol: https://shelly-api-docs.shelly.cloud/gen2/ComponentsAndServices/Switch/
Hardware: https://kb.shelly.cloud/knowledge-base/shelly-1-gen4
HA helper: homeassistant.components.shelly.coordinator (Core 2026.10).
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
import math
import inspect
import re
from typing import Any, TypedDict

from homeassistant.exceptions import HomeAssistantError


MODEL = "S4SW-001X16EU"
RPC_TIMEOUT_S = 3.0
SOURCE = "homeassistant_shelly_rpc"


class RelayStatus(TypedDict):
    output: bool
    timer_started_at: float | None
    timer_duration: float | None
    timer_expires_at: float | None
    lease_remaining_s: float | None
    device_unixtime: float | None
    lease_proven: bool
    setup_valid: bool
    configuration_error: str | None
    source: str
    firmware: str
    firmware_id: str
    fingerprint: dict[str, str | int]
    known: bool


class ShellyLeaseError(HomeAssistantError):
    """Fail visibly, including whether an ON/OFF request may have been sent."""

    def __init__(self, code: str, reason: str, *, command_attempted: bool = False,
                 command_applied: bool = False) -> None:
        super().__init__(reason)
        self.code = code
        self.reason = reason
        self.command_attempted = command_attempted
        # Means RPC accepted, never physical load/SG response confirmation.
        self.command_applied = command_applied
        self.command_may_have_applied = command_attempted


@dataclass(frozen=True)
class _Binding:
    device_id: str
    unique_id: str
    config_entry_id: str
    coordinator: Any


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    value = float(value)
    return value if math.isfinite(value) else None


def _mac(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    value = value.replace(":", "").replace("-", "").lower()
    return value if re.fullmatch(r"[0-9a-f]{12}", value) else None


def _registry_entry(hass: Any, entity_id: str) -> Any:
    from homeassistant.helpers import entity_registry as er

    if not isinstance(entity_id, str) or not entity_id.startswith("switch."):
        raise ShellyLeaseError("not_configured", "Kies eerst de SG-schakelaar van Shelly 1 Gen4.")
    registry = er.async_get(hass)
    entry = registry.async_get(entity_id)
    if entry is None or getattr(entry, "platform", None) != "shelly":
        raise ShellyLeaseError("unsupported_source", "De SG-schakelaar moet via de lokale Shelly-integratie gekoppeld zijn.")
    if getattr(entry, "disabled_by", None) is not None:
        raise ShellyLeaseError("entity_disabled", "De gekozen SG-schakelaar is uitgeschakeld in Home Assistant.")
    if (not isinstance(getattr(entry, "device_id", None), str)
            or not entry.device_id
            or not isinstance(getattr(entry, "config_entry_id", None), str)
            or not entry.config_entry_id):
        raise ShellyLeaseError("unverified_mapping", "De koppeling met het Shelly-toestel is niet bevestigd.")
    unique_id = getattr(entry, "unique_id", "")
    if (not isinstance(unique_id, str) or not unique_id.endswith("-switch:0")
            or _mac(unique_id[:-len("-switch:0")]) is None):
        raise ShellyLeaseError("wrong_channel", "Gebruik uitsluitend uitgang 0 van Shelly 1 Gen4 voor SG.")
    return entry


def shelly_mapping_error(hass: Any, entity_id: str) -> str | None:
    """Read-only registry check; names alone never establish permission."""
    try:
        _registry_entry(hass, entity_id)
    except ShellyLeaseError as err:
        return err.reason
    except (AttributeError, ImportError):
        return "De lokale Shelly-koppeling kan niet gecontroleerd worden."
    return None


class ShellyLeaseAdapter:
    """One selected Shelly 1 Gen4 switch:0, with explicit timed ON and OFF."""

    def __init__(self, hass: Any, entity_id: str, *, before_on: Any = None) -> None:
        self.hass = hass
        self.entity_id = entity_id
        self.before_on = before_on
        self._lock = asyncio.Lock()
        self._binding_key: tuple[str, str, str] | None = None
        self._identity: tuple[str, str] | None = None
        self._firmware: tuple[str, str, str] | None = None
        self._fingerprint: dict[str, str | int] = {}

    @property
    def configured(self) -> bool:
        return isinstance(self.entity_id, str) and self.entity_id.startswith("switch.")

    @property
    def source(self) -> str:
        return SOURCE

    def mapping_error(self) -> str | None:
        return shelly_mapping_error(self.hass, self.entity_id)

    def _resolve(self) -> _Binding:
        try:
            entry = _registry_entry(self.hass, self.entity_id)
            from homeassistant.components.shelly.coordinator import get_rpc_coordinator_by_device_id

            coordinator = get_rpc_coordinator_by_device_id(self.hass, entry.device_id)
        except ShellyLeaseError:
            raise
        except (AttributeError, ImportError, KeyError) as err:
            raise ShellyLeaseError("unsupported_runtime", "De lokale Shelly-verbinding voor SG is niet beschikbaar.") from err
        if (coordinator is None or not callable(getattr(getattr(coordinator, "device", None), "call_rpc", None))):
            raise ShellyLeaseError("unavailable", "De SG-schakelaar is niet bereikbaar via Shelly.")
        binding = _Binding(entry.device_id, entry.unique_id, entry.config_entry_id, coordinator)
        key = (binding.device_id, binding.unique_id, binding.config_entry_id)
        if self._binding_key is not None and key != self._binding_key:
            raise ShellyLeaseError("binding_changed", "De SG-koppeling is gewijzigd; controleer de gekozen schakelaar opnieuw.")
        if _mac(getattr(coordinator, "mac", None)) != _mac(entry.unique_id[:-len("-switch:0")]):
            raise ShellyLeaseError("unverified_mapping", "De SG-uitgang hoort niet bij het bevestigde Shelly-toestel.")
        return binding

    async def _rpc(self, binding: _Binding, method: str, params: dict | None = None,
                   *, writing: bool = False) -> dict:
        try:
            # Both the native library timeout and outer cancellation are bounded.
            async with asyncio.timeout(RPC_TIMEOUT_S):
                if writing and params and params.get("on") is True and self.before_on is not None:
                    try:
                        allowed = self.before_on()
                    except Exception as err:
                        raise ShellyLeaseError("dispatch_changed", "De actuele SG-vrijgave is gewijzigd; de aanvraag wordt opnieuw beoordeeld.") from err
                    if inspect.isawaitable(allowed):
                        close = getattr(allowed, "close", None)
                        if callable(close):
                            close()
                        allowed = False
                    if allowed is not True:
                        raise ShellyLeaseError("dispatch_changed", "De actuele SG-vrijgave is gewijzigd; de aanvraag wordt opnieuw beoordeeld.")
                result = await binding.coordinator.device.call_rpc(method, params=params, timeout=RPC_TIMEOUT_S)
        except ShellyLeaseError:
            raise
        except Exception as err:
            # Do not reproduce host names, credentials or library payloads in UI.
            raise ShellyLeaseError("write_uncertain" if writing else "unavailable",
                                   "De SG-opdracht is niet bevestigd." if writing else "De actuele SG-status kan niet gelezen worden.",
                                   command_attempted=writing) from err
        if not isinstance(result, dict):
            raise ShellyLeaseError("invalid_response", "De Shelly heeft geen controleerbaar antwoord gegeven.",
                                   command_attempted=writing, command_applied=writing)
        return result

    async def _identity_check(self, binding: _Binding) -> tuple[str, str, str | None]:
        info = await self._rpc(binding, "Shelly.GetDeviceInfo")
        mac = _mac(info.get("mac"))
        device_id = info.get("id")
        if (type(info.get("gen")) is not int or info["gen"] != 4 or info.get("model") != MODEL
                or mac is None or device_id != f"shelly1g4-{mac}"):
            raise ShellyLeaseError("unsupported_device", "SG vereist de bevestigde Shelly 1 Gen4 met potentiaalvrij contact.")
        if mac != _mac(binding.unique_id[:-len("-switch:0")]):
            raise ShellyLeaseError("unverified_mapping", "De actuele Shelly-identiteit past niet bij de gekozen SG-uitgang.")
        if info.get("profile") not in (None, "switch"):
            raise ShellyLeaseError("wrong_role", "De Shelly-uitgang staat niet in de vereiste schakelrol.")
        firmware, firmware_id, app = info.get("ver"), info.get("fw_id"), info.get("app")
        if not all(isinstance(value, str) and value.strip() for value in (firmware, firmware_id, app)):
            raise ShellyLeaseError("firmware_unknown", "De Shelly-firmware kan niet bevestigd worden.")
        identity = (device_id, mac)
        if self._identity is not None and identity != self._identity:
            raise ShellyLeaseError("binding_changed", "Het SG-toestel is gewijzigd; controleer de koppeling opnieuw.")
        changed = self._firmware is not None and self._firmware != (firmware, firmware_id, app)
        self._identity = identity
        if self._firmware is None:
            self._firmware = (firmware, firmware_id, app)
        # Local persistent commissioning can compare this exact fingerprint
        # across reload/restart; the adapter does not silently approve a change.
        self._fingerprint = {"device_id": device_id, "model": MODEL, "gen": 4,
                             "firmware_id": firmware_id, "version": firmware,
                             "app": app, "profile": "switch", "component": "switch:0"}
        self._binding_key = (binding.device_id, binding.unique_id, binding.config_entry_id)
        return firmware, firmware_id, ("Shelly-firmware gewijzigd; test de lokale SG-beveiliging opnieuw." if changed else None)

    async def _configuration_error(self, binding: _Binding) -> str | None:
        config = await self._rpc(binding, "Switch.GetConfig", {"id": 0})
        if type(config.get("id")) is not int or config["id"] != 0:
            return "De SG-uitgang kan niet als uitgang 0 bevestigd worden."
        if config.get("in_mode") != "detached":
            return "Zet de Shelly-ingang voor SG op Detached."
        if config.get("initial_state") != "off":
            return "Zet de Shelly-opstarttoestand voor SG op Uit."
        if config.get("auto_on") is not False:
            return "Schakel automatisch inschakelen op de Shelly uit."
        return None

    async def _read(self, binding: _Binding, firmware: str, firmware_id: str,
                    configuration_error: str | None) -> RelayStatus:
        raw = await self._rpc(binding, "Switch.GetStatus", {"id": 0})
        if type(raw.get("id")) is not int or raw["id"] != 0 or type(raw.get("output")) is not bool:
            raise ShellyLeaseError("status_unknown", "De actuele SG-contactstand is onbekend.")
        sys = await self._rpc(binding, "Sys.GetStatus")
        clock = _number(sys.get("unixtime"))
        if clock is not None and clock <= 0:
            clock = None
        started, duration = _number(raw.get("timer_started_at")), _number(raw.get("timer_duration"))
        if started is None or duration is None or started < 0 or duration <= 0:
            started = duration = None
        expires = started + duration if started is not None and duration is not None else None
        remaining = expires - clock if expires is not None and clock is not None else None
        proven = (raw["output"] is True and remaining is not None and 0 < remaining <= duration + 1)
        if raw.get("errors"):
            configuration_error = configuration_error or "De Shelly meldt een fout; SG blijft tijdelijk geblokkeerd."
        return {"output": raw["output"], "timer_started_at": started, "timer_duration": duration,
                "timer_expires_at": expires, "lease_remaining_s": remaining,
                "device_unixtime": clock, "lease_proven": proven,
                "setup_valid": configuration_error is None, "configuration_error": configuration_error,
                "source": SOURCE, "firmware": firmware, "firmware_id": firmware_id,
                "fingerprint": dict(self._fingerprint), "known": True}

    async def async_check_mapping(self) -> RelayStatus:
        """Fresh read-only source, configuration, state and timer check."""
        return await self.get_status()

    async def get_status(self) -> RelayStatus:
        async with self._lock:
            binding = self._resolve()
            firmware, firmware_id, error = await self._identity_check(binding)
            error = error or await self._configuration_error(binding)
            return await self._read(binding, firmware, firmware_id, error)

    async def set_output(self, on: bool, lease_s: int | float | None = None) -> RelayStatus:
        if type(on) is not bool:
            raise ShellyLeaseError("invalid_command", "Gebruik een expliciete SG-stand Aan of Uit.")
        if on:
            if lease_s is None:
                raise ShellyLeaseError("lease_required", "SG inschakelen vereist een lokale aflooptimer.")
            return await self.set_on(lease_s)
        if lease_s is not None:
            raise ShellyLeaseError("invalid_command", "Een SG-uitschakelopdracht mag geen inschakeltimer bevatten.")
        return await self.set_off()

    async def set_on(self, lease_s: int | float = 300) -> RelayStatus:
        lease = _number(lease_s)
        if lease is None or not 60 <= lease <= 600:
            raise ShellyLeaseError("invalid_lease", "De SG-aflooptimer moet tussen 60 en 600 seconden liggen.")
        async with self._lock:
            binding = self._resolve()
            firmware, firmware_id, error = await self._identity_check(binding)
            error = error or await self._configuration_error(binding)
            if error:
                raise ShellyLeaseError("configuration_invalid", error)
            before = await self._read(binding, firmware, firmware_id, None)
            if not before["setup_valid"]:
                raise ShellyLeaseError("configuration_invalid", before["configuration_error"] or "Shelly meldt een fout.")
            if before["device_unixtime"] is None:
                raise ShellyLeaseError("clock_unknown", "De lokale Shelly-aflooptimer kan nog niet gecontroleerd worden.")
            if before["output"] and not before["lease_proven"]:
                raise ShellyLeaseError("unleased_on", "SG staat aan zonder bevestigde aflooptimer; controleer de handmatige wijziging.")
            current = self._resolve()
            if current.coordinator is not binding.coordinator:
                raise ShellyLeaseError("binding_changed", "De Shelly-verbinding is gewijzigd tijdens de SG-controle.")
            result = await self._rpc(binding, "Switch.Set", {"id": 0, "on": True, "toggle_after": lease}, writing=True)
            try:
                # was_on is deliberately not treated as the new physical state.
                if type(result.get("was_on")) is not bool:
                    raise ShellyLeaseError("invalid_response", "De SG-opdracht heeft geen geldig antwoord gegeven.")
                after = await self._read(binding, firmware, firmware_id, None)
                if (not after["output"] or not after["setup_valid"] or not after["lease_proven"]
                        or after["timer_duration"] != lease
                        or after["lease_remaining_s"] is None or after["lease_remaining_s"] < lease - 15):
                    raise ShellyLeaseError("lease_unconfirmed", "SG is niet bevestigd met de vereiste lokale aflooptimer.")
                if (before["output"] and before["timer_expires_at"] is not None
                        and after["timer_expires_at"] <= before["timer_expires_at"]):
                    raise ShellyLeaseError("lease_not_renewed", "De lokale SG-aflooptimer is niet verlengd; SG wordt vrijgegeven.")
                return after
            except ShellyLeaseError as err:
                raise ShellyLeaseError(err.code, err.reason, command_attempted=True, command_applied=True) from err

    async def set_off(self) -> RelayStatus:
        async with self._lock:
            binding = self._resolve()
            # Safe OFF remains available after firmware/config changes, but only
            # while the same selected native Shelly/contact identity is proven.
            firmware, firmware_id, error = await self._identity_check(binding)
            current = self._resolve()
            if current.coordinator is not binding.coordinator:
                raise ShellyLeaseError("binding_changed", "De Shelly-verbinding is gewijzigd tijdens de SG-controle.")
            await self._rpc(binding, "Switch.Set", {"id": 0, "on": False}, writing=True)
            try:
                after = await self._read(binding, firmware, firmware_id, error)
                if after["output"] is not False:
                    raise ShellyLeaseError("off_unconfirmed", "De SG-uitschakeling is nog niet bevestigd.")
                if after["timer_started_at"] is not None:
                    raise ShellyLeaseError("off_timer_active", "Het SG-contact is uit, maar de Shelly meldt nog een actieve timer; controleer automatisch inschakelen.")
                return after
            except ShellyLeaseError as err:
                raise ShellyLeaseError(err.code, err.reason, command_attempted=True, command_applied=True) from err
