"""Private one-file import for installation-specific SolarPilot data.

The public HACS repository contains no household-specific entity IDs. A user may
optionally place ``userfiles/private_bundle.json`` next to the integration. HACS
preserves ``userfiles`` across normal upgrades.

Import is conservative:
- only known profile groups/keys are accepted;
- Home Assistant entity references are only imported when they currently exist;
- existing non-empty user choices are never overwritten;
- physical control permissions are never enabled by the importer;
- the runtime still starts in Observatie regardless of imported settings.

The same private bundle may also contain the aggregated historical bootstrap used
by the local PV, planner and battery what-if models.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
from typing import Any

BUNDLE_FORMAT = "solarpilot-private-bundle-v1"
LEGACY_PROFILE_FORMAT = "solarpilot-local-profile-v1"
BUNDLE_FILENAME = "private_bundle.json"

# Entity fields are validated against hass.states before they are imported.
_ENTITY_FIELDS: dict[str, set[str]] = {
    "site": {"grid_entity", "export_entity", "pv_entity", "battery_power_entity", "battery_soc_entity"},
    "capacity": {"average_demand_entity", "monthly_peak_entity"},
    "phase": {"phase_1_entity", "phase_2_entity", "phase_3_entity"},
    "forecast": {"current_hour_entity", "next_hour_entity", "remaining_today_entity", "tomorrow_entity"},
    "local_pv": {"forecast_power_entity", "sun_entity"},
    "economy": {"import_price_entity", "export_price_entity"},
    "dhw": {"target_entity", "temperature_entity", "power_entity", "hygiene_entity", "manual_entity"},
    "smart_climate": {"weather_entity", "outside_temp_entity"},
    "wallbox": {"power_entity", "status_entity", "demand_entity", "mode_entity"},
}
_ENTITY_LIST_FIELDS: dict[str, set[str]] = {
    "dhw": {"cooling_entities", "manual_entities"},
    "smart_climate": {"zone_entities"},
}

# Non-entity suggestion keys accepted from a private profile.
_VALUE_FIELDS: dict[str, set[str]] = {
    "site": {"grid_sign", "battery_sign"},
    "wallbox": {"name"},
}

# Safe first-import flags. They enable monitoring/advice only. Explicit physical
# control remains off. DHW is intentionally left disabled until the user confirms
# the safety checkbox in its own wizard.
_SAFE_FIRST_IMPORT: dict[str, dict[str, Any]] = {
    "capacity": {"enabled": True},
    "phase": {"enabled": True, "control_starts": False, "shed_on_overlimit": False},
    "forecast": {"enabled": True},
    "local_pv": {"enabled": True, "seed_enabled": True},
    "economy": {"enabled": True},
    "dhw": {"enabled": False, "safety_confirmed": False},
    "smart_climate": {"enabled": True, "control_enabled": False},
    "wallbox": {"enabled": True},
    "battery_analysis": {"enabled": True, "seed_enabled": True},
}


def userfiles_dir() -> Path:
    return Path(__file__).parent / "userfiles"


def bundle_path() -> Path:
    return userfiles_dir() / BUNDLE_FILENAME


def legacy_profile_path() -> Path:
    return userfiles_dir() / "profile.json"


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def load_private_bundle(path: Path | None = None) -> dict[str, Any]:
    """Load the current private bundle, with read-only legacy-profile fallback."""
    selected = path or bundle_path()
    data = _read_json(selected)
    if data.get("format") == BUNDLE_FORMAT:
        return data
    if path is None:
        legacy = _read_json(legacy_profile_path())
        if legacy.get("format") == LEGACY_PROFILE_FORMAT:
            # Legacy file already carried an embedded historical_seed. Wrapping it
            # in memory keeps old private installs usable without modifying disk.
            return {
                "format": BUNDLE_FORMAT,
                "profile_name": legacy.get("profile_name", "Privéprofiel"),
                "auto_apply": True,
                "delete_on_remove": legacy.get("delete_on_remove", True),
                "profile": {"suggestions": legacy.get("suggestions", {})},
                "historical_seed": legacy.get("historical_seed", {}),
                "legacy_source": True,
            }
    return {}


def bundle_fingerprint(bundle: dict[str, Any]) -> str:
    if not bundle:
        return ""
    payload = json.dumps(bundle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def bundle_historical_seed(bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    data = bundle if bundle is not None else load_private_bundle()
    seed = data.get("historical_seed", {}) if isinstance(data, dict) else {}
    return seed if isinstance(seed, dict) and seed.get("format") == "solarpilot-historical-analysis-v1" else {}


def _profile_suggestions(bundle: dict[str, Any]) -> dict[str, Any]:
    profile = bundle.get("profile", {})
    suggestions = profile.get("suggestions", {}) if isinstance(profile, dict) else {}
    if not suggestions and isinstance(bundle.get("suggestions"), dict):
        suggestions = bundle["suggestions"]
    return suggestions if isinstance(suggestions, dict) else {}


def _entity_exists(hass, entity_id: str) -> bool:
    return bool(entity_id and getattr(hass, "states", None) and hass.states.get(entity_id) is not None)


def private_group_suggestions(hass, group: str, bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return validated private suggestions for one config group."""
    data = bundle if bundle is not None else load_private_bundle()
    raw = _profile_suggestions(data).get(group, {})
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key in _ENTITY_FIELDS.get(group, set()):
        value = raw.get(key)
        if isinstance(value, str) and _entity_exists(hass, value):
            out[key] = value
    for key in _ENTITY_LIST_FIELDS.get(group, set()):
        value = raw.get(key)
        if isinstance(value, list):
            valid = [x for x in value if isinstance(x, str) and _entity_exists(hass, x)]
            if valid:
                out[key] = valid
    for key in _VALUE_FIELDS.get(group, set()):
        value = raw.get(key)
        if value not in (None, "", []):
            out[key] = deepcopy(value)
    return out


def _empty(value: Any) -> bool:
    return value is None or value == "" or value == [] or value == {}


def _fill_empty(target: dict[str, Any], values: dict[str, Any], effective: dict[str, Any] | None = None) -> list[str]:
    applied: list[str] = []
    effective = effective or target
    for key, value in values.items():
        current = target.get(key) if key in target else effective.get(key)
        if _empty(current):
            target[key] = deepcopy(value)
            applied.append(key)
    return applied


def _required_present(group: str, values: dict[str, Any]) -> bool:
    if group == "capacity":
        return bool(values.get("average_demand_entity") and values.get("monthly_peak_entity"))
    if group == "phase":
        return all(values.get(k) for k in ("phase_1_entity", "phase_2_entity", "phase_3_entity"))
    if group == "forecast":
        return bool(values.get("current_hour_entity") and values.get("next_hour_entity"))
    if group == "local_pv":
        return bool(values.get("forecast_power_entity") and values.get("sun_entity"))
    if group == "economy":
        return bool(values.get("import_price_entity") or values.get("export_price_entity"))
    if group == "smart_climate":
        return bool(values.get("zone_entities") and values.get("weather_entity"))
    if group == "wallbox":
        return bool(values.get("power_entity") and (values.get("status_entity") or values.get("demand_entity")))
    return True


def build_private_import(hass, entry_data: dict[str, Any], current_options: dict[str, Any], *, force: bool = False, bundle: dict[str, Any] | None = None) -> tuple[dict[str, Any], dict[str, Any]]:
    """Build options after a conservative private-bundle import.

    The returned options may be passed to ``async_update_entry``. Existing
    non-empty choices are preserved. ``force`` only re-evaluates a known bundle;
    it still does not overwrite configured values.
    """
    bundle = bundle if bundle is not None else load_private_bundle()
    if not bundle:
        return deepcopy(current_options or {}), {"status": "missing", "changed": False}
    fingerprint = bundle_fingerprint(bundle)
    options = deepcopy(current_options or {})
    previous = options.get("_private_bundle", {}) if isinstance(options.get("_private_bundle"), dict) else {}
    if (not force and previous.get("fingerprint") == fingerprint
            and not previous.get("missing_groups")):
        return options, {"status": "already_applied", "changed": False, **previous}
    if bundle.get("auto_apply", True) is False and not force:
        return options, {"status": "manual_only", "changed": False, "fingerprint": fingerprint}

    applied: dict[str, list[str]] = {}
    missing: dict[str, list[str]] = {}
    raw_suggestions = _profile_suggestions(bundle)

    # Site values live in entry.data on first setup; imported values are written
    # to options["settings"] only where the effective setting is still empty.
    site_values = private_group_suggestions(hass, "site", bundle)
    site_raw = raw_suggestions.get("site", {}) if isinstance(raw_suggestions.get("site"), dict) else {}
    settings = deepcopy(options.get("settings", {}))
    effective_site = {**(entry_data or {}), **settings}
    keys = _fill_empty(settings, site_values, effective_site)
    if keys:
        options["settings"] = settings
        applied["site"] = keys
    missing_site = [k for k in _ENTITY_FIELDS["site"] if site_raw.get(k) and k not in site_values]
    if missing_site:
        missing["site"] = sorted(missing_site)

    for group in ("capacity", "phase", "forecast", "local_pv", "economy", "dhw", "smart_climate", "wallbox"):
        values = private_group_suggestions(hass, group, bundle)
        raw = raw_suggestions.get(group, {}) if isinstance(raw_suggestions.get(group), dict) else {}
        target = deepcopy(options.get(group, {}))
        keys = _fill_empty(target, values)
        group_missing = [k for k in (_ENTITY_FIELDS.get(group, set()) | _ENTITY_LIST_FIELDS.get(group, set())) if raw.get(k) and k not in values]
        if group_missing:
            missing[group] = sorted(group_missing)
        # Safe monitor/advice defaults are added only on first creation of this
        # group and only when the required source links were actually resolved.
        if _required_present(group, {**target, **values}):
            for key, value in _SAFE_FIRST_IMPORT.get(group, {}).items():
                if key not in target:
                    target[key] = deepcopy(value)
                    keys.append(key)
        if keys:
            options[group] = target
            applied[group] = sorted(set(keys))

    # Historical analysis is read directly from the same bundle. Persist only
    # safe analysis switches in options; never copy the data itself into options.
    if bundle_historical_seed(bundle):
        target = deepcopy(options.get("battery_analysis", {}))
        keys: list[str] = []
        if not options.get("battery_analysis"):
            for key, value in _SAFE_FIRST_IMPORT["battery_analysis"].items():
                target[key] = deepcopy(value)
                keys.append(key)
        if keys:
            options["battery_analysis"] = target
            applied["battery_analysis"] = keys

    # Import metadata is deliberately non-sensitive and lets subsequent starts
    # avoid re-enabling a setting that the user later turned off.
    meta = {
        "fingerprint": fingerprint,
        "profile_name": str(bundle.get("profile_name") or "Privéprofiel"),
        "format": BUNDLE_FORMAT,
        "history": bool(bundle_historical_seed(bundle)),
        "applied_groups": sorted(applied),
        "missing_groups": sorted(missing),
    }
    options["_private_bundle"] = meta
    changed = options != (current_options or {})
    return options, {"status": "applied", "changed": changed, "applied": applied, "missing": missing, **meta}


def private_bundle_overview(options: dict[str, Any] | None = None, *, bundle: dict[str, Any] | None = None) -> str:
    """Human-readable status for the options overview."""
    bundle = bundle if bundle is not None else load_private_bundle()
    if not bundle:
        return "geen privébundel gevonden"
    fp = bundle_fingerprint(bundle)
    meta = (options or {}).get("_private_bundle", {}) if isinstance((options or {}).get("_private_bundle", {}), dict) else {}
    name = str(bundle.get("profile_name") or "Privéprofiel")
    history = " + historiek" if bundle_historical_seed(bundle) else ""
    if meta.get("fingerprint") == fp:
        missing = meta.get("missing_groups") or []
        suffix = f" · ontbrekend: {', '.join(missing)}" if missing else ""
        return f"geladen: {name}{history}{suffix}"
    return f"bestand gevonden, nog niet toegepast: {name}{history}"


def delete_private_files_if_requested() -> None:
    """Delete SolarPilot-owned private files only when the bundle opts in."""
    bundle = load_private_bundle()
    if bundle and bundle.get("delete_on_remove", True) is False:
        return
    for path in (bundle_path(), legacy_profile_path(), userfiles_dir() / "historical_seed.json"):
        try:
            path.unlink(missing_ok=True)
        except OSError:
            pass
