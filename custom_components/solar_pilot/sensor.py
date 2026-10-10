"""Native telemetry and human-readable SolarPilot decisions."""
from datetime import datetime, timezone
from homeassistant.components.sensor import SensorEntity, SensorDeviceClass, SensorStateClass
from homeassistant.helpers.entity import EntityCategory
from .entity import SolarEntity
from .pv_forecast import PV_SENSOR_DEFINITIONS
from .current_guide import CURRENT_GUIDE, GUIDE_HASH, GUIDE_VERSION, GUIDE_UPDATED


COST_SENSORS = {
    "electricity_cost_today": ("Elektriciteitskost vandaag netto", "net_cost_eur"),
    "electricity_import_cost_today": ("Netafnamekost vandaag", "import_cost_eur"),
    "electricity_export_revenue_today": ("Injectievergoeding vandaag", "export_revenue_eur"),
    "electricity_pv_avoided_today": ("Vermeden netaankoop door zon vandaag", "pv_avoided_cost_eur"),
}


def energy_display(runtime):
    """Presentation-only meter reads; never mutate site data or control state."""
    settings = runtime.settings
    pv_settings = getattr(getattr(runtime, "pv_forecast", None), "settings", {})
    result = {"inverter_limit_w": pv_settings.get("inverter_limit_w"),
              "stale_s": settings.get("stale_s", 120),
              "pv": {"value_w": None, "reported_at": None},
              "grid": {"value_w": None, "reported_at": None}}
    power = getattr(runtime, "_power", None)
    if not callable(power):
        return result

    def read(entity_id):
        value, stamp = power(entity_id)
        obj = runtime.hass.states.get(entity_id) if entity_id else None
        attrs = obj.attributes if obj else {}
        if attrs.get("estimated") is True or attrs.get("is_estimated") is True:
            return None, stamp
        return value, stamp

    pv, pv_stamp = read(settings.get("pv_entity"))
    if pv is not None and pv >= 0:
        result["pv"] = {"value_w": pv, "reported_at": pv_stamp}
    grid, grid_stamp = read(settings.get("grid_entity"))
    if settings.get("grid_sign") == "separate":
        export, export_stamp = read(settings.get("export_entity"))
        if grid is None or export is None or grid < 0 or export < 0:
            grid = None
        else:
            grid -= export
            grid_stamp = min(grid_stamp, export_stamp)
    elif settings.get("grid_sign") == "export_positive" and grid is not None:
        grid = -grid
    if grid is not None:
        result["grid"] = {"value_w": grid, "reported_at": grid_stamp}
    return result


async def async_setup_entry(hass, entry, async_add_entities):
    r = entry.runtime_data
    r.platforms.register("sensor", async_add_entities, lambda: _entities(r))


def _entities(r):
    entities = [SolarSensor(r, k, n) for k, n in [
        ("status", "Status"), ("grid", "Netvermogen"), ("surplus", "Vrij overschot"),
        ("managed", "Geregeld vermogen"), ("energy", "Geregeld verbruik indicatief"), ("learning", "Leerstatus"),
        ("ems_status", "EMS status"), ("guide", "Actuele uitleg"), ("ems_solar_today", "EMS zonne-energie vandaag"),
        ("ems_value_today", "EMS geschatte waarde vandaag"), ("ems_self_consumption", "Zelfconsumptie vandaag")]]
    entities += [SolarSensor(r, key, name) for key, (name, _) in COST_SENSORS.items()]
    if r.capacity_settings["enabled"]:
        entities += [SolarSensor(r, "capacity_status", "Kwartierpiek regeling"),
                     SolarSensor(r, "capacity_limit", "Kwartierpiek toegestane netafname"),
                     SolarSensor(r, "capacity_headroom", "Kwartierpiek vrije ruimte")]
    if r.phase_settings["enabled"]:
        entities += [SolarSensor(r, "phase_status", "Fasebewaking"),
                     SolarSensor(r, "phase_headroom", "Kleinste vrije faseruimte"),
                     SolarSensor(r, "phase_learning_status", "Faseherkenning")]
        for phase in ("l1", "l2", "l3"):
            label = phase.upper()
            entities += [SolarSensor(r, f"phase_{phase}_known", f"{label} herkend toestelvermogen"),
                         SolarSensor(r, f"phase_{phase}_residual", f"{label} netto restvermogen")]
    if r.local_pv_settings.get("enabled"):
        entities += [SolarSensor(r, "local_pv_status", "Lokale PV voorspelling"),
                     SolarSensor(r, "local_pv_corrected_power", "Lokale PV voorspelling vermogen"),
                     SolarSensor(r, "local_pv_confidence", "Lokale PV modelzekerheid")]
    if r.battery_analysis_settings.get("enabled"):
        entities += [SolarSensor(r, "battery_analysis_status", "Batterij what-if analyse"),
                     SolarSensor(r, "battery_10_5_avoided", "Batterij 10 kWh 5 kW vermeden netafname")]
    if r.battery_fleet.configured or r.battery_fleet.settings.get("enabled"):
        entities += [SolarSensor(r, "battery_fleet_status", "Batterijvloot"),
                     SolarSensor(r, "battery_fleet_soc", "Batterijvloot laadniveau"),
                     SolarSensor(r, "battery_fleet_power", "Batterijvloot vermogen")]
    if r.wallbox_settings["enabled"]:
        entities += [SolarSensor(r, "wallbox_status", "Wallbox samenspel"),
                     SolarSensor(r, "wallbox_power", "Wallbox laadvermogen")]
    entities += [SolarSensor(r, "sg_boost_status", "Zonneboost status"),
                 SolarSensor(r, "panasonic_status", "Panasonic regeling"),
                 SolarSensor(r, "panasonic_power", "Warmtepomp vermogen"),
                 SolarSensor(r, "dhw_status", "Warm water toestelstatus"),
                 SolarSensor(r, "dhw_temperature", "Tank gemeten temperatuur"),
                 SolarSensor(r, "dhw_target", "Tank gemeld doel")]
    entities += [SolarSensor(r, "status", "Regelstatus", i) for i in r.configs]
    entities += [PVForecastSensor(r,k,v) for k,v in PV_SENSOR_DEFINITIONS.items()]
    return entities


class SolarSensor(SolarEntity, SensorEntity):
    _unrecorded_attributes = frozenset({
        "devices", "recent_decisions", "recovery", "wallbox", "last_report_age_s", "remaining_s",
        "meter_note", "learning", "profiles", "handover", "dhw", "phase_learning", "phase_attribution",
        "battery_analysis", "local_pv", "sections", "ems", "planner", "cycle_learning",
        "smart_climate", "battery_fleet", "device_management", "priority_board", "historical_phase_profile", "today", "forecast",
        "capacity", "phase", "economy", "warnings", "advice", "legacy_conflicts", "dishwasher_setup", "isolated_devices",
        "energy_display", "pv_model", "thermal_model", "learning_insights", "removal",
        "pv_forecast", "savings", "electricity_today", "panasonic", "sg_boost", "panasonic_archive", "legacy_panasonic_archive",
    })

    def __init__(self, runtime, suffix, name, device_id=None):
        super().__init__(runtime, suffix, name, device_id)
        power_suffixes = {
            "grid", "surplus", "managed", "wallbox_power", "capacity_limit", "capacity_headroom", "phase_headroom",
            "local_pv_corrected_power", "phase_l1_known", "phase_l2_known", "phase_l3_known",
            "phase_l1_residual", "phase_l2_residual", "phase_l3_residual", "battery_fleet_power", "panasonic_power",
        }
        if suffix in COST_SENSORS:
            self._attr_native_unit_of_measurement = "EUR"
            self._attr_device_class = SensorDeviceClass.MONETARY
            self._attr_state_class = SensorStateClass.TOTAL
            self._attr_suggested_display_precision = 2
        elif suffix in power_suffixes:
            self._attr_native_unit_of_measurement = "W"
            self._attr_device_class = SensorDeviceClass.POWER
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif suffix in ("dhw_temperature", "dhw_target"):
            self._attr_native_unit_of_measurement = "°C"
            self._attr_device_class = SensorDeviceClass.TEMPERATURE
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif suffix in ("energy",):
            self._attr_native_unit_of_measurement = "kWh"
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif suffix == "ems_solar_today":
            self._attr_native_unit_of_measurement = "kWh"
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL_INCREASING
        elif suffix == "battery_10_5_avoided":
            self._attr_native_unit_of_measurement = "kWh"
            self._attr_device_class = SensorDeviceClass.ENERGY
            self._attr_state_class = SensorStateClass.TOTAL
        elif suffix == "ems_value_today":
            self._attr_native_unit_of_measurement = "EUR"
            self._attr_state_class = SensorStateClass.MEASUREMENT
        elif suffix in ("ems_self_consumption", "local_pv_confidence", "battery_fleet_soc"):
            self._attr_native_unit_of_measurement = "%"
            self._attr_state_class = SensorStateClass.MEASUREMENT
        self._attr_icon = "mdi:book-open-page-variant" if suffix == "guide" else "mdi:solar-power-variant"
        if suffix == "guide":
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def last_reset(self):
        if self.suffix not in COST_SENSORS or self.native_value is None:
            return None
        stamp = self.runtime.electricity_cost.cached.get("reset_timestamp")
        return datetime.fromtimestamp(stamp, timezone.utc) if stamp is not None else None

    def _ems(self):
        reader = getattr(self.runtime, "sensor_overview", None)
        return reader("ems") if callable(reader) else self.runtime.ems_overview()

    def _learning(self):
        reader = getattr(self.runtime, "sensor_overview", None)
        return reader("learning") if callable(reader) else self.runtime.learning_overview()

    @property
    def native_value(self):
        r = self.runtime
        if self.suffix in COST_SENSORS:
            return r.electricity_cost.cached.get(COST_SENSORS[self.suffix][1])
        if self.suffix == "guide":
            return GUIDE_VERSION
        if self.suffix == "energy" and not r.data_loaded:
            return None
        if self.suffix == "sg_boost_status":
            data = r.sg_boost.overview()
            return str(data.get("reason") or data.get("status") or "Zonneboost uit")[:250]
        if self.suffix in {"panasonic_status", "panasonic_power", "dhw_status", "dhw_temperature", "dhw_target"}:
            data = r.panasonic.overview()
            return {
                "panasonic_status": str(data.get("status") or "Panasonic regelt zelfstandig")[:250],
                "panasonic_power": data.get("power_w"),
                "dhw_status": str(data.get("tank_status") or data.get("status") or "Toestelstatus onbekend")[:250],
                "dhw_temperature": data.get("temperature_c"), "dhw_target": data.get("target_c"),
            }[self.suffix]
        if self.suffix in ("ems_solar_today", "ems_value_today", "ems_self_consumption"):
            today = self._ems().get("today", {})
            if self.suffix == "ems_solar_today":
                return round(float(today.get("managed_solar_kwh", 0.0) or 0.0), 4)
            if self.suffix == "ems_value_today":
                return round(float(today.get("estimated_value_eur", 0.0) or 0.0), 4)
            return today.get("self_consumption_pct")
        if self.suffix == "local_pv_status":
            return self._ems().get("local_pv", {}).get("reason", "Nog geen lokaal PV-profiel")[:250]
        if self.suffix == "local_pv_corrected_power":
            return self._ems().get("local_pv", {}).get("corrected_power_w")
        if self.suffix == "local_pv_confidence":
            value = self._ems().get("local_pv", {}).get("confidence")
            return None if value is None else round(float(value) * 100, 1)
        if self.suffix == "phase_status":
            return r.phase.reason[:250]
        if self.suffix == "phase_headroom":
            return r.phase.headroom_w
        if self.suffix == "phase_learning_status":
            p = self._ems().get("phase_learning", {})
            return f"{int(p.get('accepted_events',0))} bruikbare fasegebeurtenissen"
        if self.suffix.startswith("phase_l"):
            attr = self._ems().get("phase_attribution", {})
            idx = {"phase_l1": 0, "phase_l2": 1, "phase_l3": 2}.get(self.suffix[:8])
            rows = attr.get("phases") or []
            if idx is None or idx >= len(rows):
                return None
            row = rows[idx]
            return row.get("known_device_w") if self.suffix.endswith("_known") else row.get("residual_net_w")
        if self.suffix == "battery_fleet_status":
            b = self._ems().get("battery_fleet", {})
            return b.get("reason", "Nog geen batterijadvies")[:250]
        if self.suffix == "battery_fleet_soc":
            return self._ems().get("battery_fleet", {}).get("aggregate", {}).get("soc_pct")
        if self.suffix == "battery_fleet_power":
            return self._ems().get("battery_fleet", {}).get("aggregate", {}).get("power_w")
        if self.suffix == "battery_analysis_status":
            b = self._ems().get("battery_analysis", {})
            period = b.get("seed_period", {})
            return (f"Adviserend · historie {period.get('days','—')} dagen" if b.get("enabled") else "Uitgeschakeld")
        if self.suffix == "battery_10_5_avoided":
            for row in self._ems().get("battery_analysis", {}).get("scenarios", []):
                if abs(float(row.get("capacity_kwh", 0))-10) < 1e-6 and abs(float(row.get("power_kw", 0))-5) < 1e-6:
                    return row.get("avoided_import_kwh")
            return None
        if self.suffix == "ems_status":
            overview = self._ems()
            if overview.get("legacy_conflicts"):
                return "Vervangen regelaar nog actief"
            warnings = overview.get("warnings") or []
            return (warnings[0][:250] if warnings else "EMS gereed")
        if self.suffix == "capacity_status":
            return r.capacity.reason[:250]
        if self.suffix == "capacity_limit":
            return r.capacity.allowed_grid_w
        if self.suffix == "capacity_headroom":
            return r.capacity.optional_headroom_w
        if self.suffix == "learning":
            return self._learning()["status"]
        if self.suffix == "wallbox_status":
            return r.wallbox_guard.result.reason[:250]
        if self.suffix == "wallbox_power":
            return r.wallbox_overview()["power_w"]
        if self.key:
            return r.result.reasons.get(self.key, "Initialiseren")[:250]
        return {"status": (r.problem or {"observe": "Observatie", "solar": "Zonnestroom", "paused": "Pauze"}[r.mode]),
                "grid": None if r.grid_w is None else round(r.grid_w, 1),
                "surplus": None if r.grid_w is None else r.result.free_w,
                "managed": round(r.managed_w, 1), "energy": round(r.energy_kwh, 6)}[self.suffix]

    @property
    def extra_state_attributes(self):
        r = self.runtime
        if self.suffix in COST_SENSORS:
            data = r.electricity_cost.cached
            return {"date": data.get("date"), "partial": data.get("partial", True),
                    "description": "Variabele elektriciteitskost; vaste kosten en capaciteitstarief niet inbegrepen. Eigen zon niet dubbel aftrekken."}
        if self.suffix == "guide":
            return {
                "solar_pilot_guide": True,
                "title": CURRENT_GUIDE["title"],
                "version": GUIDE_VERSION,
                "updated": GUIDE_UPDATED,
                "intro": CURRENT_GUIDE["intro"],
                "sections": CURRENT_GUIDE["sections"],
                "rules_hash": GUIDE_HASH,
                "canonical": "docs/ACTUELE_WERKING.md",
                "note": "Deze uitleg vervangt oudere regels; UPDATE-bestanden zijn alleen migratiegeschiedenis.",
            }
        if self.suffix == "sg_boost_status":
            return r.sg_boost.overview()
        if self.suffix in {"panasonic_status", "panasonic_power", "dhw_status", "dhw_temperature", "dhw_target"}:
            return {**r.panasonic.overview(), "read_only": True}
        if self.suffix in {
            "ems_status", "capacity_status", "capacity_limit", "capacity_headroom", "phase_status", "phase_headroom",
            "phase_learning_status", "phase_l1_known", "phase_l2_known", "phase_l3_known", "phase_l1_residual",
            "phase_l2_residual", "phase_l3_residual", "ems_solar_today", "ems_value_today", "ems_self_consumption",
            "local_pv_status", "local_pv_corrected_power", "local_pv_confidence", "battery_analysis_status",
            "battery_10_5_avoided", "battery_fleet_status", "battery_fleet_soc", "battery_fleet_power",
        }:
            return self._ems()
        if self.suffix == "learning":
            return self._learning()
        if self.suffix in ("wallbox_status", "wallbox_power"):
            return r.wallbox_overview()
        if self.key:
            isolation = getattr(r, "source_isolated_devices", {}).get(self.key, {})
            return {"solar_pilot_device_id": self.key, "owned": r.states[self.key].owned,
                    "target_w": r.result.targets.get(self.key, 0), "fault": r.states[self.key].fault,
                    "isolated": bool(isolation), "isolation_reason": isolation.get("reason", ""),
                    "isolation_reserve_w": isolation.get("reserve_w", 0),
                    "phase": r.phase_learning.profile(self.key), "phase_hint": r.configs[self.key].get("phase_hint", "auto")}
        if self.suffix == "status":
            isolated = [{"id": device_id, **details}
                        for device_id, details in getattr(r, "source_isolated_devices", {}).items()]
            return {"solar_pilot": True, "mode": r.mode, "problem": r.problem,
                    "energy_display": energy_display(r),
                    "problem_kind": r.problem_kind,
                    "auto_resume_after_restart": r.auto_resume_after_restart,
                    "auto_resume_after_restart_entity": r.entity_id("switch", "auto_resume_after_restart"),
                    "pause_cause": r.pause_cause, "pause_reason": r.pause_reason,
                    "restart_requested_mode": r.restart_requested_mode,
                    "restart_recovery_pending": r.restart_recovery_pending,
                    "restart_blocking": r.restart_blocking,
                    "restart_recovery_devices": [r.configs[i]["name"] for i in r.recovery],
                    "isolated_devices": isolated,
                    "isolated_reserve_w": round(sum(item.get("reserve_w", 0) for item in isolated), 1),
                    "grid_w": r.grid_w, "pv_w": r.pv_w, "free_w": r.result.free_w,
                    "budget_w": r.result.budget_w,
                    "budget_note": "Voorwaardelijk regelbudget; geen gemeten vrije injectie", "managed_w": round(r.managed_w, 1),
                    "reserve_w": r.settings["reserve_w"], "max_import_w": r.settings["max_import_w"],
                    "panasonic": r.panasonic.overview(), "sg_boost": r.sg_boost.overview(), "devices": r.overview(), "wallbox": r.wallbox_overview(), "learning": self._learning(),
                "learning_insights": r.learning_hub.summary(),
                    "device_management": r.live_options.overview(),
                    "priority_board": r.priority_board.overview(),
                    "dishwasher_setup": getattr(r, "dishwasher_recovery_info", {"status": "not_checked"}),
                    "ems": self._ems(), "recent_decisions": list(r.logs), "recovery": list(r.recovery.values()),
                    "mode_entity": r.entity_id("select", "mode"), "reset_entity": r.entity_id("button", "reset"),
                    "prepare_remove_entity": r.entity_id("button", "prepare_remove"),
                    "removal": r.removal_overview(),
                    "guide_entity": r.entity_id("sensor", "guide"), "integration_version": GUIDE_VERSION,
                    "energy_kwh": round(r.energy_kwh, 3), "energy_estimated": r.energy_estimated,
                    "editable": r.editable, "config_entry_id": r.entry.entry_id}
        if self.suffix == "energy":
            return {"description": "Verbruik tijdens regeling; omvat ook netstroom/boost. Geen besparing of gegarandeerde zonnestroommeting.",
                    "current_estimate": r.energy_estimated}
        return {}


class PVForecastSensor(SolarEntity, SensorEntity):
    """Scalar cached forecasts only; no histories recalculated or recorded per tick."""
    def __init__(self, runtime, suffix, definition):
        name,unit,self.value_key,self.horizon=definition
        super().__init__(runtime,suffix,name)
        self._attr_icon="mdi:solar-power-variant"
        self._attr_native_unit_of_measurement=unit
        self._attr_suggested_display_precision=3 if unit=="kWh" or unit is None else 1
        if unit=="W":
            self._attr_device_class=SensorDeviceClass.POWER
        elif unit=="kWh":
            self._attr_device_class=SensorDeviceClass.ENERGY
        # Predictions are neither metered consumption nor accumulating counters.
        self._attr_state_class=None

    @property
    def native_value(self):
        c=self.runtime.pv_forecast.cached
        if not c.get("available"):return None
        if self.horizon is not None:
            rows=c.get("horizon",[])
            return rows[self.horizon].get(self.value_key) if len(rows)>self.horizon else None
        if self.value_key=="mae_w":return c.get("model",{}).get("mae_w")
        v=c.get(self.value_key)
        return round(v*100,1) if self.value_key=="confidence" and v is not None else v

    @property
    def extra_state_attributes(self):
        return {"forecast_only":True,"note":"Geen werkelijk gemeten productie of beschikbaar overschot"}
