"""Pure value-accounting tests; no Home Assistant or hardware involved."""
from copy import deepcopy
import math

import pytest

from custom_components.solar_pilot.savings import SavingsHistory, build_savings_report


DAY = "2026-10-02"


def add(history, **overrides):
    values = dict(day=DAY, dt_s=60, grid_w=-1000, pv_w=4000, automatic_w=2000,
                  battery_discharge_w=0, import_price_eur_kwh=.30,
                  export_price_eur_kwh=.03, power_estimated=False)
    values.update(overrides)
    return history.record_automatic_interval(**values)


def legacy(**overrides):
    return {"date": DAY, "managed_solar_kwh": .78, "managed_kwh": 1.07,
            "estimated_value_eur": .2106, "samples_s": 3600, **overrides}


def test_existing_daily_value_is_not_relabelled_as_automatic_savings():
    report = build_savings_report(legacy(), economy_enabled=True)
    assert report["today"]["estimated_benefit_eur"] is None
    assert report["managed_reference"]["today"]["estimated_benefit_eur"] == .2106
    assert report["proven_savings_eur"] is None
    assert report["baseline_available"] is False


def test_real_new_automatic_subset_preserves_fractional_euros_until_display():
    history = SavingsHistory()
    assert add(history)
    report = history.report(current_date=DAY)
    assert report["today"]["solar_kwh"] == pytest.approx(2/60, abs=1e-6)
    assert report["today"]["estimated_benefit_eur"] == .009
    assert report["today"]["power_estimated"] is False
    assert report["today"]["power_quality_unknown"] is False


def test_zero_automatic_watts_does_not_count_manual_wallbox_or_whole_house_solar():
    history = SavingsHistory()
    add(history, automatic_w=0, grid_w=-2000, pv_w=5000)
    report = history.report(current_date=DAY)
    assert report["today"]["estimated_benefit_eur"] == 0
    assert report["today"]["solar_kwh"] == 0
    assert "Autonoom Wallbox-laden" in report["excluded"]


@pytest.mark.parametrize("pv,grid,watts,expected", [(1000, 0, 2000, 1000),
                                                      (1000, -800, 2000, 200),
                                                      (0, 0, 2000, 0)])
def test_actual_pv_bounds_estimated_consumer_power(pv, grid, watts, expected):
    history = SavingsHistory()
    add(history, pv_w=pv, grid_w=grid, automatic_w=watts, power_estimated=True)
    row = history.records[DAY]["automatic"]
    assert row["solar_kwh"] == pytest.approx(expected/60/1000)
    assert row["estimated_value_eur"] == pytest.approx(expected/60/1000*.27)
    assert history.report(current_date=DAY)["today"]["power_estimated"] is True


def test_import_and_battery_are_assigned_before_any_solar_claim():
    history = SavingsHistory()
    add(history, grid_w=800, automatic_w=2000, battery_discharge_w=500)
    row = history.records[DAY]["automatic"]
    assert row["grid_kwh"] == pytest.approx(.8/60)
    assert row["battery_kwh"] == pytest.approx(.5/60)
    assert row["solar_kwh"] == pytest.approx(.7/60)


@pytest.mark.parametrize("field", ["pv_w", "battery_discharge_w"])
def test_unknown_attribution_is_unknown_not_free_solar(field):
    history = SavingsHistory()
    add(history, **{field: None})
    report = history.report(current_date=DAY)
    assert report["today"]["estimated_benefit_eur"] is None
    assert report["today"]["solar_coverage_s"] == 0
    assert report["today"]["solar_kwh"] is None
    assert report["today"]["value_partial"]
    assert history.records[DAY]["automatic"]["unattributed_kwh"] > 0


@pytest.mark.parametrize("field", ["import_price_eur_kwh", "export_price_eur_kwh"])
def test_missing_tariff_is_unknown_not_zero(field):
    history = SavingsHistory()
    add(history, **{field: None})
    report = history.report(current_date=DAY)
    assert report["today"]["estimated_benefit_eur"] is None
    assert report["today"]["solar_kwh"] > 0
    assert report["today"]["priced_s"] == 0


def test_negative_spread_is_not_falsely_reported_as_savings():
    history = SavingsHistory()
    add(history, import_price_eur_kwh=-.10, export_price_eur_kwh=.03)
    assert history.report(current_date=DAY)["today"]["estimated_benefit_eur"] == pytest.approx(-.004333, abs=1e-6)


def test_tariff_changes_do_not_reprice_previous_intervals():
    history = SavingsHistory()
    add(history)
    add(history, import_price_eur_kwh=.50, export_price_eur_kwh=.10)
    assert history.report(current_date=DAY)["today"]["estimated_benefit_eur"] == pytest.approx(.009 + .4/30, abs=1e-6)


def test_unpriced_periods_leave_a_qualified_known_subtotal():
    history = SavingsHistory()
    add(history)
    add(history, import_price_eur_kwh=None)
    result = history.report(current_date=DAY)["today"]
    assert result["estimated_benefit_eur"] == .009
    assert result["priced_s"] == 60 and result["coverage_s"] == 120
    assert result["value_partial"] is True


@pytest.mark.parametrize("override", [{"dt_s": 0}, {"dt_s": 121}, {"dt_s": -1},
                                     {"grid_w": None}, {"automatic_w": None},
                                     {"grid_w": math.nan}, {"day": "yesterday"},
                                     {"day": "2026-02-30"}, {"dt_s": True}])
def test_invalid_intervals_create_no_money_or_history(override):
    history = SavingsHistory()
    assert not add(history, **override)
    assert history.records == {}


def test_snapshot_restore_preserves_totals_without_backfill_or_offline_energy():
    history = SavingsHistory()
    add(history, timestamp=1200)
    restored = SavingsHistory()
    restored.restore(history.snapshot())
    assert restored.report(current_date=DAY) == history.report(current_date=DAY)
    assert not add(restored, timestamp=1200)
    assert restored.report(current_date=DAY)["today"]["estimated_benefit_eur"] == .009
    add(restored, timestamp=9000)
    assert restored.report(current_date=DAY)["today"]["coverage_s"] == 120


def test_capture_before_rollover_keeps_distinct_real_daily_records():
    history = SavingsHistory()
    history.capture(legacy(), economy_enabled=True)
    add(history)
    history.capture(legacy(), economy_enabled=True)
    history.capture(legacy(date="2026-10-03", managed_solar_kwh=0, estimated_value_eur=0), economy_enabled=True)
    add(history, day="2026-10-03")
    report = history.report(current_date="2026-10-03")
    assert report["today"]["estimated_benefit_eur"] == .009
    assert report["available_period"]["estimated_benefit_eur"] == .018
    assert report["available_period"]["start_date"] == DAY
    assert report["available_period"]["recorded_days"] == 2
    assert report["managed_reference"]["available_period"]["estimated_benefit_eur"] == .2106


def test_no_lifetime_energy_counter_can_be_reconstructed_into_saved_euros():
    report = build_savings_report({"energy_kwh": 5000, "date": DAY})
    assert report["today"]["estimated_benefit_eur"] is None
    assert report["managed_reference"]["today"]["estimated_benefit_eur"] is None


def test_current_date_does_not_show_yesterday_as_today_or_future_money():
    history = SavingsHistory()
    add(history)
    add(history, day="2026-10-04")
    report = history.report(legacy(), current_date="2026-10-03")
    assert report["today"]["estimated_benefit_eur"] is None
    assert report["available_period"]["estimated_benefit_eur"] == .009


def test_retention_is_bounded_at_90_dates_without_monthly_or_yearly_extrapolation():
    history = SavingsHistory()
    from datetime import date, timedelta
    start = date(2026, 1, 1)
    for index in range(110):
        add(history, day=(start + timedelta(days=index)).isoformat())
    assert len(history.records) == 90
    report = history.report(current_date="2026-12-31")
    assert report["available_period"]["recorded_days"] == 90
    assert report["available_period"]["estimated_benefit_eur"] == pytest.approx(.81)
    assert "yearly" not in report


def test_restore_rejects_malformed_data_and_never_counts_duplicate_days_twice():
    history = SavingsHistory()
    add(history)
    payload = history.snapshot()
    payload["records"] += [deepcopy(payload["records"][0]), None, {"date": "invalid"}]
    restored = SavingsHistory()
    restored.restore(payload)
    assert len(restored.records) == 1
    assert restored.report(current_date=DAY)["available_period"]["estimated_benefit_eur"] == .009
    restored.restore({"version": 999, "records": payload["records"]})
    assert restored.records == {}


def test_corrupt_restored_price_total_is_unknown_not_zero():
    history = SavingsHistory()
    add(history)
    payload = history.snapshot()
    payload["records"][0]["automatic"]["estimated_value_eur"] = float("nan")
    restored = SavingsHistory()
    restored.restore(payload)
    assert restored.report(current_date=DAY)["today"]["estimated_benefit_eur"] is None


def test_runtime_specific_gap_guard_can_be_stricter_than_120_seconds():
    history = SavingsHistory()
    assert not add(history, dt_s=60, max_gap_s=30)
    assert history.records == {}


def test_disabled_legacy_economy_does_not_display_a_zero_as_known_benefit():
    report = build_savings_report(legacy(estimated_value_eur=0), economy_enabled=False)
    assert report["managed_reference"]["today"]["estimated_benefit_eur"] is None


def test_reporting_is_read_only_and_never_overwrites_recorded_history():
    history = SavingsHistory()
    add(history)
    stats = legacy()
    old_stats, old_history = deepcopy(stats), history.snapshot()
    history.report(stats, economy_enabled=True, power_estimated=True, current_date=DAY)
    assert history.snapshot() == old_history and stats == old_stats
    exported = history.snapshot()
    exported["records"][0]["automatic"]["solar_kwh"] = 9999
    assert history.snapshot() == old_history


def test_explanations_separate_estimate_from_electricity_cost_and_causal_saving():
    report = build_savings_report()
    assert "afnameprijs − injectievergoeding" in report["formula"]
    assert "niet nogmaals" in report["cost_note"]
    assert "niet bewezen" in report["not_proven"]
    assert "Capaciteitstarief" in report["excluded"]
    assert "handmatige start of boost" in report["included"]
