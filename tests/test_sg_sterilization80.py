"""Sterilization stays with Panasonic and is not an SG veto.

Fictional reports exercise the real SG controller and its final runtime gate.
They do not prove that a physical Panasonic cycle ran, skipped or repeated.
"""
from copy import deepcopy
import time

import pytest

from test_sg_controller62 import fixture
from test_sg_budget_priority62 import configured


def native_row(clock, *, status="active", cooling=False):
    return {
        "context": "space_cooling" if cooling else "space_heating",
        "context_reliable": True,
        "context_signature": "fictional:cool" if cooling else "fictional:heat",
        "context_stamp": clock(),
        "cooling_possible": cooling,
        "native_task": {
            "function": "sterilization" if status == "active" else None,
            "source": "native_hvac_action" if status == "active" else "none",
            "observed_at": clock() if status == "active" else None,
            "stale_s": 120,
        },
        # Read-only context cannot establish a running cycle or SG authority.
        "task_context": {
            "function": "sterilization" if status == "planned" else None,
            "kind": "selected_program" if status == "planned" else "none",
            "observed_at": clock(),
            "stale_s": 120,
        },
    }


async def observe(manager, clock, row, **changes):
    row["context_stamp"] = clock()
    if row["native_task"]["function"] is not None:
        row["native_task"]["observed_at"] = clock()
    row["task_context"]["observed_at"] = clock()
    args = {
        "surplus_w": 4500,
        "real_surplus_w": 4500,
        "solar_stamp": clock(),
        "grid_import_w": 0,
        "grid_import_stamp": clock(),
        "data_fresh": True,
        "phase_allowed": True,
        "priority_allowed": True,
        "native_observation": deepcopy(row),
    }
    args.update(changes)
    return await manager.tick(**args)


@pytest.mark.asyncio
@pytest.mark.parametrize("profile", ["dhw_only", "general"])
@pytest.mark.parametrize("status", ["planned", "active", "unknown"])
async def test_sterilization_report_does_not_veto_sg_start_or_renewal(profile, status):
    manager, adapter, clock, runtime = fixture(profile=profile, profile_confirmed=True)
    row = native_row(clock, status=status)
    runtime.panasonic.overview = lambda: deepcopy(row)
    settings = deepcopy(runtime.entry.options)

    await observe(manager, clock, row)
    clock.advance(manager.settings["start_delay_s"])
    await observe(manager, clock, row)
    assert adapter.calls == [("on", 300)] and manager.owned

    clock.advance(manager.settings["renew_s"])
    await observe(manager, clock, row)
    assert adapter.calls == [("on", 300), ("on", 300)]
    assert manager.owned and manager.desired_on
    assert runtime.entry.options == settings


@pytest.mark.asyncio
async def test_sterilization_beginning_and_ending_never_opens_an_owned_sg_contact():
    manager, adapter, clock, runtime = fixture(profile="general", profile_confirmed=True)
    row = native_row(clock, status="planned")
    runtime.panasonic.overview = lambda: deepcopy(row)
    await observe(manager, clock, row)
    clock.advance(manager.settings["start_delay_s"])
    await observe(manager, clock, row)

    for status in ("active", "unknown"):
        row.update(native_row(clock, status=status))
        clock.advance(manager.settings["renew_s"])
        await observe(manager, clock, row)
        assert manager.owned and manager.desired_on

    assert adapter.calls == [("on", 300)] * 3
    assert not manager.completion_hold


@pytest.mark.asyncio
@pytest.mark.parametrize("context", ["cooling", "auto", "unknown"])
async def test_sterilization_cannot_certify_condensation_protection(context):
    manager, adapter, clock, runtime = fixture(profile="general", profile_confirmed=True)
    row = native_row(clock, cooling=context == "cooling")
    row["cooling_possible"] = True
    if context == "unknown":
        row.update(context="heatpump_unknown", context_reliable=False)
    runtime.panasonic.overview = lambda: deepcopy(row)

    await observe(manager, clock, row)
    clock.advance(manager.settings["start_delay_s"])
    await observe(manager, clock, row)
    assert not adapter.calls and not manager.owned
    if context == "cooling":
        assert "condens-/dauwpuntbeveiliging" in manager.reason
    else:
        assert "SG wacht op bekende Panasonic-koelcontext" in manager.reason


@pytest.mark.asyncio
@pytest.mark.parametrize("gate", ["data_fresh", "phase_allowed", "priority_allowed", "hard_limit"])
async def test_active_sterilization_never_bypasses_actual_sg_guards(gate):
    manager, adapter, clock, runtime = fixture(profile="general", profile_confirmed=True)
    row = native_row(clock)
    runtime.panasonic.overview = lambda: deepcopy(row)
    changes = {gate: gate == "hard_limit"}

    await observe(manager, clock, row, **changes)
    clock.advance(manager.settings["start_delay_s"])
    await observe(manager, clock, row, **changes)
    assert not adapter.calls and not manager.owned


@pytest.mark.asyncio
@pytest.mark.parametrize("renewal", [False, True])
@pytest.mark.parametrize("status", ["planned", "active", "unknown"])
async def test_final_runtime_gate_allows_sg_with_sterilization_information(renewal, status):
    runtime, hass = configured(export=6500)
    settings = {**runtime.sg_boost.settings, "profile": "general", "profile_confirmed": True,
                "zone_entities": ["climate.fictional_room"]}
    runtime.entry.options["sg_boost"] = deepcopy(settings)
    runtime.sg_boost.update_config(settings)
    runtime.panasonic.update_config(settings)
    hass.states.set("climate.fictional_room", "heat", {"hvac_action": "heating"})
    original = runtime.panasonic.overview

    def with_sterilization_information():
        row = original()
        row["native_task"] = {"function": "sterilization" if status == "active" else None,
                              "source": "native_hvac_action", "observed_at": row["context_stamp"],
                              "stale_s": 120}
        row["task_context"] = {"function": "sterilization" if status == "planned" else None,
                               "kind": "selected_program", "observed_at": row["context_stamp"]}
        return row

    runtime.panasonic.overview = with_sterilization_information
    if renewal:
        # Obtain a real controller-confirmed fictional lease first. Merely
        # requesting renewal must never create initial ON authority.
        manager, adapter, clock, controller_runtime = fixture(**settings)
        row = native_row(clock, status=status)
        controller_runtime.panasonic.overview = lambda: deepcopy(row)
        await observe(manager, clock, row)
        clock.advance(manager.settings["start_delay_s"])
        await observe(manager, clock, row)
        assert adapter.calls == [("on", 300)] and manager.owned
        shift = time.time() - manager._wall_clock()
        manager._relay_observed_at += shift
        manager._relay_valid_until += shift
        manager._wall_clock = time.time
        runtime.sg_boost = manager
        controller_runtime.panasonic = runtime.panasonic
        controller_runtime.sg_dispatch_allowed = runtime.sg_dispatch_allowed
    before = deepcopy(runtime.entry.options)
    assert runtime.sg_dispatch_allowed(renewal=renewal) is True
    assert runtime.entry.options == before and not hass.services.calls
