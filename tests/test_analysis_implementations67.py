"""Only shipped catalog entries can establish an implemented logic proposal."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot import analysis_implementations as implementations


def proposal(identifier="synthetic-source-clock"):
    return {"category": "logic_update", "proposal_id": identifier, "text": "Controleer de eigen bronklok."}


def test_shipped_catalog_starts_empty_without_claiming_any_uploaded_implementation():
    assert implementations.IMPLEMENTED_PROPOSALS == {}
    report = proposal()
    report.update(status="implemented", introduced_release="1.0.0-beta.1", code="switch.turn_on")
    before = deepcopy(report)
    assert implementations.logic_update_status([report], "1.0.0-beta.67") == [{
        "proposal_id": "synthetic-source-clock", "status": "untracked", "introduced_release": None,
        "summary": report["text"], "installed_release": "1.0.0-beta.67", "reason": "not_in_catalog", "recommendation_index": 0}]
    assert report == before


@pytest.mark.parametrize("introduced,installed,status", [
    ("1.0.0-beta.9", "1.0.0-beta.67", "implemented"),
    ("1.0.0-beta.67", "1.0.0-beta.9", "pending"),
    ("1.0.0-beta.67", "1.0.0-beta.67", "implemented"),
    ("1.0.0-beta.100", "1.0.0-beta.99", "pending"),
    ("1.0.0-beta.99", "1.0.0-beta.100", "implemented"),
    ("1.0.0-beta.67", "1.0.0", "implemented"),
    ("1.0.0", "1.0.0-beta.100", "pending"),
    ("1.0.0-beta.67", "1.0.0-beta.66", "pending"),
    ("1.0.0-beta.67", "1.0.1-beta.100", "implemented"),
    ("1.0.0-beta.67", "1.1.0", "implemented"),
    ("1.0.0-beta.67", "2.0.0", "implemented"),
    ("1.0.0-beta.67", "unknown", "pending"),
])
def test_beta_sequence_and_core_versions_are_numeric_with_stable_after_its_betas(monkeypatch, introduced, installed, status):
    monkeypatch.setattr(implementations, "IMPLEMENTED_PROPOSALS", {
        "synthetic-source-clock": {"introduced_release": introduced, "title": "Generieke bronklokcorrectie",
                                   "proposal_sha256": implementations.proposal_digest(proposal())}})
    result = implementations.logic_update_status([proposal()], installed)
    assert result[0]["status"] == status
    assert result[0]["introduced_release"] == introduced
    assert result[0]["installed_release"] == installed


@pytest.mark.parametrize("introduced", [None, "", "1.0.0-beta.x", "1.0.0-beta.01", "01.0.0-beta.1"])
def test_malformed_catalog_release_never_establishes_implementation(monkeypatch, introduced):
    monkeypatch.setattr(implementations, "IMPLEMENTED_PROPOSALS", {
        "synthetic-source-clock": {"introduced_release": introduced, "title": "Bronklok",
                                   "proposal_sha256": implementations.proposal_digest(proposal())}})
    assert implementations.logic_update_status([proposal()], "1.0.0-beta.67")[0]["status"] == "untracked"


def test_missing_identifier_is_untracked_and_other_advice_categories_are_omitted():
    row = proposal()
    row.pop("proposal_id")
    result = implementations.logic_update_status({"recommendations": [row, {"category": "solarpilot_setting", "text": "Advies"}]})
    assert len(result) == 1 and result[0]["proposal_id"] is None
    assert result[0]["status"] == "untracked" and result[0]["introduced_release"] is None


def test_reused_proposal_id_with_changed_meaning_cannot_claim_implementation(monkeypatch):
    row = proposal()
    digest = implementations.proposal_digest(row)
    monkeypatch.setattr(implementations, "IMPLEMENTED_PROPOSALS", {
        row["proposal_id"]: {"introduced_release": "1.0.0-beta.67", "title": "Generieke bronklokcorrectie",
                             "proposal_sha256": digest}})
    assert implementations.logic_update_status([row], "1.1.0")[0]["status"] == "implemented"
    row["text"] = "Ander regelgedrag met hetzelfde voorstel-ID."
    result = implementations.logic_update_status([row], "1.1.0")[0]
    assert result["status"] == "pending" and result["reason"] == "proposal_content_changed"


def test_proposal_fingerprint_ignores_uploaded_status_and_evidence_but_binds_the_exact_text():
    row = proposal()
    digest = implementations.proposal_digest(row)
    row.update(status="implemented", evidence=["Fictieve privémeting"], confidence="high")
    assert implementations.proposal_digest(row) == digest
    row["text"] += " "
    assert implementations.proposal_digest(row) != digest


@pytest.mark.parametrize("patch", [{"proposal_sha256": "a"}, {"title": ""}, {"private_report": "onjuist"}])
def test_invalid_or_extra_catalog_fields_never_establish_implementation(monkeypatch, patch):
    row = proposal()
    catalog = {"introduced_release": "1.0.0-beta.67", "title": "Generiek voorstel", "proposal_sha256": implementations.proposal_digest(row)}
    catalog.update(patch)
    monkeypatch.setattr(implementations, "IMPLEMENTED_PROPOSALS", {row["proposal_id"]: catalog})
    result = implementations.logic_update_status([row], "1.1.0")[0]
    assert result["status"] == "untracked" and result["reason"] == "invalid_catalog"


def test_repeated_ids_with_different_text_keep_their_original_recommendation_association(monkeypatch):
    row = proposal()
    changed = {**row, "text": "Verschillend voorstel ondanks hetzelfde ID."}
    monkeypatch.setattr(implementations, "IMPLEMENTED_PROPOSALS", {
        row["proposal_id"]: {"introduced_release": "1.0.0-beta.67", "title": "Generiek voorstel",
                             "proposal_sha256": implementations.proposal_digest(row)}})
    result = implementations.logic_update_status([{"category": "observation"}, row, changed], "1.1.0")
    assert [item["recommendation_index"] for item in result] == [1, 2]
    assert [item["status"] for item in result] == ["implemented", "pending"]
    assert result[1]["reason"] == "proposal_content_changed"
