"""The display correction is only trusted at its exact release and meaning."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.analysis_implementations import (
    IMPLEMENTED_PROPOSALS, logic_update_status, proposal_digest,
)


PROPOSAL = {
    "category": "logic_update",
    "proposal_id": "heatpump.display_operation_contract_alignment",
    "text": "Laat de actuele warmtepompkaart dezelfde twee reeds ondersteunde Aquarea-broncontracten accepteren als de backend. Toon een met passende oorspronkelijke actuele brongegevens afgeleide verwarmings-, koel- of boilertaak als afgeleid en houd de bronbenaming bij de werkelijke contractsemantiek. Behoud alle controles op geladen provider, contractbetekenis, binding, bronactualiteit, cache, conflict en meting. Verleen geen leer- of regelrecht en herschrijf geen historie.",
}


@pytest.mark.parametrize("release,status,reason", [
    ("1.0.0-beta.102", "pending", "release_not_reached"),
    ("1.0.0-beta.103", "implemented", "trusted_catalog_match"),
    ("1.0.0-beta.104", "implemented", "trusted_catalog_match"),
    ("unknown", "pending", "release_not_recognized"),
])
def test_display_proposal_needs_exact_trusted_meaning_and_loaded_release(release, status, reason):
    row = {**PROPOSAL, "evidence": ["Mutable generic evidence"], "status": "implemented"}
    before = deepcopy(row)
    catalog = IMPLEMENTED_PROPOSALS[PROPOSAL["proposal_id"]]
    assert catalog["introduced_release"] == "1.0.0-beta.103"
    assert proposal_digest(row) == catalog["proposal_sha256"]
    actual = logic_update_status([row], release=release)[0]
    assert (actual["status"], actual["reason"]) == (status, reason)
    assert row == before


def test_imported_claim_cannot_expand_the_display_proposal_to_control():
    changed = {**PROPOSAL, "text": PROPOSAL["text"] + " Geef ook regeltoestemming."}
    actual = logic_update_status([changed], release="1.0.0-beta.103")[0]
    assert actual["status"] == "pending"
    assert actual["reason"] == "proposal_content_changed"
