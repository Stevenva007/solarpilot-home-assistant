"""Historical bootstrap helpers for SolarPilot.

For HACS installs, the preferred source is ``userfiles/private_bundle.json``, which
may contain both installation-specific mappings and an aggregated historical seed.
The older ``userfiles/historical_seed.json`` remains supported. HACS preserves the
userfiles directory across upgrades. Runtime control never depends on a seed; it
only accelerates advisory learning and what-if analysis.
"""
from __future__ import annotations

import json
from pathlib import Path

from .private_bundle import bundle_historical_seed, load_private_bundle

SEED_FORMAT = "solarpilot-historical-analysis-v1"


def _read_seed(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) and data.get("format") == SEED_FORMAT else {}


def load_bundled_seed(bundle: dict | None = None) -> dict:
    """Load a private persistent seed when present, otherwise an optional bundle.

    The function name is kept for backwards compatibility with the runtime.
    """
    # Preferred beta.20+ path: a single private bundle contains both entity
    # mappings and the aggregated historical bootstrap.
    source_bundle = bundle if bundle is not None else load_private_bundle()
    data = bundle_historical_seed(source_bundle)
    if data:
        return data
    base = Path(__file__).parent
    # Backwards-compatible single seed file for earlier HACS/private installs.
    private_seed = base / "userfiles" / "historical_seed.json"
    data = _read_seed(private_seed)
    if data:
        return data
    # Developer/manual builds may still choose to ship a generic seed.
    return _read_seed(base / "data" / "historical_seed.json")
