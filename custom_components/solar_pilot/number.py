from homeassistant.components.number import NumberEntity, NumberMode
from .entity import SolarEntity
from .dhw import DHW_NUMBERS


async def async_setup_entry(hass, entry, async_add_entities):
    r = entry.runtime_data
    r.platforms.register("number", async_add_entities, lambda: _entities(r))


def _entities(r):
    entities = [SolarPriority(r, i) for i in r.configs]
    if r.dhw.configured:
        entities += [DHWNumber(r, k) for k in DHW_NUMBERS]
    return entities


class SolarPriority(SolarEntity, NumberEntity):
    _attr_native_min_value = 1
    _attr_native_max_value = 100
    _attr_native_step = 1
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:sort-numeric-ascending"

    def __init__(self, runtime, device_id):
        super().__init__(runtime, "priority", "Prioriteit", device_id)

    @property
    def native_value(self):
        if self.runtime.priority_board.active:
            return self.runtime.priority_board.effective_config(self.key)["priority"]
        return self.runtime.priorities.get(self.key, self.runtime.configs[self.key]["priority"])

    async def async_set_native_value(self, value):
        await self.runtime.set_priority(self.key, value)


class DHWNumber(SolarEntity, NumberEntity):
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:water-thermometer"

    def __init__(self, runtime, key):
        name, low, high, step, unit = DHW_NUMBERS[key]
        super().__init__(runtime, "dhw_" + key, name)
        self.setting_key = key
        self._attr_native_min_value = low
        self._attr_native_max_value = high
        self._attr_native_step = step
        self._attr_native_unit_of_measurement = unit

    @property
    def native_value(self):
        return self.runtime.dhw.settings[self.setting_key]

    async def async_set_native_value(self, value):
        await self.runtime.dhw.set_number(self.setting_key, value)
