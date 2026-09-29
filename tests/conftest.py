"""Minimal HA doubles. These tests do NOT run real Home Assistant Core."""
import importlib
from pathlib import Path
import sys
import types

ROOT = Path(__file__).resolve().parents[1]
COMP = ROOT / "custom_components" / "solar_pilot"
for name, path in (("custom_components", ROOT / "custom_components"), ("custom_components.solar_pilot", COMP)):
    mod = types.ModuleType(name)
    mod.__path__ = [str(path)]
    sys.modules[name] = mod


def module(name):
    mod = types.ModuleType(name)
    sys.modules[name] = mod
    return mod


ha = module("homeassistant")
core = module("homeassistant.core")
core.callback = lambda f: f
exceptions = module("homeassistant.exceptions")
class HomeAssistantError(Exception):
    pass
exceptions.HomeAssistantError = HomeAssistantError
helpers = module("homeassistant.helpers")
event = module("homeassistant.helpers.event")
event.async_track_time_interval = lambda *args: lambda: None
event.async_track_state_change_event = lambda *args: lambda: None
storage = module("homeassistant.helpers.storage")
class Store:
    def __init__(self, *args):
        self.data = None
        self.saves = []
    async def async_load(self):
        return self.data
    async def async_save(self, data):
        from copy import deepcopy
        self.data = deepcopy(data)
        self.saves.append(deepcopy(data))
    def async_delay_save(self, callback, *args):
        self.data = callback()
storage.Store = Store
registry = module("homeassistant.helpers.entity_registry")
class Registry:
    def async_get_entity_id(self, *args):
        return None
registry.async_get = lambda hass: Registry()
helpers.entity_registry = registry
