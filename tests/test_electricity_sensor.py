"""Execute real sensor properties with isolated entity doubles (not HA Core)."""
import ast
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace
from zoneinfo import ZoneInfo
import pytest
from custom_components.solar_pilot.electricity_cost import DailyElectricityCost


def sensor_class():
    source = Path(__file__).resolve().parents[1] / "custom_components/solar_pilot/sensor.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    nodes = [node for node in tree.body if (isinstance(node, ast.ClassDef) and node.name == "SolarSensor")
             or (isinstance(node, ast.FunctionDef) and node.name == "energy_display")
             or (isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "COST_SENSORS" for t in node.targets))]
    class Base:
        def __init__(self, runtime, suffix, name, device_id=None):
            self.runtime, self.suffix, self.key = runtime, suffix, device_id
    class SensorEntity: pass
    ns = {"SolarEntity": Base, "SensorEntity": SensorEntity, "datetime": datetime, "timezone": timezone,
          "SensorDeviceClass": SimpleNamespace(MONETARY="monetary"),
          "SensorStateClass": SimpleNamespace(TOTAL="total")}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), ns)
    return ns["SolarSensor"]


@pytest.mark.parametrize("suffix", ["electricity_cost_today", "electricity_import_cost_today",
                                   "electricity_export_revenue_today", "electricity_pv_avoided_today"])
def test_cost_sensor_cached_monetary_total_and_local_midnight(suffix):
    now = datetime(2026, 9, 27, 12, tzinfo=ZoneInfo("Europe/Brussels"))
    ledger = DailyElectricityCost()
    ledger.seed_legacy({"date":"2026-09-27", "site_import_kwh":10, "site_export_kwh":6,
                       "pv_kwh":11, "pv_self_used_kwh":5, "samples_s":43200}, now, .3, .03)
    ledger.cached = ledger.overview(now)
    runtime = SimpleNamespace(electricity_cost=ledger)
    def no_io(): raise AssertionError("Must not compute the whole EMS from a sensor property")
    runtime.ems_overview = no_io
    sensor = sensor_class()(runtime, suffix, "Cost")
    assert sensor._attr_device_class == "monetary"
    assert sensor._attr_state_class == "total"
    assert sensor._attr_native_unit_of_measurement == "EUR"
    assert sensor.last_reset == datetime(2026, 9, 26, 22, tzinfo=timezone.utc)
    assert isinstance(sensor.native_value, float)
    assert sensor.extra_state_attributes["date"] == "2026-09-27"


def test_unknown_cost_never_publishes_reset_with_a_missing_number():
    runtime = SimpleNamespace(electricity_cost=SimpleNamespace(cached={"date":"2026-09-27", "reset_timestamp":123}))
    sensor = sensor_class()(runtime, "electricity_cost_today", "Cost")
    assert sensor.native_value is None and sensor.last_reset is None
