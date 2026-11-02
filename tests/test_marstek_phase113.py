"""Phase attribution uses the monitor's real source proof, like its overview."""
from types import SimpleNamespace

from test_marstek_provider113 import provider


def phase_view(provider):
    runtime = provider.runtime
    runtime.phase_settings["enabled"] = True
    runtime.phase = SimpleNamespace(valid=True, phase_w=(1000, 500, 250))
    runtime.battery_fleet.configs["storage"]["phase_hint"] = "l1"
    return runtime._phase_attribution()


def test_native_cached_power_cannot_survive_as_known_phase_attribution(provider):
    assert phase_view(provider)["phases"][0]["battery_net_w"] == -800
    provider.coordinator.data["es_status_fresh"] = False
    assert not provider.runtime._site_data()[1]
    result = phase_view(provider)
    assert result["phases"][0]["battery_net_w"] == 0
    assert not result["phases"][0]["batteries"]


def test_phase_freshness_may_be_stricter_than_monitor_freshness(provider):
    assert provider.manager.read()[0].power_valid
    provider.runtime.phase_settings["stale_s"] = 5
    assert not phase_view(provider)["phases"][0]["batteries"]


def test_missing_soc_does_not_hide_proven_phase_power(provider):
    provider.hass.states.set("sensor.fictional_storage_soc", "unavailable", {"unit_of_measurement": "%"})
    reading = provider.manager.read()[0]
    assert reading.power_valid and not reading.soc_valid
    assert phase_view(provider)["phases"][0]["battery_net_w"] == -800
