"""Execute the shipped read-only heatpump history renderer with fictitious evidence.

Real modal lifecycle and responsive layout are exercised by the browser gate.
"""
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from test_overview_details60 import Markup
from test_heatpump_ui65 import sample
from test_sg_ui_platforms62 import execute


CARD = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot/frontend/solar-pilot-card.js"


def history_fixture():
    session = dict(segment_start="2026-10-12T06:00:00+02:00",
                   segment_end="2026-10-12T07:00:00+02:00", duration_s=3600,
                   left_pct=25, width_pct=100 / 24, start_confirmed=True,
                   start_reason="Native activiteit waargenomen",
                   stop_reason="Native einde waargenomen")
    return dict(date="2026-10-12", today="2026-10-12", first_date="2026-10-01",
                timezone="Europe/Brussels", has_data=True, on_s=3600, starts=1,
                stops=1, known_s=36000, unobserved_s=7200, partial=True,
                day_seconds=86400, energy_kwh=1.25, energy_known_s=3400,
                recording_since="2026-10-01", sessions=[session],
                task_sessions=[dict(session, task="tapwater_heating",
                                    label="Boiler opwarmen", tier="derived")],
                task_totals=[dict(task="tapwater_heating", label="Boiler opwarmen",
                                  tier="derived", on_s=3600)],
                days=[dict(date="2026-10-11", on_s=None, energy_kwh=None),
                      dict(date="2026-10-12", on_s=3600, energy_kwh=1.25)],
                sg=dict(request=dict(has_data=True, on_s=600, known_s=7200,
                                     sessions=[dict(session, duration_s=600)]),
                        contact=dict(has_data=True, on_s=0, known_s=7200, sessions=[]),
                        received=dict(has_data=False, on_s=0, sessions=[])))


def render_history(data):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required to execute the actual frontend")
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}}};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
sandbox.input=input;
const result=vm.runInContext(`(()=>{
  const dialog=Object.create(SolarPilotHeatpumpHistoryDialog.prototype);
  dialog._data=input;dialog._range=7;dialog._entryId='fictional-entry';
  dialog._body={innerHTML:'',querySelectorAll:()=>[]};dialog._scroll={scrollTop:0};
  dialog.shadowRoot={activeElement:null};dialog._renderData();
  return{html:dialog._body.innerHTML,request:dialog._historyRequest()};
})()`,sandbox);process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run([node, "-e", script, str(CARD)], input=json.dumps(data),
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def test_history_keeps_tasks_energy_and_three_sg_layers_separate():
    rendered = render_history(history_fixture())
    root = Markup(rendered["html"]).root
    text = root.text()
    assert "1 u 0 min" in text and "1,25 kWh" in text
    assert "Boiler opwarmen" in text and "Afgeleid" in text
    assert "SG-aanvraag" in text and "SG-contact" in text and "Panasonic SG-ontvangst" in text
    assert "Geen betrouwbare registratie" in text
    assert "extra verbruik door SG is niet vastgesteld" in text
    assert "SolarPilot-start" not in text
    assert rendered["request"] == {"type": "solar_pilot/heatpump_history",
                                   "config_entry_id": "fictional-entry"}
    assert {n.attributes["data-sg-history"] for n in root.walk()
            if "data-sg-history" in n.attributes} == {"request", "contact", "received"}
    assert not any(n.attributes.get("role") == "switch" for n in root.walk())
    assert {n.attributes.get("data-action") for n in root.walk()
            if n.tag == "button"} == {"range", None}


def test_unregistered_days_and_unmetered_energy_are_unknown():
    data = history_fixture()
    data.update(has_data=False, on_s=0, starts=0, stops=0, energy_kwh=None,
                energy_known_s=0, task_sessions=[], task_totals=[], sessions=[])
    root = Markup(render_history(data)["html"]).root
    for key in ("data-total", "data-starts", "data-stops", "data-energy"):
        assert next(n for n in root.walk() if key in n.attributes).text() == "—"
    missing = next(n for n in root.walk() if "missing" in n.attributes.get("class", ""))
    assert "geen registratie" in missing.attributes["aria-label"]
    assert "0m" not in missing.text()


def test_labels_reasons_events_and_dates_cannot_inject_markup():
    data = history_fixture()
    payload = '<img src=x onerror="window.injected=true">'
    data["task_sessions"][0]["label"] = payload
    data["task_totals"][0]["label"] = payload
    data["sessions"][0]["start_reason"] = payload
    data["events"] = [dict(at="2026-10-12T06:00:00+02:00", reason=payload)]
    data["note"] = payload
    root = Markup(render_history(data)["html"]).root
    assert payload in root.text()
    assert not any(n.tag == "img" for n in root.walk())
    assert not any(k.startswith("on") for n in root.walk() for k in n.attributes)


def test_timeline_clamps_percentages_and_uses_ha_timezone_for_clock():
    data = history_fixture()
    data["task_sessions"][0].update(left_pct=-9, width_pct=900)
    rendered = render_history(data)["html"]
    assert 'left:0%;width:100%' in rendered
    # CI and local Node normally run UTC; displayed wall clocks must use HA time.
    assert "06:00 – 07:00" in Markup(rendered).root.text()


def test_repeated_dst_hour_is_distinguished_with_timezone_offsets():
    data = history_fixture()
    data["day_seconds"] = 90000
    for section in ("sessions", "task_sessions"):
        data[section][0].update(segment_start="2026-10-25T02:30:00+02:00",
                                segment_end="2026-10-25T02:30:00+01:00")
    rendered = render_history(data)["html"]
    assert "02:30 GMT+2" in rendered and "02:30 GMT+1" in rendered
    assert "25 uur (tijdwissel)" in rendered


def test_unconfirmed_end_and_truncated_task_details_are_explicit():
    data = history_fixture()
    data["sessions"][0].update(ongoing=False, stop_confirmed=False, stop_reason=None)
    data["task_sessions_truncated"] = True
    text = Markup(render_history(data)["html"]).root.text()
    assert "Einde onbekend" in text and "laatst waargenomen" in text
    assert "Geen stop bevestigd" in text
    assert "Oudste taakperioden zijn niet meer volledig" in text
    assert "loopt nog" not in text


@pytest.mark.parametrize("view", ["board", "comfort"])
def test_heatpump_history_entry_does_not_expose_retained_totals_before_authorized_query(view):
    data = sample()
    data["panasonic"]["history"] = dict(on_s=7800, revision=1)
    rendered = execute(data, view=view)
    root = Markup(rendered["initial"]).root
    button = next(n for n in root.walk()
                  if n.attributes.get("data-action") == "heatpump_history")
    assert button.text() == "Geschiedenis"
    assert not rendered["calls"]
