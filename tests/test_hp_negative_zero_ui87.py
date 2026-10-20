"""Backend-approved negative-as-zero preserves raw evidence, not stale authority."""
import re

import pytest

from test_heatpump_ui65 import metered_sample, parsed
from test_sg_residual_ui86 import rejected_feed, supply


def normalized_feed(*, unit="W", raw="-12", raw_watts=-12):
    data = metered_sample(0, complete=True, roles=("main", "heater"))
    stamp = data["panasonic"]["power_observed_at"]
    data["panasonic"]["power_source_quality"] = {"supply1": {
        "valid": True, "watts": 0, "source_watts": raw_watts, "source_value": raw,
        "source_unit": unit, "source_reported_wall": stamp, "source_timestamp_kind": "last_reported",
        "measured_wall": stamp, "normalized": True, "normalization_reason": "negative_as_zero",
        "rejection_reason": None, "reason": ""}}
    return data


def details(root):
    return next(n for n in root.walk() if "data-heatpump-provenance" in n.attributes)


@pytest.mark.parametrize("view", ["board", "comfort"])
@pytest.mark.parametrize("unit,raw,raw_watts", [("W", "-12", -12), ("kW", "-0.012", -12)])
def test_valid_normalized_zero_appears_as_zero_and_raw_source_stays_in_details(view, unit, raw, raw_watts):
    _, root = parsed(normalized_feed(unit=unit, raw=raw, raw_watts=raw_watts), view)
    first = supply(root, 1)
    assert "0 W" in first.text() and "Geen verbruik" in first.text()
    assert "Ongeldige meetwaarde" not in first.text() and "Geen actuele meting" not in first.text()
    assert first.attributes["data-supply-quality"] == "valid"
    assert first.attributes["data-supply-state"] == "off"
    assert "12 W" not in first.text(), "No automatic sign flip"
    proof = details(root).text()
    assert f"Bron {raw} {unit} → toegepast 0 W" in proof
    assert "Voeding 1: normalisatie" in proof and "laatste bronrapport" in proof
    assert "bron niet actueel" not in proof


def test_normalization_does_not_refresh_its_original_source_time():
    data = normalized_feed()
    p = data["panasonic"]
    # Whole seconds survive the Node milliseconds round-trip exactly.
    # Fractional wall time can otherwise floor 120.99999976 to 120.
    data["_test_clock"] = int(data["_test_clock"])
    old = data["_test_clock"]-121
    p.update(power_observed_at=old, power_supply1_observed_at=old, power_supply2_observed_at=old)
    p["power_activity"].update(observed_at=old)
    for row in p["power_activity"]["supplies"]:
        row["observed_at"] = old
    p["power_source_quality"]["supply1"].update(source_reported_wall=old, measured_wall=old)
    _, root = parsed(data)
    assert "Geen actuele meting" in supply(root, 1).text() and "0 W" not in supply(root, 1).text()
    assert "Vermogen nog niet bekend" in root.text()
    assert "Bron -12 W → toegepast 0 W · bron niet actueel" in details(root).text()
    age = re.search(r"(\d+) s geleden · last_reported", details(root).text())
    assert age and int(age.group(1)) == 121


@pytest.mark.parametrize("code,raw", [("missing", None), ("invalid_value", "unavailable"), ("stale", "-12")])
def test_rejected_missing_or_stale_values_remain_unknown_not_normalized_zero(code, raw):
    data = rejected_feed(code, raw=raw, source_watts=None)
    quality = data["panasonic"]["power_source_quality"]["supply1"]
    quality.update(normalized=False, normalization_reason=None)
    _, root = parsed(data)
    assert "Geen actuele meting" in supply(root, 1).text() and "0 W" not in supply(root, 1).text()
    assert "→ toegepast 0 W" not in details(root).text()


@pytest.mark.parametrize("change", [
    {"normalized": False}, {"normalized": "true"}, {"normalization_reason": "other"},
    {"source_watts": None}, {"source_watts": True}, {"source_watts": -100001},
    {"source_unit": "V"}, {"source_value": None}, {"watts": True}, {"valid": False},
])
def test_unproved_normalization_marker_cannot_fabricate_raw_to_applied_evidence(change):
    data = normalized_feed()
    data["panasonic"]["power_source_quality"]["supply1"].update(change)
    _, root = parsed(data)
    assert "→ toegepast 0 W" not in details(root).text()


def test_real_measured_zero_has_no_invented_normalization():
    data = normalized_feed(raw="0", raw_watts=0)
    data["panasonic"]["power_source_quality"]["supply1"].update(normalized=False, normalization_reason=None)
    _, root = parsed(data)
    assert "0 W" in supply(root, 1).text() and "Geen verbruik" in supply(root, 1).text()
    assert "Voeding 1: normalisatie" not in details(root).text()


def test_legacy_rejected_negative_snapshot_is_not_rewritten_by_the_frontend():
    _, root = parsed(rejected_feed())
    assert "Ongeldige meetwaarde" in supply(root, 1).text() and "0 W" not in supply(root, 1).text()
    assert "→ toegepast 0 W" not in details(root).text()


def test_original_raw_value_is_escaped_in_normalization_details():
    payload = '<img src=x onerror="window.bad=true">'
    _, root = parsed(normalized_feed(raw=payload))
    proof = details(root)
    assert payload in proof.text() and "→ toegepast 0 W" in proof.text()
    assert not any(n.tag == "img" for n in proof.walk())
