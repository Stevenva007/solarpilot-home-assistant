"""Native policy switches. These switches never address a Wallbox entity."""
from homeassistant.components.switch import SwitchEntity
from .entity import SolarEntity


async def async_setup_entry(hass, entry, async_add_entities):
    r = entry.runtime_data
    r.platforms.register("switch", async_add_entities, lambda: _entities(r))


def _entities(r):
    entities = [SolarSwitch(r, "others_first", "Andere toestellen voorrang"),
                SolarSwitch(r, "learning", "Toestelvermogen en Wallbox-respons leren"),
                SolarSwitch(r, "auto_resume_after_restart", "Na herstart automatisch hervatten")]
    if r.dhw.configured:
        entities.append(SolarSwitch(r, "dhw_enabled", "Boiler automatisch regelen"))
    return entities


class SolarSwitch(SolarEntity, SwitchEntity):
    _attr_icon = "mdi:sort-priority-high"
    _unrecorded_attributes = frozenset({"profiles", "reported_interval_median_s", "response_p90_s"})

    @property
    def available(self):
        return self.runtime.data_loaded

    @property
    def is_on(self):
        if self.suffix == "auto_resume_after_restart":
            return self.runtime.auto_resume_after_restart is True
        if self.suffix == "dhw_enabled":
            return self.runtime.dhw.auto_enabled
        return self.runtime.others_first if self.suffix == "others_first" else self.runtime.learning.enabled

    @property
    def extra_state_attributes(self):
        if self.suffix == "auto_resume_after_restart":
            return {
                "on_meaning": "Pauze eindigt na een herstart zodra de opstartcontrole klaar is",
                "off_meaning": "Pauze blijft na een herstart behouden tot je zelf hervat",
                "observe_meaning": "Alleen bekijken blijft Alleen bekijken",
                "protection_meaning": "Een fout of voorbereiding voor verwijderen wordt nooit automatisch opgeheven",
                "default": "on",
            }
        if self.suffix == "dhw_enabled":
            return self.runtime.dhw.overview()
        if self.suffix == "others_first":
            return {"on_meaning": "Andere toestellen eerst; Wallbox gebruikt restoverschot",
                    "off_meaning": "Wallbox eerst; eigen flexibele lasten wijken",
                    "default": "on", "wallbox_read_only": True,
                    "wallbox_monitor_enabled": self.runtime.wallbox_settings["enabled"]}
        return self.runtime.learning_overview()

    async def async_turn_on(self, **kwargs):
        await self._set(True)

    async def async_turn_off(self, **kwargs):
        await self._set(False)

    async def _set(self, value):
        if self.suffix == "others_first":
            await self.runtime.set_others_first(value)
        elif self.suffix == "dhw_enabled":
            await self.runtime.dhw.set_enabled(value)
        elif self.suffix == "auto_resume_after_restart":
            await self.runtime.set_auto_resume_after_restart(value)
        else:
            await self.runtime.set_learning(value)
