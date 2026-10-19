from homeassistant.components.select import SelectEntity
from .const import MODES, DEVICE_MODES
from .entity import SolarEntity
from .sg_control_api import SG_MANUAL_OPTIONS, async_set_sg_manual_control
from .wallbox_priority_api import WALLBOX_PRIORITY_OPTIONS, async_set_wallbox_priority, priority_choice_view


async def async_setup_entry(hass, entry, async_add_entities):
    r = entry.runtime_data
    r.platforms.register("select", async_add_entities, lambda: _entities(r))


def _entities(runtime):
    entities = [SolarMode(runtime), SGManualControl(runtime)] + [SolarMode(runtime, i) for i in runtime.configs]
    if getattr(runtime, "wallbox_priority", None) is not None:
        overview = runtime.wallbox_priority.overview()
        entities.append(WallboxPriorityDuration(runtime))
        entities.extend(WallboxPriorityDuration(runtime, key) for key, row in overview.get("devices", {}).items()
                        if row.get("eligible") is True)
        if isinstance(overview.get("sg_boost"), dict) and overview["sg_boost"].get("eligible") is True:
            entities.append(WallboxPriorityDuration(runtime, sg=True))
    return entities


class WallboxPriorityDuration(SolarEntity, SelectEntity):
    """The stored backend deadline survives HA and browser restarts."""
    _attr_icon = "mdi:timer-outline"
    _attr_translation_key = "wallbox_priority"
    _unrecorded_attributes = frozenset({"remaining_s", "observed_at"})

    def __init__(self, runtime, device_id=None, *, sg=False):
        super().__init__(runtime, "wallbox_priority_sg" if sg else "wallbox_priority",
                         "Wallbox voorrang · SG-duur" if sg else "Wallbox voorrang · duur", device_id)
        self._attr_options = list(WALLBOX_PRIORITY_OPTIONS)
        self.target = "dhw_extra" if sg else f"device:{device_id}" if device_id else "global"

    @property
    def available(self):
        return bool(not self._inactive() and self.runtime.data_loaded is True
                    and priority_choice_view(self.runtime, self.target) is not None)

    @property
    def current_option(self):
        row = priority_choice_view(self.runtime, self.target) or {}
        option = row.get("option")
        return option if type(option) is str and option in self._attr_options else None

    @property
    def extra_state_attributes(self):
        row = priority_choice_view(self.runtime, self.target) or {}
        return {key: row.get(key) for key in ("target", "expires_at", "remaining_s", "duration_s", "indefinite", "label")}

    async def async_select_option(self, option):
        if self._inactive():
            from homeassistant.exceptions import HomeAssistantError
            raise HomeAssistantError("Deze voorrangsschakelaar is vervallen; vernieuw de bediening.")
        await async_set_wallbox_priority(self.runtime, self.target, option,
                                        context=getattr(self, "_context", None))


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


class SGManualControl(SolarEntity, SelectEntity):
    """A timed policy preference, independent of the persistent enable switch."""
    _attr_icon = "mdi:heat-pump-outline"
    _attr_translation_key = "sg_manual_control"
    _attr_options = list(SG_MANUAL_OPTIONS)
    _unrecorded_attributes = frozenset({"remaining_s"})

    def __init__(self, runtime):
        super().__init__(runtime, "sg_manual_control", "SG-boost bediening")

    @property
    def available(self):
        return bool(not self._inactive() and self.runtime.data_loaded
                    and self.runtime.sg_boost.configured)

    @property
    def current_option(self):
        manual = self.runtime.sg_boost.manual_control_overview()
        mode, duration = manual.get("mode"), manual.get("duration_s")
        if mode == "auto":
            return "auto"
        if mode in ("on", "off") and type(duration) is int and duration in (1800, 3600):
            return f"{mode}_{duration // 60}"
        return None

    @property
    def extra_state_attributes(self):
        manual = self.runtime.sg_boost.manual_control_overview()
        return {key: manual.get(key) for key in ("expires_at", "remaining_s", "active", "reason")}

    async def async_select_option(self, option):
        if type(option) is not str or option not in SG_MANUAL_OPTIONS:
            from homeassistant.exceptions import HomeAssistantError
            raise HomeAssistantError("Kies een geldige tijdelijke SG-bediening.")
        mode, duration = ("auto", None) if option == "auto" else (option.split("_")[0], int(option.split("_")[1]) * 60)
        await async_set_sg_manual_control(
            self.runtime, mode, duration, context=getattr(self, "_context", None)
        )
