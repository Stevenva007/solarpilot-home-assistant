"""Detector coverage stays independent from counter data and control policy."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from types import SimpleNamespace as NS

import pytest

from custom_components.solar_pilot.water_diagnostics import water_monitor_diagnostic
from test_runtime import build
from test_water_export101 import context as export_context
from test_water_runtime101 import platform_classes


NOW = datetime(2026, 10, 20, 12, tzinfo=timezone.utc).timestamp()
SETTINGS = {"enabled": True, "volume_entity": "sensor.fictional_water_total",
            "flow_entity": "sensor.fictional_water_flow", "leak_entity": "binary_sensor.fictional_leak"}


def view():
    def row(value):
        return {"value": value, "fresh": True, "reason": "current",
                "reported_at": NOW-10, "valid_until": NOW+290}
    return {"observed_at": NOW, "volume": row(1000), "flow": row(0), "native_leak": row(False)}


def test_current_zero_and_false_are_usable_sources_without_proving_a_completed_duration():
    snapshot = view();before = deepcopy(snapshot)
    result = water_monitor_diagnostic(snapshot, SETTINGS)
    assert result["state"] == "current"
    assert result["continuous_flow_ready"] is result["native_leak_ready"] is True
    assert snapshot == before
    assert "elapsed_s" not in result and "episode_id" not in result
    assert all(entity not in json.dumps(result) for entity in SETTINGS.values() if isinstance(entity, str))


@pytest.mark.parametrize("role,option", [("flow", "flow_entity"), ("native_leak", "leak_entity")])
def test_fresh_volume_cannot_refresh_a_stale_configured_detector(role, option):
    snapshot = view();snapshot[role].update(value=None, fresh=False, reason="stale", reported_at=NOW-7200, valid_until=NOW-6900)
    result = water_monitor_diagnostic(snapshot, SETTINGS)
    assert result["state"] == "incomplete"
    channel = result["flow_monitoring" if role == "flow" else "native_leak_monitoring"]
    assert channel == {"configured": True, "current": False, "reason": "stale",
                       "reported_at": NOW-7200, "valid_until": NOW-6900}
    snapshot["volume"].update(value=1001, reported_at=NOW, valid_until=NOW+300)
    assert water_monitor_diagnostic(snapshot, SETTINGS) == result


@pytest.mark.parametrize("role,bad", [("flow", True), ("flow", -1), ("flow", float("inf")),
                                     ("flow", float("nan")), ("flow", None),
                                     ("native_leak", "off"), ("native_leak", 0), ("native_leak", None)])
def test_fresh_flag_cannot_make_an_invalid_detector_value_usable(role, bad):
    snapshot = view();snapshot[role]["value"] = bad
    result = water_monitor_diagnostic(snapshot, SETTINGS)
    assert result["state"] == "incomplete"
    assert result["continuous_flow_ready" if role == "flow" else "native_leak_ready"] is False
    json.dumps(result, allow_nan=False)


@pytest.mark.parametrize("changes", [{"reported_at": None}, {"valid_until": None},
                                     {"valid_until": NOW-1}, {"reported_at": NOW+6},
                                     {"reported_at": True}, {"valid_until": float("inf")},
                                     {"fresh": 1}, {"fresh": False}])
def test_bad_or_expired_original_times_cannot_be_hidden_by_a_fresh_flag(changes):
    snapshot = view();snapshot["flow"].update(changes)
    assert water_monitor_diagnostic(snapshot, SETTINGS)["continuous_flow_ready"] is False


def test_omitted_optional_detector_is_not_a_failed_configured_channel():
    settings = {**SETTINGS, "leak_entity": ""}
    result = water_monitor_diagnostic(view(), settings)
    assert result["state"] == "current" and result["continuous_flow_ready"] is True
    assert result["native_leak_monitoring"]["configured"] is False and result["native_leak_ready"] is False
    settings["flow_entity"] = ""
    result = water_monitor_diagnostic(view(), settings)
    assert result["state"] == "not_configured" and result["code"] == "detectors_not_configured"
    assert result["continuous_flow_ready"] is result["native_leak_ready"] is False


@pytest.mark.parametrize("enabled", [False, None, 1, "true"])
def test_disabled_or_unconfirmed_permission_does_not_claim_detector_readiness(enabled):
    result = water_monitor_diagnostic(view(), {**SETTINGS, "enabled": enabled})
    assert result["state"] == "disabled"
    assert result["continuous_flow_ready"] is result["native_leak_ready"] is False


def test_recorder_and_sensor_reads_remain_pure_and_keep_an_unresolved_warning():
    runtime, hass = build();runtime.water.update_config(SETTINGS)
    runtime.water.now = lambda: datetime.fromtimestamp(NOW, timezone.utc)
    before = runtime.water.model.snapshot()
    for _ in range(3):
        result = runtime.water.overview()
        assert result["diagnostic"]["state"] == "unavailable"
    assert runtime.water.model.snapshot() == before and not hass.services.calls
    _, sensor = platform_classes();status = sensor(runtime, "water_status", "Water")
    assert status.native_value == "Waterbewaking mist actuele brongegevens"
    runtime.water.model.alert.update(active=True, cause="native_leak", episode_id="a"*24)
    assert status.native_value == "Eerdere waterwaarschuwing nog niet opgehelderd"
    assert not hass.services.calls


def test_export_discloses_effective_water_configuration_without_source_sampling(monkeypatch):
    env = export_context(monkeypatch)
    env.runtime.water.settings["source_stale_s"] = 300
    report = env.runtime.analysis.build()
    assert report["module_status"]["water"] is True
    assert report["effective_configuration"]["water"]["enabled"] is True
    assert report["effective_configuration"]["water"]["source_stale_s"] == env.runtime.water.settings["source_stale_s"]
    assert report["analysis_request"]["current"]["effective_settings"]["water"] == report["effective_configuration"]["water"]
    assert not env.hass.services.calls


def test_export_keeps_gap_role_semantics_when_a_consumer_has_the_same_name(monkeypatch):
    env = export_context(monkeypatch)
    env.runtime.configs["a"]["name"] = "flow"
    env.runtime.water.export = lambda **_kwargs: {
        "read_only": True, "days": [{"events": [{"kind": "source_gap", "source_role": "flow"}]}]}
    report = env.runtime.analysis.build()
    assert report["components"]["water_history"]["days"][0]["events"][0]["source_role"] == "flow"
    assert env.runtime.configs["a"]["control_entity"] not in json.dumps(report)
