"""Exercise the real dashboard popup with explicitly fictitious read-only data.

Run tools/build_example.py first. Uses local Chromium/Playwright; no HA instance,
external network or physical device commands. Screenshot output is optional.
"""
from datetime import datetime, timedelta
import importlib.util
import os
from pathlib import Path
import shutil
import sys
from zoneinfo import ZoneInfo
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("demo_consumer_history", ROOT / "custom_components/solar_pilot/consumer_history.py")
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
history = module.ConsumerHistory("Europe/Brussels")
zone = ZoneInfo("Europe/Brussels")
start = datetime(2026, 9, 26, tzinfo=zone)
now = datetime(2026, 9, 27, 13, 30, tzinfo=zone)
cfg = {"name": "Demo-verbruiker · fictieve gegevens", "kind": "switch", "control_entity": "switch.demo_consumer"}
for minute in range(int((now-start).total_seconds()/60)+1):
    at = start + timedelta(minutes=minute)
    clock = at.strftime("%H:%M")
    on = ("09:05" <= clock < "09:50" or "10:25" <= clock < "10:50" or "12:30" <= clock < "13:40")
    if clock in ("09:05", "12:30"):
        history.command("demo", cfg, 350, "Voldoende stabiel zonneoverschot; startvertraging afgerond", at)
        history.confirm("demo")
    if clock in ("09:50", "13:40"):
        history.command("demo", cfg, 0, "Onvoldoende overschot na stopvertraging; minimumlooptijd verstreken", at)
        history.confirm("demo")
    history.observe("demo", cfg, on, at, max_gap_s=90)
    if clock == "11:00":
        history.event("demo", cfg, "Demomelding: handmatig overgenomen; geen uitschakelopdracht verzonden", at)
payloads = {day: history.detail("demo", day, now) for day in ("2026-09-26", "2026-09-27")}
for value in payloads.values():
    value["current_status"] = "Actief · fictieve voorbeeldgegevens"
    value["mode"] = "auto"
    value["time_resolution_s"] = 5

errors = []
browser_path = os.environ.get('SOLARPILOT_CHROMIUM_PATH') or shutil.which("chromium") or shutil.which("google-chrome")


def check_other_histories(page, entry, host):
    out = Path(sys.argv[1] if len(sys.argv) > 1 else '/tmp/solarpilot-browser-tests')
    out.mkdir(parents=True, exist_ok=True)
    page.evaluate('data=>{window.historyFixtures=data;}', payloads)
    page.evaluate("""()=>{const c=window.demoCard,original=window.demoRead;
      window.sourceHistoryReads=[];window.nativeHistoryViews=[];
      c.addEventListener('hass-more-info',e=>{window.nativeHistoryViews.push(e.detail);});
      window.demoRead=async m=>{if(m.type!=='solar_pilot/source_history')return original(m);
        sourceHistoryReads.push(m);if(m.config_entry_id!=='demo-entry')throw Error('Wrong source-history entry');
        const battery=m.kind==='battery',wallbox=m.kind==='wallbox',heatpump=m.kind==='heatpump';
        return {schema:1,read_only:true,scope:'current_configured_sources',kind:m.kind,
          ...(wallbox||heatpump?{}:{item_id:m.item_id}),name:battery?'Fictieve batterij':wallbox?'Fictieve Wallbox':'Fictief toestel',
          sources:heatpump?[{role:'tank_temperature_entity',label:'Boilertemperatuur',entity_id:m.source==='display_tank'?'water_heater.demo_tank':'sensor.demo_tank_temperature'},
            {role:'tank_target_entity',label:'Ingesteld boilerdoel',entity_id:m.source==='display_tank'?'water_heater.demo_tank':'number.demo_tank_target'}]:
            battery?[{role:'soc',label:'Ladingstoestand',entity_id:'sensor.demo_battery_soc'},{role:'power',label:'Gemeten vermogen',entity_id:'sensor.demo_battery_power'}]:
            wallbox?[{role:'power',label:'Laadvermogen',entity_id:'sensor.demo_wallbox_power'}]:
            [{role:'control',label:'Toestelsturing',entity_id:'switch.demo_consumer'},{role:'power',label:'Vermogensmeter',entity_id:'sensor.demo_consumer_power'}],note:'Alleen huidige koppelingen met leesrechten.'};};
      c.hass={...c._hass,callWS:window.demoRead};}""")
    entry.click()
    page.wait_for_function('window.demoCard._historyDialog._data!==null && !window.demoCard._historyDialog._inflight')
    readout = host.locator('[data-history-readout]')
    lane = host.locator('[data-history-scrub=consumer]')
    client = page.context.new_cdp_session(page)
    for width in (320, 390):
        page.set_viewport_size({'width': width, 'height': 844})
        page.evaluate('()=>{const d=demoCard._historyDialog;d._resetScrub();d._syncScrub();}')
        lane.evaluate('el=>{const s=demoCard._historyDialog._scroll;s.scrollTop+=el.getBoundingClientRect().bottom-s.getBoundingClientRect().bottom+40;}')
        box = lane.bounding_box()
        x, y = box['x'] + box['width'] * (9 * 3600 + 20 * 60) / 86400, box['y'] + box['height'] / 2
        client.send('Input.dispatchTouchEvent', {'type': 'touchStart', 'touchPoints': [{'x': x-20, 'y': y, 'id': 1}]})
        client.send('Input.dispatchTouchEvent', {'type': 'touchMove', 'touchPoints': [{'x': x, 'y': y, 'id': 1}]})
        assert page.evaluate('!!demoCard._historyDialog._scrubPointer?.drag'), (width, 'common consumer horizontal touch capture')
        assert 'AAN-periode geregistreerd' in readout.inner_text(), (width, 'actual recorded consumer session')
        assert 'Momentvermogen en sessieverbruik zijn niet in deze registratie bewaard.' in readout.text_content()
        assert not readout.locator('details[data-consumer-selection]').evaluate('el=>el.open')
        def assert_free_consumer_timeline():
            geometry = lane.evaluate('''el=>{const d=demoCard._historyDialog,r=el.getBoundingClientRect(),
              readout=d._body.querySelector('[data-consumer-readout]').getBoundingClientRect(),s=d._scroll.getBoundingClientRect(),
              hit=d.shadowRoot.elementFromPoint(r.left+r.width*.4,r.top+r.height/2);
              return {uncovered:r.top>=readout.bottom+6,visible:r.top>=s.top&&r.bottom<=s.bottom,
                target:hit?.closest('[data-history-scrub]')===el};}''')
            assert all(geometry.values()), (width, 'selected consumer timeline remains visible and hit-testable', geometry)
        assert_free_consumer_timeline()
        page.evaluate('demoCard._historyDialog._renderData()')
        client.send('Input.dispatchTouchEvent', {'type': 'touchEnd', 'touchPoints': []})
        assert page.evaluate('demoCard._historyDialog._scrubPointer===null')
        assert_free_consumer_timeline()
        page.screenshot(path=str(out / f'SolarPilot-beta99-consumer-history-active-{width}.png'))
        disclosure = readout.locator('details[data-consumer-selection]')
        disclosure.locator('summary').focus()
        page.keyboard.press('Enter')
        assert disclosure.evaluate('el=>el.open') and 'overgang bevestigd' in disclosure.inner_text()
        assert 'Startreden' in disclosure.inner_text() and 'Onvoldoende overschot' in disclosure.inner_text()
        assert disclosure.locator('dt').evaluate_all('els=>els.every(el=>el.scrollWidth<=el.clientWidth+1)'), 'original labels remain readable'
        page.keyboard.press('Enter')
        assert not disclosure.evaluate('el=>el.open'), 'original details are keyboard-toggleable'
        lane.focus()
        page.keyboard.press('Home')
        assert 'Onbekend bij deze tijd' in readout.inner_text() and 'Dit bewijst geen UIT-stand.' in readout.inner_text()
        page.keyboard.press('ArrowRight')
        assert '00:01:00' in readout.inner_text(), 'keyboard remains on a historical time, never current status'
        assert host.locator('dialog').evaluate('d=>d.scrollWidth<=d.clientWidth+1'), width
        page.screenshot(path=str(out / f'SolarPilot-beta99-consumer-history-{width}.png'))
    client.detach()
    page.evaluate('()=>{const d=demoCard._historyDialog;d._click({target:d._body.querySelector("[data-history-session]")});}')
    readout.locator('details[data-consumer-selection]>summary').click()
    assert 'SolarPilot-opdracht' in readout.inner_text() and 'overgang bevestigd' in readout.inner_text()
    readout.locator('details[data-consumer-selection]>summary').click()
    host.locator('details.events>summary').click()
    event = host.locator('[data-history-event]').first
    event.evaluate('el=>{const s=demoCard._historyDialog._scroll;s.scrollTop+=el.getBoundingClientRect().bottom-s.getBoundingClientRect().bottom+40;}')
    event.click()
    assert 'Geregistreerde gebeurtenis' in readout.inner_text() and 'handmatig overgenomen' in readout.inner_text()
    page.evaluate('async()=>{await demoCard._historyDialog._fetch(true)}')
    assert 'Geregistreerde gebeurtenis' in readout.inner_text(), 'same-day refresh retains the selected original event'
    source_button = host.locator('[data-action=source-history]')
    source_button.evaluate('el=>{const s=demoCard._historyDialog._scroll;s.scrollTop+=el.getBoundingClientRect().bottom-s.getBoundingClientRect().bottom+40;}')
    source_button.click()
    sources = page.locator('solar-pilot-card >> [data-source-history-dialog]')
    page.wait_for_function('demoCard._sourceHistoryDialog?._data?.sources.length===2')
    assert not host.locator('dialog').is_visible(), 'the source chooser replaces the SolarPilot session popup'
    assert 'oudere gegevens kunnen bij een eerdere koppeling horen' in sources.locator('dialog').inner_text()
    link = sources.locator('a').first
    assert link.get_attribute('href') == '/history?entity_id=switch.demo_consumer'
    assert link.get_attribute('target') == '_blank' and 'noopener' in link.get_attribute('rel')
    page.screenshot(path=str(out / 'SolarPilot-beta99-source-history-chooser-390.png'))
    sources.locator('[data-source-index="0"]').click()
    page.wait_for_function('nativeHistoryViews.length===1')
    assert page.evaluate('nativeHistoryViews[0]') == {'entityId': 'switch.demo_consumer', 'view': 'history'}
    assert not sources.locator('dialog').is_visible(), 'native history receives focus with no SolarPilot modal over it'
    assert page.evaluate('sourceHistoryReads.length===2'), 'opening native history rechecks the current source-role binding'

    # Per-battery source graphs and individual Wallbox boundary reports are also reachable.
    page.evaluate("""()=>{const c=demoCard,a=structuredClone(c._last.attributes);
      a.ems.battery_fleet={enabled:true,control_enabled:false,reason:'Alleen bekijken',aggregate:{valid:true,soc_pct:65,power_w:-100},
        batteries:[{id:'demo-battery',name:'Fictieve batterij',valid:true,soc_pct:65,power_w:-100,phase_hint:'L1',controllable:false}]};
      const at=Date.parse('2026-09-27T10:00:00+02:00')/1000;
      a.wallbox={...a.wallbox,enabled:true,power_w:99999,activity_details:{current:{known:false},history:[{
        observed_start_at:at,start_confirmed:true,last_charging_report_at:at+300,previous_power_w:3800,
        observed_stop_at:at+310,stop_report_at:at+309,status_report_at:at+308,power_w:0,stop_confirmed:true,
        cause_reported:false,native_status:'Paused',stop_reason:'Precieze oorzaak niet doorgegeven.'}],
        ongoing:{observed_start_at:at+3600,start_confirmed:false,last_charging_report_at:at+3610,previous_power_w:2100}}};
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};c._view='storage';c._render();}""")
    battery = page.locator('solar-pilot-card >> [data-action=source_history][data-history-kind=battery]')
    assert battery.count() == 1 and battery.get_attribute('data-id') == 'demo-battery'
    battery.click()
    page.wait_for_function("demoCard._sourceHistoryDialog?._data?.kind==='battery'")
    assert sources.locator('a').first.get_attribute('href') == '/history?entity_id=sensor.demo_battery_soc'
    sources.locator('.close').click()
    page.wait_for_function('!demoCard._sourceHistoryDialog._isOpen')
    page.evaluate("()=>{demoCard._view='loads';demoCard._render();}")
    periods = page.locator('solar-pilot-card >> .wb-stop-history')
    periods.locator(':scope>summary').click()
    individual = periods.locator('.wb-history-period')
    assert individual.count() == 2
    individual.first.locator('summary').click()
    assert 'Nog geen stop bevestigd' in individual.first.inner_text() and '2,1 kW' in individual.first.inner_text()
    individual.last.locator('summary').click()
    assert 'Stop waargenomen' in individual.last.inner_text() and '0 W' in individual.last.inner_text()
    assert '3,8 kW' in individual.last.inner_text() and '99999' not in individual.last.inner_text()
    assert 'geen continue vermogensreeks' in individual.last.inner_text()
    wallbox = page.locator('solar-pilot-card >> [data-action=source_history][data-history-kind=wallbox]')
    wallbox.click()
    page.wait_for_function("demoCard._sourceHistoryDialog?._data?.kind==='wallbox'")
    assert sources.locator('a').first.get_attribute('href') == '/history?entity_id=sensor.demo_wallbox_power'
    sources.locator('.close').click()
    page.evaluate("()=>{demoCard._view='overview';demoCard._render();}")
    assert page.locator('solar-pilot-card >> [data-action=source_history][data-history-kind=wallbox]').count() == 1
    assert page.locator('solar-pilot-card >> [data-action=source_history][data-history-kind=battery]').count() == 1
    # Each displayed boiler reading goes straight to its actual source history.
    page.evaluate("""()=>{const c=demoCard,a=structuredClone(c._last.attributes),now=Date.now()/1000,p=a.panasonic;
      p.source_stale_s=120;p.temperature_c=46;p.temperature_entity='sensor.demo_tank_temperature';p.temperature_stamp=now;p.temperature_observed_at=now;
      p.target_c=51;p.target_entity='number.demo_tank_target';p.target_stamp=now;p.target_observed_at=now;
      p.display_tank={available:true,entity_id:'water_heater.demo_tank',temperature_c:49,target_c:50,temperature_stamp:now,target_stamp:now};
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};c._view='overview';c._render();}""")
    before = page.evaluate('nativeHistoryViews.length')
    temperature = page.locator('solar-pilot-card >> [data-boiler-temperatures] [data-history-role=tank_temperature_entity]')
    assert temperature.inner_text() == '49 °C'
    temperature.click()
    page.wait_for_function(f'nativeHistoryViews.length==={before+1}')
    assert page.evaluate('nativeHistoryViews.at(-1)') == {'entityId': 'water_heater.demo_tank', 'view': 'history'}
    assert page.evaluate("sourceHistoryReads.at(-1).source==='display_tank' && !('item_id' in sourceHistoryReads.at(-1))")
    target = page.locator('solar-pilot-card >> [data-boiler-temperatures] [data-history-role=tank_target_entity]')
    assert target.inner_text() == '50 °C'
    target.click()
    page.wait_for_function(f'nativeHistoryViews.length==={before+2}')
    assert page.evaluate('nativeHistoryViews.at(-1).entityId') == 'water_heater.demo_tank'
    page.evaluate("()=>{demoCard._last.attributes.panasonic.display_tank.target_stamp=Date.now()/1000-1000;demoCard._render();}")
    assert target.inner_text() == '51 °C'
    target.click()
    page.wait_for_function(f'nativeHistoryViews.length==={before+3}')
    assert page.evaluate('nativeHistoryViews.at(-1)') == {'entityId': 'number.demo_tank_target', 'view': 'history'}
    assert page.evaluate("sourceHistoryReads.at(-1).source==='configured'")
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(out / 'SolarPilot-beta99-boiler-direct-history-390.png'))
    page.evaluate("()=>{const p=demoCard._last.attributes.panasonic;p.display_tank.available=false;p.temperature_entity='';p.target_entity='';demoCard._render();}")
    assert page.locator('solar-pilot-card >> [data-action=heatpump_source_history]').count() == 0, 'unbound sources are plain text, not invented entity graphs'
    assert page.evaluate('controlWrites.length===0'), 'all device/source history interactions remain read-only'


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=browser_path, headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width":1440, "height":1000}, device_scale_factor=1, locale="nl-BE")
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content((ROOT / "SolarPilot-voorbeeld.html").read_text(encoding="utf-8"), wait_until="load")
    page.wait_for_selector("solar-pilot-card >> h1")
    page.evaluate("""payloads => {
      window.historyFixtures=payloads;window.historyReads=[];window.controlWrites=[];
      const c=document.querySelector('solar-pilot-card');window.demoCard=c;
      const a=structuredClone(c._last.attributes);a.config_entry_id='demo-entry';
      const d=a.devices[0];d.name='Demo-verbruiker · fictieve gegevens';
      d.history={date:'2026-09-27',on_s:7800,ongoing:true,revision:17};
      window.demoId=d.id;
      window.demoRead=async m=>{window.historyReads.push(m);return structuredClone(window.historyFixtures[m.date||'2026-09-27']);};
      c.hass={...c._hass,callWS:window.demoRead,callService:async(...args)=>window.controlWrites.push(args),states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};
    }""", payloads)
    page.locator('solar-pilot-card >> button[data-action=view][data-value=loads]').click()
    entry = page.locator('solar-pilot-card >> button[data-action=history]').first
    assert '2u 10m vandaag' in entry.inner_text()
    assert page.evaluate('window.historyReads.length') == 0
    entry.click()
    host = page.locator('solar-pilot-consumer-history-dialog')
    dialog = host.locator('dialog')
    page.wait_for_function("document.querySelector('solar-pilot-card')._historyDialog._data !== null")
    assert dialog.is_visible()
    assert host.locator('[data-total]').inner_text() == '2 u 10 min'
    assert host.locator('.session').count() == 3
    for session in host.locator('.session').all():
        assert session.locator(':scope > dl.reasons > dt').all_inner_texts() == ['Startreden', 'Stopreden']
    assert 'Voldoende stabiel zonneoverschot' in dialog.inner_text()
    assert 'handmatige bediening' in dialog.inner_text()
    assert 'loopt nog' in dialog.inner_text()
    assert host.locator('.segment').count() == 3
    assert host.locator('.day').count() == 7
    assert page.evaluate('window.historyReads.length') == 1
    assert page.evaluate('window.controlWrites.length') == 0

    # Hold the actual native dialog node; 80 full telemetry renders may not destroy it.
    host.locator('details.events summary').click()
    page.evaluate("""() => { const d=window.demoCard._historyDialog;
      window.dialogNode=d._dialog;d._scroll.scrollTop=210;window.savedScroll=d._scroll.scrollTop;
      for(let n=0;n<80;n++){const c=window.demoCard,a=structuredClone(c._last.attributes);a.grid_w=-500-n;
        c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}
    }""")
    assert page.evaluate("window.demoCard._historyDialog._dialog===window.dialogNode && window.dialogNode.open")
    assert page.evaluate('window.demoCard._historyDialog._scroll.scrollTop===window.savedScroll')
    assert host.locator('details.events').get_attribute('open') is not None
    assert page.evaluate('window.historyReads.length') == 1
    host.locator('[data-action=refresh]').click()
    page.wait_for_function('window.historyReads.length===2 && !window.demoCard._historyDialog._inflight')
    assert page.evaluate('window.demoCard._historyDialog._scroll.scrollTop===window.savedScroll')
    assert host.locator('details.events').get_attribute('open') is not None

    # Selected date survives main-card changes; explicit range and date controls.
    host.locator('[data-action=prev]').click()
    page.wait_for_function("window.demoCard._historyDialog._data.date==='2026-09-26'")
    assert host.locator('input[type=date]').input_value() == '2026-09-26'
    page.evaluate("""()=>{const c=window.demoCard,a=structuredClone(c._last.attributes);a.free_w=999;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}""")
    assert host.locator('input[type=date]').input_value() == '2026-09-26'
    host.locator('[data-action=range][data-value="30"]').click()
    assert host.locator('.day').count() == 30
    host.locator('[data-action=today]').click()
    page.wait_for_function("window.demoCard._historyDialog._data.date==='2026-09-27'")
    assert host.locator('[data-action=next]').is_disabled()
    host.locator('[data-action=range][data-value="7"]').click()

    # Delayed response for a prior date cannot replace the most recently selected date.
    page.evaluate("""()=>{const d=window.demoCard._historyDialog;
      d._hass={...d._hass,callWS:m=>new Promise(resolve=>setTimeout(()=>resolve(structuredClone(window.historyFixtures[m.date||'2026-09-27'])),m.date==='2026-09-26'?120:5))};
      d._selectDay('2026-09-26');d._selectDay('2026-09-27');}""")
    page.wait_for_timeout(180)
    assert host.locator('input[type=date]').input_value() == '2026-09-27'
    page.evaluate('window.demoCard._historyDialog._hass={...window.demoCard._hass,callWS:window.demoRead}')

    # Screen sizes, no horizontal overflow; real rendered popup screenshots, not mockups.
    for width in (320,390,768,1440):
        page.set_viewport_size({"width":width,"height":1000 if width>540 else 844})
        page.evaluate('window.demoCard._historyDialog._scroll.scrollTop=0')
        box=dialog.bounding_box()
        assert box['x']>=0 and box['x']+box['width']<=width+1, (width,box)
        assert page.evaluate('window.demoCard._historyDialog._scroll.scrollWidth <= window.demoCard._historyDialog._scroll.clientWidth+1'), width
        if len(sys.argv)>1 and width in (390,1440):
            dest=Path(sys.argv[1]);dest.mkdir(parents=True,exist_ok=True)
            page.screenshot(path=str(dest/f'SolarPilot-beta25-dagoverzicht-{width}.png'))
    page.set_viewport_size({"width":1440,"height":1000})

    # User-controlled labels/reasons must render as text, never executable markup.
    page.evaluate("""async()=>{const x=window.historyFixtures['2026-09-27'];
      x.name='<img src=x onerror="window.injected=true">';
      x.sessions[0].start_reason='<img src=x onerror="window.injected=true">';
      await window.demoCard._historyDialog._fetch(true);}""")
    assert host.locator('img').count() == 0
    assert '<img src=x' in dialog.inner_text()
    assert not page.evaluate('window.injected||false')
    assert page.evaluate('window.controlWrites.length') == 0

    # Esc cleans the timer and returns keyboard focus to the new live button.
    page.keyboard.press('Escape')
    page.wait_for_timeout(50)
    assert not dialog.is_visible()
    assert page.evaluate('window.demoCard._historyDialog._timer===null')
    assert page.evaluate("window.demoCard.shadowRoot.activeElement?.dataset?.action==='history'")
    reads=page.evaluate('window.historyReads.length')
    page.evaluate("""()=>{const c=window.demoCard,a=structuredClone(c._last.attributes);a.devices[0].history.revision++;
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}""")
    assert page.evaluate('window.historyReads.length') == reads
    entry.click()
    assert dialog.is_visible()
    host.locator('[data-action=close]').click()
    assert not dialog.is_visible()
    check_other_histories(page, entry, host)
    assert not errors,errors
    browser.close()
print('History popup browser checks passed: actual native dialog survives 80 telemetry renders; scrolling/date/details retained; 7/30 day navigation; racing responses; no control writes; 320/390/768/1440 layouts; XSS; Esc/close/poll cleanup and focus return. All demo readings are fictitious.')
