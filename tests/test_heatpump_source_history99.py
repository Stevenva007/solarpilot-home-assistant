"""Tank source links follow the displayed route without reading tank values."""
from copy import deepcopy
from types import SimpleNamespace as NS

import pytest

from test_source_history99 import api, configured, history_api


def setup(*, admin=True):
    runtime, hass, connection, results, errors = configured(admin=admin)
    anchors = []
    sources = {"tank_entity": "water_heater.fictional_native_tank"}
    settings = {"tank_temperature_entity": "sensor.fictional_tank_temperature",
                "tank_target_entity": "number.fictional_tank_target",
                "activity_entity": "sensor.fictional_task", "zone_entities": ["climate.fictional_zone"]}
    def discover(values):
        anchors.append(values)
        return dict(sources)
    runtime.panasonic = NS(settings=settings, native_program=NS(display_sources=discover, is_display_zone=lambda _eid: False))
    runtime.panasonic.overview = lambda: pytest.fail("The catalogue must not read live values or diagnostics")
    hass.states.get = lambda _eid: pytest.fail("The catalogue must not read source values")
    return runtime, hass, connection, results, errors, sources, anchors


def query(api, hass, connection, source="configured", **extra):
    api.websocket_source_history(hass, connection, {"id": 1, "type": api.COMMAND,
        "config_entry_id": "test", "kind": "heatpump", "source": source, **extra})


@pytest.mark.parametrize("source", ["configured", "display_tank"])
def test_both_tank_roles_follow_the_requested_current_display_route(api, source):
    runtime, hass, connection, out, errors, sources, anchors = setup()
    before = deepcopy(runtime.panasonic.settings)
    query(api, hass, connection, source)
    assert not errors and out[0]["read_only"] is True and "item_id" not in out[0]
    rows = {row["role"]: row["entity_id"] for row in out[0]["sources"]}
    expected = {role: sources["tank_entity"] if source == "display_tank" else before[role]
                for role in ("tank_temperature_entity", "tank_target_entity")}
    assert rows == expected and runtime.panasonic.settings == before
    if source == "display_tank":
        assert len(out[0]["sources"]) == 2  # Both roles may point to one actual HA entity.
        assert anchors == [[before["tank_target_entity"], before["tank_temperature_entity"],
                            before["activity_entity"], *before["zone_entities"]]]*2
    else:
        assert not anchors


def test_nonadmin_gets_only_the_readable_tank_role(api):
    _runtime, hass, connection, out, errors, _sources, _anchors = setup(admin=False)
    connection.user.permissions.check_entity = lambda entity, policy: entity == "number.fictional_tank_target"
    query(api, hass, connection)
    assert not errors and [row["role"] for row in out[0]["sources"]] == ["tank_target_entity"]


@pytest.mark.parametrize("extra", [{"item_id": "heatpump"}, {"source": "calculated_sg_goal"},
    {"source": True}, {"source": None}, {"entity_id": "sensor.fictional_private"}])
def test_tank_catalogue_rejects_arbitrary_sources_or_selected_entities(api, extra):
    _runtime, hass, connection, out, errors, _sources, _anchors = setup()
    query(api, hass, connection, **extra)
    assert not out and errors == ["invalid_format"]


def test_other_kinds_reject_the_tank_route_field(api):
    _runtime, hass, connection, out, errors, _sources, _anchors = setup()
    query(api, hass, connection, kind="wallbox")
    assert not out and errors == ["invalid_format"]


def test_display_registry_rebinding_during_read_permission_discards_the_old_route(api):
    _runtime, hass, connection, out, errors, sources, _anchors = setup(admin=False)
    def allowed(_entity, _policy):
        sources["tank_entity"] = "water_heater.fictional_replacement"
        return True
    connection.user.permissions.check_entity = allowed
    query(api, hass, connection, "display_tank")
    assert not out and errors == ["sources_changed"]


def test_native_registry_discovery_and_monitor_metadata_share_the_actual_source(api, monkeypatch):
    from test_panasonic_source_quality98 import monitored
    env, monitor = monitored(monkeypatch)
    monitor.update_config({**monitor.settings, "tank_target_entity": ""})
    runtime, hass = monitor.runtime, monitor.runtime.hass
    runtime._closed = False
    runtime.entry = NS(domain="solar_pilot", entry_id="test", state="loaded", runtime_data=runtime)
    get_entry = hass.config_entries.async_get_entry
    hass.config_entries.async_get_entry = lambda eid: runtime.entry if eid == "test" else get_entry(eid)
    out, errors = [], []
    connection = NS(user=NS(is_admin=True), send_result=lambda _id, result: out.append(result),
                    send_error=lambda _id, code, _message: errors.append(code))
    query(api, hass, connection, "display_tank")
    assert not errors and {row["entity_id"] for row in out[0]["sources"]} == {env.sources["tank_entity"]}
    env.poll(quality=env.quality.LIVE)
    view = monitor.overview()
    assert view["display_tank"]["entity_id"] == env.sources["tank_entity"]
    assert view["temperature_entity"] == monitor.settings["tank_temperature_entity"]
    assert view["target_entity"] == monitor.settings["tank_target_entity"]
    assert not hass.services.calls and env.coordinator.api_calls == []
