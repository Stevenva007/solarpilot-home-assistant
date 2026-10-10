"""Large local downloads preserve history and enforce HA permissions.

The production gzip writer runs against real temporary files. HTTP handler
permissions/metadata use explicit HA/aiohttp doubles, not an HA Core server.
"""
import asyncio
import gzip
import json
import os
from pathlib import Path
import threading
import time
from types import ModuleType, SimpleNamespace
import sys

import pytest

from test_analysis_api import api
from test_consumer_history_api import context
from custom_components.solar_pilot import analysis_export as ae
from custom_components.solar_pilot.const import VERSION


def download_context():
    runtime, hass, connection, results, errors = context()
    connection.user.id = 'admin_test'
    return runtime, hass, connection, results, errors


class HTTPError(Exception):
    def __init__(self, *, text):
        super().__init__(text)


class Forbidden(HTTPError):
    pass


class NotFound(HTTPError):
    pass


class Gone(HTTPError):
    pass


@pytest.fixture
def http_view(api, monkeypatch):
    web = SimpleNamespace(HTTPForbidden=Forbidden, HTTPNotFound=NotFound, HTTPGone=Gone,
        FileResponse=lambda path, headers: SimpleNamespace(path=path, headers=headers),
        Response=lambda status, headers: SimpleNamespace(status=status, headers=headers))
    aiohttp = ModuleType('aiohttp'); aiohttp.web = web
    http = ModuleType('homeassistant.components.http.view'); http.HomeAssistantView = type('HomeAssistantView', (), {})
    monkeypatch.setitem(sys.modules, 'aiohttp', aiohttp)
    monkeypatch.setitem(sys.modules, http.__name__, http)
    return api.analysis_download_view()


class Request(dict):
    def __init__(self, hass, user):
        super().__init__(hass_user=user)
        self.app = {'hass': hass}


async def create_download(api, *, hours=168, names=False):
    runtime, hass, connection, results, errors = download_context()
    await api.websocket_analysis_export(hass, connection, {'id': 1, 'config_entry_id': 'test',
        'hours': hours, 'include_names': names, 'download': True})
    assert not errors
    token = results[0]['download_url'].rsplit('/', 1)[1]
    return runtime, hass, connection, results[0], token


@pytest.mark.asyncio
async def test_seven_day_report_above_old_ws_ceiling_is_complete_and_private(api):
    runtime, hass, connection, results, errors = download_context()
    before = list(hass.services.calls)
    wall = time.time()
    detail = 'Observed source and control context; ' * 86
    for index in range(ae.MAX_EVENTS):
        runtime.analysis.events.append({'ts': wall - (ae.MAX_EVENTS - index) * 100,
            'release': '1.0.0-beta.54', 'kind': 'decision', 'message': detail,
            'data': {'sequence': index, 'source': 'sensor.grid'}})
    runtime.entry.data['password'] = 'DO_NOT_SHARE_THIS'
    await api.websocket_analysis_export(hass, connection, {'id': 1, 'config_entry_id': 'test',
        'hours': 168, 'download': True})
    try:
        assert not errors and len(results) == 1
        answer = results[0]
        # Source association, a small advice template and quality summary travel
        # over WS; the large recorded evidence remains in the streamed artifact.
        assert 'content' not in answer and len(json.dumps(answer)) < 8 * 1024
        assert 'history' not in answer and 'telemetry' not in answer
        assert answer['feedback_template']['source_export'] == answer['source_export']
        assert answer['uncompressed_bytes'] > ae.MAX_EXPORT_BYTES
        assert answer['filename'].endswith('-168h.json.gz')
        assert answer['media_type'] == 'application/gzip'
        token = answer['download_url'].rsplit('/', 1)[1]
        item = hass.data[api._DOWNLOADS]['files'][token]
        assert os.stat(item['path']).st_mode & 0o777 == 0o600
        with gzip.open(item['path'], 'rt', encoding='utf-8') as source:
            text = source.read()
        report = json.loads(text)
        assert report['requested_hours'] == 168
        assert len(report['telemetry']['events']) == ae.MAX_EVENTS
        assert report['telemetry']['events'][-1]['data']['sequence'] == ae.MAX_EVENTS - 1
        assert report['telemetry']['events'][0]['release'] == '1.0.0-beta.54'
        assert 'DO_NOT_SHARE_THIS' not in text and 'sensor.grid' not in text
        assert not report['privacy']['entity_names_included']
        assert report['privacy']['automatic_upload'] is False
        assert hass.services.calls == before
    finally:
        await api._close_downloads(hass)


@pytest.mark.asyncio
@pytest.mark.parametrize('names', [False, True])
async def test_explicit_names_option_survives_compression(api, names):
    runtime, hass, connection, answer, token = await create_download(api, names=names)
    try:
        with gzip.open(hass.data[api._DOWNLOADS]['files'][token]['path'], 'rt') as source:
            text = source.read()
        assert ('sensor.grid' in text) is names
        assert json.loads(text)['privacy']['entity_names_included'] is names
    finally:
        await api._close_downloads(hass)


@pytest.mark.asyncio
async def test_gzip_generation_runs_off_event_loop(api, monkeypatch):
    event_thread = threading.get_ident()
    workers = []
    original = api.write_compressed_report
    def traced(report):
        workers.append(threading.get_ident())
        return original(report)
    monkeypatch.setattr(api, 'write_compressed_report', traced)
    runtime, hass, _, _, _ = await create_download(api)
    try:
        assert workers and workers[0] != event_thread
    finally:
        await api._close_downloads(hass)


@pytest.mark.asyncio
async def test_streamed_handler_requires_admin_same_user_and_loaded_entry(api, http_view):
    runtime, hass, connection, answer, token = await create_download(api)
    try:
        assert http_view.requires_auth is True
        for user in (None, SimpleNamespace(id=connection.user.id, is_admin=False)):
            with pytest.raises(Forbidden):
                await http_view.get(Request(hass, user), token)
        with pytest.raises(NotFound):
            await http_view.get(Request(hass, SimpleNamespace(id='other_admin', is_admin=True)), token)
        response = await http_view.get(Request(hass, connection.user), token)
        assert response.headers['Cache-Control'] == 'no-store, private'
        assert response.headers['Content-Type'] == 'application/gzip'
        assert 'Content-Encoding' not in response.headers
        assert answer['filename'] in response.headers['Content-Disposition']
        assert response.path == hass.data[api._DOWNLOADS]['files'][token]['path']
        runtime._closed = True
        with pytest.raises(Gone):
            await http_view.get(Request(hass, connection.user), token)
        assert not Path(response.path).exists()
    finally:
        await api._close_downloads(hass)


@pytest.mark.asyncio
async def test_same_entry_reloaded_runtime_cannot_serve_old_snapshot(api, http_view):
    runtime, hass, connection, _, token = await create_download(api)
    old_path = hass.data[api._DOWNLOADS]['files'][token]['path']
    runtime.entry.runtime_data = SimpleNamespace(_closed=False)
    with pytest.raises(Gone):
        await http_view.get(Request(hass, connection.user), token)
    assert not Path(old_path).exists()


@pytest.mark.asyncio
async def test_browser_cleanup_requires_same_admin_and_frees_export_slot(api, http_view):
    runtime, hass, connection, _, token = await create_download(api)
    path = hass.data[api._DOWNLOADS]['files'][token]['path']
    try:
        with pytest.raises(Forbidden):
            await http_view.delete(Request(hass, SimpleNamespace(id=connection.user.id, is_admin=False)), token)
        with pytest.raises(NotFound):
            await http_view.delete(Request(hass, SimpleNamespace(id='other', is_admin=True)), token)
        assert Path(path).exists()
        response = await http_view.delete(Request(hass, connection.user), token)
        assert response.status == 204
        assert not Path(path).exists() and not hass.data[api._DOWNLOADS]['files']
    finally:
        await api._close_downloads(hass)


@pytest.mark.asyncio
async def test_expired_link_and_path_traversal_rejected(api, http_view):
    _, hass, connection, _, token = await create_download(api)
    item = hass.data[api._DOWNLOADS]['files'][token]
    path = item['path']
    with pytest.raises(NotFound):
        await http_view.get(Request(hass, connection.user), '../secrets.yaml')
    item['expires_at'] = time.monotonic() - 1
    with pytest.raises(Gone):
        await http_view.get(Request(hass, connection.user), token)
    assert not Path(path).exists() and token not in hass.data[api._DOWNLOADS]['files']


@pytest.mark.asyncio
async def test_background_expiry_removes_file_without_browser_download(api, monkeypatch):
    monkeypatch.setattr(api, 'DOWNLOAD_TTL_S', .02)
    _, hass, _, _, token = await create_download(api)
    path = hass.data[api._DOWNLOADS]['files'][token]['path']
    for _ in range(50):
        if not Path(path).exists():
            break
        await asyncio.sleep(.002)
    assert not Path(path).exists() and token not in hass.data[api._DOWNLOADS]['files']


@pytest.mark.asyncio
async def test_two_reports_bound_disk_and_preserve_existing_downloads(api):
    runtime, hass, connection, _, token = await create_download(api)
    path = hass.data[api._DOWNLOADS]['files'][token]['path']
    results, errors = [], []
    connection.send_result = lambda _, result: results.append(result)
    connection.send_error = lambda _, code, message: errors.append(code)
    try:
        runtime.analysis.last_export = 0
        await api.websocket_analysis_export(hass, connection, {'id': 2, 'config_entry_id': 'test', 'download': True})
        runtime.analysis.last_export = 0
        await api.websocket_analysis_export(hass, connection, {'id': 3, 'config_entry_id': 'test', 'download': True})
        assert len(results) == 1 and errors == ['busy'] and Path(path).exists()
        assert len(hass.data[api._DOWNLOADS]['files']) == 2
        assert hass.data[api._DOWNLOADS]['preparing'] == 0
    finally:
        await api._close_downloads(hass)


@pytest.mark.asyncio
async def test_worker_failure_releases_reservation_and_keeps_commands_untouched(api, monkeypatch):
    runtime, hass, connection, results, errors = download_context()
    before = list(hass.services.calls)
    monkeypatch.setattr(api, 'write_compressed_report', lambda _: (_ for _ in ()).throw(OSError('disk full')))
    await api.websocket_analysis_export(hass, connection, {'id': 1, 'config_entry_id': 'test', 'download': True})
    assert errors == ['export_failed'] and not results
    assert hass.data[api._DOWNLOADS] == {'files': {}, 'preparing': 0}
    assert not runtime.analysis.exporting and hass.services.calls == before


@pytest.mark.asyncio
async def test_close_during_generation_discards_artifact(api, monkeypatch):
    runtime, hass, connection, results, errors = download_context()
    paths = []
    original = api.write_compressed_report
    def close_after_write(report):
        artifact = original(report)
        paths.append(artifact['path'])
        runtime._closed = True
        return artifact
    monkeypatch.setattr(api, 'write_compressed_report', close_after_write)
    await api.websocket_analysis_export(hass, connection, {'id': 1, 'config_entry_id': 'test', 'download': True})
    assert errors == ['not_loaded'] and not results
    assert paths and all(not Path(path).exists() for path in paths)
    assert not runtime.analysis.exporting and hass.data[api._DOWNLOADS]['preparing'] == 0


@pytest.mark.asyncio
async def test_cancelled_browser_request_reaps_worker_file(api, monkeypatch):
    runtime, hass, connection, results, errors = download_context()
    entered, release = threading.Event(), threading.Event()
    original = api.write_compressed_report
    paths = []
    def waiting_writer(report):
        entered.set()
        assert release.wait(3)
        artifact = original(report)
        paths.append(artifact['path'])
        return artifact
    monkeypatch.setattr(api, 'write_compressed_report', waiting_writer)
    task = asyncio.create_task(api.websocket_analysis_export(hass, connection,
        {'id': 1, 'config_entry_id': 'test', 'download': True}))
    assert await asyncio.to_thread(entered.wait, 3)
    task.cancel(); release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not results and not errors
    assert paths and all(not Path(path).exists() for path in paths)
    assert not runtime.analysis.exporting and hass.data[api._DOWNLOADS]['preparing'] == 0


@pytest.mark.asyncio
async def test_shutdown_cleans_downloads_and_prevents_new_generation(api):
    runtime, hass, connection, _, token = await create_download(api)
    path = hass.data[api._DOWNLOADS]['files'][token]['path']
    await api._close_downloads(hass)
    runtime.analysis.last_export = 0
    errors = []
    connection.send_error = lambda _, code, message: errors.append(code)
    await api.websocket_analysis_export(hass, connection, {'id': 2, 'config_entry_id': 'test', 'download': True})
    assert errors == ['not_loaded'] and not Path(path).exists()


@pytest.mark.asyncio
@pytest.mark.parametrize('option', [None, 0, 1, 'true', [], {}])
async def test_download_option_strictly_boolean(api, option):
    _, hass, connection, results, errors = download_context()
    await api.websocket_analysis_export(hass, connection,
        {'id': 1, 'config_entry_id': 'test', 'download': option})
    assert errors == ['invalid_options'] and not results


def test_failed_json_encoding_removes_partial_private_file(monkeypatch, tmp_path):
    monkeypatch.setattr(ae.tempfile, 'tempdir', str(tmp_path))
    with pytest.raises(ValueError):
        ae.write_compressed_report({'good': list(range(500)), 'bad': float('nan')})
    assert not list(tmp_path.iterdir())


def test_new_records_stamp_collecting_release_old_records_remain_unknown():
    runtime, hass, _, _, _ = download_context()
    wall = time.time()
    runtime.analysis.samples.append({'ts': wall - 10, 'grid_w': -1000, 'pv_w': 2000})
    runtime.analysis.events.append({'ts': wall - 9, 'kind': 'old', 'message': 'Historical event'})
    runtime.analysis.capture(1)
    runtime.analysis.event('new', 'Current event')
    report = runtime.analysis.build(include_names=True)
    assert report['release'] == VERSION
    for section in ('samples', 'events'):
        assert report['telemetry'][section][0]['release'] == 'unknown'
        assert report['telemetry'][section][-1]['release'] == VERSION
    assert report['telemetry']['fast'][-1]['release'] == VERSION
    assert all(item['release'] == VERSION for item in report['telemetry']['changes'])
    assert 'release' not in runtime.analysis.samples[0]
    assert 'release' not in runtime.analysis.events[0]


def test_sg_execution_reason_retained_in_samples_and_fast_trace():
    runtime, _, _, _, _ = download_context()
    original = runtime.sg_boost.overview
    runtime.sg_boost.overview = lambda: {**original(), 'reason': 'Wacht op stabiel zonneoverschot', 'wait_s': 35, 'requested': False}
    runtime.analysis.capture(1)
    for rows in (runtime.analysis.samples, runtime.analysis.fast):
        assert rows[-1]['sg_boost']['wait_s'] == 35
        assert rows[-1]['sg_boost']['requested'] is False
        assert rows[-1]['sg_boost']['reason'] == 'Wacht op stabiel zonneoverschot'


def test_registration_adds_one_authenticated_route_and_shutdown_cleanup(api, http_view, monkeypatch):
    runtime, hass, _, _, _ = download_context()
    views, listeners = [], []
    hass.http = SimpleNamespace(register_view=views.append)
    hass.bus = SimpleNamespace(async_listen_once=lambda event, listener: listeners.append((event, listener)))
    monkeypatch.setattr(api, 'analysis_download_view', lambda: http_view)
    api.async_register_analysis_api(hass)
    api.async_register_analysis_api(hass)
    assert hass.registered == [api.websocket_analysis_export, api.websocket_analysis_feedback]
    assert views == [http_view]
    assert len(listeners) == 1 and listeners[0][0] == 'homeassistant_stop'
    assert http_view.url == '/api/solar_pilot/analysis/{token}'
