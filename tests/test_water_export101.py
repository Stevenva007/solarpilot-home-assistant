"""Water adds isolated, bounded evidence to the existing private analysis export."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from types import SimpleNamespace as NS

import pytest

from custom_components.solar_pilot import analysis_export as ae
from custom_components.solar_pilot.water_runtime import WaterRecorder
from test_runtime import build
from test_water101 import CONFIG, sample


WALL = datetime(2026, 10, 19, 21, 59, 59, 123456, tzinfo=timezone.utc)


def forbidden(*_args, **_kwargs):
    raise AssertionError("Preparing water export must not observe, write, notify or send controls")


def context(monkeypatch):
    runtime, hass = build()
    monkeypatch.setattr(ae.time, "time", lambda: WALL.timestamp())
    calls = []
    overview = {"schema": 1, "read_only": True, "configured": True,
                "flow": {"value": 0, "fresh": True}, "today": {"volume_l": None}}

    def export(*, hours, when):
        calls.append({"hours": hours, "when": when})
        return {"schema": 1, "read_only": True, "requested_hours": hours,
                "window_start": (when - timedelta(hours=hours)).isoformat(),
                "window_end": when.isoformat(), "days": []}

    runtime.water = NS(settings=deepcopy(CONFIG), overview=lambda: overview, export=export,
                       observe=forbidden, _maybe_save=forbidden, _checkpoint=forbidden,
                       store=NS(async_save=forbidden, async_delay_save=forbidden))
    hass.services.async_call = forbidden
    return NS(runtime=runtime, hass=hass, calls=calls, overview=overview)


def test_water_current_and_history_sections_are_additive_detached_and_read_only(monkeypatch):
    env = context(monkeypatch)
    before = deepcopy((env.runtime.entry.data, env.runtime.entry.options))
    report = env.runtime.analysis.prepare()
    assert not report["coverage"]["section_errors"]
    assert report["components"]["water"] == env.overview
    assert report["components"]["water_history"]["read_only"] is True
    assert all(key in report["components"] for key in (
        "runtime_and_models", "panasonic", "sg_boost", "consumers", "consumer_history", "heatpump_history"))
    env.overview["flow"]["value"] = 999
    assert report["components"]["water"]["flow"]["value"] == 0
    assert (env.runtime.entry.data, env.runtime.entry.options) == before
    assert not env.hass.services.calls


@pytest.mark.parametrize("hours", [1, 24, 168])
def test_water_history_uses_the_exact_frozen_heatpump_export_window(monkeypatch, hours):
    env = context(monkeypatch)
    heatpump_calls = []
    def heatpump_export(*, hours, when):
        heatpump_calls.append({"hours": hours, "when": when})
        return {"requested_hours": hours, "window_end": when.isoformat()}
    env.runtime.heatpump_history.export = heatpump_export
    report = env.runtime.analysis.prepare(hours=hours)
    assert env.calls == heatpump_calls == [{"hours": hours, "when": WALL}]
    water = report["components"]["water_history"]
    assert water["requested_hours"] == report["requested_hours"] == hours
    assert water["window_end"] == report["created_at"] == WALL.isoformat()
    assert water["window_start"] == (WALL - timedelta(hours=hours)).isoformat()
    assert env.calls[0]["when"].tzinfo is timezone.utc


@pytest.mark.parametrize("failed", ["water", "water_history"])
def test_one_water_section_failure_keeps_other_sections_and_discloses_only_exception_type(monkeypatch, failed):
    env = context(monkeypatch)
    def fail(*_args, **_kwargs):
        raise RuntimeError("private water source identity and credentials")
    setattr(env.runtime.water, "overview" if failed == "water" else "export", fail)
    report = env.runtime.analysis.prepare()
    assert failed not in report["components"]
    assert report["coverage"]["section_errors"] == {failed: "RuntimeError"}
    assert ("water_history" if failed == "water" else "water") in report["components"]
    assert report["components"]["panasonic"] and "consumer_history" in report["components"]
    assert "private water source" not in json.dumps(report)
    assert not env.hass.services.calls


@pytest.mark.parametrize("available", ["absent", "none", "neither", "overview", "export"])
def test_optional_water_capabilities_preserve_older_runtime_exports(monkeypatch, available):
    env = context(monkeypatch)
    if available == "absent": del env.runtime.water
    elif available == "none": env.runtime.water = None
    elif available == "neither": env.runtime.water = NS()
    elif available == "overview": del env.runtime.water.export
    else: del env.runtime.water.overview
    report = env.runtime.analysis.prepare()
    assert not report["coverage"]["section_errors"]
    assert ("water" in report["components"]) is (available == "overview")
    assert ("water_history" in report["components"]) is (available == "export")
    assert "heatpump_history" in report["components"] and "consumer_history" in report["components"]


@pytest.mark.parametrize("include_names", [False, True])
def test_water_ids_use_existing_export_privacy_rules_including_embedded_old_sources(monkeypatch, include_names):
    env = context(monkeypatch)
    current = "sensor.private_current_water"
    retired = "sensor.private_retired_water"
    label = "Privéwatermeter kelder"
    env.runtime.entry.options["water"] = {"enabled": True, "volume_entity": current}
    env.hass.states.set(current, 123, {"unit_of_measurement": "L", "friendly_name": label})
    env.overview["source"] = {"entity_id": current, "friendly_name": label}
    env.runtime.water.export = lambda *, hours, when: {
        "schema": 1, "read_only": True, "requested_hours": hours,
        "points": [{"entity_id": current, "context": {retired: {"value": 50}}}],
        "diagnostic": f"{label} follows {current} and {retired}",
        "credentials": "DO_NOT_SHARE_WATER_PASSWORD"}
    report = env.runtime.analysis.build(include_names=include_names)
    text = json.dumps(report, ensure_ascii=False)
    configured = report["configuration"]["options"]["water"]["volume_entity"]
    point = report["components"]["water_history"]["points"][0]
    assert report["privacy"]["entity_names_included"] is include_names
    assert point["entity_id"] == configured == report["components"]["water"]["source"]["entity_id"]
    assert "DO_NOT_SHARE_WATER_PASSWORD" not in text
    if include_names:
        assert configured == current and retired in point["context"] and label in text
    else:
        assert configured.startswith("sensor.source_") and configured in report["entities"]
        assert all(key.startswith("sensor.source_") for key in point["context"])
        assert current not in text and retired not in text and label not in text


@pytest.mark.parametrize("hours", [1, 24, 168])
@pytest.mark.parametrize("populated", [False, True])
def test_real_water_export_preserves_sparse_evidence_without_backfill_or_store_writes(monkeypatch, hours, populated):
    env = context(monkeypatch)
    rec = WaterRecorder(env.hass, env.runtime.entry, CONFIG)
    rec.loaded = rec._writable = True
    rec.now = lambda: WALL
    if populated:
        for offset, volume in ((-10 * 86400, 100), (-120, 200), (-60, 203)):
            when = WALL + timedelta(seconds=offset)
            rec.model.observe(sample(when, volume=volume), when, binding="a" * 64)
    rec.observe = rec._maybe_save = rec._checkpoint = forbidden
    rec.store.async_save = rec.store.async_delay_save = forbidden
    env.runtime.water = rec
    before = deepcopy((rec.model.snapshot(), rec.store.data, rec.store.saves,
                       env.runtime.entry.options, env.hass.services.calls))
    report = env.runtime.analysis.build(hours=hours, include_names=True)
    assert not report["coverage"]["section_errors"]
    history = report["components"]["water_history"]
    assert history["requested_hours"] == hours and history["window_end"] == WALL.isoformat()
    points = [point for day in history["days"] for point in day["points"]]
    assert len(points) == (2 if populated else 0)
    assert all(point["captured_at"] in {row["captured_at"] for row in rec.model.points} for point in points)
    assert all(day["complete"] is False for day in history["days"])
    if populated:
        assert sum(day["volume_covered_s"] for day in history["days"]) == 60
        assert sum(day["volume_l"] or 0 for day in history["days"]) == 3
    else:
        assert all(day["volume_l"] is None and not day["has_data"] and not day["intervals"]
                   for day in history["days"])
    assert not report["telemetry"]["samples"] and not report["telemetry"]["fast"]
    assert (rec.model.snapshot(), rec.store.data, rec.store.saves,
            env.runtime.entry.options, env.hass.services.calls) == before


@pytest.mark.parametrize("unit", ["L", "L/min", "m³"])
def test_anonymization_preserves_water_protocol_units_when_private_name_matches(monkeypatch, unit):
    env = context(monkeypatch)
    source = "sensor.private_water_total"
    env.runtime.entry.options["water"] = {"volume_entity": source}
    env.hass.states.set(source, 100, {"friendly_name": unit, "unit_of_measurement": unit})
    env.overview["volume"] = {"value": 100, "unit": unit, "source_unit": unit, "entity_id": source}
    env.runtime.water.export = lambda *, hours, when: {
        "schema": 1, "read_only": True, "points": [deepcopy(env.overview["volume"])]}
    report = env.runtime.analysis.build(include_names=False)
    current = report["components"]["water"]["volume"]
    historical = report["components"]["water_history"]["points"][0]
    assert current["unit"] == current["source_unit"] == historical["unit"] == historical["source_unit"] == unit
    assert current["entity_id"] == historical["entity_id"] != source
    assert source not in json.dumps(report)
