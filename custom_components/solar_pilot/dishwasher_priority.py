"""Preference for one protected wash cycle before optional SG boost.

This does not control the EVSE and NEVER turns EV watts into electrical capacity.
A start using currently EV-consumed solar is an irreversible cycle allocation,
not the rollback-capable handover for interruptible loads. It requires a valid
Full Solar report, actual PV, raw+filtered grid headroom and the configured
physical limits. Unexpected grid use is reported, never 'fixed' by stopping a
washing programme. All clocks/meters are supplied by the runtime.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math
from .wallbox import state_set

PRIORITY_DEFAULTS = {
    "dishwasher_priority_enabled": True,
    "dishwasher_ev_solar_priority": True,
}
PRIORITY_LABEL = "Beschermde afwasmachine → Wallbox / lagere lasten / SG-zonneboost"

def enabled(cfg):
    return cfg.get("kind") == "dishwasher" and cfg.get("dishwasher_priority_enabled", True) is True

def number(value):
    try:
        v = float(value)
        return v if math.isfinite(v) else None
    except (TypeError, ValueError):
        return None

@dataclass
class PriorityView:
    candidate_ids: set[str] = field(default_factory=set)
    active_ids: set[str] = field(default_factory=set)
    fitting_ids: set[str] = field(default_factory=set)
    stable_ids: set[str] = field(default_factory=set)
    holds: dict[str, str] = field(default_factory=dict)
    blocks: dict[str, str] = field(default_factory=dict)
    ev_credit: dict[str, float] = field(default_factory=dict)
    start_power: dict[str, dict] = field(default_factory=dict)
    luxury_block: bool = False
    reason: str = "Geen afwasbeurt vraagt voorrang"

class DishwasherPriority:
    """Small bounded runtime state; no service calls, polling or meter invention."""
    def __init__(self):
        self.view = PriorityView()
        self.since: dict[str, float] = {}
        self.last_now = None
        self.watches: dict[str, dict] = {}
        self.ev_blocks: dict[str, str] = {}

    def snapshot(self):
        return {"watches": self.watches, "ev_blocks": self.ev_blocks}

    def restore(self, data, configs):
        if not isinstance(data, dict):
            return
        self.watches = {i: dict(v) for i, v in data.get("watches", {}).items()
                        if i in configs and enabled(configs[i]) and isinstance(v, dict)
                        and number(v.get("issued_wall")) is not None}
        self.ev_blocks = {i: str(v) for i, v in data.get("ev_blocks", {}).items()
                          if i in configs and isinstance(v, str)}
        self.since.clear()  # Stable sun may not be replayed across a restart.

    def evaluate(self, *, now, wall, mode, configs, devices, states, permitted_ids,
                 actual_grid, filtered_grid, pv_w, discharge_w, reserve_w,
                 max_import_w, reading, wallbox_settings, stable_ev_credit_w,
                 lower_measured, comfort_reserve_w=0, comfort_block="", sample_gap_s=30,
                 site_ready=True):
        out = PriorityView()
        if self.last_now is not None and (now < self.last_now or now-self.last_now > sample_gap_s):
            self.since.clear()
        self.last_now = now
        preferred = {i for i, c in configs.items() if enabled(c)}
        self.since = {i: v for i, v in self.since.items() if i in preferred}
        out.active_ids = {i for i in preferred if states[i].on or i in self.watches}
        # No automatic-preference intervention during Pause/Observe. Running
        # physical cycles remain a reserved load, not an absolute 60 °C veto.
        if mode != "solar":
            self.since.clear(); self.view = out; return out
        eligible = {i for i in preferred if i in permitted_ids and not states[i].on
                    and states[i].enabled and states[i].available and not states[i].fault
                    and states[i].demand and states[i].interlock and states[i].cycle_armed
                    and states[i].manual_until <= now
                    and now-states[i].last_off >= devices[i].min_off_s}
        out.candidate_ids = eligible
        if comfort_block:
            out.blocks = {i: comfort_block for i in eligible}
            self.since.clear(); self.view = out; return out
        values = [number(v) for v in (actual_grid, filtered_grid, pv_w, discharge_w, max_import_w, comfort_reserve_w)]
        if not site_ready or any(v is None for v in values) or pv_w < 0 or discharge_w < 0:
            self.since.clear(); self.view = out; return out
        credit = 0.0
        wc = wallbox_settings
        if (wc.get("enabled") and reading.valid and reading.connected is not False
                and reading.demand is not False and reading.age_s <= wc.get("reclaim_max_age_s", 120)
                and (reading.mode or "").casefold() in state_set(wc.get("full_solar_states", "full_solar"))):
            credit = max(0.0, min(number(stable_ev_credit_w) or 0.0,
                                  number(reading.power_w) or 0.0,
                                  number(wc.get("max_takeover_w", 2500)) or 0.0))
        # Only metered own interruptible loads may be treated as releasable.
        # They remain physically in P1 until their OFF confirmation + fresh P1.
        low = {i: max(0.0, v) for i, v in lower_measured.items()
               if i not in preferred and i in states and states[i].owned and states[i].on
               and not devices[i].non_interruptible and not states[i].manual_forced
               and states[i].boost_until <= now and not states[i].deadline_force
               and not states[i].planner_grid_force
               and states[i].available and not states[i].fault}
        for i in sorted(eligible, key=lambda k: (devices[k].priority, k)):
            d = devices[i]
            ranked = configs[i].get("_priority_board_rank")
            candidate_low = {j: watts for j, watts in low.items()
                             if ranked is None or configs[j].get("_priority_board_rank", -1) > ranked}
            own_low = sum(candidate_low.values())
            # Consumption is already in P1; reserve only unconsumed commitments.
            other_commitment = sum(max(0.0, s.target_w-s.measured_w) for j, s in states.items()
                                   if s.owned and s.on and j not in candidate_low)
            free = -max(actual_grid, filtered_grid)-discharge_w-reserve_w-other_commitment-comfort_reserve_w
            cap_after_release = max_import_w-actual_grid+own_low-other_commitment-comfort_reserve_w
            allowed_credit = credit if (configs[i].get("dishwasher_ev_solar_priority", True)
                                         and i not in self.ev_blocks) else 0.0
            # Actual PV is a hard ceiling for the attribution, not a forecast.
            potential = min(max(0.0, pv_w-discharge_w-reserve_w), free+own_low+allowed_credit)
            # Diagnostic snapshot of these exact inputs, including a pool that
            # is still too small. Do not promote it to a command allocation:
            # EV credit below the fit gate must remain absent from ev_credit.
            out.start_power[i] = {
                "available_solar_w": round(max(0.0, potential), 1),
                "net_solar_after_reserves_w": round(free, 1),
                "wallbox_solar_w": round(allowed_credit, 1),
                "lower_loads_releasable_w": round(own_low, 1),
                "pv_ceiling_w": round(max(0.0, pv_w-discharge_w-reserve_w), 1),
                "comfort_reserve_w": round(comfort_reserve_w, 1),
                "unconsumed_commitment_w": round(other_commitment, 1),
                "import_headroom_after_release_w": round(max(0.0, cap_after_release), 1),
                "required_start_w": round(d.minimum+d.start_margin_w, 1),
                "source": "dishwasher_priority.evaluate",
                "not_a_start_guarantee": True,
            }
            due = states[i].deadline_force
            fits = cap_after_release >= d.minimum and (due or potential >= d.minimum+d.start_margin_w)
            if not fits:
                self.since.pop(i, None)
                continue  # Tiny residuals can still be used by the dehumidifier.
            # A ready idle/pending cycle that fits gets one start opportunity
            # before optional SG boost. Active protected cycles retain their
            # measured or unmetered future draw in the runtime budget.
            out.fitting_ids.add(i)
            out.luxury_block = True
            out.reason = "Afwasmachine past in de veilige startpool en krijgt eerst startkans vóór SG-zonneboost"
            self.since.setdefault(i, now)
            if due or now-self.since[i] >= d.start_delay_s:
                out.stable_ids.add(i)
                # Release only what is needed, not every low-priority load.
                missing = max(0.0, d.minimum+(0 if due else d.start_margin_w)
                              - (max_import_w-actual_grid-other_commitment-comfort_reserve_w if due else free+allowed_credit))
                for j in sorted(candidate_low, key=lambda k: (devices[k].priority, k), reverse=True):
                    if missing <= 0:
                        break
                    out.holds[j] = "Afwasmachine heeft voorrang; veilig vrijgeven na minimumlooptijd"
                    missing -= candidate_low[j]
            if allowed_credit > 0 and not due:
                out.ev_credit[i] = allowed_credit
            # One stable priority claimant consumes this potential pool. Other
            # dishwashers are re-evaluated on a fresh tick after the serial action.
            break
        for i in set(self.since)-eligible:
            self.since.pop(i, None)
        self.view = out
        return out

    def started(self, i, wall, borrowed, ev_w):
        if borrowed > 0:
            self.watches[i] = {"issued_wall": wall, "borrowed_w": borrowed,
                               "ev_before_w": ev_w, "status": "waiting",
                               "reason": "Afwas gestart met zonnevermogen dat Wallbox gebruikte; netto reactie wordt gecontroleerd",
                               "good_since": None, "notified": False}

    def observe(self, *, wall, readings, grid_w, grid_stamp, wb, tolerance=100, timeout_s=900):
        """Observe net balance, NOT a claimed causal or metered appliance handover.

        Never cancels an irreversible cycle. Returning messages lets the runtime
        warn once. A failed sharing attempt is blocked until operator review.
        """
        messages = []
        for i, watch in list(self.watches.items()):
            r = readings.get(i)
            if r and r.finished:
                self.watches.pop(i, None); continue
            if watch.get("status") != "waiting":
                continue
            issued = watch["issued_wall"]
            if (r and r.active and getattr(r, "stamp", 0) > issued and wb.valid and wb.stamp > issued and grid_w is not None
                    and grid_stamp > issued and grid_w <= tolerance):
                if watch.get("good_since") is None:
                    watch["good_since"] = wall
                    watch["first_grid_stamp"] = grid_stamp
                elif wall-watch["good_since"] >= 30 and grid_stamp > watch.get("first_grid_stamp", grid_stamp):
                    watch["status"] = "balanced"
                    watch["reason"] = "Nieuwe afwasstatus en netto energiebalans bevestigd; geen bewijs van exclusief gemeten fasevermogen"
            else:
                watch["good_since"] = None
            if watch["status"] == "waiting" and wall-issued >= timeout_s:
                watch["status"] = "attention"
                watch["reason"] = "Wallbox/afwas-nettobalans niet tijdig bevestigd. Beurt blijft afwerken; nieuwe voorrangsstarts op EV-vermogen geblokkeerd tot controle."
                self.ev_blocks[i] = watch["reason"]
                messages.append((i, watch["reason"]))
                watch["notified"] = True
        return messages

    def overview(self, i):
        return {"enabled": i in self.view.candidate_ids or i in self.view.active_ids,
                "order": PRIORITY_LABEL, "solar_stable": i in self.view.stable_ids,
                "conditional_ev_w": round(self.view.ev_credit.get(i, 0), 1),
                "start_power": dict(self.view.start_power.get(i, {})),
                "reason": self.view.blocks.get(i, self.view.reason),
                "wallbox_response": dict(self.watches.get(i, {})),
                "ev_start_block": self.ev_blocks.get(i, ""),
                "profile_planning": "Wacht op exclusieve Shelly-meter en latere faseprofiel-update"}
