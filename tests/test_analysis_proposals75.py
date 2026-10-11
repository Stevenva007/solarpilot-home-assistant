"""Read-only research proposals must bind exact meaning to a tested release."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.analysis_implementations import logic_update_status


PROPOSALS = [
    {
        "category": "logic_update",
        "proposal_id": "sp.learning.local-investigation.v1",
        "text": "Voeg lokaal automatisch onderzoek toe voor de gekoppelde warmtepompmeting, Wallbox-sessiebron, PV-voorspelling en ontbrekende toestelmetingen. Toon per onderwerp de actuele onderzoeksstatus, meetbewijs, mogelijke verklaringen, concrete voorstellen en noodzakelijke vervolgstap. Tel alleen afzonderlijke actuele oorspronkelijke bronrapporten als extra meetbewijs en begrens de opslag. Bewaar onderzoeksgegevens zonder na een herstart actuele bronzekerheid te herstellen. Een kleine negatieve meting kan aanleiding zijn voor een nulpuntcontrole, maar bewijst geen oorzaak en wordt nooit automatisch positief of nul gemaakt. Beoordeel de warmtepompmeting rechtstreeks, onafhankelijk van de foutscore voor huishoudelijk restverbruik. Het onderzoek wijzigt geen koppelingen, instellingen, apparaten, elektrische ruimte of regelbevoegdheden; voorstellen en gegevens gaan mee in de bestaande analyse-export.",
    },
    {
        "category": "logic_update",
        "proposal_id": "sp.sg.session-evidence.v1",
        "text": "Registreer begrensd en uitsluitend uitlezend de versie, gebruikte SG-policy en meetdekking van nieuw waargenomen SG-sessies. Maak onderscheid tussen een waargenomen start en een aanvraag die bij het begin van registratie al actief is. Een meetgat, verlopen bronbewijs, herstart of gewijzigde policy mag geen complete vergelijkbare sessie opleveren. Houd oude sessies zonder passende provenance afzonderlijk van de beoordeling van huidige timers. Toon de vastgelegde aanvraagduur en beëindigingsinformatie als onderzoeksbewijs, niet als compressorlooptijd, levensduurwinst of causaal extra SG-verbruik. Doe onderbouwde vervolgstappen voor de beoordeling van minimumduur en wolkenbuffer, zonder automatisch de extra vermogensraming, netgrens, SG-timers, lease of andere beveiliging te wijzigen.",
    },
    {
        "category": "logic_update",
        "proposal_id": "sp.analysis.recommendation-kind.v1",
        "text": "Maak in de weergave van geïmporteerde adviezen expliciet onderscheid tussen softwarelogica, advies over instellingen en waarnemingen. Gebruik uitsluitend het vertrouwde softwarecatalogusbewijs om een softwarewijziging als opgenomen te tonen. Leid uit vrije adviestekst geen toegepaste instelling, herstelde bron of afgerond onderzoek af. Toon daarnaast actuele lokale onderzoeksvoortgang en concrete voorstellen met hun eigen controletijd en bronbeperkingen. Een oud adviesrapport en actuele onderzoeksgegevens blijven afzonderlijke bewijsbronnen. De weergave blijft uitsluitend uitlezen en geeft geen nieuwe bedienings- of updatebevoegdheid.",
    },
]


@pytest.mark.parametrize("row", PROPOSALS, ids=lambda row: row["proposal_id"])
def test_research_proposals_are_release_bound_and_read_only(row):
    before = deepcopy(row)
    old = logic_update_status([row], "1.0.0-beta.74")[0]
    current = logic_update_status([row], "1.0.0-beta.75")[0]
    assert old["status"] == "pending" and old["reason"] == "release_not_reached"
    assert current["status"] == "implemented" and current["reason"] == "trusted_catalog_match"
    assert current["introduced_release"] == "1.0.0-beta.75"
    assert row == before


@pytest.mark.parametrize("row", PROPOSALS, ids=lambda row: row["proposal_id"])
def test_changed_proposal_cannot_claim_the_same_implementation(row):
    changed = {**row, "text": row["text"] + " Pas automatisch de netgrens aan."}
    result = logic_update_status([changed], "1.0.0-beta.75")[0]
    assert result["status"] == "pending" and result["reason"] == "proposal_content_changed"
