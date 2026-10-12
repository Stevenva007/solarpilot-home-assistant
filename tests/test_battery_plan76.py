"""Battery advice must conserve energy at every point of the horizon."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot.battery_plan import plan_battery


def make_slots(net_w, *, prices=None, known=None):
    start = datetime(2026, 10, 12, 0, tzinfo=timezone.utc)
    return [SimpleNamespace(start=start + timedelta(hours=i),
                            base_w=max(0, net), pv_w=max(0, -net),
                            planned_load_w=0, battery_w=999,
                            import_price=prices[i] if prices else .3,
                            pv_available=known[i] if known else True)
            for i, net in enumerate(net_w)]


def battery(**values):
    return {"available_kwh": 10, "soc_pct": 20,
            "min_soc_pct": 20, "max_soc_pct": 95,
            "power_w": 3000, "round_trip_efficiency": .9, **values}


def settings(**values):
    return {"battery_advisory": True, "pv_reserve_w": 0,
            "price_optimisation": True, **values}


def assert_conserves_energy(meta):
    energy = meta["initial_soc_kwh"]
    for row in meta["soc_trajectory"]:
        assert row["soc_start_kwh"] == pytest.approx(energy)
        energy += row["charge_ac_kwh"] - row["discharge_ac_kwh"] - row["loss_kwh"]
        assert row["soc_end_kwh"] == pytest.approx(energy)
        assert not (row["charge_ac_kwh"] and row["discharge_ac_kwh"])
    assert meta["final_soc_kwh"] == pytest.approx(energy)
    assert energy == pytest.approx(meta["initial_soc_kwh"] + meta["charge_ac_kwh"]
                                   - meta["discharge_ac_kwh"] - meta["loss_kwh"])


def test_future_pv_cannot_fund_earlier_discharge():
    slots = make_slots([2000, -3000, 2000])
    meta = plan_battery(slots, settings(), 1, battery())
    assert slots[0].battery_w == 0
    assert slots[1].battery_w == 3000
    assert slots[2].battery_w == -2000
    assert_conserves_energy(meta)


def test_roundtrip_efficiency_reduces_delivered_energy():
    slots = make_slots([-1000, 1000])
    meta = plan_battery(slots, settings(), 1, battery(round_trip_efficiency=.81))
    assert slots[0].battery_w == pytest.approx(1000)
    assert slots[1].battery_w == pytest.approx(-810)
    assert meta["loss_kwh"] == pytest.approx(.19)
    assert meta["final_soc_kwh"] == pytest.approx(2)
    assert_conserves_energy(meta)


def test_distinct_ac_power_limits_and_soc_envelope():
    slots = make_slots([-5000, -5000, 5000, 5000, 5000])
    meta = plan_battery(slots, settings(), 1,
                        battery(charge_power_w=1000, discharge_power_w=500,
                                min_soc_pct=20, max_soc_pct=30))
    assert max(s.battery_w for s in slots) <= 1000
    assert min(s.battery_w for s in slots) >= -500
    assert all(2 - 1e-12 <= row["soc_end_kwh"] <= 3 + 1e-12
               for row in meta["soc_trajectory"])
    assert_conserves_energy(meta)


def test_explicit_zero_power_never_falls_back_to_legacy_power():
    slots = make_slots([-5000, 5000])
    meta = plan_battery(slots, settings(), 1,
                        battery(soc_pct=50, charge_power_w=0, discharge_power_w=0))
    assert [s.battery_w for s in slots] == [0, 0]
    assert meta["final_soc_kwh"] == 5


def test_no_grid_charge_export_discharge_or_missing_forecast_actions():
    slots = make_slots([-3000, 5000, 5000, -2000], known=[True, False, True, True])
    meta = plan_battery(slots, settings(pv_reserve_w=200), 1, battery())
    assert slots[0].battery_w == 2800
    assert slots[1].battery_w == 0
    assert slots[2].battery_w <= 0
    assert slots[3].battery_w >= 0
    assert meta["missing_pv_slots"] == 1
    for slot in slots:
        net = slot.base_w + slot.planned_load_w - slot.pv_w
        if slot.battery_w > 0:
            assert net + slot.battery_w <= 0
        elif slot.battery_w < 0:
            assert net + slot.battery_w >= -1e-9
    assert_conserves_energy(meta)


@pytest.mark.parametrize("soc,net", [(10, [-100, -500, 3000]), (99, [50, 50, -3000])])
def test_initial_soc_outside_operating_envelope_is_preserved(soc, net):
    slots = make_slots(net)
    meta = plan_battery(slots, settings(), 1, battery(soc_pct=soc))
    assert meta["initial_soc_kwh"] == pytest.approx(soc / 10)
    assert meta["soc_trajectory"][0]["soc_start_kwh"] == pytest.approx(soc / 10)
    if soc < 20:
        assert meta["final_soc_kwh"] < 2
        assert slots[2].battery_w == 0
    else:
        assert meta["final_soc_kwh"] > 9.5
        assert slots[2].battery_w == 0
    assert_conserves_energy(meta)


def test_price_threshold_applies_to_discharge_and_can_be_disabled():
    slots = make_slots([1000, 1000, 1000], prices=[.1, .3, .5])
    meta = plan_battery(slots, settings(), 1, battery(soc_pct=90))
    assert slots[0].battery_w == 0
    assert slots[1].battery_w == slots[2].battery_w == -1000
    assert meta["discharge_price_threshold"] == .3
    plan_battery(slots, settings(price_optimisation=False), 1, battery(soc_pct=90))
    assert [s.battery_w for s in slots] == [-1000, -1000, -1000]


def test_empty_disabled_missing_inputs_clear_old_plan():
    assert plan_battery([], settings(), 1, battery())["status"] == "no_slots"
    slots = make_slots([-1000])
    assert plan_battery(slots, settings(), 1, None)["status"] == "unavailable"
    assert slots[0].battery_w == 0
    slots[0].battery_w = 999
    assert plan_battery(slots, settings(battery_advisory=False), 1, battery())["status"] == "disabled"
    assert slots[0].battery_w == 0


@pytest.mark.parametrize("values", [{"soc_pct": None}, {"soc_pct": -1}, {"soc_pct": 101},
                                   {"available_kwh": float("nan")}, {"min_soc_pct": 96},
                                   {"power_w": -1}, {"power_w": None},
                                   {"round_trip_efficiency": 0}, {"round_trip_efficiency": 1.1}])
def test_invalid_battery_inputs_fail_closed(values):
    slots = make_slots([-3000, 3000])
    meta = plan_battery(slots, settings(), 1, battery(**values))
    assert meta["status"] == "invalid_input"
    assert meta["warnings"]
    assert [s.battery_w for s in slots] == [0, 0]


def test_invalid_horizon_fails_before_any_partial_charge():
    slots = make_slots([-3000, 3000])
    slots[1].base_w = float("inf")
    meta = plan_battery(slots, settings(), 1, battery())
    assert meta["status"] == "invalid_input"
    assert [s.battery_w for s in slots] == [0, 0]
    slots = make_slots([-3000, 3000])[::-1]
    assert plan_battery(slots, settings(), 1, battery())["status"] == "invalid_input"


def test_short_slots_obey_energy_and_reserve_limits():
    slots = make_slots([-1000, 1000])
    meta = plan_battery(slots, settings(pv_reserve_w=100), .25, battery(round_trip_efficiency=1))
    assert [s.battery_w for s in slots] == pytest.approx([900, -900])
    assert meta["charge_ac_kwh"] == pytest.approx(.225)
    assert meta["loss_kwh"] == 0
    assert_conserves_energy(meta)


@pytest.mark.parametrize("duration", [0, -1, None, float("nan"), float("inf")])
def test_invalid_slot_duration_fails_closed(duration):
    slots = make_slots([-3000, 3000])
    assert plan_battery(slots, settings(), duration, battery())["status"] == "invalid_input"
    assert [s.battery_w for s in slots] == [0, 0]


def test_invalid_dynamic_import_price_fails_closed():
    slots = make_slots([-3000, 3000], prices=[.3, float("nan")])
    assert plan_battery(slots, settings(), 1, battery())["status"] == "invalid_input"
    assert [s.battery_w for s in slots] == [0, 0]


def test_overlapping_slots_cannot_double_count_battery_energy():
    slots = make_slots([-3000, 3000])
    assert plan_battery(slots, settings(), 2, battery())["status"] == "invalid_input"
    assert [s.battery_w for s in slots] == [0, 0]
