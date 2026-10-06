"""Execute the dashboard to distinguish real activity from available control."""
from html.parser import HTMLParser

import pytest

from test_decision_dashboard56 import browser_double


class ReasonRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.current = None
        self.capture = None

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == "article" and "reason-row" in values.get("class", "").split():
            self.current = {"activity": values.get("data-activity"), "classes": values["class"].split(),
                            "name": "", "state": "", "text": ""}
        elif self.current and tag == "strong" and values.get("class") == "grow":
            self.capture = "name"
        elif self.current and tag == "span" and "badge" in values.get("class", "").split():
            self.capture = "state"

    def handle_data(self, text):
        if self.current is not None:
            self.current["text"] += text
            if self.capture:
                self.current[self.capture] += text

    def handle_endtag(self, tag):
        if tag == "article" and self.current is not None:
            self.rows.append(self.current)
            self.current = None
        if tag in ("strong", "span"):
            self.capture = None


def rendered(**payload):
    markup = browser_double({"render": {"devices": [], **payload}})["html"]
    parsed = ReasonRows()
    parsed.feed(markup)
    return markup, parsed.rows


@pytest.mark.parametrize("device,label", [
    ({"on": True, "owned": True, "power_w": 310}, "Actief · SolarPilot"),
    ({"on": True, "owned": False}, "Actief · toestel"),
    ({"on": True, "manual_forced": True}, "Actief · handmatig"),
    ({"on": True, "kind": "dishwasher", "power_w": 0}, "Programma loopt"),
    ({"on": True, "kind": "dishwasher", "dishwasher": {"airdry": True}}, "Nadrogen actief"),
    # An unavailable power meter does not negate a current confirmed switch state.
    ({"on": True, "owned": True, "isolated": True, "available": True}, "Actief · SolarPilot"),
])
def test_confirmed_on_and_running_programmes_have_blue_edge_and_readable_status(device, label):
    markup, rows = rendered(devices=[{"id": "one", "name": "Toestel", "available": True, **device}])
    assert rows[0]["activity"] == "active" and "is-active" in rows[0]["classes"]
    assert rows[0]["state"] == label
    assert "Bevestigd actief" in markup
    assert ".reason-row.is-active{border-color:var(--sp-activity-blue)" in markup
    assert "--sp-activity-blue:#03a9f4" in markup


@pytest.mark.parametrize("device,activity,label", [
    ({"available": False, "on": True, "power_w": 310}, "unknown", "Niet bereikbaar"),
    ({"available": True, "on": False, "power_w": 310}, "inactive", "Wacht"),
    ({"available": True, "on": False, "kind": "dishwasher"}, "inactive", "Nog niet klaargezet"),
])
def test_offline_old_on_and_off_meter_noise_do_not_show_activity(device, activity, label):
    _, rows = rendered(devices=[{"id": "one", "name": "Toestel", **device}])
    assert rows[0]["activity"] == activity
    assert rows[0]["state"] == label and "is-active" not in rows[0]["classes"]


@pytest.mark.parametrize("zone,activity,label", [
    ({"mode": "auto", "action": "idle", "action_known": True}, "available", "AUTO beschikbaar"),
    ({"mode": "heat_cool", "action": "idle", "action_known": True}, "available", "AUTO beschikbaar"),
    ({"mode": "auto", "action": "heating", "action_known": True}, "active", "Verwarmt"),
    ({"mode": "auto", "action": "cooling", "action_known": True}, "active", "Koelt"),
    ({"mode": "off", "action": "off", "action_known": True}, "inactive", "Regeling uit"),
    ({"mode": "auto", "action": "heating", "available": False}, "unknown", "Activiteit onbekend"),
    ({"mode": "auto", "action": "cooling", "action_known": False}, "unknown", "Activiteit onbekend"),
])
def test_room_auto_availability_and_actual_heat_cool_are_visually_distinct(zone, activity, label):
    markup, rows = rendered(smartClimate={"zones": [{"entity_id": "climate.one", "name": "Ruimte",
                                                    "current": 22, "target": 21, **zone}]})
    assert rows[0]["activity"] == activity
    assert rows[0]["state"] == label + " · 22 °C"
    if activity == "available":
        assert "AUTO betekent nog niet dat de warmtepomp draait" in rows[0]["text"]
        assert ".reason-row.is-available{border-color:var(--sp-activity-blue);border-style:dashed}" in markup


def dhw_fixture(**overrides):
    return {"configured": True, "temperature_c": 49, "actual_target_c": 50, "proposed_target_c": 60,
            "normal_target_c": 50, "execution": {"heating_evidence": {"reported_heating": False},
            "source_evidence": {"target": {"available": True, "restored": False, "age_s": 5}}},
            **overrides}


def test_high_boiler_proposal_alone_is_not_selected_or_heating_activity():
    _, rows = rendered(dhw=dhw_fixture())
    assert rows[0]["activity"] == "inactive"
    assert rows[0]["state"] == "Tank 49 °C · doel 50 °C"
    assert "Extra voorraad ingesteld" not in rows[0]["text"]


def test_reported_high_boiler_goal_is_dashed_selected_buffer_without_heat_claim():
    _, rows = rendered(dhw=dhw_fixture(actual_target_c=60))
    assert rows[0]["activity"] == "available"
    assert rows[0]["state"] == "Extra voorraad ingesteld · Tank 49 °C · doel 60 °C"
    assert "Warmt water op" not in rows[0]["text"]


def test_only_current_boiler_heating_feedback_gets_solid_blue_activity():
    dhw = dhw_fixture()
    dhw["execution"]["heating_evidence"]["reported_heating"] = True
    _, rows = rendered(dhw=dhw)
    assert rows[0]["activity"] == "active"
    assert rows[0]["state"] == "Warmt water op · Tank 49 °C · doel 50 °C"


@pytest.mark.parametrize("source", [
    {"available": False}, {"available": True, "restored": True},
    {"available": True, "age_s": 301}, {"available": True, "age_s": -6},
    {"available": True, "age_s": "bad"},
])
def test_old_or_unavailable_boiler_heating_feedback_cannot_show_active(source):
    dhw = dhw_fixture(actual_target_c=60)
    dhw["execution"]["heating_evidence"]["reported_heating"] = True
    dhw["execution"]["source_evidence"]["target"] = source
    _, rows = rendered(dhw=dhw)
    assert rows[0]["activity"] == "unknown"
    assert rows[0]["state"].startswith("Toestelstatus onbekend")


@pytest.mark.parametrize("known,power,activity", [(True, 3500, "active"), (True, 0, "inactive"), (False, 3500, "unknown")])
def test_wallbox_graphic_uses_current_measured_charging_not_configured_solar_mode(known, power, activity):
    _, rows = rendered(wb={"enabled": True, "configured_mode": "Full Solar", "activity_known": known,
                           "power_w": power, "charging_threshold_w": 50})
    assert rows[0]["activity"] == activity


@pytest.mark.parametrize("aggregate,activity,label", [
    ({"valid": True, "charge_w": 1000, "discharge_w": 0}, "active", "Batterij laadt"),
    ({"valid": True, "charge_w": 0, "discharge_w": 1000}, "active", "Batterij levert stroom"),
    ({"valid": False, "charge_w": 1000}, "inactive", "Regeling aan"),
    ({"valid": True, "charge_w": 0, "discharge_w": 0}, "inactive", "Regeling aan"),
])
def test_battery_proposed_power_is_not_current_activity(aggregate, activity, label):
    _, rows = rendered(batteryFleet={"enabled": True, "control_enabled": True,
                                    "recommendation_w": -1000, "aggregate": aggregate})
    assert rows[0]["activity"] == activity and label in rows[0]["state"]


def test_activity_markup_remains_textual_and_escapes_device_names_and_reasons():
    markup, rows = rendered(devices=[{"id": "one", "name": '<img src=x onerror="bad()">',
                                    "available": True, "on": True, "reason": "Actief <script>"}])
    assert rows[0]["activity"] == "active" and "Actief · toestel" in rows[0]["state"]
    assert "<img" not in markup and "<script>" not in markup
    assert "&lt;img" in markup and "Actief &lt;script&gt;" in markup
