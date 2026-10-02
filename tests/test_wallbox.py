"""External-control arbitration: pure Python, no charger or Home Assistant Core."""
from dataclasses import replace
import pytest
from custom_components.solar_pilot.wallbox import (
    GuardResult, Reading, WallboxGuard, WALLBOX_DEFAULTS,
    confirmed_no_active_request, state_set,
)
from custom_components.solar_pilot.house_first import HouseFirstGuard
from custom_components.solar_pilot.engine import Device, State, Site, plan


def guard(**kwargs):
    return WallboxGuard({"enabled": True, "mode_entity": "select.ev_mode", **kwargs})


def reading(**kwargs):
    return replace(Reading(2000, 1000, True, "Charging", "full_solar", True), **kwargs)


def stable(g, r=None, grid=-1000, start=0, end=180, reserve=150):
    for t in range(start, end + 1, 5):
        result = g.update(t, r or reading(), grid, reserve)
    return result


def test_disabled_guard_leaves_existing_behavior_unchanged():
    assert WallboxGuard({}).update(0, Reading(), None, 150) == GuardResult()


def test_monitor_only_never_changes_dispatch_even_when_waiting():
    v = guard(policy="monitor").update(0, reading(power_w=0), -3000, 150)
    assert not v.block_increase and not v.release_flexible and v.max_increase_w is None


def test_monitor_only_offline_is_warning_not_control():
    v = guard(policy="monitor").update(100, Reading(), None, 150)
    assert v.state == "unavailable" and not v.block_increase and not v.release_flexible


def test_waiting_car_releases_our_own_loads_without_minimum_power_guess():
    v = guard().update(0, reading(power_w=0), -500, 150)
    assert v.block_increase and v.release_flexible and v.state == "waiting"


@pytest.mark.parametrize("guard_type", [WallboxGuard, HouseFirstGuard])
@pytest.mark.parametrize("mode", ["full_solar", "manual"])
def test_fresh_zero_power_and_no_demand_releases_immediately(guard_type, mode):
    g = guard_type({"enabled": True, "mode_entity": "select.ev_mode"})
    v = g.update(0, reading(power_w=0, demand=False,
                            status="Waiting for car demand", mode=mode), -5000, 150)
    assert v.state == "idle" and not v.block_increase and v.max_increase_w is None
    assert "geen vermogen gereserveerd" in v.reason


@pytest.mark.parametrize("guard_type", [WallboxGuard, HouseFirstGuard])
def test_exact_idle_status_releases_even_if_demand_helper_disagrees(guard_type):
    g = guard_type({"enabled": True, "mode_entity": "select.ev_mode"})
    v = g.update(0, reading(power_w=0, demand=True, status="Waiting for car demand"),
                 -5000, 150)
    assert v.state == "idle" and not v.block_increase


@pytest.mark.parametrize("guard_type", [WallboxGuard, HouseFirstGuard])
def test_confirmed_disconnected_low_power_releases_immediately(guard_type):
    g = guard_type({"enabled": True, "mode_entity": "select.ev_mode"})
    v = g.update(0, reading(power_w=0, demand=True, status="Unmapped status",
                            connected=False), -5000, 150)
    assert v.state == "idle" and not v.block_increase


def test_no_request_release_requires_fresh_low_power_and_explicit_evidence():
    c = WALLBOX_DEFAULTS
    assert confirmed_no_active_request(
        reading(power_w=0, demand=False, status="Waiting for car demand"), c)
    assert confirmed_no_active_request(
        reading(power_w=0, demand=True, status="Unmapped status", connected=False), c)
    assert not confirmed_no_active_request(
        reading(power_w=50, demand=False, status="Waiting for car demand"), c)
    assert not confirmed_no_active_request(
        reading(power_w=0, demand=None, status="Unmapped status"), c)
    assert not confirmed_no_active_request(
        reading(power_w=0, demand=False, status="Ready", age_s=301), c)
    assert not confirmed_no_active_request(
        reading(power_w=0, demand=False, status="Ready", valid=False), c)


@pytest.mark.parametrize(("key", "value"), [
    ("charging_threshold_w", float("nan")),
    ("charging_threshold_w", float("inf")),
    ("charging_threshold_w", float("-inf")),
    ("stale_s", float("nan")),
    ("stale_s", float("inf")),
    ("stale_s", -1),
])
def test_no_request_release_rejects_nonfinite_or_invalid_limits(key, value):
    settings = {**WALLBOX_DEFAULTS, key: value}
    assert not confirmed_no_active_request(
        reading(power_w=0, demand=False, status="Waiting for car demand"), settings)


@pytest.mark.parametrize("guard_type", [WallboxGuard, HouseFirstGuard])
def test_active_manual_and_explicit_external_stop_keep_their_session_state(guard_type):
    g = guard_type({"enabled": True, "mode_entity": "select.ev_mode"})
    manual = g.update(0, reading(power_w=2000, demand=False, status="Charging", mode="manual"),
                      -5000, 150)
    stopped = g.update(5, reading(power_w=0, demand=True, status="Charging", mode="stopped"),
                       -5000, 150)
    assert manual.state == "manual"
    assert stopped.state == "stopped"


def test_positive_power_overrides_idle_status_without_freeing_ev_watts():
    v = stable(guard(), reading(demand=False, status="Ready"), grid=-1000)
    assert v.state == "charging" and v.max_increase_w == 850


def test_charging_has_a_stabilization_window():
    v = stable(guard(), end=175)
    assert v.block_increase and v.remaining_s == 5


def test_ev_consumption_is_neither_added_nor_subtracted_again():
    # EV consumes 4 kW; meter says 900 W export. Only 750 W is free after reserve.
    v = stable(guard(), reading(power_w=4000), grid=-900)
    assert v.max_increase_w == 750


def test_surplus_window_uses_minimum_not_last_or_average():
    g = guard()
    stable(g, grid=-500, end=90)
    v = stable(g, grid=-1800, start=95, end=180)
    assert v.max_increase_w == 350


def test_import_within_window_means_no_stable_surplus():
    g = guard()
    stable(g, end=80)
    g.update(85, reading(), 100, 150)
    v = stable(g, start=90)
    assert v.max_increase_w == 0 and v.block_increase


def test_battery_discharge_is_not_usable_surplus():
    g = guard()
    for t in range(0, 181, 5):
        v = g.update(t, reading(), -1000, 150, 900)
    assert v.max_increase_w == 0


def test_large_ev_change_restarts_window():
    g = guard()
    stable(g)
    v = g.update(185, reading(power_w=2500), -1000, 150)
    assert v.block_increase and v.remaining_s == 180


def test_small_noise_does_not_restart_stability_window():
    g = guard()
    stable(g, end=175)
    v = g.update(180, reading(power_w=2010), -1000, 150)
    assert v.max_increase_w == 850


def test_runtime_gap_is_not_mistaken_for_observed_stability():
    g = guard()
    g.update(0, reading(), -5000, 150)
    v = g.update(500, reading(), -5000, 150)
    assert v.block_increase and v.remaining_s == 180


def test_own_command_requires_new_settling_window():
    g = guard()
    stable(g)
    g.note_action(180, 1001, 0, 500)
    v = g.update(185, reading(stamp=1002), -1000, 150)
    assert v.block_increase


def test_own_reduction_also_requires_settling():
    g = guard()
    stable(g)
    g.note_action(180, 1001, 1000, 0)
    assert g.update(185, reading(stamp=1002), -2000, 150).block_increase


def test_power_drop_after_our_start_triggers_conservative_cooldown():
    g = guard()
    stable(g)
    g.note_action(180, 1001, 0, 1000)
    v = g.update(185, reading(power_w=1500, stamp=1002), 0, 150)
    assert v.state == "cooldown" and v.release_flexible and v.remaining_s == 600
    assert g.conflict_count == 1


def test_old_ev_sample_cannot_be_used_as_post_command_confirmation():
    g = guard()
    stable(g)
    g.note_action(180, 1001, 0, 1000)
    v = g.update(185, reading(power_w=1500, stamp=1000), 0, 150)
    assert v.state != "cooldown" and g.conflict_count == 0


def test_watch_waits_for_an_actual_new_report():
    g = guard()
    stable(g)
    g.note_action(180, 1001, 0, 1000)
    stable(g, reading(stamp=1000), start=185, end=400)
    assert g.watch is not None
    assert g.result.block_increase
    assert "nieuw Wallbox-rapport" in g.result.reason


def test_new_stable_sample_completes_watch_without_warning():
    g = guard()
    stable(g)
    g.note_action(180, 1001, 0, 1000)
    stable(g, reading(stamp=1002), start=185, end=365)
    assert g.watch is None and not g.conflict_count


def test_uncertain_reading_blocks_then_releases_after_grace():
    g = guard()
    v = g.update(0, Reading(), -5000, 150)
    assert v.block_increase and not v.release_flexible
    assert not g.update(29, Reading(), -5000, 150).release_flexible
    assert g.update(30, Reading(), -5000, 150).release_flexible


def test_recovery_from_invalid_requires_new_stability_window():
    g = guard()
    stable(g)
    g.update(185, Reading(), -5000, 150)
    v = g.update(190, reading(), -5000, 150)
    assert v.block_increase and v.remaining_s == 180


def test_other_charging_mode_warns_but_does_not_write_mode():
    v = stable(guard(), reading(mode="eco_mode"))
    assert "geen Full solar" in v.warning


def test_unknown_or_unconfigured_solar_mode_does_not_claim_green_energy():
    assert "niet beschikbaar" in stable(guard(), reading(mode=None)).warning
    assert "niet geverifieerd" in stable(guard(mode_entity="")).warning


def test_semicolon_separator_preserves_native_comma_in_status():
    assert "locked, car connected" in state_set(WALLBOX_DEFAULTS["idle_states"])
    assert "disconnected" not in state_set(WALLBOX_DEFAULTS["idle_states"])


def ds(**kwargs):
    return Device("a", min_on_s=0, min_off_s=0, start_delay_s=0,
                  stop_delay_s=0, start_margin_w=0, **kwargs)


def site(**kwargs):
    return Site(now=1000, grid_w=-5000, filtered_grid_w=-5000, reserve_w=0, **kwargs)


def test_external_hold_releases_only_our_owned_flexible_load():
    s = State(owned=True, on=True, measured_w=1000, target_w=1000, last_on=0)
    p = plan(site(external_hold=True, external_reason="Wallbox wacht"), [ds()], {"a": s})
    assert p.action.watts == 0 and "Wallbox" in p.action.reason


def test_external_hold_never_stops_unowned_load():
    s = State(owned=False, on=True, measured_w=1000)
    assert plan(site(external_hold=True), [ds()], {"a": s}).action is None


def test_external_hold_respects_non_interruptible_cycle():
    s = State(owned=True, on=True, measured_w=1000, target_w=1000, last_on=0)
    assert plan(site(external_hold=True), [ds(non_interruptible=True)], {"a": s}).action is None


def test_external_hold_respects_minimum_run_time():
    d = replace(ds(), min_on_s=1200)
    s = State(owned=True, on=True, measured_w=1000, target_w=1000, last_on=0)
    assert plan(site(external_hold=True), [d], {"a": s}).action is None


def test_external_headroom_cap_applies_to_boost_too():
    s = State(boost_until=2000)
    p = plan(site(max_increase_w=500), [ds(nominal_w=1000)], {"a": s})
    assert p.action is None


def test_external_cap_does_not_stop_existing_safe_load():
    s = State(owned=True, on=True, measured_w=1000, target_w=1000, last_on=0)
    p = plan(site(max_increase_w=0), [ds()], {"a": s})
    assert p.action is None and p.targets["a"] == 1000


def test_external_cap_limits_variable_increase_not_total_running_load():
    s = State(owned=True, on=True, measured_w=1380, target_w=1380, last_on=0)
    p = plan(site(max_increase_w=500), [ds(kind="number")], {"a": s})
    assert p.action.watts == 1840


def test_external_hold_reason_is_visible_in_planner():
    p = plan(site(can_increase=False, increase_reason="Wallbox reactietijd"), [ds()], {"a": State()})
    assert p.action is None and p.reasons["a"] == "Wallbox reactietijd"
