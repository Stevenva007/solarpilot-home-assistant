import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLOW = (ROOT / "custom_components" / "solar_pilot" / "config_flow.py").read_text(encoding="utf-8")
CARD = (ROOT / "custom_components" / "solar_pilot" / "frontend" / "solar-pilot-card.js").read_text(encoding="utf-8")
STRINGS = json.loads((ROOT / "custom_components" / "solar_pilot" / "translations" / "en.json").read_text(encoding="utf-8"))
NL_TEXT = (ROOT / "custom_components" / "solar_pilot" / "translations" / "nl.json").read_text(encoding="utf-8")
EN_TEXT = (ROOT / "custom_components" / "solar_pilot" / "translations" / "en.json").read_text(encoding="utf-8")
OPTION_HELP = (ROOT / "custom_components" / "solar_pilot" / "frontend" / "option-help.json").read_text(encoding="utf-8")


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
    for label in ("Overzicht", "Toestellen", "Warmte & comfort", "Energie", "Batterij", "Uitleg"):
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
    for text in ("ACTIEF · SOLARPILOT", "ACTIEF · EXTERN", "ACTIEF · HANDMATIG", "VERBRUIKT"):
        assert text in CARD
    assert ".device.on" in CARD
    assert ".runstate.active" in CARD


def test_active_overview_and_wallbox_have_measured_status_not_configured_mode():
    for text in ("Nu actief", "AUTO LAADT", "WACHT OP LAADSTROOM", "LAADSTATUS ONBEKEND",
                 "STATUS ONBEKEND", "geschat vermogen", "gemeten vermogen", "wallbox-device.on"):
        assert text in CARD
    assert "_activeLoads(c)" in CARD and "_wallboxActivity(wb)" in CARD


def test_automatic_savings_are_qualified_separate_from_electricity_cost():
    for text in ("Voordeel van automatisch gestuurd zonverbruik", "Vandaag · geschat voordeel",
                 "Bewaarde periode · geschat voordeel", "Nog niet vast te stellen",
                 "Handmatige starts en boosts tellen niet mee", "ook handmatige bediening",
                 "niet automatisch extra winst voor SolarPilot"):
        assert text in CARD


def test_beta26_battery_what_if_shows_roundtrip_loss_assumption():
    assert "roundtrip_loss_pct" in CARD
    assert "% totaal round-trip verlies" in CARD


def test_priority_is_one_plain_language_stack_with_car_effect_per_rule():
    for text in (
        "Voorrang en autoladen", "Volledige voorrangslijst",
        "Mag de auto minder laden?", "Beschermde regels staan vast",
    ):
        assert text in CARD
    assert "priority-stack" in CARD and "row locked" in CARD
    assert "Nee · Auto laden staat hoger" in CARD
    assert "Toestemming is bewaard; wordt gebruikt als je dit toestel boven Auto laden zet." in CARD
    assert "'Ja · alleen na bevestigde veilige terugregeling'" not in CARD


def test_device_cards_explain_start_state_and_history_always_names_both_reasons():
    for text in (
        "<h2>Toestellen</h2>", "De gezamenlijke rangorde beheer je via Voorrang",
        "Waarom dit toestel nog niet gestart is", "start_diagnostics", "start_requirements",
        "Benodigd voor start", "Vrije zonnestroom na huisreserve", "Stabiel nodig", "Nog nodig",
        "Van autoladen beschikbaar", "Zonnevermogen voor dit toestel", "solar_start_pool",
        "APP-startvraag", "ontvangen; wacht op bevestigde toestelstatus.",
        "Een lopende afwasbeurt wordt niet opnieuw gestart",
        "Nog ongeveer", "betrouwbare actuele energiemeting", "herstartcontrole is nog bezig",
        "recovery_clear", "reliable_energy_measurement", "general_increase_permission",
        "Een veiligheidscontrole houdt nieuwe starts tegen",
        "Verbinding actueel", "AEG START beschikbaar",
        "Startreden", "Stopreden", "Een ontbrekende externe oorzaak wordt niet ingevuld",
    ):
        assert text in CARD
    assert "start-check" not in CARD


def test_device_schedule_has_one_outcome_choice_and_hides_it_with_active_priority_board():
    schedule = FLOW.split("async def async_step_device_schedule", 1)[1].split("async def async_step_analysis", 1)[0]
    schema = schedule.split("schema = {", 1)[1]
    assert 'vol.Required("wallbox_energy_choice"' in schema
    assert 'vol.Required("min_daily_runtime_min"' in schema
    assert 'vol.Required("max_daily_runtime_min"' in schema
    assert 'vol.Required("min_daily_runtime_s"' not in schema
    assert 'vol.Required("max_daily_runtime_s"' not in schema
    assert 'vol.Required("allow_wallbox_reclaim"' not in schema
    assert 'vol.Required("wallbox_power_policy"' not in schema
    assert '.get("schema") in (1, 2)' in schedule
    assert 'central_fields = {"wallbox_precedence", "wallbox_energy_choice"}' in schedule
    visible_text = "\n".join((FLOW, NL_TEXT, EN_TEXT, CARD, OPTION_HELP))
    for forbidden in (
        "Oude expliciete overnamekeuze gebruiken",
        "Oude expliciete Wallbox-overname",
        "Legacy-veld voor oudere configuraties",
    ):
        assert forbidden not in visible_text
    assert "Toestel instellen · stap 4 van 4 · Planning en energie" in NL_TEXT
    assert "Configure device · step 4 of 4 · Planning and energy" in EN_TEXT


def test_frontend_assets_are_release_bound_to_manifest_version():
    manifest = json.loads((ROOT / "custom_components" / "solar_pilot" / "manifest.json").read_text(encoding="utf-8"))
    version = manifest["version"]
    option_js = (ROOT / "custom_components" / "solar_pilot" / "frontend" / "option-help.js").read_text(encoding="utf-8")
    assert CARD.startswith(f"/* SolarPilot {version}.")
    assert f"option-help.js?v={version}" in CARD
    assert option_js.startswith(f"/* SolarPilot {version}.")
    assert f"option-help.json?v={version}" in option_js
    assert json.loads(OPTION_HELP)["version"] == version


def test_manual_dhw_hold_always_has_a_safe_resume_control():
    assert "dhw.needs_review||dhw.manual_override_active||dhw.manual_hold" in CARD
    assert "a.mode==='solar'||!!dhw.pending" in CARD
    assert "Automatische boilerregeling hervatten" in CARD
    assert "Kies eerst Pauze wanneer Automatisch regelen actief is" in CARD
    assert "Hervatten verstuurt zelf geen temperatuurwijziging" in CARD
    assert 'aria-checked="${dhw.enabled?\'true\':\'false\'}"' in CARD


def test_dhw_overview_uses_reported_target_and_prioritises_wait_status():
    assert 'spTemp(dhw.actual_target_c)' in CARD
    assert "const dhwBlocked=" in CARD
    assert "dhw.control_allowed===false" in CARD
    assert "SolarPilot-voorstel:" in CARD
    assert "niet het gemelde toesteldoel" in CARD
    assert "this._tile('Warm water',dhwTargetText" in CARD


def test_visible_mode_and_dhw_wording_matches_current_behaviour():
    visible_text = "\n".join((NL_TEXT, EN_TEXT, CARD, OPTION_HELP))
    for stale in (
        "Status description",
        "actief alleen in Zonnestroom",
        "standaard 100 W met gewone terugvalvertraging",
    ):
        assert stale not in visible_text
    assert "Boilerregeling vrijgeven (alleen actief bij Automatisch regelen)" in NL_TEXT
    assert "de gewone terugvalvertraging geldt dan niet" in NL_TEXT
    assert '"solar": "Automatisch regelen"' in NL_TEXT


def test_learning_and_history_labels_describe_their_real_scope():
    native_labels = "\n".join(
        (ROOT / "custom_components" / "solar_pilot" / name).read_text(encoding="utf-8")
        for name in ("switch.py", "button.py", "runtime.py")
    )
    for expected in (
        "meetgaten niet meegeteld",
        "Toestelvermogen en Wallbox-respons leren",
        "Deze schakelaar geldt alleen voor toestelvermogens en Wallbox-respons",
        "Apparaat-, lokale PV-, fase- en klimaatleerdata wissen",
        "Actieve bediening, klimaat-OFF-eigendom, handmatige bescherming en veiligheidsinstellingen blijven behouden",
    ):
        assert expected in CARD
    assert "<small>geen meetgaten</small>" not in CARD
    assert "<strong>Lokaal leren</strong>" not in CARD
    assert "Toestelvermogen en Wallbox-respons leren" in native_labels
    assert "Apparaat-, lokale PV-, fase- en klimaatleerdata wissen" in native_labels
    assert "Lokaal leren ingeschakeld" not in native_labels


def test_battery_tab_does_not_imply_the_wallbox_is_duplicated_there():
    nav = CARD.split("_nav(){", 1)[1].split("_globalAlerts", 1)[0]
    assert '["storage","Batterij"]' in nav
    assert '["storage","Auto & batterij"]' not in nav
    assert "<h2>Thuisbatterijen</h2>" in CARD


def test_wallbox_classifier_values_are_rendered_in_plain_dutch():
    for technical, readable in (
        ("stopped", "Gestopt"),
        ("solar", "Zonneladen"),
        ("full_solar", "Volledig zonneladen"),
        ("manual", "Handmatig laden"),
        ("unknown", "Onbekend"),
    ):
        assert f"{technical}:'{readable}'" in CARD
    assert "spWallboxMode(c.wb.effective_mode)" in CARD
    assert "_wallboxActivity(wb).label" in CARD
    assert "spWallboxMode(wb.configured_mode||wb.reported_mode)" in CARD
