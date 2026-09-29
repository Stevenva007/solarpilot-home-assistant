#!/usr/bin/env python3
"""SolarPilot public GitHub/HACS repository preflight."""
from __future__ import annotations
import ast
import json
import os
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
errors: list[str] = []
allow_owner_placeholder = os.getenv("SOLARPILOT_ALLOW_OWNER_PLACEHOLDER") == "1"
allow_license_pending = os.getenv("SOLARPILOT_ALLOW_LICENSE_PENDING") == "1"

required = [
    ROOT / "README.md",
    ROOT / "hacs.json",
    ROOT / "custom_components" / "solar_pilot" / "manifest.json",
    ROOT / "custom_components" / "solar_pilot" / "frontend" / "solar-pilot-card.js",
]
for path in required:
    if not path.exists():
        errors.append(f"missing required file: {path.relative_to(ROOT)}")

manifest_path = ROOT / "custom_components" / "solar_pilot" / "manifest.json"
if manifest_path.exists():
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    text = manifest_path.read_text(encoding="utf-8")
    if not allow_owner_placeholder and ("OWNER" in text or "REPOSITORY" in text):
        errors.append("manifest GitHub owner/repository placeholders are not finalized")
    for key in ("domain", "documentation", "issue_tracker", "codeowners", "name", "version"):
        if not manifest.get(key):
            errors.append(f"manifest missing {key}")

hacs_path = ROOT / "hacs.json"
if hacs_path.exists():
    hacs = json.loads(hacs_path.read_text(encoding="utf-8"))
    if not hacs.get("name"):
        errors.append("hacs.json missing name")
    if not hacs.get("render_readme"):
        errors.append("hacs.json must set render_readme=true when info.md is absent")
    if hacs.get("persistent_directory") != "userfiles":
        errors.append("hacs.json persistent_directory must remain userfiles")

# HACS' GitHub validator expects a recognizable repository license.  The build
# archive intentionally leaves the legal choice to the repository owner.
if not allow_license_pending and not any((ROOT / name).exists() for name in ("LICENSE", "LICENSE.txt", "LICENSE.md")):
    errors.append("repository license missing; add a GitHub-recognizable software license before release")

# Generated/cache/runtime data must never be committed.
for path in ROOT.rglob("*"):
    rel = path.relative_to(ROOT)
    if path.is_dir() and path.name in {"__pycache__", ".pytest_cache"}:
        errors.append(f"cache directory present: {rel}")
    if path.is_file() and path.name.lower().startswith("solarpilot-analyse-") and path.suffix.lower() in {".json", ".zip"}:
        errors.append(f"private analysis export present: {rel}")
    if path.is_file() and path.suffix == ".pyc":
        errors.append(f"compiled Python file present: {rel}")


# Known private migration labels from the original household build must never re-enter
# the public source, documentation or examples.
private_markers = (
    "kapsalon",
    "kelder",
    "warmtepompboiler_naar_",
    "pv_excess_control_wallbox_ev_lader_enabled",
    "pv_excess_control_ontvochtiger_",
    "pv_excess_control_koelkast_",
)
scan_roots = [ROOT / "custom_components", ROOT / "docs", ROOT / "examples", ROOT / "START_HIER.md"]
for scan_root in scan_roots:
    paths = [scan_root] if scan_root.is_file() else scan_root.rglob("*")
    for path in paths:
        if not path.is_file() or path.suffix.lower() not in {".py", ".md", ".json", ".js", ".yaml", ".yml"}:
            continue
        try:
            content = path.read_text(encoding="utf-8").lower()
        except UnicodeDecodeError:
            continue
        for marker in private_markers:
            if marker in content:
                errors.append(f"private migration marker '{marker}' present in {path.relative_to(ROOT)}")

# The public first-install helper may not embed household-specific HA entity IDs.
first_install = ROOT / "custom_components" / "solar_pilot" / "first_install.py"
if first_install.exists():
    tree = ast.parse(first_install.read_text(encoding="utf-8"))
    entity_pattern = re.compile(r"^(?:sensor|binary_sensor|climate|water_heater|select|switch|input_number|number|weather|script|automation)\.[a-z0-9_]+$")
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and entity_pattern.fullmatch(node.value):
            errors.append(f"household-specific entity default in first_install.py: {node.value}")

if errors:
    raise SystemExit("\n".join(f"ERROR: {error}" for error in errors))
print("OK: public repository preflight")
