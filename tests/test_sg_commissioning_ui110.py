"""Firmware metadata is advisory; the shipped card explains automatic verification."""
from copy import deepcopy

import pytest

from test_sg_ui_platforms62 import attributes, execute, text


def blocked():
    return attributes(fault_code="firmware_changed", reason="Bevestig de SG-koppeling",
        commissioning_confirmed=False, watchdog_confirmed=False,
        commissioning_diagnostic={"schema": 1, "evidence_available": True,
            "changed_fields": ["version", "firmware_id"], "firmware_only": True,
            "automatic": True, "verification": "verified",
            "previous_version": "2.0.1", "observed_version": "2.0.2"})


@pytest.mark.parametrize("view", ["comfort", "board"])
def test_verified_firmware_update_is_advisory_without_manual_reconfirmation(view):
    data = blocked()
    before = deepcopy(data)
    result = execute(data, view=view)
    rendered = text(result["initial"])
    assert "Firmwarewijziging automatisch gecontroleerd" in rendered
    assert "firmwarewijziging blokkeert SG niet" in rendered
    assert "firmwareversie, firmwarebuild" in rendered
    assert "2.0.1 → 2.0.2" in rendered
    assert "vraagt geen handmatige herbevestiging" in rendered
    assert "SG blijft uit" not in rendered
    assert data == before and not result["calls"]


def test_old_fault_does_not_invent_a_firmware_change_record():
    data = blocked()
    data["sg_boost"].pop("commissioning_diagnostic")
    result = execute(data)
    assert "in deze oudere registratie niet vastgelegd" in text(result["initial"])
    assert "2.0.1" not in result["initial"]
    assert not result["calls"]


def test_stale_snapshot_does_not_claim_a_current_commissioning_block():
    data = blocked()
    result = execute(data, now=data["_test_clock"]+121)
    assert "data-sg-commissioning-change" not in result["initial"]
    assert "Firmwarewijziging automatisch gecontroleerd" not in text(result["initial"])
    assert not result["calls"]


def test_diagnostic_fields_are_allowlisted_and_firmware_text_is_escaped():
    data = blocked()
    evidence = data["sg_boost"]["commissioning_diagnostic"]
    evidence.update(changed_fields=["version", "version", "secret-device-identifier", "__proto__"],
        observed_version='<img src=x onerror="unexpected()">')
    result = execute(data)
    rendered = text(result["initial"])
    assert "Gewijzigde velden: firmwareversie." in rendered
    assert "secret-device-identifier" not in rendered and "__proto__" not in rendered
    assert "<img src=x" not in result["initial"]
    assert not result["calls"]


@pytest.mark.parametrize("diagnostic", [None, {}, [], {"schema": 2},
    {"schema": 1, "evidence_available": False, "changed_fields": ["version"],
        "previous_version": "2.0.1", "observed_version": "2.0.2"}])
def test_missing_unrecognized_or_unproven_detail_does_not_claim_verified_firmware(diagnostic):
    data = blocked()
    data["sg_boost"]["commissioning_diagnostic"] = diagnostic
    result = execute(data)
    assert "Automatische hercontrole van SG-uitgang" in text(result["initial"])
    assert "in deze oudere registratie niet vastgelegd" in text(result["initial"])
    assert "2.0.1 → 2.0.2" not in text(result["initial"])
    assert not result["calls"]


def test_real_binding_change_is_not_presented_as_a_verified_firmware_update():
    data = blocked()
    data["sg_boost"]["commissioning_diagnostic"].update(
        firmware_only=False, automatic=False, verification="blocked", changed_fields=["device_id"])
    result = execute(data)
    rendered = text(result["initial"])
    assert "SG-koppeling controleren" in rendered
    assert "De SG-uitgang wijkt af" in rendered
    assert "Firmwarewijziging automatisch gecontroleerd" not in rendered
    assert not result["calls"]


def test_successful_firmware_notice_remains_visible_without_a_fault():
    data = blocked()
    data["sg_boost"].update(fault_code="", commissioning_confirmed=True, watchdog_confirmed=True)
    result = execute(data)
    assert "Firmwarewijziging automatisch gecontroleerd" in text(result["initial"])
    assert not result["calls"]
