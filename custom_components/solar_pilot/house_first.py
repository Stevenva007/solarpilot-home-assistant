"""Indirect, explicitly bounded allocation from an autonomous solar EV charger.

EV watts are conditional transferable watts, NEVER actual free export. This
module has no HA services. The runtime verifies one metered handover at a time.
"""
from __future__ import annotations
from collections import deque
from dataclasses import dataclass
import math
from .wallbox import (
    WALLBOX_DEFAULTS, GuardResult, Reading, confirmed_no_active_request, state_set,
)

HOUSE_DEFAULTS = {
    "handover_s": 240, "handover_confirm_s": 15, "handover_import_w": 100,
    "reclaim_max_age_s": 120, "max_takeover_w": 2500,
}


class HouseFirstGuard:
    def __init__(self, settings):
        self.settings = {**WALLBOX_DEFAULTS, **HOUSE_DEFAULTS, **settings}
        self.result = GuardResult()
        self.reading = Reading()
        self.history = deque(maxlen=10000)
        self.last_action = -1e12
        self.last_action_wall = 0.0
        self.invalid_since = None
        self.cooldown_until = 0.0
        self.conflict_count = 0
        self.reclaimable_w = 0.0

    def note_action(self, now, wall_time, old_w, new_w):
        self.history.clear()
        self.last_action = now
        self.last_action_wall = wall_time

    def update(self, now, reading, grid_w, reserve_w, discharge_w=0.0):
        self.reading = reading
        self.reclaimable_w = 0.0
        c, r = self.settings, reading
        if not c["enabled"]:
            self.result = GuardResult()
            return self.result
        if not r.valid:
            if self.invalid_since is None:
                self.invalid_since = now
            self.history.clear()
            # Do not pretend the EV is off. No new starts. Existing own loads
            # stay subject to actual grid/battery limits in the normal engine.
            self.result = GuardResult("unavailable", r.issue or "Wallbox-metingen niet betrouwbaar", True,
                                      False, 0, r.issue or "Geen vermogen van Wallbox overnemen")
            return self.result
        self.invalid_since = None
        if confirmed_no_active_request(r, c):
            self.history.clear(); self.cooldown_until = 0.0
            self.result = GuardResult(
                "idle", "Geen actieve Wallbox-laadvraag: geen vermogen gereserveerd"
            )
            return self.result
        if r.mode in ("manual", "unknown", "stopped"):
            self.history.clear(); self.cooldown_until = 0.0
            self.result = GuardResult(r.mode, r.session_reason or "Geen autonome zonnelaadsessie: alleen echte injectie", warning=r.session_reason if r.mode == "unknown" else "")
            return self.result
        full_solar = r.mode is not None and r.mode.casefold() in state_set(c["full_solar_states"])
        fresh = r.age_s <= c["reclaim_max_age_s"]
        warning = "" if full_solar else "Full solar niet bevestigd: geen laadvermogen overnemen; alleen echte injectie gebruiken."
        if not fresh:
            warning = "Wallbox-rapport te oud voor overname: alleen echte injectie gebruiken."
        if grid_w is None or not math.isfinite(grid_w):
            self.history.clear()
            self.result = GuardResult("settling", "Wacht op betrouwbare netmeting", True, False, 0, warning)
            return self.result
        # Retaining an owned load may consider EV watts even while new starts
        # wait for stability. It is always limited by the actual import ceiling.
        credit = max(0, r.power_w or 0) if full_solar and fresh and r.demand is not False else 0.0
        residual = max(0, -grid_w - reserve_w - max(0, discharge_w))
        pool = max(0, -grid_w - reserve_w - max(0, discharge_w) + credit)
        if now < self.cooldown_until:
            self.history.clear()
            self.result = GuardResult("cooldown", "Overname niet bevestigd: rustperiode voor nieuwe starts", True,
                                      False, 0, warning, math.ceil(self.cooldown_until-now))
            return self.result
        if self.history and now - self.history[-1][0] > c.get("sample_gap_s", 30):
            self.history.clear()
        self.history.append((now, pool, credit))
        cutoff = now - c["stable_s"]
        while len(self.history) > 1 and self.history[1][0] <= cutoff:
            self.history.popleft()
        self.reclaimable_w = min(v[2] for v in self.history)
        elapsed = now - self.history[0][0]
        ready = elapsed >= c["stable_s"] and now-self.last_action >= c["stable_s"]
        if not ready or r.stamp <= self.last_action_wall:
            self.result = GuardResult("settling", "Andere toestellen eerst; wacht op stabiele metingen", True, False,
                                      0, warning, math.ceil(max(0, c["stable_s"]-elapsed, c["stable_s"]-(now-self.last_action))))
            return self.result
        capacity = min(v[1] for v in self.history)
        # Actual residual is not transferable debt and need not use the transfer cap.
        capacity = min(capacity, max(residual, residual + c["max_takeover_w"]))
        self.result = GuardResult("house_first", "Andere toestellen eerst; Wallbox gebruikt het resterende overschot",
                                  capacity <= 0, False, capacity, warning)
        return self.result


@dataclass
class Handover:
    """One physical transfer. Completion needs several independent observations."""
    device_id: str
    old_w: float
    new_w: float
    borrowed_w: float
    ev_before_w: float
    issued: float
    wall_time: float
    timeout_s: float
    baseline_grid_stamp: float = 0.0
    status: str = "waiting"
    reason: str = "Wacht op terugregeling Wallbox en stabiele netmeting"
    good_since: float | None = None
    first_good_stamp: float = 0.0
    outcome_recorded: bool = False

    def evaluate(self, now, *, grid_w, grid_stamp, reading, measured_w, measured_stamp,
                 available, allowed, discharge_w, ceiling_w, import_tolerance_w, confirm_s):
        if self.status != "waiting":
            return
        if not allowed or not available or grid_w is None or not reading.valid:
            self.fail("Overname afgebroken: vrijgave of betrouwbare meting ontbreekt")
            return
        if grid_w > ceiling_w:
            self.fail("Overname afgebroken: netafnamegrens overschreden")
            return
        if now-self.issued >= self.timeout_s:
            self.fail("Overname niet tijdig bevestigd; eigen verhoging terugnemen")
            return
        # Fresh EV feedback must show enough reduction, not only a new timestamp.
        dropped = self.ev_before_w - (reading.power_w or 0)
        meter_ready = measured_w >= max(0.8*self.new_w, self.new_w-150)
        good = (grid_stamp > self.wall_time and measured_stamp > self.wall_time
                and reading.stamp > self.wall_time and meter_ready
                and dropped >= max(0, self.borrowed_w-import_tolerance_w)
                and grid_w <= import_tolerance_w and discharge_w <= 1)
        if not good:
            self.good_since = None
            self.first_good_stamp = 0.0
        elif self.good_since is None:
            self.good_since = now
            self.first_good_stamp = grid_stamp
        elif now-self.good_since >= confirm_s and grid_stamp > self.first_good_stamp:
            self.status = "success"
            self.reason = "Overname bevestigd: toestel verbruikt, Wallbox teruggeregeld, netmeting stabiel"

    def fail(self, reason):
        self.status, self.reason = "rollback", reason
        self.good_since = None

    def overview(self, now):
        return {"device_id": self.device_id, "state": self.status, "reason": self.reason,
                "borrowed_w": round(self.borrowed_w, 1), "previous_target_w": self.old_w,
                "remaining_s": max(0, math.ceil(self.timeout_s-(now-self.issued)))}
