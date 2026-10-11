"""Once-confirmed reset presentation never creates controller authority."""
import time

import pytest

from test_sg_wait_ui71 import wait_fixture, wait_text


def confirmed_reset_fixture(**changes):
    data = wait_fixture()
    data['sg_boost'].update(reassessment_state='waiting_new_evidence',
        reassessment_kind=None, reassessment_remaining_s=None, reassessment_valid_until=None,
        reassessment_reports=0, reassessment_final_report_required=False)
    data['sg_boost'].update(changes)
    return data


@pytest.mark.parametrize('view', ['board', 'comfort'])
@pytest.mark.parametrize('reset_kind', ['solar_reset', 'native_reset'])
def test_confirmed_reset_keeps_waiting_without_restarting_a_five_minute_timer(view, reset_kind):
    for _report in range(3):
        # The backend may still receive later low/normal reports in this hold.
        # Its once-confirmed display contract has no new reset candidate.
        wait, details = wait_text(confirmed_reset_fixture(), view)
        assert 'Wacht op nieuwe zonneperiode of gewijzigde Panasonic-context' in wait
        assert 'resetten' not in wait and 'nog ' not in wait and 'gereed' not in wait
        assert 'Ingestelde startvertraging 2 min' in details
        assert 'SG-startvertraging' not in wait
    # Contradictory leftover reset fields cannot override waiting_new_evidence.
    wait, _ = wait_text(confirmed_reset_fixture(reassessment_kind=reset_kind,
        reassessment_remaining_s=250, reassessment_valid_until=time.time() + 120), view)
    assert 'Wacht op nieuwe zonneperiode' in wait and 'nog 4 min' not in wait


@pytest.mark.parametrize('view', ['board', 'comfort'])
@pytest.mark.parametrize('kind,label', [
    ('new_solar_period', 'Nieuw zonneoverschot'),
    ('fresh_native_context', 'Gewijzigde Panasonic-context'),
])
def test_new_episode_then_ordinary_start_keep_their_separate_evidence_and_delays(view, kind, label):
    waiting, _ = wait_text(confirmed_reset_fixture(), view)
    assert 'Wacht op nieuwe zonneperiode' in waiting
    data = wait_fixture()
    data['sg_boost'].update(reassessment_kind=kind, reassessment_state='confirming_' + kind)
    wait, details = wait_text(data, view)
    assert f'{label}: nog 4 min 10 s van 5 min' in wait
    assert 'Ingestelde startvertraging 2 min' in details
    data['sg_boost'].update(reassessment_remaining_s=0,
                           reassessment_final_report_required=True)
    assert 'wacht op verse bevestiging' in wait_text(data, view)[0]
    data['sg_boost'].update(completion_hold=False, state='waiting_surplus',
                           start_remaining_s=77, start_valid_until=time.time() + 120)
    wait, _ = wait_text(data, view)
    assert 'SG-startvertraging' in wait and 'nog 1 min 17 s van 2 min' in wait
    assert '5 min' not in wait and 'verse bevestiging' not in wait


@pytest.mark.parametrize('change', [
    {'reassessment_valid_until': lambda: time.time() - 1},
    {'reassessment_valid_until': None},
    {'reassessment_source_current': False},
    {'observed_at': lambda: time.time() - 121},
    {'observed_at': lambda: time.time() + 60},
    {'reassessment_remaining_s': True},
    {'reassessment_remaining_s': 301},
])
@pytest.mark.parametrize('kind', ['new_solar_period', 'fresh_native_context'])
def test_invalid_or_expired_new_episode_never_recreates_live_wait_authority(kind, change):
    data = wait_fixture()
    data['sg_boost'].update(reassessment_kind=kind, reassessment_state='confirming_' + kind)
    data['sg_boost'].update({key: value() if callable(value) else value for key, value in change.items()})
    wait, _ = wait_text(data)
    assert 'Herbevestiging onbekend' in wait
    assert 'nog 4 min' not in wait and 'gereed' not in wait and 'starten' not in wait

