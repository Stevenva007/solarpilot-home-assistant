"""Common device history uses recorded facts and authorized native source history."""
from datetime import datetime
import json
import shutil
import subprocess

import pytest

from test_heatpump_history_ui70 import CARD, history_fixture
from test_overview_details60 import Markup


def consumer_fixture():
    data = history_fixture()
    data.update(device_id='test-consumer', day_start=datetime.fromisoformat('2026-10-12T00:00:00+02:00').timestamp())
    data['day_end'] = data['day_start'] + 86400
    data['sessions'][0].update(id=7, start=data['sessions'][0]['segment_start'],
        end=data['sessions'][0]['segment_end'], observed_until=data['sessions'][0]['segment_end'],
        start_source='solarpilot', stop_source='unknown', start_confirmed=True,
        stop_confirmed=False, stop_reason='Meetonderbreking; geen stop bevestigd.')
    data['events'] = [dict(at='2026-10-12T11:00:03+02:00', kind='info',
        reason='Handmatig overgenomen; geen uitschakeling.')]
    data.update(current_status='CURRENT_ACTIVE_SENTINEL', power_w=99999)
    return data


def run_ui(data, code, prototype='SolarPilotConsumerHistoryDialog'):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for the shipped frontend')
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},
 CustomEvent:class{constructor(type,args){this.type=type;Object.assign(this,args)}}};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);sandbox.input=input;
const result=vm.runInContext(`(()=>{const d=Object.create(${input.prototype}.prototype);d._data=input.data;
d._body={innerHTML:'',querySelector:()=>null,querySelectorAll:()=>[]};d._scroll={scrollTop:0};
d.shadowRoot={activeElement:null};d._range=7;d._day=input.data.date;${input.code}})()`,sandbox);
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run([node, '-e', script, str(CARD)],
        input=json.dumps(dict(data=data, code=code, prototype=prototype)), text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def text(html):
    return ' '.join(Markup(html).root.text().split())


def test_consumer_cursor_uses_recorded_session_reasons_and_original_timestamps():
    result = run_ui(consumer_fixture(), 'd._setScrub(d._data.day_start+6.5*3600);return d._scrubReadoutHtml();')
    value = text(result)
    assert 'AAN-periode geregistreerd' in value and 'SolarPilot-opdracht' in value
    assert 'Native activiteit waargenomen' in value
    assert 'Einde onbekend' in value and 'Meetonderbreking; geen stop bevestigd.' in value
    assert '12/10/2026, 06:00:00 GMT+2' in value
    assert 'CURRENT_ACTIVE_SENTINEL' not in value and '99999' not in value
    assert 'Momentvermogen en sessieverbruik zijn niet in deze registratie bewaard.' in value


def test_consumer_sticky_summary_keeps_full_original_observations_in_closed_disclosure():
    html = run_ui(consumer_fixture(), 'd._setScrub(d._data.day_start+6.5*3600);return d._scrubReadoutHtml();')
    root = Markup(html).root
    details = next(n for n in root.walk() if n.tag == 'details' and 'data-consumer-selection' in n.attributes)
    assert 'open' not in details.attributes
    assert 'Native activiteit waargenomen' in details.text()
    assert '12/10/2026, 06:00:00 GMT+2' in details.text()
    assert 'Meetonderbreking; geen stop bevestigd.' in details.text()
    assert all(n.tag != 'dl' for n in root.children if n is not details)
    assert 'geregistreerd deze dag' in root.text()


def test_blank_consumer_timeline_does_not_confirm_off_or_reuse_current_values():
    value = text(run_ui(consumer_fixture(), 'd._setScrub(d._data.day_start+12*3600);return d._scrubReadoutHtml();'))
    assert 'Onbekend bij deze tijd' in value and 'Dit bewijst geen UIT-stand.' in value
    assert 'AAN-periode geregistreerd' not in value and 'CURRENT_ACTIVE_SENTINEL' not in value


def test_session_and_event_buttons_are_accessible_and_select_recorded_detail():
    html = run_ui(consumer_fixture(), 'd._renderData();return d._body.innerHTML;')
    root = Markup(html).root
    assert any(n.tag == 'button' and 'data-history-session' in n.attributes for n in root.walk())
    assert any(n.tag == 'button' and 'data-history-event' in n.attributes for n in root.walk())
    assert any(n.attributes.get('role') == 'slider' for n in root.walk())
    result = run_ui(consumer_fixture(), "const item=d._data.events[0],button={disabled:false,dataset:{historyEvent:d._historyItemKey(item,'event')}};d._click({target:{closest:()=>button}});return d._scrubReadoutHtml();")
    assert 'Geregistreerde gebeurtenis 11:00:03 GMT+2' in text(result)
    assert 'Handmatig overgenomen; geen uitschakeling.' in text(result)


def test_consumer_point_and_event_selection_do_not_modify_raw_evidence():
    result = run_ui(consumer_fixture(), "const before=JSON.stringify(d._data);d._setScrub(d._data.day_start+6.5*3600);d._renderData();return {same:before===JSON.stringify(d._data),request:d._historyRequest()};")
    assert result['same'] is True
    assert result['request']['type'] == 'solar_pilot/consumer_history'


def test_wallbox_open_period_has_no_fabricated_stop_or_end_power():
    event = dict(observed_start_at=1791800000, last_charging_report_at=1791800010,
                 previous_power_w=3800)
    html = run_ui(event, "return d._wallboxPeriodHtml(input.data,'wallbox',{ongoing:true});", 'SolarPilotCard')
    value = text(html)
    assert 'Nog geen stop bevestigd' in value and 'Einde onbekend / meetonderbreking' not in value
    assert '3,8 kW' in value and 'Vermogen bij eindrapport —' in value
    assert 'geen continue vermogensreeks' in value


def test_wallbox_ongoing_and_completed_observations_are_individually_expandable():
    event = dict(observed_start_at=1791800000, last_charging_report_at=1791800010,
                 previous_power_w=3800)
    data = dict(activity_details={'history': [dict(event, observed_stop_at=1791800020,
        stop_report_at=1791800020, stop_confirmed=True, power_w=0)], 'ongoing': event})
    html = run_ui(data, "return d._wallboxExplanation(input.data,{active:false,known:false},'wb');", 'SolarPilotCard')
    root = Markup(html).root
    rows = [n for n in root.walk() if n.tag == 'details' and n.attributes.get('class') == 'wb-history-period']
    assert len(rows) == 2 and all('open' not in n.attributes for n in rows)
    assert 'Nog geen stop bevestigd' in rows[0].text() and 'Stop waargenomen' in rows[1].text()


def test_catalogue_native_links_open_authorized_entity_history_and_escape_labels():
    data = dict(schema=1, read_only=True, scope='current_configured_sources', kind='battery',
        item_id='b1', name='<img src=x>', sources=[dict(role='power', label='<img src=x>', entity_id='sensor.battery_power')])
    html = run_ui(data, "d._kind='battery';d._itemId='b1';d._statusEl={};d._data=d._validated(input.data);d._render();return d._body.innerHTML;", 'SolarPilotSourceHistoryDialog')
    root = Markup(html).root
    assert not any(n.tag == 'img' for n in root.walk())
    link = next(n for n in root.walk() if n.tag == 'a')
    assert link.attributes['href'] == '/history?entity_id=sensor.battery_power'
    assert link.attributes['target'] == '_blank' and 'noopener' in link.attributes['rel']
    assert 'oudere gegevens kunnen bij een eerdere koppeling horen' in root.text()


def test_source_controls_cover_consumer_and_per_battery_with_read_only_catalog_request():
    result = run_ui({}, "d._last={attributes:{config_entry_id:'entry'}};return d._sourceHistoryButton('battery','b1');", 'SolarPilotCard')
    root = Markup(result).root
    button = next(n for n in root.walk() if n.tag == 'button')
    assert button.attributes['data-action'] == 'source_history'
    assert button.attributes['data-history-kind'] == 'battery' and button.attributes['data-id'] == 'b1'
    request = run_ui({}, "d._entryId='entry';d._kind='consumer';d._itemId='one';return d._request();", 'SolarPilotSourceHistoryDialog')
    assert request == dict(type='solar_pilot/source_history', config_entry_id='entry', kind='consumer', item_id='one')


def test_boiler_links_follow_each_displayed_value_source_not_configured_default():
    import time
    now = time.time()
    data = {'panasonic': {'source_stale_s': 120,
        'temperature_c': 46, 'temperature_entity': 'sensor.config_temperature', 'temperature_stamp': now,
        'target_c': 51, 'target_entity': 'number.config_target', 'target_stamp': now,
        'display_tank': {'available': True, 'entity_id': 'water_heater.actual_tank',
            'temperature_c': 49, 'target_c': 50, 'temperature_stamp': now, 'target_stamp': now}}}
    result = run_ui(data, "return {temperature:d._heatpumpTankObservation(input.data,'temperature_c'),target:d._heatpumpTankReading(input.data,'target_c')};", 'SolarPilotCard')
    assert result['temperature']['entity'] == 'water_heater.actual_tank'
    assert result['temperature']['source'] == 'display_tank'
    assert result['temperature']['value'] == 49
    button = next(n for n in Markup(result['target']).root.walk() if n.tag == 'button')
    assert button.attributes['data-history-role'] == 'tank_target_entity'
    assert button.attributes['data-history-entity'] == 'water_heater.actual_tank'
    data['panasonic']['display_tank']['target_stamp'] = now - 1000
    result = run_ui(data, "return d._heatpumpTankObservation(input.data,'target_c');", 'SolarPilotCard')
    assert result['entity'] == 'number.config_target' and result['source'] == 'configured'
    assert result['value'] == 51


def test_boiler_value_without_actual_source_entity_stays_plain_and_unknown_stays_unknown():
    import time
    data = {'panasonic': {'display_tank': {'available': True, 'temperature_c': 49,
        'temperature_stamp': time.time()}}}
    assert run_ui(data, "return d._heatpumpTankReading(input.data,'temperature_c');", 'SolarPilotCard') == '49 °C'
    data['panasonic']['display_tank']['temperature_stamp'] = 0
    assert run_ui(data, "return d._heatpumpTankReading(input.data,'temperature_c');", 'SolarPilotCard') == '—'


def test_heatpump_source_request_keeps_route_closed_and_omits_item_id():
    request = run_ui({}, "d._entryId='entry';d._kind='heatpump';d._source='display_tank';d._itemId='unrelated';return d._request();", 'SolarPilotSourceHistoryDialog')
    assert request == dict(type='solar_pilot/source_history', config_entry_id='entry', kind='heatpump', source='display_tank')


def test_calculated_goal_is_never_treated_as_an_entity_source():
    import time
    from test_heatpump_goals_ui83 import goal
    data = {'panasonic': {'source_stale_s': 120, 'display_tank': {'available': True,
        'entity_id': 'water_heater.actual_tank', 'temperature_c': 49, 'target_c': 50,
        'temperature_stamp': time.time(), 'target_stamp': time.time()}, 'sg_tank_goal': goal()}}
    html = run_ui(data, "return d._heatpumpTankSummary(input.data);", 'SolarPilotCard')
    root = Markup(html).root
    buttons = [n for n in root.walk() if n.tag == 'button' and n.attributes.get('data-action') == 'heatpump_source_history']
    assert len(buttons) == 2
    assert {n.attributes['data-history-role'] for n in buttons} == {'tank_temperature_entity', 'tank_target_entity'}
    assert all('57,5' not in n.text() for n in buttons)
