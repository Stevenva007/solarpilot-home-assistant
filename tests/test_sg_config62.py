"""One SG config schema and the actual native options method bodies."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import ast
import pytest

from custom_components.solar_pilot.sg_config import SG_DEFAULTS, normalize_config, validate_config, actuator_conflicts, source_errors
from custom_components.solar_pilot.first_install import apply_first_install_suggestions
from custom_components.solar_pilot.private_bundle import private_group_suggestions, build_private_import, BUNDLE_FORMAT


def hass_with(**states):
    data = {eid: SimpleNamespace(state="off", attributes=attrs) for eid, attrs in states.items()}
    return SimpleNamespace(states=SimpleNamespace(get=lambda eid: data.get(eid)), services=SimpleNamespace(calls=[]))


def test_default_disabled_and_no_legacy_keys_survive_normalization():
    c = normalize_config({"surplus_c": 60, "control_enabled": True, "pending": {"target": 60}})
    assert c == SG_DEFAULTS
    assert not validate_config(c)


@pytest.mark.parametrize("key", ["enabled", "commissioning_confirmed", "watchdog_confirmed"])
def test_boolean_authority_is_not_coerced(key):
    assert key in validate_config({key: "true"})


@pytest.mark.parametrize("key,value", [("entity_id", "input_boolean.sg"), ("entity_id", "script.sg"),
    ("zone_entities", "climate.a"), ("zone_entities", [None]), ("zone_entities", [{"id": "a"}]),
    ("power_scope", {"bad": True}), ("expected_power_w", float("nan")), ("lease_s", True),
    ("hysteresis_w", 3500), ("renew_s", 300)])
def test_invalid_shapes_and_unsafe_timing_show_validation_errors(key, value):
    assert validate_config({key: value})


def test_sg_cannot_enable_without_separate_commissioning_and_timer_proof():
    errors = validate_config({"entity_id": "switch.sg_contact", "enabled": True})
    assert errors == {"commissioning_confirmed": "sg_commissioning", "watchdog_confirmed": "sg_watchdog"}


def test_duplicate_actuator_detected_even_if_ordinary_device_disabled():
    assert actuator_conflicts({"entity_id": "switch.sg_contact"}, [{"id": "a", "enabled": False, "control_entity": "switch.sg_contact"}]) == ["a"]


def test_duplicate_validation_tolerates_unrelated_damaged_endpoint():
    rows = [{"id": "a", "control_entity": "switch.sg_contact", "active_entity": {"bad": True}}]
    assert actuator_conflicts({"entity_id": "switch.sg_contact"}, rows) == ["a"]


def test_battery_profile_cannot_claim_the_sg_relay():
    h = hass_with(**{"switch.sg_contact": {}})
    errors = source_errors(h, {"entity_id": "switch.sg_contact"},
                           batteries=[{"id": "b", "number_entity": "switch.sg_contact"}])
    assert errors["entity_id"] == "sg_duplicate" and not h.services.calls


@pytest.mark.parametrize("source,value", [("power_entity", {"bad": True}),
                                         ("zone_entities", [{"bad": True}])])
def test_damaged_sources_return_errors_without_read_or_service_crash(source, value):
    h = hass_with()
    assert source in source_errors(h, {source: value})
    assert not h.services.calls


def test_relay_and_monitoring_links_validation_never_makes_physical_calls():
    h = hass_with(**{"switch.sg_contact": {}, "sensor.hp": {"unit_of_measurement": "kWh"}})
    errors = source_errors(h, {"entity_id": "switch.sg_contact", "power_entity": "sensor.hp"})
    assert errors["power_entity"] == "power_unit" and not h.services.calls


def test_old_private_profile_imports_read_only_sources_never_old_controller():
    h = hass_with(**{"water_heater.generic_tank": {}, "sensor.tank": {}, "climate.zone_a": {}})
    bundle = {"format": BUNDLE_FORMAT, "profile": {"suggestions": {
        "dhw": {"target_entity": "water_heater.generic_tank", "temperature_entity": "sensor.tank", "enabled": True},
        "smart_climate": {"zone_entities": ["climate.zone_a"], "control_enabled": True}}}}
    links = private_group_suggestions(h, "sg_boost", bundle)
    assert links["tank_target_entity"] == "water_heater.generic_tank" and links["zone_entities"] == ["climate.zone_a"]
    new, _ = build_private_import(h, {}, {}, bundle=bundle)
    assert "dhw" not in new and "smart_climate" not in new
    assert all(new["sg_boost"][k] is False for k in ("enabled", "commissioning_confirmed", "watchdog_confirmed"))


def actual_flow_class():
    """Run production methods with UI-only HA selector doubles, not a Core server."""
    path = Path(__file__).parents[1] / "custom_components/solar_pilot/config_flow.py"
    tree = ast.parse(path.read_text())
    cls = next(x for x in tree.body if isinstance(x, ast.ClassDef) and x.name == "SolarPilotOptions")
    cls.bases = []; cls.keywords = []
    selectors = SimpleNamespace(BooleanSelector=lambda: "bool", EntitySelector=lambda data: data,
                                SelectSelector=lambda data: data)
    vol = SimpleNamespace(Required=lambda key, **kw: key, Optional=lambda key, **kw: key, Schema=lambda data: data)
    env = {"deepcopy": deepcopy, "SG_DEFAULTS": SG_DEFAULTS, "normalize_sg": normalize_config,
           "sg_errors": source_errors, "apply_first_install_suggestions": apply_first_install_suggestions,
           "selector": selectors, "vol": vol, "optional": lambda key, c: key,
           "entity": lambda domains: domains, "num": lambda lo, hi, step=1: (lo, hi, step)}
    exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])), str(path), "exec"), env)
    return env["SolarPilotOptions"]


@pytest.fixture
def flow():
    class F(actual_flow_class()):
        def _base_options(self): return self.options
        def _site(self): return {"pv_entity": "sensor.pv"}
        def async_show_form(self, **kw): return kw
        def async_show_menu(self, **kw): return kw
        async def _save(self, opts): self.saved = opts; return {"saved": opts}
    f = F(); f.options = {"sg_boost": normalize_config()}; f.saved = None
    f.hass = hass_with(**{"switch.sg_contact": {}, "switch.sg_other": {}, "sensor.pv": {"unit_of_measurement": "W"}})
    return f


@pytest.mark.asyncio
async def test_actual_options_menu_only_exposes_current_sg_pages(flow):
    menu = await flow.async_step_comfort_hub()
    assert menu["menu_options"] == ["sg_boost", "sg_sources", "sg_advanced"]


@pytest.mark.asyncio
async def test_actual_new_binding_save_never_accepts_checked_old_proofs(flow):
    result = await flow.async_step_sg_boost({"entity_id": "switch.sg_contact", "enabled": True,
         "commissioning_confirmed": True, "watchdog_confirmed": True})
    assert result["saved"]["sg_boost"]["entity_id"] == "switch.sg_contact"
    assert all(result["saved"]["sg_boost"][k] is False for k in ("enabled", "commissioning_confirmed", "watchdog_confirmed"))
    assert not flow.hass.services.calls


@pytest.mark.asyncio
async def test_actual_confirmed_current_binding_can_save_automatic_permission(flow):
    flow.options["sg_boost"]["entity_id"] = "switch.sg_contact"
    result = await flow.async_step_sg_boost({"entity_id": "switch.sg_contact", "enabled": True,
         "commissioning_confirmed": True, "watchdog_confirmed": True})
    assert result["saved"]["sg_boost"]["enabled"] is True
    assert not flow.hass.services.calls


@pytest.mark.asyncio
async def test_actual_sources_form_clears_only_omitted_readonly_links(flow):
    flow.options["sg_boost"].update(entity_id="switch.sg_contact", tank_target_entity="water_heater.old", power_entity="sensor.old")
    result = await flow.async_step_sg_sources({"power_scope": "unconfirmed"})
    assert result["saved"]["sg_boost"]["tank_target_entity"] == ""
    assert result["saved"]["sg_boost"]["power_entity"] == ""
    assert result["saved"]["sg_boost"]["entity_id"] == "switch.sg_contact"


@pytest.mark.asyncio
async def test_reopened_form_reads_current_revoked_proof_without_losing_other_baselines(flow):
    flow.options["sg_boost"].update(entity_id="switch.sg_contact", enabled=True,
                                  commissioning_confirmed=True, watchdog_confirmed=True)
    flow.options["economy"] = {"changed_elsewhere": "old"}
    fresh = deepcopy(flow.options)
    fresh["sg_boost"].update(commissioning_confirmed=False, watchdog_confirmed=False)
    fresh["economy"]["changed_elsewhere"] = "new"
    flow.config_entry = SimpleNamespace(options=fresh)
    await flow.async_step_sg_boost()
    assert flow.options["sg_boost"]["watchdog_confirmed"] is False
    assert flow.options["economy"]["changed_elsewhere"] == "old"


@pytest.mark.asyncio
async def test_stale_checked_form_cannot_reconfirm_revoked_firmware_proof(flow):
    flow.options["sg_boost"].update(entity_id="switch.sg_contact", enabled=True,
                                  commissioning_confirmed=True, watchdog_confirmed=True)
    flow.config_entry = SimpleNamespace(options=deepcopy(flow.options))
    await flow.async_step_sg_boost()
    flow.config_entry.options["sg_boost"].update(commissioning_confirmed=False, watchdog_confirmed=False)
    stale = {key: flow.options["sg_boost"][key] for key in
             ("entity_id", "enabled", "commissioning_confirmed", "watchdog_confirmed")}
    result = await flow.async_step_sg_boost(stale)
    assert result["errors"] == {"base": "sg_reopen"} and flow.saved is None
    assert flow.options["sg_boost"]["watchdog_confirmed"] is False
    assert not flow.hass.services.calls

    # After reviewing the newly displayed unchecked values, the user can give
    # explicit fresh proof; a prior checkbox does not count as that decision.
    result = await flow.async_step_sg_boost(stale)
    assert result["saved"]["sg_boost"]["watchdog_confirmed"] is True


def live_sg_runtime():
    from test_runtime import build
    r, h = build()
    config = normalize_config({"entity_id": "switch.sg_contact", "enabled": True,
                              "commissioning_confirmed": True, "watchdog_confirmed": True})
    r.entry.options["sg_boost"] = deepcopy(config)
    r.sg_boost.update_config(config)
    r.panasonic.update_config(config)
    r.live_options.applied = deepcopy(r.entry.options)
    return r, h


@pytest.mark.asyncio
async def test_live_disable_invalidates_new_starts_even_when_sg_command_busy():
    r, h = live_sg_runtime()
    r.sg_boost._in_flight = True
    r.sg_boost.desired_on = True
    base = deepcopy(r.entry.options); desired = deepcopy(base)
    desired["sg_boost"]["enabled"] = False
    await r.live_options.submit(base, desired)
    assert r.entry.options["sg_boost"]["enabled"] is False
    assert r.sg_boost.auto_enabled is False and r.sg_boost.desired_on is False
    assert not r.entry.options["_live_pending"] and not h.services.calls


@pytest.mark.asyncio
async def test_live_rebinding_keeps_old_sg_endpoint_until_release_is_observed():
    r, h = live_sg_runtime()
    r.sg_boost.owned = True
    r.sg_boost.relay_on = True
    base = deepcopy(r.entry.options); desired = deepcopy(base)
    desired["sg_boost"].update(entity_id="switch.sg_other", enabled=False,
                               commissioning_confirmed=False, watchdog_confirmed=False)
    await r.live_options.submit(base, desired)
    assert r.entry.options["sg_boost"]["entity_id"] == "switch.sg_contact"
    assert "group:sg_boost" in r.entry.options["_live_pending"]
    assert r.sg_boost.settings["entity_id"] == "switch.sg_contact" and not h.services.calls


@pytest.mark.asyncio
async def test_live_source_edit_updates_both_monitor_and_sg_without_actuating():
    r, h = live_sg_runtime()
    base = deepcopy(r.entry.options); desired = deepcopy(base)
    desired["sg_boost"]["tank_temperature_entity"] = "sensor.generic_tank"
    await r.live_options.submit(base, desired)
    assert r.sg_boost.settings["tank_temperature_entity"] == "sensor.generic_tank"
    assert r.panasonic.settings["tank_temperature_entity"] == "sensor.generic_tank"
    assert not h.services.calls


@pytest.mark.asyncio
async def test_unrelated_hot_edit_does_not_restore_revoked_sg_proof_from_old_base():
    r, h = live_sg_runtime()
    base = deepcopy(r.entry.options); desired = deepcopy(base)
    desired["devices"][0]["name"] = "Renamed appliance"
    # Firmware observation updates effective options between opening and save.
    r.entry.options["sg_boost"].update(commissioning_confirmed=False, watchdog_confirmed=False, enabled=False)
    r.sg_boost.update_config(r.entry.options["sg_boost"])
    await r.live_options.submit(base, desired)
    assert r.configs["a"]["name"] == "Renamed appliance"
    assert r.entry.options["sg_boost"]["watchdog_confirmed"] is False
    assert r.sg_boost.settings["watchdog_confirmed"] is False and not h.services.calls
