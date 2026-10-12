"""Run repository configuration against temporary fictional repositories."""
import json
from pathlib import Path
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize("existing_block", [True, False])
def test_configure_repository_preserves_readme_prose_and_is_idempotent(tmp_path, existing_block):
    tools = tmp_path / "tools"
    tools.mkdir()
    shutil.copy2(ROOT / "tools/configure_repository.py", tools)
    manifest_dir = tmp_path / "custom_components/solar_pilot"
    manifest_dir.mkdir(parents=True)
    (manifest_dir / "manifest.json").write_text(json.dumps({"version": "1.0.0-beta.79"}))
    prefix = "# Fictional project\n\nKeep this introduction.\n"
    extra = "Keep this HACS explanation.\n\n### Extra details\n\nKeep these details.\n"
    suffix = "\n## Upgrade\n\nKeep upgrade and rollback instructions.\n"
    old = """## Open direct in HACS

[![Open your Home Assistant instance and open SolarPilot in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=old-example&repository=old-example&category=integration)

Repository: `https://github.com/old-example/old-example`

"""
    readme = tmp_path / "README.md"
    readme.write_text(prefix + ("\n" + old + extra if existing_block else "") + suffix)
    args = [sys.executable, str(tools / "configure_repository.py"), "fictional-owner", "fictional-repository"]
    subprocess.run(args, check=True, capture_output=True, text=True)
    first = readme.read_text()
    subprocess.run(args, check=True, capture_output=True, text=True)
    assert readme.read_text() == first
    for phrase in ("Keep this introduction.", "## Upgrade", "Keep upgrade and rollback instructions."):
        assert phrase in first
    if existing_block:
        assert "Keep this HACS explanation." in first and "Keep these details." in first
        assert first.index("## Open direct in HACS") < first.index("## Upgrade")
    assert first.count("## Open direct in HACS") == 1
    assert "old-example" not in first
    assert "owner=fictional-owner&repository=fictional-repository" in first
    manifest = json.loads((manifest_dir / "manifest.json").read_text())
    assert manifest["documentation"] == "https://github.com/fictional-owner/fictional-repository#readme"
    assert manifest["issue_tracker"] == "https://github.com/fictional-owner/fictional-repository/issues"
    assert manifest["codeowners"] == ["@fictional-owner"]
