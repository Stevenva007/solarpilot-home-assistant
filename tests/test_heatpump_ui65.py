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


def test_native_operation_gets_active_article_while_sg_is_open():
    _, root = parsed(sample())
    row = heatpump_row(root)
    assert row.attributes["data-activity"] == "active"
    assert "is-active" in class_names(row)
    assert "is-inactive" in class_names(stage(row, "request"))
    assert "is-inactive" in class_names(stage(row, "relay"))
    assert "is-inactive" in class_names(stage(row, "received"))
    assert "Warmtepomp in werking" in row.text()


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


def test_high_measured_watts_without_operation_does_not_claim_heat_production():
    data = sample()
    data["panasonic"].pop("operation")
    data["panasonic"]["power_w"] = 9000
    _, root = parsed(data)
    row = heatpump_row(root)
    assert row.attributes["data-activity"] == "unknown"
    assert "9 kW" in row.text()
    assert "Werking onbekend" in row.text()


@pytest.mark.parametrize("stamp", [None, "not-a-timestamp", 0, -10, "stale", "future"])
def test_missing_stale_or_invalid_operation_timestamp_is_unknown(stamp):
    data = sample()
    if stamp == "stale":
        stamp = time.time() - 121
    elif stamp == "future":
        stamp = time.time() + 60
    data["panasonic"]["operation"]["observed_at"] = stamp
    _, root = parsed(data)
    row = heatpump_row(root)
    assert row.attributes["data-activity"] == "unknown"
    assert "Werking onbekend" in row.text()


@pytest.mark.parametrize("limit", [None, 0, -1, "120"])
def test_invalid_operation_freshness_window_cannot_confirm_activity(limit):
    data = sample()
    data["panasonic"]["operation"]["stale_s"] = limit
    _, root = parsed(data)
    assert heatpump_row(root).attributes["data-activity"] == "unknown"


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
    assert "Nog niet gekoppeld" in rendered
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
