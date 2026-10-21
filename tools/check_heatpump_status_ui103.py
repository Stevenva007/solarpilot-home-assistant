"""Backend-classified current and recorded tasks in real Chromium; no writes."""
from copy import deepcopy
import os
from pathlib import Path
import shutil
import sys
import time

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
# Only the backend's HA import boundary is doubled. The classifiers, recorder,
# shipped card and native browser dialogs below execute their actual code.
import conftest  # noqa: E402, F401
from test_heatpump_status_ui103 import status_history, status_snapshot  # noqa: E402

output = Path(sys.argv[1] if len(sys.argv) > 1 else "/tmp/solarpilot-browser-tests")
output.mkdir(parents=True, exist_ok=True)
now = int(time.time())
cases = {"heating": status_snapshot(now=now), "cooling": status_snapshot(function="space_cooling", now=now),
         "water": status_snapshot(function="tapwater_heating", now=now),
         "legacy": status_snapshot(mapping="special", now=now)}
for name in ("unverified", "cross_marker", "cached", "expired"):
    cases[name] = deepcopy(cases["heating"])
cases["unverified"]["panasonic"]["source_contract"]["compatibility"]["verified"] = False
cases["cross_marker"]["panasonic"]["source_contract"]["compatibility"]["contract"] = "aquarea_special_status_action_v1"
cases["cached"]["panasonic"]["source_contract"]["status_data_mode"] = "CACHED"
cases["expired"]["panasonic"]["operation_display"].update(observed_at=now-121, valid_until=now-1)
history = status_history(now=now)
errors = []
executable = os.environ.get("SOLARPILOT_CHROMIUM_PATH") or shutil.which("chromium") or shutil.which("google-chrome")

with sync_playwright() as p:
    browser = p.chromium.launch(**({"executable_path": executable} if executable else {}),
                                headless=True, args=["--no-sandbox"])
    page = browser.new_page(viewport={"width": 390, "height": 844}, locale="nl-BE")
    page.on("pageerror", lambda error: errors.append(str(error)))
    shipped = (ROOT / "custom_components/solar_pilot/frontend/solar-pilot-card.js").read_text(encoding="utf-8")
    example = (ROOT / "SolarPilot-voorbeeld.html").read_text(encoding="utf-8")
    assert shipped in example, "Rebuild the offline example before running the browser checks"
    page.set_content(example, wait_until="load")
    page.wait_for_selector("solar-pilot-card >> h1")
    page.evaluate("""payload=>{
      window.c=document.querySelector('solar-pilot-card');window.statusCases=payload.cases;
      window.statusHistory=payload.history;window.statusWrites=[];window.statusReads=[];
      window.statusRead=async message=>{statusReads.push(message);
        if(message.type!=='solar_pilot/heatpump_history'||message.config_entry_id!=='fictional-status-entry'||'device_id' in message)throw Error('Unexpected read');
        return structuredClone(statusHistory);};
      window.applyStatus=name=>{const attributes={...structuredClone(c._last.attributes),...structuredClone(statusCases[name])};
        attributes.config_entry_id='fictional-status-entry';attributes.panasonic.history={recording:true,storage_available:true,revision:1};
        c.hass={...c._hass,callWS:statusRead,callService:async(...args)=>statusWrites.push(args),
          states:{...c._hass.states,[c._entity]:{state:'ready',attributes}}};};
      applyStatus('heating');
    }""", {"cases": cases, "history": history})
    card = page.locator("solar-pilot-card")

    for width in (320, 390):
        page.set_viewport_size({"width": width, "height": 844})
        for view in ("overview", "comfort", "loads"):
            card.locator(f".nav > button[data-action=view][data-value={view}]").click()
            for name, label in (("heating", "Verwarmen"), ("cooling", "Koelen"),
                                ("water", "Boiler opwarmen"), ("legacy", "Verwarmen")):
                page.evaluate("name=>applyStatus(name)", name)
                task = card.locator("[data-heatpump-task]")
                assert task.count() == 1 and label in task.inner_text(), (width, view, name)
                assert task.get_attribute("data-heatpump-task") == "inferred"
                assert "onbekend" not in task.inner_text().lower()
                assert "afgeleid uit verbruik en Panasonic-context" in card.locator("[data-heatpump-provenance]").text_content()
            for name in ("unverified", "cross_marker", "cached", "expired"):
                page.evaluate("name=>applyStatus(name)", name)
                assert "Actief · taak onbekend" in card.locator("[data-heatpump-task]").inner_text(), (view, name)
        card.locator(".nav > button[data-action=view][data-value=overview]").click()
        page.evaluate("applyStatus('heating')")
        task = card.locator("[data-heatpump-task]")
        task.scroll_into_view_if_needed()
        page.screenshot(path=str(output / f"SolarPilot-beta103-active-heating-{width}.png"))
        assert task.evaluate("el=>el.getBoundingClientRect().left>=0&&el.getBoundingClientRect().right<=innerWidth+1"), width

    card.locator(".nav > button[data-action=view][data-value=comfort]").click()
    card.locator('details[data-ui-key="sg:comfort:details"] > summary').click()
    source = card.locator("[data-panasonic-source-contract]")
    source.locator("summary").focus()
    page.keyboard.press("Enter")
    assert source.get_attribute("open") is not None
    proof = " ".join(source.inner_text().split())
    assert "Oorspronkelijke Panasonic-bronstatus HEATING" in proof
    assert "Hoofdtoestel ingeschakeld Ja" in proof
    assert "geen zelfstandig bewijs van warmteproductie" in source.inner_text()
    assert page.evaluate("statusReads.length===0&&statusWrites.length===0")

    card.locator("button[data-action=heatpump_history]").click()
    host = card.locator("[data-heatpump-history-dialog]")
    page.wait_for_function("c._heatpumpHistoryDialog._data!==null")
    assert "Verwarmen" in host.locator("[data-task-totals]").inner_text()
    assert "Afgeleid" in host.locator("[data-task-totals]").inner_text()
    assert "Taak onbekend" not in host.locator("[data-task-totals]").inner_text()
    native = host.locator('[data-history-key="native"]')
    native.locator("summary").click()
    assert "Panasonic-bronstatus: HEATING" in native.inner_text()
    assert "Bronmapping bij vastlegging bevestigd" in native.inner_text()
    page.evaluate("window.statusDialog=c._heatpumpHistoryDialog;window.statusDialogNode=c._heatpumpHistoryDialog._dialog;for(let i=0;i<40;i++)applyStatus('heating')")
    assert page.evaluate("c._heatpumpHistoryDialog===statusDialog&&c._heatpumpHistoryDialog._dialog===statusDialogNode&&statusDialogNode.open")
    page.keyboard.press("Escape")
    assert not host.locator("dialog").evaluate("el=>el.open")
    assert page.evaluate("statusWrites.length===0"), "The UI must never send control actions"
    assert not errors, errors
    browser.close()

print("Heatpump status103 browser checks passed: real backend and recorder; both verified semantic mappings; heating/cooling/water in three views at 320/390; mismatched/cache/expired evidence unknown; keyboard provenance; recorded derived history; telemetry/dialog lifecycle; zero control writes. All readings are fictitious.")
