"""Read-only comparison of explicitly configured sources and original reports.

This module never discovers a template dependency, renews a session, changes a
sign convention, or adds control rights. HA report alignment is not proof that
physical measurements were simultaneous. Missing inventory stays unknown.
"""
from __future__ import annotations

from datetime import datetime
import math


ALIGNMENT_LIMIT_S = 5.0
BALANCE_TOLERANCE_W = 250.0
MAX_COMPARISON_SOURCES = 16
SAFE_TEXT_VALUES = frozenset({
    "charging", "ready", "paused", "scheduled", "waiting for car demand", "locked", "locked, car connected",
    "waiting in queue by eco-smart", "waiting for green energy", "waiting in queue by power boost",
    "full_solar", "full solar", "full green", "eco_smart", "eco-smart", "off", "disabled", "manual", "manueel",
    "zonne-auto · laden", "zonne-auto · wacht op overschot", "zonne-auto · wacht op auto",
    "manueel laden", "manueel laden · klaar", "manueel / solar uit", "laden gestopt",
})


def _finite(value):
    if isinstance(value, bool):
        return None
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError, OverflowError):
        return None


def _original_report(obj, now):
    """Never use capture time or last_changed as a replacement report."""
    if obj is None:
        return None, None
    stamp = getattr(obj, "last_reported", None)
    basis = "last_reported"
    if stamp is None:
        stamp = getattr(obj, "last_updated", None)
        basis = "last_updated"
    if not isinstance(stamp, datetime) or stamp.tzinfo is None:
        return None, None
    try:
        result = _finite(stamp.timestamp())
    except (ValueError, OSError, OverflowError):
        return None, None
    if result is None or not 0 < result <= now + 5:
        return None, None
    return result, basis


def _platform(runtime, entity):
    if not entity:
        return None
    from homeassistant.helpers import entity_registry as er
    registry = er.async_get(runtime.hass)
    entry = getattr(registry, "async_get", lambda _entity: None)(entity)
    platform = getattr(entry, "platform", None)
    # Expose only public integration identifiers, never registry/device data.
    return platform if isinstance(platform, str) and len(platform) <= 80 and all(
        char.isalnum() or char in "_-." for char in platform) else None


def source_report(runtime, entity, role, now, stale_s, *, power=False, signed=False):
    """Bounded generic-role evidence; no entity identity or arbitrary attributes."""
    now, stale = _finite(now), _finite(stale_s)
    configured = isinstance(entity, str) and bool(entity)
    obj = runtime.hass.states.get(entity) if configured else None
    attrs = getattr(obj, "attributes", {})
    attrs = attrs if isinstance(attrs, dict) else {}
    stamp, basis = _original_report(obj, now) if now is not None else (None, None)
    age = now - stamp if now is not None and stamp is not None else None
    fresh = bool(age is not None and stale is not None and stale > 0 and -5 <= age <= stale)
    raw = getattr(obj, "state", None)
    value = str(raw)[:160] if raw is not None else None
    issue = ""
    if not configured:
        issue = "not_configured"
    elif obj is None:
        issue = "missing"
    elif any(attrs.get(key) for key in ("restored", "estimated", "is_estimated")):
        issue = "restored_or_estimated"
    elif any(word in str(attrs.get("friendly_name", "")).casefold() for word in ("geschat", "estimated")):
        issue = "estimated"
    elif value is None or value.casefold() in ("", "unknown", "unavailable", "none"):
        issue = "unavailable"
    elif stamp is None:
        issue = "report_time_unknown"
    elif not fresh:
        issue = "stale"
    watts = None
    if power and not issue:
        number, unit = _finite(raw), attrs.get("unit_of_measurement")
        if number is None or unit not in ("W", "kW"):
            issue = "invalid_power_or_unit"
        else:
            number *= 1000 if unit == "kW" else 1
            if not math.isfinite(number) or abs(number) > 100000 or not signed and number < 0:
                issue = "invalid_power_range"
            else:
                watts = number
    safe_value = str(watts) if power and watts is not None else value.strip().casefold() if not power and value is not None and value.strip().casefold() in SAFE_TEXT_VALUES else None
    report = {"role": role, "configured": configured, "platform": _platform(runtime, entity) if configured else None,
              "value": safe_value, "value_withheld": value is not None and safe_value is None,
              "reported_wall": stamp, "report_time_basis": basis,
              "age_s": age, "stale_limit_s": stale, "fresh": fresh, "usable": not bool(issue), "issue": issue}
    if power:
        report["watts"] = watts
    return report


def wallbox_source_dossier(runtime, now):
    """Configured comparisons are not silently declared template dependencies."""
    settings = getattr(runtime, "wallbox_settings", {})
    settings = settings if isinstance(settings, dict) else {}
    stale = settings.get("stale_s", 300)
    result = {"schema": 1, "read_only": True, "collected_at": _finite(now),
            "session": source_report(runtime, settings.get("session_mode_entity"), "session", now, stale),
            "known_sources": [source_report(runtime, settings.get(key), role, now, stale, power=role == "power")
                              for key, role in (("status_entity", "status"), ("mode_entity", "mode"), ("power_entity", "power"))],
            "dependency_relation": "unknown", "template_formula": "unknown", "template_triggers": "unknown",
            "dependencies": [], "dependency_coverage": "unknown", "dependency_issue": "runtime_unavailable",
            "reassessed_session": False, "control_effect": "none"}
    result.update(_state_template_dependencies(runtime, settings, now, stale))
    return result


def _state_template_dependencies(runtime, settings, now, stale):
    """Inspect only the selected loaded state template, never render or refresh.

    Verified against Core 2026.10.0/1 TemplateEntity / TrackTemplateResultInfo /
RenderInfo. Other provider shapes, trigger templates and broad domain/global
listeners remain unknown rather than scanning unrelated private entities.
"""
    entity_id = settings.get("session_mode_entity")
    if not isinstance(entity_id, str) or not entity_id.startswith("sensor.") or _platform(runtime, entity_id) != "template":
        return {"dependency_issue": "not_supported_state_template"}
    try:
        from homeassistant.components.sensor import DATA_COMPONENT
        from homeassistant.components.template.template_entity import TemplateEntity
        from homeassistant.helpers.event import TrackTemplateResultInfo
        from homeassistant.helpers.template import Template
        from homeassistant.helpers.template.render_info import RenderInfo
    except ImportError:
        return {"dependency_issue": "core_contract_unavailable"}
    component = runtime.hass.data.get(DATA_COMPONENT)
    entity = getattr(component, "get_entity", lambda _id: None)(entity_id)
    if (not isinstance(entity, TemplateEntity) or getattr(entity, "hass", None) is not runtime.hass
            or getattr(entity, "entity_id", None) != entity_id):
        return {"dependency_issue": "loaded_entity_not_verified"}
    tracker = getattr(entity, "_template_result_info", None)
    config = getattr(entity, "_config", None)
    template = config.get(getattr(entity, "_state_option", None)) if isinstance(config, dict) else None
    if (not isinstance(tracker, TrackTemplateResultInfo) or getattr(tracker, "hass", None) is not runtime.hass
            or not isinstance(template, Template)):
        return {"dependency_issue": "state_tracker_not_verified"}
    infos = getattr(tracker, "_info", None)
    info = infos.get(template) if isinstance(infos, dict) else None
    if (not isinstance(info, RenderInfo) or info.template is not template
            or info.collecting is not False or info.exception is not None):
        return {"dependency_issue": "successful_render_not_verified"}
    dependencies = info.entities
    if not isinstance(dependencies, (set, frozenset)) or any(not isinstance(value, str) for value in dependencies):
        return {"dependency_issue": "dependency_shape_unknown"}
    broad = bool(info.all_states or info.all_states_lifecycle or info.domains or info.domains_lifecycle)
    truncated = len(dependencies) > MAX_COMPARISON_SOURCES
    result = {"dependency_relation": "verified_state_template_dependencies", "template_formula": "available_not_exported",
              "dependency_coverage": "partial" if broad or truncated else "last_successful_render_only",
              "dependency_issue": "broad_or_bounded_dependencies" if broad or truncated else "",
              "dependencies": []}
    for index, dependency in enumerate(sorted(dependencies)[:MAX_COMPARISON_SOURCES]):
        roles = [role for key, role in (("status_entity", "status"), ("mode_entity", "mode"), ("power_entity", "power"))
                 if settings.get(key) == dependency]
        report = source_report(runtime, dependency, "dependency_" + str(index + 1), now, stale, power="power" in roles)
        report["matches_configured_roles"] = roles
        # An actual dependency can be a private unrelated text entity. Its
        # state is unnecessary for timing diagnosis and is never forwarded.
        if not report["matches_configured_roles"]:
            report["value"] = None
            report["value_withheld"] = True
        result["dependencies"].append(report)
    return result


def solar_balance_proof(grid_sources, pv_source, now, grid_sign, *, storage_sources=(), additional_producers=()):
    """Compare reports only, under the already configured sign convention.

Additional producers, if supplied by a caller, must be explicitly confirmed
non-overlapping with the primary PV source. No discovery or absence inference
is performed here. Configured storage may explain export, never cover an
unknown inventory or supply an actuator/budget allowance.
"""
    now = _finite(now)
    grid_sources = list(grid_sources)[:2]
    storage_sources = list(storage_sources)[:MAX_COMPARISON_SOURCES]
    additional_producers = list(additional_producers)[:MAX_COMPARISON_SOURCES]
    reports = grid_sources + [pv_source] + storage_sources + additional_producers
    result = {"schema": 1, "read_only": True, "collected_at": _finite(now),
              "status": "insufficient_sources", "grid_w": None, "pv_w": None, "export_excess_w": None,
              "known_discharge_w": None, "known_additional_production_w": None,
              "remaining_excess_w": None, "source_skew_s": None, "time_aligned": False,
              "alignment_limit_s": ALIGNMENT_LIMIT_S, "tolerance_w": BALANCE_TOLERANCE_W,
              "measurement_time_basis": "ha_report_not_physical_sample", "source_reports": reports,
              "coverage": {"producer_inventory": "unknown", "storage_inventory": "unknown",
                           "known_producer_count": int(pv_source.get("configured") is True) + len(additional_producers),
                           "known_storage_count": len(storage_sources)}, "control_effect": "none"}
    primary = grid_sources + [pv_source]
    stamps = [_finite(report.get("reported_wall")) for report in primary]
    if all(stamp is not None for stamp in stamps) and stamps:
        result["source_skew_s"] = max(stamps) - min(stamps)
        result["time_aligned"] = result["source_skew_s"] <= ALIGNMENT_LIMIT_S
    def usable_at(report):
        stamp, limit = _finite(report.get("reported_wall")), _finite(report.get("stale_limit_s"))
        return bool(now is not None and now > 0 and stamp is not None and stamp > 0
                    and limit is not None and limit > 0 and -5 <= now - stamp <= limit
                    and report.get("usable") is True and _finite(report.get("watts")) is not None)

    if (not primary or any(not usable_at(report) for report in primary)
            or grid_sign not in ("import_positive", "export_positive", "separate")):
        return result
    grid_values = [_finite(report.get("watts")) for report in grid_sources]
    if grid_sign == "separate":
        if len(grid_sources) != 2 or any(watts < 0 for watts in grid_values):
            return result
        grid = grid_values[0] - grid_values[1]
    elif len(grid_sources) != 1:
        return result
    else:
        grid = grid_values[0] * (-1 if grid_sign == "export_positive" else 1)
    pv = _finite(pv_source["watts"])
    if pv < 0:
        return result
    excess = max(0.0, -grid) - pv
    result.update(grid_w=grid, pv_w=pv, export_excess_w=excess)
    contributions = []
    for sources, key, negative_allowed in ((storage_sources, "known_discharge_w", True),
                                            (additional_producers, "known_additional_production_w", False)):
        values = []
        for report in sources:
            watts, stamp = _finite(report.get("watts")), _finite(report.get("reported_wall"))
            if (not usable_at(report) or watts is None or stamp is None
                    or max(stamps + [stamp]) - min(stamps + [stamp]) > ALIGNMENT_LIMIT_S
                    or not negative_allowed and watts < 0):
                values = None
                break
            values.append(max(0.0, watts))
        result[key] = sum(values) if values is not None and sources else None
        contributions.append(sum(values) if values is not None else 0.0)
    result["remaining_excess_w"] = excess - sum(contributions) if result["time_aligned"] else None
    if excess <= BALANCE_TOLERANCE_W:
        result["status"] = "no_excess_observed"
    elif not result["time_aligned"]:
        result["status"] = "reports_not_aligned"
    elif result["remaining_excess_w"] <= BALANCE_TOLERANCE_W:
        result["status"] = "known_sources_can_explain"
    else:
        result["status"] = "unexplained_with_unknown_inventory"
    return result


def runtime_solar_balance_proof(runtime, now):
    """Read selected P1/PV and configured storage only; no registry discovery."""
    settings = getattr(runtime, "settings", {})
    settings = settings if isinstance(settings, dict) else {}
    stale = settings.get("stale_s", 120)
    sign = settings.get("grid_sign", "import_positive")
    grids = [source_report(runtime, settings.get("grid_entity"), "grid", now, stale, power=True, signed=True)]
    if sign == "separate":
        grids.append(source_report(runtime, settings.get("export_entity"), "grid_export", now, stale, power=True))
    pv = source_report(runtime, settings.get("pv_entity"), "pv", now, stale, power=True)
    storage, seen = [], set()
    configurations = getattr(getattr(runtime, "battery_fleet", None), "configs", {})
    configurations = configurations if isinstance(configurations, dict) else {}
    bindings = [(settings.get("battery_power_entity"), settings.get("battery_sign"))]
    bindings.extend((cfg.get("power_entity"), cfg.get("power_sign")) for cfg in configurations.values() if isinstance(cfg, dict))
    for entity, power_sign in bindings:
        if not isinstance(entity, str) or not entity or entity in seen or len(storage) >= MAX_COMPARISON_SOURCES:
            continue
        seen.add(entity)
        report = source_report(runtime, entity, "storage_" + str(len(storage) + 1), now, stale, power=True, signed=True)
        if entity in (settings.get("grid_entity"), settings.get("export_entity"), settings.get("pv_entity")):
            report.update(usable=False, watts=None, issue="overlap_with_primary_source")
        elif power_sign not in ("charge_positive", "discharge_positive"):
            report.update(usable=False, watts=None, issue="power_sign_unknown")
        elif report.get("watts") is not None and power_sign == "charge_positive":
            report["watts"] = -report["watts"]
        storage.append(report)
    return solar_balance_proof(grids, pv, now, sign, storage_sources=storage)
