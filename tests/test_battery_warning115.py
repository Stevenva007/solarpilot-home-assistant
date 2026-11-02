"""Battery source issues open configuration, without pretending to reset a device."""
import pytest

from test_source_wait_ui52 import render_alerts
from test_audit_ui79 import execute


@pytest.mark.parametrize("reason", [
    "Fictional Venus: AC-meetdekking nog niet bevestigd",
    "Fictional battery: geen actueel AC-veldrapport",
    '<img src=x onerror="bad()"> bron onbekend',
])
def test_battery_source_warning_offers_configuration_instead_of_fault_reset(reason):
    markup, notice = render_alerts({
        "problem": reason, "problem_kind": "battery_source", "reset_entity": "button.fixture_reset",
    })
    assert notice.actions == ["configure"]
    assert 'data-config-step="battery"' in markup
    assert "Batterijbron controleren" in notice.text
    assert "bestaande batterijmonitor" in notice.text
    assert reason in notice.text
    assert "Controle afronden" not in notice.text
    assert "<img" not in markup


def test_restart_control_keeps_precedence_over_battery_configuration():
    _, notice = render_alerts({
        "problem": "Herstartcontrole", "problem_kind": "battery_source",
        "restart_recovery_pending": True, "reset_entity": "button.fixture_reset",
    })
    assert "Automatische herstartcontrole" in notice.text
    assert notice.actions == []


def test_source_configuration_action_uses_options_and_never_calls_device_services():
    result = execute("""
const card=Object.create(SolarPilotCard.prototype),routes=[];
card._openOptions=async step=>{routes.push(step);return true;};
card._hass={callService:()=>{throw Error('A source issue cannot operate or reset devices');}};
await card._click({target:{closest:()=>({dataset:{action:'configure',configStep:'battery'}})}});
console.log(JSON.stringify(routes));
""")
    assert result == ["battery"]
