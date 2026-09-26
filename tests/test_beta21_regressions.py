from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_energy_sensors_do_not_use_measurement_state_class():
    text = (ROOT / "custom_components" / "solar_pilot" / "sensor.py").read_text(encoding="utf-8")
    assert 'elif suffix == "ems_solar_today"' in text
    assert 'self._attr_state_class = SensorStateClass.TOTAL_INCREASING' in text
    assert 'elif suffix == "battery_10_5_avoided"' in text
    assert 'self._attr_state_class = SensorStateClass.TOTAL' in text


def test_async_entry_setup_preloads_private_files_in_executor():
    text = (ROOT / "custom_components" / "solar_pilot" / "__init__.py").read_text(encoding="utf-8")
    assert 'await hass.async_add_executor_job(load_private_bundle)' in text
    assert 'await hass.async_add_executor_job(load_bundled_seed, private_bundle)' in text
    assert 'await hass.async_add_executor_job(delete_private_files_if_requested)' in text
