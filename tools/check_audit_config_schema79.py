#!/usr/bin/env python3
"""Check optional clearing through real HA selectors/schema; no HA services."""
from __future__ import annotations

import asyncio
from copy import deepcopy
from pathlib import Path
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Core 2026.10 installs its supported schema implementation before selectors
# import it. Match production import order instead of retaining an old alias.
import homeassistant
import voluptuous as vol
from custom_components.solar_pilot.config_flow import SolarPilotOptions
from custom_components.solar_pilot.ems import PHASE_DEFAULTS
from custom_components.solar_pilot.sg_config import SG_DEFAULTS


class PhaseFlow:
    def __init__(self):
        self.current = {**deepcopy(PHASE_DEFAULTS),
                        "monitor_power_entities": ["sensor.fictional_monitor"]}
        self.hass = SimpleNamespace(states=SimpleNamespace(get=lambda entity: None))
        self.saved = None

    def _base_options(self):
        return {"phase": self.current}

    def async_show_form(self, **kwargs):
        return kwargs

    async def _save(self, options):
        self.saved = options
        return {"saved": True}


class SGFlow:
    async def _sg_save_form(self, step_id, user_input, schema, *, cleared):
        current = {**deepcopy(SG_DEFAULTS), "zone_entities": ["climate.fictional_zone"]}
        return {"step_id": step_id, "data_schema": vol.Schema(schema(current)), "cleared": cleared}


async def main():
    flow = PhaseFlow()
    form = await SolarPilotOptions.async_step_phase_learning(flow)
    marker = next(key for key in form["data_schema"].schema
                  if getattr(key, "schema", key) == "monitor_power_entities")
    assert marker.description["suggested_value"] == ["sensor.fictional_monitor"]
    submitted = form["data_schema"]({})
    assert "monitor_power_entities" not in submitted, "Old monitor list reinserted by schema default"
    result = await SolarPilotOptions.async_step_phase_learning(flow, submitted)
    assert result == {"saved": True}
    assert flow.saved["phase"]["monitor_power_entities"] == []
    assert flow.saved["phase"]["limit_w"] == flow.current["limit_w"]

    form = await SolarPilotOptions.async_step_sg_sources(SGFlow())
    marker = next(key for key in form["data_schema"].schema
                  if getattr(key, "schema", key) == "zone_entities")
    assert marker.description["suggested_value"] == ["climate.fictional_zone"]
    submitted = form["data_schema"]({})
    assert "zone_entities" not in submitted, "Old SG zone list reinserted by schema default"
    assert form["data_schema"]({"zone_entities": []})["zone_entities"] == []
    # Existing _sg_save_form consumes the absent selection through its scoped
    # cleared list. Commissioning/split/profile checks remain production-owned.
    explicit = await SolarPilotOptions.async_step_sg_sources(SGFlow(), submitted)
    assert "zone_entities" in explicit["cleared"]
    print("OK: 2 real HA schema regressions; omitted monitor/SG-zone selections clear")


if __name__ == "__main__":
    asyncio.run(main())
