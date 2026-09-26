"""Historical bootstrap helpers for SolarPilot.

For HACS installs, personal bootstrap data lives in ``userfiles/historical_seed.json``.
HACS preserves that directory across upgrades. The public repository deliberately
does not include the user's private historical bootstrap. Runtime control never
depends on a seed; it only accelerates advisory learning and what-if analysis.
"""
from __future__ import annotations

import json
from pathlib import Path

SEED_FORMAT = "solarpilot-historical-analysis-v1"


def _read_seed(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) and data.get("format") == SEED_FORMAT else {}


def load_bundled_seed() -> dict:
    """Load a private persistent seed when present, otherwise an optional bundle.

    The function name is kept for backwards compatibility with the runtime.
    """
    base = Path(__file__).parent
    private_seed = base / "userfiles" / "historical_seed.json"
    data = _read_seed(private_seed)
    if data:
        return data
    # Developer/manual builds may still choose to ship a generic seed.
    return _read_seed(base / "data" / "historical_seed.json")
