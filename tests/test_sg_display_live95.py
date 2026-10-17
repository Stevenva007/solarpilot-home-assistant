"""Effective SG display edits preserve live leases, sources and transactions."""
from copy import deepcopy
import math

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.live_options import PENDING, _sg_changed_keys
from custom_components.solar_pilot.sg_config import DISPLAY_ONLY_KEYS, normalize_config
from test_sg_config62 import live_sg_runtime


def legacy_runtime(*, in_flight=False):
    runtime, hass = live_sg_runtime()
    legacy = {
        "entity_id": "switch.sg_contact", "enabled": True,
        "commissioning_confirmed": True, "watchdog_confirmed": True,
        "profile": "general", "profile_confirmed": True,
        "hysteresis_w": 300, "stop_delay_s": 60,
        "zone_entities": ["climate.example_one", "climate.example_two"],
    }
    runtime.entry.options["sg_boost"] = deepcopy(legacy)
    runtime.sg_boost.update_config(legacy)
    runtime.panasonic.update_config(legacy)
    runtime.live_options.applied = deepcopy(runtime.entry.options)
    sg = runtime.sg_boost
    sg.owned = sg.relay_on = sg.desired_on = True
    sg._in_flight = in_flight
    sg._session_started, sg._minimum_started, sg._stable_since = 100, 120, 140
    sg._lease_deadline = sg._clock() + 300
    sg._import_since = 135
    sg._import_observation = {"watts": 700, "stamp": sg._wall_clock(), "source": "fictional_grid"}
    sg._import_policy = (600, 300)
    sg._binding_identity = "f" * 64
    return runtime, hass


def controls(runtime):
    sg = runtime.sg_boost
    return (sg._control_identity(), sg._generation, sg.owned, sg.relay_on, sg.desired_on,
            sg._in_flight, sg._session_started, sg._minimum_started, sg._stable_since,
            sg._lease_deadline, deepcopy(sg._manual_control), sg._import_since,
            deepcopy(sg._import_observation), sg._import_policy, sg._binding_identity,
            sg.settings["profile"], sg.settings["profile_confirmed"])


def proposal(runtime, **changes):
    base = deepcopy(runtime.entry.options)
    desired = deepcopy(base)
    desired["sg_boost"] = {**normalize_config(base["sg_boost"]), **changes}
    return base, desired


def assert_unconfirmed_display(runtime):
    config = runtime.sg_boost.settings
    assert config["sg_dhw_capacity_confirmed"] is False
    assert config["sg_dhw_capacity_confirmed_at"] == 0
    assert config["sg_dhw_capacity_binding"] == ""
    assert config["sg_dhw_capacity_target_entity"] == ""


@pytest.mark.asyncio
@pytest.mark.parametrize("in_flight", [False, True])
async def test_legacy_defaults_do_not_park_a_display_only_edit_during_owned_sg(in_flight):
    runtime, hass = legacy_runtime(in_flight=in_flight)
    before = controls(runtime)
    base, desired = proposal(runtime, sg_dhw_capacity_percent=115)
    assert base["sg_boost"]["stop_delay_s"] == 60
    assert "import_threshold_w" not in base["sg_boost"]
    assert runtime.sg_boost.settings["stop_delay_s"] == 300
    assert runtime.sg_boost.settings["import_threshold_w"] == 600
    assert _sg_changed_keys(base["sg_boost"], desired["sg_boost"]) == {"sg_dhw_capacity_percent"}

    result = await runtime.live_options.submit(base, desired)

    assert not result[PENDING]
    assert runtime.sg_boost.settings["sg_dhw_capacity_percent"] == 115
    assert runtime.panasonic.settings["sg_dhw_capacity_percent"] == 115
    assert runtime.entry.options["sg_boost"]["stop_delay_s"] == 300
    assert runtime.entry.options["sg_boost"]["import_threshold_w"] == 600
    assert controls(runtime) == before
    assert_unconfirmed_display(runtime)
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("display_change", [False, True])
async def test_same_zone_membership_keeps_original_saved_and_live_order(display_change):
    runtime, hass = legacy_runtime()
    before = controls(runtime)
    old_order = list(runtime.sg_boost.settings["zone_entities"])
    changes = {"zone_entities": list(reversed(old_order))}
    if display_change:
        changes["sg_dhw_capacity_percent"] = 115
    base, desired = proposal(runtime, **changes)
    submitted = deepcopy(desired)

    await runtime.live_options.submit(base, desired)

    assert not runtime.entry.options[PENDING]
    assert runtime.entry.options["sg_boost"]["zone_entities"] == old_order
    assert runtime.sg_boost.settings["zone_entities"] == old_order
    assert runtime.panasonic.settings["zone_entities"] == old_order
    assert desired == submitted  # Caller input and three-way leaves are untouched.
    assert controls(runtime) == before
    assert_unconfirmed_display(runtime)
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("zones", [
    ["climate.example_one"],
    ["climate.example_one", "climate.other_room"],
])
async def test_changed_zone_scope_waits_for_release(zones):
    runtime, hass = legacy_runtime()
    before = controls(runtime)
    base, desired = proposal(runtime, zone_entities=zones, sg_dhw_capacity_percent=115)
    result = await runtime.live_options.submit(base, desired)
    assert "group:sg_boost" in result[PENDING]
    assert result["sg_boost"] == base["sg_boost"]
    assert runtime.sg_boost.settings["zone_entities"] == base["sg_boost"]["zone_entities"]
    assert runtime.sg_boost.settings["sg_dhw_capacity_percent"] == 100
    assert controls(runtime) == before
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("key,value", [
    ("import_threshold_w", 900), ("stop_delay_s", 420),
    ("min_session_s", 1800), ("max_session_s", 2400),
])
async def test_mixed_display_and_actual_policy_change_stays_atomic_and_waits(key, value):
    runtime, hass = legacy_runtime()
    before = controls(runtime)
    base, desired = proposal(runtime, sg_dhw_capacity_percent=115, **{key: value})
    await runtime.live_options.submit(base, desired)
    assert "group:sg_boost" in runtime.entry.options[PENDING]
    assert runtime.sg_boost.settings[key] != value
    assert runtime.sg_boost.settings["sg_dhw_capacity_percent"] == 100
    await runtime.live_options.process_pending()
    assert controls(runtime) == before
    runtime.sg_boost.owned = runtime.sg_boost.relay_on = False
    await runtime.live_options.process_pending()
    assert not runtime.entry.options[PENDING]
    assert runtime.sg_boost.settings[key] == value
    assert runtime.sg_boost.settings["sg_dhw_capacity_percent"] == 115
    assert_unconfirmed_display(runtime)
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_existing_legacy_display_draft_applies_once_while_owned_and_preserves_order():
    runtime, hass = legacy_runtime()
    before = controls(runtime)
    old = deepcopy(runtime.entry.options["sg_boost"])
    new = {**normalize_config(old), "sg_dhw_capacity_percent": 115,
           "zone_entities": list(reversed(old["zone_entities"]))}
    runtime.entry.options[PENDING] = {"group:sg_boost": {
        "kind": "group", "group": "sg_boost", "old": old, "new": deepcopy(new),
        "created": 1000, "reason": "Wacht op de al verstuurde opdracht/overdracht"}}
    queued = deepcopy(runtime.entry.options[PENDING]["group:sg_boost"])

    await runtime.live_options.process_pending()

    assert not runtime.entry.options[PENDING]
    assert runtime.sg_boost.settings["sg_dhw_capacity_percent"] == 115
    assert runtime.entry.options["sg_boost"]["zone_entities"] == old["zone_entities"]
    assert controls(runtime) == before
    applied = deepcopy(runtime.entry.options)
    await runtime.live_options.process_pending()
    assert runtime.entry.options == applied
    assert controls(runtime) == before
    assert queued["new"] == new
    assert_unconfirmed_display(runtime)
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_pending_draft_cannot_overwrite_concurrently_changed_stored_policy():
    runtime, hass = legacy_runtime()
    old = deepcopy(runtime.entry.options["sg_boost"])
    runtime.entry.options[PENDING] = {"group:sg_boost": {
        "kind": "group", "group": "sg_boost", "old": old,
        "new": {**normalize_config(old), "sg_dhw_capacity_percent": 115}, "created": 1000}}
    runtime.entry.options["sg_boost"]["stop_delay_s"] = 420
    await runtime.live_options.process_pending()
    assert runtime.entry.options["sg_boost"]["stop_delay_s"] == 420
    assert "group:sg_boost" in runtime.entry.options[PENDING]
    assert runtime.entry.options[PENDING]["group:sg_boost"]["old"] == old
    assert runtime.sg_boost.settings["sg_dhw_capacity_percent"] == 100
    assert not hass.services.calls


@pytest.mark.parametrize("concurrent", ["percentage", "zones", "policy"])
def test_effective_comparison_does_not_suppress_three_way_conflicts(concurrent):
    runtime, hass = legacy_runtime()
    base, desired = proposal(runtime, sg_dhw_capacity_percent=115)
    if concurrent == "percentage":
        runtime.entry.options["sg_boost"]["sg_dhw_capacity_percent"] = 120
    elif concurrent == "zones":
        desired["sg_boost"]["zone_entities"].reverse()
        runtime.entry.options["sg_boost"]["zone_entities"] = ["climate.another_room"]
    else:
        runtime.entry.options["sg_boost"]["stop_delay_s"] = 420
    with pytest.raises(HomeAssistantError, match="intussen elders gewijzigd"):
        runtime.live_options.prepare(base, desired)
    assert runtime.sg_boost.settings["sg_dhw_capacity_percent"] == 100
    assert not hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("key,value", [
    ("sg_dhw_capacity_percent", True), ("sg_dhw_capacity_percent", math.nan),
    ("sg_dhw_capacity_percent", "bad"), ("sg_dhw_capacity_confirmed", "true"),
    ("zone_entities", "climate.example_one"), ("zone_entities", [None]),
    ("zone_entities", {"room": "climate.example_one"}),
    ("zone_entities", [["climate.example_one"]]),
    ("zone_entities", ["climate.example_one", "climate.example_two", "climate.example_one"]),
])
async def test_malformed_fields_are_rejected_without_changing_live_or_saved_config(key, value):
    runtime, hass = legacy_runtime()
    before, control_before = deepcopy(runtime.entry.options), controls(runtime)
    base, desired = proposal(runtime, **{key: value})
    with pytest.raises(HomeAssistantError, match="SG-instellingen ongeldig"):
        await runtime.live_options.submit(base, desired)
    assert runtime.entry.options == before
    assert controls(runtime) == control_before
    assert not hass.services.calls


@pytest.mark.parametrize("value", [[], True, "bad", 1])
def test_malformed_group_shape_does_not_gain_display_fast_path(value):
    runtime, hass = legacy_runtime()
    assert runtime.live_options.group_block("sg_boost", runtime.entry.options["sg_boost"], value)
    assert not hass.services.calls


def test_unknown_edited_legacy_field_stays_conservative_and_inputs_are_detached():
    runtime, hass = legacy_runtime()
    old = {**runtime.entry.options["sg_boost"], "unknown_history": {"retained": [1, 2]}}
    new = {**deepcopy(old), **normalize_config(old), "sg_dhw_capacity_percent": 115}
    before = deepcopy((old, new))
    assert _sg_changed_keys(old, new) <= DISPLAY_ONLY_KEYS
    new["unknown_history"]["retained"].append(3)
    assert runtime.live_options.group_block("sg_boost", old, new)
    assert old == before[0] and old["unknown_history"]["retained"] == [1, 2]
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_numeric_string_display_edit_uses_existing_normalization_without_new_confirmation():
    runtime, hass = legacy_runtime()
    base, desired = proposal(runtime, sg_dhw_capacity_percent="115")
    await runtime.live_options.submit(base, desired)
    assert not runtime.entry.options[PENDING]
    assert runtime.sg_boost.settings["sg_dhw_capacity_percent"] == 115
    assert_unconfirmed_display(runtime)
    assert not hass.services.calls
