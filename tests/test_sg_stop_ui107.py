"""Render the shipped card: a hard net stop is distinct from cloud grace."""
import pytest

from test_sg_ui_platforms62 import attributes, execute, text


@pytest.mark.parametrize("view", ["comfort", "board"])
def test_hard_net_stop_is_explained_even_without_transport_journal(view):
    data = attributes(last_session={"ended_at": 1700000000,
        "reason": "Netgrens overschreden: 4200 W afname > 4000 W"})
    result = execute(data, view=view)
    rendered = text(result["initial"])
    assert "De vaste netafnamegrens stopte deze SG-aanvraag direct" in rendered
    assert "een langere wolkenbuffer voorkomt deze stop niet" in rendered
    assert "De autonoom regelende Wallbox kan op dat moment nog laden" in rendered
    assert not result["calls"]


@pytest.mark.parametrize("reason", ["Aanhoudende netafname; extra SG-aanvraag vrijgegeven",
    "Begrensde SG-sessieduur bereikt", "SG-uitgang niet bereikbaar",
    "Netgrens overschreden: onbekend"])
def test_other_stops_are_not_misrepresented_as_proven_hard_net_stop(reason):
    result = execute(attributes(last_session={"ended_at": 1700000000, "reason": reason}))
    assert reason in text(result["initial"])
    assert 'data-sg-stop-limit="net"' not in result["initial"]
    assert not result["calls"]


def test_coherence_warning_uses_current_solar_proof_and_is_escaped():
    data = attributes()
    now = data["_test_clock"]
    message = '<img src=x onerror="unexpected()">'
    data["ems"] = {"electrical_limits": {"sg_solar_valid": True, "sg_solar_observed_at": now,
        "source_valid": True, "source_observed_at": now, "source_stale_s": 120,
        "fixed_import_limit_w": 4000, "sg_protected_ev_headroom_w": 2000,
        "sg_ev_credit_reason": message}}
    result = execute(data)
    assert message in text(result["initial"])
    assert "<img src=x" not in result["initial"]
    assert "Stabiele ruimte voor SG" in text(result["initial"])
    assert "Stabiele ruimte na Wallbox" not in text(result["initial"])
    assert not result["calls"]
    stale = execute(data, now=now+121)
    assert message not in text(stale["initial"])
    assert not stale["calls"]
