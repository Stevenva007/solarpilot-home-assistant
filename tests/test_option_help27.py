"""All shipped option text comes from the release-bound help sources."""
import importlib.util
import json
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[1]
C = ROOT / 'custom_components' / 'solar_pilot'
spec = importlib.util.spec_from_file_location('help_builder_under_test27', ROOT / 'tools' / 'update_option_help.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


def test_catalogue_matches_generator_and_manifest():
    actual = json.loads((C / 'frontend/option-help.json').read_text(encoding='utf-8'))
    assert actual == builder.build()
    assert actual['version'] == json.loads((C / 'manifest.json').read_text())['version']
    assert len(actual['entries']) >= 350


def test_every_native_option_has_specific_help_and_native_description():
    catalogue = builder.build()
    for step, definition in catalogue['steps'].items():
        for key, label in definition.get('data', {}).items():
            item = catalogue['entries'][f'{step}.{key}']
            assert item['title'] == label
            assert len(item['short']) >= 20
            assert len(item['paragraphs'][0]) >= 20
            assert len(' '.join(item['paragraphs'])) >= 180
            assert not item['short'].endswith('..')
            assert definition['data_description'][key] == item['short']
            assert not any('TODO' in t or 'Missing specific' in t for t in item['paragraphs'])


@pytest.mark.parametrize('key', ['morning_enabled', 'night_policy', 'evening_enabled', 'predictive_cooling_enabled', 'morning_time'])
def test_new_dhw_options_have_complete_paragraphs(key):
    item = builder.build()['entries'][f'dhw_comfort.{key}']
    assert len(item['paragraphs']) >= 3
    assert 'Panasonic' in ' '.join(item['paragraphs'])
    assert 'toestemming' not in item['short'] or key.endswith('enabled')


def test_missing_future_option_fails_release_instead_of_generic_guess():
    helper = builder.load('option_help')
    with pytest.raises(ValueError, match='Missing specific help'):
        helper.help_for('dhw_comfort', 'future_undefined_parameter', 'Future')


def test_nl_and_en_new_flow_fields_match():
    nl = json.loads((C/'translations/nl.json').read_text(encoding='utf-8'))
    en = json.loads((C/'translations/en.json').read_text(encoding='utf-8'))
    for step in ('dhw_comfort', 'wallbox', 'wallbox_advanced'):
        assert set(nl['options']['step'][step]['data']) == set(en['options']['step'][step]['data'])
    assert 'dhw_morning_required' in en['options']['error']


def test_option_modal_uses_native_validation_not_an_actuator_or_direct_write():
    text = (C/'frontend/option-help.js').read_text(encoding='utf-8')
    assert "hass.user?.is_admin" in text
    assert 'config/config_entries/options/flow' in text
    assert 'callService(' not in text
    assert 'update_entry' not in text
    assert 'data-permanent-disabled' in text
    assert 'niet bevestigd' in text
    assert '.replace(/[&<>' in text


def test_release_check_includes_help_and_shared_update():
    assert 'help_build.build()' in (ROOT/'tools/check_current_explanation.py').read_text()
    assert 'update_option_help.py' in (ROOT/'tools/update_current_explanation.py').read_text()


def test_new_settings_not_auto_activated_on_upgrade():
    from custom_components.solar_pilot.dhw import DHWPolicy, DHW_DEFAULTS
    old = {'rise_delay_s':60,'fall_delay_s':120,'cooling_clear_s':600, 'safety_confirmed':False}
    c = DHWPolicy(old).settings
    for key, value in old.items():
        assert c[key] == value
    for key in ('morning_enabled','evening_enabled','predictive_cooling_enabled'):
        assert c[key] is False
    assert c['night_policy'] == 'base'
    assert DHW_DEFAULTS['rise_delay_s'] == DHW_DEFAULTS['fall_delay_s'] == 300
    assert DHW_DEFAULTS['cooling_clear_s'] == 1800


def test_embedded_setup_guide_matches_and_documents_limits():
    guide = (ROOT/'docs/BETA28_INSTELLEN.md').read_text(encoding='utf-8')
    assert guide == (C/'docs/BETA28_INSTELLEN.md').read_text(encoding='utf-8')
    for phrase in ('geen fysieke acceptatietest', 'geen elektrische', 'netstroom', '45 °C', '09:00', '55 °C'):
        assert phrase.lower() in guide.lower()
