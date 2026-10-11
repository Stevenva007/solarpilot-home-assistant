"""Execute the compact card with independently bounded task/activity evidence.

The Node renderer verifies text, disclosures and ageing without HA appliance
calls. It does not claim browser geometry or physical warm-pump acceptance.
"""
import json
import re
import shutil
import subprocess
import time

import pytest

from test_heatpump_ui65 import metered_sample, native_task
from test_overview_details60 import Markup
from test_sg_ui_platforms62 import CARD


LABELS = {"tapwater_heating": "Boiler opwarmen", "space_heating": "Verwarmen",
          "space_cooling": "Koelen"}


def render(data, view="board", *, offsets=(0,)):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for shipped-card execution")
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const RealDate=Date,calls=[];let offset=0;
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},
 Date:class extends RealDate{static now(){return (input.now+offset)*1000;}},input,calls};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
const card=vm.runInContext('Object.create(SolarPilotCard.prototype)',sandbox);
card._last={attributes:input.attributes};card._busy=false;
card._hass={user:{is_admin:true},states:{},config:{time_zone:'Europe/Brussels'},
 callService:async(...args)=>calls.push(args)};
const html=input.offsets.map(value=>{offset=value;const c=card._ctx();
 return input.view==='board'?card._decisionBoard(c):input.view==='loads'?card._loads(c):card._comfort(c);});
process.stdout.write(JSON.stringify({html,calls}));
"""
    result = subprocess.run([node, "-e", script, str(CARD)],
        input=json.dumps({"attributes": data, "view": view, "offsets": offsets, "now": time.time()}),
        text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    result = json.loads(result.stdout)
    assert result["calls"] == [], "Rendering must never control physical devices"
    return [Markup(html).root for html in result["html"]]


def classes(node):
    return node.attributes.get("class", "").split()


def panel(root):
    found = [node for node in root.walk() if node.attributes.get("data-reason-key") == "overview:sg"
             or "heatpump-sg" in classes(node)]
    assert len(found) == 1
    return found[0]


def named(root, attribute):
    found = [node for node in panel(root).walk() if attribute in node.attributes]
    assert len(found) == 1
    return found[0]


def primary_label(root, attribute):
    item = named(root, attribute)
    return next(node for node in item.walk() if node.tag == "strong").text().strip()


def compact_text(node):
    """Text seen with default closed disclosures; hidden provenance is excluded."""
    if node.tag == "details" and "open" not in node.attributes:
        return " ".join(child.text() for child in node.children
                        if getattr(child, "tag", None) == "summary")
    return " ".join(compact_text(child) if hasattr(child, "tag") else child
                    for child in node.children)


def interpretation(function="space_heating", *, watts=1360, inactive_action="idle"):
    data = metered_sample(watts, function=function, roles=("main", "heater"))
    p = data["panasonic"]
    now = time.time()
    kind = "tank_route" if function == "tapwater_heating" else "selected_program"
    source = "aquarea_entity" if kind == "tank_route" else "native_program"
    p["operation"] = {"state": "idle", "label": "Compressor staat stil",
        "evidence": "compressor_frequency", "observed_at": now, "stale_s": 120}
    p.update(compressor_frequency_hz=0, compressor_running=False)
    p["native_task"] = {"function": None, "label": "Panasonic meldt rust", "source": "aquarea_poll",
        "inactive": True, "inactive_action": inactive_action, "observed_at": now, "stale_s": 120,
        "note": "Ruwe Panasonic-actie meldt rust; geen afzonderlijke compressor- of SG-reactie."}
    p["task_context"] = {"function": function, "label": "Gekozen stand uit oorspronkelijke bron",
        "source": source, "kind": kind, "observed_at": now, "stale_s": 120,
        "note": "Gekozen stand of tankroute is context zonder zelfstandige actiebevestiging."}
    p["power_activity"].update(activity_kind="main", function_kind=kind, function_source=source)
    return data


@pytest.mark.parametrize("view", ["board", "comfort", "loads"])
@pytest.mark.parametrize("function,label", LABELS.items())
def test_active_main_and_fresh_compatible_context_have_one_compact_task(view, function, label):
    root, = render(interpretation(function), view)
    assert panel(root).attributes["data-activity"] == "active"
    assert primary_label(root, "data-heatpump-operation") == label
    assert primary_label(root, "data-heatpump-task") == label
    assert named(root, "data-heatpump-task").attributes["data-heatpump-task"] == "inferred"
    if view == "board":
        badges = [node for node in panel(root).walk() if "badge" in classes(node)]
        assert len(badges) == 1 and badges[0].text().strip() == label
    visible = compact_text(panel(root))
    assert "Afgeleid" in visible
    assert "Panasonic meldt rust" not in visible
    assert "0 Hz" not in visible
    assert "zelfstandige actiebevestiging" not in visible
    assert "geen afzonderlijke compressor" not in visible
    proof = named(root, "data-heatpump-provenance")
    assert "Compressor staat stil" in proof.text()
    assert "Panasonic meldt rust" in proof.text()
    assert "Gekozen stand" in proof.text()
    assert "is-active" in classes(panel(root))


@pytest.mark.parametrize("inactive_action", ["off", None])
def test_explicit_off_or_legacy_idle_does_not_adopt_a_cached_context_function(inactive_action):
    root, = render(interpretation(inactive_action=inactive_action))
    assert primary_label(root, "data-heatpump-operation") == "Warmtepomp werkt"
    assert primary_label(root, "data-heatpump-task") != "Verwarmen"
    assert named(root, "data-heatpump-task").attributes["data-heatpump-task"] != "inferred"
    assert panel(root).attributes["data-activity"] == "active"


@pytest.mark.parametrize("function,label", LABELS.items())
def test_fresh_explicit_native_task_precedes_chosen_context_in_all_compact_labels(function, label):
    data = native_task(interpretation("space_cooling"), function)
    root, = render(data)
    assert primary_label(root, "data-heatpump-operation") == label
    assert primary_label(root, "data-heatpump-task") == label
    assert named(root, "data-heatpump-task").attributes["data-heatpump-task"] == "native"


def test_fresh_defrost_precedes_both_native_heating_and_selected_cooling():
    data = native_task(interpretation("space_cooling"), "space_heating")
    data["panasonic"]["defrost"] = {"state": "active", "source": "aquarea_poll",
        "observed_at": time.time(), "stale_s": 120}
    root, = render(data)
    assert primary_label(root, "data-heatpump-operation") == "Ontdooien"
    assert primary_label(root, "data-heatpump-task") == "Ontdooien"
    assert "Verwarmen" not in compact_text(named(root, "data-heatpump-task"))
    assert "Koelen" not in compact_text(named(root, "data-heatpump-task"))


def test_conflicting_current_tasks_keep_activity_but_never_become_chosen_heating():
    data = interpretation()
    task = data["panasonic"]["native_task"]
    task.pop("inactive")
    task.update(conflict=True, label="Panasonic-taak niet eenduidig")
    root, = render(data)
    assert primary_label(root, "data-heatpump-operation") == "Warmtepomp werkt"
    assert primary_label(root, "data-heatpump-task") != "Verwarmen"
    assert panel(root).attributes["data-activity"] == "active"
    assert "niet eenduidig" in named(root, "data-heatpump-provenance").text()


@pytest.mark.parametrize("watts", [0, 58, 199])
def test_selected_context_alone_or_below_activity_threshold_is_details_only(watts):
    root, = render(interpretation(watts=watts))
    assert panel(root).attributes["data-activity"] == "inactive"
    assert named(root, "data-heatpump-task").attributes["data-heatpump-task"] != "inferred"
    assert "Verwarmen" not in compact_text(named(root, "data-heatpump-task"))
    assert "Gekozen stand" in named(root, "data-heatpump-provenance").text()


@pytest.mark.parametrize("case", ["partial", "heater_only", "unconfirmed_roles"])
def test_inference_requires_complete_fresh_active_main_with_a_confirmed_feed_role(case):
    data = interpretation()
    p = data["panasonic"]
    pa = p["power_activity"]
    if case == "partial":
        p.update(power_complete=False, power_w=None, power_supply2_valid=False)
        pa.update(complete=False, total_w=None, state="partial")
        pa["supplies"][1].update(valid=False, watts=None, state="unknown", observed_at=None)
    elif case == "heater_only":
        p.update(power_supply1_w=0, power_supply2_w=1360)
        pa.update(activity_kind="heater")
        pa["supplies"][0].update(watts=0, state="off")
        pa["supplies"][1].update(watts=1360, state="active")
    else:
        for row in pa["supplies"]:
            row["role"] = "unconfirmed"
    root, = render(data)
    assert named(root, "data-heatpump-task").attributes["data-heatpump-task"] != "inferred"
    assert primary_label(root, "data-heatpump-operation") != "Verwarmen"
    assert primary_label(root, "data-heatpump-task") != "Verwarmen"
    if case == "heater_only":
        assert named(root, "data-heatpump-operation").attributes["data-fan-active"] == "false"


@pytest.mark.parametrize("which", ["pa_context", "selected_context"])
@pytest.mark.parametrize("stamp", [None, "stale", "future"])
def test_new_power_and_sg_cannot_freshen_an_expired_context_function(which, stamp):
    data = interpretation()
    invalid = None if stamp is None else time.time() - 121 if stamp == "stale" else time.time() + 60
    if which == "pa_context":
        data["panasonic"]["power_activity"]["context_observed_at"] = invalid
    else:
        data["panasonic"]["task_context"]["observed_at"] = invalid
    data["sg_boost"].update(desired_on=True, relay_on=True)
    data["panasonic"]["sg_status"] = "active"
    root, = render(data)
    assert primary_label(root, "data-heatpump-operation") == "Warmtepomp werkt"
    assert primary_label(root, "data-heatpump-task") != "Verwarmen"
    assert named(root, "data-heatpump-task").attributes["data-heatpump-task"] != "inferred"
    assert panel(root).attributes["data-activity"] == "active"


def test_same_packet_loses_task_and_animated_activity_when_all_evidence_ages():
    current, expired = render(interpretation(), offsets=(0, 121))
    assert primary_label(current, "data-heatpump-operation") == "Verwarmen"
    assert named(current, "data-heatpump-operation").attributes["data-fan-active"] == "true"
    assert panel(expired).attributes["data-activity"] == "unknown"
    assert not any("heatpump-operation" in classes(node) for node in panel(expired).walk())
    assert not any("data-heatpump-task" in node.attributes for node in panel(expired).walk())
    assert not any("badge" in classes(node) for node in panel(expired).walk())


def test_compact_task_does_not_create_compressor_or_sg_confirmation():
    data = interpretation()
    data["panasonic"].update(sg_status="unknown", sg_status_confirmed=False)
    data["sg_boost"].update(relay_on=True, desired_on=True)
    root, = render(data)
    graphic = named(root, "data-heatpump-operation")
    assert graphic.attributes["data-compressor-running"] == "false"
    assert graphic.attributes["data-fan-active"] == "true"
    assert "Compressor draait" not in compact_text(panel(root))
    assert not any(node.attributes.get("data-sg-stage") == "received" for node in panel(root).walk())
    assert "geen draaiende compressor" in named(root, "data-heatpump-provenance").text()


def test_unknown_task_source_stays_hidden_and_does_not_override_fresh_measured_activity():
    data = native_task(interpretation(), "tapwater_heating", source="guessed")
    root, = render(data)
    assert primary_label(root, "data-heatpump-operation") == "Verwarmen"
    assert primary_label(root, "data-heatpump-task") == "Verwarmen"
    assert "Boiler opwarmen" not in compact_text(panel(root))


@pytest.mark.parametrize("mismatch,value", [("source", "guessed"), ("kind", "tank_route"),
                                            ("function", "space_cooling")])
def test_current_context_must_match_the_meter_function_kind_and_source(mismatch, value):
    data = interpretation()
    data["panasonic"]["task_context"][mismatch] = value
    root, = render(data)
    assert primary_label(root, "data-heatpump-operation") == "Warmtepomp werkt"
    assert named(root, "data-heatpump-task").attributes["data-heatpump-task"] == "activity"
    assert "Verwarmen" not in compact_text(named(root, "data-heatpump-task"))


@pytest.mark.parametrize("flag", ["conflict", "inactive"])
def test_inconsistent_actual_function_with_conflict_or_inactive_flag_is_never_a_task(flag):
    data = native_task(interpretation(), "tapwater_heating")
    data["panasonic"]["native_task"][flag] = True
    root, = render(data)
    assert primary_label(root, "data-heatpump-operation") == "Warmtepomp werkt"
    assert named(root, "data-heatpump-task").attributes["data-heatpump-task"] == "activity"
    assert "Boiler opwarmen" not in compact_text(named(root, "data-heatpump-task"))


def test_task_provenance_is_inside_a_closed_disclosure_in_both_views():
    for view in ["board", "comfort"]:
        root, = render(interpretation(), view)
        proof = named(root, "data-heatpump-provenance")
        ancestors = []
        def locate(node, chain):
            if node is proof:
                ancestors.extend(chain)
            for child in node.children:
                if hasattr(child, "tag"):
                    locate(child, [*chain, node])
        locate(panel(root), [])
        assert any(node.tag == "details" and "open" not in node.attributes for node in ancestors)
        assert "Panasonic meldt rust" not in compact_text(panel(root))


def test_reduced_motion_css_disables_both_fan_and_heater_pulsing():
    source = CARD.read_text()
    rules = re.findall(r"@media\s*\(\s*prefers-reduced-motion\s*:\s*reduce\s*\)\s*\{([^}]+\}[^}]*)\}", source)
    assert any("heatpump-fan" in rule and re.search(r"animation\s*:\s*none", rule) for rule in rules)
    assert any("heatpump-task-icon" in rule and re.search(r"animation\s*:\s*none", rule) for rule in rules)

