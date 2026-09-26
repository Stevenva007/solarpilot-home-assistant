import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = (ROOT / "custom_components" / "solar_pilot" / "config_flow.py").read_text(encoding="utf-8")
CARD = (ROOT / "custom_components" / "solar_pilot" / "frontend" / "solar-pilot-card.js").read_text(encoding="utf-8")
STRINGS = json.loads((ROOT / "custom_components" / "solar_pilot" / "translations" / "en.json").read_text(encoding="utf-8"))


def test_root_options_are_grouped_into_seven_hubs():
    for step in (
        "overview", "energy_hub", "loads_hub", "comfort_hub",
        "storage_hub", "intelligence_hub", "advanced_hub",
    ):
        assert f'"{step}"' in FLOW
        assert step in STRINGS["options"]["step"]["init"]["menu_options"]
    # The old flat EMS entry is deliberately not a root menu item anymore.
    root_block = FLOW.split("async def async_step_init", 1)[1].split("async def async_step_overview", 1)[0]
    assert '"ems"' not in root_block


def test_progressive_disclosure_steps_exist():
    for method in (
        "async_step_power_policy",
        "async_step_timing",
        "async_step_phase_learning",
        "async_step_wallbox_advanced",
        "async_step_smart_climate_advanced",
        "async_step_battery_control",
        "async_step_device_behavior",
        "async_step_device_schedule",
    ):
        assert f"def {method}" in FLOW


def test_card_uses_six_logical_views_and_keeps_modes_global():
    for key in ("overview", "loads", "comfort", "energy", "storage", "guide"):
        assert f'data-value="{key}"' in CARD or f"value: '{key}'" in CARD or f'"{key}"' in CARD
    for label in ("Overzicht", "Verbruikers", "Comfort", "Energie", "Opslag", "Uitleg"):
        assert label in CARD
    for label in ("Observatie", "Zonnestroom", "Pauze"):
        assert label in CARD


def test_package_has_one_current_rules_doc_and_one_navigation_doc():
    assert (ROOT / "docs" / "ACTUELE_WERKING.md").exists()
    assert (ROOT / "docs" / "CONFIGURATIESTRUCTUUR.md").exists()
    obsolete = {
        "EMS.md", "BOILER.md", "WALLBOX.md", "SLIM_KLIMAAT.md",
        "BATTERIJ_AANSTURING.md", "LOKAAL_LEREND_EMS.md",
    }
    assert obsolete.isdisjoint({p.name for p in (ROOT / "docs").glob("*.md")})


def test_climate_dashboard_exposes_all_settings_with_advice_and_consequences():
    text=(ROOT/'custom_components'/'solar_pilot'/'frontend'/'solar-pilot-card.js').read_text(encoding="utf-8")
    assert 'settings_catalog' in text
    assert 'Advies:' in text
    assert 'Lager:' in text and 'Hoger:' in text
    assert "solar_pilot','set_climate_setting" in text
    assert 'Bevindingen & leren' in text
    assert 'Meldingen' in text
    assert 'hoe SolarPilot deze klimaatbeslissing maakt' in text
