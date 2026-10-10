"""Execute the dashboard to distinguish real activity from available control."""
from html.parser import HTMLParser
import time

import pytest

from test_decision_dashboard56 import browser_double
from test_heatpump_ui65 import metered_sample


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


def row_named(rows, name):
    matches = [row for row in rows if row["name"] == name]
    assert len(matches) == 1, (name, [row["name"] for row in rows])
    return matches[0]


def heatpump_row(rows):
    return row_named(rows, "Warmtepomp — Panasonic-regeling / SG-zonneboost")


def assert_unknown_heatpump_operation_is_hidden(row):
    assert row["activity"] == "unknown" and row["state"] == ""
    assert "is-active" not in row["classes"] and "is-inactive" not in row["classes"]
    assert "Werking onbekend" not in row["text"]


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
    row = row_named(rows, "Toestel")
    assert row["activity"] == "active" and "is-active" in row["classes"]
    assert row["state"] == label
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
    row = row_named(rows, "Toestel")
    assert row["activity"] == activity
    assert row["state"] == label and "is-active" not in row["classes"]


@pytest.mark.parametrize("zone", [
    {"mode": "auto", "action": "idle"}, {"mode": "heat_cool", "action": "idle"},
    {"mode": "auto", "action": "heating"}, {"mode": "auto", "action": "cooling"},
    {"mode": "off", "action": "off"}, {"mode": "unknown", "action": None, "available": False},
    {"mode": "auto", "action": None},
])
def test_readonly_room_activity_does_not_invent_a_sg_request_or_contact_confirmation(zone):
    stamp = time.time()
    markup, rows = rendered(panasonic={"configured": True, "zones": [{"entity_id": "climate.one",
        "name": "Ruimte", "temperature_c": 22, "target_c": 21, "observed_at": stamp, **zone}]},
        sgBoost=sg_fixture())
    assert len(rows) == 1
    row = heatpump_row(rows)
    # A room action is read-only context. This frontend requires the monitor's
    # independent operation evidence; the reported zone alone cannot invent it.
    assert_unknown_heatpump_operation_is_hidden(row)
    assert "SG-contact open" in row["text"] and "Niet aangevraagd" in row["text"]
    assert "Ruimte" in row["text"]
    if zone.get("available") is False:
        assert "22 °C" not in row["text"] and "Onbekend of verouderd" in row["text"]
    else:
        assert "22 °C" in row["text"]
    assert "Panasonic en ruimtes · alleen uitlezen" in markup
    assert 'data-action="climate_' not in markup


def sg_fixture(**overrides):
    stamp = time.time()
    return {"configured": True, "desired_on": False, "relay_on": False,
            "relay_confirmed": True, "panasonic_confirmed": None,
            "observed_at": stamp, "relay_observed_at": stamp, "relay_stale_s": 120, **overrides}


def test_high_reported_tank_target_alone_is_not_a_sg_request_or_contact_activity():
    stamp = time.time()
    _, rows = rendered(panasonic={"configured": True, "temperature_c": 49, "target_c": 60,
                                 "temperature_stamp": stamp, "target_stamp": stamp},
                       sgBoost=sg_fixture())
    row = heatpump_row(rows)
    assert_unknown_heatpump_operation_is_hidden(row)
    assert "SG-contact open" in row["text"]
    assert "60 °C" in row["text"] and "Afzonderlijk bevestigd" not in row["text"]


def test_sg_request_is_separately_active_without_inventing_heatpump_activity():
    markup, rows = rendered(panasonic={"configured": True, "temperature_c": 49, "target_c": 50},
                           sgBoost=sg_fixture(desired_on=True, relay_confirmed=False, relay_on=None))
    row = heatpump_row(rows)
    assert_unknown_heatpump_operation_is_hidden(row)
    assert 'data-sg-stage="request"' not in markup
    assert "SolarPilot-aanvraag" in row["text"]
    assert 'class="sg-stage is-unknown" data-sg-stage="relay"' in markup
    assert "Aangevraagd" in row["text"] and "Nog niet bevestigd" in row["text"]
    assert "is-active" not in row["classes"] and "is-available" not in row["classes"]


def test_confirmed_active_sg_contact_is_visible_without_a_blue_heatpump_activity_edge():
    markup, rows = rendered(panasonic={"configured": True, "temperature_c": 49, "target_c": 50},
                       sgBoost=sg_fixture(desired_on=True, relay_on=True))
    row = heatpump_row(rows)
    assert_unknown_heatpump_operation_is_hidden(row)
    assert 'class="sg-stage is-active" data-sg-stage="relay"' in markup
    assert "SG-contact actief" in row["text"]
    assert 'data-sg-stage="received"' not in markup
    assert "Ontvangen SG-status" not in row["text"]


@pytest.mark.parametrize("state,label,activity", [("active", "Compressor draait", "active"),
                                                ("idle", "Compressor staat stil", "inactive")])
def test_fresh_native_operation_controls_blue_edge_independently_of_open_sg(state, label, activity):
    markup, rows = rendered(panasonic={"configured": True, "operation": {
        "state": state, "label": label, "evidence": "compressor_frequency",
        "observed_at": time.time(), "stale_s": 120}}, sgBoost=sg_fixture())
    row = heatpump_row(rows)
    assert row["activity"] == activity and row["state"] == label
    assert ("is-active" in row["classes"]) is (state == "active")
    assert 'class="sg-stage is-inactive" data-sg-stage="relay"' in markup
    assert "SG-contact open" in row["text"]


@pytest.mark.parametrize("watts,label,activity", [(0, "Geen elektrisch verbruik", "inactive"),
                                                 (199, "Basisverbruik", "inactive"),
                                                 (200, "Warmtepomp werkt", "active")])
def test_metered_heatpump_activity_preserves_other_device_badges_and_independent_sg(watts, label, activity):
    data = metered_sample(watts)
    markup, rows = rendered(panasonic=data["panasonic"], sgBoost=sg_fixture(desired_on=True, relay_on=True),
        devices=[{"id": "one", "name": "Toestel", "available": True, "on": True, "owned": True}])
    row = heatpump_row(rows)
    assert row["state"] == label and row["activity"] == activity
    assert ("is-active" in row["classes"]) is (activity == "active")
    assert "Afgeleid uit gemeten elektrisch verbruik" in row["text"]
    assert "Bevestigd actief of afgeleid uit verbruik" in markup
    assert 'class="sg-stage is-active" data-sg-stage="relay"' in markup
    device = row_named(rows, "Toestel")
    assert device["state"] == "Actief · SolarPilot" and device["activity"] == "active"


@pytest.mark.parametrize("program", ["heating", "cooling", "dhw", "auto", "off"])
def test_selected_native_programme_alone_never_animates_the_heatpump(program):
    _, rows = rendered(panasonic={"configured": True, "program": program}, sgBoost=sg_fixture())
    row = heatpump_row(rows)
    assert_unknown_heatpump_operation_is_hidden(row)


@pytest.mark.parametrize("contact", [
    {"relay_on": True, "relay_confirmed": False},
    {"relay_on": False, "relay_confirmed": False},
    {"relay_on": None, "relay_confirmed": False},
    {"relay_on": None, "relay_confirmed": None},
    {"relay_on": True, "relay_confirmed": None},
])
def test_old_or_unavailable_contact_feedback_cannot_show_confirmed_sg_activity(contact):
    markup, rows = rendered(panasonic={"configured": True, "temperature_c": 49, "target_c": 60},
                       sgBoost=sg_fixture(**contact))
    row = heatpump_row(rows)
    assert_unknown_heatpump_operation_is_hidden(row)
    assert 'class="sg-stage is-unknown" data-sg-stage="relay"' in markup


@pytest.mark.parametrize("known,power,activity", [(True, 3500, "active"), (True, 0, "inactive"), (False, 3500, "unknown")])
def test_wallbox_graphic_uses_current_measured_charging_not_configured_solar_mode(known, power, activity):
    _, rows = rendered(wb={"enabled": True, "configured_mode": "Full Solar", "activity_known": known,
                           "power_w": power, "charging_threshold_w": 50})
    assert row_named(rows, "Auto laden")["activity"] == activity


@pytest.mark.parametrize("aggregate,activity,label", [
    ({"valid": True, "charge_w": 1000, "discharge_w": 0}, "active", "Batterij laadt"),
    ({"valid": True, "charge_w": 0, "discharge_w": 1000}, "active", "Batterij levert stroom"),
    ({"valid": False, "charge_w": 1000}, "inactive", "Regeling aan"),
    ({"valid": True, "charge_w": 0, "discharge_w": 0}, "inactive", "Regeling aan"),
])
def test_battery_proposed_power_is_not_current_activity(aggregate, activity, label):
    _, rows = rendered(batteryFleet={"enabled": True, "control_enabled": True,
                                    "recommendation_w": -1000, "aggregate": aggregate})
    row = row_named(rows, "Batterij")
    assert row["activity"] == activity and label in row["state"]


def test_activity_markup_remains_textual_and_escapes_device_names_and_reasons():
    markup, rows = rendered(devices=[{"id": "one", "name": '<img src=x onerror="bad()">',
                                    "available": True, "on": True, "reason": "Actief <script>"}])
    row = row_named(rows, '<img src=x onerror="bad()">')
    assert row["activity"] == "active" and "Actief · toestel" in row["state"]
    assert "<img" not in markup and "<script>" not in markup
    assert "&lt;img" in markup and "Actief &lt;script&gt;" in markup
