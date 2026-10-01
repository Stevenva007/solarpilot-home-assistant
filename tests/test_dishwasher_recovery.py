from datetime import datetime, timezone
from types import SimpleNamespace

from homeassistant.helpers import entity_registry as er
from custom_components.solar_pilot.dishwasher_recovery import recover_legacy_dishwasher


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
        rows[eid] = SimpleNamespace(device_id=device, original_name=name)
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
    assert out["devices"] == []


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
