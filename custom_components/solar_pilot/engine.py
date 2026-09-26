"""Deterministic planning engine. Pure Python, independently testable.

Sign convention: grid > 0 = import; battery discharge > 0.
An allocation is NOT an instruction to assume a device has changed state.
The runtime must verify feedback and a new grid sample after every command.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import math


@dataclass(frozen=True)
class Device:
    id: str
    name: str = "Device"
    kind: str = "switch"
    priority: int = 50
    nominal_w: float = 1000.0
    min_units: float = 6.0
    max_units: float = 16.0
    step_units: float = 1.0
    watts_per_unit: float = 230.0
    start_delay_s: float = 60.0
    stop_delay_s: float = 60.0
    min_on_s: float = 180.0
    min_off_s: float = 180.0
    start_margin_w: float = 100.0
    non_interruptible: bool = False
    max_on_s: float = 14400.0
    min_daily_runtime_s: float = 0.0
    max_daily_runtime_s: float = 0.0
    daily_deadline: str = "23:59:00"
    deadline_grid_allowed: bool = False
    allow_wallbox_reclaim: bool = False

    @property
    def minimum(self) -> float:
        return self.min_units * self.watts_per_unit if self.kind == "number" else self.nominal_w

    @property
    def maximum(self) -> float:
        return self.max_units * self.watts_per_unit if self.kind == "number" else self.nominal_w

    def quantize(self, watts: float) -> float:
        if not math.isfinite(watts) or watts + 1e-7 < self.minimum:
            return 0.0
        if self.kind != "number":
            return self.nominal_w
        units = min(self.max_units, watts / self.watts_per_unit)
        steps = math.floor((units - self.min_units + 1e-8) / self.step_units)
        return round((self.min_units + steps * self.step_units) * self.watts_per_unit, 6)


@dataclass
class State:
    owned: bool = False
    on: bool = False
    available: bool = True
    enabled: bool = True
    demand: bool = True
    interlock: bool = True
    measured_w: float = 0.0
    target_w: float = 0.0
    last_on: float = -1e12
    last_off: float = -1e12
    start_since: float | None = None
    stop_since: float | None = None
    manual_until: float = 0.0
    boost_until: float = 0.0
    fault: str = ""
    cycle_armed: bool = True
    daily_runtime_s: float = 0.0
    daily_energy_kwh: float = 0.0
    deadline_urgent: bool = False
    deadline_force: bool = False
    planner_hold: bool = False
    planner_reason: str = ""
    planner_grid_force: bool = False
    observed_once: bool = False


@dataclass(frozen=True)
class Site:
    now: float
    grid_w: float
    filtered_grid_w: float
    valid: bool = True
    mode: str = "solar"
    reserve_w: float = 150.0
    max_import_w: float = 3500.0
    battery_discharge_w: float = 0.0
    battery_ready: bool = True
    fault_elapsed_s: float = 0.0
    fault_grace_s: float = 30.0
    can_increase: bool = True
    external_hold: bool = False
    external_reason: str = ""
    increase_reason: str = ""
    max_increase_w: float | None = None
    device_increase_limits: dict[str, float] = field(default_factory=dict)
    reclaimable_w: float = 0.0
    max_takeover_w: float = 2500.0
    handover_s: float = 240.0
    handover_device: str = ""
    handover_target_w: float = 0.0
    bridge_w: float = 0.0
    rollback_device: str = ""
    rollback_target_w: float = 0.0
    rollback_reason: str = ""


@dataclass(frozen=True)
class Action:
    id: str
    watts: float
    reason: str
    reclaimed_w: float = 0.0


@dataclass
class Plan:
    budget_w: float = 0.0
    free_w: float = 0.0
    targets: dict[str, float] = field(default_factory=dict)
    reasons: dict[str, str] = field(default_factory=dict)
    action: Action | None = None


def plan(site: Site, devices: list[Device], states: dict[str, State]) -> Plan:
    """Plan one serialized command, preserving locks and physical headroom.

    Lower priority numbers win. A load too large to fit can be skipped.
    Borrowed power from storage never counts as solar surplus. A boost may
    intentionally use grid power, but not bypass demand, interlock or timing.
    """
    out = Plan()
    owned_w = sum(max(0, states[d.id].measured_w) for d in devices
                  if states[d.id].owned and states[d.id].on)
    # The conservative raw/filtered minimum prevents smoothing-created headroom.
    grid = max(site.grid_w, site.filtered_grid_w)
    # Conditional EV watts affect solar allocation only, NEVER physical headroom.
    credit = max(0.0, site.reclaimable_w, site.bridge_w)
    solar_budget = owned_w - grid - max(0, site.battery_discharge_w) - site.reserve_w + credit
    cap_budget = owned_w - site.grid_w + site.max_import_w
    out.budget_w = round(max(0.0, solar_budget), 2)
    out.free_w = round(max(0.0, -site.grid_w - site.battery_discharge_w - site.reserve_w), 2)
    blocked_site = site.mode == "paused" or not site.valid or not site.battery_ready or site.external_hold
    emergency = site.valid and site.grid_w > site.max_import_w
    remaining_solar, remaining_cap = solar_budget, cap_budget
    locked: set[str] = set()
    sorted_devices = sorted(devices, key=lambda d: (
        0 if (states[d.id].boost_until > site.now or states[d.id].deadline_urgent) else d.priority, d.id))

    for d in sorted_devices:
        s = states[d.id]
        out.targets[d.id] = 0.0
        handover_lock = (site.handover_device == d.id and s.owned and s.on
                         and site.valid and not emergency and not blocked_site
                         and s.enabled and s.demand and s.interlock and not s.fault)
        if s.owned and s.on and (d.non_interruptible or site.now - s.last_on < d.min_on_s or handover_lock):
            # A number load may be reduced to its valid minimum while running.
            amount = (site.handover_target_w if handover_lock else
                      d.minimum if d.kind == "number" and not d.non_interruptible else max(d.minimum, s.target_w))
            out.targets[d.id] = amount
            remaining_solar -= amount
            remaining_cap -= amount
            locked.add(d.id)
            out.reasons[d.id] = ("Gecontroleerde overname: Wallbox krijgt reactietijd" if handover_lock else
                                 "Cyclus laten afwerken" if d.non_interruptible else "Minimale looptijd")

    for d in sorted_devices:
        s = states[d.id]
        if d.id in locked:
            # A minimum run time prohibits stopping, not useful modulation.
            # Allocate additional headroom to a running variable load in priority
            # order while preserving its minimum already reserved above.
            if (d.kind == "number" and d.id != site.handover_device and not d.non_interruptible and not blocked_site
                    and s.available and s.enabled and s.demand and s.interlock
                    and not s.fault and s.manual_until <= site.now):
                boost = s.boost_until > site.now
                extra = remaining_cap if boost else min(remaining_solar, remaining_cap)
                previous = out.targets[d.id]
                amount = d.quantize(previous + max(0, extra))
                out.targets[d.id] = amount
                remaining_solar -= amount - previous
                remaining_cap -= amount - previous
                out.reasons[d.id] = "Minimale looptijd; vermogen regelbaar"
            continue
        reason = ""
        if s.fault:
            reason = s.fault
        elif not s.available:
            reason = "Toestel of meting onbeschikbaar"
        elif not s.enabled:
            reason = "Uitgesloten van regeling"
        elif not s.interlock:
            reason = "Vrijgave ontbreekt"
        elif not s.demand:
            reason = "Geen vraag / buiten tijdvenster"
        elif not site.valid:
            reason = "Geen betrouwbare energiemeting"
        elif site.mode == "paused":
            reason = "Regelaar gepauzeerd"
        elif site.external_hold:
            reason = site.external_reason or "Externe regelaar heeft voorrang"
        elif not site.battery_ready:
            reason = "Thuisbatterij heeft voorrang"
        elif s.manual_until > site.now:
            reason = "Handmatige bediening: tijdelijk met rust laten"
        elif s.on and not s.owned:
            reason = "Extern actief: niet overnemen"
        elif s.planner_hold and not s.on:
            reason = s.planner_reason or "EMS-planner stelt optionele start uit"
        elif not s.on and site.now - s.last_off < d.min_off_s:
            reason = "Minimale rusttijd"
        elif d.non_interruptible and not s.on and not s.cycle_armed:
            reason = "Cyclus voltooid: nieuwe vrijgave nodig"
        elif d.max_daily_runtime_s > 0 and s.daily_runtime_s >= d.max_daily_runtime_s:
            # Running non-interruptible cycles are already locked above and may finish.
            # A new cycle may not start once the configured daily maximum is reached.
            reason = "Dagmaximum bereikt"
        elif s.owned and d.max_on_s > 0 and site.now - s.last_on >= d.max_on_s:
            reason = "Maximale looptijd bereikt"
        if reason:
            out.reasons[d.id] = reason
            s.start_since = None
            continue
        manual_boost = s.boost_until > site.now
        deadline_boost = s.deadline_force
        planner_grid = s.planner_grid_force
        boost = manual_boost or deadline_boost or planner_grid
        available = remaining_cap if boost else min(remaining_solar, remaining_cap)
        eligible = (d.allow_wallbox_reclaim and not d.non_interruptible and d.min_on_s <= site.handover_s)
        if not s.owned and not eligible and not boost:
            available = min(available, remaining_solar-credit)
        needed = d.minimum + (d.start_margin_w if not s.on and not boost else 0)
        target = d.quantize(available) if available >= needed else 0.0
        if target:
            out.targets[d.id] = target
            remaining_solar -= target
            remaining_cap -= target
            if not s.on:
                if s.start_since is None:
                    s.start_since = site.now
                left = max(0, d.start_delay_s - (site.now - s.start_since))
                out.reasons[d.id] = (f"Startvertraging: {math.ceil(left)} s" if left else
                                     "Dagminimum: deadline nadert, netstroom toegestaan" if deadline_boost else
                                     "Goedkope netfallback voor dagminimum" if planner_grid else
                                     "Boost gereed" if manual_boost else
                                     "Dagminimum: deadline nadert, zonnestroom eerst" if s.deadline_urgent else
                                     "Voldoende overschot")
            else:
                out.reasons[d.id] = ("Dagminimum vóór deadline" if s.deadline_urgent else
                                     "Goedkope netfallback voor dagminimum" if planner_grid else
                                     "Tijdelijke boost" if manual_boost else "Gebruikt zonnestroom")
        else:
            s.start_since = None
            out.reasons[d.id] = "Wacht op vermogen / hogere prioriteit"

    # Failed transfers revert only the affected own increase, respecting locks.
    if site.rollback_device in out.targets:
        i = site.rollback_device
        d = next(d for d in devices if d.id == i)
        s = states[i]
        if s.owned and not d.non_interruptible:
            target = min(s.target_w, site.rollback_target_w)
            if target > 0 or site.now-s.last_on >= d.min_on_s:
                out.targets[i] = target
                out.reasons[i] = site.rollback_reason or "Overname terugnemen"
            else:
                out.reasons[i] = "Overname mislukt; minimale looptijd afwachten vóór terugnemen"

    # First reduce lower-priority flexible loads, never raise another load before
    # the runtime has confirmed the reduction and sampled the meter again.
    for d in reversed(sorted_devices):
        s = states[d.id]
        target = out.targets[d.id]
        if not s.owned or not s.on or not s.available:
            continue
        if target + 0.5 >= s.target_w:
            s.stop_since = None
            continue
        if d.non_interruptible:
            continue
        if target == 0 and site.now - s.last_on < d.min_on_s:
            continue
        if not site.valid and site.fault_elapsed_s < site.fault_grace_s:
            out.reasons[d.id] = "Meetfout: korte overbrugging"
            continue
        if s.stop_since is None:
            s.stop_since = site.now
        immediate = blocked_site or not s.enabled or not s.interlock or not s.demand or bool(s.fault) or emergency or d.id == site.rollback_device
        if not immediate and site.now - s.stop_since < d.stop_delay_s:
            out.reasons[d.id] = "Stopvertraging / wolkenbuffer"
            continue
        out.action = Action(d.id, target, out.reasons[d.id])
        return out

    if not site.valid or blocked_site or not site.can_increase or emergency:
        if not site.can_increase and site.increase_reason:
            for d in sorted_devices:
                s = states[d.id]
                if out.targets[d.id] > (s.target_w if s.owned else 0) + 0.5:
                    out.reasons[d.id] = site.increase_reason
        return out

    # Reserve already committed but currently unconsumed power (e.g. a thermostat
    # momentarily not heating). Never allocate that same headroom a second time.
    committed = sum(max(0.0, states[d.id].target_w - states[d.id].measured_w)
                    for d in devices if states[d.id].owned and states[d.id].on)
    for d in sorted_devices:
        s = states[d.id]
        target = out.targets[d.id]
        if target <= s.target_w + 0.5 and s.owned:
            continue
        if target <= 0 or (s.on and not s.owned) or not s.available or s.fault:
            continue
        if not s.on and (s.start_since is None or site.now - s.start_since < d.start_delay_s):
            continue
        current = s.measured_w if s.owned and s.on else 0.0
        own_commitment = max(0.0, s.target_w - current) if s.owned and s.on else 0.0
        other_commitment = committed - own_commitment
        cap_free = site.max_import_w - site.grid_w - other_commitment
        solar_free = -site.grid_w - site.battery_discharge_w - site.reserve_w - other_commitment
        actual_solar_free = solar_free
        grid_boost = s.boost_until > site.now or s.deadline_force or s.planner_grid_force
        eligible = (d.allow_wallbox_reclaim and not d.non_interruptible
                    and d.min_on_s <= site.handover_s and not grid_boost)
        usable_credit = min(max(0, site.reclaimable_w), max(0, site.max_takeover_w)) if eligible else 0
        solar_free += usable_credit
        free = cap_free if grid_boost else min(solar_free, cap_free)
        if site.max_increase_w is not None:
            free = min(free, site.max_increase_w)
        device_limit = site.device_increase_limits.get(d.id) if site.device_increase_limits else None
        if device_limit is not None:
            free = min(free, max(0.0, float(device_limit)))
        proposed = d.quantize(min(target, current + max(0, free)))
        if proposed <= 0 or (s.owned and proposed <= s.target_w + 0.5):
            out.reasons[d.id] = "Wacht op werkelijk vrijgekomen vermogen"
            continue
        if not s.on and not grid_boost and free < proposed + d.start_margin_w:
            out.reasons[d.id] = "Wacht op startmarge"
            continue
        borrowed = (max(0.0, proposed-current-max(0.0, actual_solar_free))
                    if eligible and not grid_boost else 0.0)
        out.action = Action(d.id, proposed, out.reasons[d.id], round(borrowed, 6))
        return out
    return out
