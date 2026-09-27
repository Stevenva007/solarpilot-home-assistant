from homeassistant.components.button import ButtonEntity
from .entity import SolarEntity


async def async_setup_entry(hass, entry, async_add_entities):
    r = entry.runtime_data
    buttons = [SolarButton(r, "reset", "Herstartcontrole en fouten wissen"),
               SolarButton(r, "reset_learning", "Leergegevens wissen"),
               SolarButton(r, "prepare_remove", "Verwijderen voorbereiden")]
    if r.dhw.configured:
        buttons += [SolarButton(r, "dhw_review", "Boilercontrole afronden"),
                    SolarButton(r, "dhw_takeover", "Boiler handmatig overnemen — verandert niets")]
    for i in r.configs:
        buttons += [SolarButton(r, "boost", "Boost 30 min — netstroom toegestaan", i),
                    SolarButton(r, "cancel_boost", "Boost annuleren", i),
                    SolarButton(r, "manual_start", "Manueel starten", i),
                    SolarButton(r, "manual_stop", "Manueel stoppen / vrijgeven", i),
                    SolarButton(r, "takeover", "Handmatig overnemen — schakelt NIET uit", i)]
    async_add_entities(buttons)


class SolarButton(SolarEntity, ButtonEntity):
    _attr_icon = "mdi:gesture-tap-button"

    async def async_press(self):
        if self.suffix == "dhw_review":
            await self.runtime.dhw.review()
        elif self.suffix == "dhw_takeover":
            await self.runtime.dhw.takeover()
        elif self.suffix == "reset_learning":
            await self.runtime.reset_learning()
        elif self.suffix == "reset":
            await self.runtime.reset()
        elif self.suffix == "prepare_remove":
            await self.runtime.prepare_removal()
        elif self.suffix == "takeover":
            await self.runtime.takeover(self.key)
        elif self.suffix == "boost":
            await self.runtime.boost(self.key)
        elif self.suffix == "manual_start":
            await self.runtime.manual_start(self.key)
        elif self.suffix == "manual_stop":
            await self.runtime.manual_stop(self.key)
        else:
            await self.runtime.cancel_boost(self.key)
