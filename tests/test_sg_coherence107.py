"""Asynchronous EV polls never manufacture reclaimable SG solar energy."""
import pytest

from custom_components.solar_pilot.heatpump_budget import sg_solar_budget
from test_priority106 import solar_wallbox


def report(hass, entity, watts, age=0):
    hass.states.set(entity, watts, {"unit_of_measurement": "W"}, age=age)


def test_recent_but_inconsistent_ev_report_cannot_start_sg():
    runtime, hass = solar_wallbox()
    # The EV poll is within 120 s, but newer P1/PV imply a smaller whole load.
    report(hass, "sensor.public_ev_power", 4400, age=75)
    report(hass, "sensor.public_pv", 3300)
    report(hass, "sensor.grid", -1100)
    budget = sg_solar_budget(runtime)
    assert budget["valid"] and budget["available_w"] == 950
    assert budget["ev_solar_w"] == 0 and budget["eligible_w"] == 950
    assert budget["ev_reported_at"] is None
    assert "P1/PV-balans" in budget["ev_credit_reason"]
    assert not runtime.sg_dispatch_allowed(automatic=True)
    assert not hass.services.calls


def test_source_recovery_restores_credit_without_changing_measurement_time():
    runtime, hass = solar_wallbox()
    report(hass, "sensor.public_ev_power", 4400, age=75)
    report(hass, "sensor.public_pv", 3300)
    report(hass, "sensor.grid", -1100)
    assert sg_solar_budget(runtime)["ev_solar_w"] == 0
    report(hass, "sensor.public_ev_power", 1600)
    budget = sg_solar_budget(runtime)
    assert budget["ev_solar_w"] == 1600
    assert budget["ev_reported_at"] == hass.states.get("sensor.public_ev_power").last_reported.timestamp()
    assert budget["ev_credit_reason"] is None
    assert not hass.services.calls


def test_inconsistent_ev_does_not_block_independent_actual_export():
    runtime, hass = solar_wallbox()
    report(hass, "sensor.public_pv", 8000)
    report(hass, "sensor.grid", -6000)
    report(hass, "sensor.public_ev_power", 5000)
    budget = sg_solar_budget(runtime)
    assert budget["ev_solar_w"] == 0
    assert budget["available_w"] == budget["eligible_w"] == 5850
    assert runtime.sg_dispatch_allowed(automatic=True)
    assert not hass.services.calls


@pytest.mark.parametrize("hp,ev,accepted", [(0, 4250, True), (0, 4251, False),
    (2000, 2250, True), (2000, 2251, False)])
def test_combined_disjoint_hp_and_ev_fit_actual_site_load_with_small_tolerance(hp, ev, accepted):
    runtime, hass = solar_wallbox()
    report(hass, "sensor.public_pv", 5000)
    report(hass, "sensor.grid", -1000)
    report(hass, "sensor.public_hp", hp)
    report(hass, "sensor.public_ev_power", ev)
    budget = sg_solar_budget(runtime)
    assert (budget["ev_solar_w"] > 0) is accepted
    assert budget["available_w"] == 850
    assert not hass.services.calls


def test_final_dispatch_rejects_credit_after_later_pv_drop():
    runtime, hass = solar_wallbox()
    assert runtime.sg_dispatch_allowed(automatic=True)
    report(hass, "sensor.public_pv", 3000)
    assert not runtime.sg_dispatch_allowed(automatic=True)
    assert runtime._sg_dispatch_rejection["code"] == "solar_threshold"
    assert not hass.services.calls


def test_live_sg_renewal_keeps_existing_soft_buffer_and_raw_hard_limit():
    from test_sg_timed84 import manual_on
    runtime, hass = solar_wallbox()
    manual_on(runtime)
    runtime.sg_boost.relay_confirmed = runtime.sg_boost.relay_on = True
    report(hass, "sensor.public_pv", 1000)
    report(hass, "sensor.public_ev_power", 5000)
    # The new coherence check removes start credit, not an admitted lease.
    assert runtime.sg_dispatch_allowed(renewal=True)
    report(hass, "sensor.grid", 4001)
    assert not runtime.sg_dispatch_allowed(renewal=True)
    assert runtime._sg_dispatch_rejection["code"] == "net_limit"
    assert not hass.services.calls
