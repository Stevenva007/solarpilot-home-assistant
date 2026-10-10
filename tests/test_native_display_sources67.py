"""Registry-bound automatic presentation sources never create control proof."""
from copy import deepcopy
from datetime import datetime, timezone
import sys
from types import ModuleType, SimpleNamespace as NS

import pytest
from homeassistant import helpers
from homeassistant.helpers import entity_registry as er

from test_native_program56 import native_program, setup
from test_runtime import Services, States


def display_setup(monkeypatch, *, stale_s=120):
    helper, coordinator, rows, entries, clock = setup(monkeypatch, stale_s=stale_s)
    rows.clear()
    helper.runtime.hass.states = States()
    helper.runtime.hass.services = Services(helper.runtime.hass.states)
    devices = {}
    registry = NS(entities=rows, async_get=rows.get)
    monkeypatch.setattr(er, "async_get", lambda _hass: registry)
    monkeypatch.setattr(er, "async_entries_for_config_entry", lambda _registry, eid: [
        row for row in rows.values() if row.config_entry_id == eid], raising=False)
    dr = ModuleType("homeassistant.helpers.device_registry")
    dr.async_get = lambda _hass: NS(devices=devices, async_get=devices.get)
    monkeypatch.setitem(sys.modules, dr.__name__, dr)
    monkeypatch.setattr(helpers, "device_registry", dr, raising=False)
    monkeypatch.setattr(native_program.time, "time", lambda: clock[0])
    helper.runtime.hass.config_entries.async_entries = lambda domain=None: [
        entry for entry in entries.values() if domain is None or entry.domain == domain]

    def state(entity_id, value, attrs=None, *, stamp=990):
        helper.runtime.hass.states.set(entity_id, value, attrs)
        obj = helper.runtime.hass.states.get(entity_id)
        obj.entity_id = entity_id
        obj.last_updated = obj.last_reported = datetime.fromtimestamp(stamp, timezone.utc)
        return obj

    def group(device_id="pump", entry_id="native"):
        if entry_id not in entries:
            entries[entry_id] = NS(domain="aquarea", runtime_data=None)
        dr_id = f"registry_{device_id}"
        devices[dr_id] = NS(id=dr_id, identifiers={("aquarea", device_id)},
                            config_entries={entry_id}, disabled_by=None)
        sources = {
            "tank_entity": f"water_heater.{device_id}_tank",
            "zone_entities": [f"climate.{device_id}_zone_1", f"climate.{device_id}_zone_2"],
            "direction_entity": f"sensor.{device_id}_direction",
            "defrost_entity": f"binary_sensor.{device_id}_defrost",
        }
        definitions = [(sources["tank_entity"], f"{device_id}_tank", "heating", {"operation_mode": "heating"}),
                       (sources["zone_entities"][0], f"{device_id}_climate_1", "auto", {"hvac_action": "off"}),
                       (sources["zone_entities"][1], f"{device_id}_climate_2", "auto", {"hvac_action": "off"}),
                       (sources["direction_entity"], f"{device_id}_direction", "WATER", {}),
                       (sources["defrost_entity"], f"{device_id}_defrost", "off", {})]
        for eid, uid, value, attrs in definitions:
            rows[eid] = NS(entity_id=eid, platform="aquarea", config_entry_id=entry_id,
                           unique_id=uid, device_id=dr_id, disabled_by=None)
            state(eid, value, attrs)
        return sources

    sources = group()
    return NS(helper=helper, coordinator=coordinator, rows=rows, entries=entries,
              devices=devices, clock=clock, sources=sources, state=state, group=group)


def assert_sources(result, expected):
    assert result["automatic"] is True
    for key in ("tank_entity", "direction_entity", "defrost_entity"):
        assert result[key] == expected[key]
    assert set(result["zone_entities"]) == set(expected["zone_entities"])


def assert_empty(result):
    assert result["automatic"] is True
    assert result["tank_entity"] == result["direction_entity"] == result["defrost_entity"] == ""
    assert result["zone_entities"] == []


def assert_no_tank_context(result):
    assert result["function"] is None
    assert result["source"] == result["kind"] == "none"
    assert result["observed_at"] is None


def test_single_exact_aquarea_device_is_discovered_without_bindings_or_poll(monkeypatch):
    env = display_setup(monkeypatch)
    env.entries["native"].runtime_data = None
    assert_sources(env.helper.display_sources(), env.sources)
    assert env.coordinator.listeners == [] and env.coordinator.api_calls == []
    assert env.helper.runtime.hass.services.calls == []


@pytest.mark.parametrize("owner", ["native", "other", None])
def test_modern_singular_device_owner_never_reads_deprecated_config_entries(monkeypatch, owner):
    env = display_setup(monkeypatch)

    class ModernDevice:
        identifiers = {("aquarea", "pump")}
        config_entry_id = owner

        @property
        def config_entries(self):
            raise AssertionError("Modern device must not read deprecated config_entries")

    env.devices["registry_pump"] = ModernDevice()
    sources = env.helper.display_sources()
    context = env.helper.read_tank_context(env.sources["tank_entity"])
    if owner == "native":
        assert_sources(sources, env.sources)
        assert context["function"] == "tapwater_heating"
    else:
        assert_empty(sources)
        assert_no_tank_context(context)


def test_sources_are_detached_and_do_not_mutate_settings_or_registry(monkeypatch):
    env = display_setup(monkeypatch)
    settings = deepcopy(env.helper.runtime.panasonic.settings)
    identities = {eid: dict(vars(row)) for eid, row in env.rows.items()}
    result = env.helper.display_sources()
    result["zone_entities"].append("climate.unrelated")
    assert_sources(env.helper.display_sources(), env.sources)
    assert env.helper.runtime.panasonic.settings == settings
    assert {eid: dict(vars(row)) for eid, row in env.rows.items()} == identities
    assert env.coordinator.listeners == [] and env.coordinator.api_calls == []
    assert env.helper.runtime.hass.services.calls == []


@pytest.mark.parametrize("same_entry", [False, True])
def test_multiple_aquarea_devices_without_anchor_do_not_guess(monkeypatch, same_entry):
    env = display_setup(monkeypatch)
    env.group("other", "native" if same_entry else "native_other")
    assert_empty(env.helper.display_sources())


@pytest.mark.parametrize("anchor_key", ["tank_entity", "zone_entities", "direction_entity", "defrost_entity"])
def test_exact_bound_anchor_selects_its_device_from_multiple_candidates(monkeypatch, anchor_key):
    env = display_setup(monkeypatch)
    other = env.group("other", "native_other")
    anchors = other[anchor_key]
    anchors = tuple(anchors) if isinstance(anchors, list) else (anchors,)
    assert_sources(env.helper.display_sources(anchors=anchors), other)


def test_consistent_anchors_select_one_group_but_cross_device_anchors_do_not(monkeypatch):
    env = display_setup(monkeypatch)
    other = env.group("other", "native_other")
    assert_sources(env.helper.display_sources(anchors=(env.sources["tank_entity"],
        env.sources["zone_entities"][1])), env.sources)
    assert_empty(env.helper.display_sources(anchors=(env.sources["tank_entity"],
        other["zone_entities"][0])))


@pytest.mark.parametrize("case", ["platform", "domain", "missing_entry", "missing_device",
    "wrong_identifier", "wrong_identifier_domain", "device_entry_mismatch"])
def test_registry_device_entry_identity_cannot_be_inferred_from_entity_names(monkeypatch, case):
    env = display_setup(monkeypatch)
    device = env.devices["registry_pump"]
    if case == "platform":
        for row in env.rows.values():
            row.platform = "unrelated"
    elif case == "domain":
        env.entries["native"].domain = "unrelated"
    elif case == "missing_entry":
        env.entries.pop("native")
    elif case == "missing_device":
        env.devices.clear()
    elif case == "wrong_identifier":
        device.identifiers = {("aquarea", "other")}
    elif case == "wrong_identifier_domain":
        device.identifiers = {("unrelated", "pump")}
    else:
        device.config_entries = {"native_other"}
    assert_empty(env.helper.display_sources())
    assert_no_tank_context(env.helper.read_tank_context(env.sources["tank_entity"]))


@pytest.mark.parametrize("suffix", ["_extra", "_climate_2", "_direction"])
def test_tank_unique_id_has_to_match_exact_role(monkeypatch, suffix):
    env = display_setup(monkeypatch)
    env.rows[env.sources["tank_entity"]].unique_id = "pump_tank" + suffix
    assert env.helper.display_sources()["tank_entity"] == ""
    assert_no_tank_context(env.helper.read_tank_context(env.sources["tank_entity"]))


@pytest.mark.parametrize("suffix", ["x", "_extra", "", "one"])
def test_zone_unique_id_requires_exact_numeric_zone_suffix(monkeypatch, suffix):
    env = display_setup(monkeypatch)
    zone = env.sources["zone_entities"][0]
    env.rows[zone].unique_id = "pump_climate_" + suffix
    assert env.helper.display_sources()["zone_entities"] == [env.sources["zone_entities"][1]]


@pytest.mark.parametrize("role", ["tank_entity", "direction_entity", "defrost_entity", "zone_entities"])
def test_disabled_registry_entities_are_not_discovered(monkeypatch, role):
    env = display_setup(monkeypatch)
    eid = env.sources[role][0] if role == "zone_entities" else env.sources[role]
    env.rows[eid].disabled_by = "user"
    result = env.helper.display_sources()
    if role == "zone_entities":
        assert eid not in result[role]
    else:
        assert result[role] == ""
    if role == "tank_entity":
        assert_no_tank_context(env.helper.read_tank_context(eid))


@pytest.mark.parametrize("value", ["unknown", "unavailable"])
def test_discovery_keeps_native_identity_while_current_tank_reader_refuses_unavailability(monkeypatch, value):
    env = display_setup(monkeypatch)
    env.state(env.sources["tank_entity"], value, {"operation_mode": "heating"})
    assert_sources(env.helper.display_sources(), env.sources)
    assert_no_tank_context(env.helper.read_tank_context(env.sources["tank_entity"]))


@pytest.mark.parametrize("value", ["heating", "heat_pump"])
def test_exact_native_tank_route_is_qualified_context_without_coordinator_or_poll(monkeypatch, value):
    env = display_setup(monkeypatch)
    env.entries["native"].runtime_data = None
    env.state(env.sources["tank_entity"], value, {"operation_mode": "heating"}, stamp=980)
    before = deepcopy(env.helper.runtime.panasonic.settings)
    result = env.helper.read_tank_context(env.sources["tank_entity"])
    assert result["function"] == "tapwater_heating"
    assert result["source"] == "aquarea_entity" and result["kind"] == "tank_route"
    assert result["observed_at"] == 980 and result["stale_s"] == 120
    assert isinstance(result["label"], str) and result["label"]
    assert isinstance(result["note"], str) and result["note"]
    assert env.helper.runtime.panasonic.settings == before
    assert env.coordinator.listeners == [] and env.coordinator.api_calls == []
    assert env.helper.runtime.hass.services.calls == []


@pytest.mark.parametrize("value,mode", [("heating", "idle"), ("idle", "heating"),
    ("off", "heating"), ("on", "heating"), ("auto", "heating"),
    ("heating", None), ("heat_pump", "heat_pump"), ("", "heating")])
def test_selected_or_inconsistent_native_tank_mode_is_not_current_task(monkeypatch, value, mode):
    env = display_setup(monkeypatch)
    attrs = {"operation_mode": mode} if mode is not None else {}
    env.state(env.sources["tank_entity"], value, attrs)
    assert_no_tank_context(env.helper.read_tank_context(env.sources["tank_entity"]))


@pytest.mark.parametrize("flag", ["restored", "estimated", "is_estimated"])
def test_restored_or_estimated_native_entity_is_not_route_context(monkeypatch, flag):
    env = display_setup(monkeypatch)
    env.state(env.sources["tank_entity"], "heating", {"operation_mode": "heating", flag: True})
    assert_no_tank_context(env.helper.read_tank_context(env.sources["tank_entity"]))


@pytest.mark.parametrize("stamp", [879, 1006, float("nan")])
def test_native_tank_context_has_bounded_actual_report_freshness(monkeypatch, stamp):
    env = display_setup(monkeypatch)
    obj = env.state(env.sources["tank_entity"], "heating", {"operation_mode": "heating"})
    if stamp != stamp:
        obj.last_reported = NS(timestamp=lambda: stamp)
    else:
        obj.last_reported = datetime.fromtimestamp(stamp, timezone.utc)
    assert_no_tank_context(env.helper.read_tank_context(env.sources["tank_entity"]))


def test_last_reported_precedes_newer_last_updated_and_last_changed(monkeypatch):
    env = display_setup(monkeypatch)
    obj = env.state(env.sources["tank_entity"], "heating", {"operation_mode": "heating"})
    obj.last_reported = datetime.fromtimestamp(879, timezone.utc)
    obj.last_updated = obj.last_changed = datetime.fromtimestamp(999, timezone.utc)
    assert_no_tank_context(env.helper.read_tank_context(env.sources["tank_entity"]))


def test_reader_uses_last_updated_only_without_reported_stamp_and_never_refreshes_on_read(monkeypatch):
    env = display_setup(monkeypatch)
    obj = env.state(env.sources["tank_entity"], "heating", {"operation_mode": "heating"}, stamp=900)
    obj.last_reported = None
    assert env.helper.read_tank_context(env.sources["tank_entity"])["observed_at"] == 900
    env.clock[0] = 1021
    assert_no_tank_context(env.helper.read_tank_context(env.sources["tank_entity"]))
    assert obj.last_updated.timestamp() == 900


@pytest.mark.parametrize("entity_id,platform", [("water_heater.generic_tank", "generic"),
    ("water_heater.generic_tank", "aquarea"), ("sensor.pump_tank", "aquarea")])
def test_generic_or_wrong_domain_heating_entity_cannot_claim_tank_function(monkeypatch, entity_id, platform):
    env = display_setup(monkeypatch)
    env.rows[entity_id] = NS(entity_id=entity_id, platform=platform, config_entry_id="native",
        unique_id="generic_tank" if entity_id.startswith("water_heater.") else "pump_tank",
        device_id="registry_pump", disabled_by=None)
    env.state(entity_id, "heating", {"operation_mode": "heating", "current_temperature": 49,
        "temperature": 50, "hvac_action": "heating"})
    assert_no_tank_context(env.helper.read_tank_context(entity_id))


def test_missing_native_tank_report_cannot_be_replaced_with_other_sources(monkeypatch):
    env = display_setup(monkeypatch)
    env.helper.runtime.hass.states.data.pop(env.sources["tank_entity"])
    env.state(env.sources["direction_entity"], "WATER")
    env.state("sensor.total_power", "3000", {"unit_of_measurement": "W"})
    assert_sources(env.helper.display_sources(), env.sources)
    assert_no_tank_context(env.helper.read_tank_context(env.sources["tank_entity"]))
    assert env.coordinator.listeners == [] and env.coordinator.api_calls == []
    assert env.helper.runtime.hass.services.calls == []
