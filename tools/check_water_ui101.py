"""Exercise actual water UI with fictitious retained reports and zero device writes.

Run build_example.py first. Chromium/Playwright only; no external API or HA site.
"""
from copy import deepcopy
import os
from pathlib import Path
import shutil
import sys

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'tests'))
from test_water_ui101 import water_day  # noqa: E402

output = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/solarpilot-browser-tests')
output.mkdir(parents=True, exist_ok=True)
browser_path = os.environ.get('SOLARPILOT_CHROMIUM_PATH') or shutil.which('chromium') or shutil.which('google-chrome')
data = water_day()
original = deepcopy(data['points'][0])
data['points'] = []
for minute in (-2, -1, 0):
    point = deepcopy(original)
    point['captured_at'] += minute*60
    for reading in [point['flow'], point['volume'], point['native_leak'],
                    *point['context']['boiler'].values(), point['context']['dishwasher']]:
        reading['reported_at'] += minute*60
        reading['valid_until'] += minute*60
    data['points'].append(point)
previous = deepcopy(data)
previous.update(date='2026-10-18', day_start=data['day_start']-86400,
                day_end=data['day_end']-86400, volume_l=0, points=[], intervals=[],
                events=[], correlations={'read_only': True, 'scope': 'household_water',
                                         'boiler_drops': [], 'dishwasher_intervals': []})
data['days'].append({'date': '2026-10-18', 'volume_l': 0})
previous['days'] = deepcopy(data['days'])
errors = []


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=browser_path, headless=True, args=['--no-sandbox'])
    page = browser.new_page(viewport={'width': 1280, 'height': 1000}, device_scale_factor=1, locale='nl-BE')
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.set_content((ROOT / 'SolarPilot-voorbeeld.html').read_text(encoding='utf-8'), wait_until='load')
    page.wait_for_selector('solar-pilot-card >> h1')
    page.evaluate("""fixtures=>{
      const c=document.querySelector('solar-pilot-card');window.demoCard=c;
      window.waterFixtures=fixtures;window.waterReads=[];window.controlWrites=[];window.nativeHistoryViews=[];
      c.addEventListener('hass-more-info',e=>nativeHistoryViews.push(e.detail));
      const a=structuredClone(c._last.attributes),now=Date.now()/1000;
      const source=(value,unit)=>({value,unit,reported_at:now-5,valid_until:now+295,fresh:true,reason:'measured'});
      a.config_entry_id='fictional-water-entry';a.integration_version='1.0.0-beta.101';a.water={schema:1,read_only:true,enabled:true,configured:true,
        flow:source(0,'L/min'),volume:source(12345.6,'L'),native_leak:source(false,null),
        today:{date:'2026-10-19',volume_l:3,volume_covered_s:60,complete:false},
        suspicion:{state:'clear',elapsed_s:0,required_s:3600,threshold_l_min:.1,last_reported_at:now-5},revision:4};
      window.waterRead=async m=>{waterReads.push(m);if(m.config_entry_id!=='fictional-water-entry')throw Error('Wrong entry');
        if(m.type==='solar_pilot/water_history')return structuredClone(waterFixtures[m.date||'2026-10-19']);
        if(m.type==='solar_pilot/source_history'&&m.kind==='water')return {schema:1,read_only:true,
          scope:'current_configured_sources',kind:'water',name:'Fictieve watermeter',sources:[
            {role:'flow_entity',label:'Stroming',entity_id:'sensor.fictional_water_flow'},
            {role:'volume_entity',label:'Totale meterstand',entity_id:'sensor.fictional_water_total'},
            {role:'leak_entity',label:'Native lekmelding',entity_id:'binary_sensor.fictional_water_leak'}]};
        throw Error('Unexpected request '+m.type);};
      c.hass={...c._hass,user:{id:'fictional-water-user',is_admin:true},callWS:waterRead,
        callService:async(...args)=>controlWrites.push(args),states:{...c._hass.states,
          [c._entity]:{state:'ready',attributes:a}}};
    }""", {'2026-10-19': data, '2026-10-18': previous})
    card = page.locator('solar-pilot-card')
    assert '0 L/min' in card.locator('[data-water-summary]').inner_text()
    card.locator('[data-action=view][data-value=water]').first.click()
    assert 'Geen lek gemeld' in card.locator('[data-water-panel]').inner_text()
    assert 'onvolledig dagbeeld' in card.locator('[data-water-panel]').inner_text()
    assert page.evaluate('waterReads.length') == 0
    # Expired false is unknown, and native true remains separate from a pattern advisory.
    page.evaluate("""()=>{const c=demoCard,a=structuredClone(c._last.attributes);a.water.native_leak.valid_until=Date.now()/1000-1;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'ready',attributes:a}}};}""")
    assert 'Onbekend' in card.locator('[data-water-panel]').inner_text()
    page.evaluate("""()=>{const c=demoCard,a=structuredClone(c._last.attributes),w=a.water;
      w.native_leak.value=true;w.native_leak.valid_until=Date.now()/1000+200;w.flow.value=.2;
      w.suspicion={state:'suspected',elapsed_s:3600,required_s:3600,threshold_l_min:.1,last_reported_at:w.flow.reported_at};
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'ready',attributes:a}}};}""")
    assert 'watermeter meldt een mogelijk lek' in card.locator('[data-water-panel]').inner_text()
    assert 'Langdurige stroming waargenomen' in card.locator('[data-water-panel]').inner_text()
    assert 'geen bewezen lek' in card.locator('[data-water-panel]').inner_text()
    page.set_viewport_size({'width': 390, 'height': 844})
    card.locator('[data-water-panel]').evaluate('el=>el.scrollIntoView({block:"start"})')
    page.screenshot(path=str(output / 'SolarPilot-beta101-water-overview-390.png'))
    card.locator('[data-action=water_history]').click()
    host = card.locator('[data-water-history-dialog]')
    page.wait_for_function('demoCard._waterHistoryDialog?._data!==null && !demoCard._waterHistoryDialog._inflight')
    assert host.locator('[data-water-total]').inner_text() == '3 L'
    assert host.locator('[data-history-scrub]').count() == 4
    assert host.locator('.day').count() == 7
    assert page.evaluate("waterReads.every(m=>m.type==='solar_pilot/water_history' && Object.keys(m).every(k=>['type','config_entry_id','date'].includes(k)))")
    client = page.context.new_cdp_session(page)
    for width in (320, 390):
        page.set_viewport_size({'width': width, 'height': 844})
        page.evaluate('()=>{const d=demoCard._waterHistoryDialog;d._resetScrub();d._syncScrub();}')
        for index, lane in enumerate(host.locator('[data-history-scrub]').all()):
            lane.evaluate('el=>{const d=demoCard._waterHistoryDialog,s=d._scroll,r=el.getBoundingClientRect();s.scrollTop+=r.bottom-s.getBoundingClientRect().bottom+40;}')
            box = lane.bounding_box()
            x = box['x'] + box['width']*(9*3600+12*60)/86400
            y = box['y'] + box['height']/2
            client.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x-16, 'y': y, 'id': 1}]})
            client.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x, 'y': y, 'id': 1}]})
            assert page.evaluate('!!demoCard._waterHistoryDialog._scrubPointer?.drag'), (width, index, 'actual horizontal pointer capture')
            assert 'Meetpunt 09:12:00 GMT+2' in host.locator('[data-water-readout]').inner_text()
            assert '49 °C' in host.locator('[data-water-readout]').inner_text()
            page.evaluate('demoCard._waterHistoryDialog._renderData()')
            client.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
            assert page.evaluate('demoCard._waterHistoryDialog._scrubPointer===null')
            geometry = lane.evaluate('''el=>{const d=demoCard._waterHistoryDialog,r=el.getBoundingClientRect(),
              s=d._scroll.getBoundingClientRect(),q=d._body.querySelector('[data-water-readout]').getBoundingClientRect(),
              hit=d.shadowRoot.elementFromPoint(r.left+r.width*.3,r.top+r.height/2);
              return {uncovered:r.top>=q.bottom+6,heading:el.previousElementSibling.getBoundingClientRect().top>=q.bottom+6,visible:r.top>=s.top&&r.bottom<=s.bottom,
                hit:hit?.closest('[data-history-scrub]')===el};}''')
            assert all(geometry.values()), (width, index, geometry)
        page.evaluate("()=>{const d=demoCard._waterHistoryDialog;d._waterActiveLane='water-flow';d._keepWaterScrubVisible();}")
        page.screenshot(path=str(output / f'SolarPilot-beta101-water-history-active-{width}.png'))
        lane = host.locator('[data-history-scrub=water-flow]')
        lane.focus()
        page.keyboard.press('Home')
        assert 'Waarden bij deze tijd zijn onbekend' in host.locator('[data-water-readout]').inner_text()
        assert '49 °C' not in host.locator('[data-water-readout]').inner_text()
        host.locator('[data-water-step="1"]').click()
        assert 'Meetpunt 09:10:00 GMT+2' in host.locator('[data-water-readout]').inner_text()
        details = host.locator('[data-water-readout] details')
        details.locator('summary').focus()
        page.keyboard.press('Enter')
        assert details.evaluate('el=>el.open') and 'Flowrapport' in details.inner_text()
        page.evaluate('demoCard._waterHistoryDialog._renderData()')
        assert details.evaluate('el=>el.open'), 'same-day refresh preserves original proof disclosure'
        page.keyboard.press('Enter')
        assert not details.evaluate('el=>el.open')
        assert host.locator('dialog').evaluate('el=>el.scrollWidth<=el.clientWidth+1'), width
    # Actual native vertical scroll remains possible; horizontal gesture capture is separate.
    lane = host.locator('[data-history-scrub=water-flow]')
    lane.evaluate('el=>{const d=demoCard._waterHistoryDialog,s=d._scroll;s.scrollTop+=el.getBoundingClientRect().bottom-s.getBoundingClientRect().bottom+50;}')
    box = lane.bounding_box()
    before = page.evaluate('demoCard._waterHistoryDialog._scroll.scrollTop')
    x, y = box['x']+box['width']*.6, box['y']+box['height']/2
    client.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x, 'y': y, 'id': 1}]})
    for dy in (20, 50, 90):
        client.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x, 'y': y-dy, 'id': 1}]})
    client.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
    page.wait_for_timeout(120)
    assert page.evaluate('demoCard._waterHistoryDialog._scroll.scrollTop') > before+10
    assert page.evaluate('demoCard._waterHistoryDialog._scrubPointer===null')
    client.detach()
    # Recorded comparisons remain household context and expand independently.
    correlation = host.locator('[data-water-key^="boiler:"]')
    correlation.locator('summary').click()
    assert '52 °C → 49 °C' in correlation.inner_text()
    assert '3 L huishoudelijke tellerstijging' in correlation.inner_text()
    assert 'geen bewijs van warmwatertap' in host.locator('.water-correlations').inner_text()
    host.locator('[data-action=range][data-value="30"]').click()
    assert host.locator('.day').count() == 30
    assert correlation.evaluate('el=>el.open')
    host.locator('[data-action=prev]').click()
    page.wait_for_function("demoCard._waterHistoryDialog._data.date==='2026-10-18'")
    assert host.locator('[data-water-total]').inner_text() == '0 L'
    assert not host.locator('[data-water-key^="boiler:"]').evaluate('el=>el.open')
    page.evaluate("""()=>{const d=demoCard._waterHistoryDialog;d._hass={...d._hass,callWS:m=>new Promise(resolve=>
      setTimeout(()=>resolve(structuredClone(waterFixtures[m.date||'2026-10-19'])),m.date==='2026-10-18'?150:5))};
      d._selectDay('2026-10-18');d._selectDay('2026-10-19');}""")
    page.wait_for_timeout(200)
    assert host.locator('input').input_value() == '2026-10-19'
    page.evaluate('demoCard._waterHistoryDialog._hass={...demoCard._hass,callWS:waterRead}')
    # Live telemetry never replaces the real modal DOM or its selected historical values.
    page.evaluate("""()=>{const d=demoCard._waterHistoryDialog;window.waterModal=d._dialog;d._setScrub(d._data.points[0].captured_at);
      for(let n=0;n<40;n++){const c=demoCard,a=structuredClone(c._last.attributes);a.water.flow.value=9999+n;
        c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'ready',attributes:a}}};}}""")
    assert page.evaluate('demoCard._waterHistoryDialog._dialog===waterModal && waterModal.open')
    assert '6 L/min' in host.locator('[data-water-readout]').inner_text()
    assert '9999' not in host.locator('[data-water-readout]').inner_text()
    page.evaluate("async()=>{waterFixtures['2026-10-19'].coverage.note='<img src=x onerror=window.injected=true>';await demoCard._waterHistoryDialog._fetch(true);}")
    assert host.locator('img').count() == 0 and not page.evaluate('window.injected||false')
    # The normal source chooser opens only an authorized current water role in native history.
    host.locator('[data-action=source-history]').evaluate('el=>{const s=demoCard._waterHistoryDialog._scroll;s.scrollTop+=el.getBoundingClientRect().bottom-s.getBoundingClientRect().bottom+30;}')
    host.locator('[data-action=source-history]').click()
    source = card.locator('[data-source-history-dialog]')
    page.wait_for_function("demoCard._sourceHistoryDialog?._data?.kind==='water'")
    assert not host.locator('dialog').is_visible()
    assert source.locator('a').first.get_attribute('href') == '/history?entity_id=sensor.fictional_water_flow'
    source.locator('[data-source-index="0"]').click()
    page.wait_for_function('nativeHistoryViews.length===1')
    assert page.evaluate('nativeHistoryViews[0]') == {'entityId': 'sensor.fictional_water_flow', 'view': 'history'}
    assert page.evaluate("waterReads.filter(m=>m.type==='solar_pilot/source_history').every(m=>m.kind==='water'&&!('item_id' in m)&&!('source' in m))")
    card.locator('[data-action=water_history]').click()
    page.wait_for_function('demoCard._waterHistoryDialog._data!==null')
    page.keyboard.press('Escape')
    page.wait_for_timeout(30)
    assert not host.locator('dialog').is_visible()
    assert page.evaluate('demoCard._waterHistoryDialog._timer===null')
    assert page.evaluate('controlWrites.length') == 0
    assert not errors, errors
    browser.close()

print('Water browser checks passed: all four actual-point lanes touch/keyboard; free active cursor at320/390; native vertical scroll; original proofs;30days; late-day replies; telemetry stability; household-only comparisons; authorized native source history; XSS; close cleanup; zero control writes. All readings are fictitious.')
