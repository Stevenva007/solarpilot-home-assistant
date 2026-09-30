"""Reconstruct the uploaded public beta.35 source in a clean baseline worktree.

Transport only: this script is never included in the release or installed in HA.
Existing GitHub publishing fixes and the asynchronous boiler test double remain.
"""
from __future__ import annotations
import argparse
import base64
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

BASE = "35ec20ef23bd4176e5480638ff82c7cc040ab2f3"
DICT_SHA = "1d6eecabe00ed4a13c11e95ed9c9af20cc0f6092828cec274506196b4a76e9ce"
BUNDLE_SHA = "db969d6dfab7423f9dbc695607b0dda0cd57b3fd544b430ef9585c9a48f69152"
PRESERVE = {"PUBLISH_TO_GITHUB.md", "tools/publish_github_windows.ps1", "tests/test_dhw_runtime.py"}

def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=Path, required=True)
    parser.add_argument("--payload", type=Path, required=True)
    args = parser.parse_args()
    root = args.target.resolve()
    payload = args.payload.resolve()
    def git(*argv: str) -> bytes:
        return subprocess.check_output(["git", "-C", str(root), *argv])
    if git("rev-parse", "HEAD").decode().strip() != BASE:
        raise SystemExit("Refusing to reconstruct on a different baseline")
    names = sorted(p.decode() for p in git("ls-tree", "-r", "--name-only", "-z", BASE).split(b"\0") if p)
    textbase = {}
    for name in names:
        raw = (root / name).read_bytes()
        try:
            textbase[name] = raw.decode("utf-8")
        except UnicodeDecodeError:
            pass
    dictionary = json.dumps({"files": textbase}, ensure_ascii=False, separators=(",", ":")).encode()
    if sha(dictionary) != DICT_SHA:
        raise SystemExit("Baseline dictionary SHA-256 mismatch")
    parts = sorted(payload.glob("part*.b64"))
    if [p.name for p in parts] != [f"part{i:02d}.b64" for i in range(5)]:
        raise SystemExit("Incomplete transport")
    encoded = "".join(p.read_text(encoding="ascii") for p in parts)
    archive = base64.b64decode(encoded, validate=True)
    if sha(archive) != BUNDLE_SHA:
        raise SystemExit("Source transport SHA-256 mismatch")
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        (tmp / "base.json").write_bytes(dictionary)
        (tmp / "bundle.zst").write_bytes(archive)
        subprocess.run(["zstd", "-d", "--patch-from=" + str(tmp / "base.json"), str(tmp / "bundle.zst"), "-o", str(tmp / "bundle.json")], check=True)
        bundle = json.loads((tmp / "bundle.json").read_bytes())
    files, hashes = bundle["files"], bundle["verify"]
    if set(files) != set(hashes) or len(files) != 55 or set(files) & PRESERVE:
        raise SystemExit("Unexpected source manifest")
    checked = {}
    for name, text in files.items():
        relative = Path(name)
        target = root / relative
        allowed = name in {"CHANGELOG.md", "README.md", "START_HIER.md"} or relative.parts[0] in {"custom_components", "docs", "tests", "tools"}
        if not allowed or relative.is_absolute() or ".." in relative.parts or not target.resolve().is_relative_to(root):
            raise SystemExit("Unsafe source path: " + name)
        data = text.encode("utf-8")
        if sha(data) != hashes[name]:
            raise SystemExit("File SHA-256 mismatch: " + name)
        checked[name] = data
    for name, data in checked.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
    for name, expected in hashes.items():
        if sha((root / name).read_bytes()) != expected:
            raise SystemExit("Written source mismatch: " + name)
    manifest = json.loads((root / "custom_components/solar_pilot/manifest.json").read_bytes())
    if manifest["version"] != "1.0.0-beta.35":
        raise SystemExit("Wrong release version")
    print(f"VERIFIED: {len(checked)} updated source/documentation files match the uploaded beta.35 bytes.")
    print("Retained: original repository history, prior test reports and three existing GitHub-specific fixes.")

if __name__ == "__main__":
    main()
