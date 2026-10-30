"""Fifteen-minute policy is displayed separately from the short local lease."""
from copy import deepcopy

import pytest

from test_sg_continuous_ui111 import NOW, deficit
from test_sg_ui_platforms62 import execute, text


@pytest.mark.parametrize("view", ["comfort", "board"])
def test_fifteen_minute_buffers_count_down_without_extending_contact_evidence(view):
    data = deficit(stop_delay_s=900, joint_solar_deficit_remaining_s=850,
        cloud_active=True, cloud_import_hold=True, cloud_remaining_s=850,
        cloud_valid_until=NOW+120)
    before = deepcopy(data)
    result = execute(data, view=view, now=NOW+10)
    rendered = text(result["initial"])
    assert "Wolkenbuffer · 600 W / 15 min" in rendered
    assert "Netafname boven 600 W · nog 14 min" in rendered
    assert "Te weinig bruikbare zonnestroom · nog 14 min wolkenbuffer" in rendered
    assert "Bevestigde lokale toestemming nog 4m" in rendered
    assert data == before and not result["calls"]


def test_long_buffer_never_outlives_its_original_source_proof_on_screen():
    data = deficit(stop_delay_s=900, joint_solar_deficit_remaining_s=850)
    result = execute(data, now=NOW+31)
    assert "Resterende zonnebuffer onbekend" in text(result["initial"])
    assert "data-sg-continuous" not in result["initial"]
    assert not result["calls"]
