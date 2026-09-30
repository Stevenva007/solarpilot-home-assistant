from homeassistant.components.select import SelectEntity
from .const import MODES, DEVICE_MODES
from .entity import SolarEntity


async def async_setup_entry(hass, entry, async_add_entities):
    r = entry.runtime_data
    r.platforms.register("select", async_add_entities, lambda: [SolarMode(r)] + [SolarMode(r, i) for i in r.configs])


class SolarMode(SolarEntity, SelectEntity):
    def __init__(self, runtime, device_id=None):
        super().__init__(runtime, "mode", "Modus", device_id)
        self._attr_options = DEVICE_MODES if device_id else MODES
        self._attr_translation_key = "device_mode" if device_id else "mode"
        self._attr_icon = "mdi:solar-power"

    @property
    def current_option(self):
        return self.runtime.device_modes.get(self.key, "disabled") if self.key else self.runtime.mode

    async def async_select_option(self, option):
        if self.key:
            await self.runtime.set_device_mode(self.key, option)
        else:
            await self.runtime.set_mode(option)
