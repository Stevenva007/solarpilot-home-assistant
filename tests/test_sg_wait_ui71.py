"""Execute shipped read-only SG wait presentation; fiction only."""
import time

import pytest

from test_overview_details60 import Markup
from test_sg_ui_platforms62 import attributes, execute


def wait_fixture(**changes):
    now = time.time()
    return attributes(profile='general', completion_hold=True, state='completion_hold',
                      start_required_s=120, rest_remaining_s=0,
                      reassessment_state='confirming_new_solar_period',
                      reassessment_kind='new_solar_period', reassessment_remaining_s=250,
                      reassessment_required_s=300, reassessment_reports=2,
                      reassessment_source_current=True, reassessment_final_report_required=False,
                      reassessment_valid_until=now + 120, **changes)


def wait_text(data, view='comfort'):
    rendered = execute(data, view=view)
    root = Markup(rendered['initial']).root
    wait = next(n for n in root.walk() if 'data-sg-wait' in n.attributes)
    assert not rendered['calls']
    return wait.text(), root.text()


@pytest.mark.parametrize('view', ['board', 'comfort'])
def test_rearm300_and_ordinary120_are_distinct_even_when_rest_ready(view):
    wait, details = wait_text(wait_fixture(), view)
    assert 'herbevestiging' in wait
    assert 'Nieuw zonneoverschot: nog 4 min 10 s van 5 min' in wait
    assert 'Ingestelde startvertraging 2 min' in details
    assert 'Rusttijd gereed' in details
    assert 'gereed' not in wait


@pytest.mark.parametrize('kind,label', [
    ('new_solar_period', 'Nieuw zonneoverschot'),
    ('fresh_native_context', 'Gewijzigde Panasonic-context'),
    ('solar_reset', 'Zonneperiode resetten'),
    ('native_reset', 'Panasonic-context resetten'),
])
def test_actual_reassessment_kind_is_named(kind, label):
    data = wait_fixture()
    data['sg_boost'].update(reassessment_kind=kind, reassessment_state='confirming_' + kind)
    assert label in wait_text(data)[0]


@pytest.mark.parametrize('elapsed', [False, True])
def test_zero_waits_for_fresh_final_confirmation_and_never_becomes_ready(elapsed):
    data = wait_fixture()
    data['sg_boost'].update(reassessment_remaining_s=1 if elapsed else 0,
                           observed_at=time.time() - 2 if elapsed else time.time())
    wait, _ = wait_text(data)
    assert 'wacht op verse bevestiging' in wait
    assert 'gereed' not in wait and 'starten' not in wait


@pytest.mark.parametrize('change', [
    {'reassessment_source_current': False},
    {'reassessment_remaining_s': None},
    {'reassessment_remaining_s': -1},
    {'reassessment_remaining_s': True},
    {'reassessment_remaining_s': 301},
    {'reassessment_kind': 'unsupported'},
    {'reassessment_state': 'confirming_wrong_kind'},
    {'reassessment_valid_until': None},
    {'reassessment_valid_until': time.time() - 1},
    {'observed_at': time.time() - 121},
])
def test_missing_invalid_and_source_expired_candidates_are_unknown(change):
    data = wait_fixture()
    data['sg_boost'].update(change)
    wait, _ = wait_text(data)
    assert 'Herbevestiging onbekend' in wait and 'nog 4 min' not in wait


@pytest.mark.parametrize('remaining', [77, 0, None])
def test_ordinary_start_wait_uses_configured_delay_without_new_final_report_rule(remaining):
    data = wait_fixture()
    data['sg_boost'].update(completion_hold=False, state='waiting_surplus',
                           start_remaining_s=remaining, start_valid_until=time.time() + 120)
    wait, _ = wait_text(data)
    assert 'SG-startvertraging' in wait
    assert ('nog 1 min 17 s van 2 min' if remaining == 77 else
            'wacht op actuele beoordeling' if remaining == 0 else
            'startvertraging onbekend') in wait
    assert 'verse bevestiging' not in wait and 'gereed' not in wait
