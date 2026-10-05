"""Execute actual card rendering/downloads and verify observed history semantics."""
from datetime import timedelta
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from test_consumer_history import ConsumerHistory, CFG, BASE, run

CARD = Path(__file__).resolve().parents[1] / 'custom_components/solar_pilot/frontend/solar-pilot-card.js'


def browser_double(payload):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node required for real frontend execution')
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const calls=[],parts={'.download':{disabled:false},'.status':{textContent:''},'.hours':{value:'168'},'.names':{checked:false}};
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},Blob,
 URL:{createObjectURL:b=>{calls.push({blob:b.size});return 'blob:local';},revokeObjectURL:()=>{}},
 document:{body:{appendChild:()=>{}},createElement:()=>({click(){calls.push({download:this.download});},remove(){}})},setTimeout:()=>0,input,calls,parts};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
vm.runInContext(`(async()=>{
 const card=Object.create(SolarPilotCard.prototype);card._hass={config:{time_zone:'Europe/Brussels'}};
 if(input.render)return {html:card._decisionBoard(input.render)};
 if(input.setting){card._hass.states=input.states||{};return {html:card._climateSettingControl(input.setting)};}
 const d=Object.create(SolarPilotAnalysisDialog.prototype);d._seq=0;d._open=true;d._entryId='entry';d.shadowRoot={querySelector:s=>parts[s]};
 d._hass={callWS:async m=>{calls.push(m);if(input.close)d.close();return {download_url:input.url||'/api/solar_pilot/analysis/token',filename:'SolarPilot-168h.json.gz'};},
 fetchWithAuth:async(path,options)=>{calls.push({path,method:options.method});if(input.hangCleanup&&options.method==='DELETE')return new Promise(()=>{});return {ok:!input.expired,status:input.expired?410:200,blob:async()=>new Blob(['compressed-file'])};}};
 d._dialog={open:false};await d._download();return {calls,status:parts['.status'].textContent,disabled:parts['.download'].disabled};
})()`,sandbox).then(x=>process.stdout.write(JSON.stringify(x))).catch(e=>{process.stderr.write(e.stack);process.exitCode=1;});
'''
    result = subprocess.run([node, '-e', script, str(CARD)], input=json.dumps(payload),
                            text=True, capture_output=True, check=True)
    return json.loads(result.stdout)


def test_seven_day_download_uses_authenticated_binary_route_then_removes_private_copy():
    result = browser_double({})
    assert result['calls'][0]['hours'] == 168 and result['calls'][0]['download'] is True
    assert [x['method'] for x in result['calls'] if 'method' in x] == ['GET', 'DELETE']
    assert any(x.get('download') == 'SolarPilot-168h.json.gz' for x in result['calls'])
    assert 'gedownload' in result['status'] and result['disabled'] is False


@pytest.mark.parametrize('url', ['https://example.invalid/private', '//example.invalid/private', '/api/other/token'])
def test_download_never_forwards_ha_authentication_to_an_unexpected_url(url):
    result = browser_double({'url': url})
    assert not any('method' in x or 'blob' in x for x in result['calls'])
    assert 'lokaal downloadadres' in result['status']


def test_expired_download_has_actionable_message_without_fake_success():
    result = browser_double({'expired': True})
    assert 'verlopen' in result['status']
    assert not any('blob' in x for x in result['calls'])


def test_closing_export_while_ws_is_pending_does_not_trigger_late_download():
    result = browser_double({'close': True})
    assert [x['method'] for x in result['calls'] if 'method' in x] == ['DELETE']
    assert not any('download' in x and 'type' not in x for x in result['calls'])


def test_private_copy_cleanup_cannot_hold_up_an_already_received_file():
    result = browser_double({'hangCleanup': True})
    assert any(x.get('download') == 'SolarPilot-168h.json.gz' for x in result['calls'])
    assert 'gedownload' in result['status'] and result['disabled'] is False


@pytest.mark.parametrize('fleet,label', [
    ({'enabled': True, 'control_enabled': False}, 'Alleen bekijken'),
    ({'enabled': True, 'control_enabled': True, 'pending': {'one': {'mode': 'charge'}}}, 'Wacht op bevestiging'),
    ({'enabled': True, 'control_enabled': True, 'faults': {'one': 'Onzeker'}}, 'Controle nodig'),
])
def test_central_battery_status_uses_actual_control_and_confirmation_contract(fleet, label):
    html = browser_double({'render': {'batteryFleet': fleet, 'devices': []}})['html']
    assert label in html and 'Regeling aan' not in html


def test_programme_source_setting_is_a_read_only_source_selector():
    html = browser_double({'setting': {'key': 'operation_mode_entity', 'type': 'program_entity', 'value': 'select.programme'},
                           'states': {'select.programme': {'attributes': {'friendly_name': 'Warmtepompprogramma'}},
                                      'sensor.mode': {'attributes': {}}, 'switch.pump': {'attributes': {}},
                                      'input_select.programme': {'attributes': {}}}})['html']
    assert 'Automatisch uit Aquarea uitlezen' in html
    assert 'select.programme' in html and 'sensor.mode' in html and 'switch.pump' not in html
    assert 'input_select.programme' not in html
    assert 'selected' in html and 'data-climate-type="program_entity"' in html


def test_own_pause_programme_intent_is_never_presented_as_current_heating():
    html = browser_double({'render': {'devices': [], 'smartClimate': {'zones': [
        {'entity_id': 'climate.one', 'name': 'Ruimte', 'mode': 'off', 'current': 22, 'target': 21,
         'execution_reason': 'Nog geen warmtevraag', 'native_program': {
             'program': 'heating', 'current_native_program': 'off', 'programme_intent': 'heating',
             'source': 'owned_off_programme'}}]}}})['html']
    assert 'warmtepompprogramma uit na eigen pauze; eerder verwarmen' in html
    assert 'warmtepompprogramma verwarmen.' not in html


def test_central_board_keeps_real_target_and_zone_reasons_distinct_and_escapes_sources():
    result = browser_double({'render': {
        'dhw': {'configured': True, 'actual_target_c': 50, 'proposed_target_c': 60, 'temperature_c': 49,
                'execution': {'reason': 'Sterilisatiebescherming tot 15:00', 'surplus_target_c': 60}},
        'smartClimate': {'zones': [
            {'entity_id': 'climate.one', 'name': 'Ruimte A', 'mode': 'off', 'current': 22, 'target': 21, 'decision_reason': 'Blijft zonder verwarming op temperatuur'},
            {'entity_id': 'climate.two', 'name': 'Ruimte B', 'mode': 'auto', 'current': 20, 'target': 21, 'decision_reason': 'Warmtevraag blijft aanhouden <script>'}]},
        'devices': []}})
    html = result['html']
    assert 'Wat gebeurt er en waarom?' in html
    assert 'Tank 49 °C · doel 50 °C' in html and 'tot 15:00' in html
    assert 'Blijft zonder verwarming' in html and 'Warmtevraag blijft aanhouden &lt;script&gt;' in html
    assert '<script>' not in html and 'doel 60 °C' not in html


def test_brief_history_has_observed_start_stop_reason_but_no_unconfirmed_command_as_change():
    model = ConsumerHistory();run(model, False, BASE)
    model.command('one', CFG, 350, 'Wacht op zon', BASE)
    assert model.brief('one', BASE)['last_change'] is None
    model.confirm('one');run(model, True, BASE + timedelta(seconds=5))
    change = model.brief('one', BASE + timedelta(seconds=5))['last_change']
    assert change['state'] == 'on' and change['source'] == 'solarpilot' and change['confirmed']
    assert change['reason'] == 'Wacht op zon'
    run(model, False, BASE + timedelta(seconds=10))
    change = model.brief('one', BASE + timedelta(seconds=10))['last_change']
    assert change['state'] == 'off' and change['source'] == 'external' and change['confirmed']


def test_unknown_stop_during_measurement_gap_remains_unconfirmed_in_central_history():
    model = ConsumerHistory();run(model, True, BASE)
    run(model, None, BASE + timedelta(seconds=5))
    change = model.brief('one', BASE + timedelta(seconds=5))['last_change']
    assert change['confirmed'] is False and change['source'] == 'unknown'
    assert change['state'] == 'unknown'
