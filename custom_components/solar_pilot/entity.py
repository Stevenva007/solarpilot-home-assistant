"""Common native entities; no frontend timers or external JavaScript required."""
from homeassistant.helpers.entity import Entity, DeviceInfo
from homeassistant.core import callback
from .const import DOMAIN, NAME, VERSION


class SolarEntity(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, runtime, suffix, name, device_id=None):
        self.runtime = runtime
        self.key = device_id
        self.suffix = suffix
        self._solar_pilot_subscribed = False
        self._attr_name = name
        self._attr_unique_id = f'{runtime.entry.entry_id}_{device_id + "_" if device_id else ""}{suffix}'
        if device_id:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, f"{runtime.entry.entry_id}_{device_id}")},
                name=runtime.configs[device_id]["name"], manufacturer=NAME,
                model="Virtuele verbruiker", via_device=(DOMAIN, runtime.entry.entry_id),
            )
        else:
            self._attr_device_info = DeviceInfo(
                identifiers={(DOMAIN, runtime.entry.entry_id)}, name=NAME,
                manufacturer=NAME, model="Lokale overschotregelaar", sw_version=VERSION,
            )

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        if self._inactive():
            # HA marks the entity ADDED and writes its first state after this
            # hook returns. A non-eager task removes it only after that finish.
            self.runtime.entry.async_create_task(
                self.hass, self._remove_late_entity(), "SolarPilot late virtual entity removal",
                eager_start=False)
            return
        self._subscribe_runtime()

    def _subscribe_runtime(self):
        if self._solar_pilot_subscribed or self._inactive():
            return
        unsubscribe = self.runtime.subscribe(self._live_write)
        self._solar_pilot_subscribed = True

        def remove_listener():
            self._solar_pilot_subscribed = False
            unsubscribe()

        self.async_on_remove(remove_listener)

    def _inactive(self):
        return (getattr(self, "_solar_pilot_retired", False) or self.runtime._closed
                or bool(self.key and self.key not in self.runtime.configs))

    async def _remove_late_entity(self):
        if not self._inactive():
            self._subscribe_runtime()
            self.async_write_ha_state()
            return
        await self.async_remove(force_remove=True)
        self.runtime.platforms.retire_registry(self)

    @callback
    def async_write_ha_state(self):
        if not self._inactive():
            super().async_write_ha_state()

    def _live_write(self):
        self.async_write_ha_state()
