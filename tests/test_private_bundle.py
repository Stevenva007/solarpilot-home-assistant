import json
from types import SimpleNamespace

from custom_components.solar_pilot import private_bundle as pb


class States:
    def __init__(self, ids):
        self._states = {entity_id: object() for entity_id in ids}

    def get(self, entity_id):
        return self._states.get(entity_id)


class Hass:
    def __init__(self, ids):
        self.states = States(ids)


def write_bundle(tmp_path, suggestions, history=True):
    data = {
        "format": pb.BUNDLE_FORMAT,
        "profile_name": "Testprofiel",
        "auto_apply": True,
        "delete_on_remove": True,
        "profile": {"suggestions": suggestions},
    }
    if history:
        data["historical_seed"] = {
            "format": "solarpilot-historical-analysis-v1",
            "source": {"homewizard_start": "2026-01-01", "homewizard_end": "2026-02-01"},
            "grid": {"period_days": 31},
        }
    path = tmp_path / "private_bundle.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_private_bundle_only_imports_existing_entities(monkeypatch, tmp_path):
    path = write_bundle(tmp_path, {
        "phase": {
            "phase_1_entity": "sensor.phase_1",
            "phase_2_entity": "sensor.missing",
            "phase_3_entity": "sensor.phase_3",
        },
        "wallbox": {"name": "My charger", "power_entity": "sensor.wallbox_power"},
    })
    monkeypatch.setattr(pb, "bundle_path", lambda: path)
    monkeypatch.setattr(pb, "legacy_profile_path", lambda: tmp_path / "no-legacy.json")
    hass = Hass({"sensor.phase_1", "sensor.phase_3", "sensor.wallbox_power"})

    phase = pb.private_group_suggestions(hass, "phase")
    assert phase == {
        "phase_1_entity": "sensor.phase_1",
        "phase_3_entity": "sensor.phase_3",
    }
    wallbox = pb.private_group_suggestions(hass, "wallbox")
    assert wallbox == {"name": "My charger", "power_entity": "sensor.wallbox_power"}


def test_private_import_prefills_profile_and_keeps_control_permissions_off(monkeypatch, tmp_path):
    suggestions = {
        "site": {
            "grid_entity": "sensor.grid",
            "grid_sign": "import_positive",
            "pv_entity": "sensor.pv",
        },
        "capacity": {
            "average_demand_entity": "sensor.avg",
            "monthly_peak_entity": "sensor.peak",
        },
        "phase": {
            "phase_1_entity": "sensor.l1",
            "phase_2_entity": "sensor.l2",
            "phase_3_entity": "sensor.l3",
        },
        "forecast": {
            "current_hour_entity": "sensor.forecast_now",
            "next_hour_entity": "sensor.forecast_next",
        },
        "local_pv": {
            "forecast_power_entity": "sensor.forecast_power",
            "sun_entity": "sun.sun",
        },
        "economy": {
            "import_price_entity": "input_number.buy",
            "export_price_entity": "input_number.sell",
        },
        "dhw": {
            "target_entity": "water_heater.tank",
            "temperature_entity": "sensor.tank_temp",
            "cooling_entities": ["climate.zone_1", "climate.zone_2"],
        },
        "smart_climate": {
            "zone_entities": ["climate.zone_1", "climate.zone_2"],
            "weather_entity": "weather.home",
            "outside_temp_entity": "sensor.outside",
        },
        "wallbox": {
            "name": "Wallbox",
            "power_entity": "sensor.wallbox_power",
            "status_entity": "sensor.wallbox_status",
            "mode_entity": "select.wallbox_mode",
        },
    }
    path = write_bundle(tmp_path, suggestions)
    monkeypatch.setattr(pb, "bundle_path", lambda: path)
    monkeypatch.setattr(pb, "legacy_profile_path", lambda: tmp_path / "no-legacy.json")
    ids = set()
    for group in suggestions.values():
        for key, value in group.items():
            if key == "name" or key.endswith("sign"):
                continue
            if isinstance(value, list):
                ids.update(value)
            elif isinstance(value, str) and "." in value:
                ids.add(value)
    hass = Hass(ids)

    options, result = pb.build_private_import(
        hass,
        {"grid_entity": "sensor.grid", "grid_sign": "import_positive", "pv_entity": "sensor.pv"},
        {},
    )
    assert result["changed"] is True
    assert options["capacity"]["enabled"] is True
    assert options["phase"]["enabled"] is True
    assert options["phase"]["control_starts"] is False
    assert options["phase"]["shed_on_overlimit"] is False
    assert options["forecast"]["enabled"] is True
    assert options["economy"]["enabled"] is True
    assert options["smart_climate"]["enabled"] is True
    assert options["smart_climate"]["control_enabled"] is False
    assert options["wallbox"]["enabled"] is True
    assert options["dhw"]["enabled"] is False
    assert options["dhw"]["safety_confirmed"] is False
    assert options["battery_analysis"]["enabled"] is True
    assert options["battery_analysis"]["seed_enabled"] is True
    assert options["_private_bundle"]["history"] is True


def test_same_bundle_does_not_reenable_user_disabled_monitor(monkeypatch, tmp_path):
    path = write_bundle(tmp_path, {
        "phase": {
            "phase_1_entity": "sensor.l1",
            "phase_2_entity": "sensor.l2",
            "phase_3_entity": "sensor.l3",
        }
    })
    monkeypatch.setattr(pb, "bundle_path", lambda: path)
    monkeypatch.setattr(pb, "legacy_profile_path", lambda: tmp_path / "no-legacy.json")
    hass = Hass({"sensor.l1", "sensor.l2", "sensor.l3"})
    options, _ = pb.build_private_import(hass, {}, {})
    options["phase"]["enabled"] = False

    again, result = pb.build_private_import(hass, {}, options)
    assert result["status"] == "already_applied"
    assert again["phase"]["enabled"] is False


def test_missing_entity_group_is_retried_without_overwriting_user_values(monkeypatch, tmp_path):
    path = write_bundle(tmp_path, {
        "capacity": {
            "average_demand_entity": "sensor.avg",
            "monthly_peak_entity": "sensor.peak",
        }
    }, history=False)
    monkeypatch.setattr(pb, "bundle_path", lambda: path)
    monkeypatch.setattr(pb, "legacy_profile_path", lambda: tmp_path / "no-legacy.json")

    first, result = pb.build_private_import(Hass({"sensor.avg"}), {}, {})
    assert "capacity" in result["missing_groups"]
    assert first["capacity"]["average_demand_entity"] == "sensor.avg"
    assert "monthly_peak_entity" not in first["capacity"]

    # The same bundle is retried because it still had unresolved source groups.
    second, result2 = pb.build_private_import(Hass({"sensor.avg", "sensor.peak"}), {}, first)
    assert result2["status"] == "applied"
    assert second["capacity"]["monthly_peak_entity"] == "sensor.peak"
    assert second["capacity"]["enabled"] is True
