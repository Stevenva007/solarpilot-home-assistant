"""Forecast lifecycle must also invalidate the boiler's five-minute veto cache."""
from types import SimpleNamespace
import time

from test_dhw_runtime import setup


def prediction_context(monkeypatch):
    monkeypatch.setattr(time, "time", lambda: 10000.0)
    runtime, hass = setup(config={"predictive_cooling_enabled": True})
    evidence = {"valid": True, "warm": True, "predictions": 0}

    def predict(*args, **kwargs):
        evidence["predictions"] += 1
        return [24, 25] if evidence["warm"] else [23, 23]

    profile = SimpleNamespace(confidence=lambda settings: .7, predict=predict)
    climate = SimpleNamespace(
        settings={"enabled": True, "weather_entity": "weather.example",
                  "zone_entities": ["climate.example"], "model_confidence_min": .55,
                  "forecast_refresh_s": 3600, "soft_band_c": .5},
        configured=True,
        state=SimpleNamespace(fault="", last_forecast_wall=9990,
                              profiles={"climate.example": profile}),
        last_solar_hourly=[0, 0],
        _zones=lambda: [{"entity_id": "climate.example", "current": 23,
                         "target": 23, "mode": "cool"}],
        _outside_hourly=lambda: [27, 28],
        forecast_cache_valid=lambda: evidence["valid"],
    )
    runtime.smart_climate = climate
    return runtime, hass, climate, evidence


def test_invalid_weather_evidence_clears_cached_cooling_immediately(monkeypatch):
    runtime, hass, climate, evidence = prediction_context(monkeypatch)
    assert runtime.dhw._predicted_cooling()[0]
    assert evidence["predictions"] == 1
    evidence["valid"] = False
    assert runtime.dhw._predicted_cooling() == (False, "")
    assert evidence["predictions"] == 1
    assert not hass.services.calls


def test_recovered_weather_is_rechecked_without_five_minute_wait(monkeypatch):
    runtime, hass, climate, evidence = prediction_context(monkeypatch)
    assert runtime.dhw._predicted_cooling()[0]
    evidence["valid"] = False
    assert not runtime.dhw._predicted_cooling()[0]
    evidence.update(valid=True, warm=False)
    assert not runtime.dhw._predicted_cooling()[0]
    assert evidence["predictions"] == 2
    assert not hass.services.calls


def test_new_successful_forecast_invalidates_old_cooling_prediction(monkeypatch):
    runtime, hass, climate, evidence = prediction_context(monkeypatch)
    assert runtime.dhw._predicted_cooling()[0]
    evidence["warm"] = False
    climate.state.last_forecast_wall = 10000
    assert not runtime.dhw._predicted_cooling()[0]
    assert evidence["predictions"] == 2
    assert not hass.services.calls


def test_rebound_weather_cannot_reuse_old_cooling_prediction(monkeypatch):
    runtime, hass, climate, evidence = prediction_context(monkeypatch)
    assert runtime.dhw._predicted_cooling()[0]
    evidence["warm"] = False
    climate.settings["weather_entity"] = "weather.other"
    assert not runtime.dhw._predicted_cooling()[0]
    assert evidence["predictions"] == 2
    assert not hass.services.calls


def test_same_valid_forecast_keeps_bounded_prediction_cache(monkeypatch):
    runtime, hass, climate, evidence = prediction_context(monkeypatch)
    assert runtime.dhw._predicted_cooling()[0]
    assert runtime.dhw._predicted_cooling()[0]
    assert evidence["predictions"] == 1
    assert not hass.services.calls
