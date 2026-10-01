from datetime import datetime, timezone
from copy import deepcopy
import asyncio
import ast
from pathlib import Path
from types import SimpleNamespace

import pytest
from homeassistant.helpers import entity_registry as er
from custom_components.solar_pilot.dishwasher_recovery import (
    LegacyDishwasherRecoveryRetry,
    recover_legacy_dishwasher,
)
import custom_components.solar_pilot.dishwasher_recovery as recovery_module
from custom_components.solar_pilot.runtime import SolarRuntime
from test_runtime import Services, build


class States:
    def __init__(self):
        self.data = {}
    def set(self, entity_id, state, friendly_name, **attrs):
        a = {"friendly_name": friendly_name, **attrs}
        self.data[entity_id] = SimpleNamespace(
            entity_id=entity_id, state=str(state), attributes=a,
            last_updated=datetime.now(timezone.utc), last_reported=datetime.now(timezone.utc),
        )
    def get(self, entity_id):
        return self.data.get(entity_id)
    def async_all(self):
        return list(self.data.values())


class Registry:
    def __init__(self, rows):
        self.rows = rows
    def async_get(self, entity_id):
        return self.rows.get(entity_id)


def appliance(marker=True):
    states = States(); rows = {}
    def add(eid, state, name, device="dev1", restored=False):
        states.set(eid, state, name, restored=restored)
        rows[eid] = SimpleNamespace(device_id=device, original_name=name, disabled_by=None)
    if marker:
        add("sensor.afwasmachine_dashboardstatus", "Klaar om te starten", "Afwasmachine dashboardstatus", device="helper")
    add("button.aeg_afwasmachine_executecommand_3", "unavailable", "Afwasmachine START", restored=True)
    add("button.aeg_afwasmachine_executecommand_7", "unknown", "Afwasmachine START")
    add("sensor.aeg_afwasmachine_appliancestate", "Ready To Start", "Afwasmachine Appliance state")
    add("sensor.aeg_afwasmachine_connectivitystate", "Connected", "Afwasmachine Connectivity state")
    add("sensor.aeg_afwasmachine_remotecontrol", "Not Safety Relevant Enabled", "Afwasmachine Remote control")
    add("binary_sensor.aeg_afwasmachine_doorstate", "off", "Afwasmachine Door state")
    add("select.aeg_afwasmachine_userselections_programuid", "Eco", "Afwasmachine Program uid")
    add("sensor.aeg_afwasmachine_cyclephase", "Unavailable", "Afwasmachine Cycle phase")
    add("sensor.aeg_afwasmachine_alerts", "2", "Afwasmachine Alerts")
    add("number.aeg_afwasmachine_starttime", "0", "Afwasmachine Start time")
    return SimpleNamespace(states=states), Registry(rows)


def test_beta38_recovers_missing_legacy_aeg_profile(monkeypatch):
    hass, reg = appliance()
    monkeypatch.setattr(er, "async_get", lambda _hass: reg)
    out, info = recover_legacy_dishwasher(hass, {"devices": [{"id":"dehum","name":"Droger","kind":"switch"}]})
    assert info["status"] == "recovered" and info["changed"] is True
    d = next(x for x in out["devices"] if x.get("kind") == "dishwasher")
    assert d["start_button"] == "button.aeg_afwasmachine_executecommand_7"
    assert d["cycle_program_entity"] == "select.aeg_afwasmachine_userselections_programuid"
    assert d["dishwasher_state_entity"] == "sensor.aeg_afwasmachine_appliancestate"
    assert d["dishwasher_arming_mode"] == "app"
    assert d["dishwasher_remote_states"] == "Enabled"
    assert d["dishwasher_start_deadline"] == "13:00:00"
    assert d["dishwasher_after_deadline"] == "next_day"
    assert d["dishwasher_deadline_grid_allowed"] is True
    assert d["dishwasher_mapping_confirmed"] is True
    assert "Ado Drying" in d["dishwasher_running_states"]
    assert d["dishwasher_alert_entity"] == ""
    assert d["dishwasher_priority_enabled"] is True
    assert d["wallbox_precedence"] == "consumer_first"
    assert d["id"] in out["_beta38_recovered_auto_devices"]
    assert info["roles"]["start_button"]["status"] == "selected"
    assert info["roles"]["start_button"]["rejected"]["restored"] == 1


def test_recovery_never_runs_without_legacy_dashboard_marker(monkeypatch):
    hass, reg = appliance(marker=False)
    monkeypatch.setattr(er, "async_get", lambda _hass: reg)
    out, info = recover_legacy_dishwasher(hass, {"devices": []})
    assert info["status"] == "not_applicable"
    assert out["devices"] == []


def test_existing_dishwasher_is_never_overwritten(monkeypatch):
    hass, reg = appliance()
    monkeypatch.setattr(er, "async_get", lambda _hass: reg)
    original = {"id":"existing","name":"Mijn afwas","kind":"dishwasher","start_button":"button.keep"}
    out, info = recover_legacy_dishwasher(hass, {"devices": [original]})
    assert info["status"] == "already_configured"
    assert out["devices"] == [original]


def test_incomplete_mapping_does_not_grant_start_right(monkeypatch):
    hass, reg = appliance()
    hass.states.data.pop("select.aeg_afwasmachine_userselections_programuid")
    monkeypatch.setattr(er, "async_get", lambda _hass: reg)
    out, info = recover_legacy_dishwasher(hass, {"devices": []})
    assert info["status"] == "incomplete"
    assert info["roles"]["program"]["status"] == "missing"
    assert info["roles"]["program"]["candidate_count"] == 1
    assert info["roles"]["program"]["rejected"]["not_loaded"] == 1
    assert all("entity_id" not in str(value) and "dev1" not in str(value)
               for value in info["roles"].values())
    assert out["devices"] == []


def test_ambiguous_role_is_reported_without_private_identifiers(monkeypatch):
    hass, reg = appliance()
    eid = "button.aeg_afwasmachine_executecommand_start_extra"
    hass.states.set(eid, "unknown", "Afwasmachine START extra")
    reg.rows[eid] = SimpleNamespace(device_id="dev1", original_name="Afwasmachine START extra", disabled_by=None)
    monkeypatch.setattr(er, "async_get", lambda _hass: reg)

    out, info = recover_legacy_dishwasher(hass, {"devices": []})

    assert info["status"] == "incomplete"
    assert info["roles"]["start_button"]["status"] == "ambiguous"
    assert info["roles"]["start_button"]["usable_count"] == 2
    assert "button.aeg" not in str(info) and "dev1" not in str(info)
    assert out["devices"] == []


@pytest.mark.parametrize(("state", "restored", "reason"), [
    ("unavailable", False, "unavailable"),
    ("unknown", True, "restored"),
])
def test_sole_unusable_start_is_missing_never_selected(monkeypatch, state, restored, reason):
    hass, reg = appliance()
    hass.states.data.pop("button.aeg_afwasmachine_executecommand_3")
    reg.rows.pop("button.aeg_afwasmachine_executecommand_3")
    hass.states.set("button.aeg_afwasmachine_executecommand_7", state, "Afwasmachine START", restored=restored)
    monkeypatch.setattr(er, "async_get", lambda _hass: reg)

    out, info = recover_legacy_dishwasher(hass, {"devices": []})

    role = info["roles"]["start_button"]
    assert info["status"] == "incomplete" and out["devices"] == []
    assert role["status"] == "missing" and role["usable_count"] == 0
    assert role["rejected"][reason] == 1


@pytest.mark.parametrize("disabled", [False, True])
def test_registry_only_start_reports_not_loaded_or_disabled(monkeypatch, disabled):
    hass, reg = appliance()
    for eid in ("button.aeg_afwasmachine_executecommand_3", "button.aeg_afwasmachine_executecommand_7"):
        hass.states.data.pop(eid)
        reg.rows.pop(eid)
    eid = "button.aeg_afwasmachine_executecommand_registry"
    reg.rows[eid] = SimpleNamespace(device_id="dev1", original_name="Afwasmachine START",
                                    disabled_by="integration" if disabled else None)
    monkeypatch.setattr(er, "async_get", lambda _hass: reg)

    out, info = recover_legacy_dishwasher(hass, {"devices": []})

    reason = "disabled" if disabled else "not_loaded"
    role = info["roles"]["start_button"]
    assert info["status"] == "incomplete" and out["devices"] == []
    assert role["status"] == "missing" and role["rejected"][reason] == 1


def test_sensor_program_uid_is_supported(monkeypatch):
    hass, reg = appliance()
    old = "select.aeg_afwasmachine_userselections_programuid"
    hass.states.data.pop(old)
    reg.rows.pop(old)
    eid = "sensor.aeg_afwasmachine_userselections_programuid"
    hass.states.set(eid, "Eco", "Afwasmachine Program uid")
    reg.rows[eid] = SimpleNamespace(device_id="dev1", original_name="Afwasmachine Program uid", disabled_by=None)
    monkeypatch.setattr(er, "async_get", lambda _hass: reg)

    out, info = recover_legacy_dishwasher(hass, {"devices": []})

    assert info["status"] == "recovered"
    assert out["devices"][0]["cycle_program_entity"] == eid


def test_beta39_repairs_only_beta38_recovered_profile(monkeypatch):
    hass, reg = appliance()
    monkeypatch.setattr(er, "async_get", lambda _hass: reg)
    base, info = recover_legacy_dishwasher(hass, {"devices": []})
    assert info["status"] == "recovered"
    d = next(x for x in base["devices"] if x.get("kind") == "dishwasher")
    # Simulate the exact beta.38 auto-generated fields that could block/start-track incorrectly.
    d["dishwasher_running_states"] = "Running;Paused"
    d["dishwasher_alert_entity"] = "sensor.aeg_afwasmachine_alerts"
    d["dishwasher_alert_mode"] = "aeg_attributes"
    base.pop("_beta39_dishwasher_repair", None)
    out, repaired = recover_legacy_dishwasher(hass, base)
    fixed = next(x for x in out["devices"] if x["id"] == d["id"])
    assert repaired["status"] == "repaired"
    assert "Ado Drying" in fixed["dishwasher_running_states"]
    assert fixed["dishwasher_alert_entity"] == ""
    assert set(repaired["repair_changes"]) == {"running_states", "unverified_auto_alarm"}


def test_beta39_does_not_modify_manual_dishwasher_profile(monkeypatch):
    hass, reg = appliance()
    monkeypatch.setattr(er, "async_get", lambda _hass: reg)
    original = {"id":"manual","name":"Mijn afwas","kind":"dishwasher",
                "dishwasher_running_states":"Running;Paused",
                "dishwasher_alert_entity":"sensor.aeg_afwasmachine_alerts",
                "dishwasher_alert_mode":"aeg_attributes"}
    out, info = recover_legacy_dishwasher(hass, {"devices": [original]})
    assert info["status"] == "already_configured"
    assert out["devices"] == [original]


def test_removed_recovered_profile_is_not_recreated_or_reenabled(monkeypatch):
    hass, reg = appliance()
    monkeypatch.setattr(er, "async_get", lambda _hass: reg)
    recovered, _ = recover_legacy_dishwasher(hass, {"devices": []})
    recovered["devices"] = []

    out, info = recover_legacy_dishwasher(hass, recovered)

    assert info["status"] == "previously_recovered"
    assert info["changed"] is False
    assert out["devices"] == []


@pytest.mark.asyncio
async def test_retry_stops_and_reports_inactive_after_previously_recovered_profile_removed(monkeypatch):
    hass, reg = appliance()
    monkeypatch.setattr(er, "async_get", lambda _hass: reg)
    recovered, _ = recover_legacy_dishwasher(hass, {"devices": []})
    recovered["devices"] = []
    runtime, _ = build(kind="switch")
    runtime.entry.options = recovered
    runtime.configs.clear()

    retry = LegacyDishwasherRecoveryRetry(runtime)

    assert await retry.attempt() is False
    assert retry._closed is True
    assert runtime.dishwasher_recovery_info["status"] == "previously_recovered"
    assert runtime.dishwasher_recovery_info["retry_active"] is False


@pytest.mark.asyncio
async def test_post_start_retry_adds_late_states_live_rebinds_and_sets_only_recovered_auto(monkeypatch):
    complete_hass, reg = appliance()
    hass = SimpleNamespace(states=States())
    hass.services = Services(hass.states)
    hass.async_create_task = asyncio.create_task

    class ConfigEntries:
        def __init__(self):
            self.updates = []
        def async_update_entry(self, entry, *, options):
            entry.options = deepcopy(options)
            self.updates.append(deepcopy(options))

    hass.config_entries = ConfigEntries()
    monkeypatch.setattr(er, "async_get", lambda _hass: reg)
    unsubscribed = []
    def track_states(_hass, _ids, callback):
        def unsub():
            unsubscribed.append(("state", callback.__name__))
        return unsub
    def track_timer(_hass, callback, _interval):
        def unsub():
            unsubscribed.append(("timer", callback.__name__))
        return unsub
    monkeypatch.setattr(recovery_module, "async_track_state_change_event", track_states)
    monkeypatch.setattr(recovery_module, "async_track_time_interval", track_timer)
    entry = SimpleNamespace(entry_id="late", data={"grid_entity": "sensor.grid"}, options={"devices": []})
    runtime = SolarRuntime(hass, entry)
    runtime.dishwasher_recovery_info = {"status": "not_applicable", "changed": False}
    listener_calls = []
    original_close = runtime.dishwasher_app.close
    original_start = runtime.dishwasher_app.start
    runtime.dishwasher_app.close = lambda: (listener_calls.append("close"), original_close())[1]
    runtime.dishwasher_app.start = lambda: (listener_calls.append("start"), original_start())[1]
    refreshes = []
    async def refresh():
        refreshes.append(True)
    runtime.platforms.refresh = refresh

    retry = LegacyDishwasherRecoveryRetry(runtime)
    assert await retry.start() is False
    assert not runtime.configs
    # The AEG integration and legacy helper publish only after SolarPilot setup.
    hass.states.data.update(complete_hass.states.data)

    assert await retry.attempt() is True
    recovered = next(c for c in runtime.configs.values() if c["kind"] == "dishwasher")
    recovered_id = recovered["id"]
    assert runtime.device_modes[recovered_id] == "auto"
    assert runtime.live_options.applied["devices"][-1]["id"] == recovered_id
    assert listener_calls == ["close", "start"]
    assert refreshes == [True]
    assert hass.config_entries.updates[-1]["devices"][-1]["id"] == recovered_id
    assert runtime.dishwasher_recovery_info["status"] == "recovered"
    assert runtime.dishwasher_recovery_info["retry_active"] is False
    assert unsubscribed == [("state", "_on_state"), ("timer", "_on_interval")]
    assert not runtime.dishwasher_app.data[recovered_id].get("request")
    assert not [call for call in hass.services.calls if call[0] in {"button", "switch", "script"}]
    # Closed/idempotent: no duplicate profile and no second mutation.
    assert await retry.attempt() is False
    retry.close()
    assert unsubscribed == [("state", "_on_state"), ("timer", "_on_interval")]
    assert len([c for c in runtime.configs.values() if c["kind"] == "dishwasher"]) == 1


@pytest.mark.asyncio
async def test_retry_never_overwrites_manual_profile_or_mode():
    runtime, _hass = build(kind="dishwasher")
    before = deepcopy(runtime.configs["a"])
    runtime.device_modes["a"] = "disabled"

    retry = LegacyDishwasherRecoveryRetry(runtime)

    assert await retry.start() is False
    assert await retry.attempt() is False
    assert runtime.configs["a"] == before
    assert runtime.device_modes["a"] == "disabled"


def test_integration_unload_closes_temporary_recovery_listener():
    path = Path(__file__).parents[1] / "custom_components" / "solar_pilot" / "__init__.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    unload = next(node for node in tree.body
                  if isinstance(node, ast.AsyncFunctionDef) and node.name == "async_unload_entry")
    calls = [node for node in ast.walk(unload) if isinstance(node, ast.Call)]
    assert any(isinstance(call.func, ast.Attribute) and call.func.attr == "close"
               and isinstance(call.func.value, ast.Name) and call.func.value.id == "retry"
               for call in calls)
