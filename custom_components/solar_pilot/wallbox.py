"""Read-only external-charger coordination. No service calls or API polling.

In this Wallbox-first guard, EV power never enters the allocation budget.
House-first conditional transfers are handled separately in house_first.py.
This guard only constrains SolarPilot's own loads. Delayed telemetry cannot
provide a guarantee of zero transient import or identify a causal conflict.
"""
from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import math

WALLBOX_DEFAULTS = {
    "enabled": False,
    "policy": "priority",
    "name": "Wallbox",
    "stale_s": 300,
    "stable_s": 180,
    "cooldown_s": 600,
    "fault_grace_s": 30,
    "charging_threshold_w": 50,
    "drop_tolerance_w": 250,
    "demand_states": "Charging;Waiting in queue by Eco-Smart;Waiting for green energy;Waiting in queue by Power Boost",
    "idle_states": "Ready;Paused;Scheduled;Waiting for car demand;Locked;Locked, car connected",
    "full_solar_states": "full_solar;Full solar;Full green",
}
READ_KEYS = ("power_entity", "status_entity", "demand_entity", "mode_entity")
CONTROL_KEYS = ("control_entity", "number_entity", "start_script", "stop_script")


def state_set(value: str) -> set[str]:
    """Semicolons, not commas: Wallbox has 'Locked, car connected'."""
    return {part.strip().casefold() for part in value.split(";") if part.strip()}


def protected_entity(hass, settings: dict, entity_id: str | None) -> bool:
    """Block direct calls to configured read entities and their HA devices.

    This cannot inspect the internals of arbitrary scripts or other automations.
    """
    if not settings.get("enabled") or not entity_id:
        return False
    references = {settings.get(k) for k in READ_KEYS} - {None, ""}
    if entity_id in references:
        return True
    from homeassistant.helpers import entity_registry as er
    lookup = getattr(er.async_get(hass), "async_get", lambda _: None)
    target = lookup(entity_id)
    device_id = getattr(target, "device_id", None)
    if not device_id:
        return False
    return any(getattr(lookup(ref), "device_id", None) == device_id for ref in references)


def conflicting_devices(hass, settings: dict, devices: list[dict]) -> list[str]:
    if not settings.get("enabled"):
        return []
    return [d["id"] for d in devices if (
        d.get("power_entity") == settings.get("power_entity")
        or any(protected_entity(hass, settings, d.get(k)) for k in CONTROL_KEYS)
    )]


@dataclass(frozen=True)
class Reading:
    power_w: float | None = None
    stamp: float = 0.0
    demand: bool | None = None
    status: str | None = None
    mode: str | None = None
    valid: bool = False
    issue: str = ""
    age_s: float = 0.0


@dataclass(frozen=True)
class GuardResult:
    state: str = "disabled"
    reason: str = "Wallbox-monitor uitgeschakeld"
    block_increase: bool = False
    release_flexible: bool = False
    max_increase_w: float | None = None
    warning: str = ""
    remaining_s: int = 0


class WallboxGuard:
    """Conservative Wallbox-first policy, independent of Home Assistant."""

    def __init__(self, settings: dict):
        self.settings = {**WALLBOX_DEFAULTS, **settings}
        self.result = GuardResult()
        self.reading = Reading()
        self.history: deque[tuple[float, float]] = deque(maxlen=10000)
        self.phase = None
        self.anchor_w = None
        self.invalid_since = None
        self.cooldown_until = 0.0
        self.last_action = -1e12
        self.last_action_wall = 0.0
        self.watch = None
        self.conflict_count = 0

    def note_action(self, now: float, wall_time: float, old_w: float, new_w: float):
        """Called only for a SolarPilot-controlled appliance, never the EV."""
        self.history.clear()
        self.last_action = now
        self.last_action_wall = wall_time
        # A reduction also needs fresh settling; retain any earlier watch until
        # the EV feedback is known, rather than overwriting its higher baseline.
        if new_w > old_w + 0.5 and self.reading.valid:
            self.watch = {"power_w": self.reading.power_w or 0.0,
                          "now": now, "wall_time": wall_time}

    def update(self, now: float, reading: Reading, grid_w: float | None,
               reserve_w: float, discharge_w: float = 0.0) -> GuardResult:
        self.reading = reading
        result = self._evaluate(now, reading, grid_w, reserve_w, discharge_w)
        self.result = result
        return result

    def _evaluate(self, now, r, grid, reserve, discharge):
        c = self.settings
        if not c["enabled"]:
            return GuardResult()
        priority = c["policy"] == "priority"
        warning = ""
        if c.get("mode_entity"):
            if r.mode is None:
                warning = "Zonnelaadmodus niet beschikbaar; alleen groene stroom niet bevestigd."
            elif r.mode.casefold() not in state_set(c["full_solar_states"]):
                warning = "Wallbox meldt geen Full solar; netstroom kan worden gebruikt."
        else:
            warning = "Zonnelaadmodus niet gekoppeld; alleen groene stroom niet geverifieerd."

        if not r.valid:
            if self.invalid_since is None:
                self.invalid_since = now
            self.history.clear()
            self.phase = None
            release = now - self.invalid_since >= c["fault_grace_s"]
            return GuardResult("unavailable", r.issue or "Wallbox-metingen onbetrouwbaar",
                               priority, priority and release, 0.0 if priority else None,
                               r.issue or "Wallbox-metingen onbetrouwbaar")
        self.invalid_since = None
        charging = (r.power_w or 0) >= c["charging_threshold_w"]
        phase = "charging" if charging else "waiting" if r.demand else "idle"
        if not priority:
            self.history.clear()
            self.watch = None
            return GuardResult(phase, "Alleen monitoren: geen invloed op toestelprioriteiten", warning=warning)

        # Detect a possible interaction, not its cause. Cloud cover can produce
        # the same observation. Yielding our own loads is intentionally cautious.
        if self.watch and r.stamp > self.watch["wall_time"]:
            if self.watch["power_w"] - (r.power_w or 0) >= c["drop_tolerance_w"]:
                self.cooldown_until = now + c["cooldown_s"]
                self.conflict_count += 1
                self.watch = None
                self.history.clear()
            elif now - self.watch["now"] >= c["stable_s"]:
                self.watch = None

        if now < self.cooldown_until:
            return GuardResult("cooldown", "Mogelijke wisselwerking: eigen flexibele lasten terugnemen",
                               True, True, 0.0, warning,
                               math.ceil(self.cooldown_until - now))
        if phase != self.phase:
            self.history.clear()
            self.phase = phase
            self.anchor_w = r.power_w
        # Significant EV modulation restarts the rest-surplus observation window.
        if self.anchor_w is None or abs((r.power_w or 0) - self.anchor_w) >= c["drop_tolerance_w"]:
            self.history.clear()
            self.anchor_w = r.power_w or 0.0
        if phase == "waiting":
            self.history.clear()
            return GuardResult("waiting", "Wallbox wacht op zon: eigen flexibele lasten geven voorrang",
                               True, True, 0.0, warning)
        if grid is None or not math.isfinite(grid):
            self.history.clear()
            return GuardResult("settling", "Wacht op betrouwbare netmeting", True, False, 0.0, warning)

        # Net power already includes EV consumption. Neither add nor subtract it
        # again here. Only residual export, net of the reserve/storage, is usable.
        residual = max(0.0, -grid - reserve - max(0.0, discharge))
        if self.history and now - self.history[-1][0] > c.get("sample_gap_s", 30):
            self.history.clear()
        self.history.append((now, residual))
        cutoff = now - c["stable_s"]
        # Retain one sample at or before cutoff to cover the entire window.
        while len(self.history) > 1 and self.history[1][0] <= cutoff:
            self.history.popleft()
        elapsed = now - self.history[0][0]
        ready = elapsed >= c["stable_s"] and now - self.last_action >= c["stable_s"]
        if not ready:
            return GuardResult("settling", "Wallbox krijgt reactietijd; wacht op stabiel restoverschot",
                               True, False, 0.0, warning,
                               math.ceil(max(c["stable_s"] - elapsed,
                                             c["stable_s"] - (now - self.last_action), 0)))
        if r.stamp <= self.last_action_wall:
            return GuardResult("settling", "Wacht op nieuw Wallbox-rapport na eigen opdracht",
                               True, False, 0.0, warning)
        # Inactivity also has a confirmation delay, but once confirmed we need
        # not reserve energy for a car which is not requesting a charge.
        if phase == "idle":
            return GuardResult("idle", "Geen actieve laadvraag; gewone toestelprioriteiten", warning=warning)
        limit = min(value for _, value in self.history)
        return GuardResult("charging", "Wallbox regelt zelf; alleen stabiel restoverschot vrijgeven",
                           limit <= 0, False, round(limit, 2), warning)
