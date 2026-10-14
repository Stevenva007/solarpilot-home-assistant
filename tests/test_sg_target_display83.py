"""Local display metadata, original target time and immutable SG comparison history."""
from copy import deepcopy
from datetime import timedelta

import pytest

from custom_components.solar_pilot.sg_config import normalize_config, validate_config, DISPLAY_ONLY_KEYS
from custom_components.solar_pilot.sg_target_display import calculate_sg_tank_goal as calculate_raw, contact_observation, resolved_goal_binding
from custom_components.solar_pilot.heatpump_history import HeatpumpHistory
from test_heatpump_history70 import BASE, observe, sg
from test_heatpump_history81 import tank_source
from test_sg_config62 import actual_flow_class, hass_with
from test_live_config34 import flow_class

NOW = BASE.timestamp()
BINDING = "a"*64


def calculate_sg_tank_goal(config, tank, now):
    return calculate_raw(config, {"entity_id": "water_heater.synthetic_tank", **tank}, now, source_binding=BINDING)


def profile(percent=115, confirmed=NOW-10):
    return normalize_config({"sg_dhw_capacity_percent": percent, "sg_dhw_capacity_confirmed": True,
                             "sg_dhw_capacity_confirmed_at": confirmed, "sg_dhw_capacity_target_entity": "water_heater.synthetic_tank",
                             "sg_dhw_capacity_binding": BINDING})


def snapshot(at=BASE, *, percent=115, confirmed=NOW-10, target=50):
    p = tank_source(at, target=target)
    p["sg_tank_goal"] = calculate_sg_tank_goal(profile(percent, confirmed), p["display_tank"], at.timestamp())
    return p


def test_confirmed_115_uses_normal_celsius_target_without_native_goal_feedback_or_mutation():
    c = profile(); tank = {"target_c": 50, "target_stamp": NOW-7, "temperature_c": 48,
                          "max_temp": 55, "sg_received": "unknown"}
    before = deepcopy((c, tank))
    result = calculate_sg_tank_goal(c, tank, NOW)
    assert result["calculated_c"] == 57.5 and result["normal_target_c"] == 50
    assert result["normal_target_reported_at"] == NOW-7 and result["valid_until"] == NOW+113
    assert result["source"] == "local_confirmed_profile" and result["profile_confirmed_at"] == NOW-10
    assert result["read_only"] is True and "applied_target" not in result
    assert (c, tank) == before


@pytest.mark.parametrize("changes,reason", [
    ({"sg_dhw_capacity_confirmed": False}, "profile_unconfirmed"),
    ({"sg_dhw_capacity_percent": None}, "profile_invalid"),
    ({"sg_dhw_capacity_percent": True}, "profile_invalid"),
    ({"sg_dhw_capacity_percent": float("nan")}, "profile_invalid"),
    ({"sg_dhw_capacity_confirmed_at": 0}, "profile_confirmation_invalid"),
    ({"sg_dhw_capacity_confirmed_at": NOW+1}, "profile_confirmation_invalid"),
])
def test_missing_invalid_or_future_local_confirmation_never_invents_goal(changes, reason):
    c = {**profile(), **changes}
    result = calculate_sg_tank_goal(c, {"target_c": 50, "target_stamp": NOW-7}, NOW)
    assert result["calculated_c"] is None and result["reason"] == reason


def test_public_default_never_claims_confirmed_100_or_115_percent():
    result = calculate_sg_tank_goal(normalize_config(), {"target_c": 50, "target_stamp": NOW-7}, NOW)
    assert result["profile_percent"] is None and result["calculated_c"] is None
    assert result["reason"] == "profile_unconfirmed"


@pytest.mark.parametrize("target,stamp", [(None, NOW), (True, NOW), (50, 0), (50, NOW-121), (50, NOW+6)])
def test_normal_goal_must_be_fresh_valid_and_source_timed(target, stamp):
    result = calculate_sg_tank_goal(profile(), {"target_c": target, "target_stamp": stamp}, NOW)
    assert result["normal_target_c"] is None and result["calculated_c"] is None
    assert result["reason"] == "normal_target_unavailable"


def test_unknown_sg_limit_is_never_silently_capped_with_ordinary_ha_limit():
    result = calculate_sg_tank_goal(profile(150), {"target_c": 80, "target_stamp": NOW, "max_temp": 65}, NOW)
    assert result["calculated_c"] is None and result["reason"] == "calculated_target_out_of_range"


@pytest.mark.parametrize("key,value", [("configured", False), ("relay_confirmed", False),
    ("relay_observed_at", NOW-121), ("relay_on", None), ("relay_valid_until", NOW-1)])
def test_requested_or_expired_contact_does_not_become_actual_on(key, value):
    value = contact_observation({**sg(BASE, request=True, contact=True), key: value}, NOW)
    assert value["contact_state"] == "unknown"


def test_recorded_factor_changes_only_new_comparisons_and_keeps_contact_separate():
    model = HeatpumpHistory()
    observe(model, BASE, p=snapshot(), s=sg(BASE, request=True, contact=False))
    changed = BASE+timedelta(seconds=5)
    observe(model, changed, p=snapshot(changed, percent=120, confirmed=changed.timestamp()),
            s=sg(changed, request=False, contact=True))
    detail = model.detail(None, changed)["tank_temperature"]
    first, second = [row["sg_goal"] for row in detail["points"]]
    assert (first["calculated_c"], first["profile_percent"], first["contact_state"]) == (57.5, 115, "off")
    assert (second["calculated_c"], second["profile_percent"], second["contact_state"]) == (60, 120, "on")
    assert second["profile_confirmed_at"] == changed.timestamp()
    assert detail["current"]["sg_goal"] == second
    stored = model.snapshot()
    restored = HeatpumpHistory(); restored.restore(stored, changed+timedelta(seconds=5))
    historical = restored.detail(None, changed+timedelta(seconds=5))["tank_temperature"]
    assert [row["sg_goal"] for row in historical["points"]] == [first, second]
    assert historical["current"]["sg_goal"] is None  # No live state restored from history.


def test_pre_feature_history_remains_without_calculated_targets():
    model = HeatpumpHistory(); observe(model, BASE, p=tank_source(BASE))
    stored = model.snapshot()
    for row in stored["native_evidence"]["points"]:
        row.pop("sg_goal", None)
    restored = HeatpumpHistory(); restored.restore(stored, BASE+timedelta(seconds=5))
    assert restored.detail(None, BASE+timedelta(seconds=5))["tank_temperature"]["points"][0]["sg_goal"] is None


def test_history_live_goal_expires_at_original_target_time_even_when_capture_is_recent():
    model = HeatpumpHistory(); p = snapshot()
    p["display_tank"]["target_stamp"] = NOW-115
    p["sg_tank_goal"] = calculate_sg_tank_goal(profile(), p["display_tank"], NOW)
    observe(model, BASE, p=p, s=sg(BASE, contact=True))
    live = model.detail(None, BASE+timedelta(seconds=6))["tank_temperature"]["current"]
    assert live["current"] is True and live["sg_goal"]["calculated_c"] is None
    assert live["sg_goal"]["normal_target_reported_at"] == NOW-115
    assert live["sg_goal"]["contact_state"] == "on"


@pytest.mark.parametrize("field,value", [("calculated_c", 60), ("profile_confirmed_at", NOW+1),
    ("normal_target_reported_at", NOW), ("contact_state", "requested"), ("calculated_c", True),
    ("contact_reported_at", True), ("contact_valid_until", NOW-1)])
def test_corrupt_goal_math_times_or_contact_cannot_be_restored(field, value):
    model = HeatpumpHistory(); observe(model, BASE, p=snapshot(), s=sg(BASE, contact=True))
    stored = model.snapshot(); stored["native_evidence"]["points"][0]["sg_goal"][field] = value
    with pytest.raises(ValueError):
        HeatpumpHistory().restore(stored, BASE+timedelta(seconds=5))


@pytest.mark.asyncio
async def test_display_metadata_live_change_preserves_sg_dispatch_windows_and_control_permissions():
    from test_sg_config62 import live_sg_runtime
    runtime, hass = live_sg_runtime()
    runtime.sg_boost._stable_since = 1234
    runtime.sg_boost.desired_on = True
    runtime.sg_boost.completion_hold = True
    native_before = deepcopy({key: runtime.panasonic.overview().get(key) for key in (
        "context", "context_reliable", "context_signature", "cooling_possible", "sg_status", "sg_effect_confirmed")})
    before = (runtime.sg_boost._generation, runtime.sg_boost._stable_since, runtime.sg_boost.desired_on,
              runtime.sg_boost.completion_hold, runtime.sg_boost.settings["profile_confirmed"])
    base = deepcopy(runtime.entry.options); desired = deepcopy(base)
    desired["sg_boost"].update(profile())
    # Only the three display fields are edited; all actuator policy is retained.
    desired["sg_boost"] = {**base["sg_boost"], **{key: profile()[key] for key in
        ("sg_dhw_capacity_percent", "sg_dhw_capacity_confirmed", "sg_dhw_capacity_confirmed_at", "sg_dhw_capacity_binding", "sg_dhw_capacity_target_entity")}}
    await runtime.live_options.submit(base, desired)
    assert before == (runtime.sg_boost._generation, runtime.sg_boost._stable_since, runtime.sg_boost.desired_on,
                      runtime.sg_boost.completion_hold, runtime.sg_boost.settings["profile_confirmed"])
    assert runtime.panasonic.settings["sg_dhw_capacity_percent"] == 115 and not hass.services.calls
    assert native_before == {key: runtime.panasonic.overview().get(key) for key in native_before}
    assert runtime.panasonic.settings["tank_target_entity"] == base["sg_boost"]["tank_target_entity"]
    assert {"sg_dhw_capacity_percent", "sg_dhw_capacity_confirmed", "sg_dhw_capacity_confirmed_at"} <= DISPLAY_ONLY_KEYS


@pytest.mark.asyncio
async def test_options_confirmation_dates_new_factor_and_source_changes_without_device_write(monkeypatch):
    class F(actual_flow_class()):
        def _base_options(self): return self.options
        def _site(self): return {}
        def async_show_form(self, **kw): return kw
        async def _save(self, opts): self.options = opts; return {"saved": opts}
    flow = F(); flow.options = {"sg_boost": normalize_config()}
    flow.hass = hass_with(**{"water_heater.synthetic_tank": {}})
    monkeypatch.setattr("time.time", lambda: NOW)
    import sys
    monkeypatch.setattr(sys.modules["custom_components.solar_pilot.sg_target_display"], "resolved_goal_binding", lambda h, e: BINDING if e else None)
    result = await flow.async_step_sg_sources({"sg_dhw_capacity_target_entity": "water_heater.synthetic_tank",
        "sg_dhw_capacity_percent": 115, "sg_dhw_capacity_confirmed": True})
    assert result["saved"]["sg_boost"]["sg_dhw_capacity_confirmed_at"] == NOW
    changed = await flow.async_step_sg_sources({"sg_dhw_capacity_percent": 120})
    assert changed["saved"]["sg_boost"]["sg_dhw_capacity_confirmed"] is False
    assert changed["saved"]["sg_boost"]["sg_dhw_capacity_confirmed_at"] == 0
    assert not flow.hass.services.calls


@pytest.mark.parametrize("key,value", [("sg_dhw_capacity_percent", True), ("sg_dhw_capacity_percent", 99),
                                      ("sg_dhw_capacity_confirmed", "true"), ("sg_dhw_capacity_confirmed_at", True)])
def test_bad_local_metadata_is_visible_validation_error(key, value):
    assert key in validate_config({key: value})


@pytest.mark.parametrize("config_patch,tank,actual_binding", [
    ({"sg_dhw_capacity_target_entity": ""}, {"entity_id": "water_heater.synthetic_tank"}, BINDING),
    ({"sg_dhw_capacity_target_entity": "sensor.scalar_target"}, {"entity_id": "water_heater.synthetic_tank"}, BINDING),
    ({}, {"entity_id": "water_heater.other_tank"}, BINDING),
    ({}, {"entity_id": "water_heater.synthetic_tank"}, "b"*64),
    ({}, {"entity_id": "water_heater.synthetic_tank"}, None),
])
def test_profile_cannot_follow_autodiscovery_another_tank_or_reused_entity_identity(config_patch, tank, actual_binding):
    result = calculate_raw({**profile(), **config_patch}, {**tank, "target_c": 50, "target_stamp": NOW}, NOW,
                           source_binding=actual_binding)
    assert result["calculated_c"] is None and result["profile_percent"] is None
    assert result["reason"] == "profile_source_unbound"


def test_registry_binding_changes_when_same_entity_id_is_reused_for_other_device(monkeypatch):
    from types import SimpleNamespace, ModuleType
    import sys
    from homeassistant import helpers
    entry = SimpleNamespace(entity_id="water_heater.synthetic_tank", platform="aquarea", unique_id="synthetic_dhw",
                            device_id="synthetic_device", config_entry_id="synthetic_entry")
    registry = ModuleType("homeassistant.helpers.entity_registry")
    registry.async_get = lambda h: SimpleNamespace(async_get=lambda eid: entry)
    monkeypatch.setitem(sys.modules, registry.__name__, registry)
    monkeypatch.setattr(helpers, "entity_registry", registry, raising=False)
    first = resolved_goal_binding(None, entry.entity_id)
    assert len(first) == 64 and "synthetic" not in first
    entry.device_id = "different_device"
    assert resolved_goal_binding(None, entry.entity_id) != first
    entry.unique_id = None
    assert resolved_goal_binding(None, entry.entity_id) is None


@pytest.mark.asyncio
async def test_capacity_confirmation_without_explicit_registered_tank_is_visible_form_error(monkeypatch):
    class F(actual_flow_class()):
        def _base_options(self): return self.options
        def _site(self): return {}
        def async_show_form(self, **kw): return kw
        async def _save(self, opts): raise AssertionError("Unbound percentage cannot be confirmed")
    flow = F(); flow.options = {"sg_boost": normalize_config()}; flow.hass = hass_with()
    result = await flow.async_step_sg_sources({"sg_dhw_capacity_percent": 115, "sg_dhw_capacity_confirmed": True})
    assert result["errors"]["sg_dhw_capacity_confirmed"] == "sg_target_binding"
    assert not flow.hass.services.calls


@pytest.mark.asyncio
async def test_imported_or_stale_capacity_confirmation_cannot_bypass_local_options_choice(flow_class):
    from test_runtime import build
    runtime, hass = build(); flow = flow_class(runtime)
    desired = deepcopy(flow._base_options())
    desired["sg_boost"] = profile()
    await flow._live_save(desired)
    assert flow._live_desired["sg_boost"]["sg_dhw_capacity_confirmed"] is False
    assert flow._live_desired["sg_boost"]["sg_dhw_capacity_binding"] == ""
    assert flow._live_desired["sg_boost"]["sg_dhw_capacity_confirmed_at"] == 0
    assert not hass.services.calls


def test_capacity_only_choice_does_not_change_other_history_lane_binding():
    from test_runtime import build
    from custom_components.solar_pilot.heatpump_history_runtime import history_binding
    runtime, _hass = build()
    before = history_binding(runtime, runtime.panasonic.overview(), runtime.sg_boost.overview())
    current = deepcopy(runtime.panasonic.settings)
    current.update({key: profile()[key] for key in (
        "sg_dhw_capacity_percent", "sg_dhw_capacity_confirmed", "sg_dhw_capacity_confirmed_at",
        "sg_dhw_capacity_binding", "sg_dhw_capacity_target_entity")})
    runtime.panasonic.update_config(current); runtime.sg_boost.update_config(current)
    assert history_binding(runtime, runtime.panasonic.overview(), runtime.sg_boost.overview()) == before
