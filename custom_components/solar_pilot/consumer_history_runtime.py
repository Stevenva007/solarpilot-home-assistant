"""Read-only history recorder with bounded, batched Home Assistant storage."""
from __future__ import annotations

from datetime import datetime, timezone
import logging
import time

from homeassistant.helpers.storage import Store

from .consumer_history import ConsumerHistory
from .const import DOMAIN
from .dishwasher_meter import DishwasherMeter, METER_DEFAULTS

_LOGGER = logging.getLogger(__name__)


def history_storage_key(entry_id):
    return f"{DOMAIN}.{entry_id}.consumer_history"


class ConsumerHistoryRecorder:
    def __init__(self, hass, entry, configs, interval_s=5):
        zone = getattr(getattr(hass, "config", None), "time_zone", "Europe/Brussels")
        self.model = ConsumerHistory(zone)
        self.configs = configs
        self.hass, self.entry = hass, entry
        self.meters = {}
        self._meter_saved = {}
        self.store = Store(hass, 1, history_storage_key(entry.entry_id))
        self.interval_s = float(interval_s)
        self.max_gap_s = max(30, self.interval_s*2)
        self.loaded = False
        self._writable = False
        self._closed = False
        self.error = ""
        self._save_scheduled = False
        self._saved_revision = -1
        self._last_checkpoint = time.monotonic()

    @staticmethod
    def now():
        return datetime.now(timezone.utc)

    async def start(self):
        if self.loaded or self._closed:
            return
        try:
            data = await self.store.async_load()
            if self.model.restore(data, self.configs, self.now()) is False:
                raise ValueError("Unsupported or incomplete consumer history")
            stored = (data or {}).get("dishwasher_meters", {})
            if not isinstance(stored, dict):
                raise ValueError("Unreadable dishwasher meter history")
            self._meter_saved = stored
            self._writable = True
        except Exception:
            # History is optional telemetry and must not stop the controller.
            _LOGGER.exception("SolarPilot verbruikershistoriek kon niet geladen worden")
            self.error = "Bestaande historiek niet volledig geladen; opslag blijft behouden en nieuwe registratie is alleen tijdelijk"
        self.loaded = True

    def _checkpoint(self):
        self._save_scheduled = False
        self._saved_revision = self.model.revision
        self._last_checkpoint = time.monotonic()
        result = self.model.snapshot()
        result["dishwasher_meters"] = {**self._meter_saved,
            **{key: meter.snapshot() for key, meter in self.meters.items()}}
        return result

    def _maybe_save(self):
        if not self.loaded or not self._writable or self._closed or self._save_scheduled:
            return
        if self.model.revision != self._saved_revision or time.monotonic()-self._last_checkpoint >= 60:
            self._save_scheduled = True
            self.store.async_delay_save(self._checkpoint, 5)

    def _meter_key(self, device_id):
        cfg = self.configs[device_id]
        return "|".join((device_id, cfg.get("power_entity", ""), cfg.get("energy_entity", "")))

    def _meter(self, device_id):
        cfg = self.configs[device_id]
        if cfg.get("kind") != "dishwasher" or not cfg.get("power_entity"):
            return None
        key = self._meter_key(device_id)
        existing = self.meters.get(key)
        settings_key = tuple(cfg.get(name, default) for name, default in METER_DEFAULTS.items())
        if existing is None or existing.settings_key != settings_key:
            # New thresholds do not inherit elapsed activity or counter baselines.
            saved = existing.snapshot() if existing is not None else self._meter_saved.get(key)
            meter = DishwasherMeter(cfg)
            if not meter.restore(saved):
                self._writable = False
                self.error = "Meterhistoriek onleesbaar; bestaande opslag blijft behouden"
            self.meters[key] = meter
        return self.meters[key]

    def _exclusive_meter(self, device_id):
        cfg = self.configs[device_id]
        runtime = getattr(self.entry, "runtime_data", None)
        check = getattr(runtime, "_dedicated_meter", None)
        if not callable(check) or not check(device_id):
            return False
        energy = cfg.get("energy_entity")
        return not energy or not any(other_id != device_id and other.get("energy_entity") == energy
            for other_id, other in self.configs.items())

    def meter_brief(self, device_id):
        meter = self.meters.get(self._meter_key(device_id))
        if meter is None or not meter.latest:
            return None
        result = {k: v for k, v in meter.latest.items() if k not in ("energy_delta_kwh", "activity_changed")}
        wall = self.now().timestamp()
        stale = result["stale_s"]
        for prefix in ("power", "energy"):
            stamp = result.get(prefix + "_reported_at")
            if stamp is None or not -5 <= wall - stamp <= stale:
                result[prefix + "_valid"] = False
                result["power_w" if prefix == "power" else "energy_total_kwh"] = None
        if not -5 <= wall - result["observed_at"] <= stale:
            result.update(active=None, source="unknown")
        return result

    def observe(self, device_id, active, when, *, native_finished=False):
        if self._closed:
            return
        try:
            meter = self._meter(device_id)
            evidence = None
            if meter is not None:
                evidence = meter.sample(self.hass, when.astimezone(self.model.zone), active, native_finished,
                    dedicated=self._exclusive_meter(device_id))
                active = evidence["active"]
            before = self.model.devices.get(device_id, {}).get("open_id")
            self.model.observe(device_id, self.configs[device_id], active, when, max_gap_s=self.max_gap_s)
            if evidence is not None:
                row = self.model.devices[device_id]
                session = row["sessions"][-1] if row["sessions"] else None
                if session is not None:
                    if row["open_id"] is not None:
                        session["energy_partial"] = True
                        delta = evidence.get("energy_delta_kwh")
                        if before == row["open_id"] and delta is not None:
                            session["meter_energy_kwh"] = session.get("meter_energy_kwh", 0.) + delta
                        if evidence["source"] == "meter":
                            session["activity_source"] = "exclusive_power_meter"
                            if before != row["open_id"]:
                                session["start_reason"] += "; activiteit bevestigd door eigen vermogensmeter, programmafase onbekend"
                    elif before is not None and evidence["source"] == "meter" and active is False:
                        session["stop_reason"] = "Langdurig laag vermogen gemeten; afwasprogramma-einde niet bevestigd"
                        session["stop_source"] = "unknown"
                        session["stop_confirmed"] = False
                        day = self.model._day(when.timestamp())
                        row["days"][day]["stops"] = max(0, row["days"][day]["stops"] - 1)
                # Energy can change with no activity transition; persist it too.
                if evidence.get("energy_delta_kwh") is not None:
                    self.model._change(row)
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
        result = self.model.brief(device_id, self.now())
        if device_id in self.configs:
            result["meter"] = self.meter_brief(device_id)
        return result

    def access_sources(self, device_id):
        return self.model.access_sources(device_id)

    def detail(self, device_id, day=None):
        cfg = self.configs[device_id]
        self.model.ensure(device_id, cfg, self.now())
        result = self.model.detail(device_id, day, self.now())
        result["recording_error"] = self.error
        result["time_resolution_s"] = self.interval_s
        meter = self.meters.get(self._meter_key(device_id))
        if meter is not None:
            result["meter"] = self.meter_brief(device_id)
            result["meter_day"] = dict(meter.days.get(result["date"], {}))
            if not result["meter_day"].get("pairs", 0):
                result["meter_day"]["kwh"] = None
            result["note"] += " Bij de afwasmachine kan activiteit uit de eigen meter zijn afgeleid. Korte stille fasen blijven onderdeel van de waargenomen activiteit; een meter bewijst geen programma-einde. Gemeten kWh zijn alleen de geregistreerde tellerstappen, geen gegarandeerd volledig dag- of cyclusverbruik."
        return result

    async def close(self, *, persist=True):
        if self._closed:
            return
        self._closed = True
        for name in ("_async_cleanup_delay_listener", "_async_cleanup_final_write_listener"):
            cleanup = getattr(self.store, name, None)
            if callable(cleanup):
                try:
                    cleanup()
                except Exception:
                    _LOGGER.debug("SolarPilot verbruikershistoriek-listener kon niet sluiten", exc_info=True)
        self._save_scheduled = False
        self.model.pause_recording()
        if self.loaded and self._writable and persist:
            try:
                await self.store.async_save(self._checkpoint())
            except Exception:
                # Optional historian failure must not prevent core lease persistence.
                _LOGGER.exception("SolarPilot verbruikershistoriek kon niet worden opgeslagen bij afsluiten")
                self.error = "Laatste historie kon niet worden opgeslagen; eerdere checkpoint blijft behouden"
