"""Only the exact generic proposal and a shipped release establish implementation."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.analysis_implementations import logic_update_status, proposal_digest, IMPLEMENTED_PROPOSALS

PROPOSALS = [{'category': 'logic_update',
  'proposal_id': 'water.boiler_window_source_roles',
  'text': 'Maak de automatische water/boilervergelijking gevoelig voor opeenvolgende kleine dalingen '
          'binnen een begrensd tijdvenster. Leg bij nieuwe meetgaten de betrokken bronrol vast en laat '
          'alleen aantoonbaar relevante onderbrekingen een vergelijking blokkeren. Behoud onbekende '
          'oudere bronherkomst, echte temperatuur-/tellergaten, bronwissels, herstarts en tellerresets '
          'als grens. Tel overlappende vensters niet dubbel en blijf huishoudelijke samenloop tonen '
          'zonder water aan een toestel toe te schrijven.'},
 {'category': 'logic_update',
  'proposal_id': 'planner.pv_daylight_summary_consistency',
  'text': 'Gebruik voor de PV-waarschuwing in de plannerkwaliteit dezelfde daglicht-MAE en '
          'minimummeetdekking als de PV-vraag. Toon bij ontoereikend daglichtbewijs onbekend en laat '
          'nachtelijke nulmetingen geen positieve samenvatting veroorzaken. Dit verandert uitsluitend '
          'de uitleg; geen kalibratiefactor, reserve, plannerbeslissing of actuatorrecht.'},
 {'category': 'logic_update',
  'proposal_id': 'heatpump.learning_enablement_contract',
  'text': 'Laat het enablement-gebaseerde Aquarea-statuscontract een gekozen of ingeschakelde '
          'verwarmingsstand niet zelfstandig als bevestigde uitgevoerde warmtepomptaak aan het leerpad '
          'aanbieden. Toets de gebonden LIVE-bronnen en benodigde pomp-, meet- en contextvoorwaarden, '
          'behoud conservatieve onbekendheid bij ontbrekend bewijs en wijzig geen oude historie of '
          'stuurvoorwaarden.'}]


@pytest.mark.parametrize("proposal", PROPOSALS, ids=lambda r: r["proposal_id"])
def test_beta102_catalog_tracks_exact_meaning_without_trusting_imported_claims(proposal):
    before = deepcopy(proposal)
    row = {**proposal, "evidence": ["Mutable generic evidence"], "status": "implemented"}
    catalog = IMPLEMENTED_PROPOSALS[proposal["proposal_id"]]
    assert proposal_digest(row) == catalog["proposal_sha256"]
    assert logic_update_status([row], release="1.0.0-beta.101")[0]["reason"] == "release_not_reached"
    assert logic_update_status([row], release="1.0.0-beta.102")[0]["status"] == "implemented"
    assert logic_update_status([row], release="1.0.0-beta.103")[0]["status"] == "implemented"
    changed = {**row, "text": row["text"] + " Changed scope."}
    assert logic_update_status([changed], release="1.0.0-beta.102")[0]["reason"] == "proposal_content_changed"
    assert logic_update_status([row], release="unknown")[0]["status"] == "pending"
    assert proposal == before
