from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from .entity import SolarEntity


async def async_setup_entry(hass, entry, async_add_entities):
    r = entry.runtime_data
    r.platforms.register("binary_sensor", async_add_entities, lambda: [SolarProblem(r, "problem", "Aandacht nodig")])


class SolarProblem(SolarEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self):
        return bool(self.runtime.problem)

    @property
    def extra_state_attributes(self):
        return {"message": self.runtime.problem}
