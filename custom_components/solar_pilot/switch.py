"""Native policy switches. These switches never address a Wallbox entity."""
from homeassistant.components.switch import SwitchEntity
from .entity import SolarEntity
from .wallbox_priority_api import async_set_wallbox_priority, priority_choice_view


async def async_setup_entry(hass, entry, async_add_entities):
    r = entry.runtime_data
    r.platforms.register("switch", async_add_entities, lambda: _entities(r))


def _entities(r):
    entities = [SolarSwitch(r, "others_first", "Andere toestellen voorrang"),
                SolarSwitch(r, "learning", "Toestelvermogen en Wallbox-respons leren"),
                SolarSwitch(r, "auto_resume_after_restart", "Na herstart automatisch hervatten")]
    entities.append(SolarSwitch(r, "sg_boost_enabled", "Automatische zonneboost"))
    if getattr(r, "wallbox_priority", None) is not None:
        overview = r.wallbox_priority.overview()
        entities.append(WallboxPrioritySwitch(r))
        entities.extend(WallboxPrioritySwitch(r, key) for key, row in overview.get("devices", {}).items()
                        if row.get("eligible") is True)
        if isinstance(overview.get("sg_boost"), dict) and overview["sg_boost"].get("eligible") is True:
            entities.append(WallboxPrioritySwitch(r, sg=True))
    return entities


class WallboxPrioritySwitch(SolarEntity, SwitchEntity):
    """ON selects thirty minutes; the companion select exposes every duration."""
    _attr_icon = "mdi:ev-station"
    _unrecorded_attributes = frozenset({"remaining_s", "observed_at"})

    def __init__(self, runtime, device_id=None, *, sg=False):
        super().__init__(runtime, "wallbox_priority_sg" if sg else "wallbox_priority",
                         "Wallbox voorrang geven · SG-zonneboost" if sg else "Wallbox voorrang geven", device_id)
        self.target = "dhw_extra" if sg else f"device:{device_id}" if device_id else "global"

    @property
    def available(self):
        return bool(not self._inactive() and self.runtime.data_loaded is True
                    and priority_choice_view(self.runtime, self.target) is not None)

    @property
    def is_on(self):
        row = priority_choice_view(self.runtime, self.target)
        return row.get("active") is True if row is not None else None

    @property
    def extra_state_attributes(self):
        row = priority_choice_view(self.runtime, self.target) or {}
        return {**{key: row.get(key) for key in ("target", "option", "expires_at", "remaining_s", "duration_s",
                                                "indefinite", "label")},
                "on_duration_s": 1800, "off_meaning": "Automatisch volgens de bestaande voorrangsregels",
                "wallbox_read_only": True}

    async def async_turn_on(self, **kwargs):
        await self._set_priority("30m")

    async def async_turn_off(self, **kwargs):
        await self._set_priority("auto")

    async def _set_priority(self, option):
        if self._inactive():
            from homeassistant.exceptions import HomeAssistantError
            raise HomeAssistantError("Deze voorrangsschakelaar is vervallen; vernieuw de bediening.")
        await async_set_wallbox_priority(self.runtime, self.target, option,
                                        context=getattr(self, "_context", None))


class SolarSwitch(SolarEntity, SwitchEntity):
    _attr_icon = "mdi:sort-priority-high"
    # Keep full models available to the dashboard and exports; Recorder only
    # needs the switch state and compact learning summary, not each catalogue.
    _unrecorded_attributes = frozenset({
        "profiles", "reported_interval_median_s", "response_p90_s",
        "pv_model", "phase_learning", "thermal_model",
        # Presentation clocks remain live, but an unchanged idle SG policy
        # must not create a new Recorder row merely because it was rendered.
        "observed_at", "relay_observed_at", "relay_valid_until",
    })

    @property
    def available(self):
        return self.runtime.data_loaded

    @property
    def is_on(self):
        if self.suffix == "auto_resume_after_restart":
            return self.runtime.auto_resume_after_restart is True
        if self.suffix == "sg_boost_enabled":
            return self.runtime.sg_boost.overview().get("enabled") is True
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
        if self.suffix == "sg_boost_enabled":
            return self.runtime.sg_boost.overview()
        if self.suffix == "others_first":
            return {"on_meaning": "Andere toestellen eerst; Wallbox gebruikt restoverschot",
                    "off_meaning": "Wallbox eerst; eigen flexibele lasten wijken",
                    "default": "on", "wallbox_read_only": True,
                    "wallbox_monitor_enabled": self.runtime.wallbox_settings["enabled"]}
        reader = getattr(self.runtime, "sensor_overview", None)
        return reader("learning") if callable(reader) else self.runtime.learning_overview()

    async def async_turn_on(self, **kwargs):
        await self._set(True)

    async def async_turn_off(self, **kwargs):
        await self._set(False)

    async def _set(self, value):
        if self.suffix == "others_first":
            await self.runtime.set_others_first(value)
        elif self.suffix == "sg_boost_enabled":
            await self.runtime.sg_boost.set_enabled(value)
        elif self.suffix == "auto_resume_after_restart":
            await self.runtime.set_auto_resume_after_restart(value)
        else:
            await self.runtime.set_learning(value)
