"""The shipped card describes only a currently proven, bounded EV transfer."""
from copy import deepcopy

import pytest

from test_sg_ui_platforms62 import attributes, execute, text


def transfer():
    data = attributes(desired_on=True, relay_on=True, lease_confirmed=True,
        owner="solarpilot", state="boost_requested", lease_remaining_s=300)
    now = data["_test_clock"]
    data["sg_boost"]["relay_valid_until"] = now+120
    data["ems"] = {"electrical_limits": {"source_valid": True,
        "source_observed_at": now, "source_stale_s": 120,
        "sg_solar_valid": True, "sg_solar_observed_at": now,
        "fixed_import_limit_w": 4000,
        "sg_wallbox_transfer": {"state": "active", "active": True,
            "remaining_s": 240, "expires_at": now+240, "started_at": now,
            "observed_at": now, "eligible_w": 2500, "applicable": True,
            "valid_until": now+120}}}
    return data


@pytest.mark.parametrize("view", ["comfort", "board"])
def test_current_transfer_is_visible_as_a_bounded_delay_without_control_calls(view):
    data = transfer()
    before = deepcopy(data)
    result = execute(data, view=view)
    rendered = text(result["initial"])
    assert "Wallbox krijgt tijd om terug te regelen" in rendered
    # Show the real four-minute deadline while its separate source proof
    # remains current; the source expiry hides the entire message later.
    assert "Nog 4 min reactietijd voor de Wallbox" in rendered
    assert "SG mag tijdelijk 2,5 kW laadruimte benutten" in rendered
    assert "De wolkenbuffer loopt apart door" in rendered
    assert "Softwarematige netafnamegrens" in rendered
    assert not result["calls"] and data == before


def test_client_clock_decreases_the_original_deadline_and_never_extends_it():
    data = transfer()
    now = data["_test_clock"]
    result = execute(data, now=now+35)
    assert "Nog 3 min 25 s reactietijd voor de Wallbox" in text(result["initial"])
    assert not result["calls"]
    expired = execute(data, now=now+120)
    assert "data-sg-wallbox-transfer" not in expired["initial"]
    assert not expired["calls"]


@pytest.mark.parametrize("field,value", [
    ("state", "expired"), ("state", '<img src=x onerror="bad()">'),
    ("active", False), ("active", "true"), ("applicable", False),
    ("applicable", 1), ("remaining_s", True), ("remaining_s", 0),
    ("remaining_s", -1), ("remaining_s", 601), ("remaining_s", "240"),
    ("eligible_w", None), ("eligible_w", 0), ("eligible_w", "2500"), ("eligible_w", 100001),
    ("started_at", None), ("expires_at", None), ("valid_until", None),
    ("observed_at", None),
])
def test_malformed_or_unapproved_transfer_never_advertises_a_live_countdown(field, value):
    data = transfer()
    data["ems"]["electrical_limits"]["sg_wallbox_transfer"][field] = value
    result = execute(data)
    assert "data-sg-wallbox-transfer" not in result["initial"]
    assert '<img src=x' not in result["initial"]
    assert not result["calls"]


@pytest.mark.parametrize("change", ["restored", "stale", "future", "future_grid", "future_solar", "future_sg", "expired",
    "invalid_site", "invalid_solar", "lease_expired", "contact_open", "not_owned"])
def test_old_or_unconfirmed_runtime_evidence_cannot_keep_transfer_message_alive(change):
    data = transfer()
    now = data["_test_clock"]
    source = data["ems"]["electrical_limits"]
    value = source["sg_wallbox_transfer"]
    if change == "restored":
        data["restored"] = True
    elif change == "stale":
        value["observed_at"] = now-121
    elif change == "future":
        value["observed_at"] = now+1
    elif change == "future_grid":
        source["source_observed_at"] = now+1
    elif change == "future_solar":
        source["sg_solar_observed_at"] = now+1
    elif change == "future_sg":
        data["sg_boost"]["observed_at"] = now+1
    elif change == "expired":
        value["expires_at"] = now
    elif change == "invalid_site":
        source["source_valid"] = False
    elif change == "invalid_solar":
        source["sg_solar_valid"] = False
    elif change == "lease_expired":
        data["sg_boost"]["lease_remaining_s"] = 0
    elif change == "contact_open":
        data["sg_boost"]["relay_on"] = False
    else:
        data["sg_boost"]["owner"] = "external"
    result = execute(data)
    assert "data-sg-wallbox-transfer" not in result["initial"]
    assert not result["calls"]


def test_historical_net_stop_is_explained_without_claiming_the_new_exception_never_applies():
    data = transfer()
    data["sg_boost"]["last_session"] = {"ended_at": data["_test_clock"]-1200,
        "reason": "Netgrens overschreden: 4200 W afname > 4000 W"}
    result = execute(data)
    rendered = text(result["initial"])
    assert "Buiten een geldige Wallbox-overdracht" in rendered
    assert "De vaste netafnamegrens stopte deze SG-aanvraag direct" in rendered
    assert not result["calls"]
