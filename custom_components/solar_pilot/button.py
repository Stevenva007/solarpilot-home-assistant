from homeassistant.components.button import ButtonEntity
from .entity import SolarEntity


async def async_setup_entry(hass, entry, async_add_entities):
    r = entry.runtime_data
    r.platforms.register("button", async_add_entities, lambda: _entities(r))


def _entities(r):
    buttons = [SolarButton(r, "reset", "Herstartcontrole en fouten wissen"),
               SolarButton(r, "reset_learning", "Apparaat-, lokale PV-, fase- en activiteitsleerdata wissen"),
               SolarButton(r, "prepare_remove", "Verwijderen voorbereiden")]
    buttons.append(SolarButton(r, "sg_boost_resume", "Automatische zonneboost hervatten"))
    for i in r.configs:
        if r.configs[i].get("kind") == "dishwasher":
            buttons += [SolarButton(r, "dishwasher_arm", "Eén afwasbeurt klaarzetten", i),
                        SolarButton(r, "dishwasher_cancel", "Afwasstart annuleren — programma niet stoppen", i),
                        SolarButton(r, "takeover", "Handmatig overnemen — schakelt NIET uit", i)]
            continue
        buttons += [SolarButton(r, "boost", "Boost 30 min — netstroom toegestaan", i),
                    SolarButton(r, "cancel_boost", "Boost annuleren", i),
                    SolarButton(r, "manual_start", "Manueel starten", i),
                    SolarButton(r, "manual_stop", "Manueel stoppen / vrijgeven", i),
                    SolarButton(r, "takeover", "Handmatig overnemen — schakelt NIET uit", i)]
    return buttons


class SolarButton(SolarEntity, ButtonEntity):
    _attr_icon = "mdi:gesture-tap-button"

    async def async_press(self):
        if self.suffix == "dishwasher_arm":
            await self.runtime.arm_dishwasher(self.key)
        elif self.suffix == "dishwasher_cancel":
            await self.runtime.cancel_dishwasher(self.key)
        elif self.suffix == "sg_boost_resume":
            await self.runtime.sg_boost.resume_automation()
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
