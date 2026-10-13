"""Actual Core source-contract probe, called by the real-HA lifecycle gate.

Only fictitious local entities are constructed. One ordinary Core tracker setup
render prepares evidence; production diagnostics must not render or refresh it.
No service, network request, option mutation or physical device is involved.
"""
from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import patch


async def verify_source_contract(hass):
    from homeassistant.components.sensor import DATA_COMPONENT
    from homeassistant.components.template.sensor import StateSensorEntity
    from homeassistant.helpers import entity_registry as er
    from homeassistant.helpers.entity_component import EntityComponent
    from homeassistant.helpers.event import TrackTemplate, TrackTemplateResultInfo
    from homeassistant.helpers.template import Template
    from homeassistant.helpers.template.render_info import RenderInfo

    from custom_components.solar_pilot.source_diagnostics import wallbox_source_dossier

    component = hass.data[DATA_COMPONENT]
    assert isinstance(component, EntityComponent)
    registry = er.async_get(hass)
    registration = registry.async_get_or_create("sensor", "template", "source_contract81_session",
                                               suggested_object_id="source_contract81_session")
    entity_id = registration.entity_id
    source_ids = ("sensor.source_contract81_status", "sensor.source_contract81_mode", "sensor.source_contract81_power",
                  "sensor.source_contract81_private")
    state_template = Template("{{ states('sensor.source_contract81_status') ~ states('sensor.source_contract81_private') }}", hass)
    config = {"name": "Synthetic source-contract session", "state": state_template}
    entity = StateSensorEntity(hass, config, "source_contract81_session")
    entity.entity_id = entity_id
    old_entity = component.get_entity(entity_id)
    component._entities[entity_id] = entity
    tracker = None
    try:
        for source, value, attrs in ((source_ids[0], "Ready", {}), (source_ids[1], "full_solar", {}),
                                    (source_ids[2], "0", {"unit_of_measurement": "W"}),
                                    (source_ids[3], "Synthetic private text to withhold", {}), (entity_id, "Laden gestopt", {})):
            hass.states.async_set(source, value, attrs)
        tracker = TrackTemplateResultInfo(hass, [TrackTemplate(state_template, {})], lambda _event, _updates: None)
        tracker.async_setup()
        entity._template_result_info = tracker
        info = tracker._info[state_template]
        assert isinstance(info, RenderInfo) and info.collecting is False and info.exception is None
        assert info.entities == frozenset((source_ids[0], source_ids[3]))
        runtime = SimpleNamespace(hass=hass, wallbox_settings={"enabled": True, "stale_s": 300,
                                  "session_mode_entity": entity_id, "status_entity": source_ids[0],
                                  "mode_entity": source_ids[1], "power_entity": source_ids[2]})
        now = hass.states.get(entity_id).last_reported.timestamp()
        with patch.object(Template, "async_render_to_info", side_effect=AssertionError("Diagnostic rendered a template")), \
                patch.object(TrackTemplateResultInfo, "async_refresh", side_effect=AssertionError("Diagnostic refreshed a tracker")):
            dossier = wallbox_source_dossier(runtime, now)
        assert dossier["dependency_relation"] == "verified_state_template_dependencies"
        assert dossier["dependency_coverage"] == "last_successful_render_only"
        assert len(dossier["dependencies"]) == 2
        status = next(source for source in dossier["dependencies"] if source["matches_configured_roles"] == ["status"])
        hidden = next(source for source in dossier["dependencies"] if not source["matches_configured_roles"])
        assert status["reported_wall"] == hass.states.get(source_ids[0]).last_reported.timestamp()
        assert status["value"] == "ready" and hidden["value"] is None and hidden["value_withheld"] is True
        encoded = json.dumps(dossier)
        assert "Synthetic private text" not in encoded and "sensor.source_contract81" not in encoded
        assert dossier["reassessed_session"] is False and dossier["control_effect"] == "none"
        return {"state_template_contract": "actual Core types and original reports verified",
                "diagnostic_render_or_refresh": False, "private_dependency_value_exported": False}
    finally:
        if tracker is not None:
            tracker.async_remove()
        if old_entity is None:
            component._entities.pop(entity_id, None)
        else:
            component._entities[entity_id] = old_entity
        for source in (*source_ids, entity_id):
            hass.states.async_remove(source)
        registry.async_remove(entity_id)
