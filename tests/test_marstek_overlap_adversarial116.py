"""Independent probes keep the in-flight bridge bound to old native evidence."""
from datetime import datetime, timezone

import pytest

from test_marstek_provider113 import provider  # noqa: F401 - native fixture
from test_marstek_poll_overlap116 import begin_next_poll


def test_overlap_keeps_the_oldest_accepted_clock_not_just_the_udp_clock(provider):
    accepted = provider.manager._monitor_source_stamp("sensor.fictional_storage_ac", "power",
        provider.clock.wall-115, 800)
    assert accepted == provider.clock.wall-115
    begin_next_poll(provider, 4)
    assert provider.stamp() == accepted
    begin_next_poll(provider, 2)
    assert provider.stamp() is None


@pytest.mark.parametrize("change", ["monotonic_backwards", "completed_future", "completed_changed", "success_changed"])
def test_unmatched_or_reversed_provider_clocks_cannot_use_completed_proof(provider, change):
    provider.stamp()
    begin_next_poll(provider)
    if change == "monotonic_backwards":
        provider.clock.mono -= 30
    elif change == "completed_future":
        provider.coordinator.data["last_update"] = provider.clock.mono+1
    elif change == "completed_changed":
        provider.coordinator.data["last_update"] += 1
    else:
        provider.coordinator.last_update_success_time = datetime.fromtimestamp(
            provider.clock.wall-5, timezone.utc)
    assert provider.stamp() is None
    assert not provider.hass.services.calls


def test_power_proof_does_not_create_a_missing_soc_field_during_overlap(provider):
    accepted = provider.stamp("power")
    assert accepted is not None
    next(iter(provider.cache.values()))["response"]["result"].pop("bat_soc")
    begin_next_poll(provider)
    assert provider.stamp("power") == accepted
    assert provider.stamp("soc") is None
    assert not provider.hass.services.calls
