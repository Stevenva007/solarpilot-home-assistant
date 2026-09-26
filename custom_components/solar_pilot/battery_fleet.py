"""Generic multi-battery monitoring and future-safe control primitives.

The default is deliberately read-only.  A battery may only receive commands when
both the global controller and the individual battery have explicit control
permission and the profile confirms SolarPilot is the exclusive owner.
"""
from __future__ import annotations
from dataclasses import dataclass
import math
import time

BATTERY_FLEET_DEFAULTS = {
    "enabled": False,
    "control_enabled": False,
    "strategy": "loads_first",  # loads_first | peak_shaving | hybrid | advisory
    "grid_target_w": 0.0,
    "charge_reserve_w": 150.0,
    "discharge_reserve_w": 100.0,
    "allow_grid_charge": False,
    "allow_export_discharge": False,
    "command_min_interval_s": 30.0,
    "settle_s": 30.0,
    "ack_timeout_s": 120.0,
    "target_tolerance_w": 250.0,
}

BATTERY_DEFAULTS = {
    "name": "Thuisbatterij",
    "enabled": True,
    "capacity_kwh": 10.0,
    "soc_entity": "",
    "power_entity": "",
    "power_sign": "discharge_positive",
    "min_soc_pct": 10.0,
    "reserve_soc_pct": 15.0,
    "max_soc_pct": 95.0,
    "max_charge_w": 5000.0,
    "max_discharge_w": 5000.0,
    "phase_hint": "unknown",
    "control_kind": "read_only",  # read_only | signed_number | scripts
    "control_enabled": False,
    "exclusive_control_confirmed": False,
    "number_entity": "",
    "number_sign": "discharge_positive",
    "charge_script": "",
    "discharge_script": "",
    "idle_script": "",
}


def finite(value):
    try:
        out = float(value)
        return out if math.isfinite(out) else None
    except (TypeError, ValueError):
        return None


@dataclass(frozen=True)
class BatteryReading:
    id: str
    name: str
    valid: bool
    soc_pct: float | None
    power_w: float | None  # positive = discharge to site, negative = charge from site
    capacity_kwh: float
    min_soc_pct: float
    reserve_soc_pct: float
    max_soc_pct: float
    max_charge_w: float
    max_discharge_w: float
    controllable: bool = False
    phase_hint: str = "unknown"

    @property
    def discharge_w(self):
        return 0.0 if self.power_w is None else max(0.0, self.power_w)

    @property
    def charge_w(self):
        return 0.0 if self.power_w is None else max(0.0, -self.power_w)

    @property
    def discharge_available_w(self):
        if not self.valid or self.soc_pct is None or self.soc_pct <= self.reserve_soc_pct:
            return 0.0
        return max(0.0, self.max_discharge_w)

    @property
    def charge_available_w(self):
        if not self.valid or self.soc_pct is None or self.soc_pct >= self.max_soc_pct:
            return 0.0
        return max(0.0, self.max_charge_w)


@dataclass(frozen=True)
class BatteryFleetRecommendation:
    valid: bool
    total_target_w: float = 0.0  # advisory target: positive discharge, negative charge
    allocations: dict[str, float] | None = None  # advisory allocation across valid batteries
    reason: str = "Geen batterijregeling"
    control_allocations: dict[str, float] | None = None  # only explicitly controllable batteries


def aggregate(readings):
    valid = [r for r in readings if r.valid]
    if not valid:
        return {
            "valid": False, "count": len(readings), "valid_count": 0,
            "capacity_kwh": 0.0, "soc_pct": None, "power_w": None,
            "discharge_w": 0.0, "charge_w": 0.0,
            "discharge_available_w": 0.0, "charge_available_w": 0.0,
        }
    cap = sum(max(0.0, r.capacity_kwh) for r in valid)
    weighted = sum((r.soc_pct or 0.0) * max(0.0, r.capacity_kwh) for r in valid)
    powers = [r.power_w for r in valid if r.power_w is not None]
    power = sum(powers) if len(powers) == len(valid) else None
    return {
        "valid": True, "count": len(readings), "valid_count": len(valid),
        "capacity_kwh": round(cap, 3),
        "soc_pct": None if cap <= 0 else round(weighted / cap, 2),
        "power_w": None if power is None else round(power, 1),
        "discharge_w": round(sum(r.discharge_w for r in valid), 1),
        "charge_w": round(sum(r.charge_w for r in valid), 1),
        "discharge_available_w": round(sum(r.discharge_available_w for r in valid), 1),
        "charge_available_w": round(sum(r.charge_available_w for r in valid), 1),
    }


def _allocate(readings, request_w, *, controllable_only=False):
    """Allocate a signed fleet request. Charge lowest SOC first, discharge highest first."""
    if abs(request_w) < 1:
        return {r.id: 0.0 for r in readings}
    charging = request_w < 0
    candidates = [r for r in readings if r.valid and (r.controllable or not controllable_only) and
                  ((r.charge_available_w > 0) if charging else (r.discharge_available_w > 0))]
    candidates.sort(key=lambda r: (r.soc_pct if r.soc_pct is not None else 50.0), reverse=not charging)
    remaining = abs(request_w)
    out = {r.id: 0.0 for r in readings}
    for r in candidates:
        limit = r.charge_available_w if charging else r.discharge_available_w
        take = min(remaining, limit)
        out[r.id] = -take if charging else take
        remaining -= take
        if remaining <= 1:
            break
    return out


def recommend(settings, readings, grid_w, capacity_allowed_grid_w=None):
    """Recommend battery power without bypassing load, SoC or capacity guards.

    `grid_w`: positive import, negative export.  The result is advisory unless
    explicit battery control is enabled elsewhere.
    """
    c = {**BATTERY_FLEET_DEFAULTS, **(settings or {})}
    if not c["enabled"]:
        return BatteryFleetRecommendation(False, reason="Batterijvloot uitgeschakeld")
    grid = finite(grid_w)
    if grid is None:
        return BatteryFleetRecommendation(False, reason="Netmeting ongeldig; geen batterijadvies")
    agg = aggregate(readings)
    if not agg["valid"]:
        return BatteryFleetRecommendation(False, reason="Geen geldige batterijmetingen")

    strategy = c.get("strategy", "loads_first")
    target = 0.0
    reason = "Batterij in rust"
    export = max(0.0, -grid)
    imp = max(0.0, grid)
    goal = float(c.get("grid_target_w", 0.0))

    # Loads-first / hybrid: use only the residual after ordinary flexible loads.
    # `goal` permits an intentional small import/export bias without changing the
    # deterministic appliance controller.
    if strategy in ("loads_first", "hybrid", "advisory"):
        if grid < goal - float(c["charge_reserve_w"]):
            request = (goal - float(c["charge_reserve_w"])) - grid
            target = -min(max(0.0, request), agg["charge_available_w"])
            reason = f"Netvermogen {grid:.0f} W ligt onder batterijdoel: batterij kan laden"
        elif grid > goal + float(c["discharge_reserve_w"]):
            request = grid - (goal + float(c["discharge_reserve_w"]))
            target = min(max(0.0, request), agg["discharge_available_w"])
            reason = f"Netvermogen {grid:.0f} W ligt boven batterijdoel: batterij kan ontladen"

    # Peak shaving can be a dedicated strategy or an extra requirement in hybrid.
    cap = finite(capacity_allowed_grid_w)
    if strategy in ("peak_shaving", "hybrid") and cap is not None and grid > cap:
        needed = min(grid - cap, agg["discharge_available_w"])
        if needed > target:
            target = needed
            reason = f"Kwartierpiekbudget vraagt ongeveer {needed:.0f} W batterijontlading"
    if strategy == "peak_shaving" and target == 0 and export > float(c["charge_reserve_w"]):
        target = -min(export - float(c["charge_reserve_w"]), agg["charge_available_w"])
        reason = f"Buiten piekbeperking: resterende injectie {export:.0f} W kan batterij laden"

    if target < 0 and grid > 0 and not c.get("allow_grid_charge"):
        target = 0.0
        reason = "Netladen niet toegestaan"
    if target > 0 and grid < 0 and not c.get("allow_export_discharge"):
        target = min(target, max(0.0, grid + target)) if target + grid > 0 else 0.0
        if target <= 0:
            reason = "Ontladen naar het net niet toegestaan"

    advisory_alloc = _allocate(readings, target, controllable_only=False)
    control_alloc = _allocate(readings, target, controllable_only=True)
    advisory_target = sum(advisory_alloc.values())
    return BatteryFleetRecommendation(True, advisory_target, advisory_alloc, reason, control_alloc)


class BatteryFleetState:
    """Small persisted command journal used by the runtime adapter."""
    def __init__(self):
        self.last_command_mono = 0.0
        self.pending = None
        self.faults = {}
        self.last_recommendation = None

    def snapshot(self):
        # monotonic timestamps are not restored as deadlines; pending is review-only.
        return {"pending": self.pending, "faults": dict(self.faults)}

    def restore(self, data):
        if not isinstance(data, dict):
            return
        self.faults = dict(data.get("faults", {}))
        if data.get("pending"):
            self.faults["restart"] = "Batterijopdracht was bezig tijdens herstart; handmatige controle vereist"
        self.pending = None
        self.last_command_mono = time.monotonic()
