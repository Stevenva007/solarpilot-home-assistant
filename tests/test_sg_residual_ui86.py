"""Current actual residual rearm and rejected HP readings stay distinct."""
import time

import pytest

from test_heatpump_ui65 import metered_sample, parsed
from test_sg_wait_ui71 import wait_fixture, wait_text


def rejected_feed(code="negative", *, raw="-8", source_watts=-8, age=0):
    data = metered_sample(0, complete=False, roles=("main", "heater"))
    now = time.time()
    p = data["panasonic"]
    p.update(power_w=None, power_kind="unknown", power_complete=False,
             power_supply1_w=None, power_supply1_valid=False, power_supply1_observed_at=None)
    p["power_activity"].update(state="unknown", active=False, observed_at=None,
                               total_w=None, complete=False)
    p["power_activity"]["supplies"][0].update(valid=False, watts=None, state="unknown", observed_at=None)
    p["power_activity"]["supplies"][1].update(valid=True, watts=0, state="off", observed_at=now)
    p["power_source_quality"] = {"supply1": {"valid": False, "watts": None,
        "rejection_reason": code, "source_reported_wall": now-age,
        "source_value": raw, "source_watts": source_watts, "source_unit": "W",
        "measured_wall": None}}
    return data


def supply(root, number):
    return next(n for n in root.walk() if n.attributes.get("data-supply-number") == str(number))


@pytest.mark.parametrize("view", ["board", "comfort"])
@pytest.mark.parametrize("code,raw,watts", [("negative", "-8", -8),
    ("out_of_range", "100001", 100001), ("invalid_value", "not-a-number", None)])
def test_fresh_rejected_numeric_reading_is_invalid_and_never_zero_or_sign_flipped(view, code, raw, watts):
    _, root = parsed(rejected_feed(code, raw=raw, source_watts=watts), view)
    first = supply(root, 1)
    assert first.attributes["data-supply-state"] == "unknown"
    assert first.attributes["data-supply-quality"] == "invalid"
    assert "Ongeldige meetwaarde" in first.text()
    assert "Geen actuele meting" not in first.text() and "0 W" not in first.text()
    assert "8 W" not in first.text() and "Actief verbruik" not in first.text()
    assert "Vermogen nog niet bekend" in root.text()
    assert "0 W" in supply(root, 2).text(), "A separate actual measured zero remains zero"


@pytest.mark.parametrize("code,raw", [("invalid_value", None), ("invalid_value", "unknown"),
    ("invalid_value", "unavailable"), ("missing", None), ("not_configured", None),
    ("restored", "-8"), ("stale", "-8"), ("invalid_timestamp", "-8")])
def test_missing_or_noncurrent_source_does_not_get_an_invalid_current_value_label(code, raw):
    _, root = parsed(rejected_feed(code, raw=raw, source_watts=None))
    first = supply(root, 1)
    assert "Geen actuele meting" in first.text()
    assert "Ongeldige meetwaarde" not in first.text() and "0 W" not in first.text()


@pytest.mark.parametrize("age", [121, -6])
def test_rejected_negative_original_report_must_itself_be_current(age):
    _, root = parsed(rejected_feed(age=age))
    first = supply(root, 1)
    assert "Geen actuele meting" in first.text() and "Ongeldige meetwaarde" not in first.text()


def test_actual_valid_zero_remains_a_measurement_not_an_error():
    data = metered_sample(0, complete=True, roles=("main", "heater"))
    _, root = parsed(data)
    assert "0 W" in supply(root, 1).text() and "Geen verbruik" in supply(root, 1).text()
    assert supply(root, 1).attributes["data-supply-quality"] == "valid"
    assert "Ongeldige meetwaarde" not in root.text()


def solar_budget(data):
    now = time.time()
    data["sg_boost"]["estimated_power_w"] = 3200
    data["ems"] = {"electrical_limits": {"source_valid": True,
        "source_observed_at": now, "source_stale_s": 120,
        "sg_solar_valid": True, "sg_solar_observed_at": now,
        "sg_residual_solar_w": 5000, "sg_eligible_solar_w": 5000, "sg_hp_solar_w": 0}}
    return data


@pytest.mark.parametrize("view", ["board", "comfort"])
def test_optional_hp_meter_note_uses_real_solar_and_extra_estimate_without_global_start_permission(view):
    _, root = parsed(solar_budget(rejected_feed()), view)
    note = next(n for n in root.walk() if "data-sg-optional-meter" in n.attributes)
    assert "actuele P1/PV-metingen" in note.text() and "3,2 kW geraamde extra opname" in note.text()
    assert "Warmtepompbijdrage blijft onbekend" in note.text()
    assert "SG-contact Open" in root.text()
    assert "Wacht op voldoende zonneoverschot" in root.text()
    assert "Ongeldige meetwaarde" in supply(root, 1).text()
    assert "0 W" not in supply(root, 1).text()
    assert "start toegestaan" not in note.text().lower() and "contact actief" not in note.text().lower()


@pytest.mark.parametrize("change", ["stale_solar", "invalid_solar", "missing_solar", "boolean_residual",
    "missing_estimate", "boolean_estimate", "negative_estimate", "stale_sg"])
def test_optional_meter_explanation_never_fabricates_current_budget_or_estimate(change):
    data = solar_budget(rejected_feed())
    limits = data["ems"]["electrical_limits"]
    if change == "stale_solar":
        limits["sg_solar_observed_at"] = time.time()-121
    elif change == "invalid_solar":
        limits["sg_solar_valid"] = False
    elif change == "missing_solar":
        limits["sg_residual_solar_w"] = None
    elif change == "boolean_residual":
        limits["sg_residual_solar_w"] = True
    elif change == "stale_sg":
        data["sg_boost"]["observed_at"] = time.time()-121
    else:
        data["sg_boost"]["estimated_power_w"] = {
            "missing_estimate": None, "boolean_estimate": True, "negative_estimate": -100}[change]
    _, root = parsed(data)
    assert not any("data-sg-optional-meter" in n.attributes for n in root.walk())


def residual_wait():
    data = wait_fixture()
    data["sg_boost"].update(reassessment_kind="fresh_residual_surplus",
        reassessment_state="confirming_fresh_residual_surplus",
        residual_reassessment_available=True, residual_reassessment_threshold_w=3200,
        real_residual_surplus_w=5000)
    return data


@pytest.mark.parametrize("view", ["board", "comfort"])
def test_residual_rearm_300s_is_distinct_from_ordinary_start_and_actual_contact(view):
    wait, details = wait_text(residual_wait(), view)
    assert "restoverschot herbevestigen" in wait
    assert "Actueel restoverschot: nog 4 min 10 s van 5 min" in wait
    assert "Restoverschot 5 kW · nodig 3,2 kW" in wait
    assert "Ingestelde startvertraging 2 min" in details and "Rusttijd gereed" in details
    assert "SG-contact Open" in details
    assert "gereed" not in wait and "contact actief" not in wait.lower()


@pytest.mark.parametrize("remaining", [0, 1])
def test_zero_residual_clock_waits_for_fresh_final_report_without_start_permission(remaining):
    data = residual_wait()
    data["sg_boost"].update(reassessment_remaining_s=remaining, observed_at=time.time()-2)
    wait, details = wait_text(data)
    assert "wacht op verse bevestiging" in wait
    assert "gereed" not in wait and "SG-contact Open" in details


@pytest.mark.parametrize("change", [{"reassessment_source_current": False},
    {"reassessment_valid_until": 1}, {"observed_at": 1},
    {"reassessment_state": "confirming_wrong_kind"}, {"reassessment_remaining_s": True}])
def test_invalid_or_expired_residual_proof_hides_countdown_and_numeric_comparison(change):
    data = residual_wait()
    data["sg_boost"].update(change)
    wait, _ = wait_text(data)
    assert "Herbevestiging onbekend" in wait
    assert "nog 4 min" not in wait and "Restoverschot 5 kW" not in wait


@pytest.mark.parametrize("value", [None, True, -1])
def test_unknown_residual_watts_never_become_a_measured_zero_in_banner(value):
    data = residual_wait()
    data["sg_boost"]["real_residual_surplus_w"] = value
    wait, _ = wait_text(data)
    assert "nog 4 min 10 s" in wait and "Restoverschot 0 W" not in wait
    assert "Restoverschot 5 kW" not in wait


def test_waiting_for_residual_path_names_evidence_without_pretending_it_is_confirmed():
    data = residual_wait()
    data["sg_boost"].update(reassessment_kind=None, reassessment_state="waiting_new_evidence",
                           reassessment_remaining_s=None)
    wait, _ = wait_text(data)
    assert "voldoende actueel restoverschot" in wait
    assert "nog 4 min" not in wait and "Restoverschot 5 kW" not in wait
