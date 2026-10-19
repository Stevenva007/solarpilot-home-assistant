from homeassistant.components.binary_sensor import BinarySensorEntity, BinarySensorDeviceClass
from .entity import SolarEntity


async def async_setup_entry(hass, entry, async_add_entities):
    r = entry.runtime_data
    r.platforms.register("binary_sensor", async_add_entities, lambda: _entities(r))


def _entities(runtime):
    result = [SolarProblem(runtime, "problem", "Aandacht nodig")]
    water = getattr(runtime, "water", None)
    if water is not None and water.settings.get("enabled"):
        result.append(WaterWarning(runtime, "water_leak_warning", "Waterlekwaarschuwing"))
    return result


class SolarProblem(SolarEntity, BinarySensorEntity):
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def is_on(self):
        return bool(self.runtime.problem)

    @property
    def extra_state_attributes(self):
        return {"message": self.runtime.problem}


class WaterWarning(SolarEntity, BinarySensorEntity):
    """Advisory signal, including an unresolved earlier source warning."""
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    @property
    def available(self):
        return bool(self.runtime.water.settings.get("enabled"))

    @property
    def is_on(self):
        view = self.runtime.water.overview()
        if view.get("alert", {}).get("active") is True:
            return True
        settings = self.runtime.water.settings
        known = []
        if settings.get("leak_entity"):
            row = view.get("native_leak", {})
            known.append(row.get("fresh") is True and row.get("value") is False)
        if settings.get("flow_entity"):
            row = view.get("flow", {})
            known.append(row.get("fresh") is True and view.get("suspicion", {}).get("state") in ("clear", "pending"))
        return False if known and all(known) else None

    @property
    def extra_state_attributes(self):
        view = self.runtime.water.overview()
        return {"read_only": True, "alert": view.get("alert", {}),
                "suspicion": view.get("suspicion", {}),
                "description": "Metermelding of vermoeden; geen gegarandeerde lekdetectie en geen afsluiterbediening."}
