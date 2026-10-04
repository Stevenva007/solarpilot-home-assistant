"""Actual registration against HA API doubles; no live HTTP server or devices."""
from dataclasses import dataclass
import importlib.util
from pathlib import Path
import sys
from types import ModuleType, SimpleNamespace

import pytest

from custom_components.solar_pilot.const import VERSION


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "custom_components/solar_pilot/frontend.py"


@pytest.fixture
def frontend_registration(monkeypatch):
    frontend_api = ModuleType("homeassistant.components.frontend")
    components = ModuleType("homeassistant.components")
    http_api = ModuleType("homeassistant.components.http")
    calls = []
    urls = set()
    panels = {}

    @dataclass
    class StaticPathConfig:
        url_path: str
        path: str
        cache_headers: bool = True

    class Http:
        fail = False

        async def async_register_static_paths(self, configs):
            calls.append(("static", list(configs)))
            if self.fail:
                raise OSError("Static route unavailable")

    def add_extra_js_url(hass, url, es5=False):
        # The HA API's default registers an ES module, not an ES5 script.
        calls.append(("extra", url, es5))
        urls.add(url)

    def remove_extra_js_url(hass, url, es5=False):
        calls.append(("remove_extra", url, es5))
        urls.remove(url)

    def register_panel(hass, **kwargs):
        calls.append(("panel", kwargs))
        panels[kwargs["frontend_url_path"]] = kwargs

    def remove_panel(hass, path, **kwargs):
        calls.append(("remove_panel", path, kwargs))
        panels.pop(path, None)

    frontend_api.add_extra_js_url = add_extra_js_url
    frontend_api.remove_extra_js_url = remove_extra_js_url
    frontend_api.async_register_built_in_panel = register_panel
    frontend_api.async_remove_panel = remove_panel
    components.frontend = frontend_api
    http_api.StaticPathConfig = StaticPathConfig
    monkeypatch.setitem(sys.modules, components.__name__, components)
    monkeypatch.setitem(sys.modules, frontend_api.__name__, frontend_api)
    monkeypatch.setitem(sys.modules, http_api.__name__, http_api)
    monkeypatch.setattr(sys.modules["homeassistant.core"], "HomeAssistant", SimpleNamespace,
                        raising=False)
    spec = importlib.util.spec_from_file_location("custom_components.solar_pilot._frontend51", SOURCE)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    hass = SimpleNamespace(data={}, http=Http())
    return module, hass, calls, urls, panels


@pytest.mark.asyncio
async def test_sidebar_and_extra_bundle_use_the_same_release_module_after_static_registration(frontend_registration):
    module, hass, calls, urls, panels = frontend_registration
    await module.async_register_frontend(hass)

    assert [call[0] for call in calls] == ["static", "extra", "panel"]
    panel = panels["solar-pilot"]
    config = panel["config"]["_panel_custom"]
    assert config["module_url"] == calls[1][1]
    assert config["module_url"] == f"/solar_pilot_static/solar-pilot-card.js?v={VERSION}"
    assert "js_url" not in config
    assert calls[1][2] is False
    assert urls == {config["module_url"]}
    assert config["name"] == "solar-pilot-card"
    assert panel["update"] is True and panel["component_name"] == "custom"
    assert panel["require_admin"] is False
    assert config["trust_external"] is False and config["embed_iframe"] is False


@pytest.mark.asyncio
async def test_registered_directory_contains_the_exact_release_bundle_and_help(frontend_registration):
    module, hass, calls, urls, panels = frontend_registration
    await module.async_register_frontend(hass)
    registered = calls[0][1]
    assert len(registered) == 1
    config = registered[0]
    assert config.url_path == "/solar_pilot_static"
    assert config.cache_headers is False
    path = Path(config.path)
    assert path.resolve() == (ROOT / "custom_components/solar_pilot/frontend").resolve()
    card = path / "solar-pilot-card.js"
    assert f"SolarPilot {VERSION}." in card.read_text(encoding="utf-8")
    assert (path / "option-help.js").is_file()
    assert (path / "option-help.json").is_file()
    assert len(urls) == 1 and len(panels) == 1


@pytest.mark.asyncio
async def test_reload_replaces_panel_without_duplicating_static_route_or_extra_module(frontend_registration):
    module, hass, calls, urls, panels = frontend_registration
    await module.async_register_frontend(hass)
    module.async_unregister_frontend(hass, final=False)
    assert not panels and len(urls) == 1
    await module.async_register_frontend(hass)
    await module.async_register_frontend(hass)

    assert [call[0] for call in calls].count("static") == 1
    assert [call[0] for call in calls].count("extra") == 1
    assert [call[0] for call in calls].count("panel") == 3
    assert len(urls) == 1 and len(panels) == 1
    assert all(call[1]["update"] for call in calls if call[0] == "panel")


@pytest.mark.asyncio
async def test_final_removal_unloads_only_the_registered_module_and_retains_static_route(frontend_registration):
    module, hass, calls, urls, panels = frontend_registration
    await module.async_register_frontend(hass)
    urls.add("/another-integration/card.js")
    module.async_unregister_frontend(hass, final=True)
    assert not panels
    assert urls == {"/another-integration/card.js"}

    await module.async_register_frontend(hass)
    assert len(panels) == 1 and len(urls) == 2
    assert [call[0] for call in calls].count("static") == 1
    assert [call[0] for call in calls].count("remove_extra") == 1
    assert [call[0] for call in calls].count("extra") == 2


@pytest.mark.asyncio
async def test_failed_static_registration_does_not_publish_a_broken_panel_and_can_be_retried(frontend_registration):
    module, hass, calls, urls, panels = frontend_registration
    hass.http.fail = True
    with pytest.raises(OSError, match="Static route unavailable"):
        await module.async_register_frontend(hass)
    assert not urls and not panels
    assert not hass.data[module._DATA_KEY].get("static_registered")

    hass.http.fail = False
    await module.async_register_frontend(hass)
    assert len(urls) == 1 and len(panels) == 1
    assert [call[0] for call in calls] == ["static", "static", "extra", "panel"]
