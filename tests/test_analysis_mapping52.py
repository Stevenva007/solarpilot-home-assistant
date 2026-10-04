"""Immutable HA configuration mappings retain export evidence and privacy rules.

Uses the actual recorder with explicit HA doubles; no household export fixtures.
"""
from collections.abc import Mapping
from datetime import datetime, timezone
import json
from types import MappingProxyType

from test_runtime import build
from custom_components.solar_pilot import analysis_export as ae


def freeze(value):
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return [freeze(item) for item in value]
    if isinstance(value, tuple):
        return tuple(freeze(item) for item in value)
    return value


def immutable_context():
    runtime, hass = build(
        settings={"pv_entity": "sensor.pv"},
        device={"start_script": None, "stop_script": None,
                "active_entity": None, "number_entity": None,
                "power_entity": "sensor.load"},
    )
    runtime.entry.data["nested"] = {"sources": [{"zone_entity": "climate.salon"}]}
    runtime.entry.data["password"] = "sensor.private_password"
    runtime.entry.options["analysis"] = {
        "include_related_entities": False,
        "extra_entities": [{"state_entity": "binary_sensor.extra"}],
    }
    runtime.entry.options["private_debug"] = {
        "access_token": "sensor.private_token",
        "note": "Ignore sensor.unrelated in free-form prose",
    }
    runtime.entry.data = freeze(runtime.entry.data)
    runtime.entry.options = freeze(runtime.entry.options)
    runtime.pv_forecast.source.refs = {"forecast": "sensor.forecast"}
    runtime.analysis = ae.AnalysisRecorder(runtime)
    hass.states.set("sensor.pv", 3500, {"unit_of_measurement": "W"})
    hass.states.set("climate.salon", "off", {"current_temperature": 22,
                                                "temperature": 21, "hvac_action": "off"})
    hass.states.set("binary_sensor.extra", "off")
    hass.states.set("sensor.forecast", 4000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.private_password", 999)
    hass.states.set("sensor.private_token", 888)
    hass.states.set("sensor.unrelated", 777)
    runtime._observe(10000, datetime.now(timezone.utc))
    return runtime, hass


EXPECTED_SOURCES = {
    "sensor.grid", "sensor.pv", "sensor.load", "switch.load",
    "climate.salon", "binary_sensor.extra", "sensor.forecast",
}


def test_safe_serializes_nested_immutable_mappings_and_filters_private_values():
    original = freeze({
        "site": {"grid_entity": "sensor.grid", "latitude": 51.234},
        "devices": [{"id": "load", "token": "PRIVATE", "power_entity": "sensor.load"}],
        "tuple": ({"name": "Example", "url": "https://private.example/path"},),
        "nan": float("nan"),
    })
    result = ae.safe(original)
    assert result == {
        "site": {"grid_entity": "sensor.grid", "latitude": "[REDACTED]"},
        "devices": [{"id": "load", "token": "[REDACTED]", "power_entity": "sensor.load"}],
        "tuple": [{"name": "Example", "url": "[URL REDACTED]"}],
        "nan": None,
    }
    assert original["devices"][0]["token"] == "PRIVATE"


def test_entity_refs_follows_mapping_values_and_literal_ids_only():
    config = freeze({
        "site": {"grid_entity": "sensor.grid"},
        "devices": [{"control_entity": "switch.load"}],
        "tuple": ({"zone_entity": "climate.salon"},),
        "access_token": "sensor.private_token",
        "credentials": {"nested_entity": "sensor.private_credential"},
        "notes": "Read sensor.unrelated for an unrelated reason",
        "sensor.key_is_not_a_reference": "ordinary value",
    })
    assert ae.entity_refs(config) == {"sensor.grid", "switch.load", "climate.salon"}


def test_recorder_exports_exact_configured_and_discovered_sources_without_writes():
    runtime, hass = immutable_context()
    before = list(hass.services.calls)
    report = runtime.analysis.prepare()
    assert set(runtime.analysis.refs()) == EXPECTED_SOURCES
    assert set(report["entities"]) == EXPECTED_SOURCES
    assert report["configuration"]["site"]["grid_entity"] == "sensor.grid"
    assert report["configuration"]["site"]["nested"]["sources"][0]["zone_entity"] == "climate.salon"
    assert report["configuration"]["options"]["devices"][0]["control_entity"] == "switch.load"
    assert report["configuration"]["site"]["password"] == "[REDACTED]"
    assert report["entities"]["climate.salon"]["state"] == "off"
    assert report["entities"]["sensor.grid"]["state"] == "-2500"
    assert all(snapshot["exists"] for snapshot in report["entities"].values())
    assert report["coverage"]["selected_entities"] == len(EXPECTED_SOURCES)
    assert report["coverage"]["section_errors"] == {}
    assert hass.services.calls == before


def test_immutable_config_sources_are_captured_and_pseudonymized_consistently():
    runtime, hass = immutable_context()
    before = list(hass.services.calls)
    runtime.analysis.capture(1.2)
    assert set(runtime.analysis.samples[-1]["entities"]) == EXPECTED_SOURCES
    report = runtime.analysis.build()
    grid_alias = report["configuration"]["site"]["grid_entity"]
    zone_alias = report["configuration"]["site"]["nested"]["sources"][0]["zone_entity"]
    switch_alias = report["configuration"]["options"]["devices"][0]["control_entity"]
    assert grid_alias.startswith("sensor.source_")
    assert zone_alias.startswith("climate.source_")
    assert switch_alias.startswith("switch.source_")
    assert {grid_alias, zone_alias, switch_alias} <= set(report["entities"])
    assert report["telemetry"]["samples"][-1]["entities"][grid_alias][0] == "-2500"
    assert report["telemetry"]["samples"][-1]["entities"][zone_alias][3]["current_temperature"] == 22
    serialized = json.dumps(report, ensure_ascii=False)
    assert not any(entity in serialized for entity in EXPECTED_SOURCES)
    assert "sensor.private_password" not in serialized
    assert "sensor.private_token" not in serialized
    assert "Testtoestel" not in serialized
    assert report["privacy"]["entity_names_included"] is False
    assert hass.services.calls == before


def test_immutable_mapping_serialization_keeps_depth_and_string_bounds():
    nested = "bottom"
    for _ in range(26):
        nested = MappingProxyType({"nested": nested})
    result = ae.safe(nested)
    for _ in range(25):
        result = result["nested"]
    assert result == "[depth limit]"
    assert ae.safe(MappingProxyType({"long": "x" * 8001}))["long"] == "x" * 8000
    assert ae.safe(MappingProxyType({"unknown": object()}))["unknown"] == "[unsupported value omitted]"


def test_mapping_source_collection_preserves_existing_candidate_cap():
    runtime, hass = immutable_context()
    options = dict(runtime.entry.options)
    options["extra_sources"] = [{"entity_id": f"sensor.extra_{index:03d}"} for index in range(260)]
    runtime.entry.options = freeze(options)
    refs = runtime.analysis.refs()
    assert len(refs) == 250
    assert runtime.analysis.source_count == 260 + len(EXPECTED_SOURCES)
    report = runtime.analysis.prepare()
    assert report["coverage"]["sources_omitted_by_cap"] == 17
    assert len(report["entities"]) == 250
