"""Independent adversarial checks of the new total-HP electrical deduction.

All source names and readings are fictional. These exercise source evidence,
not a physical heat pump or connection limit.
"""
import asyncio
from datetime import datetime, timezone
import time
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot import heatpump_budget
from custom_components.solar_pilot.heatpump_budget import sg_expected_increment, sg_solar_budget
from custom_components.solar_pilot.sg_transport import ShellyLeaseError
from test_sg_solar_credit69 import metered
from test_sg_transport62 import native, writes


@pytest.mark.parametrize("hp,extra", [(0, 3000), (500, 2500), (750, 2250), (751, 3000), (3000, 3000)])
def test_complete_hp_report_must_fit_the_whole_site_before_reducing_new_load(hp, extra):
    # Whole-site actual load is only 500 W. Up to 250 W asynchronous-meter
    # tolerance is accepted; a cloud report above it cannot erase future SG draw.
    runtime, hass = metered(grid=-3500, pv=4000, hp=hp, reserve=150)
    runtime.sg_boost.settings["expected_power_w"] = 3000
    budget = sg_solar_budget(runtime)
    assert budget["valid"]
    assert budget["available_w"] == 3350
    assert sg_expected_increment(runtime) == extra
    assert not hass.services.calls


def test_incoherent_hp_report_cannot_pass_a_small_live_phase_envelope():
    from dataclasses import replace

    runtime, hass = metered(grid=-3500, pv=4000, hp=3000, reserve=150)
    runtime.sg_boost.settings.update(expected_power_w=3000, threshold_w=2500)
    runtime.phase_settings.update(enabled=True, control_starts=True)
    runtime.phase = replace(runtime.phase, enabled=True, valid=True,
                            block_increase=False, headroom_w=500)
    assert sg_solar_budget(runtime)["available_w"] >= 2500
    allowed, reason = runtime.heat_pump_increase_allowed()
    assert not allowed and "Fasegrens" in reason
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_new_p1_during_preflight_rejects_now_impossible_hp_credit(native):
    runtime, hass = metered(grid=-1000, pv=4000, hp=3000, reserve=0)
    runtime.sg_boost.settings.update(expected_power_w=3000, threshold_w=500)
    runtime.settings["max_import_w"] = 3500
    runtime.phase_settings.update(enabled=True, control_starts=True, limit_w=4000,
        phase_1_entity="sensor.fictional_phase1", phase_2_entity="sensor.fictional_phase2",
        phase_3_entity="sensor.fictional_phase3")
    for n in (1, 2, 3):
        hass.states.set(f"sensor.fictional_phase{n}", 1000, {"unit_of_measurement": "W"})
    assert runtime.sg_dispatch_allowed(automatic=True)
    native.adapter.before_on = lambda: runtime.sg_dispatch_allowed(automatic=True)
    native.device.pause_read = asyncio.Event()
    native.device.release_read = asyncio.Event()
    pending = asyncio.create_task(native.adapter.set_on(300))
    await asyncio.wait_for(native.device.pause_read.wait(), timeout=2)
    # HP has actually stopped but its cloud report has not changed yet.
    # Current P1 proves the old 3 kW no longer fits. Full future SG draw must
    # be reconsidered, and now exceeds the live phase room.
    hass.states.set("sensor.grid", -3500, {"unit_of_measurement": "W"})
    for n in (1, 2, 3):
        hass.states.set(f"sensor.fictional_phase{n}", 3000, {"unit_of_measurement": "W"})
    native.device.release_read.set()
    with pytest.raises(ShellyLeaseError) as caught:
        await pending
    assert caught.value.code == "dispatch_changed" and not caught.value.command_attempted
    assert runtime._sg_dispatch_rejection["code"] == "phase_limit"
    assert writes(native) == [] and not hass.services.calls


def test_hp_used_only_for_electrical_room_still_constrains_original_budget_time():
    runtime, hass = metered(grid=1000, pv=4000, hp=800, reserve=0)
    runtime.sg_boost.settings["expected_power_w"] = 3000
    hp = hass.states.get("sensor.public_hp")
    site_stamp = hass.states.get("sensor.grid").last_reported.timestamp()
    hp_stamp = site_stamp-20
    hp.last_reported = hp.last_updated = datetime.fromtimestamp(hp_stamp, timezone.utc)
    budget = sg_solar_budget(runtime)
    # There is no HP solar attribution at this imported balance, but the
    # 800 W is still being deducted from the future 3 kW electrical envelope.
    assert budget["hp_solar_w"] == 0
    assert sg_expected_increment(runtime, budget) == 2200
    assert budget["hp_power_reported_at"] == hp_stamp
    assert budget["stamp"] <= hp_stamp
    assert not hass.services.calls


def test_manual_new_request_waits_for_hp_report_newer_than_the_last_command():
    runtime, hass = metered(grid=1000, pv=4000, hp=800, reserve=0)
    runtime.sg_boost.settings["expected_power_w"] = 3000
    runtime.settings["max_import_w"] = 3500
    runtime.sg_boost._manual_control = {"mode": "on", "expires_at": time.time()+1800, "duration_s": 1800}
    runtime.sg_boost._manual_deadline = time.monotonic()+1800
    site_stamp = hass.states.get("sensor.grid").last_reported.timestamp()
    hp = hass.states.get("sensor.public_hp")
    hp.last_reported = hp.last_updated = datetime.fromtimestamp(site_stamp-20, timezone.utc)
    runtime.last_issued_wall = site_stamp-10
    assert not runtime.sg_dispatch_allowed()
    assert runtime._sg_dispatch_rejection["code"] == "settle"
    assert not hass.services.calls


def test_reusing_a_budget_cannot_turn_aged_hp_credit_into_fresh_zero_extra(monkeypatch):
    runtime, hass = metered(grid=-1000, pv=4000, hp=3000, reserve=0)
    runtime.sg_boost.settings["expected_power_w"] = 3000
    budget = sg_solar_budget(runtime)
    stamp = budget["hp_power_reported_at"]
    assert sg_expected_increment(runtime, budget) == 0
    monkeypatch.setattr(heatpump_budget, "time", SimpleNamespace(time=lambda: stamp+121))
    assert sg_expected_increment(runtime, budget) == 3000
    assert budget["hp_power_reported_at"] == stamp
    assert not hass.services.calls
