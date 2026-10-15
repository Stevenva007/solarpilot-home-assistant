"""Read existing native cloud-energy periods; never fetch or relabel history.

Aquarea 1.5.4 keeps the sensor's actual aggregation start separately from its
HA report time. In particular an upgraded sensor can temporarily retain an old
local period. Neither export time nor a friendly name proves its cloud day.
Calendar bounds identify the aggregate, not measured coverage or completeness.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
import math


_KEYS = {
    "energy_consumption": ("day", "total"),
    "heating_energy_consumption": ("day", "heating"),
    "cooling_energy_consumption": ("day", "cooling"),
    "tank_energy_consumption": ("day", "tank"),
    "accumulated_energy_consumption": ("month", "total"),
    "heating_accumulated_energy_consumption": ("month", "heating"),
    "cooling_accumulated_energy_consumption": ("month", "cooling"),
    "tank_accumulated_energy_consumption": ("month", "tank"),
}


def _aware(value):
    if not isinstance(value, datetime) or value.tzinfo is None:
        return None
    try:
        stamp = value.timestamp()
        return value if math.isfinite(stamp) and 0 < stamp <= 4102444800 else None
    except (TypeError, ValueError, OverflowError, OSError):
        return None


def _number(value):
    if isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) and value >= 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def period_evidence(provider, key, *, period_start, fetched_at, reported_at, captured_at):
    """Project only an observed native period under the exact verified contract.

    The caller establishes source identity; this pure projection never invents
    a start from now, a source label, the entity state or the fetch timestamp.
    End is the exclusive calendar boundary, not the end of measured coverage.
    """
    if not isinstance(key, str) or key not in _KEYS:
        return None
    provider = provider if isinstance(provider, dict) else {}
    known = (provider.get("integration_loaded") is True
             and provider.get("integration_domain") == "aquarea"
             and provider.get("integration_version") == "1.5.4"
             and provider.get("library_distribution") == "aioaquarea-ng"
             and provider.get("library_version") == "1.3.1")
    start, fetched, reported, captured = map(_aware, (period_start, fetched_at, reported_at, captured_at))
    period, scope = _KEYS[key]
    result = {"schema": 1, "read_only": True, "source_kind": "panasonic_cloud_energy",
              "provider": {name: provider.get(name) if isinstance(provider.get(name), str)
                           and len(provider[name]) <= 80 else None
                           for name in ("integration_domain", "integration_version", "library_distribution", "library_version")},
              "aggregation": period, "scope": scope, "timezone": "UTC" if known else None,
              "period_start": None, "period_end": None, "period_end_exclusive": True,
              "reported_period_start": start.isoformat() if start else None,
              "period_basis": "native_sensor_period_being_processed",
              "source_fetched_at": fetched.isoformat() if fetched else None,
              "source_reported_at": reported.isoformat() if reported else None,
              "source_fetch_age_s": (captured-fetched).total_seconds() if captured and fetched else None,
              "source_report_age_s": (captured-reported).total_seconds() if captured and reported else None,
              "freshness_evaluated": False, "period_contains_capture": None,
              "coverage_start": None, "coverage_end": None, "coverage_complete": False,
              "status": "unknown", "reason_code": "cloud_period_contract_unverified"}
    if not known:
        return result
    if start is None:
        return {**result, "reason_code": "cloud_period_start_missing"}
    if (start.utcoffset() != timedelta(0) or any((start.hour, start.minute, start.second, start.microsecond))
            or period == "month" and start.day != 1):
        return {**result, "reason_code": "cloud_period_start_not_utc_boundary"}
    if (captured is None or fetched is None or reported is None
            or fetched > captured + timedelta(seconds=5) or reported > captured + timedelta(seconds=5)
            or start > captured + timedelta(seconds=5)):
        return {**result, "reason_code": "cloud_period_original_time_unverified"}
    if period == "day":
        end = start + timedelta(days=1)
    else:
        end = start.replace(year=start.year + (start.month == 12), month=start.month % 12 + 1)
    return {**result, "status": "known_period", "reason_code": "native_cloud_period",
            "period_start": start.isoformat(), "period_end": end.isoformat(),
            "period_contains_capture": start <= captured < end}


def cloud_energy_periods(hass, refs, provider, *, captured_at=None):
    """Capture only exact registered native sensor periods on the HA loop.

    No entity update, recorder read, restore-data read, network call or device
    write is made. Missing/foreign bindings do not acquire period metadata.
    Only current export snapshots use this result; old samples stay untouched.
    """
    result = {}
    captured_at = captured_at if captured_at is not None else datetime.now(timezone.utc)
    try:
        from homeassistant.helpers import device_registry as dr, entity_registry as er
        from homeassistant.helpers.entity_component import DATA_INSTANCES
        registry, devices = er.async_get(hass), dr.async_get(hass)
        component = hass.data.get(DATA_INSTANCES, {}).get("sensor")
        if component is None:
            return result
        for eid in refs:
            if not isinstance(eid, str) or not eid.startswith("sensor."):
                continue
            try:
                row = registry.async_get(eid)
                if (row is None or row.platform != "aquarea" or row.disabled_by is not None
                        or not isinstance(row.unique_id, str)):
                    continue
                entity = component.get_entity(eid)
                kind = type(entity)
                key = getattr(getattr(entity, "entity_description", None), "key", None)
                if (key not in _KEYS or kind.__module__ != "custom_components.aquarea.sensor"
                        or kind.__name__ != ("EnergyConsumptionSensor" if _KEYS[key][0] == "day"
                                            else "EnergyAccumulatedConsumptionSensor")):
                    continue
                entry = hass.config_entries.async_get_entry(row.config_entry_id)
                coordinator = entity.coordinator
                info = coordinator.device_info
                native_id = info.device_id
                device = devices.async_get(row.device_id)
                owner = getattr(device, "config_entry_id", None)
                owns_device = (owner == row.config_entry_id if owner is not None else
                               row.config_entry_id in getattr(device, "config_entries", ()))
                if (entry is None or entry.domain != "aquarea" or device is None or not owns_device
                        or {value for domain, value in device.identifiers if domain == "aquarea"} != {native_id}
                        or type(coordinator).__module__ != "custom_components.aquarea.coordinator"
                        or type(coordinator).__name__ != "AquareaDataUpdateCoordinator"
                        or coordinator.hass is not hass or coordinator._entry is not entry
                        or not isinstance(entry.runtime_data, dict) or entry.runtime_data.get(native_id) is not coordinator
                        or not isinstance(native_id, str) or not native_id
                        or entity.unique_id != row.unique_id or row.unique_id != f"{native_id}_{key}"
                        or entity.entity_id != eid or coordinator.last_update_success is not True
                        or entity.available is not True):
                    continue
                state = hass.states.get(eid)
                if (state is None or state.attributes.get("unit_of_measurement") != "kWh"
                        or state.attributes.get("device_class") != "energy" or state.attributes.get("restored") is True
                        or _number(entity.native_value) is None or _number(state.state) != _number(entity.native_value)):
                    continue
                result[eid] = period_evidence(provider, key, period_start=entity.period_being_processed,
                    fetched_at=getattr(coordinator, "_last_monthly_fetch_time", None),
                    reported_at=getattr(state, "last_reported", None), captured_at=captured_at)
            except (AttributeError, KeyError, TypeError, ValueError, RuntimeError, OverflowError):
                continue
    except (ImportError, AttributeError, TypeError, ValueError, RuntimeError):
        return result
    return result
