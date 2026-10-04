"""Add/remove only SolarPilot virtual entities, without unloading the integration."""
from __future__ import annotations
import inspect
import logging

_LOGGER = logging.getLogger(__name__)


class LivePlatforms:
    def __init__(self, runtime):
        self.r = runtime
        self.registrations = {}
        self.entities = {}
        self.retiring = {}

    @staticmethod
    def uid(entity):
        return entity._attr_unique_id

    def register(self, platform, add, factory):
        self.registrations[platform] = (add, factory)
        rows = factory()
        self.entities[platform] = {self.uid(e): e for e in rows}
        add(rows)

    def retire_registry(self, entity):
        """Purge only retired virtual consumer entries, preserving hub settings."""
        for rows in self.retiring.values():
            for uid, old in list(rows.items()):
                if old is entity:
                    rows.pop(uid, None)
        if getattr(entity, "entity_id", None) and getattr(entity, "key", None) and entity.key not in self.r.configs:
            from homeassistant.helpers import entity_registry as er
            registry = er.async_get(self.r.hass)
            if hasattr(registry, "async_get") and registry.async_get(entity.entity_id):
                registry.async_remove(entity.entity_id)

    async def refresh(self):
        for platform, (add, factory) in self.registrations.items():
            previous = self.entities.setdefault(platform, {})
            retiring = self.retiring.setdefault(platform, {})
            wanted = {self.uid(e): e for e in factory()}
            for uid in list(previous.keys() - wanted.keys()):
                old = previous[uid]
                # add() schedules HA work; a retirement can arrive before hass
                # is assigned. The entity hook must reject that late addition.
                old._solar_pilot_retired = True
                if getattr(old, "hass", None) is not None:
                    value = old.async_remove()
                    if inspect.isawaitable(value):
                        await value
                # Preserve optional hub-entity registry customisations when a
                # telemetry group is temporarily disabled; purge only retired
                # SolarPilot virtual consumer entries, never source entities.
                self.retire_registry(old)
                if getattr(old, "hass", None) is None:
                    retiring[uid] = old
                previous.pop(uid, None)
            for uid in retiring.keys() & wanted.keys():
                # A queued add has not completed its removal. Reuse it if the
                # same identity returns, avoiding two competing HA additions.
                old = retiring.pop(uid)
                old._solar_pilot_retired = False
                previous[uid] = old
            for uid in previous.keys() & wanted.keys():
                # Runtime values stay on the SAME entity instance/listeners.
                previous[uid]._attr_device_info = wanted[uid]._attr_device_info
                previous[uid]._attr_name = wanted[uid]._attr_name
            new = [e for uid,e in wanted.items() if uid not in previous]
            if new:
                add(new)
                previous.update({self.uid(e):e for e in new})
        # Update only names of virtual SolarPilot devices; never source appliances.
        try:
            from homeassistant.helpers import device_registry as dr
            registry=dr.async_get(self.r.hass)
            from .const import DOMAIN
            for i,c in self.r.configs.items():
                device=registry.async_get_device(identifiers={(DOMAIN,f"{self.r.entry.entry_id}_{i}")})
                if device:
                    registry.async_update_device(device.id,name=c["name"])
        except (ImportError, AttributeError):
            pass  # HA test doubles may omit the optional device registry.
