"""Execute shipped read-only cloud-buffer presentation; fictitious sources only."""
import json
import shutil
import subprocess
import time

import pytest

from test_overview_details60 import Markup
from test_sg_minimum_ui72 import minimum_fixture
from test_sg_ui_platforms62 import CARD, execute


def cloud_fixture(**changes):
    data = minimum_fixture()
    data['sg_boost'].update(import_threshold_w=600, stop_delay_s=300,
                           cloud_active=True, cloud_import_hold=True,
                           cloud_remaining_s=250, cloud_valid_until=time.time() + 120,
                           minimum_remaining_s=0, minimum_active=False)
    data['sg_boost'].update({key: value() if callable(value) else value
                            for key, value in changes.items()})
    return data


def render_cloud(data, view='comfort'):
    result = execute(data, view=view)
    root = Markup(result['initial']).root
    buffers = [n for n in root.walk() if 'data-sg-cloud' in n.attributes]
    assert not result['calls']
    return buffers, root.text()


@pytest.mark.parametrize('view', ['board', 'comfort'])
def test_cloud_threshold_and_duration_are_visible_after_minimum(view):
    buffers, details = render_cloud(cloud_fixture(), view)
    assert len(buffers) == 1
    text = buffers[0].text()
    assert 'Wolkenbuffer · 600 W / 5 min' in text
    assert 'Netafname boven 600 W · nog 4 min 10 s' in text
    assert 'Minimumduur en wolkenbuffer lopen tegelijk' in text
    assert 'harde beveiligingen kunnen SG eerder vrijgeven' in text
    assert 'Drempel netafname wolkenbuffer 600 W' in details
    assert 'Aaneengesloten bufferduur 5 min' in details
    assert 'Minimum verstreken' in details
    assert 'Compressor draait' not in details


@pytest.mark.parametrize('change', [
    {'cloud_remaining_s': None}, {'cloud_remaining_s': -1},
    {'cloud_remaining_s': True}, {'cloud_remaining_s': 301},
    {'cloud_active': False}, {'cloud_valid_until': None},
    {'cloud_valid_until': time.time() - 1}, {'observed_at': time.time() - 121},
    {'observed_at': None}, {'observed_at': lambda: time.time() + 60},
    {'relay_confirmed': False}, {'relay_on': False}, {'lease_confirmed': False},
    {'lease_remaining_s': 0}, {'owner': 'manual'},
    {'relay_valid_until': time.time() - 1},
])
def test_unconfirmed_stale_expired_and_invalid_cloud_time_is_unknown(change):
    text = render_cloud(cloud_fixture(**change))[0][0].text()
    assert 'Resterende wolkenbuffer onbekend' in text
    assert 'nog 4 min' not in text and 'Geen lopende importbuffer' not in text


@pytest.mark.parametrize('remaining,elapsed', [(0, 0), (1, 2)])
def test_zero_cloud_time_does_not_release_sg_or_claim_new_authority(remaining, elapsed):
    data = cloud_fixture(cloud_remaining_s=remaining, observed_at=time.time() - elapsed)
    buffers, details = render_cloud(data)
    assert 'Wolkenbuffer verstreken · actuele regeling bepaalt het vrijgeven' in buffers[0].text()
    assert 'SG-contact Actief' in details
    assert data['sg_boost']['desired_on'] is True
    assert data['sg_boost']['cloud_remaining_s'] == remaining


@pytest.mark.parametrize('cloud_remaining', [250, 0])
def test_cloud_and_minimum_are_independent_simultaneous_clocks(cloud_remaining):
    data = cloud_fixture(cloud_remaining_s=cloud_remaining,
                         minimum_remaining_s=480, minimum_active=True)
    _, details = render_cloud(data)
    assert 'Minimum SG-aanvraagduur · 20 min' in details
    assert 'Nog 8 min · alleen de SG-aanvraag' in details
    assert ('Netafname boven 600 W · nog 4 min 10 s' if cloud_remaining else
            'Wolkenbuffer verstreken') in details
    assert 'extra 5 min' not in details


@pytest.mark.parametrize('expired', [False, True])
def test_idle_cloud_status_requires_its_original_current_sources(expired):
    data = cloud_fixture(cloud_active=False, cloud_remaining_s=None,
                         cloud_valid_until=time.time() + (-1 if expired else 120))
    text = render_cloud(data)[0][0].text()
    assert ('Resterende wolkenbuffer onbekend' if expired else
            'Geen lopende importbuffer') in text


def test_nonfinite_overview_anchor_cannot_revive_a_cloud_countdown():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node is required for actual frontend execution')
    script = r"""
const fs=require('node:fs'),vm=require('node:vm'),data=JSON.parse(fs.readFileSync(0,'utf8'));
const sandbox={HTMLElement:class{},window:{},customElements:{get:()=>null,define:()=>{}},data};
vm.createContext(sandbox);vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),sandbox);
process.stdout.write(vm.runInContext(`(()=>{const card=Object.create(SolarPilotCard.prototype);
card._last={attributes:data};data.sg_boost.observed_at=Infinity;
return card._sgCloudBanner(card._ctx());})()`,sandbox));
"""
    result = subprocess.run([node, '-e', script, str(CARD)], input=json.dumps(cloud_fixture()),
                            text=True, capture_output=True)
    assert result.returncode == 0, result.stderr
    text = Markup(result.stdout).root.text()
    assert 'Resterende wolkenbuffer onbekend' in text and 'nog 4 min' not in text


@pytest.mark.parametrize('remaining,expected', [(91, 'nog 1 min 31 s'),
                                             (92, 'Resterende wolkenbuffer onbekend')])
def test_fractional_duration_accepts_only_its_backend_ceiling(remaining, expected):
    text = render_cloud(cloud_fixture(stop_delay_s=90.2, cloud_remaining_s=remaining))[0][0].text()
    assert expected in text


def test_explicit_custom_import_policy_is_shown_without_solar_reset_hysteresis():
    data = cloud_fixture(import_threshold_w=450, stop_delay_s=90,
                         hysteresis_w=900, cloud_remaining_s=60)
    text = render_cloud(data)[0][0].text()
    assert 'Wolkenbuffer · 450 W / 1 min 30 s' in text
    assert 'Netafname boven 450 W · nog 1 min' in text
    assert '900 W' not in text


@pytest.mark.parametrize('change', [
    {'desired_on': False}, {'import_threshold_w': True},
    {'import_threshold_w': None}, {'stop_delay_s': -1}, {'stop_delay_s': None},
])
def test_no_active_request_or_invalid_policy_has_no_cloud_banner(change):
    assert render_cloud(cloud_fixture(**change))[0] == []
