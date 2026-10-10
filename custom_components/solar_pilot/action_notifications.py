"""One persistent HA notification for checks that still need the user.

This reporter observes durable fault flags. It never changes a controller,
replays a command, or turns an ordinary wait/manual choice into a fault.
"""
from __future__ import annotations

import hashlib
import logging
import re

_LOGGER = logging.getLogger(__name__)
_MAX_ITEMS = 32
_MAX_REASON = 220


def _text(value, limit=_MAX_REASON):
    """Keep household labels/reasons bounded and inert in HA's Markdown."""
    plain = " ".join(str(value or "").split())[:limit]
    return re.sub(r"([\\`*_\[\]()!<>])", r"\\\1", plain)


class ActionRequiredNotifications:
    """Synchronise actionable faults independently of learning/restart notices."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.notification_id = f"solar_pilot_{runtime.entry.entry_id}_action_required"
        self._last_signature = ""
        self._active = False
        self._dirty = False
        self._transport_failed = False
        self._resync_after_restore = False

    def snapshot(self):
        """Persist delivery state, not household labels or fault text."""
        return {"schema": 1, "active": self._active, "signature": self._last_signature}

    def restore(self, raw):
        if (not isinstance(raw, dict) or type(raw.get("schema")) is not int or raw["schema"] != 1
                or not isinstance(raw.get("active"), bool) or not isinstance(raw.get("signature"), str)):
            return
        signature = raw["signature"]
        if ((raw["active"] and re.fullmatch(r"[0-9a-f]{64}", signature) is None)
                or (not raw["active"] and signature)):
            return
        self._active = raw["active"]
        self._last_signature = signature
        # HA notifications are process-local. A persisted receipt does not
        # prove the notice still exists after a real HA restart. Stable ids
        # make this one initial create idempotent without per-tick spam.
        self._resync_after_restore = self._active

    def _save_delivery(self):
        if self._dirty:
            self.runtime.store.async_delay_save(self.runtime._snapshot, 1)
            self._dirty = False

    def _items(self):
        r = self.runtime
        items = []
        sg = getattr(r, "sg_boost", None)
        if sg is not None:
            # SG owns only its assigned relay. Routine sun/source/rest waits
            # are dashboard states, not user-action faults or global pauses.
            view = sg.overview() if callable(getattr(sg, "overview", None)) else {}
            if isinstance(view, dict) and view.get("action_required") is True:
                reason = view.get("fault") or view.get("reason") or "De SG-koppeling vraagt controle"
                items.append("Extra zonneboost via SG: " + _text(reason)
                             + ". Open SolarPilot → Warmtepomp — Panasonic-regeling → Instellen en details; "
                             "controleer de toegewezen uitgang, één eigenaar en de lokaal aflopende toestemming. "
                             "Bevestig de contactmapping en lokale timer alleen na een echte ingebruiknamecontrole. "
                             "Panasonic en de overige geldige toestellen behouden hun eigen regeling.")

        configs = getattr(r, "configs", {})
        faults = getattr(r, "faults", {})
        reclaims = getattr(r, "reclaim_blocks", {})
        for device_id in sorted(set(faults) | set(reclaims)):
            name = _text(configs.get(device_id, {}).get("name") or "Toestel", 80)
            reasons = list(dict.fromkeys(str(x) for x in (faults.get(device_id), reclaims.get(device_id)) if x))
            if reasons:
                items.append(name + ": " + _text("; ".join(reasons))
                             + ". Open SolarPilot → Overzicht of Toestellen; controleer de actuele "
                             "toestelstand en kies Controle afronden als het toestel veilig uit is.")

        batteries = getattr(r, "battery_fleet", None)
        battery_configs = getattr(batteries, "configs", {})
        for battery_id, reason in sorted(getattr(getattr(batteries, "state", None), "faults", {}).items()):
            if reason:
                name = _text(battery_configs.get(battery_id, {}).get("name") or "Batterijregeling", 80)
                items.append(name + ": " + _text(reason)
                             + ". Open SolarPilot → Batterij; controleer de actuele batterijstand "
                             "en rond daarna de foutcontrole op het overzicht af.")

        if getattr(r, "problem_kind", "") == "source_configuration":
            reason = getattr(r, "problem", "") or "Een gekoppelde toestelbron of instelling klopt niet"
            items.append("Toestelbronnen controleren: " + _text(reason)
                         + ". Open SolarPilot → Toestellen → Toestellen beheren; "
                         "controleer de gekoppelde bronnen, de exclusieve vermogensmeter en de eenheid. "
                         "Controle afronden herstelt deze koppeling niet.")

        conflicts = getattr(r, "legacy_conflicts", lambda: [])()
        if conflicts:
            names = ", ".join(_text(row.get("name") or row.get("entity_id") or "Oude regeling", 80)
                              for row in conflicts[:8])
            items.append("Dubbele regeling actief: " + names
                         + ". Kies welke regeling het toestel bedient. Schakel de oude regeling "
                         "uit of pas de koppeling aan voordat je SolarPilot automatisch laat regelen. "
                         "SolarPilot schakelt de andere regeling niet zelf uit.")

        cause = getattr(r, "pause_cause", "")
        if cause == "internal_fault":
            items.append("Regeling gepauzeerd door een interne fout. Open Home Assistant → "
                         "Instellingen → Systeem → Logboeken en bekijk de SolarPilot-fout. "
                         "Rond daarna de controle op het SolarPilot-overzicht af en hervat Automatisch regelen.")
        elif cause == "command_fault":
            items.append("Regeling blijft gepauzeerd na een opdrachtfout. Open SolarPilot → Overzicht; "
                         "controleer de betrokken regeling en rond de controle af. "
                         "Kies daarna Automatisch regelen om te hervatten.")
        # Separate controllers may have the same display name and fault text.
        # Keep each affected controller; deduplicate only reasons per device.
        return items

    def message(self):
        items = self._items()
        if not items:
            return ""
        lines = ["Deze controles vragen nog jouw aandacht:", ""]
        lines.extend("- " + item for item in items[:_MAX_ITEMS])
        if len(items) > _MAX_ITEMS:
            lines.append(f"- Nog {len(items) - _MAX_ITEMS} controles: bekijk de overige regelingen op het SolarPilot-overzicht.")
        return "\n".join(lines)

    async def sync(self):
        """Create/update on change, dismiss after resolution, retry transport failures."""
        try:
            message = self.message()
            signature = hashlib.sha256(message.encode("utf-8")).hexdigest() if message else ""
            if (signature == self._last_signature and bool(message) == self._active
                    and not self._resync_after_restore):
                self._save_delivery()
                self._transport_failed = False
                return
            services = self.runtime.hass.services
            service = "create" if message else "dismiss"
            if not services.has_service("persistent_notification", service):
                return
            data = {"notification_id": self.notification_id}
            if message:
                data.update(title="SolarPilot: controle nodig", message=message)
            await services.async_call("persistent_notification", service, data, blocking=False)
            # Accepted delivery is deduplicated even if persisting its small
            # receipt fails. That persistence is retried without another notice.
            self._last_signature = signature
            self._active = bool(message)
            self._resync_after_restore = False
            self._dirty = True
            self._save_delivery()
        except Exception:
            # Notification availability must never become a controller fault.
            # Keep the old signature so the next cycle tries again.
            if not self._transport_failed:
                _LOGGER.warning("SolarPilot-controlebericht kon niet worden bijgewerkt; volgende cyclus probeert opnieuw",
                                exc_info=True)
            self._transport_failed = True
            return
        self._transport_failed = False
