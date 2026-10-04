"""Self-contained SolarPilot frontend registration.

The frontend bundle lives inside the custom integration itself.  Users do not
need to copy a second file into /config/www and do not need to maintain a
Lovelace resource manually.
"""
from __future__ import annotations

from pathlib import Path
import logging

from homeassistant.components import frontend as ha_frontend
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant

from .const import DOMAIN, VERSION

_LOGGER = logging.getLogger(__name__)

_DATA_KEY = f"{DOMAIN}_frontend"
_STATIC_URL = "/solar_pilot_static"
_PANEL_URL = "solar-pilot"
_CARD_URL = f"{_STATIC_URL}/solar-pilot-card.js?v={VERSION}"


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Register the bundled card and a sidebar Control Center."""
    state = hass.data.setdefault(_DATA_KEY, {})
    if not state.get("static_registered"):
        frontend_dir = Path(__file__).parent / "frontend"
        await hass.http.async_register_static_paths(
            [StaticPathConfig(_STATIC_URL, str(frontend_dir), False)]
        )
        state["static_registered"] = True

    if not state.get("js_registered"):
        ha_frontend.add_extra_js_url(hass, _CARD_URL)
        state["js_registered"] = True

    # update=True makes reloads idempotent on current Home Assistant versions.
    ha_frontend.async_register_built_in_panel(
        hass,
        component_name="custom",
        sidebar_title="SolarPilot",
        sidebar_icon="mdi:solar-power-variant",
        frontend_url_path=_PANEL_URL,
        config={
            "_panel_custom": {
                "name": "solar-pilot-card",
                "embed_iframe": False,
                "trust_external": False,
                # Match add_extra_js_url's default module loading. A classic
                # script uses a separate loader/cache and shares global const
                # declarations across release URLs in an open browser session.
                "module_url": _CARD_URL,
            }
        },
        require_admin=False,
        update=True,
    )
    state["panel_registered"] = True


def async_unregister_frontend(hass: HomeAssistant, *, final: bool = False) -> None:
    """Remove visible frontend registrations.

    Home Assistant has no public API to unregister a static HTTP path at runtime;
    that path disappears after the normal restart which also completes manual
    custom-component removal.
    """
    state = hass.data.get(_DATA_KEY, {})
    try:
        ha_frontend.async_remove_panel(hass, _PANEL_URL, warn_if_unknown=False)
    except TypeError:
        # Compatibility with older signatures.
        ha_frontend.async_remove_panel(hass, _PANEL_URL)
    state["panel_registered"] = False

    if final and state.get("js_registered"):
        try:
            remover = getattr(ha_frontend, "remove_extra_js_url", None)
            if remover is not None:
                remover(hass, _CARD_URL)
        except (AttributeError, ValueError):
            _LOGGER.debug("SolarPilot extra JS URL was already absent")
        state["js_registered"] = False
        # Keep static_registered in memory until restart; re-registering the same
        # static path before a restart is not necessary and can conflict.
