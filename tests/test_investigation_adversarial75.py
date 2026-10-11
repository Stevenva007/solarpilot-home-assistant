"""Independent source-proof stress tests; no household fixtures or services."""
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
import time

import pytest

from custom_components.solar_pilot.investigation import LocalInvestigation
from test_runtime import build


@pytest.fixture
def clock(monkeypatch):
    values = [time.time()]
    monkeypatch.setattr(time, "time", lambda: values[0])
    return values


def source(hass, entity, value, clock, *, age=0, attrs=None):
    hass.states.set(entity, value, {"unit_of_measurement": "W", **(attrs or {})})
    obj = hass.states.get(entity)
    obj.last_reported = datetime.fromtimestamp(clock[0] - age, timezone.utc)
    obj.last_updated = datetime.fromtimestamp(clock[0], timezone.utc)
    return obj


def setup(clock, *, split=False):
    runtime, hass = build(power=True, settings={"pv_entity": "sensor.pv"})
    cfg = ({"power_entity": "", "power_supply1_entity": "sensor.hp_main",
            "power_supply2_entity": "sensor.hp_other", "split_power_confirmed": True}
           if split else {"power_entity": "sensor.hp_total", "power_scope": "total"})
    runtime.panasonic.update_config({**cfg, "stale_s": 120})
    source(hass, "sensor.grid", -1000, clock)
    source(hass, "sensor.pv", 3000, clock)
    source(hass, "sensor.load", 0, clock)
    source(hass, "sensor.hp_main" if split else "sensor.hp_total", -7, clock)
    if split:
        source(hass, "sensor.hp_other", 0, clock)
    return runtime, hass, LocalInvestigation(runtime)


def hp(engine, clock):
    return next(item for item in engine.refresh(clock[0])["items"]
                if item["id"] == "heatpump_meter")


def test_polling_and_newer_attributes_cannot_invent_distinct_source_reports(clock):
    _runtime, hass, engine = setup(clock)
    first = hp(engine, clock)
    original_stamp = hass.states.get("sensor.hp_total").last_reported
    for _ in range(12):
        clock[0] += 6
        obj = hass.states.get("sensor.hp_total")
        obj.state = "-6.5"
        obj.attributes["friendly_name"] = "Meter gewijzigd"
        obj.last_updated = datetime.fromtimestamp(clock[0], timezone.utc)
        current = hp(engine, clock)
    assert current["metrics"]["reports"] == first["metrics"]["reports"] == 1
    assert current["metrics"]["negative_reports"] == 1
    assert not current["hypotheses"]
    assert hass.states.get("sensor.hp_total").last_reported == original_stamp
    assert not hass.services.calls


@pytest.mark.parametrize("age", [121, 1000, -6, -600])
def test_negative_rejection_alone_never_proves_timestamp_freshness(clock, age):
    _runtime, hass, engine = setup(clock)
    for _ in range(6):
        source(hass, "sensor.hp_total", -7, clock, age=age)
        current = hp(engine, clock)
        clock[0] += 61
    assert current["status"] == "check_needed"
    assert current["metrics"]["reports"] == 0
    assert current["metrics"]["negative_reports"] == 0
    assert current["metrics"]["current_w"] is None
    assert not current["hypotheses"]
    assert not hass.services.calls


@pytest.mark.parametrize("stamp", [True, "1000", float("nan"), float("inf"), -1])
def test_malformed_report_time_does_not_fall_back_to_newer_updated_time(clock, stamp):
    _runtime, hass, engine = setup(clock)
    obj = hass.states.get("sensor.hp_total")
    obj.last_reported = SimpleNamespace(timestamp=lambda: stamp)
    current = hp(engine, clock)
    assert current["metrics"]["reports"] == 0
    assert not current["hypotheses"]
    assert current["metrics"]["current_w"] is None


@pytest.mark.parametrize("attrs", [{"restored": True}, {"estimated": True},
                                  {"is_estimated": True}, {"unit_of_measurement": "kWh"},
                                  {"friendly_name": "Estimated power"}])
def test_placeholder_and_energy_sources_do_not_strengthen_negative_hypothesis(clock, attrs):
    _runtime, hass, engine = setup(clock)
    for _ in range(6):
        source(hass, "sensor.hp_total", -7, clock, attrs=attrs)
        current = hp(engine, clock)
        clock[0] += 61
    assert current["metrics"]["reports"] == 0
    assert current["metrics"]["negative_reports"] == 0
    assert not current["hypotheses"]


def test_partial_real_zero_does_not_make_unknown_whole_heatpump_zero(clock):
    _runtime, hass, engine = setup(clock, split=True)
    current = hp(engine, clock)
    assert current["metrics"]["reports"] == 2
    assert current["metrics"]["valid_reports"] == 1
    assert current["metrics"]["negative_reports"] == 1
    assert current["metrics"]["complete_current"] is False
    assert current["metrics"]["current_w"] is None
    hass.states.data.pop("sensor.hp_main")
    clock[0] += 61
    source(hass, "sensor.hp_other", 0, clock)
    missing = hp(engine, clock)
    assert missing["metrics"]["complete_current"] is False
    assert missing["metrics"]["current_w"] is None
    assert missing["metrics"]["negative_reports"] == 1


def test_new_explicit_binding_cannot_inherit_old_negative_pattern(clock):
    runtime, hass, engine = setup(clock)
    for _ in range(6):
        source(hass, "sensor.hp_total", -7, clock)
        old = hp(engine, clock)
        clock[0] += 61
    assert old["hypotheses"]
    runtime.panasonic.settings["power_entity"] = "sensor.replacement"
    source(hass, "sensor.replacement", 0, clock)
    new = hp(engine, clock)
    assert new["status"] == "observed_ok"
    assert new["metrics"]["reports"] == 1
    assert new["metrics"]["negative_reports"] == 0
    assert new["metrics"]["current_w"] == 0
    assert not new["hypotheses"]
    assert not hass.services.calls


def test_source_rebase_to_earlier_report_cannot_count_twice(clock):
    _runtime, hass, engine = setup(clock)
    initial = hp(engine, clock)
    clock[0] += 61
    source(hass, "sensor.hp_total", -8, clock, age=62)
    current = hp(engine, clock)
    assert current["metrics"]["reports"] == initial["metrics"]["reports"] == 1
    assert current["metrics"]["negative_reports"] == 1


def test_restore_retains_history_without_restoring_current_health_or_recounting(clock):
    runtime, hass, engine = setup(clock)
    source(hass, "sensor.hp_total", 0, clock)
    assert hp(engine, clock)["status"] == "observed_ok"
    saved = engine.snapshot()
    restored = LocalInvestigation(runtime)
    restored.restore(saved)
    assert restored.overview(clock[0])["items"] == []
    same = hp(restored, clock)
    assert same["metrics"]["reports"] == 1
    hass.states.get("sensor.hp_total").attributes["restored"] = True
    clock[0] += 61
    invalid = hp(restored, clock)
    assert invalid["status"] == "check_needed"
    assert invalid["metrics"]["current_w"] is None
    assert invalid["metrics"]["reports"] == 1


def test_expired_success_cannot_present_current_complete_power(clock):
    _runtime, hass, engine = setup(clock)
    source(hass, "sensor.hp_total", 0, clock)
    assert hp(engine, clock)["status"] == "observed_ok"
    clock[0] += 121
    expired = next(item for item in engine.overview(clock[0])["items"]
                   if item["id"] == "heatpump_meter")
    assert expired["status"] == "collecting"
    assert expired["metrics"]["complete_current"] is False
    assert expired["metrics"]["current_w"] is None


def test_default_overview_expires_current_claim_without_explicit_now(clock):
    _runtime, hass, engine = setup(clock)
    source(hass, "sensor.hp_total", 0, clock)
    assert hp(engine, clock)["status"] == "observed_ok"
    clock[0] += 121
    expired = next(item for item in engine.overview()["items"]
                   if item["id"] == "heatpump_meter")
    assert expired["status"] == "collecting"
    assert expired["metrics"]["current_w"] is None


def test_new_bad_report_revokes_health_before_next_full_minute_refresh(clock):
    _runtime, hass, engine = setup(clock)
    source(hass, "sensor.hp_total", 0, clock)
    assert hp(engine, clock)["status"] == "observed_ok"
    clock[0] += 5
    source(hass, "sensor.hp_total", -7, clock)
    current = hp(engine, clock)
    assert current["status"] == "collecting"
    assert current["metrics"]["complete_current"] is False
    assert current["metrics"]["current_w"] is None
    assert current["metrics"]["reports"] == 1


def test_unexamined_consumers_cannot_receive_complete_source_health_status(clock):
    runtime, hass, engine = setup(clock)
    for index in range(1, 33):
        runtime.configs[f"extra_{index}"] = {
            "name": f"Verbruiker {index}",
            "power_entity": f"sensor.consumer_{index}" if index < 32 else "",
        }
        if index < 32:
            source(hass, f"sensor.consumer_{index}", 0, clock)
    current = next(item for item in engine.refresh(clock[0])["items"]
                   if item["id"] == "consumer_meters")
    assert current["status"] == "collecting"
    assert current["metrics"]["examined_count"] == 32
    assert current["metrics"]["configured_count"] == 33
    assert current["metrics"]["unexamined_count"] == 1
    assert not hass.services.calls


def test_changed_reserved_meter_ownership_invalidates_prior_hp_source_pattern(clock):
    runtime, hass, engine = setup(clock)
    for _ in range(6):
        source(hass, "sensor.hp_total", -7, clock)
        old = hp(engine, clock)
        clock[0] += 61
    assert old["hypotheses"]
    runtime.configs["a"]["power_entity"] = "sensor.hp_total"
    new = hp(engine, clock)
    assert new["status"] == "check_needed"
    assert new["metrics"]["reports"] == 0
    assert new["metrics"]["negative_reports"] == 0
    assert not new["hypotheses"]
    assert new["metrics"]["current_w"] is None


def test_diagnostic_patterns_cannot_change_configuration_or_sg_ownership(clock):
    runtime, hass, engine = setup(clock)
    before = deepcopy({"site": runtime.settings, "panasonic": runtime.panasonic.settings,
                       "wallbox": runtime.wallbox_settings, "planner": runtime.planner_settings,
                       "entry": runtime.entry.options, "sg": runtime.sg_boost.snapshot()})
    for _ in range(10):
        source(hass, "sensor.hp_total", -7, clock)
        current = hp(engine, clock)
        clock[0] += 61
    assert current["hypotheses"]
    after = {"site": runtime.settings, "panasonic": runtime.panasonic.settings,
             "wallbox": runtime.wallbox_settings, "planner": runtime.planner_settings,
             "entry": runtime.entry.options, "sg": runtime.sg_boost.snapshot()}
    assert after == before
    assert not hass.services.calls
    assert runtime.panasonic.settings["power_entity"] == "sensor.hp_total"
