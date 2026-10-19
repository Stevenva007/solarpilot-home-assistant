"""Deliver one advisory notice per water episode, without control authority.

Delivery receipts survive restarts. Restoring a receipt never recreates an old
notice: a new, currently evidenced episode is required for a new delivery.
"""
from __future__ import annotations

import asyncio
from collections.abc import Mapping
import logging
import re

_LOGGER = logging.getLogger(__name__)
_EPISODE = re.compile(r"[a-f0-9]{24}")
_MAX_EPISODES = 512
_CAUSES = frozenset({"native_leak", "continuous_flow", "both"})


class WaterNotifications:
    """Separate persistent water notices, with a bounded delivery ledger."""

    def __init__(self, runtime):
        self.runtime = runtime
        self.notification_id = f"solar_pilot_{runtime.entry.entry_id}_water_advisory"
        self._active = False
        self._episode_id = None
        self._delivered = []
        self._dirty = False
        self._transport_failed = False
        self._lock = asyncio.Lock()

    def snapshot(self):
        return {"schema": 1, "active": self._active, "episode_id": self._episode_id,
                "delivered_episodes": list(self._delivered)}

    def restore(self, raw):
        if (not isinstance(raw, Mapping) or type(raw.get("schema")) is not int or raw["schema"] != 1
                or type(raw.get("active")) is not bool
                or not isinstance(raw.get("delivered_episodes"), list)):
            return
        delivered = raw["delivered_episodes"]
        if (len(delivered) > _MAX_EPISODES
                or any(not isinstance(value, str) or _EPISODE.fullmatch(value) is None for value in delivered)
                or len(set(delivered)) != len(delivered)):
            return
        episode = raw.get("episode_id")
        if (raw["active"] and (not isinstance(episode, str) or episode not in delivered)
                or not raw["active"] and episode is not None):
            return
        self._active, self._episode_id = raw["active"], episode
        self._delivered = list(delivered)
        # No resynchronization: even when HA discarded the displayed notice,
        # a receipt must not announce the same physical episode after restart.

    @staticmethod
    def _current_alert(view):
        if not isinstance(view, Mapping):
            return None
        alert = view.get("alert")
        if (not isinstance(alert, Mapping) or type(alert.get("active")) is not bool
                or alert.get("evidence_current") is not True or not isinstance(alert.get("cause"), str)
                or alert["cause"] not in _CAUSES
                or not isinstance(alert.get("episode_id"), str)
                or _EPISODE.fullmatch(alert["episode_id"]) is None):
            return None
        return {key: alert[key] for key in ("active", "cause", "episode_id")}

    @staticmethod
    def message(cause):
        if cause == "native_leak":
            title = "SolarPilot: waterleksignaal"
            text = ("De gekoppelde watermeter meldt een mogelijk lek. Dit is het actuele signaal van die bron. "
                    "Controleer de bronmelding en de waterinstallatie.")
        elif cause == "both":
            title = "SolarPilot: waterleksignaal en aanhoudend verbruik"
            text = ("De gekoppelde watermeter meldt een mogelijk lek. Daarnaast is gedurende de ingestelde tijd "
                    "aanhoudend waterdebiet boven de ingestelde drempel gemeten. De debietwaarschuwing "
                    "stelt op zichzelf geen fysiek lek vast. Controleer de bronmelding en de waterinstallatie.")
        else:
            title = "SolarPilot: aanhoudend watergebruik"
            text = ("Er is gedurende de ingestelde tijd aanhoudend waterdebiet boven de ingestelde drempel "
                    "gemeten. Dit kan normaal verbruik zijn of op een lek wijzen; SolarPilot heeft hiermee "
                    "geen fysiek lek vastgesteld. Controleer het actuele watergebruik.")
        return title, (text + "\n\nOpen SolarPilot → Water voor de actuele metingen en historie. "
                       "SolarPilot sluit geen waterkraan en bedient geen toestel.")

    def _save_delivery(self):
        if self._dirty:
            self.runtime.store.async_delay_save(self.runtime._snapshot, 1)
            self._dirty = False

    async def sync(self, view=None):
        """Only create/dismiss our own notice; transport failures are retried."""
        async with self._lock:
            try:
                water = self.runtime.water
                settings = water.settings
                if not isinstance(settings, Mapping):
                    self._save_delivery()
                    return
                disabled = settings.get("enabled") is False or settings.get("notifications") is False
                permitted = settings.get("enabled") is True and settings.get("notifications") is True
                if disabled:
                    alert = None
                    dismiss = self._active
                elif not permitted:
                    self._save_delivery()
                    return
                else:
                    if view is None:
                        view = water.overview()
                    alert = self._current_alert(view)
                    if alert is None:
                        self._save_delivery()
                        return
                    dismiss = (not alert["active"] and self._active
                               and alert["episode_id"] == self._episode_id)
                create = bool(alert is not None and alert["active"]
                              and alert["episode_id"] not in self._delivered)
                if not create and not dismiss:
                    self._save_delivery()
                    self._transport_failed = False
                    return
                service = "create" if create else "dismiss"
                services = self.runtime.hass.services
                if not services.has_service("persistent_notification", service):
                    return
                data = {"notification_id": self.notification_id}
                if create:
                    title, message = self.message(alert["cause"])
                    data.update(title=title, message=message)
                await services.async_call("persistent_notification", service, data, blocking=False)
                if create:
                    self._episode_id = alert["episode_id"]
                    self._delivered = (self._delivered + [self._episode_id])[-_MAX_EPISODES:]
                else:
                    self._episode_id = None
                self._active = create
                self._dirty = True
                self._save_delivery()
            except Exception:
                if not self._transport_failed:
                    _LOGGER.warning("SolarPilot-waterbericht kon niet worden bijgewerkt; volgende cyclus probeert opnieuw",
                                    exc_info=True)
                self._transport_failed = True
                return
            self._transport_failed = False
