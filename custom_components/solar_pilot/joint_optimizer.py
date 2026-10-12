"""Bounded joint improvement of already satisfied flexible-load schedules.

This dependency-free module never dispatches appliances. It keeps each device's
committed energy/count and searches one-device relocations and two-device
exchanges. ``best_found`` is not a global-optimality certificate. Call before
battery what-if scheduling, from an executor, with an isolated plan snapshot.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timedelta
import math
import time

MAX_EVALUATIONS = 1000
MAX_SECONDS = 0.1
MAX_SLOTS = 576
MAX_DEVICES = 16
EPSILON = 1e-8


def _number(value):
    if isinstance(value, bool):
        raise ValueError("Boolean numeric input")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("Non-finite numeric input")
    return result


def _clock(raw):
    parts = str(raw).split(":")
    if len(parts) not in (2, 3):
        raise ValueError("Invalid clock")
    hour, minute = int(parts[0]), int(parts[1])
    second = int(parts[2]) if len(parts) == 3 else 0
    if not (0 <= hour < 24 and 0 <= minute < 60 and 0 <= second < 60):
        raise ValueError("Invalid clock")
    return hour, minute, second


def _at(day, clock):
    return day.replace(hour=clock[0], minute=clock[1], second=clock[2], microsecond=0)


def _slot_legal(start, seconds, cfg):
    """Require the entire physical slot inside its window and daily deadline."""
    end_ts = start.timestamp() + seconds
    deadline = _at(start, _clock(cfg.get("daily_deadline", "23:59:00")))
    if end_ts > deadline.timestamp() + EPSILON:
        return False
    if not cfg.get("time_window_enabled"):
        return True
    begin_clock = _clock(cfg.get("time_window_start", "00:00:00"))
    end_clock = _clock(cfg.get("time_window_end", "23:59:00"))
    begin = _at(start, begin_clock)
    end = _at(start, end_clock)
    if begin_clock <= end_clock:
        return begin.timestamp() <= start.timestamp() and end_ts <= end.timestamp() + EPSILON
    if start.timestamp() < end.timestamp():
        begin -= timedelta(days=1)
    else:
        end += timedelta(days=1)
    return begin.timestamp() <= start.timestamp() and end_ts <= end.timestamp() + EPSILON


@dataclass(frozen=True)
class _Device:
    id: str
    priority: int
    power: float
    peak: float
    required: float
    contiguous: bool
    grid_allowed: bool
    legal: frozenset[int]
    original: tuple[int, ...]
    date_counts: tuple[tuple[str, int], ...]


def optimize_joint_plan(slots, plans, devices, settings, slot_h, capacity_target_w=None):
    """Improve the household objective atomically, preserving every daily goal.

    Inputs use PlannedSlot/DevicePlan's existing attribute contract. On invalid
    input, unsupported storage advice or an invalid incumbent, return fallback
    without any mutations. Missing PV is eligible only with the same three
    explicit early-grid permissions as the incumbent planner.
    """
    started = time.monotonic()
    metadata = {"status": "fallback", "baseline_objective_eur": None,
                "optimized_objective_eur": None, "improvement_eur": 0.0,
                "evaluations": 0, "applied": False,
                "global_optimality_proven": False,
                "objective": "net_import_export_cost_plus_soft_peak_penalty",
                "reason": "Invalid or unsupported planning input"}
    try:
        duration = _number(slot_h)
        if not 0 < duration <= 24 or not 1 <= len(slots) <= MAX_SLOTS:
            raise ValueError("Invalid horizon")
        seconds = duration * 3600
        evaluation_limit = min(MAX_EVALUATIONS, max(0, int(settings.get("joint_optimizer_max_evaluations", MAX_EVALUATIONS))))
        time_limit = min(MAX_SECONDS, max(0.0, _number(settings.get("joint_optimizer_time_budget_s", MAX_SECONDS))))
        reserve = _number(settings.get("pv_reserve_w", 150.0))
        if reserve < 0:
            raise ValueError("Negative reserve")
        target = None if capacity_target_w is None else _number(capacity_target_w)
        penalty = _number(settings.get("capacity_penalty_eur_kwh", 0.5)) if settings.get("capacity_penalty_enabled", True) and target is not None else 0.0
        if penalty < 0 or (target is not None and target < 0):
            raise ValueError("Invalid soft peak penalty")
        base, fixed, prices_in, prices_out, available, fixed_names = [], [], [], [], [], []
        previous_ts = None
        for slot in slots:
            if not isinstance(slot.start, datetime):
                raise ValueError("Invalid slot start")
            ts = slot.start.timestamp()
            if previous_ts is not None and abs(ts - previous_ts - seconds) > 0.001:
                raise ValueError("Nonuniform slot times")
            previous_ts = ts
            pv, load = _number(slot.pv_w), _number(slot.base_w)
            committed, storage = _number(slot.planned_load_w), _number(slot.battery_w)
            if min(pv, load, committed) < 0 or abs(storage) > EPSILON:
                raise ValueError("Invalid load or already scheduled storage advice")
            # Unknown production is never free energy, even if an upstream
            # object still carries a stale numeric PV value.
            base.append(load - (pv if slot.pv_available else 0.0))
            fixed.append(committed)
            prices_in.append(_number(slot.import_price))
            prices_out.append(_number(slot.export_price))
            available.append(bool(slot.pv_available))
            fixed_names.append(list(slot.devices))
        cfg_by_id = {}
        for cfg in devices:
            if not isinstance(cfg, dict) or not isinstance(cfg.get("id"), str) or cfg["id"] in cfg_by_id:
                raise ValueError("Invalid/duplicate device")
            cfg_by_id[cfg["id"]] = cfg
        moving = []
        for device_id, plan in plans.items():
            cfg = cfg_by_id.get(device_id)
            if not cfg or cfg.get("fixed_active_cycle") or not cfg.get("enabled", True) or not cfg.get("forecast_deferrable", False):
                continue
            # Existing specialized autonomous controls never become new decision
            # variables merely because a planner configuration was supplied.
            role = str(cfg.get("type", cfg.get("kind", ""))).lower()
            if role in {"heatpump", "heat_pump", "wallbox", "ev", "sg", "sg_ready"}:
                continue
            required = _number(plan.required_kwh)
            planned = _number(plan.planned_kwh)
            if required <= 0.001 or ("required_kwh" in cfg and _number(cfg["required_kwh"]) <= 0.001) or not plan.selected_slots:
                continue
            if planned < 0:
                raise ValueError("Negative committed energy")
            chosen = tuple(plan.selected_slots)
            if any(isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(slots) for i in chosen) or tuple(sorted(set(chosen))) != chosen:
                raise ValueError("Invalid incumbent schedule")
            contiguous = bool(plan.contiguous_cycle)
            if contiguous != bool(cfg.get("contiguous_cycle")):
                raise ValueError("Inconsistent cycle semantics")
            if contiguous:
                cycle_duration = _number(cfg.get("cycle_duration_min", 0))
                if cycle_duration <= 0 or len(chosen) != math.ceil(cycle_duration / (duration * 60)):
                    raise ValueError("Invalid cycle duration")
                power = _number(cfg.get("cycle_average_w") or (required * 1000 / (len(chosen) * duration)))
            else:
                power = _number(cfg.get("power_w", 0))
            if power <= 0 or power * len(chosen) * duration / 1000 + EPSILON < planned:
                raise ValueError("Inconsistent committed energy")
            peak = max(power, _number(cfg.get("cycle_peak_w") or power)) if contiguous else power
            legal = frozenset(i for i, slot in enumerate(slots) if _slot_legal(slot.start, seconds, cfg))
            grid_allowed = bool(cfg.get("cheap_grid_allowed") and cfg.get("deadline_grid_allowed") and settings.get("early_grid_enabled"))
            date_counts = tuple(sorted(Counter(slots[i].start.date().isoformat() for i in chosen).items()))
            moving.append(_Device(device_id, int(cfg.get("priority", 50)), power, peak, required,
                                  contiguous, grid_allowed, legal, chosen, date_counts))
            for index, names in enumerate(fixed_names):
                if names.count(device_id) != (1 if index in chosen else 0):
                    raise ValueError("Inconsistent slot membership")
                if index in chosen:
                    fixed[index] -= power
                    names.remove(device_id)
                    if fixed[index] < -1e-5:
                        raise ValueError("Inconsistent slot power")
                    fixed[index] = max(0.0, fixed[index])
        moving.sort(key=lambda d: (d.priority, d.id))
        if len(moving) > MAX_DEVICES:
            raise ValueError("Too many joint planning variables")

        def evaluate(schedule):
            allocated = list(fixed)
            peak_extra = [0.0] * len(slots)
            grid_slots = {}
            for dev in moving:
                selected = schedule[dev.id]
                if len(selected) != len(dev.original) or len(set(selected)) != len(selected) or not set(selected).issubset(dev.legal):
                    return None
                # A cheaper tomorrow must never postpone today's committed
                # allocation. Preserve each local calendar day's slot count,
                # including the day pattern of a complete protected cycle.
                date_counts = tuple(sorted(Counter(slots[i].start.date().isoformat() for i in selected).items()))
                if date_counts != dev.date_counts:
                    return None
                if dev.contiguous and selected != tuple(range(selected[0], selected[0] + len(selected))):
                    return None
                solar_energy = 0.0
                grid = []
                for i in selected:
                    if not available[i] and not dev.grid_allowed:
                        return None
                    surplus = max(0.0, -(base[i] + allocated[i]) - reserve) if available[i] else 0.0
                    solar = min(dev.power, surplus)
                    solar_threshold = dev.power * .35 if dev.contiguous else min(dev.power, max(150.0, dev.power * .35))
                    if not dev.contiguous and not dev.grid_allowed and surplus + EPSILON < solar_threshold:
                        return None
                    solar_energy += solar * duration / 1000
                    if surplus + EPSILON < solar_threshold:
                        grid.append(i)
                    allocated[i] += dev.power
                    peak_extra[i] += dev.peak - dev.power
                if dev.contiguous and not dev.grid_allowed and solar_energy + EPSILON < dev.required * 0.35:
                    return None
                grid_slots[dev.id] = grid
            objective = 0.0
            for i, load in enumerate(allocated):
                net = base[i] + load
                objective += duration / 1000 * (max(0.0, net) * prices_in[i] - max(0.0, -net) * prices_out[i])
                if penalty:
                    objective += duration / 1000 * max(0.0, net + peak_extra[i] - target) * penalty
            if not math.isfinite(objective):
                return None
            return objective, allocated, grid_slots

        current = {dev.id: dev.original for dev in moving}
        baseline_result = evaluate(current)
        if baseline_result is None:
            metadata["reason"] = "Incumbent fails full-slot, cycle, forecast or priority solar validation"
            return metadata
        baseline = best = baseline_result[0]
        metadata.update(status="unchanged", baseline_objective_eur=baseline,
                        optimized_objective_eur=baseline, reason="No improving feasible candidate found")
        if not settings.get("price_optimisation", True):
            metadata["reason"] = "Price optimisation is disabled; incumbent preference retained"
            return metadata
        if not moving:
            metadata["reason"] = "No movable committed flexible loads"
            return metadata
        exhausted = False

        def consider(changes):
            nonlocal best, current, exhausted
            if metadata["evaluations"] >= evaluation_limit or time.monotonic() - started >= time_limit:
                exhausted = True
                return False
            metadata["evaluations"] += 1
            candidate = {**current, **changes}
            result = evaluate(candidate)
            if result is not None and result[0] < best - EPSILON:
                best, current = result[0], candidate
                return True
            return False

        # Pair exchanges run first: a greedy priority allocation can trap two
        # devices where neither individual relocation improves the household.
        changed = True
        while changed and not exhausted:
            changed = False
            for left_index, left in enumerate(moving):
                for right in moving[left_index + 1:]:
                    a, b = current[left.id], current[right.id]
                    if len(a) == len(b) and a != b:
                        changed |= consider({left.id: b, right.id: a})
                    if exhausted:
                        break
                    if not left.contiguous and not right.contiguous:
                        for i in a:
                            for j in b:
                                if i == j or j in a or i in b:
                                    continue
                                new_a = tuple(sorted((set(a) - {i}) | {j}))
                                new_b = tuple(sorted((set(b) - {j}) | {i}))
                                changed |= consider({left.id: new_a, right.id: new_b})
                                if exhausted:
                                    break
                            if exhausted:
                                break
                    if exhausted:
                        break
                if exhausted:
                    break
            for dev in moving:
                if exhausted:
                    break
                selected = current[dev.id]
                if dev.contiguous:
                    for i in range(len(slots) - len(selected) + 1):
                        shifted = tuple(range(i, i + len(selected)))
                        if shifted != selected:
                            changed |= consider({dev.id: shifted})
                        if exhausted:
                            break
                else:
                    for old in selected:
                        for new in sorted(dev.legal - set(selected)):
                            shifted = tuple(sorted((set(selected) - {old}) | {new}))
                            changed |= consider({dev.id: shifted})
                            if exhausted:
                                break
                        if exhausted:
                            break
        metadata["status"] = "budget" if exhausted else ("best_found" if best < baseline - EPSILON else "unchanged")
        metadata["reason"] = "Bounded local joint search; no global optimality certificate" if exhausted or best < baseline - EPSILON else metadata["reason"]
        if best < baseline - EPSILON:
            # Final recomputation before a single commit; never mutate inputs
            # while exploring a candidate or on failed validation.
            verified = evaluate(current)
            if verified is None or verified[0] > baseline - EPSILON:
                metadata.update(status="fallback", reason="Final candidate validation failed")
                return metadata
            final_names = [list(names) for names in fixed_names]
            for dev in moving:
                for i in current[dev.id]:
                    final_names[i].append(dev.id)
            # These are the existing plain dataclass objects, rather than HA
            # entities. Keep the original attribute references so even an
            # injected setter exception cannot leave a half-committed plan.
            saved_slots = [(slot, slot.planned_load_w, slot.devices) for slot in slots]
            saved_plans = [(plans[dev.id], plans[dev.id].selected_slots,
                            plans[dev.id].reason, plans[dev.id].cheap_grid_slots)
                           for dev in moving]
            try:
                for i, slot in enumerate(slots):
                    slot.planned_load_w = verified[1][i]
                    slot.devices = final_names[i]
                for dev in moving:
                    plan = plans[dev.id]
                    if tuple(plan.selected_slots) != current[dev.id]:
                        plan.selected_slots = list(current[dev.id])
                        plan.reason = "Gezamenlijk verbeterde planning; bestaand dagdoel en cyclus behouden"
                    plan.cheap_grid_slots = verified[2][dev.id]
            except Exception:
                for slot, load, names in saved_slots:
                    object.__setattr__(slot, "planned_load_w", load)
                    object.__setattr__(slot, "devices", names)
                for plan, selected, reason, grid in saved_plans:
                    object.__setattr__(plan, "selected_slots", selected)
                    object.__setattr__(plan, "reason", reason)
                    object.__setattr__(plan, "cheap_grid_slots", grid)
                metadata.update(status="fallback", reason="Candidate commit failed; incumbent restored")
                return metadata
            metadata.update(applied=True, optimized_objective_eur=verified[0],
                            improvement_eur=baseline - verified[0])
        return metadata
    except (AttributeError, TypeError, ValueError, OverflowError, KeyError, IndexError):
        return metadata
