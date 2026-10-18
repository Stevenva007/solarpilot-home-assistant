"""Independent source-bound period rendering probes, using the shipped card."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from custom_components.solar_pilot.heatpump_history import HeatpumpHistory
from test_heatpump_history70 import BASE, observe
from test_heatpump_history_ui70 import history_fixture, render_history
from test_overview_details60 import Markup


CARD = Path(__file__).resolve().parents[1]/"custom_components/solar_pilot/frontend/solar-pilot-card.js"


def _run(data, code):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the real period renderer")
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}}};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
sandbox.input=input;
const result=vm.runInContext(`(()=>{
 const d=Object.create(SolarPilotHeatpumpHistoryDialog.prototype);d._data=input.data;d._range=7;
 let nodes=[],html='',writes=0;
 const body={querySelector:()=>null,querySelectorAll:selector=>
   selector==='details[open][data-history-key]'?nodes.filter(n=>n.open):
   selector==='details[data-history-key]'?nodes:[]};
 Object.defineProperty(body,'innerHTML',{get:()=>html,set:value=>{
   html=value;nodes=Array.from(value.matchAll(/<details[^>]*data-history-key="([^"]+)"/g),m=>({dataset:{historyKey:m[1]},open:false}));
 }});
 d._body=body;d._scroll={scrollTop:37};d.shadowRoot={activeElement:null};
 d._hass={callService:()=>{writes++;},callWS:()=>{writes++;}};
 const before=JSON.stringify(d._data);
 ${input.code}
})()`,sandbox);
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run([node, "-e", script, str(CARD)], input=json.dumps({"data": data, "code": code}),
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _iso(stamp):
    return datetime.fromtimestamp(stamp, timezone.utc).isoformat()


def _period(start, end, *, task="heatpump_unknown", tier="unknown", label="Taak onbekend", **fields):
    return {"segment_start": _iso(start), "segment_end": _iso(end), "duration_s": end-start,
            "task": task, "tier": tier, "label": label, **fields}


def _data():
    data = history_fixture()
    start = datetime.fromisoformat(data["date"]+"T00:00:00+02:00").timestamp()
    data.update(day_start=start, day_end=start+86400)
    data["sessions"][0].update(id=71, start=data["sessions"][0]["segment_start"])
    return data


def _project(data):
    return _run(data, """
 const parent=d._data.sessions[0],rows=d._sessionPeriods(d._data.task_sessions,parent);
 return {rows,html:d._sessionTasksHtml(rows,parent),unchanged:before===JSON.stringify(d._data),writes};
""")


def test_real_subsecond_backend_interval_is_not_reclassified_as_a_zero_duration_point():
    model = HeatpumpHistory()
    for seconds in (.1, .9):
        observe(model, BASE+timedelta(seconds=seconds), watts=1800, task=None)
    data = model.detail(None, BASE+timedelta(seconds=.9))
    raw = data["task_sessions"][0]
    assert raw["segment_start"] == raw["segment_end"] and raw["duration_s"] == .8
    result = _project(data)
    assert result["rows"][0]["period_s"] == .8
    assert "0,8 s" in Markup(result["html"]).root.text()
    assert "duur niet vastgesteld" not in result["html"]
    assert result["unchanged"] and result["writes"] == 0


def test_real_fractional_interval_crossing_one_iso_second_is_never_inflated_to_one_second():
    model = HeatpumpHistory()
    for seconds in (.95, 1.05):
        observe(model, BASE+timedelta(seconds=seconds), watts=1800, task=None)
    data = model.detail(None, BASE+timedelta(seconds=1.05))
    assert data["task_sessions"][0]["duration_s"] == .1
    result = _project(data)
    assert result["rows"][0]["period_s"] == .1
    assert "0,1 s" in Markup(result["html"]).root.text()
    assert result["unchanged"]


@pytest.mark.parametrize("day,start,end,seconds", [
    ("2026-03-29", "2026-03-28T23:00:00+00:00", "2026-03-29T22:00:00+00:00", 82800),
    ("2026-10-25", "2026-10-24T22:00:00+00:00", "2026-10-25T23:00:00+00:00", 90000),
])
def test_multi_day_parent_clips_each_interval_and_uses_half_open_local_day_for_points(day, start, end, seconds):
    data = _data()
    left, right = datetime.fromisoformat(start).timestamp(), datetime.fromisoformat(end).timestamp()
    data.update(date=day, today=day, day_start=left, day_end=right, day_seconds=seconds)
    data["sessions"][0].update(segment_start=_iso(left-3600), segment_end=_iso(right+3600),
                                duration_s=seconds+7200)
    data["task_sessions"] = [_period(left-60, left+60), _period(right-30, right+20),
                             _period(left-1, left-1), _period(left, left),
                             _period(right-.1, right-.1), _period(right, right)]
    before = deepcopy(data)
    result = _project(data)
    rows = result["rows"]
    assert [(r["period_start"], r["period_end"]) for r in rows] == [
        (left, left), (left, left+60), (right-30, right), (right-.1, right-.1)]
    assert [r["period_s"] for r in rows] == [0, 60, 30, 0]
    assert sum(r["period_s"] for r in rows) == 90
    assert not any(r["period_start"] == right for r in rows)
    assert result["unchanged"] and data == before


def test_repeated_dst_hour_shows_two_actual_offsets_and_elapsed_seconds():
    data = _data()
    start = datetime.fromisoformat("2026-10-25T00:00:00+02:00").timestamp()
    data.update(date="2026-10-25", today="2026-10-25", day_start=start, day_end=start+90000, day_seconds=90000)
    a = datetime.fromisoformat("2026-10-25T02:30:00+02:00").timestamp()
    b = datetime.fromisoformat("2026-10-25T02:30:00+01:00").timestamp()
    data["sessions"][0].update(segment_start=_iso(a), segment_end=_iso(b+30), duration_s=3630)
    data["task_sessions"] = [_period(a, b), _period(b, b+30)]
    result = _project(data)
    text = Markup(result["html"]).root.text()
    assert "02:30:00 GMT+2" in text and "02:30:00 GMT+1" in text
    assert "1 u" in text and "30 s" in text
    assert [row["period_s"] for row in result["rows"]] == [3600, 30]


def test_nested_parent_clipping_does_not_use_unclipped_raw_duration_or_drop_overlap():
    data = _data()
    parent = data["sessions"][0]
    left = datetime.fromisoformat(parent["segment_start"]).timestamp()
    parent["segment_end"] = _iso(left+60)
    parent["duration_s"] = 60
    data["task_sessions"] = [_period(left+30, left+100, task="space_heating", tier="derived", label="Verwarmen"),
                             _period(left-100, left+40), _period(left-20, left+80)]
    result = _project(data)
    assert [(r["period_start"]-left, r["period_end"]-left, r["period_s"]) for r in result["rows"]] == [
        (0, 40, 40), (0, 60, 60), (30, 60, 30)]
    assert all(row["period_clipped"] for row in result["rows"])
    assert "Getoond binnen deze sessie en dag" in result["html"]
    assert result["unchanged"] and result["writes"] == 0


def test_same_rounded_iso_boundaries_cannot_make_a_child_longer_than_its_recorded_parent():
    data = _data()
    left = datetime.fromisoformat(data["sessions"][0]["segment_start"]).timestamp()
    data["sessions"][0].update(segment_end=_iso(left+1), duration_s=.1)
    data["task_sessions"] = [_period(left, left+1, duration_s=.8)]
    result = _project(data)
    assert result["rows"][0]["period_s"] == .1
    assert "0,1 s" in Markup(result["html"]).root.text()
    assert result["unchanged"]


def test_invalid_periods_are_omitted_without_reinterpreting_valid_neighbouring_unknowns():
    data = _data()
    left = datetime.fromisoformat(data["sessions"][0]["segment_start"]).timestamp()
    data["task_sessions"] = [None, {"segment_start": "invalid", "segment_end": "invalid"},
                             _period(left+20, left+10), _period(left+25, left+28)]
    result = _project(data)
    assert len(result["rows"]) == 1
    assert result["rows"][0]["task"] == "heatpump_unknown"
    assert result["rows"][0]["tier"] == "unknown" and result["rows"][0]["period_s"] == 3
    assert result["unchanged"] and result["writes"] == 0


def test_many_unknown_intervals_keep_counts_points_and_all_raw_chronology_without_new_totals():
    data = _data()
    left = datetime.fromisoformat(data["sessions"][0]["segment_start"]).timestamp()
    rows = [_period(left+n*10, left+n*10+3) for n in range(9)]
    rows += [_period(left+95, left+95), _period(left+97, left+97)]
    rows += [_period(left+100, left+120, task="space_heating", tier="derived", label="Verwarmen")]
    data["task_sessions"] = list(reversed(rows))
    data["energy_kwh"], data["on_s"] = 9.87, 3600
    result = _project(data)
    root = Markup(result["html"]).root
    summary = next(n for n in root.walk() if "data-session-task-summary" in n.attributes)
    raw = [n for n in root.walk() if "data-session-task-period" in n.attributes]
    assert "11 waarnemingen" in summary.text() and "2 meetpunten zonder vastgestelde duur" in summary.text()
    assert "27 s" in summary.text() and "20 s" in summary.text()
    assert len(raw) == 12 and "Alle 12 taakperioden en meetpunten" in root.text()
    assert [r["period_start"] for r in result["rows"]] == sorted(r["period_start"] for r in result["rows"])
    assert result["unchanged"] and result["writes"] == 0
    assert data["energy_kwh"] == 9.87 and data["on_s"] == 3600


def test_preserved_overlapping_history_is_not_deduplicated_or_added_to_parent_and_day_totals():
    model = HeatpumpHistory()
    observe(model, BASE, watts=1800, task=None)
    observe(model, BASE+timedelta(seconds=5), watts=1800, task=None)
    saved = model.snapshot()
    lane = saved["tasks"]["devices"]["heatpump_unknown:unknown"]
    original = lane["sessions"][0]
    lane["sessions"] = [{**deepcopy(original), "id": index} for index in range(1, 10)]
    restored = HeatpumpHistory()
    restored.restore(saved, BASE+timedelta(seconds=10))
    data = restored.detail(None, BASE+timedelta(seconds=10))
    assert len(data["task_sessions"]) == 9 and data["on_s"] == 5
    before = deepcopy(data)
    result = _run(data, "d._renderData();return {html,unchanged:before===JSON.stringify(d._data),writes};")
    root = Markup(result["html"]).root
    assert len([n for n in root.walk() if "data-session-task-period" in n.attributes]) == 9
    summary = next(n for n in root.walk() if "data-session-task-summary" in n.attributes)
    assert "9 waarnemingen" in summary.text()
    overlap = next(n for n in root.walk() if "data-session-period-overlap" in n.attributes)
    assert "Opgetelde duur" in overlap.text() and "geen extra sessielooptijd" in overlap.text()
    assert next(n for n in root.walk() if "data-total" in n.attributes).text() == "5 s"
    parent_head = next(n for n in root.walk() if n.attributes.get("class") == "session-head")
    assert "5 s" in parent_head.text()
    assert data == before and result["unchanged"] and result["writes"] == 0


def test_support_is_not_absorbed_into_primary_summary_or_unknown_period_count():
    data = _data()
    left = datetime.fromisoformat(data["sessions"][0]["segment_start"]).timestamp()
    data["task_sessions"] = [_period(left+n*10, left+n*10+3) for n in range(9)]
    data["support_sessions"] = [_period(left+20, left+60, task="electrical_support", tier="derived", label="Elektrische ondersteuning")]
    html = render_history(data)["html"]
    root = Markup(html).root
    summary = next(n for n in root.walk() if "data-session-task-summary" in n.attributes)
    assert "9 waarnemingen" in summary.text() and "Elektrische ondersteuning" not in summary.text()
    support = [n for n in root.walk() if "data-session-support" in n.attributes]
    assert len(support) == 1 and "40 s" in support[0].text()


def test_labels_parent_keys_and_source_reasons_cannot_inject_active_markup():
    data = _data()
    payload = '<img src=x onerror="window.injected=true">'
    left = datetime.fromisoformat(data["sessions"][0]["segment_start"]).timestamp()
    data["sessions"][0].update(id=payload, start=payload, start_reason=payload)
    data["task_sessions"] = [_period(left+n*10, left+n*10+3, label=payload) for n in range(9)]
    html = render_history(data)["html"]
    root = Markup(html).root
    assert payload in root.text()
    assert not any(n.tag in ("img", "script", "svg") for n in root.walk())
    assert not any(key.startswith("on") for n in root.walk() for key in n.attributes)


def test_expanded_raw_period_details_survive_same_day_refresh_without_payload_or_actuator_mutation():
    data = _data()
    left = datetime.fromisoformat(data["sessions"][0]["segment_start"]).timestamp()
    data["task_sessions"] = [_period(left+n*10, left+n*10+3) for n in range(9)]
    result = _run(data, """
 d._renderData();const initial=nodes.find(n=>n.dataset.historyKey.startsWith('session-tasks:'));
 if(!initial)return {missing:true};initial.open=true;const key=initial.dataset.historyKey;
 d._renderData();const same=nodes.find(n=>n.dataset.historyKey===key);
 const unchanged=before===JSON.stringify(d._data);
 d._data={...d._data,date:'2026-10-13',today:'2026-10-13',day_start:d._data.day_start+86400,day_end:d._data.day_end+86400,
   sessions:d._data.sessions.map(s=>({...s,segment_start:new Date(Date.parse(s.segment_start)+86400000).toISOString(),segment_end:new Date(Date.parse(s.segment_end)+86400000).toISOString()})),
   task_sessions:d._data.task_sessions.map(s=>({...s,segment_start:new Date(Date.parse(s.segment_start)+86400000).toISOString(),segment_end:new Date(Date.parse(s.segment_end)+86400000).toISOString()}))};
 d._renderData();const other=nodes.find(n=>n.dataset.historyKey.startsWith('session-tasks:'));
 return {sameOpen:same?.open,sameKey:key,otherOpen:other?.open,otherKey:other?.dataset.historyKey,unchanged,writes};
""")
    assert result.get("sameOpen") is True
    assert result["otherOpen"] is False and result["sameKey"] != result["otherKey"]
    assert result["unchanged"] and result["writes"] == 0
