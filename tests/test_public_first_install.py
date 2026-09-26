import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_public_first_install_has_no_household_specific_entity_ids():
    path = ROOT / "custom_components" / "solar_pilot" / "first_install.py"
    tree = ast.parse(path.read_text(encoding="utf-8"))
    pattern = re.compile(r"^(?:sensor|binary_sensor|climate|water_heater|select|switch|input_number|number|weather|script|automation)\.[a-z0-9_]+$")
    found = [node.value for node in ast.walk(tree) if isinstance(node, ast.Constant) and isinstance(node.value, str) and pattern.fullmatch(node.value)]
    assert found == []


def test_public_first_install_keeps_safe_sun_suggestion():
    text = (ROOT / "custom_components" / "solar_pilot" / "first_install.py").read_text(encoding="utf-8")
    assert '"sun_entity": "sun.sun"' in text


def test_public_repository_has_no_private_migration_markers():
    markers = (
        "kapsalon",
        "kelder",
        "warmtepompboiler_naar_",
        "pv_excess_control_wallbox_ev_lader_enabled",
        "pv_excess_control_ontvochtiger_",
        "pv_excess_control_koelkast_",
    )
    paths = [
        ROOT / "custom_components" / "solar_pilot" / "ems.py",
        ROOT / "custom_components" / "solar_pilot" / "current_guide.py",
        ROOT / "START_HIER.md",
    ]
    text = "\n".join(path.read_text(encoding="utf-8").lower() for path in paths)
    assert not any(marker in text for marker in markers)


def test_root_and_embedded_current_guides_match():
    root_guide = (ROOT / "docs" / "ACTUELE_WERKING.md").read_text(encoding="utf-8")
    embedded_guide = (ROOT / "custom_components" / "solar_pilot" / "docs" / "ACTUELE_WERKING.md").read_text(encoding="utf-8")
    assert root_guide == embedded_guide
