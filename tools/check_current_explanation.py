#!/usr/bin/env python3
"""Fail a SolarPilot release when the current explanation is stale or mismatched."""
from __future__ import annotations
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GUIDE_PATH = ROOT / "custom_components" / "solar_pilot" / "current_guide.py"
spec = importlib.util.spec_from_file_location("current_guide_check", GUIDE_PATH)
guide = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(guide)

manifest = json.loads((ROOT / "custom_components" / "solar_pilot" / "manifest.json").read_text(encoding="utf-8"))
const_text = (ROOT / "custom_components" / "solar_pilot" / "const.py").read_text(encoding="utf-8")
card_text = (ROOT / "custom_components" / "solar_pilot" / "frontend" / "solar-pilot-card.js").read_text(encoding="utf-8")
actual_md = (ROOT / "docs" / "ACTUELE_WERKING.md").read_text(encoding="utf-8")
embedded_md = (ROOT / "custom_components" / "solar_pilot" / "docs" / "ACTUELE_WERKING.md").read_text(encoding="utf-8")
expected_md = guide.render_markdown()

errors = []
if manifest.get("version") != guide.GUIDE_VERSION:
    errors.append("manifest version != current guide version")
if f'VERSION = "{guide.GUIDE_VERSION}"' not in const_text:
    errors.append("const.py version != current guide version")
if f"SolarPilot {guide.GUIDE_VERSION}." not in card_text:
    errors.append("dashboard card version != current guide version")
if actual_md != expected_md:
    errors.append("docs/ACTUELE_WERKING.md is not regenerated from current_guide.py")
if embedded_md != expected_md:
    errors.append("embedded ACTUELE_WERKING.md is not regenerated from current_guide.py")
if "solar-pilot-guide-card" not in card_text:
    errors.append("Home Assistant guide card missing")
if errors:
    raise SystemExit("\n".join(f"ERROR: {e}" for e in errors))
print(f"OK: actuele uitleg {guide.GUIDE_VERSION} · {guide.GUIDE_HASH[:16]}")
