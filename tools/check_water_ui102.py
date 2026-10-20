"""Real Chromium coverage diagnostics with fictional sources and no writes.

The beta101 water gate remains separate. Build the example before this gate.
"""
import os
from pathlib import Path
import shutil
import sys

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from test_water_ui102 import diagnostic_snapshot  # noqa: E402
from test_water_ui101 import water_day  # noqa: E402

output = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/solarpilot-browser-tests')
output.mkdir(parents=True, exist_ok=True)
browser_path = os.environ.get('SOLARPILOT_CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('google-chrome')
cases = {'current': diagnostic_snapshot(), 'stale_flow': diagnostic_snapshot(flow_age=1200),
         'stale_leak': diagnostic_snapshot(leak_age=1200),
         'both_stale': diagnostic_snapshot(flow_age=1200, leak_age=1200),
         'flow_only': diagnostic_snapshot(leak_configured=False),
         'volume_only': diagnostic_snapshot(flow_configured=False, leak_configured=False),
         'disabled': diagnostic_snapshot(enabled=False)}
errors = []


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=browser_path, headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1280, 'height': 1000}, device_scale_factor=1, locale='nl-BE')
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_content((ROOT / 'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'), wait_until='load')
    page.wait_for_selector('solar-pilot-card >> h1')
    page.evaluate("""payload=>{
      const c=document.querySelector('solar-pilot-card');window.demoCard=c;
      window.waterCases=payload.cases;window.waterDay=payload.day;window.waterReads=[];
      window.controlWrites=[];window.nativeHistoryViews=[];
      c.addEventListener('hass-more-info',e=>nativeHistoryViews.push(e.detail));
      window.waterRead=async m=>{waterReads.push(m);if(m.config_entry_id!=='fictional-water-entry')throw Error('Wrong entry');
        if(m.type==='solar_pilot/water_history')return structuredClone(waterDay);
        if(m.type==='solar_pilot/source_history'&&m.kind==='water')return {schema:1,read_only:true,
          scope:'current_configured_sources',kind:'water',name:'Fictieve waterbronnen',sources:[
            {role:'flow_entity',label:'Stroming',entity_id:'sensor.fictional_water_flow'},
            {role:'leak_entity',label:'Native lekmelding',entity_id:'binary_sensor.fictional_water_leak'}]};
        throw Error('Unexpected read '+m.type);};
      window.applyWater=name=>{const a=structuredClone(c._last.attributes);a.config_entry_id='fictional-water-entry';
        a.integration_version='1.0.0-beta.102';a.water=structuredClone(waterCases[name]);
        c.hass={...c._hass,user:{id:'fictional-water-user',is_admin:true},callWS:waterRead,
          callService:async(...args)=>controlWrites.push(args),states:{...c._hass.states,[c._entity]:{state:'ready',attributes:a}}};};
      applyWater('both_stale');
    }""", {'cases': cases, 'day': water_day()})
    card = page.locator('solar-pilot-card')
    assert 'waterbewaking mist actuele' in card.locator('[data-water-diagnostic-summary]').inner_text()
    card.locator('[data-action=view][data-value=water]').first.click()
    panel = card.locator('[data-water-panel]')
    diagnostic = panel.locator('[data-water-diagnostic]')

    for width in (320, 390):
        page.set_viewport_size({'width': width, 'height': 844})
        page.evaluate("applyWater('both_stale')")
        assert diagnostic.get_attribute('data-diagnostic-state') == 'unavailable'
        assert diagnostic.locator('[data-current=false]').count() == 2
        assert panel.locator(':scope > .summarygrid > .tile').nth(1).locator('strong').inner_text() == '—'
        assert panel.locator(':scope > .summarygrid > .tile').nth(2).locator('strong').inner_text() == 'Onbekend'
        assert 'Langdurige stroming kan nu niet betrouwbaar worden bewaakt' in diagnostic.inner_text()
        assert 'Dit bewijst niet dat er geen lek is' in diagnostic.inner_text()
        assert page.evaluate("()=>{const w=demoCard._last.attributes.water,d=demoCard._waterDiagnostic({water:w});return d.flow_monitoring.reported_at===w.flow.reported_at&&d.flow_monitoring.reported_at!==w.volume.reported_at;}")
        diagnostic.evaluate('el=>el.scrollIntoView({block:"start"})')
        assert diagnostic.evaluate('el=>el.scrollWidth<=el.clientWidth+1'), width
        page.screenshot(path=str(output / f'SolarPilot-beta102-water-coverage-{width}.png'))
        help_details = diagnostic.locator('details')
        help_details.locator('summary').focus()
        page.keyboard.press('Enter')
        assert help_details.evaluate('el=>el.open')
        assert 'als de bron MQTT gebruikt' in help_details.inner_text()
        assert 'force_update' in help_details.inner_text() and 'wijzigt geen broninstellingen' in help_details.inner_text()
        assert 'brokerberichten niet gecontroleerd' in help_details.inner_text()
        assert help_details.locator('a').get_attribute('href') == 'https://www.home-assistant.io/integrations/mqtt/#the-last-reported-state-attribute'
        assert 'noopener' in help_details.locator('a').get_attribute('rel')
        # A current counter update neither replaces old flow/off proof nor closes the user's explanation.
        page.evaluate("""()=>{const c=demoCard,a=structuredClone(c._last.attributes),now=Date.now()/1000;
          a.water.volume.reported_at=now;a.water.volume.valid_until=now+300;a.water.volume.value+=1;
          c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'ready',attributes:a}}};}""")
        assert diagnostic.get_attribute('data-diagnostic-state') == 'unavailable'
        assert diagnostic.locator('[data-current=false]').count() == 2
        assert help_details.evaluate('el=>el.open')
        page.keyboard.press('Enter')
        assert not help_details.evaluate('el=>el.open')

    for name, state, currents in [('current', 'current', 2), ('stale_flow', 'incomplete', 1),
                                  ('stale_leak', 'incomplete', 1), ('flow_only', 'current', 1),
                                  ('volume_only', 'not_configured', 0), ('disabled', 'disabled', 0)]:
        page.evaluate('applyWater', name)
        assert diagnostic.get_attribute('data-diagnostic-state') == state, name
        assert diagnostic.locator('[data-current=true]').count() == currents, name
        if name == 'current':
            assert panel.locator(':scope > .summarygrid > .tile').nth(1).locator('strong').inner_text() == '0 L/min'
            assert panel.locator(':scope > .summarygrid > .tile').nth(2).locator('strong').inner_text() == 'Geen lek gemeld'
            assert 'vereiste stromingsduur moet nog afzonderlijk worden bevestigd' in diagnostic.inner_text()
        if name == 'flow_only':
            assert 'Niet gekoppeld' in diagnostic.locator('[data-water-monitor-channel=native-leak]').inner_text()
            assert 'geen lek is' in diagnostic.locator('[data-water-monitor-channel=native-leak]').inner_text()
        if name == 'disabled':
            assert diagnostic.locator('details').count() == 0

    # A cached ready flag expires from the original flow timestamp at render time.
    page.evaluate("""()=>{applyWater('current');const c=demoCard,a=structuredClone(c._last.attributes),now=Date.now()/1000;
      a.water.flow.reported_at=now-299.8;a.water.flow.valid_until=now+.2;
      a.water.diagnostic.flow_monitoring.reported_at=a.water.flow.reported_at;
      a.water.diagnostic.flow_monitoring.valid_until=a.water.flow.valid_until;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'ready',attributes:a}}};}""")
    assert diagnostic.get_attribute('data-diagnostic-state') == 'current'
    page.wait_for_timeout(300)
    page.evaluate('demoCard._refreshObservationDisplay()')
    assert diagnostic.get_attribute('data-diagnostic-state') == 'incomplete'
    assert diagnostic.locator('[data-water-monitor-channel=flow]').get_attribute('data-current') == 'false'
    assert diagnostic.locator('[data-water-monitor-channel=native-leak]').get_attribute('data-current') == 'true'

    # Malformed diagnostics remain visible errors; source values are not fabricated.
    page.evaluate("""()=>{applyWater('current');const c=demoCard,a=structuredClone(c._last.attributes);a.water.diagnostic.hidden=true;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'ready',attributes:a}}};}""")
    assert 'waterdiagnose ontbreekt of is ongeldig' in diagnostic.inner_text()
    page.evaluate("""()=>{applyWater('stale_flow');const c=demoCard,a=structuredClone(c._last.attributes);
      a.water.diagnostic.summary='<img src=x onerror=window.injected=true>';a.water.diagnostic.note='<script>window.injected=true</script>';
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'ready',attributes:a}}};}""")
    assert diagnostic.locator('img,script').count() == 0 and not page.evaluate('window.injected||false')
    assert '<img src=x' in diagnostic.inner_text()

    # Current coverage cannot overwrite the retained historical cursor or its source dates.
    page.evaluate("applyWater('both_stale')")
    card.locator('[data-action=water_history]').click()
    host = card.locator('[data-water-history-dialog]')
    page.wait_for_function('demoCard._waterHistoryDialog?._data!==null&&!demoCard._waterHistoryDialog._inflight')
    client = page.context.new_cdp_session(page)
    for width in (320, 390):
        page.set_viewport_size({'width': width, 'height': 844})
        lane = host.locator('[data-history-scrub=water-flow]')
        lane.evaluate('el=>{const s=demoCard._waterHistoryDialog._scroll;s.scrollTop+=el.getBoundingClientRect().bottom-s.getBoundingClientRect().bottom+40;}')
        box = lane.bounding_box()
        x, y = box['x']+box['width']*(9*3600+12*60)/86400, box['y']+box['height']/2
        client.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x-15, 'y': y, 'id': 1}]})
        client.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x, 'y': y, 'id': 1}]})
        assert page.evaluate('!!demoCard._waterHistoryDialog._scrubPointer?.drag')
        page.evaluate('demoCard._waterHistoryDialog._renderData()')
        client.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        assert 'Meetpunt 09:12:00 GMT+2' in host.locator('[data-water-readout]').inner_text()
        assert '6 L/min' in host.locator('[data-water-readout]').inner_text()
        assert lane.evaluate('''el=>{const d=demoCard._waterHistoryDialog,r=el.getBoundingClientRect(),q=d._body.querySelector('[data-water-readout]').getBoundingClientRect();
          return r.top>=q.bottom+6&&d.shadowRoot.elementFromPoint(r.left+r.width*.5,r.top+r.height/2)?.closest('[data-history-scrub]')===el;}''')
        page.screenshot(path=str(output / f'SolarPilot-beta102-water-history-{width}.png'))
        lane.focus()
        page.keyboard.press('Home')
        assert 'Waarden bij deze tijd zijn onbekend' in host.locator('[data-water-readout]').inner_text()
        host.locator('[data-water-step="1"]').click()
    client.detach()
    assert 'voortschrijdende vensters van maximaal 30 minuten' in host.locator('.water-correlations').inner_text()
    assert 'gemelde dalingen overlappen elkaar niet' in host.locator('.water-correlations').inner_text()
    assert 'geen bewijs van warmwatertap' in host.locator('.water-correlations').inner_text()
    page.evaluate("""()=>{const c=demoCard,d=c._waterHistoryDialog;window.waterModal=d._dialog;
      for(let n=0;n<20;n++){const a=structuredClone(c._last.attributes);a.water.volume.value+=1;
        c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'ready',attributes:a}}};}}""")
    assert page.evaluate('demoCard._waterHistoryDialog._dialog===waterModal&&waterModal.open')
    assert '6 L/min' in host.locator('[data-water-readout]').inner_text()
    page.evaluate("""()=>{const d=demoCard._waterHistoryDialog;d._hass={...d._hass,callWS:m=>new Promise(resolve=>window.lateWater=resolve)};d._fetch(true);d.close();lateWater(structuredClone(waterDay));}""")
    page.wait_for_timeout(30)
    assert not host.locator('dialog').is_visible() and page.evaluate('demoCard._waterHistoryDialog._timer===null')
    card.locator('[data-action=water_history]').click()
    page.wait_for_function('demoCard._waterHistoryDialog._data!==null&&!demoCard._waterHistoryDialog._inflight')
    host.locator('[data-action=source-history]').click()
    source = card.locator('[data-source-history-dialog]')
    page.wait_for_function("demoCard._sourceHistoryDialog?._data?.kind==='water'")
    assert not host.locator('dialog').is_visible()
    source.locator('[data-source-index="0"]').click()
    page.wait_for_function('nativeHistoryViews.length===1')
    assert page.evaluate('nativeHistoryViews[0]') == {'entityId': 'sensor.fictional_water_flow', 'view': 'history'}
    assert page.evaluate("waterReads.filter(m=>m.type==='solar_pilot/source_history').length===2")
    assert page.evaluate("waterReads.every(m=>m.type==='solar_pilot/water_history'?Object.keys(m).every(k=>['type','config_entry_id','date'].includes(k)):m.type==='solar_pilot/source_history'&&m.kind==='water'&&!('item_id'in m))")
    assert page.evaluate('controlWrites.length') == 0
    assert not errors, errors
    browser.close()

print('Water102 browser checks passed: independent channel coverage at320/390; stale zero/off never renewed by volume; original times; conditional MQTT help; closed-schema/XSS; expiry; retained touch/keyboard cursor; lifecycle; revalidated native HA history; zero control writes. All readings are fictitious.')
