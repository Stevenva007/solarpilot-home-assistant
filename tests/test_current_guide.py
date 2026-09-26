import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE_PATH = ROOT / "custom_components" / "solar_pilot" / "current_guide.py"

spec = importlib.util.spec_from_file_location("current_guide_under_test", GUIDE_PATH)
guide = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(guide)


def test_current_guide_version_matches_release():
    manifest = json.loads((ROOT / "custom_components" / "solar_pilot" / "manifest.json").read_text())
    const_text = (ROOT / "custom_components" / "solar_pilot" / "const.py").read_text()
    card_text = (ROOT / "custom_components" / "solar_pilot" / "frontend" / "solar-pilot-card.js").read_text()
    assert manifest["version"] == guide.GUIDE_VERSION
    assert f'VERSION = "{guide.GUIDE_VERSION}"' in const_text
    assert f"SolarPilot {guide.GUIDE_VERSION}." in card_text


def test_current_markdown_is_generated_from_single_source():
    actual = (ROOT / "docs" / "ACTUELE_WERKING.md").read_text()
    assert actual == guide.render_markdown()


def test_current_guide_has_required_topics_and_no_previous_release_label():
    titles = " ".join(s["title"] for s in guide.CURRENT_GUIDE["sections"])
    for topic in ("Wallbox", "warm water", "PV-model", "Fase", "Thuisbatterij", "verwarmen", "Kwartierpiek", "Migratie"):
        assert topic.lower() in titles.lower()
    current = guide.render_markdown()
    assert "1.0.0-beta.8" not in current
    assert "1.0.0-beta.9" not in current
    assert "43 °C setpoint" not in current


def test_home_assistant_card_exposes_current_guide():
    card = (ROOT / "custom_components" / "solar_pilot" / "frontend" / "solar-pilot-card.js").read_text()
    sensor = (ROOT / "custom_components" / "solar_pilot" / "sensor.py").read_text()
    assert "solar-pilot-guide-card" in card
    assert "Actuele uitleg" in card
    assert '"guide", "Actuele uitleg"' in sensor
    assert "solar_pilot_guide" in sensor


def test_readme_and_start_here_point_to_canonical_current_guide():
    for filename in ("README.md", "START_HIER.md"):
        text = (ROOT / filename).read_text()
        assert "ACTUELE_WERKING.md" in text
