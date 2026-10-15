"""Original native aggregation periods, including UTC/local rollover edges."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import sys
from types import ModuleType, SimpleNamespace as NS
from zoneinfo import ZoneInfo

import pytest

from custom_components.solar_pilot.cloud_energy_period import cloud_energy_periods, period_evidence


UTC = timezone.utc
BRUSSELS = ZoneInfo("Europe/Brussels")
PROVIDER = {"integration_loaded": True, "integration_domain": "aquarea", "integration_version": "1.5.4",
            "library_distribution": "aioaquarea-ng", "library_version": "1.3.1"}


def evidence(start, captured, *, key="energy_consumption", fetched=None, reported=None, provider=None):
    return period_evidence(PROVIDER if provider is None else provider, key, period_start=start,
        fetched_at=fetched or captured-timedelta(minutes=3), reported_at=reported or captured-timedelta(seconds=2),
        captured_at=captured)


@pytest.mark.parametrize("local,expected", [
    ("2026-10-15T00:30:00+02:00", "2026-10-14T00:00:00+00:00"),
    ("2026-10-15T02:30:00+02:00", "2026-10-15T00:00:00+00:00"),
    ("2026-11-01T00:30:00+01:00", "2026-10-31T00:00:00+00:00"),
    ("2026-11-01T01:30:00+01:00", "2026-11-01T00:00:00+00:00"),
    ("2027-01-01T00:30:00+01:00", "2026-12-31T00:00:00+00:00"),
    ("2026-10-15T23:30:00-04:00", "2026-10-16T00:00:00+00:00"),
])
def test_daily_original_cloud_period_is_not_replaced_by_export_local_date(local, expected):
    captured = datetime.fromisoformat(local)
    native_start = datetime.fromisoformat(expected)
    result = evidence(native_start, captured)
    assert result["status"] == "known_period" and result["period_start"] == expected
    assert datetime.fromisoformat(result["period_end"])-native_start == timedelta(days=1)
    assert result["timezone"] == "UTC" and result["period_end_exclusive"] is True
    assert result["coverage_start"] is None and result["coverage_end"] is None
    assert result["coverage_complete"] is False  # Nominal bounds never claim full measured coverage.


@pytest.mark.parametrize("start,end", [
    ("2026-10-01T00:00:00+00:00", "2026-11-01T00:00:00+00:00"),
    ("2026-12-01T00:00:00+00:00", "2027-01-01T00:00:00+00:00"),
    ("2028-02-01T00:00:00+00:00", "2028-03-01T00:00:00+00:00"),
])
def test_monthly_original_period_uses_exclusive_next_cloud_month(start, end):
    result = evidence(datetime.fromisoformat(start), datetime.fromisoformat(end)+timedelta(minutes=30),
                      key="accumulated_energy_consumption")
    assert result["period_start"] == start and result["period_end"] == end
    assert result["aggregation"] == "month"


@pytest.mark.parametrize("day", ["2026-03-29", "2026-10-25"])
def test_cloud_utc_day_stays_24_hours_through_brussels_dst(day):
    start = datetime.fromisoformat(day).replace(tzinfo=UTC)
    result = evidence(start, start+timedelta(hours=12))
    finish = datetime.fromisoformat(result["period_end"])
    assert (finish-start).total_seconds() == 86400
    assert start.astimezone(BRUSSELS).hour != finish.astimezone(BRUSSELS).hour


def test_known_period_is_not_a_freshness_claim_or_renamed_as_current_cloud_day():
    start = datetime(2026, 10, 14, tzinfo=UTC)
    captured = datetime(2026, 10, 15, 12, tzinfo=UTC)
    fetched = start+timedelta(hours=20)
    result = evidence(start, captured, fetched=fetched, reported=fetched)
    assert result["status"] == "known_period" and result["period_start"] == start.isoformat()
    assert result["period_contains_capture"] is False
    assert result["freshness_evaluated"] is False and result["source_fetch_age_s"] == 16*3600
    assert result["source_report_age_s"] == 16*3600 and result["coverage_complete"] is False


@pytest.mark.parametrize("start", [None, "2026-10-15", datetime(2026, 10, 15),
    datetime(2026, 10, 15, tzinfo=BRUSSELS), datetime(2026, 10, 15, 1, tzinfo=UTC)])
def test_missing_or_restored_local_period_does_not_acquire_utc_bounds(start):
    captured = datetime(2026, 10, 15, 12, tzinfo=UTC)
    result = evidence(start, captured)
    assert result["status"] == "unknown" and result["period_start"] is None and result["period_end"] is None
    if isinstance(start, datetime) and start.tzinfo:
        assert result["reported_period_start"] == start.isoformat()


@pytest.mark.parametrize("change", ["version", "sdk", "not_loaded", "future_fetch", "future_report", "missing_capture", "missing_fetch"])
def test_unverified_source_metadata_or_original_times_never_claim_known_period(change):
    provider = dict(PROVIDER)
    start = datetime(2026, 10, 15, tzinfo=UTC)
    capture = start+timedelta(hours=12)
    values = {"period_start": start, "fetched_at": capture-timedelta(minutes=3),
              "reported_at": capture-timedelta(seconds=2), "captured_at": capture}
    if change == "version": provider["integration_version"] = "1.5.5"
    elif change == "sdk": provider["library_version"] = "1.3.2"
    elif change == "not_loaded": provider["integration_loaded"] = 1
    elif change == "future_fetch": values["fetched_at"] = capture+timedelta(seconds=6)
    elif change == "future_report": values["reported_at"] = capture+timedelta(seconds=6)
    elif change == "missing_capture": values["captured_at"] = None
    else: values["fetched_at"] = None
    original = deepcopy(provider)
    result = period_evidence(provider, "energy_consumption", **values)
    assert provider == original
    assert result["status"] == "unknown" and result["period_start"] is None


def setup_source(monkeypatch, *, key="energy_consumption"):
    import homeassistant.helpers.entity_registry as er
    import homeassistant.helpers as helpers
    component_module = ModuleType("homeassistant.helpers.entity_component")
    component_module.DATA_INSTANCES = "entity_components"
    monkeypatch.setitem(sys.modules, component_module.__name__, component_module)
    devices_module = ModuleType("homeassistant.helpers.device_registry")
    monkeypatch.setitem(sys.modules, devices_module.__name__, devices_module)
    monkeypatch.setattr(helpers, "device_registry", devices_module, raising=False)
    eid = "sensor.synthetic_cloud_energy"
    start = datetime(2026, 10, 15, tzinfo=UTC)
    captured = start+timedelta(hours=12)
    row = NS(platform="aquarea", disabled_by=None, config_entry_id="native", device_id="registered",
             unique_id=f"pump_{key}")
    entry = NS(domain="aquarea", runtime_data={})
    device = NS(config_entry_id="native", identifiers={("aquarea", "pump")})
    state = NS(state="4.2", attributes={"unit_of_measurement": "kWh", "device_class": "energy"},
               last_reported=captured-timedelta(seconds=2))
    hass = NS(data={}, config_entries=NS(async_get_entry=lambda _: entry), states=NS(get=lambda _: state))
    coordinator = type("AquareaDataUpdateCoordinator", (), {"__module__": "custom_components.aquarea.coordinator"})()
    coordinator.hass, coordinator._entry = hass, entry
    coordinator.device_info = NS(device_id="pump")
    coordinator.last_update_success = True
    coordinator._last_monthly_fetch_time = captured-timedelta(minutes=3)
    entry.runtime_data["pump"] = coordinator
    entity = type("EnergyAccumulatedConsumptionSensor" if "accumulated" in key else "EnergyConsumptionSensor", (),
                  {"__module__": "custom_components.aquarea.sensor"})()
    entity.entity_description, entity.coordinator = NS(key=key), coordinator
    entity.unique_id, entity.entity_id, entity.available = row.unique_id, eid, True
    entity.native_value, entity.period_being_processed = 4.2, start
    hass.data[component_module.DATA_INSTANCES] = {"sensor": NS(get_entity=lambda _: entity)}
    monkeypatch.setattr(er, "async_get", lambda _: NS(async_get=lambda _: row))
    devices_module.async_get = lambda _: NS(async_get=lambda _: device)
    return NS(hass=hass, eid=eid, entry=entry, row=row, device=device, entity=entity, coordinator=coordinator,
              captured=captured, state=state)


@pytest.mark.parametrize("key,scope", [("energy_consumption", "total"), ("heating_energy_consumption", "heating"),
    ("cooling_energy_consumption", "cooling"), ("tank_energy_consumption", "tank"),
    ("accumulated_energy_consumption", "total"), ("heating_accumulated_energy_consumption", "heating"),
    ("cooling_accumulated_energy_consumption", "cooling"), ("tank_accumulated_energy_consumption", "tank")])
def test_exact_registered_native_source_preserves_period_and_original_times(key, scope, monkeypatch):
    env = setup_source(monkeypatch, key=key)
    if "accumulated" in key:
        env.entity.period_being_processed = env.entity.period_being_processed.replace(day=1)
    result = cloud_energy_periods(env.hass, [env.eid], PROVIDER, captured_at=env.captured)[env.eid]
    assert result["status"] == "known_period" and result["scope"] == scope
    assert result["source_fetched_at"] == env.coordinator._last_monthly_fetch_time.isoformat()
    assert result["source_reported_at"] == env.state.last_reported.isoformat()
    assert result["reported_period_start"] == env.entity.period_being_processed.isoformat()
    assert "pump" not in str(result) and "registered" not in str(result)


@pytest.mark.parametrize("change", ["uid", "entry", "device", "disabled", "provider_class", "foreign_entity_class",
    "not_owned", "ambiguous_device", "unavailable", "restored", "nan", "bool", "state_mismatch", "unit", "foreign_entry", "failed_poll"])
def test_wrong_bindings_optimistic_states_and_unavailable_sources_do_not_acquire_period(change, monkeypatch):
    env = setup_source(monkeypatch)
    if change == "uid": env.row.unique_id = "neighbor_energy_consumption"
    elif change == "entry": env.entry.runtime_data.clear()
    elif change == "device": env.device.identifiers = {("aquarea", "neighbor")}
    elif change == "disabled": env.row.disabled_by = "user"
    elif change == "provider_class": env.coordinator.__class__ = type("Other", (), {})
    elif change == "foreign_entity_class": env.entity.__class__ = type("Other", (), {})
    elif change == "not_owned": env.device.config_entry_id = "neighbor"
    elif change == "ambiguous_device": env.device.identifiers.add(("aquarea", "neighbor"))
    elif change == "unavailable": env.entity.available = False
    elif change == "restored": env.state.attributes["restored"] = True
    elif change == "nan": env.entity.native_value = float("nan")
    elif change == "bool": env.entity.native_value = True
    elif change == "state_mismatch": env.state.state = "9.8"
    elif change == "unit": env.state.attributes["unit_of_measurement"] = "W"
    elif change == "foreign_entry": env.coordinator._entry = NS()
    else: env.coordinator.last_update_success = False
    assert cloud_energy_periods(env.hass, [env.eid], PROVIDER, captured_at=env.captured) == {}
