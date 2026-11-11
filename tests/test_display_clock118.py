"""Server-clock alignment must not rejuvenate sources or create SG commands."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
from types import ModuleType, SimpleNamespace as NS

import pytest

from test_sg_manual_ui84 import fixture, NOW
from test_sg_ui_platforms62 import CARD


@pytest.fixture(params=['voluptuous', 'probatio'])
def api(monkeypatch, request):
    for backend in ('voluptuous', 'probatio'):
        lib = ModuleType(backend)
        lib.Required = lambda key: key
        monkeypatch.setitem(sys.modules, backend, lib)
    messages = ModuleType('homeassistant.components.websocket_api.messages')
    messages.BASE_COMMAND_MESSAGE_SCHEMA = type('Schema', (), {'__module__': request.param+'.schema'})()
    monkeypatch.setitem(sys.modules, messages.__name__, messages)
    comp = ModuleType('homeassistant.components')
    ws = ModuleType('homeassistant.components.websocket_api')
    ws.websocket_command = lambda schema: lambda fn: fn
    ws.async_register_command = lambda hass, fn: hass.registered.append(fn)
    comp.websocket_api = ws
    monkeypatch.setitem(sys.modules, comp.__name__, comp)
    monkeypatch.setitem(sys.modules, ws.__name__, ws)
    name = 'custom_components.solar_pilot._display_clock_test'
    spec = importlib.util.spec_from_file_location(name, CARD.parents[1]/'display_clock_api.py')
    module = importlib.util.module_from_spec(spec)
    monkeypatch.setitem(sys.modules, name, module)
    spec.loader.exec_module(module)
    return module


def context():
    runtime = NS(_closed=False)
    entry = NS(domain='solar_pilot', runtime_data=runtime)
    hass = NS(data={}, registered=[], config_entries=NS(async_get_entry=lambda key: entry if key == 'example' else None))
    results, errors = [], []
    connection = NS(user=NS(is_admin=False),
                    send_result=lambda _, result: results.append(result),
                    send_error=lambda _, code, message: errors.append((code, message)))
    return hass, entry, connection, results, errors


def test_authenticated_read_only_viewer_gets_only_server_time(api, monkeypatch):
    hass, _, connection, results, errors = context()
    monkeypatch.setattr(api.time, 'time', lambda: NOW)
    api.websocket_display_clock(hass, connection, {'id': 1, 'type': api.COMMAND, 'config_entry_id': 'example'})
    assert not errors
    assert results == [{'schema': 1, 'read_only': True, 'config_entry_id': 'example', 'server_time': NOW}]
    # The fake runtime intentionally has no sensors, controllers, stores or services.


@pytest.mark.parametrize('change', ['anonymous', 'missing', 'wrong_domain', 'closed', 'unloaded'])
def test_authentication_and_loaded_entry_are_required(api, change):
    hass, entry, connection, results, errors = context()
    msg = {'id': 1, 'type': api.COMMAND, 'config_entry_id': 'example'}
    if change == 'anonymous':
        connection.user = None
    elif change == 'missing':
        msg['config_entry_id'] = 'other'
    elif change == 'wrong_domain':
        entry.domain = 'other'
    elif change == 'closed':
        entry.runtime_data._closed = True
    else:
        entry.runtime_data = None
    api.websocket_display_clock(hass, connection, msg)
    assert not results and len(errors) == 1


@pytest.mark.parametrize('change', [{'config_entry_id': True}, {'config_entry_id': ''},
                                  {'type': 'solar_pilot/other'}, {'save': {}}, {'server_time': NOW}])
def test_request_cannot_supply_time_or_control_arguments(api, change):
    hass, _, connection, results, errors = context()
    api.websocket_display_clock(hass, connection, {'id': 1, 'type': api.COMMAND, 'config_entry_id': 'example', **change})
    assert not results and errors[0][0] == 'invalid_format'


def test_registration_is_idempotent(api):
    hass, *_ = context()
    api.async_register_display_clock_api(hass)
    api.async_register_display_clock_api(hass)
    assert hass.registered == [api.websocket_display_clock]


def execute(body, *, offset=-5.4, data=None):
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for actual frontend execution')
    source = r'''
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const BaseDate=Date,sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},input,
 setTimeout,clearTimeout,document:{visibilityState:'visible'},server:input.now,mono:100,wall:input.now+input.offset};
vm.createContext(sandbox);
vm.runInContext(`Date=class extends Date{static now(){return wall*1000;}};performance={now:()=>mono*1000};`,sandbox);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
vm.runInContext(`(async()=>{
 const calls=[],card=Object.create(SolarPilotCard.prototype),connection={connected:true};
 card.isConnected=true;card._last={state:'Zonnestroom',attributes:input.data};
 card._last.attributes.display_clock={schema:1,read_only:true};
 card._hass={user:{id:'fictional-viewer',is_admin:false},connection,callWS:async msg=>{
  calls.push(msg);mono+=0.02;wall+=0.02;server+=0.02;
  return {schema:1,read_only:true,config_entry_id:msg.config_entry_id,server_time:server-0.01};
 }};
 card._refreshObservationDisplay=()=>{};
 card._setDisplayClockContext(card._last);
 const advance=seconds=>{mono+=seconds;wall+=seconds;server+=seconds;};
 const states=()=>({manual:card._sgManualState(card._ctx()),contact:card._sgDisplayStates(card._ctx()).relay,
   reason:card._heatpumpReason(card._ctx()),fresh:card._freshObservation(card._ctx().sgBoost.observed_at,120),
   html:card._sgManualControl(card._ctx())});
 ${input.body}
})()`,sandbox).then(result=>process.stdout.write(JSON.stringify(result))).catch(error=>{process.stderr.write(error.stack);process.exitCode=1;});
'''
    result = subprocess.run([node, '-e', source, str(CARD)],
                            input=json.dumps({'now': NOW, 'offset': offset, 'data': data or fixture(), 'body': body}),
                            text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize('offset', [-3600, -7.5, -5.4, 0, 5.4, 3600])
def test_repeated_live_updates_do_not_flicker_with_a_different_screen_clock(offset):
    result = execute('''
 const rows=[];await card._syncDisplayClock();
 for(let i=0;i<151;i++){
   const s=card._last.attributes.sg_boost;s.observed_at=server;s.relay_observed_at=server;
   await card._syncDisplayClock();rows.push(states());advance(1);
 }
 return {rows,calls};
''', offset=offset)
    assert all(row['manual']['mode'] == 'auto' and row['contact']['state'] == 'inactive' for row in result['rows'])
    assert all(row['fresh'] and 'aria-pressed="true"' in row['html'] for row in result['rows'])
    assert len(result['calls']) <= 6
    assert all(call == {'type': 'solar_pilot/display_clock', 'config_entry_id': 'example'} for call in result['calls'])


@pytest.mark.parametrize('delta', [-121, 6])
@pytest.mark.parametrize('offset', [-3600, 3600])
def test_aligned_time_still_rejects_stale_and_future_source_evidence(delta, offset):
    result = execute(f'''
 await card._syncDisplayClock();const s=card._last.attributes.sg_boost;
 s.observed_at=server+({delta});s.relay_observed_at=server+({delta});
 return states();
''', offset=offset)
    assert result['manual']['mode'] is None and result['contact']['state'] == 'unknown'
    assert not result['fresh']


def test_sync_does_not_extend_a_manual_deadline_or_a_local_contact_lease():
    data = fixture('on', remaining=10)
    data['sg_boost'].update(desired_on=True, relay_on=True, relay_valid_until=NOW+5)
    result = execute('''
 await card._syncDisplayClock();const before=states();advance(11);
 const after=states();return {before,after,calls};
''', data=data)
    assert result['before']['contact']['state'] == 'active'
    assert result['after']['contact']['state'] == 'unknown'
    assert 'Tijd verstreken' in result['after']['html']
    assert len(result['calls']) == 1


@pytest.mark.parametrize('change', ['schema', 'entry', 'boolean', 'string', 'zero', 'slow', 'reversed'])
def test_invalid_or_slow_time_reply_never_creates_a_clock_sample(change):
    result = execute('''
 const clock=new SolarPilotDisplayClock(),data={schema:1,read_only:true,config_entry_id:'example',server_time:server};
 let started=mono,finished=mono+0.1;
 ''' + {'schema': 'data.schema=true;', 'entry': "data.config_entry_id='other';", 'boolean': 'data.server_time=true;',
        'string': 'data.server_time=String(server);', 'zero': 'data.server_time=0;', 'slow': 'finished=started+5.1;',
        'reversed': 'finished=started-1;'}[change] + '''
 return {accepted:clock.accept(data,'example',started,finished),now:clock.now()};
''')
    assert result == {'accepted': False, 'now': None}


@pytest.mark.parametrize('change', ['expired', 'suspended', 'wall_jump', 'monotonic_reversed', 'disconnected'])
def test_clock_loss_is_unknown_and_cannot_fall_back_to_the_screen_clock(change):
    action = {'expired': 'advance(181);', 'suspended': 'wall+=100;', 'wall_jump': 'wall-=100;',
              'monotonic_reversed': 'mono-=1;', 'disconnected': 'connection.connected=false;'}[change]
    result = execute('await card._syncDisplayClock();'+action+'return states();')
    assert result['manual']['mode'] is None and result['contact']['state'] == 'unknown'
    assert 'tijdsafstemming' in result['reason']


def test_late_response_after_user_or_entry_change_is_ignored():
    result = execute('''
 let resolve;card._hass.callWS=msg=>{calls.push(msg);return new Promise(r=>resolve=r);};
 const pending=card._syncDisplayClock();
 card._hass.user={id:'another-viewer',is_admin:false};
 card._last.attributes.config_entry_id='other';card._setDisplayClockContext(card._last);
 resolve({schema:1,read_only:true,config_entry_id:'example',server_time:server});await pending;
 return {state:states(),sample:card._displayClock?._sample??null,calls};
''')
    assert result['sample'] is None and result['state']['manual']['mode'] is None
    assert len(result['calls']) == 1


def test_restored_and_unavailable_snapshots_remain_unknown_after_sync():
    result = execute('''
 await card._syncDisplayClock();card._last.attributes.restored=true;const restored=states();
 card._last.attributes.restored=false;card._last.state='unavailable';return {restored,unavailable:states()};
''')
    assert all(row['manual']['mode'] is None and row['contact']['state'] == 'unknown' for row in result.values())
