"""Common native entities; no frontend timers or external JavaScript required."""
from homeassistant.helpers.entity import Entity, DeviceInfo
from .const import DOMAIN, NAME, VERSION


class SolarEntity(Entity):
    _attr_should_poll = False
    _attr_has_entity_name = True

    def __init__(self, runtime, suffix, name, device_id=None):
        self.runtime = runtime
        self.key = device_id
        self.suffix = suffix
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
        self.async_on_remove(self.runtime.subscribe(self.async_write_ha_state))
