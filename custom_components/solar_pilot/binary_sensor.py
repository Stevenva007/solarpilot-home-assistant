from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from .entity import SolarEntity


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([SolarProblem(entry.runtime_data, "problem", "Aandacht nodig")])


class SolarProblem(SolarEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self):
        return bool(self.runtime.problem)

    @property
    def extra_state_attributes(self):
        return {"message": self.runtime.problem}
