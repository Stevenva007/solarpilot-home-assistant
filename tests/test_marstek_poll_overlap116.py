"""Completed native proof can survive an in-flight poll, never its own expiry."""
from datetime import datetime, timezone

import pytest

from test_marstek_provider113 import provider  # noqa: F401 - shared fictional native fixture


def begin_next_poll(p, seconds=10):
    p.advance(seconds)
    p.stats["ES.GetStatus"].update(last_success=True, last_updated=p.clock.wall)
    # ES has answered, but the coordinator still awaits other poll methods.
    p.cache[(p.host, 2)] = {"addr": (p.host, p.port), "timestamp": p.clock.mono,
        "response": {"id": 2, "result": {"ongrid_power": p.coordinator.data["ongrid_power"]}}}


def test_completed_proof_survives_poll_overlap_without_renewal(provider):
    original = provider.stamp()
    begin_next_poll(provider)
    assert provider.stamp() == original
    diagnostic = provider.manager._source_diagnostics[("sensor.fictional_storage_ac", "power")]
    assert diagnostic["evidence"]["detail_code"] == "inflight_previous_completed"
    assert diagnostic["evidence"]["es_reported_at_wall"] > diagnostic["evidence"]["coordinator_success_at_wall"]
    # Every in-flight reply remains insufficient to extend the old field proof.
    begin_next_poll(provider, 110)
    assert provider.stamp() is None


def test_first_read_cannot_borrow_an_inflight_poll(provider):
    begin_next_poll(provider)
    assert provider.stamp() is None


@pytest.mark.parametrize("change", ["failed_command", "failed_coordinator", "wrong_binding", "new_value", "changed_completed", "cache_only_new_value"])
def test_overlap_bridge_rejects_failed_or_unmatched_evidence(provider, change):
    provider.stamp()
    begin_next_poll(provider)
    if change == "failed_command":
        provider.stats["ES.GetStatus"]["last_success"] = False
    elif change == "failed_coordinator":
        provider.coordinator.last_update_success = False
    elif change == "wrong_binding":
        provider.rows["sensor.fictional_storage_ac"].device_id = "replacement"
    elif change == "new_value":
        provider.coordinator.data["ongrid_power"] = 801
    elif change == "changed_completed":
        provider.coordinator.data["last_update"] = provider.clock.mono
    else:
        provider.manager._native_source_proofs.clear()
    assert provider.stamp() is None
    assert not provider.hass.services.calls


def test_new_completed_reply_renews_only_after_coordinator_completion(provider):
    first = provider.stamp()
    begin_next_poll(provider)
    assert provider.stamp() == first
    provider.coordinator.last_update_success_time = datetime.fromtimestamp(provider.clock.wall+.001, timezone.utc)
    provider.coordinator.data["last_update"] = provider.clock.mono
    assert provider.stamp() == pytest.approx(provider.clock.wall)


def test_stable_zero_is_not_missing_and_overlap_never_fabricates_it(provider):
    for key in ("ongrid_power",):
        provider.coordinator.data[key] = 0
        next(iter(provider.cache.values()))["response"]["result"][key] = 0
    provider.hass.states.set("sensor.fictional_storage_ac", 0, {"unit_of_measurement": "W"})
    first = provider.stamp()
    assert first is not None
    begin_next_poll(provider)
    reading = provider.manager.read()[0]
    assert reading.valid and reading.power_w == 0
    assert reading.power_stamp == first
    provider.advance(120)
    reading = provider.manager.read()[0]
    assert not reading.power_valid and reading.power_w is None


def test_source_diagnostics_freeze_check_without_raw_identity(provider):
    reading = provider.manager.read()[0]
    evidence = reading.source_evidence.copy()
    assert evidence["es_reported_at_wall"] == pytest.approx(provider.clock.wall-14)
    begin_next_poll(provider)
    provider.manager.read()
    assert reading.source_evidence == evidence
    import json
    content = json.dumps(provider.manager.overview())
    assert provider.host not in content
    assert provider.rows["sensor.fictional_storage_ac"].unique_id not in content


def test_overlap_rejects_missing_provider_cache_even_with_completed_proof(provider):
    provider.stamp()
    begin_next_poll(provider)
    provider.coordinator.udp_client._router.cache = None
    assert provider.stamp() is None


def test_expired_bridge_keeps_original_failure_evidence(provider):
    original = provider.stamp()
    begin_next_poll(provider, 106.5)
    assert provider.stamp() is None
    evidence = provider.manager._source_diagnostics[("sensor.fictional_storage_ac", "power")]["evidence"]
    assert evidence["last_verified_reported_at_wall"] == original
    assert evidence["field_reported_at_wall"] == original
    assert "accepted_reported_at_wall" not in evidence
