"""Execute read-only SG minimum-duration presentation with fictitious evidence."""
import time

import pytest

from test_overview_details60 import Markup
from test_sg_ui_platforms62 import attributes, execute


def minimum_fixture():
    now = time.time()
    return attributes(profile='general', state='active', desired_on=True, relay_on=True,
                      owner='solarpilot', lease_confirmed=True, lease_remaining_s=180,
                      remaining_s=1800, relay_valid_until=now + 180,
                      min_session_s=1200, effective_min_session_s=1200,
                      minimum_limited_by_max=False, minimum_remaining_s=1120,
                      minimum_active=True, minimum_import_hold=False,
                      minimum_valid_until=now + 120)


def render_minimum(data, view='comfort'):
    result = execute(data, view=view)
    root = Markup(result['initial']).root
    minimum = [n for n in root.walk() if 'data-sg-minimum' in n.attributes]
    assert not result['calls']
    return minimum, root.text()


@pytest.mark.parametrize('view', ['board', 'comfort'])
def test_active_owned_sg_minimum_does_not_claim_native_compressor_runtime(view):
    minimum, details = render_minimum(minimum_fixture(), view)
    assert len(minimum) == 1
    text = minimum[0].text()
    assert 'Minimum SG-aanvraagduur · 20 min' in text
    assert 'Nog 18 min 40 s · alleen de SG-aanvraag' in text
    assert 'Panasonic bepaalt zelf de compressorlooptijd' in text
    assert 'beveiligingen kunnen SG eerder vrijgeven' in text
    assert 'Na het minimum kan SG doorgaan zolang de normale voorwaarden kloppen' in text
    assert 'Ingesteld SG-minimum 20 min' in details
    assert 'Compressor draait' not in details


@pytest.mark.parametrize('change', [
    {'minimum_remaining_s': None}, {'minimum_remaining_s': -1},
    {'minimum_remaining_s': True}, {'minimum_remaining_s': 1201},
    {'minimum_active': False}, {'minimum_valid_until': None},
    {'minimum_valid_until': time.time() - 1}, {'observed_at': time.time() - 121},
    {'relay_confirmed': False}, {'relay_on': False}, {'lease_confirmed': False},
    {'lease_remaining_s': 0}, {'owner': 'manual'},
    {'relay_valid_until': time.time() - 1}, {'effective_min_session_s': None},
])
def test_missing_stale_expired_or_unconfirmed_minimum_is_unknown(change):
    data = minimum_fixture()
    data['sg_boost'].update(change)
    minimum, _ = render_minimum(data)
    assert 'Resterende minimumduur onbekend' in minimum[0].text()
    assert 'Nog 18 min' not in minimum[0].text()


@pytest.mark.parametrize('remaining,elapsed', [(0, 0), (1, 2)])
def test_elapsed_minimum_is_not_stop_authority(remaining, elapsed):
    data = minimum_fixture()
    data['sg_boost'].update(minimum_remaining_s=remaining, observed_at=time.time() - elapsed)
    text = render_minimum(data)[0][0].text()
    assert 'Minimum verstreken · actuele regeling bepaalt het vrijgeven' in text
    assert 'gereed' not in text and 'wordt uitgeschakeld' not in text


def test_effective_existing_hard_max_is_explicit_and_not_changed():
    data = minimum_fixture()
    data['sg_boost'].update(effective_min_session_s=900, minimum_limited_by_max=True,
                           minimum_remaining_s=800)
    minimum, details = render_minimum(data)
    assert 'Minimum SG-aanvraagduur · 15 min' in minimum[0].text()
    assert 'bestaande maximale sessieduur begrenst het minimum' in minimum[0].text()
    assert 'Ingesteld SG-minimum 20 min' in details and 'Effectief SG-minimum 15 min' in details


@pytest.mark.parametrize('remaining,expected', [
    (300, 'Nog 5 min'),
    (301, 'Resterende minimumduur onbekend'),
])
def test_fractional_ack_delay_accepts_only_backend_ceiling(remaining, expected):
    data = minimum_fixture()
    data['sg_boost'].update(effective_min_session_s=299.3, minimum_limited_by_max=True,
                           minimum_remaining_s=remaining)
    minimum, _ = render_minimum(data)
    assert expected in minimum[0].text()


def test_soft_import_hold_is_distinct_and_hidden_without_valid_positive_minimum():
    data = minimum_fixture()
    data['sg_boost']['minimum_import_hold'] = True
    assert 'Tijdelijke netafname' in render_minimum(data)[0][0].text()
    data['sg_boost']['minimum_remaining_s'] = None
    assert 'Tijdelijke netafname' not in render_minimum(data)[0][0].text()


def test_no_active_request_has_no_active_minimum_banner():
    data = minimum_fixture()
    data['sg_boost']['desired_on'] = False
    assert render_minimum(data)[0] == []
