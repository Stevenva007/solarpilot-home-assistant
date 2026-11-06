"""SG event diagnosis distinguishes a safety context from reported action."""
from copy import deepcopy

import pytest

from test_sg_controller62 import fixture


def observation(manager, clock):
    manager._native_observation = {
        "context": "space_heating", "power_w": 1600, "power_kind": "measured",
        "power_supply1_w": 1600, "power_supply2_w": 0,
        "native_task": {"function": "tapwater_heating", "source": "aquarea_poll",
                        "observed_at": clock(), "stale_s": 120},
    }


def test_event_keeps_program_context_reported_action_and_electrical_input_distinct():
    manager, adapter, clock, runtime = fixture()
    observation(manager, clock)
    before = deepcopy(manager._native_observation)
    summary = manager._observation_summary()
    assert "regelcontext space_heating" in summary
    assert "gemelde actie tapwater_heating" in summary
    assert "gemeten 1600 W" in summary and "voeding 2 0 W" in summary
    assert "native space_heating" not in summary
    assert "compressor" not in summary
    assert manager._native_observation == before and adapter.calls == []


@pytest.mark.parametrize("native", [
    None, {}, {"function": "tapwater_heating"},
    {"function": "tapwater_heating", "observed_at": True, "stale_s": 120},
    {"function": "tapwater_heating", "observed_at": 1, "stale_s": 120},
    {"function": "tapwater_heating", "observed_at": 1_800_000_006, "stale_s": 120},
    {"function": "compressor_on", "observed_at": 1_800_000_000, "stale_s": 120},
])
def test_missing_old_future_or_unknown_native_action_is_not_a_current_report(native):
    manager, adapter, clock, runtime = fixture()
    observation(manager, clock)
    manager._native_observation["native_task"] = native
    summary = manager._observation_summary()
    assert "gemelde actie" not in summary
    assert "regelcontext space_heating" in summary and "gemeten 1600 W" in summary
    assert not adapter.calls


def test_event_formatter_does_not_refresh_original_action_timestamp():
    manager, adapter, clock, runtime = fixture()
    observation(manager, clock)
    stamp = manager._native_observation["native_task"]["observed_at"]
    assert "gemelde actie" in manager._observation_summary()
    clock.advance(121)
    assert "gemelde actie" not in manager._observation_summary()
    assert manager._native_observation["native_task"]["observed_at"] == stamp
    assert not adapter.calls
