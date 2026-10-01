"""Exercise the real dashboard popup with explicitly fictitious read-only data.

Run tools/build_example.py first. Uses local Chromium/Playwright; no HA instance,
external network or physical device commands. Screenshot output is optional.
"""
from datetime import datetime, timedelta
import importlib.util
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
browser_path = shutil.which("chromium") or shutil.which("google-chrome")
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
        assert session.locator('dt').all_inner_texts() == ['Startreden', 'Stopreden']
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
    assert not errors,errors
    browser.close()
print('History popup browser checks passed: actual native dialog survives 80 telemetry renders; scrolling/date/details retained; 7/30 day navigation; racing responses; no control writes; 320/390/768/1440 layouts; XSS; Esc/close/poll cleanup and focus return. All demo readings are fictitious.')
