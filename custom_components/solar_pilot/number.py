from homeassistant.components.number import NumberEntity, NumberMode
from .entity import SolarEntity


async def async_setup_entry(hass, entry, async_add_entities):
    r = entry.runtime_data
    r.platforms.register("number", async_add_entities, lambda: _entities(r))


def _entities(r):
    return [SolarPriority(r, i) for i in r.configs]


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
