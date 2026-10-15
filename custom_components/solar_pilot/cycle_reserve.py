"""Keep a future cycle peak electrical, while flexible loads use real export."""
from __future__ import annotations

import math


def solar_cycle_reserve_relief(kind: str, non_interruptible: bool,
                               total_reserve_w: float, trusted_cycle_peak_w: float) -> float:
    """Return only the solar reservation a managed flexible load may reuse.

    The caller still deducts the complete reservation from electrical headroom.
    A trusted running unmetered dishwasher can heat again; this does not create
    solar power, EV credit or permission to interrupt any protected cycle.
    """
    if kind not in ("switch", "number", "script") or non_interruptible:
        return 0.0
    if not all(math.isfinite(value) for value in (total_reserve_w, trusted_cycle_peak_w)):
        return 0.0
    return min(max(0.0, total_reserve_w), max(0.0, trusted_cycle_peak_w))
