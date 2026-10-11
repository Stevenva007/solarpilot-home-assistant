"""Generic beta74 proposals are source-free, release-bound and read-only."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.analysis_implementations import logic_update_status


PROPOSALS = [{'category': 'logic_update',
  'proposal_id': 'sp.sg.confirmed-reset-display.v1',
  'text': 'Toon bij een algemene SG-wachtstand geen nieuwe bevestigingsteller voor een lage-zonfase of native rustfase '
          'die voor die wachtstand al bevestigd is. De bestaande beoordeling en opslag van nieuwe bronrapporten '
          'blijven behouden. Een werkelijk nieuwe zonneperiode of gewijzigde native aanleiding vraagt nog steeds eigen '
          'actuele bevestiging en daarna de gewone startvertraging. De weergave blijft uitsluitend uitlezen: zij '
          'wijzigt geen wachtstand, bronbewijs, relaisopdracht, lease, minimumduur, wolkenbuffer, maximum of '
          'beveiliging.'},
 {'category': 'logic_update',
  'proposal_id': 'sp.wallbox.session-source-diagnostics.v1',
  'text': 'Onderscheid bij een onbekende effectieve Wallbox-laadsessie een ontbrekende koppeling van een reeds '
          'gekoppelde bron met verouderde, ontbrekende of niet herkende terugmelding. Noem voor een gekoppelde bron de '
          'benodigde controle van actualiteit en toestandstoewijzing, zonder opnieuw te suggereren dat er nog geen '
          'sensor gekoppeld is. Behoud de bestaande vraagidentiteit en bereken de bevindingversie met het bestaande '
          'mechanisme. De bronversheidsgrens, classificatie, voorrang en toestemming voor EV-overname blijven '
          'behouden; Full Solar als instelling bewijst geen actieve zonnesessie.'},
 {'category': 'logic_update',
  'proposal_id': 'sp.hp.inactive-scope-display.v1',
  'text': 'Beperk de weergave dat de hele warmtepomp niet actief is tot actueel bewijs met passend bereik. '
          'Uitgeschakelde ruimteacties alleen bewijzen geen rust van een onafhankelijk tankcircuit. Bij ontbrekend of '
          'ongeldig totaalvermogen en een native OFF-melding met onbekend bereik blijft de totale activiteit onbekend; '
          'bekende ruimte- en deelmetingen blijven afzonderlijk zichtbaar. Behoud het onderscheid tussen native taak, '
          'gekozen programma, afgeleide elektrische activiteit en compressorbewijs. Deze correctie geeft geen nieuwe '
          'SG- of Panasonic-bedieningsbevoegdheid en vult geen historie of leermodellen achteraf in.'}]


@pytest.mark.parametrize("proposal", PROPOSALS, ids=lambda p: p["proposal_id"])
@pytest.mark.parametrize("installed,expected", [("1.0.0-beta.73", "pending"),
                                                ("1.0.0-beta.74", "implemented")])
def test_beta74_proposal_meaning_is_exact_and_requires_installed_release(proposal, installed, expected):
    before = deepcopy(proposal)
    result = logic_update_status([proposal], installed)[0]
    assert result["status"] == expected
    assert result["introduced_release"] == "1.0.0-beta.74"
    assert proposal == before
    changed = {**proposal, "text": proposal["text"] + " Wijzig ook de bevoegdheden."}
    changed_result = logic_update_status([changed], "1.0.0-beta.74")[0]
    assert changed_result["status"] == "pending"
    assert changed_result["reason"] == "proposal_content_changed"
