"""A reaction window is bounded evidence, not renewable net headroom."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.sg_wallbox_transfer import SGWallboxTransfer


IDENTITY = "a" * 64
OTHER_IDENTITY = "b" * 64


class Clock:
    def __init__(self):
        self.now, self.wall = 100.0, 1700000000.0

    def advance(self, seconds):
        self.now += seconds
        self.wall += seconds


def observe(transfer, clock, *, grid=0, **changes):
    data = dict(now=clock.now, wall=clock.wall, grid_w=grid, grid_stamp=clock.wall,
        limit_w=3500, recovery_w=600, eligible_w=2500, duration_s=240,
        confirm_s=15, identity=IDENTITY, live=True)
    data.update(changes)
    return transfer.observe(**data)


def allowed(transfer, clock, *, grid=4000, projected=None, **changes):
    data = dict(now=clock.now, wall=clock.wall, grid_w=grid,
        projected_w=grid if projected is None else projected, limit_w=3500,
        eligible_w=2500, identity=IDENTITY, live=True)
    data.update(changes)
    return transfer.allowed(**data)


def armed():
    transfer, clock = SGWallboxTransfer(), Clock()
    observe(transfer, clock)
    clock.advance(15)
    observe(transfer, clock)
    assert transfer.overview(now=clock.now, wall=clock.wall)["state"] == "ready"
    return transfer, clock


def active():
    transfer, clock = armed()
    observe(transfer, clock, grid=4000)
    assert allowed(transfer, clock)
    return transfer, clock


def test_initial_overload_cannot_create_a_window_without_observed_recovery():
    transfer, clock = SGWallboxTransfer(), Clock()
    observe(transfer, clock, grid=4000)
    assert transfer.snapshot()["episode"] is None
    assert not allowed(transfer, clock)
    assert not allowed(transfer, clock, grid=0, projected=4000, live=False)


def test_recovery_requires_duration_two_reports_and_continuous_observations():
    transfer, clock = SGWallboxTransfer(), Clock()
    observe(transfer, clock)
    original_report = clock.wall
    clock.advance(15)
    observe(transfer, clock, grid_stamp=original_report)
    assert not allowed(transfer, clock, grid=0, projected=4000)
    observe(transfer, clock)
    assert allowed(transfer, clock, grid=0, projected=4000, live=False)
    # After a source gap, a single fresh low value does not restore readiness.
    observe(transfer, clock, grid_w=None, grid_stamp=None)
    observe(transfer, clock)
    clock.advance(31)
    observe(transfer, clock)
    assert not allowed(transfer, clock, grid=0, projected=4000)
    clock.advance(15)
    observe(transfer, clock)
    assert allowed(transfer, clock, grid=0, projected=4000)


def test_recovery_threshold_cannot_exceed_a_smaller_import_limit():
    transfer, clock = SGWallboxTransfer(), Clock()
    observe(transfer, clock, grid=550, limit_w=500)
    clock.advance(15)
    observe(transfer, clock, grid=550, limit_w=500)
    assert not allowed(transfer, clock, grid=550, limit_w=500)
    observe(transfer, clock, grid=500, limit_w=500)
    clock.advance(15)
    observe(transfer, clock, grid=500, limit_w=500)
    assert allowed(transfer, clock, grid=500, projected=1000, limit_w=500)


def test_new_start_can_temporarily_borrow_only_from_an_observed_safe_baseline():
    transfer, clock = armed()
    assert allowed(transfer, clock, grid=0, projected=4000, live=False)
    assert not allowed(transfer, clock, grid=4000, projected=4000, live=False)
    assert not allowed(transfer, clock, grid=0, projected=6001)
    assert not allowed(transfer, clock, grid=0, projected=3500)
    assert not allowed(transfer, clock, grid=0, projected=-1)


def test_first_current_overload_opens_one_absolute_reaction_window():
    transfer, clock = armed()
    before = transfer.snapshot()
    assert observe(transfer, clock, grid=4000)
    original = transfer.snapshot()["episode"]
    assert original["expires_at"]-original["started_at"] == 240
    for _ in range(4):
        clock.advance(30)
        observe(transfer, clock, grid=4100)
        assert allowed(transfer, clock)
        assert transfer.snapshot()["episode"]["expires_at"] == original["expires_at"]
    clock.advance(120)
    assert not allowed(transfer, clock)
    observe(transfer, clock, grid=4100)
    assert transfer.overview(now=clock.now, wall=clock.wall)["state"] == "exhausted"
    assert transfer.snapshot()["episode"]["expires_at"] == original["expires_at"]
    assert before["episode"] is None


def test_holding_near_the_limit_never_buys_another_window():
    transfer, clock = active()
    original = transfer.snapshot()["episode"]["expires_at"]
    for index in range(12):
        clock.advance(30)
        observe(transfer, clock, grid=3490 if index % 2 else 3510)
    assert not allowed(transfer, clock)
    assert transfer.snapshot()["episode"]["expires_at"] == original
    assert not allowed(transfer, clock, grid=3400, projected=4000)
    observe(transfer, clock, grid=600)
    clock.advance(15)
    observe(transfer, clock, grid=600)
    assert allowed(transfer, clock, grid=600, projected=4000)
    observe(transfer, clock, grid=4000)
    assert transfer.snapshot()["episode"]["expires_at"] > original


def test_larger_later_ev_report_cannot_expand_the_original_credit_cap():
    transfer, clock = armed()
    observe(transfer, clock, grid=4000, eligible_w=1000)
    assert allowed(transfer, clock, grid=4500, eligible_w=2500)
    assert not allowed(transfer, clock, grid=4501, eligible_w=2500)
    assert not allowed(transfer, clock, grid=4500, eligible_w=999)


def test_uncovered_overload_disarms_until_measured_recovery():
    transfer, clock = armed()
    observe(transfer, clock, grid=6100)
    assert transfer.snapshot()["episode"] is None
    observe(transfer, clock, grid=4000)
    assert not allowed(transfer, clock)


def test_external_or_lost_live_session_has_no_high_import_exception():
    transfer, clock = armed()
    observe(transfer, clock, grid=4000, live=False)
    assert not allowed(transfer, clock)
    transfer, clock = active()
    original = transfer.snapshot()
    assert not allowed(transfer, clock, live=False)
    observe(transfer, clock, grid=4000, live=False)
    assert transfer.snapshot() == original
    assert allowed(transfer, clock, live=True)


def test_changed_identity_cannot_return_and_reuse_a_previous_window():
    transfer, clock = active()
    deadline = transfer.snapshot()["episode"]["expires_at"]
    observe(transfer, clock, grid=4000, identity=OTHER_IDENTITY)
    assert not allowed(transfer, clock, identity=OTHER_IDENTITY)
    observe(transfer, clock, grid=4000, identity=IDENTITY)
    assert not allowed(transfer, clock)
    assert transfer.snapshot()["episode"]["expires_at"] == deadline


def test_changed_limit_requires_new_identity_or_still_cannot_reuse_episode():
    transfer, clock = active()
    assert not allowed(transfer, clock, limit_w=3000)


def test_render_and_final_checks_never_refresh_or_create_persisted_evidence():
    transfer, clock = armed()
    saved = deepcopy(transfer.snapshot())
    for _ in range(10):
        transfer.overview(now=clock.now, wall=clock.wall)
        allowed(transfer, clock, grid=0, projected=4000)
        allowed(transfer, clock)
    assert transfer.snapshot() == saved
    transfer, clock = active()
    saved = deepcopy(transfer.snapshot())
    clock.advance(10)
    for _ in range(10):
        assert allowed(transfer, clock)
        transfer.overview(now=clock.now, wall=clock.wall)
    assert transfer.snapshot() == saved


def test_restart_keeps_original_deadline_but_does_not_restore_readiness():
    transfer, clock = armed()
    restored = SGWallboxTransfer()
    restored.restore(transfer.snapshot())
    assert not allowed(restored, clock, grid=0, projected=4000)
    transfer, clock = active()
    deadline = transfer.snapshot()["episode"]["expires_at"]
    clock.advance(100)
    restored.restore(transfer.snapshot())
    assert not allowed(restored, clock)  # No monotonic proof until observe.
    observe(restored, clock, grid=4000)
    assert allowed(restored, clock)
    assert restored.overview(now=clock.now, wall=clock.wall)["remaining_s"] == 140
    assert restored.snapshot()["episode"]["expires_at"] == deadline
    clock.advance(140)
    observe(restored, clock, grid=4000)
    assert not allowed(restored, clock)


def test_expired_or_invalidated_restore_never_renews_itself():
    transfer, clock = active()
    clock.advance(240)
    observe(transfer, clock, grid=4000)
    restored = SGWallboxTransfer()
    restored.restore(transfer.snapshot())
    clock.wall -= 100
    observe(restored, clock, grid=4000)
    assert not allowed(restored, clock)


def test_wall_clock_rollback_does_not_extend_original_monotonic_deadline():
    transfer, clock = active()
    clock.advance(100)
    clock.wall -= 90
    observe(transfer, clock, grid=4000)
    assert transfer.overview(now=clock.now, wall=clock.wall)["remaining_s"] == 140
    clock.advance(140)
    assert not allowed(transfer, clock)


def test_restoring_before_original_start_and_clock_regression_fail_closed():
    transfer, clock = active()
    saved = transfer.snapshot()
    restored = SGWallboxTransfer()
    restored.restore(saved)
    clock.wall -= 1
    observe(restored, clock, grid=4000)
    assert not allowed(restored, clock)
    clock.wall += 1
    assert not allowed(restored, clock)
    clock.now -= 1
    assert not allowed(transfer, clock)


def test_restart_after_a_partial_wall_rollback_cannot_gain_saved_live_remainder():
    transfer, clock = active()
    clock.advance(100)
    assert not observe(transfer, clock, grid=4000)  # Checkpoints alone need no write.
    saved = transfer.snapshot()
    assert saved["remaining_cap_s"] == 140
    restored = SGWallboxTransfer()
    restored.restore(saved)
    clock.wall -= 30  # Still after session start, but before the saved report.
    observe(restored, clock, grid=4000)
    assert not allowed(restored, clock)
    clock.wall += 30
    assert not allowed(restored, clock)


def test_saved_remaining_cap_also_bounds_future_restore_after_wall_time_recovers():
    transfer, clock = active()
    clock.advance(100)
    observe(transfer, clock, grid=4000)
    saved = transfer.snapshot()
    saved["remaining_cap_s"] = 30  # A stricter original monotonic remainder.
    restored = SGWallboxTransfer()
    restored.restore(saved)
    observe(restored, clock, grid=4000)
    assert restored.overview(now=clock.now, wall=clock.wall)["remaining_s"] == 30
    clock.advance(30)
    assert not allowed(restored, clock)


def test_initial_window_uses_the_original_high_p1_report_time():
    transfer, clock = armed()
    report_time = clock.wall
    clock.advance(20)
    observe(transfer, clock, grid=4000, grid_stamp=report_time)
    view = transfer.overview(now=clock.now, wall=clock.wall)
    assert view["started_at"] == report_time and view["remaining_s"] == 220


def test_high_report_older_than_proven_recovery_cannot_create_fresh_grace():
    transfer, clock = armed()
    observe(transfer, clock, grid=4000, grid_stamp=clock.wall-1)
    assert transfer.snapshot()["episode"] is None
    assert not allowed(transfer, clock)


def test_backdated_low_report_after_high_episode_does_not_prove_recovery():
    transfer, clock = active()
    clock.advance(240)
    observe(transfer, clock, grid=4000)
    high_report = clock.wall
    clock.advance(1)
    observe(transfer, clock, grid=0, grid_stamp=high_report-10)
    clock.advance(15)
    observe(transfer, clock, grid=0, grid_stamp=high_report-5)
    assert not allowed(transfer, clock, grid=0, projected=4000)
    observe(transfer, clock, grid=0)
    clock.advance(15)
    observe(transfer, clock, grid=0)
    assert allowed(transfer, clock, grid=0, projected=4000)


def test_source_stamp_highwater_survives_restart_and_rejects_a_backdated_report():
    transfer, clock = active()
    clock.advance(30)
    observe(transfer, clock, grid=4000)
    saved = transfer.snapshot()
    restored = SGWallboxTransfer()
    restored.restore(saved)
    clock.advance(5)
    observe(restored, clock, grid=4000, grid_stamp=saved["grid_reported_at"]-1)
    assert not allowed(restored, clock)
    assert restored.snapshot()["episode"]["invalidated"] is True


@pytest.mark.parametrize("change", [{"grid_stamp": None}, {"grid_stamp": float("nan")},
    {"grid_stamp": 1800000000},
    {"grid_w": True}, {"grid_w": None}, {"identity": "not a source identity"},
    {"duration_s": True}, {"duration_s": 601}, {"confirm_s": 240},
    {"eligible_w": float("inf")}, {"limit_w": -1}])
def test_malformed_observations_cannot_create_or_restore_readiness(change):
    transfer, clock = armed()
    observe(transfer, clock, **change)
    assert not allowed(transfer, clock, grid=0, projected=4000)


@pytest.mark.parametrize("value", [None, [], {"schema": True}, {"schema": 1, "armed": True},
    {"schema": 1, "identity": IDENTITY, "episode": {"schema": 1}}])
def test_malformed_restore_grants_no_permission(value):
    transfer, clock = armed()
    transfer.restore(value)
    assert not allowed(transfer, clock, grid=0, projected=4000)


@pytest.mark.parametrize("field,bad", [("started_at", True), ("expires_at", float("inf")),
    ("credit_cap_w", -1), ("expired", 0), ("invalidated", None), ("identity", "c" * 63)])
def test_damaged_episode_never_becomes_an_active_restore(field, bad):
    transfer, clock = active()
    saved = transfer.snapshot()
    saved["episode"][field] = bad
    restored = SGWallboxTransfer()
    restored.restore(saved)
    observe(restored, clock, grid=4000)
    assert not allowed(restored, clock)


@pytest.mark.parametrize("field,bad", [("observed_at", None), ("observed_at", True),
    ("observed_at", 1), ("remaining_cap_s", float("inf")),
    ("remaining_cap_s", True), ("remaining_cap_s", 241)])
def test_damaged_original_time_checkpoint_does_not_resume(field, bad):
    transfer, clock = active()
    saved = transfer.snapshot()
    saved[field] = bad
    restored = SGWallboxTransfer()
    restored.restore(saved)
    observe(restored, clock, grid=4000)
    assert not allowed(restored, clock)


def test_extreme_integer_source_and_storage_values_fail_closed_without_overflow():
    huge = 10**10000
    transfer, clock = armed()
    observe(transfer, clock, eligible_w=huge)
    assert not allowed(transfer, clock, grid=0, projected=4000)
    transfer, clock = active()
    saved = transfer.snapshot()
    saved["remaining_cap_s"] = huge
    transfer.restore(saved)
    observe(transfer, clock, grid=4000)
    assert not allowed(transfer, clock)
