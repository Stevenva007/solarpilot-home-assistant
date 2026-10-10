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
    assert {'sg_boost.entity_id', 'sg_boost.enabled', 'sg_boost.commissioning_confirmed',
            'sg_boost.watchdog_confirmed', 'sg_sources.power_scope',
            'sg_advanced.lease_s', 'sg_advanced.renew_s'} <= set(actual['entries'])


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


@pytest.mark.parametrize('key', ['start_delay_s', 'stop_delay_s', 'rest_s', 'lease_s', 'renew_s'])
def test_sg_options_have_complete_paragraphs(key):
    item = builder.build()['entries'][f'sg_advanced.{key}']
    assert len(item['paragraphs']) >= 3
    assert 'Panasonic' in ' '.join(item['paragraphs'])
    assert 'SolarPilot' in ' '.join(item['paragraphs'])


def test_missing_future_option_fails_release_instead_of_generic_guess():
    helper = builder.load('option_help')
    with pytest.raises(ValueError, match='Missing specific help'):
        helper.help_for('sg_advanced', 'future_undefined_parameter', 'Future')


def test_nl_and_en_new_flow_fields_match():
    nl = json.loads((C/'translations/nl.json').read_text(encoding='utf-8'))
    en = json.loads((C/'translations/en.json').read_text(encoding='utf-8'))
    for step in ('sg_boost', 'sg_sources', 'sg_advanced', 'wallbox', 'wallbox_advanced'):
        assert set(nl['options']['step'][step]['data']) == set(en['options']['step'][step]['data'])
    assert {'sg_commissioning', 'sg_watchdog', 'sg_reopen'} <= set(en['options']['error'])


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


def test_new_sg_settings_never_infer_authority_from_old_temperature_options():
    from custom_components.solar_pilot.sg_config import normalize_config, SG_DEFAULTS
    old = {'rise_delay_s':60, 'fall_delay_s':120, 'cooling_clear_s':600,
           'safety_confirmed':True, 'auto_enabled':True, 'boost_temp':60}
    config = normalize_config(old)
    assert config == SG_DEFAULTS
    assert not config['enabled']
    assert not config['commissioning_confirmed']
    assert not config['watchdog_confirmed']
    explicit = {'threshold_w':3400, 'expected_power_w':3500, 'power_scope':'supply1'}
    assert all(normalize_config(explicit)[key] == value for key,value in explicit.items())


def test_historical_embedded_setup_guide28_remains_byte_equal():
    guide = (ROOT/'docs/BETA28_INSTELLEN.md').read_text(encoding='utf-8')
    assert guide == (C/'docs/BETA28_INSTELLEN.md').read_text(encoding='utf-8')
    for phrase in ('geen fysieke acceptatietest', 'geen elektrische', 'netstroom', '45 °C', '09:00', '55 °C'):
        assert phrase.lower() in guide.lower()


def test_current_embedded_setup_guide62_documents_commissioning_and_rollback():
    guide = (ROOT/'docs/BETA62_INSTELLEN.md').read_text(encoding='utf-8')
    assert guide == (C/'docs/BETA62_INSTELLEN.md').read_text(encoding='utf-8')
    for phrase in ('expliciete toestemming', 'lokale', '300', '60', 'rollback', 'back-up', 'voeding 1', 'Panasonic'):
        assert phrase.lower() in guide.lower()


def test_retired_panasonic_writer_help_is_not_a_current_configuration_surface():
    catalogue = builder.build()
    retired_steps = {'dhw', 'dhw_basic', 'dhw_comfort', 'dhw_advanced', 'climate', 'climate_basic', 'climate_advanced'}
    assert not retired_steps.intersection(catalogue['steps'])
    assert not any(key.startswith(('dhw_', 'climate_', 'dashboard:dhw_', 'dashboard:climate_'))
                   for key in catalogue['entries'])
    assert not any('manual_suspend_extra_dhw' in key or 'respect_optional_dhw' in key
                   for key in catalogue['entries'])
