"""Closed retained source semantics, without device identities or task claims.

The known SDK's DeviceAction describes specialStatus, including its OFF value.
Retaining that contract explains a raw historical field; it never rewrites the
old field, proves global OFF, proves compressor operation or grants control.
"""
from __future__ import annotations

import math
import re

CONTRACT_ID = "aioaquarea_ng_1_3_1_special_status"
MAX_ZONES = 2
MAX_TIME = 4102444800
ACTIONS = frozenset({"OFF", "IDLE", "HEATING", "COOLING", "HEATING_WATER"})
MODES = {"OFF":"off", "HEAT":"heating", "COOL":"cooling",
         "AUTO_HEAT":"heating", "AUTO_COOL":"cooling"}
REASONS = frozenset({"provider_contract_unverified", "native_source_mapping_unverified",
                    "native_typed_snapshot_unverified", "native_poll_not_current",
                    "native_typed_value_unverified", "native_source_not_current",
                    "native_source_value_conflict", "known_special_status_action_mapping"})


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError, OverflowError):
        return None


def _time(value):
    value = _number(value)
    return value if value is not None and 0 < value <= MAX_TIME else None


def _enum(value, allowed, default=None):
    return value if isinstance(value, str) and value in allowed else default


def _version(value):
    return value if isinstance(value, str) and re.fullmatch(r"\d{1,4}\.\d{1,4}\.\d{1,4}(?:[-+][A-Za-z0-9.]{1,16})?", value) else None


def _dict(value):
    return value if isinstance(value, dict) else {}


def _project(raw, captured_at, stale_s, *, retained=False):
    if not isinstance(raw, dict):
        return None
    now = _time(captured_at)
    outer_stale, source_stale = _number(stale_s), _number(raw.get("stale_s"))
    stale = (min(outer_stale, source_stale) if outer_stale is not None and source_stale is not None
             and 0 < outer_stale <= 600 and 0 < source_stale <= 600 else None)
    def fresh(value):
        return bool(now is not None and value is not None and stale is not None and -5 <= now-value <= stale)
    def observed(row):
        stamp, native = _time(row.get("observed_at")), _time(row.get("native_observed_at"))
        return {"observed_at":stamp, "fresh":fresh(stamp),
                "native_observed_at":native, "native_fresh":fresh(native)}

    provider_raw = _dict(raw.get("provider"))
    provider = {"integration_domain":_enum(provider_raw.get("integration_domain"), {"aquarea"}),
                "integration_version":_version(provider_raw.get("integration_version")),
                "library_distribution":_enum(provider_raw.get("library_distribution"), {"aioaquarea-ng"}),
                "library_version":_version(provider_raw.get("library_version"))}
    provider_loaded = raw.get("provider_loaded") is True
    known = (type(raw.get("schema")) is int and raw["schema"] == 1 and raw.get("read_only") is True and provider_loaded
             and raw.get("contract_id") == CONTRACT_ID and raw.get("action_semantics") == "special_status"
             and provider["integration_domain"] == "aquarea" and provider["integration_version"] in ("1.5.2", "1.5.3")
             and provider["library_distribution"] == "aioaquarea-ng" and provider["library_version"] == "1.3.1")
    pump_raw, direction_raw, program_raw, tank_raw = (_dict(raw.get(key)) for key in ("pump","direction","program","tank"))
    pump = {"state":_enum(pump_raw.get("state"), {"on","off"}, "unknown"), **observed(pump_raw)}
    direction = {"state":_enum(direction_raw.get("state"), {"IDLE","PUMP","WATER"}), **observed(direction_raw)}
    mode = _enum(program_raw.get("raw_mode"), MODES)
    program = {"state":_enum(program_raw.get("state"), {"heating","cooling","off"}),
               "raw_mode":mode, **observed(program_raw)}
    tank = {"enabled":tank_raw.get("enabled") if type(tank_raw.get("enabled")) is bool else None, **observed(tank_raw)}
    zones_raw = raw.get("zones")
    zones = []
    valid_zones = isinstance(zones_raw, list) and 1 <= len(zones_raw) <= MAX_ZONES and all(isinstance(row,dict) for row in zones_raw)
    if isinstance(zones_raw, list):
        for index, value in enumerate(zones_raw[:MAX_ZONES], 1):
            row = _dict(value)
            zones.append({"number":index,
                          "enabled":row.get("enabled") if type(row.get("enabled")) is bool else None,
                          "state":_enum(row.get("state"), {"heat","cool","auto","off"}), **observed(row)})
    original = _time(raw.get("observed_at"))
    registered = raw.get("native_device_registered") is True
    claimed = raw.get("verified") is True if retained else raw.get("status") == "verified"
    valid_optional = lambda row: (row.get("native_observed_at") is None or _time(row.get("native_observed_at")) is not None)
    typed_rows = (tank_raw.get("enabled") is None or type(tank_raw.get("enabled")) is bool)
    if valid_zones:
        typed_rows = typed_rows and all((row.get("enabled") is None or type(row.get("enabled")) is bool)
                                      and (row.get("state") is None or _enum(row.get("state"), {"heat","cool","auto","off"}) is not None)
                                      for row in zones_raw)
    all_rows = [pump_raw,direction_raw,program_raw,tank_raw,*zones_raw] if valid_zones else []
    verified = bool(known and claimed and provider_loaded and registered and fresh(original)
                    and pump["state"] != "unknown" and direction["state"] is not None and program["state"] is not None
                    and mode is not None and MODES[mode] == program["state"] and valid_zones and typed_rows
                    and all(valid_optional(row) for row in all_rows)
                    and all(row["fresh"] for row in (pump,direction,program,tank,*zones)))
    return {"schema":1, "read_only":True, "provider":provider,
            "contract_id":CONTRACT_ID if known else None, "action_semantics":"special_status" if known else "unknown",
            "verified":verified, "provider_loaded":provider_loaded, "native_device_registered":registered,
            "observed_at":original, "stale_s":stale, "fresh":fresh(original),
            "raw_device_action":_enum(raw.get("raw_device_action"), ACTIONS),
            "reason_code":_enum(raw.get("reason_code"), REASONS, "provider_contract_unverified"),
            "pump":pump, "direction":direction, "program":program, "tank":tank, "zones":zones}


def contract_evidence(raw, captured_at, stale_s):
    """Project one current contract; absent legacy metadata remains absent."""
    return _project(raw, captured_at, stale_s)


def retained_contract_evidence(raw, captured_at, stale_s):
    """Validate closed stored fields and freshness at their original capture.

    No contemporary device, mapping or timestamp is read. Unknown contracts
    cannot be promoted by optimistic booleans, a new library version, private
    strings or a stale source marked fresh. Additional keys are rejected.
    """
    if raw is None:
        return None
    if not isinstance(raw, dict):
        raise ValueError("Ongeldig historisch broncontract")
    clean = _project(raw, captured_at, stale_s, retained=True)
    if clean != raw:
        raise ValueError("Tegenstrijdig historisch broncontract")
    # Equality treats 1 as True in Python; require actual booleans and schema
    # types separately before accepting persisted flags.
    if (type(raw.get("schema")) is not int or raw["schema"] != 1 or raw.get("read_only") is not True
            or any(type(raw.get(key)) is not bool for key in ("verified","provider_loaded","native_device_registered","fresh"))):
        raise ValueError("Ongeldig historisch broncontract")
    for row in [raw["pump"],raw["direction"],raw["program"],raw["tank"],*raw["zones"]]:
        if any(type(row.get(key)) is not bool for key in ("fresh","native_fresh")):
            raise ValueError("Ongeldig historisch broncontract")
        if "enabled" in row and row["enabled"] is not None and type(row["enabled"]) is not bool:
            raise ValueError("Ongeldig historisch broncontract")
    if any(type(row.get("number")) is not int for row in raw["zones"]):
        raise ValueError("Ongeldig historisch broncontract")
    return clean
