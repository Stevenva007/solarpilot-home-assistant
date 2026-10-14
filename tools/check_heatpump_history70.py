"""Real native heatpump history popup regressions, with fictitious data only.

Run build_example.py first. No account, HA instance, network or actuator writes.
"""
from datetime import date, datetime, timedelta
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


def goal_fixture(day):
    at = datetime.fromisoformat(f"{day}T12:40:00+02:00").timestamp()
    return {"normal_target_c": 50, "calculated_c": 57.5, "profile_percent": 115,
        "profile_confirmed_at": at-3600, "normal_target_reported_at": at-7,
        "valid_until": at+113, "stale_s": 120, "source": "local_confirmed_profile",
        "source_binding": "b"*64, "read_only": True, "reason": "calculated",
        "contact_state": "off", "contact_reported_at": at-2,
        "contact_valid_until": at+118, "contact_stale_s": 120}


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
                          on_s=600 if known and key == "request" else 300 if known and key == "contact" else 0,
                          known_s=7200 if known else 0, partial=True,
                          sessions=[session(day, "12:40", "12:50")] if known and key == "request" else [session(day, "12:30", "12:35")] if known and key == "contact" else [])
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
                days=days, sg=lanes,
                sg_contact_overlay={"schema": 1, "on_s": 300 if registered else None,
                    "segments": ([dict(session(day, "12:30", "12:35"), state="on", reported_at=None),
                                  dict(session(day, "12:35", "12:50"), state="off", reported_at=None),
                                  dict(session(day, "12:50", "13:30"), state="unknown", reported_at=None)] if registered else [])},
                tank_temperature={"schema": 1, "current": {"current": False}, "points": ([{
                    "captured_at": datetime.fromisoformat(f"{day}T12:40:00+02:00").timestamp(),
                    "temperature_c": 57, "temperature_reported_at": datetime.fromisoformat(f"{day}T12:39:56+02:00").timestamp(),
                    "ordinary_target_c": 50, "ordinary_target_reported_at": datetime.fromisoformat(f"{day}T12:39:53+02:00").timestamp(),
                    "stale_s": 120, "sg_goal": goal_fixture(day)
                }] if registered else [])},
                support_sessions=[session(day, "12:40", "12:45")] if registered else [],
                support_totals=[{"label": "Elektrische ondersteuning", "on_s": 300}] if registered else [],
                native_evidence={"schema": 1, "read_only": True, "points": [{
                    "captured_at": datetime.fromisoformat(f"{day}T12:40:00+02:00").timestamp(), "continuity": True,
                    "sg_goal": goal_fixture(day),
                    "native": {"confirmed": False, "inactive_reported": True, "inactive_scope": "space_circuit",
                               "reported_at": datetime.fromisoformat(f"{day}T12:39:55+02:00").timestamp(), "fresh": True},
                    "tank": {"temperature_c": 57, "temperature_reported_at": datetime.fromisoformat(f"{day}T12:39:56+02:00").timestamp(),
                             "ordinary_target_c": 50, "ordinary_target_reported_at": datetime.fromisoformat(f"{day}T12:39:53+02:00").timestamp()},
                    "effective_target": {"temperature_c": None, "status": "unknown"}, "completion": {"state": "unknown"},
                    "supplies": [{"valid": False, "watts": None, "reported_at": None},
                                 {"valid": True, "watts": 0, "reported_at": datetime.fromisoformat(f"{day}T12:39:58+02:00").timestamp()}]
                }] if registered else []},
                electrical_activity={"has_data": registered, "starts": 1 if registered else 0, "stops": 1 if registered else 0,
                    "sessions": [dict(session(day, "12:30", "12:31"), duration_s=5, short_observed_period=True,
                                      end=f"{day}T12:30:05+02:00", observed_until=f"{day}T12:30:05+02:00",
                                      segment_end=f"{day}T12:30:05+02:00", width_pct=5/864)] if registered else []},
                events=[dict(at=f"{day}T11:00:00+02:00", reason="Meetonderbreking · fictieve melding")],
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
    assert host.locator('[data-sg-contact-overlay]').is_visible(), "actual contact lane must be visible without expanding SG details"
    assert host.locator('[data-sg-contact-overlay] [data-sg-contact-state=on]').count() == 1, "actual ON distinct from 10 minute request"
    assert host.locator('[data-sg-contact-overlay] [data-sg-contact-state=off]').count() == 1, "actual OFF explicit"
    assert host.locator('[data-sg-contact-overlay] [data-sg-contact-state=unknown]').count() == 1, "gap cannot appear OFF"
    assert "5 min AAN" in host.locator('[data-sg-contact-overlay]').inner_text(), "contact actual duration"
    assert "57 °C" in host.locator('[data-tank-history]').inner_text() and "50 °C" in host.locator('[data-tank-history]').inner_text() and "Ingesteld doel" in host.locator('[data-tank-history]').inner_text(), "recorded tank/ordinary target directly visible"
    assert host.locator('[data-support-history]').is_visible(), "electrical support beside primary task"
    assert host.locator('[data-session-support]').count() == 1, "support retains its own session interval"
    assert host.locator('[data-session-tank]').count() == 1, "tank readings scoped to session"
    assert host.locator('[role=switch],[data-action=sg_boost_enabled],[data-action=manual_start]').count() == 0, "history contains no device controls"
    host.locator('details[data-history-key=sg]>summary').click()
    visible_text(host.locator('[data-sg-history=request]>.duration'), "10 min", "independent SG request runtime")
    visible_text(host.locator('[data-sg-history=contact]>.duration'), "5 min", "confirmed actual SG contact runtime")
    visible_text(host.locator('[data-sg-history=received]>.duration'), "—", "unknown Panasonic SG reception")
    assert "extra verbruik door SG is niet vastgesteld" in dialog.inner_text(), "SG causal energy must remain unclaimed"
    host.locator('details[data-history-key=coverage]>summary').click()
    assert "Ontbrekende perioden blijven onbekend" in dialog.inner_text(), "gaps must remain unknown"
    host.locator('details[data-history-key=native]>summary').click()
    native = host.locator('details[data-history-key=native]')
    assert "Native ruimtekring in rust" in native.inner_text(), "scoped idle cannot become whole-HP inactivity"
    assert "57 °C" in native.inner_text() and "50 °C" in native.inner_text(), "temperature and ordinary target remain separate"
    assert "57,5 °C" in native.inner_text() and "SG-doel bij AAN · berekend" in native.inner_text(), "stored calculated preview remains conditional"
    assert "Effectief doel" in native.inner_text() and "Native voltooiing" in native.inner_text(), "unknown programme target/result remain separate"
    assert "12:40" in native.inner_text() and "12:39" in native.inner_text(), "capturetime must remain distinct from original reports"
    assert "0 W" in native.inner_text() and "onbruikbaar / ontbreekt" in native.inner_text(), "true zero and unknown feed stay different"
    host.locator('details[data-history-key=electrical]>summary').click()
    electrical = host.locator('details[data-history-key=electrical]')
    assert "5 s" in electrical.inner_text() and "≤ 30 s" in electrical.inner_text(), "short raw activity remains visible"
    assert "compressorstarts" in electrical.inner_text() and "Geen perioden samengevoegd" in electrical.inner_text(), "raw interval semantics remain explicit"
    for width in (320, 390, 768, 1280):
        page.set_viewport_size({"width": width, "height": 1000})
        assert dialog.evaluate("d=>d.scrollWidth<=d.clientWidth+1"), (width, "new open evidence table must scroll within the modal")
        assert page.evaluate("c._heatpumpHistoryDialog._scroll.scrollWidth<=c._heatpumpHistoryDialog._scroll.clientWidth+1"), (width, "new proof overflow outside scroll wrapper")
    page.set_viewport_size({"width": 390, "height": 844})

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
    for key in ("sg", "coverage", "native", "electrical"):
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

    # New live task and calculated goal use original typed status/contact
    # fields. Rendering and a changing request never send device commands.
    page.evaluate("""()=>{
      const a=structuredClone(c._last.attributes),now=Date.now()/1000,p=a.panasonic;
      p.source_stale_s=120;p.display_tank={available:true,temperature_c:49,temperature_stamp:now,
        target_c:50,target_stamp:now};
      p.native_task={source:'aquarea_poll',observed_at:now,stale_s:120,inactive:true,
        inactive_action:'off',inactive_scope:'global',verified_global_off:true};
      p.source_contract={schema:1,read_only:true,status:'verified',
        contract_id:'aioaquarea_ng_1_3_1_special_status',action_semantics:'special_status',
        provider:{integration_domain:'aquarea',integration_version:'1.5.3',library_distribution:'aioaquarea-ng',library_version:'1.3.1'},
        raw_device_action:'OFF',pump:{state:'on',observed_at:now},direction:{state:'PUMP',observed_at:now},
        program:{state:'heating',observed_at:now},tank:{enabled:true,observed_at:now},
        zones:[{enabled:true,state:'heat',observed_at:now}]};
      p.operation_display={read_only:true,model_eligible:false,context:'space_heating',function:'space_heating',
        tier:'derived',source:'aquarea_contract',kind:'coherent_native_context',
        source_contract_id:'aioaquarea_ng_1_3_1_special_status',observed_at:now,valid_until:now+120,
        active:true,activity_observed_at:now,activity_valid_until:now+120,stale_s:120,
        support:{active:false,watts:0,observed_at:now,valid_until:now+120},
        reason:'Afgeleid uit actuele broncontext',action:''};
      p.sg_tank_goal={read_only:true,source:'local_confirmed_profile',normal_target_c:50,normal_target_reported_at:now,
        calculated_c:57.5,profile_percent:115,profile_confirmed_at:now-60,valid_until:now+120};
      a.sg_boost={...a.sg_boost,observed_at:now,relay_observed_at:now,relay_confirmed:true,
        relay_on:true,desired_on:false,relay_valid_until:now+120,relay_stale_s:120};
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};
    }""")
    assert host.locator('dialog').is_visible(), "new live evidence cannot replace the native popup"
    visible_text(page.locator('solar-pilot-card >> [data-heatpump-task] strong'), "Verwarmen", "known typed contract resolves space task")
    live_tank=page.locator('solar-pilot-card >> [data-boiler-temperatures]')
    assert "49 °C" in live_tank.inner_text() and "50 °C" in live_tank.inner_text(), "actual tank and normal goal"
    assert "57,5 °C" in live_tank.inner_text() and "SG-doel · berekend" in live_tank.inner_text(), "actual closed contact plus calculated goal"
    page.evaluate("()=>{const s=c._last.attributes.sg_boost;s.relay_on=false;s.desired_on=true;c._refreshObservationDisplay();}")
    assert "SG-doel bij AAN · berekend" in live_tank.inner_text(), "request cannot be actual closed contact"
    page.evaluate("()=>{c._last.attributes.sg_boost.relay_confirmed=false;c._refreshObservationDisplay();}")
    assert "57,5 °C" not in live_tank.inner_text(), "unknown contact keeps preview out of concise overview"
    assert "SG-doel bij AAN · berekend" in page.locator('solar-pilot-card >> [data-heatpump-provenance]').text_content(), "conditional expanded preview remains available"
    page.evaluate("()=>{c._last.attributes.panasonic.sg_tank_goal.valid_until=Date.now()/1000-1;c._refreshObservationDisplay();}")
    assert "57,5 °C" not in page.locator('solar-pilot-card >> [data-heatpump-provenance]').text_content(), "expired ordinary source cannot retain a computed target"
    assert page.evaluate("c._heatpumpHistoryDialog._dialog===hpDialogNode && hpDialogNode.open"), "live task/goal refresh preserves modal node"

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
    assert not dialog.is_visible() and page.evaluate("c._heatpumpHistoryDialog._timer===null && c._heatpumpHistoryDialog._readingTimer===null"), "Escape closes dialog and polling"
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
    assert not dialog.is_visible() and page.evaluate("c._heatpumpHistoryDialog._timer===null && c._heatpumpHistoryDialog._readingTimer===null"), "entry change closes history from prior installation"
    page.evaluate("""()=>{const a=structuredClone(c._last.attributes);a.config_entry_id='fictional-entry';
      c.hass={...c._hass,states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};c._openHeatpumpHistory();}""")
    page.wait_for_function("c._heatpumpHistoryDialog._data!==null")
    page.evaluate("""()=>{const d=c._heatpumpHistoryDialog;window.hpSeqBeforeClose=d._seq;
      d._hass={...c._hass,callWS:()=>new Promise(resolve=>setTimeout(()=>resolve(hpFixtures['2026-10-11']),80))};
      d._fetch(true);c.remove();}""")
    page.wait_for_timeout(120)
    assert page.evaluate("!c._heatpumpHistoryDialog._isOpen && !c._heatpumpHistoryDialog._dialog.open && c._heatpumpHistoryDialog._timer===null && c._heatpumpHistoryDialog._readingTimer===null && c._heatpumpHistoryDialog._seq>hpSeqBeforeClose"), "unload invalidates pending fetch and closes polling"
    assert page.evaluate("hpWrites.length===0"), "history must never send actuator/service writes"
    assert not errors, ("browser errors", errors)
    browser.close()

print("Heatpump history browser checks passed: native popup; 80 renders; date/scroll/Details; 7/30 days; racing responses; separate tasks/SG/whole-HP energy; unknown gaps; three views at 320/390/768/1280; XSS; Escape/close/unload; no writes. All data are fictitious.")
