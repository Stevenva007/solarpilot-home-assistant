"""Cross-component safety boundaries for the general SG profile.

Fictional observations exercise software decisions only, never live equipment.
"""
from copy import deepcopy
from types import MappingProxyType

import pytest
from homeassistant.exceptions import HomeAssistantError

from custom_components.solar_pilot.private_bundle import (
    BUNDLE_FORMAT, build_private_import, private_group_suggestions,
)
from custom_components.solar_pilot.panasonic_migration import migrate_panasonic
from custom_components.solar_pilot.sg_config import normalize_config
from test_sg_budget_priority62 import configured, mature_reclaim
from test_sg_config62 import live_sg_runtime


def general(runtime, hass):
    c = {**runtime.sg_boost.settings, "profile": "general", "profile_confirmed": True,
         "zone_entities": ["climate.public_room"], "cooling_protection_confirmed": False}
    runtime.entry.options["sg_boost"] = deepcopy(c)
    runtime.sg_boost.update_config(c)
    runtime.panasonic.update_config(c)
    hass.states.set("climate.public_room", "cool", {"hvac_action": "cooling"})
    return c


def test_unprotected_general_cooling_cannot_dispatch_or_pause_a_lower_load():
    runtime, hass = configured(export=5000)
    general(runtime, hass)
    assert runtime.sg_dispatch_allowed() is False
    assert runtime.sg_dispatch_allowed(renewal=True) is False
    hass.states.set("sensor.grid", -2200, {"unit_of_measurement": "W"})
    assert mature_reclaim(runtime, hass) is None
    assert not hass.services.calls


@pytest.mark.parametrize("meter_key", ["power_supply1_entity", "power_supply2_entity"])
def test_split_meter_reserved_from_ordinary_reclaim_and_concurrent_live_edits(meter_key):
    runtime, _hass = configured()
    runtime.panasonic.settings.update(power_entity="", **{meter_key: "sensor.load"})
    assert not runtime._dedicated_meter("a")
    before = deepcopy(runtime.entry.options)
    after = deepcopy(before)
    after["sg_boost"].update(power_entity="", **{meter_key: "sensor.load"})
    with pytest.raises(HomeAssistantError, match="toestelmeter"):
        runtime.live_options._validate_meter_scopes(before, after)


def test_profile_change_waits_for_manual_active_relay_and_preserves_hold():
    runtime, _hass = live_sg_runtime()
    runtime.sg_boost.manual_hold = True
    runtime.sg_boost.relay_on = True
    before = deepcopy(runtime.sg_boost.settings)
    after = {**before, "profile": "general", "profile_confirmed": True}
    reason = runtime.live_options.group_block("sg_boost", before, after)
    assert "vrijgave" in reason
    assert runtime.sg_boost.manual_hold


def test_private_source_suggestions_cannot_grant_new_control_permissions():
    runtime, hass = configured()
    hass.states.set("sensor.public_frequency", 25, {"unit_of_measurement": "Hz"})
    hass.states.set("binary_sensor.public_sg_received", "on")
    raw = {"power_supply1_entity": "sensor.public_hp", "power_supply2_entity": "sensor.load",
           "compressor_frequency_entity": "sensor.public_frequency",
           "sg_status_entity": "binary_sensor.public_sg_received",
           "profile": "general", "profile_confirmed": True,
           "cooling_protection_confirmed": True, "split_power_confirmed": True,
           "enabled": True, "commissioning_confirmed": True, "watchdog_confirmed": True}
    bundle = {"format": BUNDLE_FORMAT, "profile": {"suggestions": {"sg_boost": raw}}}
    suggestions = private_group_suggestions(hass, "sg_boost", bundle)
    assert suggestions["compressor_frequency_entity"] == "sensor.public_frequency"
    assert suggestions["sg_status_entity"] == "binary_sensor.public_sg_received"
    assert all(key not in suggestions for key in
               ("profile", "profile_confirmed", "cooling_protection_confirmed", "split_power_confirmed"))
    imported, _report = build_private_import(hass, {}, {}, bundle=bundle)
    c = normalize_config(imported["sg_boost"])
    assert c["profile"] == "dhw_only"
    assert all(c[key] is False for key in
               ("enabled", "profile_confirmed", "cooling_protection_confirmed", "split_power_confirmed"))
    assert not hass.services.calls


def test_beta63_immutable_nested_config_and_private_archive_remain_idempotent():
    runtime, _hass = configured()
    options = deepcopy(runtime.entry.options)
    options["_panasonic_migration"] = 1
    options["retained"] = {"nested": [{"value": "preserve"}]}
    old_sg = deepcopy(options["sg_boost"])
    archive = {"version": 1, "read_only": True, "backup_options": {"legacy": [1, 2]},
               "backup_store": {"history": [3, 4]}, "assessment": {"changed": True}}
    stored = {"panasonic_archive": archive, "sg_boost": {"schema": 1, "completion_hold": True,
              "manual_hold": True, "relay_entity": old_sg["entity_id"]}, "history": [5, 6]}
    before = deepcopy(options), deepcopy(stored)
    new, data, report = migrate_panasonic(MappingProxyType(options), stored)
    assert not report["changed"]
    assert new["sg_boost"] == old_sg and data["sg_boost"] == stored["sg_boost"]
    assert data["panasonic_archive"] == archive and new["retained"] == options["retained"]
    again, repeated, report2 = migrate_panasonic(MappingProxyType(new), data)
    assert again == new and repeated == data and not report2["changed"]
    assert (options, stored) == before


@pytest.mark.parametrize("key", ["power_supply1_entity", "power_supply2_entity",
                                "compressor_frequency_entity", "sg_status_entity"])
def test_new_readonly_bindings_remain_inside_panasonic_command_deny_boundary(key):
    runtime, hass = configured()
    c = {**runtime.sg_boost.settings, key: "switch.public_native_source"}
    runtime.entry.options["sg_boost"] = c
    assert runtime.command_authority.is_native("switch.public_native_source")
    with pytest.raises(HomeAssistantError):
        runtime.command_authority.assert_allowed("switch", "turn_on", "switch.public_native_source")
    assert not hass.services.calls
