"""Public diagnostics expose SG evidence flags, never private Panasonic details."""
import json

import pytest

from custom_components.solar_pilot.diagnostics import async_get_config_entry_diagnostics
from test_runtime import build


@pytest.mark.asyncio
@pytest.mark.parametrize('scope', ['unconfirmed', 'total', 'supply1', 'supply2'])
async def test_diagnostics_keep_power_scope_and_proof_flags_without_private_details(scope):
    runtime, hass = build()
    runtime.entry.runtime_data = runtime
    runtime.panasonic.settings.update(
        power_scope=scope, power_entity='sensor.private_heatpump_power',
        tank_temperature_entity='sensor.private_tank',
        zone_entities=['climate.private_salon', 'climate.private_room'])
    overview_calls = []

    def overview():
        overview_calls.append(1)
        return {'configured': True, 'enabled': True, 'state': 'blocked',
                'desired_on': False, 'relay_on': None, 'action_required': True,
                'commissioning_confirmed': True, 'watchdog_confirmed': False,
                'entity_id': 'switch.private_sg', 'reason': 'Private room details',
                'fault': 'Private command details', 'blocked_reasons': ['Private history'],
                'temperature_c': 48.6, 'power_w': 2100}

    runtime.sg_boost.overview = overview
    before_services = list(hass.services.calls)
    result = await async_get_config_entry_diagnostics(hass, runtime.entry)
    assert overview_calls == [1]
    assert result['panasonic'] == {'configured': True, 'read_only': True,
                                  'power_scope': scope, 'power_meter': True, 'zone_count': 2}
    assert result['sg_boost']['action_required'] is True
    assert result['sg_boost']['relay_on'] is None
    assert not result['sg_boost']['watchdog_confirmed']
    public_text = json.dumps(result)
    assert 'private' not in public_text.lower()
    assert '48.6' not in public_text and '2100' not in public_text
    assert list(hass.services.calls) == before_services
