"""Admin-only analysis preparation and private streamed local downloads."""
from __future__ import annotations
import asyncio
import os
import secrets
import time
from homeassistant.components import websocket_api
from homeassistant.components.websocket_api.messages import BASE_COMMAND_MESSAGE_SCHEMA
from homeassistant.core import callback
from .const import DOMAIN
from .analysis_export import serialize_report, write_compressed_report

if type(BASE_COMMAND_MESSAGE_SCHEMA).__module__.split('.', 1)[0] == 'probatio':
    import probatio as vol
else:
    import voluptuous as vol
COMMAND = 'solar_pilot/analysis_export'
_REGISTERED = DOMAIN + '_analysis_api'
_DOWNLOADS = DOMAIN + '_analysis_downloads'
DOWNLOAD_URL = '/api/solar_pilot/analysis/{token}'
DOWNLOAD_TTL_S = 600
MAX_READY_DOWNLOADS = 2


def _runtime(hass, entry_id):
    entry = hass.config_entries.async_get_entry(entry_id)
    runtime = getattr(entry, 'runtime_data', None) if entry is not None and entry.domain == DOMAIN else None
    return runtime if runtime is not None and not runtime._closed else None


async def _worker(hass, call):
    execute = getattr(hass, 'async_add_executor_job', None)
    return await execute(call) if execute else await asyncio.to_thread(call)


def _delete(path):
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


async def _remove_download(hass, token):
    item = hass.data.get(_DOWNLOADS, {}).get('files', {}).pop(token, None)
    if item is not None:
        item['timer'].cancel()
        await _worker(hass, lambda: _delete(item['path']))


async def _close_downloads(hass):
    hass.data.setdefault(_DOWNLOADS, {'files': {}, 'preparing': 0})['closed'] = True
    for token in list(hass.data.get(_DOWNLOADS, {}).get('files', {})):
        await _remove_download(hass, token)


def _expire_download(hass, token):
    """Scheduled even if the browser closes and never fetches the download."""
    create = getattr(hass, 'async_create_task', asyncio.create_task)
    create(_remove_download(hass, token))


def analysis_download_view():
    """Use HA's normal bearer authentication; random URLs grant no access."""
    from aiohttp import web
    from homeassistant.components.http.view import HomeAssistantView

    class AnalysisDownloadView(HomeAssistantView):
        url = DOWNLOAD_URL
        name = 'api:solar_pilot:analysis_download'
        requires_auth = True

        async def get(self, request, token):
            hass = request.app['hass']
            user = request.get('hass_user')
            if user is None or not user.is_admin:
                raise web.HTTPForbidden(text='Alleen een Home Assistant-beheerder mag deze analyse downloaden')
            item = hass.data.get(_DOWNLOADS, {}).get('files', {}).get(token)
            # The token is an identifier, never a filesystem path or a bearer
            # credential. Another administrator cannot download this report.
            if item is None or item['user_id'] != user.id:
                raise web.HTTPNotFound(text='Deze analyse-download is niet beschikbaar')
            if time.monotonic() >= item['expires_at']:
                await _remove_download(hass, token)
                raise web.HTTPGone(text='Deze analyse-download is verlopen; maak de export opnieuw')
            if _runtime(hass, item['entry_id']) is not item['runtime']:
                await _remove_download(hass, token)
                raise web.HTTPGone(text='SolarPilot is herladen; maak de export opnieuw')
            # FileResponse reads the compressed file asynchronously in bounded
            # blocks/sendfile. Do not set Content-Encoding: the saved artifact
            # is explicitly a .json.gz file, not a transparently decoded body.
            return web.FileResponse(item['path'], headers={
                'Content-Type': 'application/gzip',
                'Content-Disposition': 'attachment; filename="' + item['filename'] + '"',
                'Cache-Control': 'no-store, private',
                'X-Content-Type-Options': 'nosniff',
                'Referrer-Policy': 'no-referrer',
            })

        async def delete(self, request, token):
            """The browser releases its private file after receiving the body."""
            hass = request.app['hass']
            user = request.get('hass_user')
            if user is None or not user.is_admin:
                raise web.HTTPForbidden(text='Alleen een Home Assistant-beheerder mag deze analyse verwijderen')
            item = hass.data.get(_DOWNLOADS, {}).get('files', {}).get(token)
            if item is None or item['user_id'] != user.id:
                raise web.HTTPNotFound(text='Deze analyse-download is niet beschikbaar')
            await _remove_download(hass, token)
            return web.Response(status=204, headers={'Cache-Control': 'no-store, private'})

    return AnalysisDownloadView()

@websocket_api.websocket_command({
    vol.Required('type'): COMMAND,
    vol.Required('config_entry_id'): str,
    vol.Optional('hours'): int,
    vol.Optional('include_names'): bool,
    vol.Optional('download'): bool,
})
@websocket_api.async_response
async def websocket_analysis_export(hass, connection, msg):
    user = connection.user
    if user is None or not user.is_admin:
        connection.send_error(msg['id'], 'unauthorized', 'Alleen een Home Assistant-beheerder mag deze analyse exporteren')
        return
    hours = msg.get('hours', 24); names = msg.get('include_names', False)
    download = msg.get('download', False)
    if type(hours) is not int or hours not in (1, 24, 168) or type(names) is not bool or type(download) is not bool:
        connection.send_error(msg['id'], 'invalid_options', 'Kies 1 uur, 24 uur of 7 dagen')
        return
    r = _runtime(hass, msg['config_entry_id'])
    if r is None:
        connection.send_error(msg['id'], 'not_loaded', 'SolarPilot is niet geladen')
        return
    recorder = r.analysis
    now = time.monotonic()
    if recorder.exporting or (recorder.last_export and now-recorder.last_export < 30):
        connection.send_error(msg['id'], 'busy', 'Wacht 30 seconden tussen analyse-exports')
        return
    downloads = hass.data.setdefault(_DOWNLOADS, {'files': {}, 'preparing': 0})
    if download and downloads.get('closed'):
        connection.send_error(msg['id'], 'not_loaded', 'Home Assistant sluit af; probeer na de herstart opnieuw')
        return
    if download and (not getattr(user, 'id', None)):
        connection.send_error(msg['id'], 'unauthorized', 'Een geldige Home Assistant-beheerder is nodig voor deze download')
        return
    if download and len(downloads['files']) + downloads['preparing'] >= MAX_READY_DOWNLOADS:
        connection.send_error(msg['id'], 'busy', 'Er staan nog twee analyse-downloads klaar. Die verlopen na tien minuten; probeer daarna opnieuw.')
        return
    recorder.exporting = True
    if download:
        downloads['preparing'] += 1
    artifact = None
    try:
        async with r._lock:
            # All HA-only reads and model copies happen on the HA thread.
            raw = recorder.prepare(hours)
        # Sanitization, pseudonyms and large JSON serialization run off the event loop.
        if download:
            task = asyncio.create_task(_worker(hass, lambda: write_compressed_report(recorder.finalize(raw, names))))
            try:
                artifact = await asyncio.shield(task)
            except asyncio.CancelledError:
                # Executor work cannot be cancelled. Reap its private file
                # before releasing the reservation, rather than leaking it.
                artifact = await task
                raise
            if downloads.get('closed') or _runtime(hass, msg['config_entry_id']) is not r:
                connection.send_error(msg['id'], 'not_loaded', 'SolarPilot is herladen tijdens het exporteren; probeer opnieuw')
                return
            token = secrets.token_urlsafe(32)
            filename = 'SolarPilot-analyse-' + raw['release'] + '-' + str(hours) + 'h.json.gz'
            downloads['files'][token] = {**artifact, 'user_id': user.id, 'entry_id': msg['config_entry_id'],
                'runtime': r, 'expires_at': time.monotonic() + DOWNLOAD_TTL_S, 'filename': filename,
                'timer': asyncio.get_running_loop().call_later(DOWNLOAD_TTL_S, _expire_download, hass, token)}
            metadata = {'filename': filename, 'download_url': DOWNLOAD_URL.format(token=token),
                'media_type': 'application/gzip', 'size_bytes': artifact['size_bytes'],
                'uncompressed_bytes': artifact['uncompressed_bytes'], 'expires_in_s': DOWNLOAD_TTL_S}
            artifact = None  # The expiring download registry now owns the file.
            connection.send_result(msg['id'], metadata)
        else:
            text = await _worker(hass, lambda: serialize_report(recorder.finalize(raw, names)))
            connection.send_result(msg['id'], {'filename': 'SolarPilot-analyse-' + raw['release'] + '-' + str(hours) + 'h.json', 'content': text, 'media_type': 'application/json'})
        recorder.last_export = time.monotonic()
    except ValueError as err:
        if download:
            recorder.error = 'Analyse-export mislukt: ValueError'
            connection.send_error(msg['id'], 'export_failed', 'De analyse kon niet veilig worden opgeslagen. Er is geen geschiedenis weggelaten of apparaat bediend.')
        else:
            connection.send_error(msg['id'], 'export_too_large', str(err))
    except Exception as err:
        recorder.error = 'Export onvolledig: ' + type(err).__name__
        message = ('Onvoldoende lokale opslagruimte; de bewaarde geschiedenis blijft intact.'
                   if isinstance(err, OSError) and getattr(err, 'errno', None) == 28 else
                   'Export mislukt: ' + type(err).__name__ + '. Er zijn geen apparaten bediend.')
        connection.send_error(msg['id'], 'export_failed', message)
    finally:
        try:
            if artifact is not None:
                await _worker(hass, lambda: _delete(artifact['path']))
        finally:
            if download:
                downloads['preparing'] -= 1
            recorder.exporting = False

@callback
def async_register_analysis_api(hass):
    if hass.data.get(_REGISTERED):
        return
    websocket_api.async_register_command(hass, websocket_analysis_export)
    # HA always exposes http for the integration's frontend. Test doubles may
    # only provide the WebSocket registrar, so keep that contract independent.
    if getattr(hass, 'http', None) is not None:
        hass.http.register_view(analysis_download_view())
        async def close_downloads(_event):
            await _close_downloads(hass)
        hass.bus.async_listen_once('homeassistant_stop', close_downloads)
    hass.data[_REGISTERED] = True
