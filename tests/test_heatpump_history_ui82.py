"""Exercise the shipped UI against distinct task, support, contact and tank evidence."""
from datetime import datetime
import time

import pytest

from test_heatpump_history_ui70 import history_fixture, render_history
from test_heatpump_ui65 import metered_sample, parsed, business_tile
from test_overview_details60 import Markup


def point(iso, temperature, target):
    stamp = datetime.fromisoformat(iso).timestamp()
    return {"captured_at": stamp, "temperature_c": temperature,
            "temperature_reported_at": stamp-3, "ordinary_target_c": target,
            "ordinary_target_reported_at": stamp-5, "continuous_from_previous": False}


def test_contact_lane_is_visible_and_does_not_use_request_or_reception():
    data = history_fixture()
    session = data["sessions"][0]
    data["sg_contact_overlay"] = {"schema": 1, "on_s": 0, "segments": [
        dict(session, state="off", reported_at=1),
        dict(session, state="unknown", left_pct=60, width_pct=10, reported_at=None)]}
    root = Markup(render_history(data)["html"]).root
    overlay = next(n for n in root.walk() if "data-sg-contact-overlay" in n.attributes)
    assert "0 s AAN" in overlay.text()
    states = [n.attributes["data-sg-contact-state"] for n in overlay.walk()
              if "data-sg-contact-state" in n.attributes]
    assert states == ["off", "unknown"]
    assert "AAN-tijd onbekend" not in overlay.text()
    # A requested session of 10 minutes cannot fabricate any contact AAN.
    assert not any(n.attributes.get("data-sg-contact-state") == "on" for n in root.walk())
    assert "Onbekend / meetgat" in overlay.text()


def test_historical_boiler_values_are_source_bound_and_current_values_cannot_leak():
    data = history_fixture()
    data["today"] = "2026-10-13"
    data["tank_temperature"] = {"schema": 1, "stale_s": 120,
        "current": {"current": True, "captured_at": time.time(), "capture_stale_s": 30, "stale_s": 120, "temperature_c": 61, "ordinary_target_c": 62,
                    "temperature_reported_at": time.time(), "ordinary_target_reported_at": time.time()},
        "points": [point("2026-10-12T06:05:00+02:00", 44, 50),
                   point("2026-10-12T06:55:00+02:00", 49, 51),
                   point("2026-10-13T09:05:00+02:00", 58, 60)]}
    root = Markup(render_history(data)["html"]).root
    strip = next(n for n in root.walk() if "data-tank-history" in n.attributes)
    assert strip.attributes["data-tank-history"] == "recorded"
    assert "49 °C" in strip.text() and "51 °C" in strip.text()
    assert "61 °C" not in strip.text() and "62 °C" not in strip.text()
    row = next(n for n in root.walk() if "data-session-tank" in n.attributes)
    assert "44 °C → 49 °C" in row.text() and "ingesteld doel 51 °C" in row.text()
    assert "06:04:57" in row.text() and "06:54:57" in row.text()


def test_current_boiler_values_expire_independently_including_real_zero():
    data = history_fixture()
    data["tank_temperature"] = {"schema": 1, "stale_s": 120,
        "current": {"current": True, "captured_at": time.time(), "capture_stale_s": 30, "stale_s": 120, "temperature_c": 0, "ordinary_target_c": 62,
                    "temperature_reported_at": time.time(), "ordinary_target_reported_at": time.time()-1000},
        "points": []}
    root = Markup(render_history(data)["html"]).root
    assert next(n for n in root.walk() if "data-tank-temperature" in n.attributes).text() == "0 °C"
    assert next(n for n in root.walk() if "data-tank-target" in n.attributes).text() == "—"


def display(function="tapwater_heating", **override):
    stamp = time.time()-2
    value = {"read_only": True, "model_eligible": False, "function": function, "context": function, "source": "aquarea_entity",
        "tier": "derived", "observed_at": stamp, "valid_until": stamp+120,
        "activity_observed_at": stamp, "activity_valid_until": stamp+120,
        "active": True, "stale_s": 120,
        "support": {"active": True, "watts": 2760, "observed_at": stamp, "valid_until": stamp+120}}
    value.update(override)
    return value


@pytest.mark.parametrize("function,label", [("tapwater_heating", "Boiler opwarmen"),
    ("space_heating", "Verwarmen"), ("space_cooling", "Koelen"),
    ("defrost", "Ontdooien"), ("sterilization", "Sterilisatie")])
def test_new_primary_task_is_retained_beside_electrical_support(function, label):
    data = metered_sample(2760, complete=False, roles=("heater", "unconfirmed"))
    data["panasonic"]["operation_display"] = display(function)
    _, root = parsed(data)
    assert label in business_tile(root, "data-heatpump-task").text()
    assert "Aan" in business_tile(root, "data-heatpump-heater").text()
    assert "2,76 kW" in business_tile(root, "data-heatpump-heater").text()
    assert "Compressor draait" not in business_tile(root, "data-heatpump-task").text()


def test_expired_primary_task_cannot_fall_back_to_legacy_selected_program():
    data = metered_sample(3700, function="space_heating", roles=("main", "heater"))
    data["panasonic"]["operation_display"] = display("tapwater_heating", observed_at=time.time()-1000,
                                                   valid_until=time.time()-880)
    _, root = parsed(data)
    task = business_tile(root, "data-heatpump-task")
    assert "Actief · taak onbekend" in task.text()
    assert "Boiler opwarmen" not in task.text() and "Verwarmen" not in task.text()


def test_boiler_actual_and_target_are_on_overview_with_independent_freshness():
    data = metered_sample()
    data["panasonic"].update(temperature_c=47.3, target_c=51.2, target_stamp=time.time()-1000)
    _, root = parsed(data)
    strip = next(n for n in root.walk() if "data-boiler-temperatures" in n.attributes)
    assert "47,3 °C" in strip.text() and "Ingesteld boilerdoel" in strip.text()
    assert "51,2 °C" not in strip.text() and "—" in strip.text()


def test_multi_heater_sum_expires_while_newer_feed_still_proves_support_on():
    data = metered_sample(2400, complete=False, roles=("heater", "unconfirmed"))
    value = display("tapwater_heating")
    now = time.time()
    # The 2500 W sum includes an older 100 W feed and a newer 2400 W feed.
    # After the older feed expires, only the latter still proves support AAN.
    value["support"].update(watts=2500, observed_at=now-2, valid_until=now+118,
                            watts_observed_at=now-121, watts_valid_until=now-1)
    data["panasonic"]["operation_display"] = value
    _, root = parsed(data)
    support = business_tile(root, "data-heatpump-heater")
    assert "Aan" in support.text()
    assert support.attributes["data-heatpump-heater"] == "active"
    assert "2,5 kW" not in support.text()
    assert "2,4 kW" not in support.text(), "An expired sum cannot silently become a partial measurement"
    assert not any(n.tag == "b" for n in support.walk())
