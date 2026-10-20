"""Water coverage is explicit and never refreshed by a different source."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import time

import pytest

from test_water_ui101 import run_water, text, water_day
from test_overview_details60 import Markup

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('water_diagnostic_ui_fixture', ROOT / 'custom_components/solar_pilot/water_diagnostics.py')
diagnostics = importlib.util.module_from_spec(spec)
spec.loader.exec_module(diagnostics)


def diagnostic_snapshot(*, flow_age=5, leak_age=5, flow_configured=True,
                        leak_configured=True, enabled=True, now=None):
    now = time.time() if now is None else now

    def source(value, unit, age, configured=True):
        return dict(value=value if configured else None, unit=unit,
                    reported_at=now-age if configured else None,
                    valid_until=now-age+300 if configured else None,
                    fresh=configured, reason='current' if configured else 'not_configured')

    view = dict(schema=1, read_only=True, enabled=enabled, configured=True, observed_at=now,
                volume=source(12345, 'L', 1), flow=source(0, 'L/min', flow_age, flow_configured),
                native_leak=source(False, None, leak_age, leak_configured),
                today={'volume_l': 12, 'volume_covered_s': 60},
                suspicion={'state': 'unknown', 'elapsed_s': 0})
    settings = dict(enabled=enabled,
                    flow_entity='sensor.fictional_flow' if flow_configured else '',
                    leak_entity='binary_sensor.fictional_leak' if leak_configured else '')
    view['diagnostic'] = diagnostics.water_monitor_diagnostic(view, settings)
    return view


def diagnose(view, code='return d._waterDiagnostic({water:input.data});'):
    return run_water(view, "d._last={state:'ready',attributes:{}};d._hass={config:{time_zone:'Europe/Brussels'}};"+code,
                     'SolarPilotCard')


def test_current_zero_and_false_mean_source_ready_not_completed_duration_or_leak_free():
    view = diagnostic_snapshot()
    result = diagnose(view)
    assert result['valid'] and result['state'] == 'current'
    assert result['continuous_flow_ready'] and result['native_leak_ready']
    html = diagnose(view, 'return d._waterDiagnosticHtml({water:input.data});')
    value = text(html)
    assert 'Gekoppelde bewakingsbronnen actueel' in value
    assert 'vereiste stromingsduur moet nog afzonderlijk worden bevestigd' in value
    assert 'bewijst geen lekvrijheid' in value
    assert 'force_update' not in value


@pytest.mark.parametrize('flow_age,leak_age,state,flow_ready,leak_ready', [
    (900, 5, 'incomplete', False, True), (5, 900, 'incomplete', True, False),
    (900, 900, 'unavailable', False, False),
])
def test_fresh_counter_never_repairs_stale_flow_or_false_leak(flow_age, leak_age, state, flow_ready, leak_ready):
    view = diagnostic_snapshot(flow_age=flow_age, leak_age=leak_age)
    original = deepcopy(view)
    result = diagnose(view)
    assert result['state'] == state
    assert result['continuous_flow_ready'] is flow_ready
    assert result['native_leak_ready'] is leak_ready
    assert result['flow_monitoring']['reported_at'] == view['flow']['reported_at']
    assert result['native_leak_monitoring']['reported_at'] == view['native_leak']['reported_at']
    assert result['flow_monitoring']['reported_at'] != view['volume']['reported_at']
    assert view == original


@pytest.mark.parametrize('flow,leak,state,flow_ready,leak_ready', [
    (True, False, 'current', True, False), (False, True, 'current', False, True),
    (False, False, 'not_configured', False, False),
])
def test_only_configured_detectors_define_state_and_missing_capability_stays_explicit(flow, leak, state, flow_ready, leak_ready):
    view = diagnostic_snapshot(flow_configured=flow, leak_configured=leak)
    result = diagnose(view)
    assert result['state'] == state and result['continuous_flow_ready'] is flow_ready
    assert result['native_leak_ready'] is leak_ready
    value = text(diagnose(view, 'return d._waterDiagnosticHtml({water:input.data});'))
    if not flow:
        assert 'Langdurige stroming kan nu niet betrouwbaar worden bewaakt' in value
    if not leak:
        assert 'Een native lekmelding is nu niet actueel beschikbaar' in value
    assert 'Niet gekoppeld' in value


def test_disabled_sources_do_not_become_current_or_trigger_mqtt_configuration_advice():
    view = diagnostic_snapshot(enabled=False)
    result = diagnose(view)
    assert result['state'] == 'disabled' and not result['continuous_flow_ready']
    assert not result['native_leak_ready']
    assert 'force_update' not in text(diagnose(view, 'return d._waterDiagnosticHtml({water:input.data});'))


def test_cached_ready_expires_against_its_own_original_report_even_with_new_counter():
    view = diagnostic_snapshot(flow_age=0, leak_age=0)
    view['volume']['reported_at'] += 301
    view['volume']['valid_until'] += 301
    result = diagnose(view, "Date.now=()=>Math.round((input.data.observed_at+301)*1000);return {diagnostic:d._waterDiagnostic({water:input.data}),facts:d._waterFacts({water:input.data})};")
    assert result['diagnostic']['valid'] and result['diagnostic']['state'] == 'unavailable'
    assert not result['diagnostic']['continuous_flow_ready']
    assert not result['diagnostic']['native_leak_ready']
    assert result['facts']['volume'] == 12345
    assert result['facts']['flow'] is None and result['facts']['leak'] is None


@pytest.mark.parametrize('mutation', [
    "delete w.diagnostic", "w.diagnostic.schema=true", "w.diagnostic.read_only=false",
    "w.diagnostic.state='safe'", "w.diagnostic.code='anything'", "w.diagnostic.hidden=true",
    "w.diagnostic.flow_monitoring.current='true'", "w.diagnostic.native_leak_monitoring.reported_at=false",
    "w.diagnostic.flow_monitoring.entity_id='sensor.fictional_injection'",
])
def test_invalid_closed_diagnostic_is_visible_and_never_silently_accepted(mutation):
    view = diagnostic_snapshot()
    result = diagnose(view, f"const w=input.data;{mutation};return {{diagnostic:d._waterDiagnostic({{water:w}}),html:d._waterDiagnosticHtml({{water:w}})}};")
    assert result['diagnostic']['valid'] is False
    assert 'waterdiagnose ontbreekt of is ongeldig' in text(result['html'])
    assert 'Gekoppelde bewakingsbronnen actueel' not in text(result['html'])


def test_stale_mqtt_help_is_conditional_read_only_and_does_not_claim_actual_configuration():
    view = diagnostic_snapshot(flow_age=900)
    html = diagnose(view, 'return d._waterDiagnosticHtml({water:input.data});')
    value = text(html)
    assert 'als de bron MQTT gebruikt' in value and 'force_update' in value
    assert 'MQTT-configuratie en de werkelijk ontvangen brokerberichten niet gecontroleerd' in value
    assert 'wijzigt geen broninstellingen' in value
    assert 'Een nieuwe totale meterstand vernieuwt geen flow- of lekrapport' in value
    root = Markup(html).root
    links = [n for n in root.walk() if n.tag == 'a']
    assert len(links) == 1 and links[0].attributes['href'].startswith('https://www.home-assistant.io/integrations/mqtt/')
    assert 'noopener' in links[0].attributes['rel']
    assert not any(n.tag in ('input', 'select', 'button') for n in root.walk())


def test_backend_summary_note_and_reason_are_rendered_as_text():
    view = diagnostic_snapshot(flow_age=900)
    view['diagnostic']['summary'] = '<img src=x onerror=alert(1)>'
    view['diagnostic']['note'] = '<script>alert(2)</script>'
    view['diagnostic']['flow_monitoring']['reason'] = '<img src=x>'
    html = diagnose(view, 'return d._waterDiagnosticHtml({water:input.data});')
    root = Markup(html).root
    assert not any(n.tag in ('img', 'script') for n in root.walk())
    assert '<img src=x' in root.text() and '<script>' in root.text()


def test_boiler_comparison_annotation_keeps_rolling_nonoverlap_and_household_partial_scope():
    html = run_water(water_day(), 'return d._waterCorrelationsHtml();')
    value = text(html)
    assert 'voortschrijdende vensters van maximaal 30 minuten' in value
    assert 'gemelde dalingen overlappen elkaar niet' in value
    assert 'huishoudelijke tellerstijging in bruikbare deelintervallen' in value
    assert 'geen bewijs van warmwatertap, oorzaak of verbruik per toestel' in value


def test_coverage_diagnostic_is_visible_in_water_tab_and_summary_without_control_actions():
    view = diagnostic_snapshot(flow_age=900, leak_age=900)
    result = diagnose(view, 'const c={water:input.data,a:{config_entry_id:"fictional-entry"}};return {html:d._water(c),summary:d._waterSummary(c)};')
    root = Markup(result['html']).root
    assert any('data-water-diagnostic' in n.attributes for n in root.walk())
    assert 'waterbewaking mist actuele' in text(result['summary'])
    assert {n.attributes.get('data-action') for n in root.walk() if n.tag == 'button'} == {
        'configure', 'water_history', 'source_history'}


def test_keyboard_focus_and_open_help_survive_current_meter_rerender_without_scrolling():
    result = run_water({}, """
d._view=d._lastRenderedView='water';let focused=null;
const old={dataset:{uiKey:'water:report-help'},open:true};
d.shadowRoot={activeElement:{tagName:'SUMMARY',parentElement:old}};
d._content={querySelectorAll:()=>[old]};const state=d._captureUiState();
const next={dataset:{uiKey:'water:report-help'},open:false};
d._content={querySelectorAll:()=>[next],querySelector:()=>({focus:options=>{focused=options}})};
d._restoreUiState(state);return {open:next.open,focused};
""", 'SolarPilotCard')
    assert result == {'open': True, 'focused': {'preventScroll': True}}
