"""Cloud-import policy is implemented only by its exact public release catalog."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.analysis_implementations import logic_update_status


@pytest.mark.parametrize("installed,status", [("1.0.0-beta.72", "pending"), ("1.0.0-beta.73", "implemented")])
def test_beta73_cloud_proposal_binds_threshold_delay_authority_and_release(installed, status):
    row = {'category': 'logic_update', 'proposal_id': 'sp.sg.cloud-import-buffer.v1', 'text': 'Gebruik voor de zachte SG-importstop een instelbare netafnamegrens van 600 W en vijf aaneengesloten minuten als standaard. Netafname op of onder de grens wist de lopende importteller. De teller loopt tijdens de minimale SG-aanvraagduur door, zodat de minimumduur en wolkenbuffer elkaar overlappen. Vernieuw de korte lokale aflooptimer ook na de minimumduur zolang de lopende wolkenbuffer en de bevestigde eigen aanvraag actueel geldig zijn; controleer dit opnieuw vóór iedere relaisopdracht. Verlopen contact-, bron- of leasebewijs geeft geen nieuwe inschakelbevoegdheid. Houd de drempel voor het bevestigen van een nieuwe zonneperiode afzonderlijk en behoud de vorige waarde. Zet alleen de oude standaardcombinatie van 300 W en één minuut om naar de nieuwe standaard; behoud afwijkende instellingen. Toon de effectieve importgrens, wachttijd en actuele resterende buffer. De bestaande maximale sessieduur en alle elektrische, bron-, voorrangs-, native-, handmatige en foutbeveiligingen houden voorrang. Panasonic behoudt zijn eigen regeling en instellingen.'}
    before = deepcopy(row)
    result = logic_update_status([row], installed)[0]
    assert result["status"] == status
    assert result["introduced_release"] == "1.0.0-beta.73"
    assert row == before
    changed = {**row, "text": row["text"].replace("600 W", "onbegrensde import")}
    assert logic_update_status([changed], "1.0.0-beta.73")[0]["status"] == "pending"
