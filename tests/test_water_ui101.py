"""The shipped water UI displays retained evidence without device attribution."""
from datetime import datetime
import json
import shutil
import subprocess
import time

import pytest

from test_overview_details60 import CARD, Markup


def water_day():
    start = datetime.fromisoformat('2026-10-19T00:00:00+02:00').timestamp()
    at = start + 9*3600 + 12*60

    def reading(value, unit=None):
        return dict(value=value, unit=unit, reported_at=at-2, valid_until=at+298,
                    fresh=True, reason='measured')

    point = dict(captured_at=at, volume=reading(1000.5, 'L'), flow=reading(6, 'L/min'),
                 native_leak=reading(False), context_binding='a'*64,
                 context={'boiler': {'temperature': reading(49), 'target': reading(50)},
                          'dishwasher': reading(True)})
    return dict(schema=1, read_only=True, date='2026-10-19', today='2026-10-19',
                min_date='2026-09-20', timezone='Europe/Brussels',
                day_start=start, day_end=start+86400, day_seconds=86400,
                generated_at=at+60, retention_days=30, revision=4, has_data=True,
                volume_l=3, volume_covered_s=60, complete=False,
                points=[point], days=[dict(date='2026-10-19', volume_l=3)],
                intervals=[dict(start=at-60, end=at, volume_l=3, day='2026-10-19', reason='counter_delta')],
                events=[dict(at=at+600, kind='counter_gap')], coverage={'point_cap': 8192},
                correlations={'read_only': True, 'scope': 'household_water',
                    'boiler_drops': [dict(start=at-600, end=at, temperature_start_c=52,
                        temperature_end_c=49, drop_c=3, observed_volume_l=3,
                        volume_partial=True, water_observed=True, flow_observed=True)],
                    'dishwasher_intervals': [dict(start=at-60, end=at, observed_volume_l=3,
                        volume_partial=True, scope='household_during_observed_dishwasher')]})


def run_water(data, code, prototype='SolarPilotWaterHistoryDialog'):
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


def test_water_cursor_uses_one_actual_capture_and_original_source_times():
    data = water_day()
    html = run_water(data, 'd._setScrub(d._data.points[0].captured_at-20);return d._scrubReadoutHtml();')
    value = text(html)
    assert 'Meetpunt 09:12:00 GMT+2' in value
    assert '6 L/min' in value and '1.000,5 L' in value
    assert '49 °C' in value and '50 °C' in value and 'Programma actief' in value
    assert 'Niet gemeld' in value and '19/10/2026, 09:11:58 GMT+2' in value
    assert 'geen oorzaak of liters per toestel' in value


def test_water_gap_never_borrows_future_or_current_numeric_context():
    data = water_day()
    data.update(current_flow=99999, current_temperature=99)
    html = run_water(data, 'd._setScrub(d._data.points[0].captured_at-31);return d._scrubReadoutHtml();')
    value = text(html)
    assert 'Gekozen tijd 09:11:29 GMT+2' in value and 'Waarden bij deze tijd zijn onbekend' in value
    assert '6 L/min' not in value and '49 °C' not in value and '99999' not in value


def test_keyboard_exact_actual_time_retains_its_point_without_moving_the_marker():
    html = run_water(water_day(), 'd._setScrub(d._data.points[0].captured_at,{snap:false});return d._scrubReadoutHtml();')
    value = text(html)
    assert 'Meetpunt 09:12:00 GMT+2' in value and '6 L/min' in value


@pytest.mark.parametrize('role,value,expected', [
    ('flow', 0, '0 L/min'), ('volume', 0, '0 L'), ('native_leak', False, 'Niet gemeld')])
def test_water_actual_zero_and_false_remain_known(role, value, expected):
    data = water_day()
    data['points'][0][role]['value'] = value
    html = run_water(data, 'd._setScrub(d._data.points[0].captured_at);return d._scrubReadoutHtml();')
    assert expected in text(html)


@pytest.mark.parametrize('change', [
    "p.flow.value=true", "p.flow.value=NaN", "p.flow.value=Infinity",
    "p.flow.fresh=false", "p.flow.reported_at=p.captured_at+10",
    "p.flow.valid_until=p.captured_at-1", "p.flow.unit='W'", "p.flow.value=-1",
])
def test_water_invalid_or_expired_reading_is_unknown_at_capture(change):
    result = run_water(water_day(), f'const p=d._data.points[0];{change};return d._pointWater(p);')
    assert result['flow'] is None
    assert result['temperature'] == 49


def test_water_history_keeps_old_capture_valid_without_using_wall_clock():
    result = run_water(water_day(), 'return d._pointWater(d._data.points[0]);')
    assert result['flow'] == 6 and result['leak'] is False


def test_water_lanes_are_independent_point_samples_and_raw_data_stays_unchanged():
    result = run_water(water_day(), "const before=JSON.stringify(d._data);d._renderData();return {html:d._body.innerHTML,same:before===JSON.stringify(d._data)};")
    root = Markup(result['html']).root
    assert result['same']
    lanes = [n for n in root.walk() if 'data-history-scrub' in n.attributes]
    assert len(lanes) == 4 and all(n.attributes.get('role') == 'slider' for n in lanes)
    assert 'Elke streep is een bewaard meetpunt' in root.text()
    assert 'geen 0 liter' in root.text() and 'onvolledig dagbeeld' in root.text()


def test_water_correlations_keep_household_scope_and_no_attributed_device_liters():
    html = run_water(water_day(), 'return d._waterCorrelationsHtml();')
    value = text(html)
    assert '52 °C → 49 °C' in value and 'daling 3 °C' in value
    assert '3 L huishoudelijke tellerstijging in bruikbare deelintervallen' in value
    assert 'geen gemeten vaatwasverbruik' in value and 'geen bewijs van warmwatertap' in value
    data = water_day()
    data['correlations']['boiler_drops'][0]['water_observed'] = None
    html = run_water(data, 'return d._waterCorrelationsHtml();')
    assert 'Geen bevestigde waterwaarneming' in text(html)


def test_water_request_and_source_catalogue_never_send_arbitrary_entity_ids():
    result = run_water({}, "d._entryId='fictional-entry';return d._historyRequest();")
    assert result == dict(type='solar_pilot/water_history', config_entry_id='fictional-entry')
    request = run_water({}, "d._entryId='fictional-entry';d._kind='water';d._itemId='ignored';return d._request();", 'SolarPilotSourceHistoryDialog')
    assert request == dict(type='solar_pilot/source_history', config_entry_id='fictional-entry', kind='water')


def test_water_envelope_rejects_missing_read_only_or_invalid_local_date():
    for field, value in [('read_only', False), ('date', '2026-02-30'), ('timezone', '<invalid>')]:
        data = water_day()
        data[field] = value
        assert run_water(data, "try{d._validatedWaterDay(input.data);return false;}catch{return true;}") is True


def test_water_day_bounds_cannot_silently_select_the_previous_local_day():
    data = water_day()
    data['day_start'] -= 86400
    data['day_end'] -= 86400
    assert run_water(data, "try{d._validatedWaterDay(input.data);return false;}catch{return true;}") is True


def test_live_water_uses_original_current_sources_and_stale_false_becomes_unknown():
    now = time.time()
    source = dict(value=0, unit='L/min', reported_at=now-10, valid_until=now+100, fresh=True)
    data = dict(schema=1, read_only=True, configured=True, enabled=True,
                flow=source, volume=dict(source, value=100, unit='L'),
                native_leak=dict(source, value=False, unit=None), today={'volume_l': 0})
    code = "d._last={state:'ready',attributes:{}};return d._waterFacts({water:input.data});"
    result = run_water(data, code, 'SolarPilotCard')
    assert result['flow'] == 0 and result['leak'] is False and result['today'] == 0
    data['native_leak']['valid_until'] = now-1
    assert run_water(data, code, 'SolarPilotCard')['leak'] is None
    data['enabled'] = False
    assert run_water(data, code, 'SolarPilotCard')['flow'] is None


def test_water_view_and_configuration_have_only_explicit_read_only_navigation():
    result = run_water({}, "d._last={state:'ready',attributes:{}};return d._water({a:{config_entry_id:'fictional-entry'},water:{}});", 'SolarPilotCard')
    root = Markup(result).root
    actions = {n.attributes.get('data-action') for n in root.walk() if n.tag == 'button'}
    assert actions == {'configure', 'water_history', 'source_history'}
    assert any(n.attributes.get('data-config-step') == 'water' for n in root.walk())


def test_water_source_and_coverage_text_are_escaped():
    data = water_day()
    data['coverage']['note'] = '<img src=x onerror=alert(1)>'
    html = run_water(data, 'd._renderData();return d._body.innerHTML;')
    assert not any(n.tag == 'img' for n in Markup(html).root.walk())
    assert '<img src=x' in text(html)
