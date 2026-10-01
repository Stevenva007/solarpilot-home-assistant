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
    for label in ("Overzicht", "Toestellen", "Warmte & comfort", "Energie", "Auto & batterij", "Uitleg"):
        assert label in CARD
    for label in ("Alleen bekijken", "Automatisch regelen", "Pauze"):
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


def test_live_dashboard_refresh_preserves_open_sections_and_avoids_guide_churn():
    assert '_captureUiState' in CARD
    assert '_restoreUiState' in CARD
    assert '_viewRenderSignature' in CARD
    assert 'this._view!=="guide"' in CARD
    assert '.view{animation:' not in CARD


def test_beta26_mobile_menu_and_manual_consumer_controls_are_visible():
    assert "hass-toggle-menu" in CARD
    assert "mobile-menu" in CARD
    assert "Home Assistant-menu openen" in CARD
    assert "Manueel starten" in CARD
    assert "Manueel stoppen" in CARD
    assert "manual_start_entity" in CARD and "manual_stop_entity" in CARD


def test_beta26_active_consumers_have_clear_visual_state_badges():
    for text in ("AAN · SOLARPILOT", "AAN · EXTERN", "MANUEEL", "VERBRUIKT"):
        assert text in CARD
    assert ".device.on" in CARD
    assert ".runstate.active" in CARD


def test_beta26_battery_what_if_shows_roundtrip_loss_assumption():
    assert "roundtrip_loss_pct" in CARD
    assert "% totaal round-trip verlies" in CARD
