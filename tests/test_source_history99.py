"""Current source catalogues are scoped links, never invented historical data."""
from copy import deepcopy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import sys

import pytest

from test_consumer_history_api import api as history_api, context
from custom_components.solar_pilot.consumer_history import ConsumerHistory


@pytest.fixture
def api(history_api, monkeypatch):
    name = "custom_components.solar_pilot._test_source_history99"
    path = Path(__file__).resolve().parents[1]/"custom_components/solar_pilot/source_history_api.py"
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    assert module.vol.__name__ == history_api.vol.__name__
    assert module.websocket_source_history.test_schema == {
        "type": module.COMMAND, "config_entry_id": str, "kind": str, "item_id": str, "source": str}
    return module


def configured(*, admin=True):
    runtime, hass, connection, results, errors = context(admin=admin)
    runtime.configs["a"].update(name="Fictional consumer", power_entity="sensor.fictional_power")
    runtime.battery_fleet.configs["battery-a"] = {
        "name": "Fictional battery", "soc_entity": "sensor.fictional_soc", "power_entity": "sensor.fictional_battery_w",
        "number_entity": "number.fictional_battery_target", "charge_script": "script.fictional_charge",
        "discharge_script": "script.fictional_discharge", "idle_script": "script.fictional_idle"}
    runtime.wallbox_settings.update(name="Fictional Wallbox", power_entity="sensor.fictional_ev_w",
        status_entity="sensor.fictional_ev_status", session_mode_entity="sensor.fictional_ev_session")
    return runtime, hass, connection, results, errors


def query(api, hass, connection, kind="consumer", item="a", **extra):
    message = {"id": 1, "type": api.COMMAND, "config_entry_id": "test", "kind": kind}
    if kind != "wallbox":
        message["item_id"] = item
    message.update(extra)
    api.websocket_source_history(hass, connection, message)


@pytest.mark.parametrize("kind,item", [("consumer", "a"), ("battery", "battery-a"), ("wallbox", None)])
def test_source_links_only_and_no_runtime_or_control_mutations(api, kind, item):
    runtime, hass, connection, results, errors = configured()
    before = deepcopy((runtime.entry.options, runtime._snapshot(), hass.services.calls))
    query(api, hass, connection, kind, item)
    assert not errors and results[0]["schema"] == 1 and results[0]["read_only"] is True
    assert results[0]["scope"] == "current_configured_sources" and results[0]["kind"] == kind
    assert results[0]["sources"]
    assert all(set(row) == {"role", "label", "entity_id"} for row in results[0]["sources"])
    assert ("item_id" in results[0]) is (kind != "wallbox")
    assert (runtime.entry.options, runtime._snapshot(), hass.services.calls) == before


def test_permission_filter_is_per_current_source_not_a_historical_device_permission(api):
    runtime, hass, connection, results, errors = configured(admin=False)
    connection.user.permissions.check_entity = lambda entity, policy: entity == "sensor.fictional_power"
    runtime.consumer_history.access_sources = lambda _item: (_ for _ in ()).throw(AssertionError("No retained ACL lookup"))
    query(api, hass, connection)
    assert not errors and [row["entity_id"] for row in results[0]["sources"]] == ["sensor.fictional_power"]
    assert "access_sources" not in json.dumps(results)


def test_latest_archived_config_sources_are_separate_from_old_private_source_ids(api):
    runtime, hass, connection, results, errors = configured(admin=False)
    runtime.consumer_history.configs["archived"] = {"name": "Fictional archive", "power_entity": "sensor.fictional_latest"}
    runtime.consumer_history.access_sources = lambda _item: ({"sensor.fictional_private_old"}, False)
    connection.user.permissions.check_entity = lambda entity, policy: entity == "sensor.fictional_latest"
    query(api, hass, connection, item="archived")
    assert not errors and results[0]["sources"][0]["entity_id"] == "sensor.fictional_latest"
    assert "laatst bewaarde" in results[0]["note"]
    assert "fictional_private_old" not in json.dumps(results)


def test_permission_lookup_reloading_entry_discards_the_pre_reload_catalogue(api):
    runtime, hass, connection, results, errors = configured(admin=False)
    def allowed(entity, policy):
        runtime.entry.runtime_data = SimpleNamespace(_closed=False)
        return True
    connection.user.permissions.check_entity = allowed
    query(api, hass, connection)
    assert not results and errors == ["not_loaded"]


def test_permission_lookup_rebinding_sources_discards_the_old_catalogue(api):
    runtime, hass, connection, results, errors = configured(admin=False)
    def allowed(entity, policy):
        runtime.configs["a"]["power_entity"] = "sensor.fictional_replacement"
        return True
    connection.user.permissions.check_entity = allowed
    query(api, hass, connection)
    assert not results and errors == ["sources_changed"]


@pytest.mark.parametrize("extra", [{"entity_id": "sensor.fictional_private"}, {"kind": "unknown"},
    {"kind": True}, {"item_id": True}, {"item_id": ""}, {"config_entry_id": None},
    {"type": "solar_pilot/analysis_export"}, {"action": "apply"}])
def test_catalogue_does_not_accept_generic_entity_queries_or_mutations(api, extra):
    _runtime, hass, connection, results, errors = configured()
    query(api, hass, connection, **extra)
    assert not results and errors == ["invalid_format"]


def test_wallbox_request_must_omit_item_id(api):
    _runtime, hass, connection, results, errors = configured()
    query(api, hass, connection, "wallbox", item_id="a")
    assert not results and errors == ["invalid_format"]


def test_registration_is_idempotent(api):
    _runtime, hass, _connection, _results, _errors = configured()
    api.async_register_source_history_api(hass)
    api.async_register_source_history_api(hass)
    assert hass.registered == [api.websocket_source_history]


@pytest.mark.parametrize("day,seconds", [("2026-03-29", 23*3600), ("2026-10-25", 25*3600), ("2026-10-26", 24*3600)])
def test_common_consumer_day_bounds_use_actual_timezone_offsets(day, seconds):
    model = ConsumerHistory("Europe/Brussels")
    when = datetime.fromisoformat(day+"T22:00:00+00:00")
    cfg = {"name": "Fictional consumer", "kind": "switch", "control_entity": "switch.fictional"}
    model.observe("a", cfg, True, when)
    result = model.detail("a", day, when)
    assert result["day_end"]-result["day_start"] == result["day_seconds"] == seconds
    assert datetime.fromtimestamp(result["day_start"], timezone.utc).astimezone(model.zone).date().isoformat() == day
