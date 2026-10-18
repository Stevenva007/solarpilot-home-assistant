"""Independent source-time, retention and READ-boundary probes for scrubbing."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot.heatpump_history import HeatpumpHistory
from custom_components.solar_pilot.heatpump_history_runtime import HeatpumpHistoryRecorder
from test_heatpump_history70 import BASE, observe, sg
from test_heatpump_history81 import tank_source
from test_heatpump_history_api70 import api, context, query
from test_runtime import build


def _total_source(at, watts=1800):
    p = tank_source(at, watts=watts)
    p.update(power_scope="total", power_w=watts, power_complete=True)
    for n in (1, 2):
        p.pop(f"power_supply{n}_entity", None)
        p.update({f"power_supply{n}_valid": False, f"power_supply{n}_w": None,
                  f"power_supply{n}_observed_at": None})
    p["power_activity"].pop("supplies")
    return p


def _point(model, at=BASE):
    return model.detail(None, at)["native_evidence"]["points"][0]


def test_total_meter_real_zero_keeps_original_report_without_fake_feed_sum():
    model = HeatpumpHistory()
    p = _total_source(BASE, 0)
    p["power_observed_at"] = BASE.timestamp()-17
    observe(model, BASE, p=p)
    point = _point(model)
    power = point["power"]
    assert power["total_w"] == 0 and power["complete"] is True
    assert power["source_scope"] == "total" and power["kind"] == "measured"
    assert power["reported_at"] == BASE.timestamp()-17
    assert power["valid_until"] == BASE.timestamp()+103
    assert all(feed["watts"] is None for feed in point["supplies"])
    assert point["tank"]["temperature_reported_at"] == BASE.timestamp()-4


def test_split_power_deadline_uses_the_oldest_actual_contributor():
    model = HeatpumpHistory()
    p = tank_source(BASE, watts=1800, main=1700, heater=100)
    p["power_observed_at"] = BASE.timestamp()-1
    for n, age in ((1, 110), (2, 3)):
        p[f"power_supply{n}_observed_at"] = BASE.timestamp()-age
        p["power_activity"]["supplies"][n-1]["observed_at"] = BASE.timestamp()-age
    observe(model, BASE, p=p)
    power = _point(model)["power"]
    assert power["total_w"] == 1800 and power["source_scope"] == "split"
    assert power["reported_at"] == BASE.timestamp()-110
    assert power["valid_until"] == BASE.timestamp()+10


@pytest.mark.parametrize("failure", ["old", "missing", "boolean", "incomplete", "contradictory"])
def test_invalid_split_total_never_promotes_valid_individual_feed_to_whole_pump_watts(failure):
    model = HeatpumpHistory()
    p = tank_source(BASE, watts=1800, main=1700, heater=100)
    if failure == "old":
        p["power_supply2_observed_at"] = BASE.timestamp()-121
        p["power_activity"]["supplies"][1]["observed_at"] = BASE.timestamp()-121
    elif failure == "missing":
        p["power_supply2_valid"] = False
        p["power_activity"]["supplies"][1].update(valid=False, watts=None)
    elif failure == "boolean":
        p["power_w"] = True
    elif failure == "incomplete":
        p["power_complete"] = False
    else:
        p["power_w"] = 1900
    observe(model, BASE, p=p)
    point = _point(model)
    assert point.get("power", {}).get("total_w") is None
    assert point["supplies"][0]["watts"] == 1700
    assert model.detail(None, BASE)["energy_kwh"] is None


def test_legacy_points_do_not_gain_current_watts_after_restore_new_capture_or_detail():
    model = HeatpumpHistory()
    observe(model, BASE, p=_total_source(BASE, 1200))
    saved = model.snapshot()
    legacy = saved["native_evidence"]["points"][0]
    legacy.pop("power")
    original = deepcopy(legacy)
    restored = HeatpumpHistory()
    restored.restore(saved, BASE+timedelta(seconds=5))
    assert "power" not in _point(restored, BASE+timedelta(seconds=5))
    later = BASE+timedelta(seconds=10)
    p = _total_source(later, 9300)
    p["display_tank"]["temperature_c"] = 61  # A real changed snapshot is retained.
    observe(restored, later, p=p)
    points = restored.detail(None, later)["native_evidence"]["points"]
    assert points[0] == original and "power" not in points[0]
    assert points[-1]["power"]["total_w"] == 9300
    assert points[-1]["tank"]["temperature_c"] == 61
    assert points[0]["tank"]["temperature_c"] != 61
    assert saved["native_evidence"]["points"][0] == original


def _corrupt_power(power, field):
    replacements = {
        "schema_bool": ("schema", True), "schema_future": ("schema", 2),
        "watts_bool": ("total_w", True), "watts_nan": ("total_w", float("nan")),
        "watts_inf": ("total_w", float("inf")), "watts_negative": ("total_w", -1),
        "watts_large": ("total_w", 100001), "time_zero": ("reported_at", 0),
        "time_bool": ("reported_at", True), "time_future": ("reported_at", BASE.timestamp()+6),
        "expiry_past": ("valid_until", BASE.timestamp()-1),
        "expiry_extended": ("valid_until", BASE.timestamp()+121),
        "complete_number": ("complete", 1), "complete_false": ("complete", False),
        "scope_partial": ("source_scope", "partial"), "estimated": ("kind", "estimated"),
        "stale_bool": ("stale_s", True), "stale_zero": ("stale_s", 0),
    }
    key, value = replacements[field]
    power[key] = value


@pytest.mark.parametrize("field", ["schema_bool", "schema_future", "watts_bool", "watts_nan",
    "watts_inf", "watts_negative", "watts_large", "time_zero", "time_bool", "time_future",
    "expiry_past", "expiry_extended", "complete_number", "complete_false", "scope_partial",
    "estimated", "stale_bool", "stale_zero"])
def test_malformed_retained_power_fails_closed_without_replacing_valid_existing_history(field):
    model = HeatpumpHistory()
    observe(model, BASE, p=_total_source(BASE, 1800))
    before = model.snapshot()
    bad = deepcopy(before)
    _corrupt_power(bad["native_evidence"]["points"][0]["power"], field)
    with pytest.raises(ValueError):
        model.restore(bad, BASE+timedelta(seconds=10))
    assert model.snapshot() == before


def test_corrupt_retained_split_sum_cannot_become_a_complete_power_point():
    model = HeatpumpHistory()
    observe(model, BASE, p=tank_source(BASE, watts=1800, main=1700, heater=100))
    saved = model.snapshot()
    saved["native_evidence"]["points"][0]["power"]["total_w"] = 1900
    with pytest.raises(ValueError):
        HeatpumpHistory().restore(saved, BASE+timedelta(seconds=10))


@pytest.mark.asyncio
async def test_unreadable_new_power_does_not_overwrite_the_original_store():
    runtime, hass = build()
    model = HeatpumpHistory()
    observe(model, BASE, p=_total_source(BASE))
    stored = {"version": 1, "history": model.snapshot(), "access_sources": ["sensor.fictional_old"],
              "access_sources_complete": True}
    stored["history"]["native_evidence"]["points"][0]["power"]["schema"] = 2
    original = deepcopy(stored)
    recorder = HeatpumpHistoryRecorder(hass, runtime.entry)
    recorder.now = lambda: BASE+timedelta(seconds=10)
    recorder.store.data = stored
    await recorder.start()
    recorder.observe(_total_source(BASE+timedelta(seconds=15)), {}, BASE+timedelta(seconds=15))
    await recorder.close()
    assert recorder.loaded and not recorder._writable and recorder.error
    assert recorder.store.data == original and not recorder.store.saves
    assert not hass.services.calls


@pytest.mark.parametrize("day,start,end,seconds", [
    ("2026-03-29", "2026-03-28T23:00:00+00:00", "2026-03-29T22:00:00+00:00", 82800),
    ("2026-10-25", "2026-10-24T22:00:00+00:00", "2026-10-25T23:00:00+00:00", 90000),
])
def test_numeric_local_day_bounds_are_real_utc_instants_across_dst(day, start, end, seconds):
    when = datetime.fromisoformat(end)-timedelta(seconds=1)
    detail = HeatpumpHistory().detail(day, when)
    assert type(detail["day_start"]) in (int, float) and type(detail["day_end"]) in (int, float)
    assert detail["day_start"] == datetime.fromisoformat(start).timestamp()
    assert detail["day_end"] == datetime.fromisoformat(end).timestamp()
    assert detail["day_end"]-detail["day_start"] == detail["day_seconds"] == seconds


def test_midnight_sample_belongs_to_one_local_day_only():
    model = HeatpumpHistory()
    boundary = datetime(2026, 10, 12, 22, tzinfo=timezone.utc)
    observe(model, boundary-timedelta(seconds=1), p=_total_source(boundary-timedelta(seconds=1)))
    next_day = _total_source(boundary, 4500)
    next_day["display_tank"]["temperature_c"] = 58
    observe(model, boundary, p=next_day)
    previous = model.detail("2026-10-12", boundary)
    current = model.detail("2026-10-13", boundary)
    assert [p["captured_at"] for p in previous["native_evidence"]["points"]] == [boundary.timestamp()-1]
    assert [p["captured_at"] for p in current["native_evidence"]["points"]] == [boundary.timestamp()]
    assert previous["day_end"] == current["day_start"] == boundary.timestamp()


def test_new_power_points_require_read_permission_on_all_retained_sources(api):
    runtime, hass, connection, out, errors, _ = context(admin=False)
    runtime.heatpump_history.now = lambda: BASE+timedelta(seconds=5)
    runtime.heatpump_history.observe(_total_source(BASE, 4321), sg(BASE), BASE,
                                   binding="private-binding", sources={"sensor.fictional_restricted_old"})
    connection.user.permissions.check_entity = lambda entity, policy: entity != "sensor.fictional_restricted_old"
    query(api, hass, connection, date="2026-10-11")
    assert not out and errors[-1][0] == "unauthorized"
    assert "fictional_restricted" not in errors[-1][1] and not hass.services.calls


def test_authorized_scrub_payload_has_no_source_ids_or_write_side_effects(api):
    runtime, hass, connection, out, errors, _ = context(admin=True)
    runtime.heatpump_history.now = lambda: BASE+timedelta(seconds=5)
    runtime.heatpump_history.observe(_total_source(BASE, 4321), sg(BASE), BASE,
                                   binding="private-binding", sources={"sensor.fictional_restricted_old"})
    before = deepcopy((runtime.entry.data, runtime.entry.options, runtime._snapshot(), hass.services.calls))
    query(api, hass, connection, date="2026-10-11")
    assert not errors and out[0]["native_evidence"]["points"][0]["power"]["total_w"] == 4321
    encoded = json.dumps(out)
    assert "fictional_restricted" not in encoded and "private-binding" not in encoded
    assert "synthetic_tank" not in encoded and "access_sources" not in encoded
    assert (runtime.entry.data, runtime.entry.options, runtime._snapshot(), hass.services.calls) == before


def _scrub_ui(data, operation):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node is required for the actual shipped scrub selector")
    card = Path(__file__).resolve().parents[1]/"custom_components/solar_pilot/frontend/solar-pilot-card.js"
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),input=JSON.parse(fs.readFileSync(0,'utf8'));
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}}};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
sandbox.input=input.data;
const result=vm.runInContext(`(()=>{
 const dialog=Object.create(SolarPilotHeatpumpHistoryDialog.prototype);
 dialog._data=input;dialog._isOpen=true;
 const marker={hidden:true,style:{}},attributes={},readout={innerHTML:'',getBoundingClientRect:()=>({height:0})};
 const lane={querySelector:()=>marker,setAttribute:(key,value)=>{attributes[key]=value;}};
 dialog._body={querySelector:()=>readout,querySelectorAll:()=>[lane]};
 ${input.operation}
 return {state:dialog._scrub,selected:dialog._scrubState(),html:readout.innerHTML,
         marker,attributes};
})()`,sandbox);
process.stdout.write(JSON.stringify(result));
"""
    result = subprocess.run([node, "-e", script, str(card)],
                            input=json.dumps({"data": data, "operation": operation}),
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


def _ui_sample():
    model = HeatpumpHistory()
    observe(model, BASE, p=tank_source(BASE, task="tapwater_heating", watts=1700))
    data = model.detail(None, BASE)
    data["tank_temperature"]["current"].update(temperature_c=99, ordinary_target_c=98)
    at = BASE.timestamp()
    def period(left, right, **fields):
        return {"segment_start": datetime.fromtimestamp(left, timezone.utc).isoformat(),
                "segment_end": datetime.fromtimestamp(right, timezone.utc).isoformat(), **fields}
    data["task_sessions"] = [period(at-300, at, task="space_heating", label="Vorige taak", tier="confirmed", stop_confirmed=True),
                             period(at, at+300, task="tapwater_heating", label="Boiler opwarmen", tier="confirmed")]
    data["sg_contact_overlay"] = {"schema": 1, "segments": [period(at-300, at, state="off"),
                                                            period(at, at+300, state="on")]}
    data["sg"]["request"]["sessions"] = [period(at, at+300)]
    data["sg"]["received"]["sessions"] = []
    return data


def test_nearest_future_sample_moves_marker_time_and_all_context_to_its_actual_capture():
    data = _ui_sample()
    at = BASE.timestamp()
    result = _scrub_ui(data, f"dialog._setScrub({at-20});")
    assert result["state"]["at"] == result["state"]["pointAt"] == at
    assert result["selected"]["point"]["captured_at"] == at
    assert float(result["marker"]["style"]["left"].rstrip("%")) == pytest.approx(
        (at-data["day_start"])/data["day_seconds"]*100)
    assert result["attributes"]["aria-valuenow"] == at-data["day_start"]
    assert result["attributes"]["aria-valuetext"].startswith("Meetpunt ")
    assert "Boiler opwarmen" in result["html"] and "Vorige taak" not in result["html"]
    assert "1,7 kW" in result["html"] and "57 °C" in result["html"]
    assert "99 °C" not in result["html"] and "98 °C" not in result["html"]


def test_no_sample_within_snap_window_does_not_borrow_current_or_next_numeric_values():
    at = BASE.timestamp()
    result = _scrub_ui(_ui_sample(), f"dialog._setScrub({at-151});")
    assert result["state"]["at"] == at-151 and result["state"]["pointAt"] is None
    assert result["selected"]["point"] is None
    assert result["attributes"]["aria-valuetext"].startswith("Gekozen tijd ")
    assert "1,7 kW" not in result["html"] and "57 °C" not in result["html"]
    assert "99 °C" not in result["html"] and "98 °C" not in result["html"]
    assert "Geen vastgelegd meetpunt binnen" in result["html"]


def test_refresh_losing_selected_point_keeps_time_without_silently_reselecting_nearby_sample():
    at = BASE.timestamp()
    operation = f"""
dialog._setScrub({at});
const replacement=JSON.parse(JSON.stringify(dialog._data.native_evidence.points[0]));
replacement.captured_at={at+5};replacement.tank.temperature_c=91;
dialog._data.native_evidence.points=[replacement];dialog._syncScrub();
"""
    result = _scrub_ui(_ui_sample(), operation)
    assert result["state"]["at"] == at and result["selected"]["point"] is None
    assert result["attributes"]["aria-valuetext"].startswith("Gekozen tijd ")
    assert "91 °C" not in result["html"] and "1,7 kW" not in result["html"]


def test_first_actual_confirmed_native_point_has_task_even_with_no_positive_duration_session():
    model = HeatpumpHistory()
    observe(model, BASE, p=tank_source(BASE, task="tapwater_heating"))
    data = model.detail(None, BASE)
    result = _scrub_ui(data, f"dialog._setScrub({BASE.timestamp()});")
    assert result["selected"]["point"]["native"]["confirmed"] is True
    assert "Boiler opwarmen" in result["html"]


def test_confirmed_stop_at_sample_boundary_never_carries_previous_task_forward():
    data = _ui_sample()
    at = BASE.timestamp()
    data["task_sessions"] = data["task_sessions"][:1]
    data["native_evidence"]["points"][0]["native"].update(
        confirmed=False, function=None, inactive_reported=True, fresh=True)
    result = _scrub_ui(data, f"dialog._setScrub({at});")
    assert "Vorige taak" not in result["html"] and "Boiler opwarmen" not in result["html"]


@pytest.mark.parametrize("iso,offset", [("2026-10-25T02:30:00+02:00", "GMT+2"),
                                        ("2026-10-25T02:30:00+01:00", "GMT+1")])
def test_repeated_dst_hour_selection_reports_the_actual_instant_and_offset(iso, offset):
    when = datetime.fromisoformat(iso)
    model = HeatpumpHistory()
    observe(model, when, p=_total_source(when))
    data = model.detail(None, when)
    result = _scrub_ui(data, f"dialog._setScrub({when.timestamp()-20});")
    assert result["state"]["at"] == when.timestamp()
    assert offset in result["attributes"]["aria-valuetext"]
    assert "02:30:00" in result["attributes"]["aria-valuetext"]


@pytest.mark.parametrize("external_tank", [False, True])
def test_cached_native_status_cannot_redate_bound_tank_or_goal_but_independent_sources_survive(monkeypatch, external_tank):
    from custom_components.solar_pilot.panasonic_monitor import PanasonicMonitor
    from custom_components.solar_pilot.sg_target_display import resolved_goal_binding
    from test_aquarea_semantics98 import split_setup

    env = split_setup(monkeypatch)
    env.clock[0] = BASE.timestamp()
    env.helper._display_metadata_checked = BASE.timestamp()
    runtime = env.helper.runtime
    runtime.settings = {}
    runtime.hass.config = SimpleNamespace(units=SimpleNamespace(temperature_unit="°C"))
    tank_id = env.sources["tank_entity"]
    if external_tank:
        tank_id = "water_heater.fictional_external_tank"
        env.rows[tank_id] = SimpleNamespace(entity_id=tank_id, platform="mqtt", config_entry_id="external",
                                            unique_id="external-tank", device_id="external-device", disabled_by=None)
    power_id = "sensor.fictional_independent_power"
    env.rows[power_id] = SimpleNamespace(entity_id=power_id, platform="shelly", config_entry_id="shelly",
                                        unique_id="external-power", device_id="meter-device", disabled_by=None)
    config = {"tank_temperature_entity": tank_id, "tank_target_entity": tank_id,
              "zone_entities": env.sources["zone_entities"], "stale_s": 120,
              "power_entity": power_id, "power_scope": "total",
              "sg_dhw_capacity_confirmed": True, "sg_dhw_capacity_target_entity": tank_id,
              "sg_dhw_capacity_binding": resolved_goal_binding(runtime.hass, tank_id),
              "sg_dhw_capacity_percent": 115, "sg_dhw_capacity_confirmed_at": BASE.timestamp()-100}
    monitor = PanasonicMonitor(runtime, config)
    runtime.panasonic = monitor
    monitor.native_program = env.helper
    runtime._power = lambda entity, _stale=120: (
        float(runtime.hass.states.get(entity).state), runtime.hass.states.get(entity).last_reported.timestamp())
    env.poll(quality=env.quality.CACHED)
    for eid in env.sources["zone_entities"]:
        env.state(eid, "heat", {"hvac_action": "heating"}, stamp=BASE.timestamp())
    env.state(env.sources["pump_status_entity"], "On", stamp=BASE.timestamp())
    env.state(env.sources["direction_entity"], "PUMP", stamp=BASE.timestamp())
    env.state(tank_id, "idle", {"operation_mode": "idle", "temperature_unit": "°C",
                                 "current_temperature": 52, "temperature": 50}, stamp=BASE.timestamp())
    env.state(power_id, "3200", {"unit_of_measurement": "W"}, stamp=BASE.timestamp())
    snapshot = monitor.overview()
    assert env.coordinator.last_update_success is True
    assert snapshot["source_contract"]["reason_code"] == "native_status_not_live"
    assert snapshot["power_w"] == 3200 and snapshot["power_complete"] is True
    assert snapshot["native_task"]["function"] is None
    assert snapshot["context_reliable"] is False and snapshot["cooling_possible"] is True
    model = HeatpumpHistory()
    observe(model, BASE, p=snapshot, s=sg(BASE, request=True, contact=False))
    point = _point(model)
    assert point["power"]["total_w"] == 3200
    assert point["native"]["confirmed"] is False
    if external_tank:
        assert snapshot["temperature_c"] == snapshot["display_tank"]["temperature_c"] == 52
        assert snapshot["target_c"] == point["tank"]["ordinary_target_c"] == 50
        assert point["tank"]["temperature_c"] == 52
        assert snapshot["sg_tank_goal"]["calculated_c"] == point["sg_goal"]["calculated_c"] == 57.5
    else:
        assert snapshot["temperature_c"] is None and snapshot["target_c"] is None
        assert snapshot["display_tank"]["temperature_c"] is None
        assert snapshot["display_tank"]["temperature_stamp"] is None
        assert point["tank"]["temperature_c"] is None and point["tank"]["ordinary_target_c"] is None
        assert snapshot["sg_tank_goal"]["calculated_c"] is None
        assert point["sg_goal"] is None or point["sg_goal"]["calculated_c"] is None

    # Re-labelling this same cached object cannot renew the old HA attributes.
    env.clock[0] += 1
    env.coordinator.device._status.data_mode = env.quality.LIVE
    edited = monitor.overview()
    assert edited["native_task"]["function"] is None
    assert edited["context_reliable"] is False and edited["cooling_possible"] is True
    assert edited["power_w"] == 3200
    if external_tank:
        assert edited["temperature_c"] == 52 and edited["sg_tank_goal"]["calculated_c"] == 57.5
    else:
        assert edited["temperature_c"] is None and edited["target_c"] is None
        assert edited["display_tank"]["temperature_c"] is None
        assert edited["sg_tank_goal"]["calculated_c"] is None

    # A genuinely replaced LIVE provider generation can restore the source;
    # it never fills the earlier CACHED historical point with present values.
    env.poll(quality=env.quality.LIVE)
    restored = monitor.overview()
    assert restored["temperature_c"] == 52 and restored["target_c"] == 50
    assert restored["power_w"] == 3200
    observe(model, BASE+timedelta(seconds=1), p=restored)
    if not external_tank:
        assert _point(model, BASE+timedelta(seconds=1))["tank"]["temperature_c"] is None
        assert model.detail(None, BASE+timedelta(seconds=1))["native_evidence"]["points"][-1]["tank"]["temperature_c"] == 52
    assert not runtime.hass.services.calls and env.coordinator.api_calls == []
