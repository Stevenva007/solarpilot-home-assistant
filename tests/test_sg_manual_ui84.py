"""Execute temporary SG controls; requests never fabricate physical confirmation."""
import json
import shutil
import subprocess

import pytest

from test_overview_details60 import Markup
from test_sg_ui_platforms62 import CARD, attributes

NOW = 1_800_000_000


def fixture(mode="auto", duration=1800, remaining=1700):
    data = attributes()
    data["sg_boost"].update(observed_at=NOW, relay_observed_at=NOW,
                            relay_on=False, relay_confirmed=True)
    data["sg_boost"]["manual_control"] = {"mode": mode, "active": mode != "auto",
        "duration_s": duration if mode != "auto" else None,
        "remaining_s": remaining if mode != "auto" else None,
        "expires_at": NOW + remaining if mode != "auto" else None,
        "reason": "Wacht op actuele veilige voorwaarden"}
    return data


def execute(data=None, *, view="comfort", now=NOW, actions=(), admin=True, error=None,
            timeout=False, pending=False, change_context=False):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for actual frontend execution")
    script = r'''
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const BaseDate=Date,sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},input,
Date:class extends BaseDate{static now(){return input.now*1000;}},
setTimeout:input.timeout?(f)=>{queueMicrotask(f);return 1;}:setTimeout,
clearTimeout:input.timeout?()=>{}:clearTimeout};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
vm.runInContext(`(async()=>{
 const calls=[],card=Object.create(SolarPilotCard.prototype);let resolveCall;
 card._last={attributes:input.data};card._busy=false;card._error='';card._feedback='';
 card._hass={user:{id:'fictional-admin',is_admin:input.admin},states:{},callService:async(domain,service,data)=>{
   calls.push({domain,service,data});if(input.error)throw new Error(input.error);
   if(input.timeout)return new Promise(()=>{});if(input.pending)return new Promise(r=>resolveCall=r);
 }};card._render=()=>{};
 const render=()=>input.view==='overview'?card._decisionBoard(card._ctx()):card._comfort(card._ctx());
 const initial=render();let during=null;
 for(const item of input.actions){
   const result=card._click({target:{closest:()=>({disabled:false,dataset:{action:'sg_manual_control',...item}})}});
   if(input.pending){during=render();await card._click({target:{closest:()=>({disabled:false,dataset:{action:'sg_manual_control',sgMode:'auto'}})}});
     if(input.change_context){card._invalidateSgManualRequest();card._hass.user={id:'other',is_admin:false};}
     resolveCall();}await result;
 }
 return {initial,during,final:render(),calls,error:card._error,feedback:card._feedback,busy:card._busy,
   manualBusy:card._sgManualBusy===true,manualState:card._sgManualState(card._ctx())};
})()`,sandbox).then(r=>process.stdout.write(JSON.stringify(r))).catch(e=>{process.stderr.write(e.stack);process.exitCode=1;});
'''
    result = subprocess.run([node, "-e", script, str(CARD)], input=json.dumps({"data": data or fixture(),
        "view": view, "now": now, "actions": actions, "admin": admin, "error": error,
        "timeout": timeout, "pending": pending, "change_context": change_context}),
        text=True, capture_output=True, timeout=5)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def root(result, key="initial"):
    return Markup(result[key]).root


def control(result, key="initial"):
    return next(n for n in root(result, key).walk() if "data-sg-manual-control" in n.attributes)


@pytest.mark.parametrize("view", ["comfort", "overview"])
def test_five_visible_controls_have_exact_time_choices_and_no_device_calls(view):
    result = execute(view=view)
    row = control(result)
    buttons = [n for n in row.walk() if n.attributes.get("data-action") == "sg_manual_control"]
    assert [(b.attributes["data-sg-mode"], b.attributes.get("data-sg-duration")) for b in buttons] == [
        ("auto", None), ("on", "1800"), ("on", "3600"), ("off", "1800"), ("off", "3600")]
    assert "Automatisch" in row.text() and "Veiligheidsvoorwaarden blijven gelden" in row.text()
    assert not any("disabled" in b.attributes for b in buttons)
    assert not result["calls"]


@pytest.mark.parametrize("mode,duration", [("on", 1800), ("on", 3600), ("off", 1800), ("off", 3600), ("auto", None)])
def test_actual_click_requests_one_sg_only_service_with_exact_duration(mode, duration):
    action = {"sgMode": mode}
    expected = {"config_entry_id": "example", "mode": mode}
    if duration is not None:
        action["sgDuration"] = str(duration)
        expected["duration_s"] = duration
    result = execute(actions=[action])
    assert result["calls"] == [{"domain": "solar_pilot", "service": "sg_manual_control", "data": expected}]
    assert "wacht op de actuele SolarPilot-status" in result["feedback"]
    assert control(result, "final").attributes["data-sg-manual-control"] == "auto", "No optimistic mode change"
    assert "Open" in root(result, "final").text(), "Request does not fabricate relay ON"
    assert result["busy"] is False and result["manualBusy"] is False


@pytest.mark.parametrize("mode", ["on", "off"])
def test_countdown_is_elapsed_from_original_deadline_and_does_not_claim_contact(mode):
    result = execute(fixture(mode), now=NOW + 80)
    row = control(result)
    assert row.attributes["data-sg-manual-control"] == mode
    assert "Nog 27 min · daarna automatisch" in row.text()
    selected = [n for n in row.walk() if n.attributes.get("aria-pressed") == "true"]
    assert len(selected) == 1 and selected[0].attributes.get("data-sg-duration") == "1800"
    assert "SG-contact Open" in root(result).text()
    assert "Aanvraag wacht" in row.text() if mode == "on" else "Aanvraag wacht" not in row.text()
    assert not result["calls"]


@pytest.mark.parametrize("mode", ["on", "off"])
def test_expiry_waits_for_backend_auto_without_automatic_browser_service(mode):
    result = execute(fixture(mode, remaining=10), now=NOW + 11)
    row = control(result)
    assert "Tijd verstreken · wacht op automatische beoordeling" in row.text()
    assert not any(n.attributes.get("aria-pressed") == "true" for n in row.walk())
    assert result["manualState"]["mode"] == mode and not result["calls"]
    current = execute(fixture("auto"), now=NOW)
    assert current["manualState"]["mode"] == "auto"
    assert "Tijd verstreken" not in control(current).text()


@pytest.mark.parametrize("change", [
    {"duration_s": True}, {"duration_s": 0}, {"duration_s": 7200},
    {"remaining_s": True}, {"remaining_s": -1}, {"remaining_s": 1801},
    {"expires_at": True}, {"expires_at": None}, {"expires_at": NOW + 1802},
])
def test_invalid_countdown_never_becomes_a_valid_time(change):
    data = fixture("on")
    data["sg_boost"]["manual_control"].update(change)
    result = execute(data)
    assert "Resterende tijd onbekend" in control(result).text()
    assert "Nog 28" not in control(result).text()


@pytest.mark.parametrize("change", [{"observed_at": NOW-121}, {"observed_at": NOW+6},
    {"observed_at": None}, {"observed_at": True}])
def test_stale_or_invalid_mode_snapshot_is_unknown(change):
    data = fixture("on")
    data["sg_boost"].update(change)
    result = execute(data)
    assert result["manualState"]["mode"] is None
    assert "Bedieningskeuze onbekend" in control(result).text()
    assert not result["calls"]


@pytest.mark.parametrize("mode", ["paused", "observe"])
def test_pause_and_observe_keep_manual_on_disabled_but_off_and_auto_available(mode):
    data = fixture()
    data["mode"] = mode
    result = execute(data, actions=[{"sgMode": "on", "sgDuration": "1800"}])
    buttons = [n for n in control(result).walk() if n.attributes.get("data-action") == "sg_manual_control"]
    assert all("disabled" in n.attributes for n in buttons if n.attributes["data-sg-mode"] == "on")
    assert all("disabled" not in n.attributes for n in buttons if n.attributes["data-sg-mode"] != "on")
    assert not result["calls"] and "Automatisch regelen" in result["error"]


def test_master_disabled_blocks_on_and_is_not_implicitly_enabled():
    data = fixture()
    data["sg_boost"]["enabled"] = False
    result = execute(data, actions=[{"sgMode": "on", "sgDuration": "3600"}])
    assert not result["calls"] and "Schakel zonneboost eerst in" in result["error"]
    assert data["sg_boost"]["enabled"] is False


def test_non_admin_and_legacy_backend_cannot_submit_stale_dom_actions():
    result = execute(admin=False, actions=[{"sgMode": "on", "sgDuration": "1800"}])
    assert not result["calls"] and all("disabled" in n.attributes for n in control(result).walk() if n.attributes.get("data-action") == "sg_manual_control")
    legacy = fixture()
    del legacy["sg_boost"]["manual_control"]
    result = execute(legacy, actions=[{"sgMode": "off", "sgDuration": "1800"}])
    assert not result["calls"] and "werk integratie en kaart samen bij" in control(result).text()


@pytest.mark.parametrize("action", [{"sgMode": "auto", "sgDuration": "0"},
    {"sgMode": "auto", "sgDuration": "1800"}, {"sgMode": "on"},
    {"sgMode": "off", "sgDuration": "60"}, {"sgMode": "on", "sgDuration": "Infinity"},
    {"sgMode": "toggle", "sgDuration": "1800"}])
def test_invalid_stale_dom_choice_never_calls_a_service(action):
    result = execute(actions=[action])
    assert not result["calls"] and result["error"]


@pytest.mark.parametrize("timeout,error", [(False, "Offline"), (True, None)])
def test_service_failure_or_timeout_releases_pending_and_keeps_reported_mode(timeout, error):
    result = execute(fixture("off"), actions=[{"sgMode": "on", "sgDuration": "1800"}], timeout=timeout, error=error)
    assert len(result["calls"]) == 1 and "niet bevestigd" in result["error"]
    assert "Controleer de actuele bedieningskeuze" in result["error"]
    assert result["manualState"]["mode"] == "off" and not result["feedback"]
    assert result["busy"] is False and result["manualBusy"] is False


def test_pending_request_disables_duplicates_and_never_changes_contact():
    result = execute(actions=[{"sgMode": "on", "sgDuration": "1800"}], pending=True)
    assert len(result["calls"]) == 1
    during = control(result, "during")
    assert "Bedieningskeuze versturen" in during.text()
    assert all("disabled" in n.attributes for n in during.walk() if n.attributes.get("data-action") == "sg_manual_control")
    assert "SG-contact Open" in root(result, "during").text()


def test_account_change_discards_late_feedback_and_pending_state():
    result = execute(actions=[{"sgMode": "on", "sgDuration": "1800"}], pending=True, change_context=True)
    assert len(result["calls"]) == 1 and not result["feedback"]
    assert result["busy"] is False and result["manualBusy"] is False


def test_blocked_reason_is_escaped_and_visible_without_claiming_sg_contact():
    data = fixture("on")
    payload = '<img src=x onerror="window.bad=true">'
    data["sg_boost"]["manual_control"]["reason"] = "Fasegrens bereikt " + payload
    result = execute(data)
    row = control(result)
    assert "Aanvraag wacht:" in row.text() and "Fasegrens bereikt" in row.text() and payload in row.text()
    assert not any(n.tag == "img" for n in row.walk())
    assert "SG-contact Open" in root(result).text()


def gap_fixture(kind="cloud", remaining=60):
    data = fixture()
    data["sg_boost"].update(state="waiting_surplus", completion_hold=False,
        start_required_s=120, start_remaining_s=remaining, start_valid_until=NOW-1,
        start_cloud_active=True, start_cloud_kind=kind, start_cloud_remaining_s=240,
        start_cloud_valid_until=NOW+240)
    return data


@pytest.mark.parametrize("kind", ["cloud", "measurement_gap"])
def test_start_clock_continues_through_short_gap_without_eligible_or_contact_claim(kind):
    result = execute(gap_fixture(kind), now=NOW+40)
    text = root(result).text()
    assert "Nog 20 s inschakelwachttijd" in text
    assert "Nog 3 min 20 s van maximaal 5 min overbrugging" in text
    assert ("Wolkendip" if kind == "cloud" else "Korte meetonderbreking") in text
    assert "SG start pas bij actuele voldoende zon en veilige voorwaarden" in text
    assert "SG-contact Open" in text and not result["calls"]


@pytest.mark.parametrize("kind,waiting", [("cloud", "wacht op voldoende zon"),
    ("measurement_gap", "wacht op actuele meting")])
def test_elapsed_start_clock_during_gap_waits_for_current_evidence(kind, waiting):
    result = execute(gap_fixture(kind), now=NOW+80)
    text = root(result).text()
    assert "Wachttijd verstreken" in text and waiting in text
    assert "Nog 2 min 40 s van maximaal 5 min overbrugging" in text
    assert "Voldoende overschot bevestigen" not in text and not result["calls"]


@pytest.mark.parametrize("change", [
    {"start_cloud_kind": "unknown"}, {"start_cloud_remaining_s": True},
    {"start_cloud_remaining_s": None}, {"start_cloud_remaining_s": 301},
    {"start_cloud_valid_until": NOW-1}, {"start_cloud_valid_until": None},
    {"observed_at": NOW-121},
])
def test_invalid_gap_proof_never_claims_remaining_clock_or_buffer(change):
    data = gap_fixture()
    data["sg_boost"].update(change)
    text = root(execute(data)).text()
    assert "Resterende inschakelwachttijd onbekend" in text
    assert "Resterende overbrugging onbekend" in text
    assert "SG start pas bij actuele voldoende zon en veilige voorwaarden" in text


def test_gap_zero_does_not_display_new_start_authority_or_send_a_command():
    data = gap_fixture(remaining=0)
    data["sg_boost"].update(start_cloud_remaining_s=0, start_cloud_valid_until=NOW)
    result = execute(data)
    text = root(result).text()
    assert "Overbrugging verstreken · wacht op actuele beoordeling" in text
    assert "wacht op voldoende zon" in text and not result["calls"]


@pytest.mark.parametrize("mode", ["on", "off"])
def test_manual_clock_is_independent_and_hides_automatic_gap_minimum_import_banners(mode):
    data = gap_fixture()
    data["sg_boost"]["manual_control"] = fixture(mode)["sg_boost"]["manual_control"]
    data["sg_boost"].update(desired_on=True, min_session_s=1200,
        import_threshold_w=600, stop_delay_s=300)
    result = execute(data, now=NOW+80)
    row = control(result)
    assert "Nog 27 min · daarna automatisch" in row.text()
    assert not any("data-sg-wait" in n.attributes or "data-sg-minimum" in n.attributes or
        "data-sg-cloud" in n.attributes for n in root(result).walk())
    assert not result["calls"]


def test_missing_meter_can_keep_clock_visible_while_controller_state_is_blocked():
    data = gap_fixture("measurement_gap", remaining=0)
    data["sg_boost"].update(state="blocked", reason="Wacht op actuele netmeting")
    text = root(execute(data)).text()
    assert "Korte meetonderbreking" in text
    assert "Wachttijd verstreken · wacht op actuele meting" in text
    assert "SG-contact Open" in text
