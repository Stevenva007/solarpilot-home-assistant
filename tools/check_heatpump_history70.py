"""Real native heatpump history popup regressions, with fictitious data only.

Run build_example.py first. No account, HA instance, network or actuator writes.
"""
from datetime import date, timedelta
import os
from pathlib import Path
import shutil

from playwright.sync_api import sync_playwright


ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("SOLARPILOT_SCREENSHOT_DIR", "/tmp/solarpilot-browser-tests"))
OUT.mkdir(parents=True, exist_ok=True)
TODAY = "2026-10-12"


def session(day, start, end, *, ongoing=False):
    sh, sm = map(int, start.split(":"))
    eh, em = map(int, end.split(":"))
    duration = (eh * 60 + em - sh * 60 - sm) * 60
    return dict(start=f"{day}T{start}:00+02:00", end=None if ongoing else f"{day}T{end}:00+02:00",
                observed_until=f"{day}T{end}:00+02:00", segment_start=f"{day}T{start}:00+02:00",
                segment_end=f"{day}T{end}:00+02:00", duration_s=duration, ongoing=ongoing,
                left_pct=(sh * 60 + sm) / 14.4, width_pct=duration / 864,
                start_confirmed=True, stop_confirmed=not ongoing,
                start_source="external", stop_source="external",
                start_reason="Panasonic-activiteit waargenomen; startoorzaak niet vastgesteld.",
                stop_reason="Einde van de waargenomen activiteit; stopoorzaak niet vastgesteld.")


def fixture(day):
    registered = day in ("2026-10-11", TODAY)
    sessions = [session(day, "09:05", "09:50"), session(day, "12:30", "13:30", ongoing=day == TODAY)] if registered else []
    tasks = [dict(s, task=task, label=label, tier=tier) for s, task, label, tier in
             zip(sessions, ("tapwater_heating", "space_heating"), ("Boiler opwarmen", "Verwarmen"), ("derived", "confirmed"))]
    days = []
    for offset in range(29, -1, -1):
        value = (date.fromisoformat(TODAY) - timedelta(days=offset)).isoformat()
        known = value in ("2026-10-11", TODAY)
        days.append(dict(date=value, on_s=6300 if known else None, known_s=36000 if known else 0,
                         starts=2 if known else 0, energy_kwh=1.76 if known else None,
                         energy_known_s=10000 if known else 0))
    lanes = {}
    for key in ("request", "contact", "received"):
        known = registered and key != "received"
        lanes[key] = dict(device_id="sg_" + key, name=key, has_data=known,
                          on_s=600 if known and key == "request" else 0,
                          known_s=7200 if known else 0, partial=True,
                          sessions=[session(day, "12:40", "12:50")] if known and key == "request" else [])
    return dict(device_id="heatpump", name="Warmtepomp · fictieve registratie", date=day,
                today=TODAY, first_date="2026-09-13", timezone="Europe/Brussels",
                generated_at=f"{TODAY}T13:30:00+02:00", recording_since="2026-10-11",
                current_status="Panasonic regelt zelfstandig · fictieve gegevens", retention_days=30,
                day_seconds=86400, has_data=registered, on_s=6300 if registered else 0,
                known_s=36000 if registered else 0, unobserved_s=12600 if registered else 48600,
                partial=True, starts=2 if registered else 0, stops=1 if registered else 0,
                energy_kwh=1.76 if registered else None, energy_known_s=10000 if registered else 0,
                sessions=sessions, task_sessions=tasks,
                task_totals=[dict(task=t["task"], label=t["label"], tier=t["tier"], on_s=t["duration_s"]) for t in tasks],
                days=days, sg=lanes, events=[dict(at=f"{day}T11:00:00+02:00", reason="Meetonderbreking · fictieve melding")],
                note="Lokale waarnemingen; geen startopdracht naar de warmtepomp.")


fixtures = {day: fixture(day) for day in ("2026-10-10", "2026-10-11", TODAY)}
errors = []


def visible_text(locator, expected, context):
    assert locator.count() == 1, (context, "expected one element", locator.count())
    assert locator.is_visible(), (context, "element should be visible")
    actual = locator.inner_text()
    assert actual == expected, (context, f"expected {expected!r}, got {actual!r}")


with sync_playwright() as playwright:
    executable = os.environ.get("SOLARPILOT_CHROMIUM_PATH") or shutil.which("chromium")
    browser = playwright.chromium.launch(**({"executable_path": executable} if executable else {}),
                                         headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 844}, locale="nl-BE", timezone_id="UTC")
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content((ROOT / "SolarPilot-voorbeeld.html").read_text(encoding="utf-8"), wait_until="load")
    page.wait_for_selector("solar-pilot-card >> h1")
    page.evaluate("""fixtures=>{
      window.hpFixtures=fixtures;window.hpReads=[];window.hpWrites=[];
      window.c=document.querySelector('solar-pilot-card');
      const a=structuredClone(c._last.attributes);a.config_entry_id='fictional-entry';
      a.panasonic.history={recording:true,storage_available:true,revision:1};
      window.hpRead=async m=>{hpReads.push(m);
        if(m.type!=='solar_pilot/heatpump_history'||m.config_entry_id!=='fictional-entry'||'device_id' in m)throw Error('Unexpected history read '+JSON.stringify(m));
        return structuredClone(hpFixtures[m.date||'2026-10-12']);};
      c.hass={...c._hass,callWS:hpRead,callService:async(...args)=>hpWrites.push(args),
        states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};
    }""", fixtures)
    for view in ("overview", "comfort", "loads"):
        page.locator(f'solar-pilot-card >> .nav > button[data-action=view][data-value={view}]').click()
        visible_text(page.locator('solar-pilot-card >> button[data-action=heatpump_history]'),
                     "Geschiedenis", (view, "read-only history entry"))
    assert page.evaluate("hpReads.length===0 && hpWrites.length===0"), "closed history must neither read nor write"
    page.locator('solar-pilot-card >> .nav > button[data-action=view][data-value=overview]').click()
    page.locator('solar-pilot-card >> button[data-action=heatpump_history]').click()
    host = page.locator("solar-pilot-card >> [data-heatpump-history-dialog]")
    dialog = host.locator("dialog")
    page.wait_for_function("c._heatpumpHistoryDialog._data!==null")
    visible_text(host.locator("h2"), "Warmtepompgeschiedenis", "popup title")
    visible_text(host.locator("[data-total]"), "1 u 45 min", "registered runtime")
    visible_text(host.locator("[data-energy]"), "1,76 kWh", "measured whole-HP energy")
    visible_text(host.locator("[data-starts]"), "2", "observed starts")
    visible_text(host.locator("[data-stops]"), "1", "observed stops")
    assert host.locator(".session").count() == 2, "two actual activity sessions"
    assert host.locator(".task-timeline [data-history-task]").count() == 2, "task timeline must contain two intervals"
    assert "Boiler opwarmen" in dialog.inner_text() and "Afgeleid" in dialog.inner_text(), "derived tank task visible"
    assert "Verwarmen" in dialog.inner_text() and "Bevestigd" in dialog.inner_text(), "native task visible"
    assert "09:05" in dialog.inner_text(), "HA Brussels time must be used even when viewer browser is UTC"
    assert "SolarPilot-start" not in dialog.inner_text(), "native heatpump starts cannot be attributed to SolarPilot"
    assert host.locator('[role=switch],[data-action=sg_boost_enabled],[data-action=manual_start]').count() == 0, "history contains no device controls"
    host.locator('details[data-history-key=sg]>summary').click()
    visible_text(host.locator('[data-sg-history=request]>.duration'), "10 min", "independent SG request runtime")
    visible_text(host.locator('[data-sg-history=contact]>.duration'), "0 s", "confirmed inactive SG contact runtime")
    visible_text(host.locator('[data-sg-history=received]>.duration'), "—", "unknown Panasonic SG reception")
    assert "extra verbruik door SG is niet vastgesteld" in dialog.inner_text(), "SG causal energy must remain unclaimed"
    host.locator('details[data-history-key=coverage]>summary').click()
    assert "Ontbrekende perioden blijven onbekend" in dialog.inner_text(), "gaps must remain unknown"

    # The actual dialog node, scroll and open explanations survive 80 complete
    # telemetry renders. Opaque recording metadata refreshes the live fragment
    # without exposing retained-history totals before its authorized API query.
    page.evaluate("""()=>{const d=c._heatpumpHistoryDialog;window.hpDialogNode=d._dialog;
      d._scroll.scrollTop=240;window.hpSavedScroll=d._scroll.scrollTop;window.hpReadsBefore=hpReads.length;
      for(let n=0;n<80;n++){const a=structuredClone(c._last.attributes);a.grid_w=-500-n;
        c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}
    }""")
    assert page.evaluate("c._heatpumpHistoryDialog._dialog===hpDialogNode && hpDialogNode.open"), "80 card renders must preserve native dialog node"
    assert page.evaluate("c._heatpumpHistoryDialog._scroll.scrollTop===hpSavedScroll"), "80 renders must preserve popup scroll"
    assert page.evaluate("hpReads.length===hpReadsBefore"), "unchanged history revision must not refetch on card renders"
    for key in ("sg", "coverage"):
        assert host.locator(f'details[data-history-key={key}]').get_attribute("open") is not None, (key, "Details lost across card renders")
    page.evaluate("""()=>{window.hpSignatureBefore=c._observationSignature;
      c._last.attributes.panasonic.history.recording=false;c._last.attributes.panasonic.history.revision++;
      c._refreshObservationDisplay();}""")
    assert page.evaluate("c._observationSignature!==hpSignatureBefore"), "opaque history metadata must refresh live fragment without a new HA event"
    assert page.evaluate("c.shadowRoot.querySelector('[data-action=heatpump_history]').textContent==='Geschiedenis'"), "live entry may not expose unauthorized retained totals"
    host.locator('[data-action=refresh]').click()
    page.wait_for_function("hpReads.length>hpReadsBefore && !c._heatpumpHistoryDialog._inflight")
    assert page.evaluate("c._heatpumpHistoryDialog._scroll.scrollTop===hpSavedScroll"), "same-day refresh must retain scroll"
    assert host.locator('details[data-history-key=sg]').get_attribute("open") is not None, "same-day refresh must retain SG Details"

    # Actual date/range controls and a delayed prior-day response.
    host.locator('[data-action=prev]').click()
    page.wait_for_function("c._heatpumpHistoryDialog._data.date==='2026-10-11'")
    assert host.locator('input[type=date]').input_value() == "2026-10-11", "previous date selection"
    page.evaluate("c._render()")
    assert host.locator('input[type=date]').input_value() == "2026-10-11", "selected date survives main render"
    host.locator('[data-action=range][data-value="30"]').click()
    assert host.locator(".day").count() == 30, "30-day activity overview"
    missing = host.locator('.day[data-day="2026-10-10"]')
    assert "geen registratie" in missing.get_attribute("aria-label"), "unregistered day is unknown"
    assert "—" in missing.inner_text() and "0m" not in missing.inner_text(), "unknown day may not claim zero activity"
    missing.click()
    page.wait_for_function("c._heatpumpHistoryDialog._data.date==='2026-10-10'")
    for key in ("data-total", "data-energy", "data-starts", "data-stops"):
        visible_text(host.locator(f"[{key}]"), "—", (key, "unregistered selected day"))
    assert host.locator(".task-timeline .segment").count() == 0, "unknown day may not invent task intervals"
    host.locator('[data-action=today]').click()
    page.wait_for_function("c._heatpumpHistoryDialog._data.date==='2026-10-12'")
    assert host.locator('[data-action=next]').is_disabled(), "cannot navigate after today"
    host.locator('[data-action=range][data-value="7"]').click()
    assert host.locator(".day").count() == 7, "7-day activity overview"
    page.evaluate("""()=>{const d=c._heatpumpHistoryDialog;
      d._hass={...c._hass,callWS:m=>new Promise(resolve=>setTimeout(()=>resolve(structuredClone(hpFixtures[m.date])),m.date==='2026-10-11'?120:5))};
      d._selectDay('2026-10-11');d._selectDay('2026-10-12');}""")
    page.wait_for_timeout(180)
    assert host.locator('input[type=date]').input_value() == TODAY, "stale prior-day response must not overwrite latest selection"
    page.evaluate("c._heatpumpHistoryDialog._hass={...c._hass,callWS:hpRead}")

    # An unavailable read leaves the native popup usable, with an inert error
    # message. It never falls back to any actuator call or control endpoint.
    page.evaluate("""async()=>{const d=c._heatpumpHistoryDialog;
      d._hass={...c._hass,callWS:async()=>{throw Error('Geschiedenis tijdelijk niet beschikbaar <img src=x>');}};
      await d._fetch(true);}""")
    assert dialog.is_visible(), "history read failure must not destroy popup"
    assert "tijdelijk niet beschikbaar <img src=x>" in host.locator('.update-status').inner_text(), "read failure is visible inert text"
    assert host.locator("img").count() == 0, "read failure message must escape markup"
    page.evaluate("c._heatpumpHistoryDialog._hass={...c._hass,callWS:hpRead}")

    # When the backend can no longer confirm continuity, the last observed
    # endpoint does not become an ongoing session or a new confirmed stop.
    page.evaluate("""async()=>{const x=hpFixtures['2026-10-12'];
      x.sessions[1].ongoing=false;x.sessions[1].stop_confirmed=false;x.sessions[1].stop_reason=null;
      x.task_sessions[1].ongoing=false;await c._heatpumpHistoryDialog._fetch(true);}""")
    visible_text(host.locator('.session').last.locator('.pill').first, "Einde onbekend", "stalled recorder has no confirmed end")
    assert "laatst waargenomen" in host.locator('.session').last.inner_text(), "stale endpoint must be labelled as last observed"
    assert "loopt nog" not in dialog.inner_text(), "stale continuity cannot claim ongoing activity"
    visible_text(host.locator('[data-stops]'), "1", "stale continuity cannot invent a stop")
    assert host.locator('.task-timeline .ongoing').count() == 0, "stale task intervals may not retain live hatching"

    # A registered partial meter day still has runtime, while whole-HP kWh is
    # unknown. Label/reason/event HTML is inert text in the real browser.
    page.evaluate("""async()=>{const x=hpFixtures['2026-10-12'];x.energy_kwh=null;x.energy_known_s=0;
      const html='<img src=x onerror="window.hpInjected=true">';
      x.name=html;x.task_sessions[0].label=html;x.task_totals[0].label=html;
      x.sessions[0].start_reason=html;x.events[0].reason=html;x.note=html;
      await c._heatpumpHistoryDialog._fetch(true);}""")
    visible_text(host.locator("[data-energy]"), "—", "partial-only power cannot fabricate whole-HP kWh")
    visible_text(host.locator("[data-total]"), "1 u 45 min", "registered activity survives missing energy")
    assert host.locator("img").count() == 0 and not page.evaluate("window.hpInjected||false"), "history labels must escape HTML"
    assert "<img src=x" in dialog.inner_text(), "escaped user labels remain readable as text"
    page.evaluate("fixtures=>{window.hpFixtures=fixtures;}", fixtures)
    page.keyboard.press("Escape")
    page.wait_for_timeout(70)
    assert not dialog.is_visible() and page.evaluate("c._heatpumpHistoryDialog._timer===null"), "Escape closes dialog and polling"
    assert page.evaluate("c.shadowRoot.activeElement?.dataset?.action==='heatpump_history'"), "Escape returns focus to current live entry"

    # Render and inspect every entry view at all four requested widths.
    for view in ("overview", "comfort", "loads"):
        page.locator(f'solar-pilot-card >> .nav > button[data-action=view][data-value={view}]').click()
        page.locator('solar-pilot-card >> button[data-action=heatpump_history]').click()
        page.wait_for_function("c._heatpumpHistoryDialog._data!==null && !c._heatpumpHistoryDialog._inflight")
        for width in (320, 390, 768, 1280):
            page.set_viewport_size({"width": width, "height": 844 if width < 540 else 1000})
            page.evaluate("c._heatpumpHistoryDialog._scroll.scrollTop=0")
            box = dialog.bounding_box()
            assert box and box["x"] >= 0 and box["x"] + box["width"] <= width + 1, (view, width, "dialog outside viewport", box)
            assert dialog.evaluate("d=>d.scrollWidth<=d.clientWidth+1"), (view, width, "dialog contents overflow horizontally")
            assert page.evaluate("c._heatpumpHistoryDialog._scroll.scrollWidth<=c._heatpumpHistoryDialog._scroll.clientWidth+1"), (view, width, "history scroll area overflows horizontally")
            visible_text(host.locator("[data-total]"), "1 u 45 min", (view, width, "runtime metric"))
            page.screenshot(path=str(OUT / f"SolarPilot-warmtepompgeschiedenis70-{view}-{width}.png"))
        host.locator('[data-action=close]').click()
        assert not dialog.is_visible(), (view, "explicit close")
        page.wait_for_timeout(60)

    # Close/unload and config-entry changes invalidate late responses and stop
    # timers. These read-only failures must never issue physical commands.
    page.locator('solar-pilot-card >> button[data-action=heatpump_history]').click()
    page.wait_for_function("c._heatpumpHistoryDialog._data!==null")
    page.evaluate("""()=>{const a=structuredClone(c._last.attributes);a.config_entry_id='different-fictional-entry';
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};}""")
    assert not dialog.is_visible() and page.evaluate("c._heatpumpHistoryDialog._timer===null"), "entry change closes history from prior installation"
    page.evaluate("""()=>{const a=structuredClone(c._last.attributes);a.config_entry_id='fictional-entry';
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};c._openHeatpumpHistory();}""")
    page.wait_for_function("c._heatpumpHistoryDialog._data!==null")
    page.evaluate("""()=>{const d=c._heatpumpHistoryDialog;window.hpSeqBeforeClose=d._seq;
      d._hass={...c._hass,callWS:()=>new Promise(resolve=>setTimeout(()=>resolve(hpFixtures['2026-10-11']),80))};
      d._fetch(true);c.remove();}""")
    page.wait_for_timeout(120)
    assert page.evaluate("!c._heatpumpHistoryDialog._isOpen && !c._heatpumpHistoryDialog._dialog.open && c._heatpumpHistoryDialog._timer===null && c._heatpumpHistoryDialog._seq>hpSeqBeforeClose"), "unload invalidates pending fetch and closes polling"
    assert page.evaluate("hpWrites.length===0"), "history must never send actuator/service writes"
    assert not errors, ("browser errors", errors)
    browser.close()

print("Heatpump history browser checks passed: native popup; 80 renders; date/scroll/Details; 7/30 days; racing responses; separate tasks/SG/whole-HP energy; unknown gaps; three views at 320/390/768/1280; XSS; Escape/close/unload; no writes. All data are fictitious.")
