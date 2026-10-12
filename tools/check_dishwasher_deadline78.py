"""Actual deadline UI with source-generated, fictional HA-double telemetry.

Both dashboard views run in an isolated browser with all networking blocked.
Runtime fixture commands target only the existing in-memory HA test doubles;
the browser cannot call Home Assistant or any real appliance.
"""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get("SOLARPILOT_SCREENSHOT_DIR", "/tmp/solarpilot-browser-tests"))
OUT.mkdir(parents=True, exist_ok=True)

FIXTURE_SCRIPT = r'''
import asyncio, json, sys, time
from copy import deepcopy
import pytest
sys.path.insert(0, "tests")
import conftest
from test_dishwasher_app31 import configured, event, move, ready

async def fixtures():
    with pytest.MonkeyPatch.context() as patch:
        clock = [10_000.0]
        patch.setattr(time, "monotonic", lambda: clock[0])
        r,h,c,w = configured(patch, "2026-09-30T14:14",
            dishwasher_start_deadline="14:15:00", start_delay_s=300,
            start_margin_w=100, dishwasher_deadline_grid_allowed=False)
        c["name"] = "Afwasmachine · fictief softwarevoorbeeld"
        r.settings.update(max_import_w=4000, pv_entity="sensor.example_pv")
        h.states.set("sensor.example_pv", 0, {"unit_of_measurement":"W"})
        h.states.set("sensor.grid", 3100, {"unit_of_measurement":"W"})
        ready(r,h,c,w)
        await r.tick()
        clock[0] += 120
        move(h,w,"2026-09-30T14:16")
        await r.tick()
        blocked = deepcopy(r.overview()[0])
        allocation = blocked["start_diagnostics"]["power"]["allocation"]
        assert allocation["available_w"] == 900 and allocation["required_w"] == 2000
        assert allocation["grid_allowed"] and blocked["dishwasher"]["deadline_due"]
        assert not [x for x in h.services.calls if x[:2] == ("button","press")]
        clock[0] += 120
        move(h,w,"2026-09-30T14:35")
        h.states.set("sensor.grid", 400, {"unit_of_measurement":"W"})
        await r.tick()
        pending = deepcopy(r.overview()[0])
        assert pending["dishwasher"]["request_status"] == "start_requested"
        clock[0] += 60
        move(h,w,"2026-09-30T14:36")
        event(r,h,c,w,"dishwasher_state_entity","Running")
        await r.tick()
        running = deepcopy(r.overview()[0])
        assert running["dishwasher"]["request_status"] == "running"
        assert not running["dishwasher"]["app_request"]
        assert not running["dishwasher"]["ticket_armed"]
        assert running["dishwasher"]["start_requested_at"] != running["dishwasher"]["start_confirmed_at"]
        assert len([x for x in h.services.calls if x[:2] == ("button","press")]) == 1
        unknown = deepcopy(running)
        unknown.update(available=False, on=False, owned=False, power_w=None,
            reason="Fictief ontbrekende verbinding; actuele activiteit onbekend",
            start_diagnostics=None, start_requirements=None)
        unknown["dishwasher"].update(request_context=False, request_status="none",
            cycle_status=None, program="", phase="", completion=None,
            start_deadline=None, start_requested_at=None, start_confirmed_at=None,
            app_message="Geen actuele cyclusgegevens ontvangen")
        print(json.dumps({"blocked":blocked,"pending":pending,
            "running":running,"unknown":unknown}, ensure_ascii=False))

asyncio.run(fixtures())
'''

fixtures = json.loads(subprocess.check_output(
    [sys.executable, "-B", "-c", FIXTURE_SCRIPT], cwd=ROOT, text=True))


def fact(scope, label):
    """Read the value associated with one visible field, not unrelated page text."""
    return scope.locator(".start-facts > span").filter(
        has_text=re.compile("^" + re.escape(label))).first.locator("b").inner_text()


def responsive(page, scope):
    for width in (320, 390, 768, 1440):
        page.set_viewport_size({"width": width, "height": 1120})
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), width
        assert scope.evaluate("e => e.scrollWidth <= e.clientWidth + 2"), width


errors = []
with sync_playwright() as runner:
    browser = runner.chromium.launch(executable_path=shutil.which("chromium"),
        headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 1440, "height": 1120},
        locale="nl-BE", timezone_id="Europe/Brussels")
    page.route("**/*", lambda route: route.abort())
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.set_content((ROOT / "SolarPilot-voorbeeld.html").read_text(encoding="utf-8"),
        wait_until="load")
    page.wait_for_selector("solar-pilot-card >> h1")
    page.evaluate(r'''data => {
        window.c = document.querySelector('solar-pilot-card');
        window.deadlineFixtures = data; window.deviceCalls = []; window.apiCalls = [];
        window.base = structuredClone(c._last.attributes);
        base.mode = 'solar'; base.problem = ''; base.config_entry_id = 'fictitious';
        window.showDeadline = (name, patch = {}, appliance = {}) => {
            const a = structuredClone(base), d = structuredClone(deadlineFixtures[name]);
            Object.assign(d, patch); Object.assign(d.dishwasher, appliance);
            a.devices = [d];
            c.hass = {...c._hass, config:{...c._hass.config,time_zone:'Europe/Brussels'},
                user:{is_admin:true},
                callService:async(...args) => {deviceCalls.push(args);throw Error('No actuator calls');},
                callWS:async(...args) => {apiCalls.push(args);throw Error('No backend calls');},
                states:{...c._hass.states,[c._entity]:{state:'Zonnestroom',attributes:a}}};
        };
        window.liveUpdates = () => {
            for(let n=0;n<80;n++) {
                const a=structuredClone(c._last.attributes);a.grid_w=-200-n;
                c.hass={...c._hass,states:{...c._hass.states,
                    [c._entity]:{state:'Zonnestroom',attributes:a}}};
            }
        };
        showDeadline('running');
    }''', fixtures)
    assert page.evaluate("c._decisionBoard.toString().includes('Vastgelegde startdeadline')"), \
        "Preview must be built from the current beta.78 frontend"

    row = page.locator('solar-pilot-card >> [data-reason-key="overview:device:a"]')
    details = row.locator(".reason-details")
    details.locator("summary").click()
    assert "Programma loopt" in row.inner_text()
    assert fact(row, "Vrijgegeven beurt") == "gebruikt voor deze beurt"
    assert "14:15" in fact(row, "Vastgelegde startdeadline")
    assert "14:35" in fact(row, "Start aangevraagd")
    assert "14:36" in fact(row, "Start bevestigd")
    assert "nog niet klaargezet" not in row.inner_text().lower()
    page.evaluate("liveUpdates()")
    assert details.get_attribute("open") is not None
    assert "14:15" in fact(row, "Vastgelegde startdeadline")
    responsive(page, row)
    row.screenshot(path=str(OUT / "SolarPilot-beta78-afwas-startbevestiging.png"))

    page.evaluate("showDeadline('blocked')")
    assert details.get_attribute("open") is not None
    assert "netafnamegrens" in row.inner_text().lower()
    assert "900 W" in row.inner_text() and "2000 W" in row.inner_text()
    assert fact(row, "Netstroom op deadline") == "toegestaan"
    assert fact(row, "Beschikbaar voor dit toestel") == "900 W"
    assert fact(row, "Benodigd voor start") == "2 kW"
    assert "zonneoverschot niet nodig" in row.inner_text()
    assert "Van autoladen beschikbaar" not in row.inner_text()
    assert "Zonnevermogen voor dit toestel" not in row.inner_text()
    responsive(page, row)
    row.screenshot(path=str(OUT / "SolarPilot-beta78-afwas-deadline-netruimte.png"))

    page.evaluate("showDeadline('pending')")
    assert fact(row, "Vrijgegeven beurt") == "start aangevraagd"
    assert "14:35" in fact(row, "Start aangevraagd")
    assert row.locator(".start-facts > span").filter(has_text="Start bevestigd").count() == 0
    page.evaluate("showDeadline('unknown')")
    assert "Niet bereikbaar" in row.inner_text()
    assert "Vermogen nog niet bekend" in row.inner_text()
    assert fact(row, "Vastgelegde startdeadline") == "nog niet bekend"
    assert row.locator(".start-facts > span").filter(has_text="Start bevestigd").count() == 0

    page.locator('solar-pilot-card >> [data-action="view"][data-value="loads"]').click()
    card = page.locator("solar-pilot-card >> .dishwasher")
    page.evaluate("showDeadline('running')")
    assert "PROGRAMMA ACTIEF" in card.inner_text()
    assert "14:15" in card.locator(".app-plan").inner_text()
    assert "14:35" in fact(card, "Start aangevraagd")
    assert "14:36" in fact(card, "Start bevestigd")
    assert "nog niet klaargezet" not in card.inner_text().lower()
    assert card.locator("[data-action=dishwasher_arm],[data-action=dishwasher_cancel],"
        "[data-action=manual_stop],[data-action=boost]").count() == 0
    card.locator("details > summary").click()
    page.evaluate("liveUpdates()")
    assert card.locator("details").get_attribute("open") is not None
    responsive(page, card)
    card.screenshot(path=str(OUT / "SolarPilot-beta78-afwas-toestelkaart.png"))

    page.evaluate("showDeadline('blocked')")
    assert fact(card, "Netstroom op deadline") == "toegestaan"
    assert fact(card, "Beschikbaar voor dit toestel") == "900 W"
    assert fact(card, "Benodigd voor start") == "2 kW"
    assert "Zonnevermogen voor dit toestel" not in card.inner_text()
    assert card.locator("details").get_attribute("open") is not None
    responsive(page, card)

    # Text and timestamp payloads must remain text; invalid dates stay unknown.
    page.evaluate(r'''() => {
        const payload='<img src=x onerror=window.pwned=1><script>window.pwned=2</script>';
        showDeadline('running', {reason:payload,start_diagnostics:null},
            {program:payload,app_message:payload,start_deadline:payload,
             start_requested_at:payload,start_confirmed_at:payload});
    }''')
    assert card.locator("img,script").count() == 0
    assert page.evaluate("window.pwned || 0") == 0
    assert "<img" in card.inner_text()
    assert "Invalid Date" not in card.inner_text()
    assert "14:35" not in card.inner_text() and "14:36" not in card.inner_text()
    page.locator('solar-pilot-card >> [data-action="view"][data-value="overview"]').click()
    if details.get_attribute("open") is None:
        details.locator("summary").click()
    assert row.locator("img,script").count() == 0
    assert fact(row, "Vastgelegde startdeadline") == "nog niet bekend"
    assert "Invalid Date" not in row.inner_text()
    assert page.evaluate("window.pwned || 0") == 0
    page.evaluate("showDeadline('unknown')")
    assert "Niet bereikbaar" in row.inner_text()
    assert page.evaluate("deviceCalls.length === 0 && apiCalls.length === 0")
    assert not errors, errors
    browser.close()

print("OK: actual runtime-derived deadline/START/Running UI in overview and loads, "
    "consumed context without new permission, specific grid room instead of solar wait, "
    "unknown boundaries, 80 updates with preserved details, widths 320/390/768/1440, "
    "escaped text and dates, no networking or browser actuator calls. Fictional HA doubles only.")
