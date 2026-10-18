"""Current source links cannot disclose retained sources or query history."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
from types import SimpleNamespace as NS

import pytest

from test_consumer_history_api import api as history_api_doubles


@pytest.fixture
def source_api(history_api_doubles, monkeypatch):
    name = "custom_components.solar_pilot._test_source_history_permissions99"
    path = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot/source_history_api.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    assert module.vol.__name__ == history_api_doubles.vol.__name__
    return module


def forbidden(*_args, **_kwargs):
    raise AssertionError("A current-source catalogue must not read values, history, retained ACLs or controls")


def context(*, admin=False, allowed=()):
    configs = {"load": {"id": "load", "name": "Current load", "kind": "number",
        "control_entity": "switch.current_load", "power_entity": "sensor.current_load_power",
        "number_entity": "number.current_load_target", "unapproved_secret_entity": "sensor.secret_extra"}}
    archived = {"old": {"id": "old", "name": "Archived load", "kind": "switch",
                         "control_entity": "switch.archived_last_binding"}}
    # The archive may contain stale copies of current configs. The active
    # runtime binding, not proposed options or retained ACLs, is authoritative.
    history_configs = {**deepcopy(configs), **archived}
    history_configs["load"]["power_entity"] = "sensor.obsolete_copy"
    batteries = {"load": {"id": "load", "name": "Battery with same local ID",
        "soc_entity": "sensor.battery_soc", "power_entity": "sensor.battery_power",
        "number_entity": "number.battery_target"}}
    wallbox = {"name": "Configured Wallbox", "power_entity": "sensor.ev_power",
               "status_entity": "sensor.ev_status", "mode_entity": "select.ev_mode"}
    runtime = NS(_closed=False, configs=configs,
        consumer_history=NS(configs=history_configs, access_sources=forbidden, detail=forbidden),
        battery_fleet=NS(configs=batteries), wallbox_settings=wallbox,
        analysis=NS(export=forbidden), heatpump_history=NS(export=forbidden))
    runtime.panasonic = NS(settings={"tank_temperature_entity": "sensor.tank_temperature",
        "tank_target_entity": "water_heater.configured_tank", "zone_entities": [],
        "activity_entity": "switch.unapproved_heatpump_activity", "power_entity": "sensor.unapproved_heatpump_power"},
        native_program=NS(display_sources=forbidden, is_display_zone=forbidden), overview=forbidden)
    entry = NS(entry_id="entry", domain="solar_pilot", state="loaded", runtime_data=runtime,
        options={"devices": [{"id": "load", "power_entity": "sensor.unapproved_pending_binding"}],
                 "batteries": [{"id": "load", "soc_entity": "sensor.pending_battery"}]})
    runtime.entry = entry
    entries = {"entry": entry}
    hass = NS(config_entries=NS(async_get_entry=entries.get), data={}, registered=[],
              states=NS(get=forbidden), services=NS(async_call=forbidden))
    checked = []
    allow = set(allowed)
    def check(entity, policy):
        assert policy == "read"
        checked.append(entity)
        return entity in allow
    user = NS(is_admin=admin, permissions=NS(check_entity=check))
    results, errors = [], []
    connection = NS(user=user, send_result=lambda _id, data: results.append(data),
                    send_error=lambda _id, code, _message: errors.append(code))
    return NS(runtime=runtime, entry=entry, entries=entries, hass=hass, connection=connection,
              out=results, errors=errors, checked=checked)


def request(api, env, kind="consumer", item_id="load", source=None, **extra):
    message = {"id": 1, "type": api.COMMAND, "config_entry_id": "entry", "kind": kind}
    if kind not in ("wallbox", "heatpump"):
        message["item_id"] = item_id
    if kind == "heatpump":
        message["source"] = source if source is not None else "configured"
    elif source is not None:
        message["source"] = source
    message.update(extra)
    api.websocket_source_history(env.hass, env.connection, message)


def returned_entities(env):
    return {row["entity_id"] for row in env.out[0]["sources"]}


def test_current_read_permissions_allow_source_links_without_opening_private_old_device_history(source_api):
    env = context(allowed={"sensor.current_load_power"})
    request(source_api, env)
    assert not env.errors and returned_entities(env) == {"sensor.current_load_power"}
    assert set(env.checked) == {"sensor.current_load_power", "switch.current_load", "number.current_load_target"}
    payload = env.out[0]
    assert payload["read_only"] is True and payload["scope"] == "current_configured_sources"
    assert set(payload) == {"schema", "read_only", "scope", "kind", "name", "sources", "note", "item_id"}
    assert all(set(row) == {"role", "label", "entity_id"} for row in payload["sources"])


@pytest.mark.parametrize("kind,expected", [
    ("consumer", {"sensor.current_load_power", "switch.current_load", "number.current_load_target"}),
    ("battery", {"sensor.battery_soc", "sensor.battery_power", "number.battery_target"}),
    ("wallbox", {"sensor.ev_power", "sensor.ev_status", "select.ev_mode"}),
])
def test_exact_kind_namespace_uses_current_approved_runtime_sources_only(source_api, kind, expected):
    env = context(admin=True)
    before = deepcopy((env.runtime.configs, env.runtime.consumer_history.configs,
                       env.runtime.battery_fleet.configs, env.runtime.wallbox_settings, env.entry.options))
    request(source_api, env, kind=kind)
    assert not env.errors and returned_entities(env) == expected
    assert not env.checked  # Administrator, without treating an ID as a query.
    assert (env.runtime.configs, env.runtime.consumer_history.configs,
            env.runtime.battery_fleet.configs, env.runtime.wallbox_settings, env.entry.options) == before


def test_archived_consumer_uses_last_approved_config_not_private_retained_sources(source_api):
    env = context(allowed={"switch.archived_last_binding"})
    request(source_api, env, item_id="old")
    assert not env.errors and returned_entities(env) == {"switch.archived_last_binding"}
    assert env.out[0]["item_id"] == "old" and "laatst bewaarde" in env.out[0]["note"]
    assert env.checked == ["switch.archived_last_binding"]


@pytest.mark.parametrize("kind,allowed", [("consumer", "number.current_load_target"),
    ("battery", "sensor.battery_soc"), ("wallbox", "sensor.ev_status")])
def test_nonadmin_only_receives_each_individually_readable_current_source(source_api, kind, allowed):
    env = context(allowed={allowed})
    request(source_api, env, kind=kind)
    assert not env.errors and returned_entities(env) == {allowed}


@pytest.mark.parametrize("kind", ["consumer", "battery", "wallbox"])
def test_no_permitted_sources_returns_no_name_or_entity_catalogue(source_api, kind):
    env = context()
    request(source_api, env, kind=kind)
    assert env.out == [] and env.errors == ["unauthorized"]


def test_permission_lookup_failure_is_closed_per_source(source_api):
    env = context()
    def check(entity, _policy):
        if entity == "sensor.current_load_power":
            return True
        raise RuntimeError("permission provider unavailable")
    env.connection.user.permissions.check_entity = check
    request(source_api, env)
    assert not env.errors and returned_entities(env) == {"sensor.current_load_power"}


@pytest.mark.parametrize("extra", [{"entity_id": "sensor.unrelated"}, {"entities": ["sensor.unrelated"]},
    {"source": "sensor.unrelated"}, {"date": "2026-10-18"}, {"export": True}])
def test_callers_cannot_inject_entity_queries_or_turn_the_catalogue_into_a_history_export(source_api, extra):
    env = context(admin=True)
    request(source_api, env, **extra)
    assert env.out == [] and env.errors == ["invalid_format"] and not env.checked


@pytest.mark.parametrize("kind", ["wallbox", "heatpump"])
def test_non_item_catalogue_cannot_accept_an_item_id_from_another_subject_namespace(source_api, kind):
    env = context(admin=True)
    message = {"id": 1, "type": source_api.COMMAND, "config_entry_id": "entry", "kind": kind, "item_id": "load"}
    if kind == "heatpump": message["source"] = "configured"
    source_api.websocket_source_history(env.hass, env.connection, message)
    assert not env.out and env.errors == ["invalid_format"]


@pytest.mark.parametrize("kind,item_id,error", [("unknown", "load", "invalid_format"),
    ("consumer", "../load", "not_found"), ("battery", "old", "not_found"),
    ("consumer", "", "invalid_format"), ("consumer", [], "invalid_format")])
def test_unknown_or_malformed_subjects_never_fall_back_to_another_catalogue(source_api, kind, item_id, error):
    env = context(admin=True)
    request(source_api, env, kind=kind, item_id=item_id)
    assert env.out == [] and env.errors == [error]


@pytest.mark.parametrize("entity", ["sensor.bad?entity_id=secret", "sensor.a,sensor.secret", "sensor.a\n",
                                  "sensor.a/../../secret", "sensor.UPPER", "", ["sensor.secret"], True])
def test_malformed_configured_entity_identifiers_are_not_native_history_links(source_api, entity):
    env = context(admin=True)
    env.runtime.configs["load"] = {"name": "Malformed source", "power_entity": entity,
                                   "unapproved_secret_entity": "sensor.secret"}
    request(source_api, env)
    assert not env.errors and returned_entities(env) == set()


@pytest.mark.parametrize("change", ["anonymous", "closed", "wrong_domain", "unloaded", "wrong_runtime_owner", "missing_entry"])
def test_authentication_and_exact_loaded_entry_binding_are_required(source_api, change):
    env = context(admin=True)
    if change == "anonymous": env.connection.user = None
    elif change == "closed": env.runtime._closed = True
    elif change == "wrong_domain": env.entry.domain = "another_integration"
    elif change == "unloaded": env.entry.state = "not_loaded"
    elif change == "wrong_runtime_owner": env.runtime.entry = NS(entry_id="entry")
    else: env.entries.clear()
    request(source_api, env)
    assert not env.out and env.errors == ["unauthorized" if change == "anonymous" else "not_loaded"]


@pytest.mark.parametrize("change", ["rebind", "reload", "closed"])
def test_a_permission_callback_cannot_publish_a_catalogue_after_its_source_or_runtime_changes(source_api, change):
    env = context()
    def check(_entity, _policy):
        if change == "rebind": env.runtime.configs["load"]["power_entity"] = "sensor.rebound"
        elif change == "reload": env.entries["entry"] = NS(**vars(env.entry))
        else: env.runtime._closed = True
        return True
    env.connection.user.permissions.check_entity = check
    request(source_api, env)
    assert not env.out and env.errors == ["sources_changed" if change == "rebind" else "not_loaded"]


def test_registration_is_idempotent_and_the_api_exposes_no_command_handler(source_api):
    env = context(admin=True)
    source_api.async_register_source_history_api(env.hass)
    source_api.async_register_source_history_api(env.hass)
    assert env.hass.registered == [source_api.websocket_source_history]


def test_configured_heatpump_temperature_is_filtered_separately_from_its_target(source_api):
    env = context(allowed={"sensor.tank_temperature"})
    request(source_api, env, kind="heatpump")
    assert not env.errors and returned_entities(env) == {"sensor.tank_temperature"}
    assert set(env.checked) == {"sensor.tank_temperature", "water_heater.configured_tank"}
    assert env.out[0]["kind"] == "heatpump" and "item_id" not in env.out[0]
    assert {row["role"] for row in env.out[0]["sources"]} == {"tank_temperature_entity"}


def test_heatpump_catalogue_has_no_authority_to_list_power_sg_actuators_or_unapproved_entities(source_api):
    env = context(admin=True)
    env.runtime.panasonic.settings.update(sg_status_entity="binary_sensor.secret_sg",
        entity_id="switch.secret_contact", unknown_temperature_entity="sensor.secret_temperature")
    request(source_api, env, kind="heatpump")
    assert not env.errors and returned_entities(env) == {"sensor.tank_temperature", "water_heater.configured_tank"}
    assert {row["role"] for row in env.out[0]["sources"]} == {"tank_temperature_entity", "tank_target_entity"}


@pytest.mark.parametrize("source", [None, "", "sensor.unrelated", "display_zone", True])
def test_heatpump_source_route_is_closed_and_required(source_api, source):
    env = context(admin=True)
    message = {"id": 1, "type": source_api.COMMAND, "config_entry_id": "entry", "kind": "heatpump"}
    if source is not None: message["source"] = source
    source_api.websocket_source_history(env.hass, env.connection, message)
    assert not env.out and env.errors == ["invalid_format"]


def test_display_tank_and_configured_temperature_routes_keep_their_distinct_source_bindings(source_api):
    env = context(admin=True)
    env.runtime.panasonic.native_program = NS(display_sources=lambda _anchors: {"tank_entity": "water_heater.native_tank"},
                                              is_display_zone=lambda _entity: False)
    request(source_api, env, kind="heatpump", source="display_tank")
    assert not env.errors
    assert [(row["role"], row["entity_id"]) for row in env.out[0]["sources"]] == [
        ("tank_temperature_entity", "water_heater.configured_tank"),
        ("tank_target_entity", "water_heater.configured_tank")]
    env.out.clear()
    request(source_api, env, kind="heatpump", source="configured")
    assert returned_entities(env) == {"sensor.tank_temperature", "water_heater.configured_tank"}


def test_configured_room_zone_is_not_mislabeled_as_the_discovered_tank(source_api):
    env = context(allowed={"water_heater.native_tank"})
    env.runtime.panasonic.settings["tank_target_entity"] = "climate.room_zone"
    env.runtime.panasonic.settings["zone_entities"] = ["climate.room_zone"]
    anchors_seen = []
    def discover(anchors):
        anchors_seen.append(anchors)
        return {"tank_entity": "water_heater.native_tank", "power_entity": "sensor.secret"}
    env.runtime.panasonic.native_program = NS(display_sources=discover, is_display_zone=lambda entity: entity == "climate.room_zone")
    request(source_api, env, kind="heatpump", source="display_tank")
    assert not env.errors and returned_entities(env) == {"water_heater.native_tank"}
    assert all("climate.room_zone" in anchors for anchors in anchors_seen)
    assert len(env.out[0]["sources"]) == 2  # Attribute roles on one entity remain explicit.


def test_automatic_tank_source_rebinding_during_permissions_is_rejected(source_api):
    env = context()
    env.runtime.panasonic.settings["tank_target_entity"] = ""
    current = ["water_heater.first_tank"]
    env.runtime.panasonic.native_program = NS(display_sources=lambda _anchors: {"tank_entity": current[0]},
                                              is_display_zone=lambda _entity: False)
    def check(_entity, _policy):
        current[0] = "water_heater.other_tank"
        return True
    env.connection.user.permissions.check_entity = check
    request(source_api, env, kind="heatpump", source="display_tank")
    assert not env.out and env.errors == ["sources_changed"]


def test_ambiguous_display_tank_discovery_does_not_pick_an_entity_from_other_roles(source_api):
    env = context(admin=True)
    env.runtime.panasonic.settings["tank_target_entity"] = ""
    env.runtime.panasonic.native_program = NS(display_sources=lambda _anchors: {
        "tank_entity": "", "zone_entities": ["climate.unrelated_room"], "direction_entity": "sensor.unrelated_route"},
        is_display_zone=lambda _entity: False)
    request(source_api, env, kind="heatpump", source="display_tank")
    assert not env.errors and returned_entities(env) == set()
