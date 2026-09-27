"""Read-only history recorder with bounded, batched Home Assistant storage."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import time

from homeassistant.helpers.storage import Store

from .consumer_history import ConsumerHistory
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)


def history_storage_key(entry_id):
    return f"{DOMAIN}.{entry_id}.consumer_history"


class ConsumerHistoryRecorder:
    def __init__(self, hass, entry, configs, interval_s=5):
        zone = getattr(getattr(hass, "config", None), "time_zone", "Europe/Brussels")
        self.model = ConsumerHistory(zone)
        self.configs = configs
        self.store = Store(hass, 1, history_storage_key(entry.entry_id))
        self.interval_s = float(interval_s)
        self.max_gap_s = max(30, self.interval_s*2)
        self.loaded = False
        self.error = ""
        self._save_scheduled = False
        self._saved_revision = -1
        self._last_checkpoint = time.monotonic()

    @staticmethod
    def now():
        return datetime.now(timezone.utc)

    async def start(self):
        try:
            data = await self.store.async_load() or {}
            self.model.restore(data, self.configs, self.now())
        except Exception:
            # History is optional telemetry and must not stop the controller.
            _LOGGER.exception("SolarPilot verbruikershistoriek kon niet geladen worden")
            self.error = "Bestaande historiek kon niet worden geladen; eerdere perioden zijn onbekend"
        self.loaded = True

    def _checkpoint(self):
        self._save_scheduled = False
        self._saved_revision = self.model.revision
        self._last_checkpoint = time.monotonic()
        return self.model.snapshot()

    def _maybe_save(self):
        if not self.loaded or self._save_scheduled:
            return
        if self.model.revision != self._saved_revision or time.monotonic()-self._last_checkpoint >= 60:
            self._save_scheduled = True
            self.store.async_delay_save(self._checkpoint, 5)

    def observe(self, device_id, active, when):
        try:
            self.model.observe(device_id, self.configs[device_id], active, when, max_gap_s=self.max_gap_s)
            self._maybe_save()
        except Exception:
            if not self.error:
                _LOGGER.exception("SolarPilot verbruikershistoriek kon niet worden bijgewerkt")
            self.error = "Historiekregistratie onvolledig; controleer het Home Assistant-logboek"

    def command(self, device_id, watts, reason):
        self.model.command(device_id, self.configs[device_id], watts, reason, self.now())

    def confirm(self, device_id):
        self.model.confirm(device_id)

    def failure(self, device_id, reason):
        self.model.failure(device_id, self.configs[device_id], reason, self.now())
        self._maybe_save()

    def event(self, device_id, reason):
        self.model.event(device_id, self.configs[device_id], reason, self.now())
        self._maybe_save()

    def brief(self, device_id):
        return self.model.brief(device_id, self.now())

    def detail(self, device_id, day=None):
        cfg = self.configs[device_id]
        self.model.ensure(device_id, cfg, self.now())
        result = self.model.detail(device_id, day, self.now())
        result["recording_error"] = self.error
        result["time_resolution_s"] = self.interval_s
        return result

    async def close(self):
        self.model.pause_recording()
        if self.loaded:
            try:
                await self.store.async_save(self._checkpoint())
            except Exception:
                # Optional historian failure must not prevent core lease persistence.
                _LOGGER.exception("SolarPilot verbruikershistoriek kon niet worden opgeslagen bij afsluiten")
                self.error = "Laatste historie kon niet worden opgeslagen; eerdere checkpoint blijft behouden"
