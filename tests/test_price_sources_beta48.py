"""Unavailable pricing and missing slots never become cheap planner evidence."""
from datetime import datetime, timezone

import pytest

from test_runtime import build


def pricing():
    runtime, hass = build()
    runtime.economy_settings.update(enabled=True,
                                    import_price_entity="sensor.dynamic_import",
                                    export_price_entity="sensor.dynamic_export",
                                    fixed_import_eur_kwh=.30,
                                    fixed_export_eur_kwh=.03)
    runtime.planner_settings["slot_min"] = 15
    return runtime, hass


@pytest.mark.parametrize("scenario", ["unknown", "unavailable", "restored", "stale", "future"])
def test_unusable_dynamic_price_source_uses_configured_fixed_tariff(scenario):
    runtime, hass = pricing()
    state = scenario if scenario in ("unknown", "unavailable") else .02
    attrs = {"today": [.01] * 24, "restored": scenario == "restored"}
    age = 36*3600+1 if scenario == "stale" else -6 if scenario == "future" else 0
    for eid in ("sensor.dynamic_import", "sensor.dynamic_export"):
        hass.states.set(eid, state, attrs, reported_age=age)
    imports, exports = runtime._planner_prices(4, datetime(2026, 10, 3, 12, tzinfo=timezone.utc))
    assert imports == pytest.approx([.30] * 4)
    assert exports == pytest.approx([.03] * 4)


def test_daily_price_hole_does_not_shift_valid_hours():
    runtime, hass = pricing()
    today = [.10+hour*.01 for hour in range(24)]
    today[11] = "unknown"
    hass.states.set("sensor.dynamic_import", .25, {"today": today})
    # 10:00 remains hour 10; only hour 11 uses the fixed fallback.
    imports, _ = runtime._planner_prices(12, datetime(2026, 10, 3, 10, tzinfo=timezone.utc))
    assert imports == pytest.approx([.20]*4 + [.30]*4 + [.22]*4)


def test_timestamped_price_hole_does_not_extend_prior_cheap_block():
    runtime, hass = pricing()
    hass.states.set("sensor.dynamic_import", .25, {"prices": [
        {"start": "2026-10-03T11:00:00+00:00", "price": .10},
        {"start": "2026-10-03T12:00:00+00:00", "price": "unknown"},
        {"start": "2026-10-03T13:00:00+00:00", "price": .40},
    ]})
    imports, _ = runtime._planner_prices(12, datetime(2026, 10, 3, 11, tzinfo=timezone.utc))
    assert imports == pytest.approx([.10]*4 + [.30]*4 + [.40]*4)


def test_daily_tariff_report_can_be_older_than_six_hours():
    runtime, hass = pricing()
    hass.states.set("sensor.dynamic_import", .25, {"today": [.12]*24}, reported_age=12*3600)
    imports, _ = runtime._planner_prices(4, datetime(2026, 10, 3, 12, tzinfo=timezone.utc))
    assert imports == pytest.approx([.12]*4)


def test_stable_manual_scalar_tariff_is_not_expired_as_dynamic_forecast():
    runtime, hass = pricing()
    runtime.economy_settings["import_price_entity"] = "input_number.fixed_tariff"
    hass.states.set("input_number.fixed_tariff", .23, reported_age=90*86400)
    imports, _ = runtime._planner_prices(4, datetime(2026, 10, 3, 12, tzinfo=timezone.utc))
    assert imports == pytest.approx([.23]*4)


def test_expired_timestamp_blocks_do_not_extend_yesterday_into_new_day():
    runtime, hass = pricing()
    # The entity's own report is current, but these tariff slots expired.
    hass.states.set("sensor.dynamic_import", .25, {"prices": [
        {"start": "2026-10-02T11:00:00+00:00", "price": .01},
        {"start": "2026-10-02T12:00:00+00:00", "price": .02},
    ]})
    imports, _ = runtime._planner_prices(4, datetime(2026, 10, 3, 12, tzinfo=timezone.utc))
    assert imports == pytest.approx([.30]*4)


def test_explicit_price_end_respects_gap_before_next_known_block():
    runtime, hass = pricing()
    hass.states.set("sensor.dynamic_import", .25, {"prices": [
        {"start": "2026-10-03T11:00:00+00:00", "end": "2026-10-03T12:00:00+00:00", "price": .10},
        {"start": "2026-10-03T13:00:00+00:00", "end": "2026-10-03T14:00:00+00:00", "price": .40},
    ]})
    imports, _ = runtime._planner_prices(12, datetime(2026, 10, 3, 11, tzinfo=timezone.utc))
    assert imports == pytest.approx([.10]*4 + [.30]*4 + [.40]*4)


def test_future_first_price_block_cannot_price_current_uncovered_slot():
    runtime, hass = pricing()
    hass.states.set("sensor.dynamic_import", .25, {"prices": [
        {"start": "2026-10-03T13:00:00+00:00", "end": "2026-10-03T14:00:00+00:00", "price": .01},
    ]})
    imports, _ = runtime._planner_prices(8, datetime(2026, 10, 3, 12, tzinfo=timezone.utc))
    assert imports == pytest.approx([.30]*4 + [.01]*4)
