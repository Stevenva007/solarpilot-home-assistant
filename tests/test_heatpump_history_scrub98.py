"""Execute the shipped scrub selector against recorded evidence, never live values."""
from datetime import datetime, timezone
import json
import shutil
import subprocess

import pytest

from test_heatpump_history_ui70 import CARD, history_fixture, render_history
from test_overview_details60 import Markup


def scrub_fixture():
    data = history_fixture()
    start = datetime.fromisoformat('2026-10-12T00:00:00+02:00').timestamp()
    at = start + 6 * 3600 + 120
    data.update(day_start=start, day_end=start + 86400,
                support_sessions=[dict(data['sessions'][0])])
    data['sg_contact_overlay'] = {'schema': 1, 'segments': [dict(
        data['sessions'][0], state='off', reported_at=at - 2)]}
    data['native_evidence'] = {'schema': 1, 'read_only': True, 'points': [{
        'captured_at': at, 'source_stale_s': 120,
        'tank': {'temperature_c': 44, 'temperature_reported_at': at - 3,
                 'ordinary_target_c': 50, 'ordinary_target_reported_at': at - 5},
        'power': {'schema': 1, 'total_w': 0, 'reported_at': at - 2,
                  'valid_until': at + 118, 'stale_s': 120,
                  'source_scope': 'total', 'complete': True, 'kind': 'measured'},
        'supplies': [{'valid': True, 'watts': 1000, 'reported_at': at - 2},
                     {'valid': True, 'watts': 2000, 'reported_at': at - 2}]}]}
    # Deliberately conflicting current values must never reach the scrub readout.
    data['tank_temperature'] = {'schema': 1, 'current': {
        'current': True, 'captured_at': at, 'temperature_c': 99,
        'temperature_reported_at': at, 'ordinary_target_c': 98,
        'ordinary_target_reported_at': at}, 'points': []}
    return data


def run_scrub(data, code):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required to execute the shipped frontend')
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const context={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}}};
vm.createContext(context);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
context.input=input;
const result=vm.runInContext(`(()=>{const d=Object.create(SolarPilotHeatpumpHistoryDialog.prototype);
d._data=input.data;d._day=input.data.date;d._body={querySelector:()=>null,querySelectorAll:()=>[]};
${input.code}})()`,context);process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run([node, '-e', script, str(CARD)],
                            input=json.dumps({'data': data, 'code': code}),
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_snap_moves_time_marker_and_context_to_the_actual_capture():
    data = scrub_fixture()
    data['task_sessions'] = [dict(data['task_sessions'][0],
        segment_start='2026-10-12T06:01:00+02:00')]
    result = run_scrub(data, "d._setScrub(input.data.day_start+21600);return {state:d._scrubState(),html:d._scrubReadoutHtml()};")
    assert result['state']['at'] == data['native_evidence']['points'][0]['captured_at']
    text = Markup(result['html']).root.text()
    assert 'Meetpunt 06:02:00 GMT+2' in text
    assert 'Boiler opwarmen · Afgeleid' in text and 'SG-contact UIT' in text
    assert '0 W' in text and '44 °C' in text and '50 °C' in text
    assert '06:01:57 GMT+2' in text
    assert '99 °C' not in text and '98 °C' not in text
    assert '1,25 kWh is het dagtotaal' in text


def test_gap_keeps_selected_time_and_never_fills_measurements_or_off():
    result = run_scrub(scrub_fixture(), "d._setScrub(input.data.day_start+12*3600);return {state:d._scrubState(),html:d._scrubReadoutHtml()};")
    assert result['state']['point'] is None
    text = Markup(result['html']).root.text()
    assert 'Gekozen tijd 12:00:00 GMT+2' in text
    assert 'Geen vastgelegd meetpunt binnen 2½ minuut' in text
    assert '44 °C' not in text and '0 W' not in text
    assert 'SG-contact Onbekend / meetgat' in text
    assert 'Onbekend / geen AAN-periode' in text


@pytest.mark.parametrize('field,value', [('complete', False), ('total_w', True),
    ('total_w', -1), ('reported_at', 0), ('reported_at', 'bad'),
    ('valid_until', None), ('valid_until', 0), ('stale_s', True),
    ('source_scope', 'partial'), ('kind', 'estimated')])
def test_invalid_aggregate_cannot_fall_back_to_individual_feeds(field, value):
    data = scrub_fixture()
    data['native_evidence']['points'][0]['power'][field] = value
    html = run_scrub(data, 'd._setScrub(input.data.native_evidence.points[0].captured_at);return d._scrubReadoutHtml();')
    root = Markup(html).root
    total = next(n for n in root.walk() if n.tag == 'span' and n.text().startswith('Totaal vermogen'))
    assert '—' in total.text() and '3 kW' not in total.text()
    assert 'Voeding 1 1 kW' in root.text() and 'Voeding 2 2 kW' in root.text()


def test_legacy_power_unknown_and_original_sources_expire_at_capture():
    data = scrub_fixture()
    point = data['native_evidence']['points'][0]
    point.pop('power')
    point['tank']['temperature_reported_at'] = point['captured_at'] - 121
    html = run_scrub(data, 'd._setScrub(input.data.native_evidence.points[0].captured_at);return d._scrubReadoutHtml();')
    text = Markup(html).root.text()
    assert 'Totaal vermogen —' in text and 'Boilertemperatuur —' in text
    assert 'Ingesteld boilerdoel 50 °C' in text
    assert '3 kW' not in text


def test_scrub_uses_all_retained_points_and_does_not_resnap_refresh():
    data = scrub_fixture()
    first = data['native_evidence']['points'][0]
    data['native_evidence']['points'].extend(dict(first, captured_at=first['captured_at'] + 300 * n) for n in range(1, 201))
    result = run_scrub(data, 'd._setScrub(input.data.native_evidence.points[0].captured_at);const before=d._scrubState().at;d._data.native_evidence.points.shift();return {before,state:d._scrubState(),html:d._scrubReadoutHtml()};')
    assert result['before'] == first['captured_at']
    assert result['state']['at'] == first['captured_at']
    assert result['state']['point'] is None
    assert 'Gekozen tijd' in result['html'] and 'Meetpunt 06:07' not in result['html']


def test_every_time_lane_has_synchronized_accessible_scrub_surface():
    root = Markup(render_history(scrub_fixture())['html']).root
    lanes = [n for n in root.walk() if 'data-history-scrub' in n.attributes]
    assert {n.attributes['data-history-scrub'] for n in lanes} == {
        'task', 'contact', 'support', 'sg-request', 'sg-contact', 'sg-received'}
    assert all(n.attributes['role'] == 'slider' and n.attributes['tabindex'] == '0' for n in lanes)
    assert all(any('data-history-crosshair' in c.attributes for c in n.walk()) for n in lanes)


def test_dst_mapping_uses_actual_utc_day_and_keyboard_does_not_snap_back():
    data = scrub_fixture()
    data.update(date='2026-10-25', day_seconds=90000,
        day_start=datetime.fromisoformat('2026-10-25T00:00:00+02:00').timestamp(),
        day_end=datetime.fromisoformat('2026-10-26T00:00:00+01:00').timestamp())
    data['native_evidence']['points'] = []
    result = run_scrub(data, "const lane={};const event={target:{closest:()=>lane},key:'ArrowRight',preventDefault(){}};d._setScrub(d._data.day_start+9000,{snap:false});const first=d._scrubClock(d._scrubState().at);d._setScrub(d._data.day_start+12600,{snap:false});const second=d._scrubClock(d._scrubState().at);d._scrubKeydown(event);return {first,second,at:d._scrubState().at,target:d._scrubTarget({clientX:50},{left:0,width:100})};")
    assert result['first'] == '02:30:00 GMT+2'
    assert result['second'] == '02:30:00 GMT+1'
    assert result['at'] == data['day_start'] + 12660
    assert result['target'] == data['day_start'] + 45000


def test_vertical_gesture_and_second_pointer_cancel_without_selection():
    result = run_scrub(scrub_fixture(), "const lane={getBoundingClientRect:()=>({left:0,width:300})};const e={target:{closest:()=>lane},button:0,pointerId:1,pointerType:'touch',clientX:10,clientY:10};d._scrubPointerDown(e);d._scrubPointerMove({...e,clientX:11,clientY:35});const vertical=d._scrubPointer;d._scrubPointerDown(e);d._scrubPointerDown({...e,pointerId:2,isPrimary:false});return {vertical,pointer:d._scrubPointer,state:d._scrubState()};")
    assert result == {'vertical': None, 'pointer': None, 'state': None}


def test_capture_lives_on_stable_body_and_day_change_clears_it():
    result = run_scrub(scrub_fixture(), "let held=false,releases=0;d._body.setPointerCapture=()=>held=true;d._body.hasPointerCapture=()=>held;d._body.releasePointerCapture=()=>{held=false;releases++};d._fetch=()=>{};const lane={getBoundingClientRect:()=>({left:0,width:300})};const e={target:{closest:()=>lane},button:0,pointerId:1,pointerType:'touch',clientX:10,clientY:10,cancelable:true,preventDefault(){}};d._scrubPointerDown(e);d._scrubPointerMove({...e,clientX:30});const captured=held;d._selectDay('2026-10-11');return {captured,releases,state:d._scrubState(),pointer:d._scrubPointer,bounds:d._scrubBounds()};")
    assert result == {'captured': True, 'releases': 1, 'state': None, 'pointer': None, 'bounds': None}


def test_scrub_labels_are_escaped():
    data = scrub_fixture()
    payload = '<img src=x onerror="window.injected=true">'
    data['task_sessions'][0]['label'] = payload
    html = run_scrub(data, 'd._setScrub(input.data.native_evidence.points[0].captured_at);return d._scrubReadoutHtml();')
    root = Markup(html).root
    assert payload in root.text()
    assert not any(n.tag == 'img' for n in root.walk())


def test_new_native_semantics_caption_keeps_original_legacy_label():
    result = run_scrub(scrub_fixture(), "const p={native:{source:'aquarea_poll'},source_contract:{schema:1,read_only:true,verified:true,raw_device_action:'OFF',contract_id:'aioaquarea_ng_split_operation_status_v1',action_semantics:'operation_status'}};const current=d._nativeHistoryCaption(p);p.source_contract.contract_id='aioaquarea_ng_1_3_1_special_status';p.source_contract.action_semantics='special_status';const legacy=d._nativeHistoryCaption(p);return {current,legacy};")
    assert result['current'] == {'profile': True, 'verified': True, 'label': 'Panasonic-bronstatus: OFF'}
    assert result['legacy'] == {'profile': True, 'verified': True, 'label': 'SDK-profielstatus: OFF'}


def test_latest_observed_endpoint_is_visible_but_confirmed_stop_is_not_extended():
    data = scrub_fixture()
    at = data['native_evidence']['points'][0]['captured_at']
    end = datetime.fromtimestamp(at, timezone.utc).isoformat()
    for rows in (data['task_sessions'], data['support_sessions'], data['sg']['request']['sessions']):
        rows[0].update(segment_end=end, ongoing=False, stop_confirmed=False)
    html = run_scrub(data, 'd._setScrub(input.data.native_evidence.points[0].captured_at);return d._scrubReadoutHtml();')
    text = Markup(html).root.text()
    assert 'Boiler opwarmen · Afgeleid' in text
    assert 'SG-aanvraag AAN geregistreerd' in text
    assert 'Elektrische ondersteuning Geregistreerd' in text
    for rows in (data['task_sessions'], data['support_sessions'], data['sg']['request']['sessions']):
        rows[0]['stop_confirmed'] = True
    text = Markup(run_scrub(data, 'd._setScrub(input.data.native_evidence.points[0].captured_at);return d._scrubReadoutHtml();')).root.text()
    assert 'Taak Onbekend / meetgat' in text
    assert 'SG-aanvraag Onbekend / geen AAN-periode' in text
