"""Exercise real status sensor properties with explicit entity/runtime doubles."""
from types import SimpleNamespace

import pytest

from test_electricity_sensor import sensor_class


def runtime(isolated):
    return SimpleNamespace(
        source_isolated_devices=isolated,
        mode="solar", problem="", problem_kind="", restart_recovery_pending=False, restart_blocking=False,
        recovery={}, configs={"a": {"name": "Offline load", "phase_hint": "auto"}},
        states={"a": SimpleNamespace(owned=True, fault="")},
        result=SimpleNamespace(targets={"a": 0}, free_w=100, budget_w=100),
        grid_w=-100, pv_w=500, managed_w=0, settings={"reserve_w": 0, "max_import_w": 0},
        dhw=SimpleNamespace(overview=lambda: {}), overview=lambda: [],
        wallbox_overview=lambda: {}, learning_overview=lambda: {},
        learning_hub=SimpleNamespace(summary=lambda: {}),
        live_options=SimpleNamespace(overview=lambda: {}),
        priority_board=SimpleNamespace(overview=lambda: {}),
        ems_overview=lambda: {}, logs=[], removal_overview=lambda: {},
        entity_id=lambda domain, suffix, *args: f"{domain}.test_{suffix}",
        energy_kwh=0, energy_estimated=False, editable=True, entry=SimpleNamespace(entry_id="test"),
        phase_learning=SimpleNamespace(profile=lambda device_id: {}),
    )


def make_sensor(r, device_id=None):
    cls = sensor_class()
    cls.extra_state_attributes.fget.__globals__["GUIDE_VERSION"] = "synthetic-version"
    return cls(r, "status", "Status", device_id)


@pytest.mark.parametrize(("devices", "reserve"), [
    ({}, 0),
    ({"a": {"name": "Offline load", "reason": "Control status unavailable", "reserve_w": 350}}, 350),
    ({"a": {"name": "Offline load", "reason": "Control status unavailable", "reserve_w": 350},
      "b": {"name": "Other offline load", "reason": "Power source unavailable", "reserve_w": 200}}, 550),
])
def test_global_sensor_publishes_isolated_devices_and_separate_reserve_without_changing_actual_power(devices, reserve):
    r = runtime(devices)
    data = make_sensor(r).extra_state_attributes
    assert data["mode"] == "solar" and not data["restart_recovery_pending"]
    assert not data["restart_blocking"]
    assert data["isolated_devices"] == [{"id": device_id, **details} for device_id, details in devices.items()]
    assert data["isolated_reserve_w"] == reserve
    assert data["managed_w"] == 0
    assert r.source_isolated_devices == devices


@pytest.mark.parametrize("isolated", [False, True])
def test_device_sensor_exposes_local_isolation_without_inventing_a_command_fault(isolated):
    reason = "Control status unavailable"
    r = runtime({"a": {"name": "Offline load", "reason": reason, "reserve_w": 350}} if isolated else {})
    data = make_sensor(r, "a").extra_state_attributes
    assert data["isolated"] is isolated
    assert data["isolation_reason"] == (reason if isolated else "")
    assert data["isolation_reserve_w"] == (350 if isolated else 0)
    assert data["fault"] == "" and data["target_w"] == 0
