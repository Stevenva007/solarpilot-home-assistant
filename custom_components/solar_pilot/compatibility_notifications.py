"""Report a proven provider-contract break without any controller authority.

An unknown, missing or stale source is not an incompatibility. Only the bound,
loaded semantic inspector can raise or clear this separate advisory notice.
"""
from __future__ import annotations

from collections.abc import Mapping
import hashlib
import logging
import re

from .operation_source_evidence import valid_semantic_contract

_LOGGER = logging.getLogger(__name__)
_FINGERPRINT = re.compile(r"[0-9a-f]{64}")
_INCOMPATIBLE_DETAILS = frozenset({
    "operation_status_no_longer_special_status",
    "operation_status_mapping_changed",
    "action_or_status_getter_semantics_changed",
})


def _label(value):
    text = " ".join(value.split())[:80] if isinstance(value, str) else "onbekend"
    return text if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.+_-]{0,79}", text) else "onbekend"


class CompatibilityNotifications:
    """One idempotent notification per entry, separate from device faults."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.notification_id = f"solar_pilot_{runtime.entry.entry_id}_provider_compatibility"
        self._active = False
        self._signature = ""
        self._resync = False
        self._dirty = False
        self._transport_failed = False

    def snapshot(self):
        return {"schema": 1, "active": self._active, "signature": self._signature}

    def restore(self, value):
        if (not isinstance(value, dict) or type(value.get("schema")) is not int or value["schema"] != 1
                or type(value.get("active")) is not bool or not isinstance(value.get("signature"), str)):
            return
        signature = value["signature"]
        if (value["active"] and _FINGERPRINT.fullmatch(signature) is None
                or not value["active"] and signature):
            return
        self._active, self._signature = value["active"], signature
        self._resync = self._active

    @staticmethod
    def state(contract):
        if (not isinstance(contract, Mapping) or contract.get("provider_loaded") is not True
                or contract.get("native_device_registered") is not True):
            return "unknown"
        if (contract.get("compatibility_state") == "incompatible"
                and contract.get("reason_code") == "provider_semantics_changed"
                and contract.get("compatibility_detail") in _INCOMPATIBLE_DETAILS):
            return "incompatible"
        proof = contract.get("compatibility")
        if (contract.get("compatibility_state") == "compatible" and contract.get("status") == "verified"
                and isinstance(proof, Mapping) and valid_semantic_contract(dict(proof))):
            return "compatible"
        return "unknown"

    @staticmethod
    def message(contract):
        provider = contract.get("provider", {})
        provider = provider if isinstance(provider, Mapping) else {}
        integration = _label(provider.get("integration_version"))
        library = _label(provider.get("library_version"))
        return (f"De geladen Aquarea-koppeling ({integration}, bibliotheek {library}) gebruikt een "
                "gewijzigd of niet-herkend gegevenscontract. SolarPilot kan daardoor sommige Panasonic-statusfuncties "
                "niet betrouwbaar uitlezen. De eigen Panasonic-comfortregeling blijft behouden.\n\n"
                "De geplande onderhoudscontrole onderzoekt deze incompatibiliteit voor een volgende "
                "software-update op GitHub. De melding verdwijnt wanneer SolarPilot een compatibel "
                "geladen contract vaststelt.")

    def _save_delivery(self):
        if self._dirty:
            self.runtime.store.async_delay_save(self.runtime._snapshot, 1)
            self._dirty = False

    async def sync(self, source_contract=None):
        """Only notify/dismiss; never change a fault, lease, mode or appliance."""
        try:
            if source_contract is None:
                view = self.runtime.panasonic.overview()
                source_contract = view.get("source_contract") if isinstance(view, Mapping) else None
            state = self.state(source_contract)
            # Missing proof cannot clear an existing proven incompatibility.
            if state == "unknown":
                self._save_delivery()
                return
            message = self.message(source_contract) if state == "incompatible" else ""
            signature = hashlib.sha256(message.encode()).hexdigest() if message else ""
            if signature == self._signature and bool(message) == self._active and not self._resync:
                self._save_delivery()
                self._transport_failed = False
                return
            service = "create" if message else "dismiss"
            services = self.runtime.hass.services
            if not services.has_service("persistent_notification", service):
                return
            data = {"notification_id": self.notification_id}
            if message:
                data.update(title="SolarPilot: Aquarea-compatibiliteit", message=message)
            await services.async_call("persistent_notification", service, data, blocking=False)
            self._active, self._signature = bool(message), signature
            self._resync = False
            self._dirty = True
            self._save_delivery()
        except Exception:
            if not self._transport_failed:
                _LOGGER.warning("SolarPilot-compatibiliteitsbericht kon niet worden bijgewerkt; volgende cyclus probeert opnieuw",
                                exc_info=True)
            self._transport_failed = True
            return
        self._transport_failed = False
