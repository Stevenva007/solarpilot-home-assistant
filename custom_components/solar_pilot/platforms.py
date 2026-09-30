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

    @staticmethod
    def uid(entity):
        return entity._attr_unique_id

    def register(self, platform, add, factory):
        self.registrations[platform] = (add, factory)
        rows = factory()
        self.entities[platform] = {self.uid(e): e for e in rows}
        add(rows)

    async def refresh(self):
        for platform, (add, factory) in self.registrations.items():
            previous = self.entities.setdefault(platform, {})
            wanted = {self.uid(e): e for e in factory()}
            for uid in list(previous.keys() - wanted.keys()):
                old = previous[uid]
                if getattr(old, "hass", None) is not None:
                    value = old.async_remove()
                    if inspect.isawaitable(value):
                        await value
                # Preserve optional hub-entity registry customisations when a
                # telemetry group is temporarily disabled; purge only retired
                # SolarPilot virtual consumer entries, never source entities.
                if getattr(old, "entity_id", None) and getattr(old, "key", None) and old.key not in self.r.configs:
                    from homeassistant.helpers import entity_registry as er
                    registry = er.async_get(self.r.hass)
                    if hasattr(registry, "async_get") and registry.async_get(old.entity_id):
                        registry.async_remove(old.entity_id)
                previous.pop(uid, None)
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
