"""Run shipped heat-pump markup against independent fresh/stale evidence.

These are Node renderer checks, not browser layout or physical HA acceptance.
Synthetic entity IDs and values deliberately contain no installation data.
"""
import time

import pytest

from test_overview_details60 import Markup
from test_sg_ui_platforms62 import execute, text


def sample():
    now = time.time()
    return {
        "mode": "solar", "config_entry_id": "example", "devices": [],
        "panasonic": {
            "configured": True, "source_stale_s": 120,
            "operation": {"state": "active", "label": "Warmtepomp in werking",
                          "evidence": "native_action", "observed_at": now, "stale_s": 120},
            "temperature_c": 47.3, "temperature_stamp": now,
            "target_c": 51.2, "target_stamp": now,
            "power_w": 3700, "power_kind": "measured", "power_scope": "total",
            "power_observed_at": now, "power_complete": True,
            "power_supply1_w": 3100, "power_supply1_valid": True,
            "power_supply1_observed_at": now,
            "power_supply2_w": 600, "power_supply2_valid": True,
            "power_supply2_observed_at": now,
            "compressor_frequency_hz": 42, "compressor_running": True,
            "compressor_frequency_observed_at": now,
            "sg_status": "inactive", "sg_status_confirmed": True,
            "sg_status_observed_at": now,
            "program": "heating", "program_label": "Verwarmen",
            "context_reliable": True, "context_stamp": now,
            "zones": [{"name": "Testzone", "current": 22.7, "target": 23.4,
                       "mode": "heat", "action": "heating", "available": True,
                       "observed_at": now}],
        },
        "sg_boost": {
            "configured": True, "enabled": True, "desired_on": False,
            "relay_on": False, "relay_confirmed": True,
            "observed_at": now, "relay_observed_at": now, "relay_stale_s": 120,
            "reason": "Wacht op voldoende zonneoverschot", "owner": "none",
            "switch_entity": "switch.synthetic_physical_contact",
            "enabled_entity": "switch.synthetic_policy",
            "resume_entity": "button.synthetic_resume",
        },
    }


def metered_sample(watts=3700, *, complete=True, function=None, roles=("unconfirmed", "unconfirmed")):
    """A backend power classification, independent of native operation/SG."""
    data = sample()
    p = data["panasonic"]
    p.pop("operation")
    stamp = p["power_observed_at"]
    state = "off" if watts == 0 else "basis" if watts < 200 else "active"
    label = {"off": "Geen elektrisch verbruik", "basis": "Basisverbruik", "active": "Warmtepomp werkt"}[state]
    if function:
        label = {"tapwater_heating": "Sanitair water opwarmen", "space_heating": "Ruimte verwarmen",
                 "space_cooling": "Ruimte koelen"}[function]
    p.update(power_scope="split", power_w=watts if complete else None, power_complete=complete,
             power_supply1_w=watts, power_supply2_w=0, power_supply2_valid=complete)
    supplies = [
        {"number": number, "role": roles[number - 1], "label": f"Voeding {number}",
         "watts": value, "valid": valid, "state": supply_state, "observed_at": stamp if valid else None}
        for number, value, valid, supply_state in [(1, watts, True, state), (2, 0 if complete else None, complete, "off" if complete else "unknown")]
    ]
    p["power_activity"] = {
        "state": state if complete else "partial", "active": watts >= 200,
        "label": label if complete else "Actief verbruik op voeding 1",
        "note": "Afgeleid uit gemeten elektrisch verbruik; dit bevestigt geen compressor- of SG-effect.",
        "evidence": "metered_power_and_context" if function else "metered_power",
        "threshold_w": 200, "observed_at": stamp, "stale_s": 120,
        "total_w": watts if complete else None, "complete": complete, "function": function if complete else None,
        "context_observed_at": stamp if function else None, "supplies": supplies,
    }
    return data


def parsed(data, view="board"):
    result = execute(data, view=view)
    assert result["calls"] == [], "Rendering must never control physical equipment"
    return result, Markup(result["initial"]).root


def heatpump_row(root):
    return next(node for node in root.walk()
                if node.tag == "article" and "Warmtepomp — Panasonic-regeling" in node.text())


def stage(root, name):
    return next(node for node in root.walk() if node.attributes.get("data-sg-stage") == name)


def class_names(node):
    return node.attributes.get("class", "").split()


def heatpump_panel(root):
    panels = [node for node in root.walk()
              if node.attributes.get("data-reason-key") == "overview:sg"
              or "heatpump-sg" in class_names(node)]
    assert len(panels) == 1
    return panels[0]


def assert_unknown_operation_is_hidden(root):
    panel = heatpump_panel(root)
    assert panel.attributes["data-activity"] == "unknown"
    assert "is-unknown" in class_names(panel)
    assert "is-active" not in class_names(panel)
    assert "is-inactive" not in class_names(panel)
    assert "is-idle" not in class_names(panel)
    assert not any(node.attributes.get("data-heatpump-operation") is not None
                   or {"heatpump-operation", "heatpump-icon", "heatpump-fan"}.intersection(class_names(node))
                   for node in panel.walk())
    if panel.tag == "article":
        header = next(node for node in panel.walk() if "row" in class_names(node))
        assert not any("badge" in class_names(node) for node in header.walk())
    assert "Werking onbekend" not in panel.text()


def operation_graphic(root):
    graphics = [node for node in heatpump_panel(root).walk() if "heatpump-operation" in class_names(node)]
    assert len(graphics) == 1
    return graphics[0]


def supply_row(root, number):
    rows = [node for node in heatpump_panel(root).walk()
            if node.attributes.get("data-supply-number") == str(number)]
    assert len(rows) == 1
    return rows[0]


@pytest.mark.parametrize("view", ["board", "comfort"])
@pytest.mark.parametrize("watts,label,activity", [(0, "Geen elektrisch verbruik", "inactive"),
                                                 (199, "Basisverbruik", "inactive"),
                                                 (200, "Warmtepomp werkt", "active"),
                                                 (3700, "Warmtepomp werkt", "active")])
def test_confirmed_complete_power_can_describe_electrical_activity_without_native_operation(view, watts, label, activity):
    _, root = parsed(metered_sample(watts), view)
    panel = heatpump_panel(root)
    graphic = operation_graphic(root)
    assert panel.attributes["data-activity"] == activity
    assert label in graphic.text()
    assert "afgeleid" in graphic.text().lower()
    assert graphic.attributes["data-evidence"] == "metered_power"
    assert ("is-active" in class_names(panel)) is (activity == "active")
    assert "Werking onbekend" not in panel.text()
    for which in ["request", "relay", "received"]:
        assert "is-inactive" in class_names(stage(panel, which))


@pytest.mark.parametrize("function,label", [("tapwater_heating", "Sanitair water opwarmen"),
                                           ("space_heating", "Ruimte verwarmen"),
                                           ("space_cooling", "Ruimte koelen")])
def test_power_and_fresh_separate_context_show_an_explicit_function_inference(function, label):
    _, root = parsed(metered_sample(function=function))
    graphic = operation_graphic(root)
    assert label in graphic.text()
    assert "afgeleid" in graphic.text().lower()
    assert graphic.attributes["data-evidence"] == "metered_power_and_context"
    assert "is-active" in class_names(heatpump_panel(root))
    assert "Compressor draait" not in graphic.text()


@pytest.mark.parametrize("stamp", [None, "stale", "future"])
def test_expired_function_context_falls_back_to_still_fresh_generic_power(stamp):
    data = metered_sample(function="tapwater_heating")
    invalid = time.time() - 121 if stamp == "stale" else time.time() + 60 if stamp == "future" else None
    data["panasonic"]["power_activity"].update(context_observed_at=invalid, observed_at=invalid)
    _, root = parsed(data)
    graphic = operation_graphic(root)
    assert "Warmtepomp werkt" in graphic.text()
    assert "Sanitair water opwarmen" not in graphic.text()
    assert graphic.attributes["data-evidence"] == "metered_power"
    assert "is-active" in class_names(heatpump_panel(root))


@pytest.mark.parametrize("power_expired", [False, True])
def test_single_complete_meter_and_function_context_expire_independently(power_expired):
    data = metered_sample(function="tapwater_heating")
    p = data["panasonic"]
    p["power_scope"] = "total"
    stale = time.time() - 121
    p["power_activity"].update(supplies=[], context_observed_at=stale, observed_at=stale)
    if power_expired:
        p["power_observed_at"] = p["power_stamp"] = stale
    _, root = parsed(data)
    panel = heatpump_panel(root)
    assert "Sanitair water opwarmen" not in panel.text()
    if power_expired:
        assert_unknown_operation_is_hidden(root)
        assert "Vermogen nog niet bekend" in panel.text()
    else:
        assert "Warmtepomp werkt" in operation_graphic(root).text()
        assert "3,7 kW" in panel.text()
        assert operation_graphic(root).attributes["data-evidence"] == "metered_power"
    for which in ["request", "relay", "received"]:
        assert "is-inactive" in class_names(stage(panel, which))


def test_one_fresh_high_supply_reports_only_its_partial_activity():
    _, root = parsed(metered_sample(3700, complete=False))
    panel = heatpump_panel(root)
    graphic = operation_graphic(root)
    assert "Actief verbruik op voeding 1" in graphic.text()
    assert "Warmtepomp werkt" not in graphic.text()
    assert "Sanitair water opwarmen" not in graphic.text()
    assert graphic.attributes["data-evidence"] == "metered_power"
    power = next(node for node in panel.walk() if "reason-power" in class_names(node))
    assert "Vermogen nog niet bekend" in power.text()
    assert "Totaal onbekend · deelmeting onvolledig" in power.text()
    first = next(node for node in power.walk() if node.attributes.get("data-supply-number") == "1")
    second = next(node for node in power.walk() if node.attributes.get("data-supply-number") == "2")
    assert "3,7 kW" in first.text() and "Actief verbruik" in first.text()
    assert "Geen actuele meting" in second.text() and "0 W" not in second.text()


@pytest.mark.parametrize("watts", [0, 199])
def test_one_partial_low_supply_cannot_describe_whole_heatpump_as_idle_or_off(watts):
    _, root = parsed(metered_sample(watts, complete=False))
    assert_unknown_operation_is_hidden(root)
    panel = heatpump_panel(root)
    assert "Geen elektrisch verbruik" not in panel.text()
    assert "Totaal onbekend · deelmeting onvolledig" in panel.text()
    first = next(node for node in panel.walk() if node.attributes.get("data-supply-number") == "1")
    assert first.attributes["data-supply-state"] == ("off" if watts == 0 else "basis")
    assert ("Geen verbruik" if watts == 0 else "Basisverbruik") in first.text()


@pytest.mark.parametrize("which", [1, 2])
def test_new_power_snapshot_cannot_refresh_an_expired_underlying_supply(which):
    data = metered_sample(function="tapwater_heating")
    stale = time.time() - 121
    p = data["panasonic"]
    p[f"power_supply{which}_observed_at"] = stale
    p["power_activity"]["supplies"][which - 1]["observed_at"] = stale
    _, root = parsed(data)
    panel = heatpump_panel(root)
    assert "Warmtepomp werkt" not in panel.text()
    assert "Sanitair water opwarmen" not in panel.text()
    assert "Totaal voeding 1 + voeding 2" not in panel.text()
    assert "3,7 kW" not in next(node for node in panel.walk() if "reason-power" in class_names(node)).children[0].text()
    assert_unknown_operation_is_hidden(root)
    if which == 2:
        first = next(node for node in panel.walk() if node.attributes.get("data-supply-number") == "1")
        assert "3,7 kW" in first.text() and "Actief verbruik" in first.text()


@pytest.mark.parametrize("stamp", [None, "stale", "future"])
def test_fresh_individual_supplies_do_not_refresh_expired_generic_classification(stamp):
    data = metered_sample()
    data["panasonic"]["power_activity"]["observed_at"] = (
        time.time() - 121 if stamp == "stale" else time.time() + 60 if stamp == "future" else None)
    _, root = parsed(data)
    assert_unknown_operation_is_hidden(root)
    assert "3,7 kW" in supply_row(root, 1).text()
    assert "0 W" in supply_row(root, 2).text()


@pytest.mark.parametrize("roles", [("unconfirmed", "unconfirmed"), ("main", "heater")])
def test_feed_functions_are_shown_only_when_explicitly_configured_and_zero_remains_a_reading(roles):
    _, root = parsed(metered_sample(3700, roles=roles))
    first, second = supply_row(root, 1), supply_row(root, 2)
    assert "3,7 kW" in first.text() and "Actief verbruik" in first.text()
    assert "0 W" in second.text() and "Geen verbruik" in second.text()
    assert second.attributes["data-supply-state"] == "off"
    if roles[0] == "main":
        assert "regeling" in first.text() and "pompen" in first.text()
        assert "Elektrische ondersteuning" in second.text()
    else:
        assert "compressor" not in first.text().lower() and "pompen" not in first.text().lower()
        assert "Elektrische ondersteuning" not in second.text()


def test_native_compressor_operation_remains_visible_with_zero_electrical_classification():
    data = metered_sample(0)
    data["panasonic"]["operation"] = {"state": "active", "label": "Compressor draait",
        "evidence": "compressor_frequency", "observed_at": time.time(), "stale_s": 120}
    _, root = parsed(data)
    graphic = operation_graphic(root)
    assert "Compressor draait" in graphic.text()
    assert "Geen elektrisch verbruik" in graphic.text()
    assert graphic.attributes["data-compressor-running"] == "true"
    assert "is-active" in class_names(heatpump_panel(root))


def test_native_active_operation_and_power_task_inference_remain_distinguishable():
    data = metered_sample(function="tapwater_heating")
    data["panasonic"]["operation"] = {"state": "active", "label": "Compressor draait",
        "evidence": "compressor_frequency", "observed_at": time.time(), "stale_s": 120}
    _, root = parsed(data)
    graphic = operation_graphic(root)
    assert "Sanitair water opwarmen" in graphic.text()
    assert "Compressor draait" in graphic.text()
    assert "afgeleid" in graphic.text().lower()
    assert graphic.attributes["data-evidence"] == "nativelyconfirmed"
    assert graphic.attributes["data-compressor-running"] == "true"


def test_legacy_single_partial_meter_has_no_whole_heatpump_total_or_function():
    data = metered_sample(3700, complete=False)
    p = data["panasonic"]
    p.update(power_scope="supply1", power_w=3700, power_supply1_w=None, power_supply1_valid=False)
    p["power_activity"].update(supplies=[], label="Actief verbruik op deelmeter")
    _, root = parsed(data)
    graphic = operation_graphic(root)
    assert "Actief verbruik op deelmeter" in graphic.text()
    assert "Warmtepomp werkt" not in graphic.text() and "Sanitair water opwarmen" not in graphic.text()
    assert "Alleen voeding 1 · gedeeltelijke meting" in heatpump_panel(root).text()
    assert "Totaal warmtepomp" not in heatpump_panel(root).text()


@pytest.mark.parametrize("function,label", [(None, "Warmtepomp werkt"),
                                           ("tapwater_heating", "Sanitair water opwarmen")])
def test_native_idle_and_high_auxiliary_power_show_electrical_activity_while_preserving_compressor_zero(function, label):
    data = metered_sample(3700, function=function, roles=("main", "heater"))
    p = data["panasonic"]
    p["operation"] = {"state": "idle", "label": "Compressor staat stil", "evidence": "compressor_frequency",
                      "observed_at": time.time(), "stale_s": 120}
    p.update(compressor_frequency_hz=0, compressor_running=False, power_supply1_w=0, power_supply2_w=3700)
    p["power_activity"]["supplies"][0].update(watts=0, state="off")
    p["power_activity"]["supplies"][1].update(watts=3700, state="active")
    _, root = parsed(data)
    graphic = operation_graphic(root)
    heading = next(node for node in graphic.walk() if node.tag == "strong")
    note = next(node for node in graphic.walk() if node.tag == "small")
    assert label in heading.text() and "0 Hz" in heading.text()
    assert "Compressor staat stil" not in heading.text()
    assert "Compressor staat stil" in note.text()
    assert "afgeleid" in graphic.text().lower()
    assert graphic.attributes["data-compressor-running"] == "false"
    assert graphic.attributes["data-evidence"] == ("metered_power_and_context" if function else "metered_power")
    assert "is-active" in class_names(heatpump_panel(root))
    assert "Elektrische ondersteuning" in heatpump_panel(root).text()


def test_sg_contact_receipt_and_policy_do_not_change_metered_activity():
    data = metered_sample()
    _, off_root = parsed(data)
    data["sg_boost"].update(desired_on=True, relay_on=True)
    data["panasonic"]["sg_status"] = "active"
    _, on_root = parsed(data)
    assert operation_graphic(off_root).text() == operation_graphic(on_root).text()
    assert operation_graphic(off_root).attributes == operation_graphic(on_root).attributes
    for which in ["request", "relay", "received"]:
        assert "is-inactive" in class_names(stage(off_root, which))
        assert "is-active" in class_names(stage(on_root, which))
    assert "Compressorbedrijf bewijst geen extra verbruik door SG" in heatpump_panel(on_root).text()


def test_native_operation_gets_active_article_while_sg_is_open():
    _, root = parsed(sample())
    row = heatpump_row(root)
    assert row.attributes["data-activity"] == "active"
    assert "is-active" in class_names(row)
    assert "is-inactive" in class_names(stage(row, "request"))
    assert "is-inactive" in class_names(stage(row, "relay"))
    assert "is-inactive" in class_names(stage(row, "received"))
    assert "Warmtepomp in werking" in row.text()
    graphic = [node for node in row.walk() if node.attributes.get("data-heatpump-operation") == "active"]
    assert len(graphic) == 1
    assert "Warmtepomp in werking" in graphic[0].text()


@pytest.mark.parametrize("operation,expected", [("idle", "inactive"), ("unknown", "unknown")])
def test_sg_contact_and_receipt_never_promote_idle_or_unknown_operation(operation, expected):
    data = sample()
    data["panasonic"]["operation"].update(state=operation, label="Geen actieve warmte- of koelactie")
    data["panasonic"].update(sg_status="active", compressor_running=False, compressor_frequency_hz=0)
    data["sg_boost"].update(desired_on=True, relay_on=True)
    _, root = parsed(data)
    row = heatpump_row(root)
    assert row.attributes["data-activity"] == expected
    assert "is-active" not in class_names(row)
    assert "is-active" in class_names(stage(row, "request"))
    assert "is-active" in class_names(stage(row, "relay"))
    assert "is-active" in class_names(stage(row, "received"))
    if operation == "unknown":
        assert_unknown_operation_is_hidden(root)
    else:
        assert any(node.attributes.get("data-heatpump-operation") == "idle" for node in row.walk())
        assert "Geen actieve warmte- of koelactie" in row.text()


@pytest.mark.parametrize("view", ["board", "comfort"])
@pytest.mark.parametrize("missing_operation", [False, True])
def test_high_measured_watts_with_unknown_operation_hides_indicator_and_keeps_other_information(view, missing_operation):
    data = sample()
    if missing_operation:
        data["panasonic"].pop("operation")
    else:
        data["panasonic"]["operation"].update(state="unknown", label="Werking onbekend", evidence="none")
    data["panasonic"]["power_w"] = 9000
    _, root = parsed(data, view)
    assert_unknown_operation_is_hidden(root)
    panel = heatpump_panel(root)
    for reading in ["9 kW", "gemeten", "47,3 °C", "51,2 °C", "Verwarmen", "Testzone"]:
        assert reading in panel.text()
    for which in ["request", "relay", "received"]:
        assert "is-inactive" in class_names(stage(panel, which))
    assert data["sg_boost"]["reason"] in panel.text()
    assert any(node.tag == "details" and node.attributes.get("data-ui-key") == f"sg:{'overview' if view == 'board' else view}:monitor"
               for node in panel.walk())
    assert any(node.tag == "details" for node in panel.walk())


@pytest.mark.parametrize("stamp", [None, "not-a-timestamp", 0, -10, "stale", "future"])
@pytest.mark.parametrize("view", ["board", "comfort"])
def test_missing_stale_or_invalid_operation_timestamp_hides_only_operation(stamp, view):
    data = sample()
    if stamp == "stale":
        stamp = time.time() - 121
    elif stamp == "future":
        stamp = time.time() + 60
    data["panasonic"]["operation"]["observed_at"] = stamp
    _, root = parsed(data, view)
    assert_unknown_operation_is_hidden(root)
    panel = heatpump_panel(root)
    assert "3,7 kW" in panel.text() and "47,3 °C" in panel.text()
    assert data["sg_boost"]["reason"] in panel.text()
    assert len([node for node in panel.walk() if "data-sg-stage" in node.attributes]) == 3


@pytest.mark.parametrize("limit", [None, 0, -1, "120"])
def test_invalid_operation_freshness_window_cannot_confirm_activity(limit):
    data = sample()
    data["panasonic"]["operation"]["stale_s"] = limit
    _, root = parsed(data)
    assert_unknown_operation_is_hidden(root)


@pytest.mark.parametrize("which,key", [("request", "observed_at"), ("relay", "relay_observed_at"),
                                       ("received", "sg_status_observed_at")])
@pytest.mark.parametrize("stamp", [None, "stale"])
def test_each_sg_evidence_stage_expires_independently(which, key, stamp):
    data = sample()
    data["sg_boost"].update(desired_on=True, relay_on=True)
    data["panasonic"]["sg_status"] = "active"
    source = data["panasonic"] if which == "received" else data["sg_boost"]
    source[key] = time.time() - 121 if stamp == "stale" else stamp
    _, root = parsed(data)
    row = heatpump_row(root)
    assert "is-unknown" in class_names(stage(row, which))
    for independent in {"request", "relay", "received"} - {which}:
        assert "is-active" in class_names(stage(row, independent))
    assert row.attributes["data-activity"] == "active"


def test_valid_zero_watts_remains_a_measurement_in_both_views():
    data = sample()
    data["panasonic"].update(power_w=0)
    for view in ["board", "comfort"]:
        _, root = parsed(data, view)
        power = next(node for node in root.walk() if "reason-power" in class_names(node))
        assert power.children[0].text() == "0 W"
        assert "gemeten" in power.text()
        assert "Vermogen nog niet bekend" not in power.text()


@pytest.mark.parametrize("stamp", [None, "stale"])
def test_total_measurement_with_no_fresh_timestamp_is_unknown(stamp):
    data = sample()
    data["panasonic"]["power_observed_at"] = time.time() - 121 if stamp == "stale" else stamp
    _, root = parsed(data)
    power = next(node for node in heatpump_row(root).walk() if "reason-power" in class_names(node))
    assert "Vermogen nog niet bekend" in power.text()
    assert "3,7 kW" not in power.text()


@pytest.mark.parametrize("invalid_supply", ["valid", "stamp"])
def test_partial_split_preserves_fresh_supply_one_and_never_shows_a_total(invalid_supply):
    data = sample()
    p = data["panasonic"]
    p.update(power_scope="split", power_w=None, power_complete=False)
    if invalid_supply == "valid":
        p["power_supply2_valid"] = False
    else:
        p["power_supply2_observed_at"] = time.time() - 121
    _, root = parsed(data)
    power = next(node for node in heatpump_row(root).walk() if "reason-power" in class_names(node))
    assert "Vermogen nog niet bekend" in power.text()
    assert "Totaal onbekend · deelmeting onvolledig" in power.text()
    assert "Voeding 1: 3,1 kW · Voeding 2: onbekend" in power.text()
    assert "3,7 kW" not in power.text()


def test_partial_split_does_not_present_cached_total_after_a_supply_expires():
    data = sample()
    data["panasonic"].update(power_scope="split", power_complete=False,
        power_supply2_observed_at=time.time() - 121)
    _, root = parsed(data)
    power = next(node for node in heatpump_row(root).walk() if "reason-power" in class_names(node))
    assert "Vermogen nog niet bekend" in power.text()
    assert "3,7 kW" not in power.text()
    assert "Voeding 1: 3,1 kW · Voeding 2: onbekend" in power.text()


@pytest.mark.parametrize("view", ["comfort", "board"])
def test_stale_temperatures_and_zone_values_are_never_presented_as_current(view):
    data = sample()
    p = data["panasonic"]
    stale = time.time() - 121
    p.update(temperature_stamp=stale, target_stamp=stale, context_stamp=stale)
    p["zones"][0]["observed_at"] = stale
    result, root = parsed(data, view)
    rendered = text(result["initial"])
    for obsolete in ["47,3 °C", "51,2 °C", "22,7 °C", "23,4 °C"]:
        assert obsolete not in rendered
    assert "Bedrijfscontext onbekend of verouderd" in rendered
    assert "Warmtepompprogramma onbekend" in rendered
    zone = next(node for node in root.walk() if "zone" in class_names(node))
    assert "Onbekend of verouderd" in zone.text()
    assert "verwarmt" not in zone.text()


@pytest.mark.parametrize("view", ["comfort", "board"])
def test_unlinked_heatpump_has_neutral_status_and_configuration_path(view):
    data = {"mode": "solar", "devices": [], "panasonic": {}, "sg_boost": {}}
    result, root = parsed(data, view)
    rendered = text(result["initial"])
    assert "Warmtepomp — Panasonic-regeling" in rendered
    assert_unknown_operation_is_hidden(root)
    assert "Nog niet gekoppeld" not in rendered
    assert "SG-zonneboost is nog niet gekoppeld" in rendered
    if view == "board":
        assert "Instellen en details" in rendered
        assert any(node.attributes.get("data-action") == "view" and node.attributes.get("data-value") == "comfort"
                   for node in root.walk())
    else:
        assert "Zonneboost instellen" in rendered
        assert any(node.attributes.get("data-action") == "configure" and node.attributes.get("data-config-step") == "sg_boost"
                   for node in root.walk())
    assert "is-unknown" in class_names(stage(root, "relay"))
    assert "is-unknown" in class_names(stage(root, "received"))
    assert not any(node.attributes.get("data-activity") == "active" for node in root.walk())
    assert any(node.attributes.get("data-action") in {"configure", "view"}
               for node in root.walk())
    switches = [node for node in root.walk() if node.attributes.get("role") == "switch"]
    assert all("disabled" in node.attributes for node in switches)


def test_manual_external_sg_contact_is_independent_from_solarpilot_policy_and_operation():
    data = sample()
    data["panasonic"].update(operation={"state": "idle", "label": "Geen actieve warmte- of koelactie",
        "evidence": "native_action", "observed_at": time.time(), "stale_s": 120},
        sg_status="active", compressor_frequency_hz=0, compressor_running=False)
    data["sg_boost"].update(enabled=False, desired_on=False, relay_on=True,
                           manual_hold=True, state="manual_hold", owner="manual")
    result, root = parsed(data)
    row = heatpump_row(root)
    assert row.attributes["data-activity"] == "inactive"
    assert "is-inactive" in class_names(stage(row, "request"))
    assert "is-active" in class_names(stage(row, "relay"))
    assert "is-active" in class_names(stage(row, "received"))
    assert "Handmatige overname" in text(result["initial"])
    assert "uitgeschakeld" in text(result["initial"])


def test_fresh_received_sg_source_survives_unavailable_relay_and_solarpilot_snapshot():
    data = sample()
    data["sg_boost"].update(observed_at=None, relay_observed_at=None)
    data["panasonic"]["sg_status"] = "active"
    _, root = parsed(data)
    assert "is-unknown" in class_names(stage(root, "request"))
    assert "is-unknown" in class_names(stage(root, "relay"))
    assert "is-active" in class_names(stage(root, "received"))



@pytest.mark.parametrize('confirmed,remaining', [(False, 0), (True, 0), (False, None)])
def test_expired_rpc_timer_in_new_snapshot_cannot_reuse_cached_on_contact(confirmed, remaining):
    data = sample()
    data['sg_boost'].update(owner='solarpilot', desired_on=True, relay_on=True,
        relay_valid_until=time.time()-1, lease_confirmed=confirmed, lease_remaining_s=remaining)
    data['panasonic'].update(sg_status='active')
    _, root = parsed(data)
    row = heatpump_row(root)
    assert row.attributes['data-activity'] == 'active'  # independent native operation
    assert 'is-unknown' in class_names(stage(row, 'relay'))
    assert 'Open' not in stage(row, 'relay').text()  # expiry never fabricates OFF
    assert 'is-active' in class_names(stage(row, 'received'))


def test_new_actual_on_readback_without_timer_stays_visible_with_no_lease_proof():
    data = sample()
    data['sg_boost'].update(owner='solarpilot', desired_on=False, relay_on=True,
        relay_valid_until=None, lease_confirmed=False, lease_remaining_s=0, fault_code='lease_failed',
        reason='SG-contact bleef na de lokale aflooptijd aan; controleer de terugval')
    _, root = parsed(data)
    assert 'is-active' in class_names(stage(root, 'relay'))
    assert 'controleer de terugval' in root.text()
    assert 'Niet bevestigd' in root.text()
    # A fault label does not keep an expired source reading fresh.
    data['sg_boost']['relay_observed_at'] = time.time() - 121
    _, root = parsed(data)
    assert 'is-unknown' in class_names(stage(root, 'relay'))


@pytest.mark.parametrize('deadline', ['expired', 'invalid', 'future'])
def test_rpc_timer_boundary_is_independent_of_owner_policy_or_fault_label(deadline):
    data = sample()
    until = time.time()+60 if deadline == 'future' else time.time()-1 if deadline == 'expired' else 'invalid'
    data['sg_boost'].update(owner='manual', relay_on=True, lease_confirmed=False,
        lease_remaining_s=0, relay_valid_until=until, fault_code='lease_failed')
    _, root = parsed(data)
    expected = 'is-active' if deadline == 'future' else 'is-unknown'
    assert expected in class_names(stage(root, 'relay'))
