#!/usr/bin/env python3
"""Generate docs/ACTUELE_WERKING.md from SolarPilot's canonical guide."""
from __future__ import annotations
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "custom_components" / "solar_pilot" / "current_guide.py"
OUT = ROOT / "docs" / "ACTUELE_WERKING.md"
EMBEDDED_OUT = ROOT / "custom_components" / "solar_pilot" / "docs" / "ACTUELE_WERKING.md"

spec = importlib.util.spec_from_file_location("solar_pilot_current_guide", SRC)
mod = importlib.util.module_from_spec(spec)
assert spec.loader is not None
spec.loader.exec_module(mod)
rendered = mod.render_markdown()
OUT.write_text(rendered, encoding="utf-8")
EMBEDDED_OUT.parent.mkdir(parents=True, exist_ok=True)
EMBEDDED_OUT.write_text(rendered, encoding="utf-8")
print(OUT)
print(EMBEDDED_OUT)

# Help and native field descriptions belong to the same release.
import subprocess
import sys
subprocess.run([sys.executable, "-B", str(ROOT / "tools" / "update_option_help.py")], check=True)
