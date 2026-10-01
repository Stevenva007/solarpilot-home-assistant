#!/usr/bin/env python3
"""Validate that SolarPilot's technical handoff dossier is current.

This check has two jobs:
1. The dossier must describe the same release as manifest.json and contain the
   required handoff sections.
2. On normal pushes/PRs, a functional integration change must update
   OVERDRACHT.md in the same change set.

The second check is intentionally skipped when no usable base SHA is supplied
(for example scheduled validation and tag-release validation).
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "OVERDRACHT.md"
MANIFEST = ROOT / "custom_components" / "solar_pilot" / "manifest.json"
CURRENT_GUIDE = ROOT / "docs" / "ACTUELE_WERKING.md"

errors: list[str] = []

if not HANDOFF.exists():
    errors.append("OVERDRACHT.md ontbreekt")
    handoff_text = ""
else:
    handoff_text = HANDOFF.read_text(encoding="utf-8")

manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
version = str(manifest.get("version") or "").strip()
if not version:
    errors.append("manifest.json bevat geen versie")

version_match = re.search(
    r"<!--\s*solarpilot-handoff-version:\s*([^\s]+)\s*-->",
    handoff_text,
)
if not version_match:
    errors.append("machineleesbare solarpilot-handoff-version ontbreekt")
elif version_match.group(1) != version:
    errors.append(
        f"OVERDRACHT.md versie {version_match.group(1)!r} != manifest versie {version!r}"
    )

schema_match = re.search(
    r"<!--\s*solarpilot-handoff-schema:\s*(\d+)\s*-->",
    handoff_text,
)
if not schema_match:
    errors.append("machineleesbare solarpilot-handoff-schema ontbreekt")

if version and f"**Actuele productieversie:** `{version}`" not in handoff_text:
    errors.append("zichtbare actuele productieversie ontbreekt of is verouderd")

required_sections = (
    "## AI-handoff",
    "## 1. Projectstatus",
    "## 2. Bronnen van waarheid",
    "## 3. Niet-onderhandelbare ontwerpregels",
    "## 4. Huidige functionele toestand",
    "## 5. Architectuur en belangrijke bestanden",
    "## 6. Configuratie, migratie en persistente data",
    "## 7. Test- en releaseprocedure",
    "## 8. Installeren, upgraden en rollback",
    "## 9. Privacy en secrets",
    "## 10. Bekende grenzen en volgende aandachtspunten",
    "## 11. Release-checklist",
)
for section in required_sections:
    if section not in handoff_text:
        errors.append(f"verplicht onderdeel ontbreekt: {section}")

if CURRENT_GUIDE.exists() and version:
    current_text = CURRENT_GUIDE.read_text(encoding="utf-8")
    if f"**Versie:** {version}" not in current_text:
        errors.append("ACTUELE_WERKING.md loopt niet gelijk met manifestversie")

def _usable_sha(value: str | None) -> bool:
    if not value:
        return False
    value = value.strip()
    return bool(re.fullmatch(r"[0-9a-fA-F]{40}", value)) and set(value) != {"0"}

base = (os.getenv("HANDOFF_PR_BASE") or os.getenv("HANDOFF_BASE") or "").strip()
head = (os.getenv("HANDOFF_HEAD") or "").strip()

if _usable_sha(base) and _usable_sha(head):
    try:
        subprocess.run(
            ["git", "cat-file", "-e", f"{base}^{{commit}}"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        changed_raw = subprocess.check_output(
            ["git", "diff", "--name-only", base, head],
            cwd=ROOT,
            text=True,
        )
        changed = {line.strip() for line in changed_raw.splitlines() if line.strip()}
        functional = {
            path
            for path in changed
            if path.startswith("custom_components/solar_pilot/")
            or path == "hacs.json"
        }
        if functional and "OVERDRACHT.md" not in changed:
            preview = ", ".join(sorted(functional)[:8])
            if len(functional) > 8:
                preview += ", …"
            errors.append(
                "functionele SolarPilot-wijziging zonder bijgewerkt OVERDRACHT.md: "
                + preview
            )
    except (subprocess.CalledProcessError, OSError) as err:
        errors.append(f"git-diffcontrole overdrachtsdossier mislukt: {err}")

if errors:
    raise SystemExit("\n".join(f"ERROR: {error}" for error in errors))

print(f"OK: overdrachtsdossier {version}")
