"""SG-only authority at the real runtime boundary, using HA service recording.

All entity names and saved evidence are fictitious. These are software tests,
not a claim that a relay lease or a manufacturer's SG response was tried live.
"""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace
import ast
import time

import pytest
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er

from custom_components.solar_pilot.runtime import SolarRuntime
from custom_components.solar_pilot.panasonic_authority import PanasonicCommandAuthority
from test_runtime import build

ROOT = Path(__file__).resolve().parents[1]
COMPONENT = ROOT / "custom_components" / "solar_pilot"
NATIVE_TARGETS = {
    "water_heater.native_tank", "number.native_tank_target",
    "climate.native_zone_one", "climate.native_zone_two",
    "switch.native_heater", "select.native_program", "button.native_powerful",
}

def actuator_calls(hass):
    """Read-only forecast/notification calls are not equipment writes."""
    return [call for call in hass.services.calls
            if call[0] not in {"weather", "persistent_notification"}]

def obsolete_installation(*, target="water_heater.native_tank"):
    runtime, hass = build(settings={"pv_entity": "sensor.pv", "settle_s": 0,
                                   "filter_s": 0, "reserve_w": 0})
    # Real legacy keys intentionally remain in the input: they cannot create
    # permission merely because a second writer once owned those endpoints.
    runtime.entry.options.update({
        "dhw": {"enabled": True, "safety_confirmed": True,
                "target_entity": target, "temperature_entity": "sensor.native_tank",
                "power_entity": "sensor.native_power", "night_enabled": False,
                "hygiene_schedule_enabled": False, "rise_delay_s": 0,
                "command_min_interval_s": 0, "surplus_threshold_w": 1000},
        "smart_climate": {"enabled": True, "control_enabled": True,
                          "zone_entities": ["climate.native_zone_one", "climate.native_zone_two"],
                          "automatic_control_enabled": True},
    })
    hass.config = SimpleNamespace(time_zone="UTC", units=SimpleNamespace(temperature_unit="°C"))
    hass.states.set("sensor.grid", -7000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.pv", 8000, {"unit_of_measurement": "W"})
    hass.states.set("sensor.native_tank", 42, {"unit_of_measurement": "°C"})
    hass.states.set("sensor.native_power", 2200, {"unit_of_measurement": "W"})
    hass.states.set("water_heater.native_tank", "heat_pump", {
        "temperature": 60, "current_temperature": 42, "temperature_unit": "°C",
        "supported_features": 1, "min_temp": 30, "max_temp": 65,
        "target_temp_step": 1, "hvac_action": "heating",
    })
    hass.states.set("number.native_tank_target", 60, {
        "unit_of_measurement": "°C", "min": 30, "max": 65, "step": 1,
    })
    for entity_id in ("climate.native_zone_one", "climate.native_zone_two"):
        hass.states.set(entity_id, "off", {"current_temperature": 19,
                                         "temperature": 21, "hvac_action": "off"})
    return SolarRuntime(hass, runtime.entry), hass

@pytest.mark.asyncio
@pytest.mark.parametrize("entity_id,service,extra", [
    ("water_heater.native_tank", "set_temperature", {"temperature": 60}),
    ("water_heater.native_tank", "turn_on", None),
    ("water_heater.native_tank", "turn_off", None),
    ("water_heater.native_tank", "set_operation_mode", {"operation_mode": "heat_pump"}),
    ("climate.native_zone_one", "set_hvac_mode", {"hvac_mode": "auto"}),
    ("climate.native_zone_one", "set_hvac_mode", {"hvac_mode": "off"}),
    ("climate.native_zone_one", "set_temperature", {"temperature": 22}),
    ("climate.unconfigured_zone", "turn_on", None),
    ("water_heater.unconfigured_tank", "set_temperature", {"temperature": 60}),
])
async def test_native_climate_and_tank_domains_have_no_generic_writer_authority(entity_id, service, extra):
    runtime, hass = obsolete_installation()
    with pytest.raises(HomeAssistantError):
        await runtime._call(entity_id, service, extra)
    assert actuator_calls(hass) == []

@pytest.mark.asyncio
@pytest.mark.parametrize("entity_id,service,extra", [
    ("number.native_tank_target", "set_value", {"value": 60}),
    ("switch.native_heater", "turn_on", None),
    ("select.native_program", "select_option", {"option": "cool"}),
    ("button.native_powerful", "press", None),
])
async def test_other_entities_of_the_native_heatpump_device_are_also_read_only(monkeypatch, entity_id, service, extra):
    runtime, hass = obsolete_installation(target="number.native_tank_target")
    rows = {entity: SimpleNamespace(device_id="native-pump", platform="aquarea",
                                    config_entry_id="native-entry")
            for entity in NATIVE_TARGETS}
    monkeypatch.setattr(er, "async_get", lambda _hass: SimpleNamespace(async_get=rows.get))
    hass.config_entries = SimpleNamespace(async_get_entry=lambda _id: SimpleNamespace(domain="aquarea"))
    with pytest.raises(HomeAssistantError):
        await runtime._call(entity_id, service, extra)
    assert actuator_calls(hass) == []

@pytest.mark.asyncio
@pytest.mark.parametrize("extra", [
    {"entity_id": "water_heater.native_tank"},
    {"entity_id": ["switch.load", "switch.native_heater"]},
    {"device_id": "native-pump"}, {"area_id": "native-area"},
    {"floor_id": "native-floor"}, {"label_id": "native-label"},
    {"target": {"entity_id": "switch.native_heater"}},
])
async def test_generic_extra_payload_cannot_replace_or_broaden_the_validated_target(extra):
    runtime, hass = obsolete_installation()
    with pytest.raises(HomeAssistantError):
        await runtime._call("switch.load", "turn_on", extra)
    assert actuator_calls(hass) == []

@pytest.mark.asyncio
async def test_safe_existing_load_and_number_control_still_use_their_exact_targets():
    runtime, hass = obsolete_installation()
    await runtime._call("switch.load", "turn_on")
    await runtime._call("number.amps", "set_value", {"value": 8})
    assert actuator_calls(hass) == [
        ("switch", "turn_on", {"entity_id": "switch.load"}),
        ("number", "set_value", {"entity_id": "number.amps", "value": 8}),
    ]

def obsolete_store(kind):
    stamp = time.time()
    dhw = {
        "auto_enabled": True, "owned_target": 60, "baseline_target": 50,
        "manual_hold": False, "needs_review": False,
    }
    climate = {"owned_off": ["climate.native_zone_one"],
               "expected_mode": {"climate.native_zone_one": "off"}}
    if kind == "pending":
        dhw["pending"] = {"target": 60, "issued_wall": stamp - 30,
                          "entity_id": "water_heater.native_tank", "release": False}
        climate["pending_commands"] = {
            "climate.native_zone_one": {"mode": "auto", "issued_wall": stamp - 30}}
    elif kind == "restart":
        dhw["restart_recovery"] = {"target": 50, "issued_wall": stamp - 30}
    elif kind == "automatic_recovery":
        dhw["fault"] = "Boileropdracht niet bevestigd; handmatige controle vereist"
        dhw["automatic_recovery"] = {"target": 60, "failed_wall": stamp - 100,
                                     "target_entity": "water_heater.native_tank"}
        dhw["recovery_budget"] = {"failures": 2, "not_before_wall": stamp + 900}
        dhw["failed_command"] = {"requested_target_c": 60, "reported_target_c": 50}
    elif kind == "manual_hold":
        dhw["manual_hold"] = True
    elif kind == "damaged_journals":
        dhw.update(pending=["broken"], automatic_recovery="broken",
                   recovery_budget=[1], restart_recovery={"target": float("nan")})
        climate["pending_commands"] = ["broken"]
    return {"mode": "observe", "auto_resume_after_restart": False,
            "dhw": dhw, "smart_climate": climate, "devices_modes": {},
            "energy_kwh": 12.5, "unknown_private_evidence": {"keep": True}}

@pytest.mark.asyncio
@pytest.mark.parametrize("target", ["water_heater.native_tank", "number.native_tank_target"])
@pytest.mark.parametrize("kind", ["pending", "restart", "automatic_recovery", "manual_hold", "damaged_journals"])
async def test_legacy_journals_never_replay_or_compensate_native_commands_through_lifecycle(target, kind):
    runtime, hass = obsolete_installation(target=target)
    original = obsolete_store(kind)
    runtime.store.data = deepcopy(original)
    await runtime.start()
    # A subsequent actual tick, explicit Pause and removal preparation must
    # not trigger the old target release or climate AUTO restoration.
    await runtime.tick()
    await runtime.set_mode("paused")
    await runtime.prepare_removal()
    await runtime.close()
    assert not [call for call in actuator_calls(hass)
                if call[0] in {"water_heater", "climate"}
                or call[2].get("entity_id") in NATIVE_TARGETS]
    assert runtime.energy_kwh == 12.5

@pytest.mark.asyncio
async def test_legacy_enabled_settings_cannot_restore_native_authority_when_global_solar_is_selected():
    runtime, hass = obsolete_installation()
    runtime.store.data = {"mode": "solar", "dhw": {"auto_enabled": True},
                          "smart_climate": {"enabled": True}, "device_modes": {"a": "disabled"}}
    await runtime.start()
    for _ in range(3):
        await runtime.tick()
    await runtime.close()
    assert not [call for call in actuator_calls(hass)
                if call[0] in {"water_heater", "climate"}
                or call[2].get("entity_id") in NATIVE_TARGETS]

def test_production_has_no_direct_native_temperature_or_hvac_service_dispatch():
    """A dormant exclusive controller is still an unwanted command path."""
    forbidden = {"set_temperature", "set_hvac_mode", "set_operation_mode",
                 "set_preset_mode", "set_aux_heat"}
    found = []
    for path in COMPONENT.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
                continue
            if node.func.attr not in {"async_call", "_call"}:
                continue
            # Native writes in beta.61 were sent directly or via _call; neither
            # may remain hidden behind an unused switch in the new release.
            constants = [arg.value for arg in node.args if isinstance(arg, ast.Constant)
                         and isinstance(arg.value, str)]
            if any(value in forbidden for value in constants):
                found.append(f"{path.name}:{node.lineno}")
    assert found == []

def install_scripts(hass, scripts):
    """Match the verified HA ScriptEntity.script.sequence read surface."""
    hass.data = {"script": SimpleNamespace(get_entity=lambda eid:
        SimpleNamespace(script=SimpleNamespace(sequence=scripts[eid]))
        if eid in scripts else None)}

def authority_runtime(monkeypatch):
    runtime, hass = build()
    rows = {eid: SimpleNamespace(entity_id=eid, device_id="native-pump",
                                  platform="aquarea", config_entry_id="native-entry")
            for eid in NATIVE_TARGETS}
    monkeypatch.setattr(er, "async_get", lambda _hass: SimpleNamespace(async_get=rows.get,
                                                                      entities=rows))
    return runtime, hass, PanasonicCommandAuthority(runtime), rows

def test_archived_native_bindings_remain_protected_without_active_old_controllers(monkeypatch):
    runtime, _hass, authority, rows = authority_runtime(monkeypatch)
    rows.clear()
    runtime.panasonic_archive = {"backup_options": {
        "dhw": {"target_entity": "number.native_tank_target"},
        "smart_climate": {"zone_entities": ["climate.native_zone_one"]}}}
    with pytest.raises(HomeAssistantError):
        authority.assert_allowed("number", "set_value", "number.native_tank_target", {"value": 50})
    assert authority.is_native("climate.native_zone_one")
    assert not authority.is_native("number.amps")

@pytest.mark.parametrize("enabled", [True, False])
@pytest.mark.parametrize("endpoint", ["switch.sg_contact", "switch.sg_alias", "number.sg_setting"])
def test_reserved_sg_device_is_never_an_ordinary_or_battery_target(monkeypatch, enabled, endpoint):
    runtime, _hass, authority, rows = authority_runtime(monkeypatch)
    runtime.entry.options["sg_boost"] = {"entity_id": "switch.sg_contact", "enabled": enabled}
    for eid in ("switch.sg_contact", "switch.sg_alias", "number.sg_setting"):
        rows[eid] = SimpleNamespace(entity_id=eid, device_id="sg-relay", platform="shelly")
    domain = endpoint.split(".", 1)[0]
    with pytest.raises(HomeAssistantError):
        authority.assert_allowed(domain, "set_value" if domain == "number" else "turn_on", endpoint)

def test_sg_rebind_changes_the_reserved_contact_without_cached_permission(monkeypatch):
    runtime, _hass, authority, _rows = authority_runtime(monkeypatch)
    runtime.entry.options["sg_boost"] = {"entity_id": "switch.first"}
    with pytest.raises(HomeAssistantError):
        authority.assert_allowed("switch", "turn_on", "switch.first")
    runtime.entry.options["sg_boost"] = {"entity_id": "switch.second"}
    with pytest.raises(HomeAssistantError):
        authority.assert_allowed("switch", "turn_on", "switch.second")
    assert authority.assert_allowed("switch", "turn_off", "switch.first") == {"entity_id": "switch.first"}

@pytest.mark.parametrize("branch", ["direct", "choose", "if", "repeat", "parallel", "sequence", "nested"])
@pytest.mark.parametrize("endpoint", ["water_heater.native_tank", "switch.native_heater", "switch.sg_contact"])
def test_every_indirect_script_branch_refuses_native_or_reserved_sg_writes(monkeypatch, branch, endpoint):
    runtime, hass, authority, _rows = authority_runtime(monkeypatch)
    runtime.entry.options["sg_boost"] = {"entity_id": "switch.sg_contact"}
    forbidden = {"action": "water_heater.set_temperature" if endpoint.startswith("water_heater") else "switch.turn_on",
                 "target": {"entity_id": endpoint}}
    bodies = {
        "direct": [forbidden],
        "choose": [{"choose": [{"conditions": [], "sequence": [forbidden]}]}],
        "if": [{"if": [], "then": [], "else": [forbidden]}],
        "repeat": [{"repeat": {"count": 2, "sequence": [forbidden]}}],
        "parallel": [{"parallel": [{"sequence": [forbidden]}]}],
        "sequence": [{"sequence": [forbidden]}],
        "nested": [{"action": "script.child"}],
    }
    install_scripts(hass, {"script.parent": bodies[branch], "script.child": [forbidden]})
    with pytest.raises(HomeAssistantError):
        authority.assert_allowed("script", "turn_on", "script.parent")
    assert actuator_calls(hass) == []

@pytest.mark.parametrize("step", [
    {"action": "{{ selected_action }}", "target": {"entity_id": "switch.load"}},
    {"action": "switch.turn_on", "target": {"entity_id": "{{ selected_entity }}"}},
    {"action": "switch.turn_on", "target": {"entity_id": "all"}},
    {"action": "switch.turn_on", "target": {"device_id": "any-device"}},
    {"action": "switch.turn_on", "target": {"area_id": "any-area"}},
    {"action": "switch.turn_on", "target": {"floor_id": "any-floor"}},
    {"action": "switch.turn_on", "target": {"label_id": "any-label"}},
    {"action": "automation.trigger", "target": {"entity_id": "automation.proxy"}},
    {"action": "scene.turn_on", "target": {"entity_id": "scene.proxy"}},
    {"action": "rest_command.proxy"}, {"action": "python_script.proxy"},
    {"event": "proxy_event"},
    {"action": "switch.turn_on", "target": {"entity_id": "switch.load"}, "event": "proxy_event"},
    {"choose": [], "event": "proxy_event"},
    {"action": "switch.turn_on", "data_template": {"entity_id": "{{ selected_entity }}"}},
    {"action": "switch.turn_on", "target": {"entity_id": "switch.load"}, "data": {"entity_id": "switch.load"}},
    {"parallel": [{"sequence": [], "action": "climate.set_hvac_mode",
                   "target": {"entity_id": "climate.hidden"}}]},
    {"parallel": [{"sequence": [], "service": "water_heater.set_temperature",
                   "data": {"entity_id": "water_heater.hidden", "temperature": 60}}]},
])
def test_unprovable_script_proxy_targets_are_quarantined_before_any_service(monkeypatch, step):
    runtime, hass, authority, _rows = authority_runtime(monkeypatch)
    install_scripts(hass, {"script.proxy": [step]})
    with pytest.raises(HomeAssistantError):
        authority.assert_allowed("script", "turn_on", "script.proxy")
    assert actuator_calls(hass) == []

def test_safe_script_and_battery_data_variables_remain_supported_without_target_templates(monkeypatch):
    runtime, hass, authority, _rows = authority_runtime(monkeypatch)
    install_scripts(hass, {"script.safe": [
        {"variables": {"power_w": "{{ signed_power_w }}"}},
        {"if": [], "then": [{"action": "number.set_value", "target": {"entity_id": "number.amps"},
                                "data": {"value": "{{ power_w }}"}}],
         "else": [{"action": "switch.turn_off", "data": {"entity_id": "switch.load"}}]},
    ]})
    variables = {"variables": {"signed_power_w": -1800}}
    payload = authority.assert_allowed("script", "turn_on", "script.safe", variables)
    assert payload == {"entity_id": "script.safe", **variables}
    variables["variables"]["signed_power_w"] = 100
    assert payload["variables"]["signed_power_w"] == -1800

def test_unknown_script_is_not_treated_as_a_safe_existing_permission(monkeypatch):
    _runtime, _hass, authority, _rows = authority_runtime(monkeypatch)
    with pytest.raises(HomeAssistantError, match="niet controleerbaar"):
        authority.assert_allowed("script", "turn_on", "script.unavailable")

def test_script_body_change_invalidates_previous_permission_immediately(monkeypatch):
    _runtime, hass, authority, _rows = authority_runtime(monkeypatch)
    scripts = {"script.safe": [{"action": "switch.turn_on", "target": {"entity_id": "switch.load"}}]}
    install_scripts(hass, scripts)
    assert authority.assert_allowed("script", "turn_on", "script.safe")["entity_id"] == "script.safe"
    scripts["script.safe"] = [{"action": "climate.set_hvac_mode",
                                "target": {"entity_id": "climate.native_zone_one"},
                                "data": {"hvac_mode": "auto"}}]
    with pytest.raises(HomeAssistantError):
        authority.assert_allowed("script", "turn_on", "script.safe")

def test_recursive_script_is_rejected_without_executing_it(monkeypatch):
    _runtime, hass, authority, _rows = authority_runtime(monkeypatch)
    install_scripts(hass, {"script.first": [{"action": "script.second"}],
                           "script.second": [{"action": "script.first"}]})
    with pytest.raises(HomeAssistantError, match="Recursieve"):
        authority.assert_allowed("script", "turn_on", "script.first")
    assert actuator_calls(hass) == []

@pytest.mark.asyncio
async def test_battery_direct_adapter_cannot_bypass_native_device_authority(monkeypatch):
    from test_battery_runtime import setup_battery
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    target = runtime.battery_fleet.configs["bat1"]["number_entity"]
    rows = {target: SimpleNamespace(entity_id=target, platform="aquarea", device_id="native-pump")}
    monkeypatch.setattr(er, "async_get", lambda _hass: SimpleNamespace(async_get=rows.get))
    sent = await runtime.battery_fleet.tick(grid_w=-1800, allow_command=True)
    assert sent is False
    assert actuator_calls(hass) == []
    assert "bat1" in runtime.battery_fleet.state.faults
    assert runtime.battery_fleet.state.pending is None

@pytest.mark.asyncio
async def test_battery_authority_rechecks_after_durable_intent_before_dispatch(monkeypatch):
    from test_battery_runtime import setup_battery
    runtime, hass = setup_battery(global_control=True, profile_control=True, exclusive=True)
    target = runtime.battery_fleet.configs["bat1"]["number_entity"]
    original_save = runtime.store.async_save

    async def change_sg_binding_after_save(data):
        await original_save(data)
        runtime.entry.options["sg_boost"] = {"entity_id": "switch.sg_contact"}
        rows = {target: SimpleNamespace(entity_id=target, platform="shelly", device_id="sg-device"),
                "switch.sg_contact": SimpleNamespace(entity_id="switch.sg_contact", platform="shelly", device_id="sg-device")}
        monkeypatch.setattr(er, "async_get", lambda _hass: SimpleNamespace(async_get=rows.get))

    runtime.store.async_save = change_sg_binding_after_save
    await runtime.battery_fleet.tick(grid_w=-1800, allow_command=True)
    assert actuator_calls(hass) == []
    assert "bat1" in runtime.battery_fleet.state.faults

@pytest.mark.asyncio
@pytest.mark.parametrize('target', ['switch.sg_contact', 'switch.native_heater', ['switch.load']])
async def test_invalid_imported_profile_is_local_and_does_not_block_healthy_sibling(monkeypatch, target):
    runtime, hass = build(settings={'settle_s': 0, 'filter_s': 0})
    healthy = {**runtime.entry.options['devices'][0], 'id': 'healthy',
               'name': 'Independent load', 'control_entity': 'switch.healthy'}
    runtime.entry.options['devices'][0]['control_entity'] = target
    runtime.entry.options['devices'].append(healthy)
    runtime.entry.options['sg_boost'] = {'entity_id': 'switch.sg_contact', 'enabled': False}
    hass.states.set('switch.healthy', 'off')
    hass.states.set('switch.sg_contact', 'off')
    hass.states.set('switch.native_heater', 'off')
    rows = {'switch.native_heater': SimpleNamespace(entity_id='switch.native_heater',
                                                    platform='aquarea', device_id='native-device')}
    monkeypatch.setattr(er, 'async_get', lambda _hass: SimpleNamespace(
        async_get=rows.get, async_get_entity_id=lambda *_args: None))
    runtime = SolarRuntime(hass, runtime.entry)
    runtime.mode = 'solar'
    runtime.device_modes = {'a': 'auto', 'healthy': 'auto'}
    await runtime.tick()
    assert runtime.mode == 'solar' and not runtime.problem.startswith('Interne fout')
    assert runtime.states['a'].fault and not runtime.states['a'].available
    assert 'a' not in runtime.faults and not runtime.restart_blocking
    assert runtime.pending and runtime.pending['id'] == 'healthy'
    assert actuator_calls(hass) == [('switch', 'turn_on', {'entity_id': 'switch.healthy'})]
