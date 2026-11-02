"""Battery setup refuses incomplete scope, and source problems stay actionable."""
from copy import deepcopy
import sys
from types import ModuleType, SimpleNamespace as NS

import pytest

from homeassistant.helpers import entity_registry as er
from test_marstek_config_ui113 import flow, inputs, render  # noqa: F401
from test_audit_ui79 import execute


@pytest.mark.asyncio
@pytest.mark.parametrize("confirmation", [False, None, "true", "false", 1, 0, [], {}])
async def test_confirmation_error_never_saves_or_activates_a_monitor(flow, confirmation):
    before = deepcopy(flow.options)
    await flow.async_step_battery_marstek()
    result = await flow.async_step_battery_marstek(inputs(ac_power_confirmed=confirmation))
    assert result["errors"]["ac_power_confirmed"] == "battery_ac_confirmation"
    assert flow.saved is None and flow.options == before


@pytest.mark.asyncio
async def test_missing_confirmation_is_not_inherited_from_previous_form_input(flow):
    await flow.async_step_battery_marstek()
    submitted = inputs()
    submitted.pop("ac_power_confirmed")
    result = await flow.async_step_battery_marstek(submitted)
    assert result["errors"]["ac_power_confirmed"] == "battery_ac_confirmation"
    assert flow.saved is None


@pytest.fixture
def native_flow(flow, monkeypatch):
    module = ModuleType("homeassistant.helpers.entity_component")
    module.DATA_INSTANCES = "entity_components"
    monkeypatch.setitem(sys.modules, module.__name__, module)
    coordinator_type = type("MarstekDataUpdateCoordinator", (), {
        "__module__": "custom_components.marstek.coordinator",
    })
    coordinator = coordinator_type()
    entry = NS(domain="marstek", runtime_data=NS(coordinator=coordinator))
    row = NS(platform="marstek", config_entry_id="fictional-marstek-entry",
             unique_id="fictional-ongrid-sensor", device_id="fictional-storage")
    entity = NS(entity_id="sensor.fixture_ac", unique_id=row.unique_id,
                entity_description=NS(key="ongrid_power"), coordinator=coordinator)
    flow.hass.data = {module.DATA_INSTANCES: {"sensor": NS(get_entity=lambda eid:
        entity if eid == entity.entity_id else None)}}
    flow.hass.config_entries = NS(async_get_entry=lambda entry_id: entry)
    monkeypatch.setattr(er, "async_get", lambda hass: NS(async_get=lambda eid: row))
    flow.native_entity = entity
    return flow


@pytest.mark.asyncio
@pytest.mark.parametrize("key", ["battery_power", "em_total_power", "pv_power", "offgrid_power"])
async def test_loaded_native_non_ongrid_field_cannot_be_saved_as_battery_ac(native_flow, key):
    before = deepcopy(native_flow.options)
    native_flow.native_entity.entity_description.key = key
    await native_flow.async_step_battery_marstek()
    result = await native_flow.async_step_battery_marstek(inputs())
    assert result["errors"]["power_entity"] == "battery_native_scope"
    assert native_flow.saved is None and native_flow.options == before


@pytest.mark.asyncio
async def test_known_native_ac_direction_cannot_be_reversed(native_flow):
    await native_flow.async_step_battery_marstek()
    result = await native_flow.async_step_battery_marstek(inputs(power_sign="charge_positive"))
    assert result["errors"]["power_sign"] == "battery_native_sign"
    assert native_flow.saved is None


@pytest.mark.asyncio
async def test_verified_native_scope_still_needs_the_explicit_confirmation(native_flow):
    await native_flow.async_step_battery_marstek()
    result = await native_flow.async_step_battery_marstek(inputs(ac_power_confirmed=False))
    assert result["errors"] == {"ac_power_confirmed": "battery_ac_confirmation"}
    assert native_flow.saved is None
    result = await native_flow.async_step_battery_marstek(inputs())
    assert result["saved"]["batteries"][0]["ac_power_confirmed"] is True


@pytest.mark.asyncio
async def test_unloaded_provider_does_not_invent_a_different_sensor_scope(flow):
    await flow.async_step_battery_marstek()
    result = await flow.async_step_battery_marstek(inputs())
    assert result["saved"]["batteries"][0]["power_entity"] == "sensor.fixture_ac"
    assert result["saved"]["batteries"][0]["ac_power_confirmed"] is True


def test_unconfirmed_zero_power_with_known_soc_explains_the_actual_repair():
    reason = "AC-meetdekking nog niet bevestigd. Bewerk de Marstek-monitor."
    result = render(power_valid=False, power_w=0, source_code="ac_unconfirmed", reason=reason)
    assert result["reading"]["state"] == "Onbekend"
    assert "11%" in result["storage"] and reason in result["storage"]
    assert 'data-action="configure" data-config-step="battery"' in result["storage"]
    assert "Batterijbron controleren" in result["storage"]
    assert "bestuurbaar" not in result["storage"]


def test_invalid_native_scope_reason_is_escaped_in_display():
    result = render(power_valid=False, source_code="native_source_scope", reason='<img src=x onerror="bad()">')
    assert "<img" not in result["storage"] and "&lt;img" in result["storage"]


def test_changing_source_reason_refreshes_the_same_unknown_reading():
    result = execute("""
Date.now=()=>1800000000000;
const card=Object.create(SolarPilotCard.prototype);
const b={id:'fixture',profile:'marstek_venus_e3',power_valid:false,power_w:0,
soc_valid:true,soc_pct:11,soc_stamp:1800000000,power_stamp:1800000000,stale_s:120,
source_code:'ac_unconfirmed',reason:'Bevestiging ontbreekt'};
const context={batteryFleet:{batteries:[b]}};
const previous=card._marstekDisplaySignature(context);
b.source_code='native_source_scope';b.reason='Kies Vermogen netaansluiting';
console.log(JSON.stringify({changed:previous!==card._marstekDisplaySignature(context)}));
""")
    assert result["changed"] is True
