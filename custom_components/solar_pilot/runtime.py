"""Local, serialized Home Assistant runtime with feedback and durable leases."""
from __future__ import annotations
import asyncio
from copy import copy, deepcopy
from collections import deque
from dataclasses import fields, replace
from datetime import datetime, timedelta, timezone
import logging
import math
import time
from zoneinfo import ZoneInfo
from time import perf_counter

from homeassistant.core import callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.helpers import entity_registry as er

from .const import DEFAULTS, DEVICE_DEFAULTS, DOMAIN, NAME, VERSION
from .engine import Action, Device, Plan, Site, State, plan
from .wallbox import (WALLBOX_DEFAULTS, Reading, WallboxGuard,
                      confirmed_no_active_request, state_set,
                      protected_entity, conflicting_devices)

from .consumer_wallbox import PRIORITY_DEFAULTS, ConsumerWallboxPriority, follows_wallbox
from .electricity_cost import DailyElectricityCost
from .savings import SavingsHistory
from .wallbox_activity import WallboxActivityHistory, classify_native_status
from .consumer_history_runtime import ConsumerHistoryRecorder
from .dishwasher_app import DishwasherApp
from .dishwasher_priority import DishwasherPriority, enabled as dishwasher_has_priority
from .dishwasher import DishwasherControl, read as read_dishwasher, normalize_config as normalize_dishwasher
from .dishwasher_recovery import RECOVERED_AUTO_KEY, RECOVERY_KEY, RECOVERY_SOURCE
from .analysis_export import AnalysisRecorder
from .house_first import HOUSE_DEFAULTS, HouseFirstGuard, Handover
from .learning import LocalLearning
from .heatpump_learning import HeatPumpActivityModel
from .historical import load_bundled_seed
from .wallbox_profile import WallboxProfile, PROFILE_DEFAULTS
from .wallbox_policy import SESSION_DEFAULTS, classify_session, reclaim_permission
from .pv_model import LOCAL_PV_DEFAULTS, LocalPVModel, PVPrediction
from .pv_forecast import PVForecast
from .phase_learning import PhaseLearning, phase_allocation_from_hint, phase_total_headroom_w
from .battery_analysis import BATTERY_ANALYSIS_DEFAULTS, BatteryOpportunitySimulator
from .battery_runtime import BatteryFleetManager
from .thermal_runtime import SmartClimateManager
from .dhw_runtime import DHWManager
from .ems import (CAPACITY_DEFAULTS, ECONOMY_DEFAULTS, FORECAST_DEFAULTS,
                  PLANNER_DEFAULTS, PHASE_DEFAULTS, KNOWN_LEGACY_CONFLICTS,
                  accounting_step, capacity_decision, fresh_daily_stats,
                  phase_decision, planner_decision)
from .unified_planner import UNIFIED_PLANNER_DEFAULTS, UnifiedPlanner, PLANNER_SETTING_SPECS, planner_settings_catalog
from .cycle_learning import CycleEnergyModel
from .learning_hub import LearningHub
from .live_options import LiveOptions, ARCHIVED, keyed
from .platforms import LivePlatforms
from .priority_board import PriorityBoard
from .heatpump_budget import climate_solar_budget, heatpump_power, heatpump_shared, shared_commitment

_LOGGER = logging.getLogger(__name__)


class SolarRuntime:
    def __init__(self, hass, entry, historical_seed=None):
        self.hass, self.entry = hass, entry
        self.settings = {**DEFAULTS, **entry.data, **entry.options.get("settings", {})}
        self.capacity_settings = {**CAPACITY_DEFAULTS, **entry.options.get("capacity", {})}
        self.economy_settings = {**ECONOMY_DEFAULTS, **entry.options.get("economy", {})}
        self.forecast_settings = {**FORECAST_DEFAULTS, **entry.options.get("forecast", {})}
        self.planner_settings = {**UNIFIED_PLANNER_DEFAULTS, **entry.options.get("planner", {})}
        self.phase_settings = {**PHASE_DEFAULTS, **entry.options.get("phase", {})}
        self.local_pv_settings = {**LOCAL_PV_DEFAULTS, **entry.options.get("local_pv", {})}
        self.battery_analysis_settings = {**BATTERY_ANALYSIS_DEFAULTS, **entry.options.get("battery_analysis", {})}
        self.historical_seed = historical_seed if isinstance(historical_seed, dict) else load_bundled_seed()
        self.local_pv = LocalPVModel(self.local_pv_settings, self.historical_seed)
        self.pv_forecast = PVForecast(self)
        self.phase_learning = PhaseLearning(self.phase_settings)
        self.battery_analysis = BatteryOpportunitySimulator(self.battery_analysis_settings, self.historical_seed)
        self.battery_fleet = BatteryFleetManager(self)
        self.smart_climate = SmartClimateManager(self)
        self.capacity = capacity_decision(datetime.now().astimezone(), None, None, None, {"enabled": False})
        self.phase = phase_decision((None, None, None), {"enabled": False})
        self.ems_stats = fresh_daily_stats()
        self.savings_history = SavingsHistory()
        self.electricity_cost = DailyElectricityCost()
        self.planner_hold_since = {}
        self.unified_planner = UnifiedPlanner(self.planner_settings, self.historical_seed)
        self.cycle_learning = CycleEnergyModel()
        self.unified_plan = None
        self.wallbox_settings = {**WALLBOX_DEFAULTS, **HOUSE_DEFAULTS, **PRIORITY_DEFAULTS, **PROFILE_DEFAULTS, **SESSION_DEFAULTS, **entry.options.get("wallbox", {})}
        self.others_first = True
        self.consumer_wallbox = ConsumerWallboxPriority(self.wallbox_settings)
        self.wallbox_profile = WallboxProfile(self.hass, self.wallbox_settings)
        self.learning = LocalLearning()
        self.heatpump_learning = HeatPumpActivityModel()
        self.handover = None
        self.last_handover = {}
        self.reclaim_blocks = {}
        self._yield_to_wallbox = False
        self.wallbox_guard = self._make_wallbox_guard()
        self.wallbox_activity = WallboxActivityHistory(stale_s=self.wallbox_settings["stale_s"],
            charging_threshold_w=self.wallbox_settings["charging_threshold_w"])
        self.configs = {d["id"]: normalize_dishwasher({**DEVICE_DEFAULTS, **d}) for d in entry.options.get("devices", [])}
        self.dishwasher = DishwasherControl()
        self.dishwasher_priority = DishwasherPriority()
        self.dishwasher_app = DishwasherApp(self)
        self.states = {key: State(last_off=time.monotonic(), cycle_armed=cfg.get("kind") != "dishwasher") for key, cfg in self.configs.items()}
        self.consumer_history = ConsumerHistoryRecorder(hass, entry, {**keyed(entry.options.get(ARCHIVED)), **self.configs}, self.settings["interval_s"])
        self.mode = "observe"
        self.priorities = {}
        self.device_modes = {}
        self.recovery = {}
        self.restart_requested_mode = None
        self._restart_faults = {}
        self._restart_notice = False
        self.faults = {}
        self.listeners = set()
        self.logs = deque(maxlen=30)
        self.pending = None
        self.result = Plan()
        self._start_context = {}
        self.grid_w = None
        self.pv_w = None
        self.filtered = None
        self.managed_w = 0.0
        self.energy_kwh = 0.0
        self.data_loaded = False
        self.energy_estimated = False
        self.problem = ""
        self.problem_kind = ""
        self.last_tick = time.monotonic()
        self.runtime_day = ""
        self.last_issued = -1e12
        self.last_issued_wall = 0.0
        self.invalid_since = None
        self.energy_saved_at = time.monotonic()
        self._lock = asyncio.Lock()
        self._remove_timer = None
        self._closed = False
        self._skip_options_reload_once = False
        self.removal_requested = False
        self._removal_ready_noted = False
        self.store = Store(hass, 1, f"{DOMAIN}.{entry.entry_id}")
        self.dhw = DHWManager(self)
        self.analysis = AnalysisRecorder(self)
        self.learning_hub = LearningHub(self)
        self.live_options = LiveOptions(self)
        self.platforms = LivePlatforms(self)
        self.priority_board = PriorityBoard(self)

    def heat_pump_shared(self):
        """The configured room zones and tank use one physical heat pump."""
        return heatpump_shared(self)

    def _local_now(self):
        zone = getattr(getattr(self.hass, "config", None), "time_zone", "Europe/Brussels")
        try:
            return datetime.now(ZoneInfo(zone))
        except (ValueError, KeyError, TypeError):
            return datetime.now().astimezone()

    def heat_pump_increase_allowed(self, *, check_capacity=True):
        """Final live electrical gate; an earlier plan is never a power lease."""
        grid, valid, _discharge, ready, reported = self._site_data()
        pv, _pv_reported = self._power(self.settings.get("pv_entity"))
        if not valid or not ready or pv is None or pv < 0:
            return False, "Wacht op betrouwbare net-, zonne- en batterijmetingen"
        if reported <= self.last_issued_wall:
            return False, "Wacht op een nieuwe netmeting na de vorige opdracht"
        if time.monotonic() - self.last_issued < self.settings["settle_s"]:
            return False, "Wacht op stabiele metingen na de vorige opdracht"
        if self._closed or self.mode != "solar" or self.restart_blocking or self.faults:
            return False, "Automatische regeling wacht op herstel of vrijgave"
        if self.pending or self.handover or self.battery_fleet.busy:
            return False, "Wacht op bevestiging van de vorige verdeling"
        if not check_capacity:
            return True, "Actuele bronnen en eerdere opdrachten gecontroleerd vóór veilig vrijmaken"
        hp = heatpump_power(self)
        planned = float(self.dhw.settings["estimated_heat_power_w"])
        incremental = shared_commitment(planned, 0, hp["watts"] if hp["valid"] else None)
        isolated = max(0.0, float(self.isolated_reserve_w))
        unconsumed = sum(max(0.0, st.target_w - st.measured_w)
                         for i, st in self.states.items() if st.owned and st.on
                         and i not in self.source_isolated_devices)
        projected = grid + incremental + isolated + unconsumed
        if projected > self.settings["max_import_w"]:
            return False, "Extra warmtepompbedrijf wacht op ruimte binnen de netgrens"
        if (self.phase_settings.get("enabled") and self.phase_settings.get("control_starts")
                and (not self.phase.valid or self.phase.block_increase
                     or self.phase.headroom_w is None
                     or self.phase.headroom_w < incremental + isolated + unconsumed)):
            return False, self.phase.reason or "Wacht op veilige ruimte op de elektrische fasen"
        if self.capacity_settings.get("enabled"):
            if not self.capacity.valid:
                return False, "Wacht op betrouwbare kwartierpiekmeting"
            limit = self.capacity.allowed_grid_w
            if limit is None:
                limit = max(0.0, self.capacity.effective_target_w - self.capacity_settings["margin_w"])
            if projected > limit:
                return False, "Kwartierpiek laat nu geen extra warmtepompbedrijf toe"
        return True, "Actuele elektrische ruimte gecontroleerd"

    def climate_solar_budget(self):
        budget = climate_solar_budget(self)
        allowed, reason = self.heat_pump_increase_allowed()
        if not allowed:
            budget.update(valid=False, reason=reason)
        return budget

    def _dishwasher_comfort_context(self):
        """Respect ordinary heat-pump demand; never stop it for a wash start.

        Ongoing heat consumption is ALREADY in P1. Reserve only an imminent normal
        tank demand not yet drawing confirmed heat, never subtract it twice.
        A missing configured comfort source blocks a new priority start.
        """
        manager = self.dhw
        if not manager.configured:
            return 0.0, ""
        r = manager.reading
        if r.protected:
            # A protected manufacturer cycle is not an absolute dishwasher veto:
            # reserve its configured load, without writing ANY tank target. With
            # ample genuine power both appliances may operate. Unknown protection
            # feedback is not permission to start a competing protected cycle.
            if "onbekend" in r.protection_reason.casefold():
                return 0.0, "Afwasstart wacht op betrouwbare fabrikant-/hygiënebescherming"
            if "staat uit" in r.protection_reason.casefold():
                return 0.0, ""
            hp = heatpump_power(self)
            return shared_commitment(manager.settings["estimated_heat_power_w"], 0,
                                     hp["watts"] if hp["valid"] else None), ""
        if r.temperature_c is None or r.actual_target_c is None:
            return 0.0, "Afwasstart wacht op betrouwbare gekoppelde boilerstatus"
        target, obj = manager._target()
        normal = float(manager.settings["normal_c"])
        differential = float(manager.settings["tank_differential_c"])
        # A verified requested evening reserve up to its configured cap is also
        # ordinary comfort. The optional 60 C target is explicitly excluded.
        ordinary_target = normal
        if normal < r.actual_target_c <= float(manager.settings["evening_cap_c"]) and r.actual_target_c < float(manager.settings["surplus_c"]):
            ordinary_target = r.actual_target_c
        # water_heater.state may be an operating MODE, not proof of current
        # compressor activity. Only explicit action or an exclusive live meter
        # can establish that heating is already included in the net reading.
        hp = heatpump_power(self)
        measured = hp["watts"] if hp["valid"] else None
        heating = bool(obj and obj.attributes.get("hvac_action") == "heating")
        heating = heating or bool(not self.heat_pump_shared() and manager.exclusive_meter()
                                  and measured is not None and measured > 100)
        reserve = 0.0
        if r.temperature_c <= ordinary_target+differential and not heating:
            reserve = shared_commitment(manager.settings["estimated_heat_power_w"], 0,
                                        measured if manager.exclusive_meter() else None)
        # Existing ordinary space heat is never a stop reason or a blanket veto.
        # Pending climate/DHW commands still use the existing serialized gate.
        return reserve, ""

    def _update_dishwasher_priority(self, now, local_now, grid, valid, discharge, ready, wb):
        if self.dhw.configured:
            self.dhw.read(grid, valid, discharge, local_now)
        reserve, comfort_block = self._dishwasher_comfort_context()
        self._shared_heatpump_comfort_reserve_w = reserve
        for i, watch in list(self.dishwasher_priority.watches.items()):
            completed = self.dishwasher_app.data.get(i, {}).get("completion", {})
            if completed.get("ended_at", 0) >= watch["issued_wall"]:
                self.dishwasher_priority.watches.pop(i, None)
        devices = {d.id:d for d in self.devices()}
        # Without a Shelly, the displayed 'measured_w' is an estimate. Reserve a
        # full possible future heater step rather than treating that estimate as
        # proof the cycle already draws its maximum. This is deliberately
        # conservative; actual phase scheduling remains deferred.
        unmetered = sum(devices[i].maximum for i,c in self.configs.items()
            if c.get("kind") == "dishwasher" and self.states[i].on and not c.get("power_entity"))
        reserve += unmetered
        self._dishwasher_unmetered_reserve = unmetered
        permitted = {i for i,c in self.configs.items() if dishwasher_has_priority(c)
            and self.dishwasher.permitted(c, read_dishwasher(self.hass,c), time.time())[0]}
        # This release's additional reservation is scoped to an actual priority
        # claimant, not unrelated installations or tomorrow's waiting request.
        if not (permitted or any(c.get("kind") == "dishwasher" and self.states[i].on
                                 for i,c in self.configs.items())):
            reserve, comfort_block = 0.0, ""
            self._shared_heatpump_comfort_reserve_w = 0.0
        lower = {}
        for i,c in self.configs.items():
            if not dishwasher_has_priority(c) and c.get("power_entity") and self._dedicated_meter(i):
                watts, _ = self._power(c["power_entity"])
                if watts is not None and watts >= 0:
                    lower[i] = watts
        capacity_limit = self.settings["max_import_w"]
        if self.capacity_settings["enabled"]:
            capacity_limit = (0.0 if not self.capacity.valid else min(capacity_limit,
                self.capacity.allowed_grid_w if self.capacity.allowed_grid_w is not None
                else self.capacity.effective_target_w or capacity_limit))
        view = self.dishwasher_priority.evaluate(now=now, wall=time.time(), mode=self.mode,
            configs=self.priority_board.configs(), devices=devices, states=self.states, permitted_ids=permitted,
            actual_grid=grid if valid else None, filtered_grid=self.filtered,
            pv_w=self.pv_w, discharge_w=discharge, reserve_w=self.settings["reserve_w"],
            max_import_w=capacity_limit, reading=wb, wallbox_settings=self.wallbox_settings,
            stable_ev_credit_w=getattr(self.wallbox_guard,"reclaimable_w",0),
            lower_measured=lower, comfort_reserve_w=reserve, comfort_block=comfort_block,
            sample_gap_s=max(30,self.settings["interval_s"]*2),
            site_ready=valid and ready and not self.restart_blocking and not self.faults)
        self._dishwasher_comfort_reserve = reserve
        return view

    def _per_device_wallbox_enabled(self):
        # The configured Wallbox solar-start threshold is harmless by itself.
        # Activate per-device precedence only when at least one consumer explicitly
        # deviates from the global preference, preserving legacy global behaviour.
        if hasattr(self, "priority_board") and self.priority_board.active:
            return True
        return any(c.get("wallbox_precedence", "global") != "global" or dishwasher_has_priority(c)
                   for c in getattr(self, "configs", keyed(self.entry.options.get("devices"))).values())

    def _make_wallbox_guard(self):
        per_device = self._per_device_wallbox_enabled()
        c = {**self.wallbox_settings,
             "policy": "house_first" if self.others_first else "priority",
             "stable_s": self.learning.effective_stable_s(self.wallbox_settings["stable_s"]),
             "sample_gap_s": max(30, self.settings["interval_s"] * 2)}
        return HouseFirstGuard(c) if self.others_first or per_device else WallboxGuard(c)

    @property
    def editable(self):
        return (self.mode != "solar" and not self.dhw.busy and not self.pending and not self.handover
                and not self.battery_fleet.busy and not self.recovery and not any(s.owned for s in self.states.values()))

    def _snapshot(self):
        return {
            "mode": self.mode,
            "restart_requested_mode": self.restart_requested_mode,
            "faults": dict(self.faults),
            "restart_faults": dict(self._restart_faults),
            "live_options": self.live_options.snapshot(),
            "learning_hub": self.learning_hub.snapshot(),
            "dishwasher": self.dishwasher.snapshot(),
            "dishwasher_app": self.dishwasher_app.snapshot(),
            "dishwasher_priority": self.dishwasher_priority.snapshot(),
            "dhw": self.dhw.snapshot(),
            "priorities": self.priorities, "device_modes": self.device_modes,
            "others_first": self.others_first, "learning": self.learning.snapshot(),
            "heatpump_learning": self.heatpump_learning.snapshot(),
            "local_pv": self.local_pv.snapshot(), "pv_forecast": self.pv_forecast.snapshot(), "phase_learning": self.phase_learning.snapshot(),
            "battery_analysis": self.battery_analysis.snapshot(),
            "battery_fleet": self.battery_fleet.snapshot(), "smart_climate": self.smart_climate.snapshot(),
            "unified_planner": self.unified_planner.snapshot(),
            "cycle_learning": self.cycle_learning.snapshot(),
            "reclaim_blocks": self.reclaim_blocks,
            "handover": self.handover.overview(time.monotonic()) if self.handover else None,
            "cycle_armed": {i: s.cycle_armed for i, s in self.states.items()},
            "manual_forced": {i: bool(s.manual_forced) for i, s in self.states.items() if s.manual_forced},
            "manual_stop_requested": {i: bool(s.manual_stop_requested) for i, s in self.states.items() if s.manual_stop_requested},
            "energy_kwh": self.energy_kwh, "ems_stats": self.ems_stats,
            "savings_history": self.savings_history.snapshot(),
            "wallbox_activity": self.wallbox_activity.snapshot(),
            "electricity_cost": self.electricity_cost.snapshot(),
            "daily_runtime": {i: {"date": self.runtime_day, "seconds": round(s.daily_runtime_s, 3), "energy_kwh": round(s.daily_energy_kwh, 6)} for i, s in self.states.items()},
            "leases": {**self.recovery, **{i: {"watts": s.target_w, "name": self.configs[i]["name"]}
                       for i, s in self.states.items() if s.owned}},
        }

    async def _migrate_beta37_activation_profile(self):
        """One-time activation of safe, already configured regulation and learning.

        It never invents entity mappings, confirms a safety acknowledgement,
        grants a new appliance start right or enables unconfirmed battery control.
        The marker makes later user choices sticky.
        """
        current = dict(self.entry.options)
        if current.get("_beta37_activation_profile") == 1:
            return False
        options = deepcopy(current)

        def merge_group(name, **updates):
            value = deepcopy(options.get(name, {})) if isinstance(options.get(name, {}), dict) else {}
            value.update(updates)
            options[name] = value
            return value

        merge_group("analysis", enabled=True, retention_days=7, sample_interval_s=300)
        merge_group("planner", enabled=True, base_load_learning=True, replay_enabled=True,
                    forecast_deferral_enabled=True, adaptive_power_guard=True)
        merge_group("local_pv", enabled=True, seed_enabled=True)
        merge_group("pv_forecast", enabled=True, auto_discover=True,
                    calibration_enabled=True, shadow_enabled=True)
        merge_group("battery_analysis", enabled=True, seed_enabled=True)
        merge_group("economy", enabled=True)

        forecast = deepcopy(options.get("forecast", {})) if isinstance(options.get("forecast", {}), dict) else {}
        if any(forecast.get(k) for k in ("current_hour_entity", "next_hour_entity",
                                         "remaining_today_entity", "tomorrow_entity")):
            forecast["enabled"] = True
            options["forecast"] = forecast
        capacity = deepcopy(options.get("capacity", {})) if isinstance(options.get("capacity", {}), dict) else {}
        if capacity.get("average_demand_entity"):
            capacity["enabled"] = True
            options["capacity"] = capacity
        phase = deepcopy(options.get("phase", {})) if isinstance(options.get("phase", {}), dict) else {}
        phase_sources = [phase.get("phase_1_entity"), phase.get("phase_2_entity"), phase.get("phase_3_entity")]
        if all(phase_sources):
            phase.update(enabled=True, learning_enabled=True, use_learned_device_map=True, control_starts=True)
            phase["shed_on_overlimit"] = bool(phase.get("shed_on_overlimit", False))
            options["phase"] = phase
        wallbox = deepcopy(options.get("wallbox", {})) if isinstance(options.get("wallbox", {}), dict) else {}
        if wallbox.get("power_entity"):
            wallbox["enabled"] = True
            options["wallbox"] = wallbox
        climate = deepcopy(options.get("smart_climate", {})) if isinstance(options.get("smart_climate", {}), dict) else {}
        zones = list(climate.get("zone_entities", []) or [])
        zones_ok = bool(zones)
        for entity_id in zones:
            obj = self.hass.states.get(entity_id)
            modes = {str(x).casefold() for x in (getattr(obj, "attributes", {}) or {}).get("hvac_modes", [])} if obj else set()
            if obj is None or not {"auto", "off"}.issubset(modes):
                zones_ok = False
                break
        if zones:
            climate["enabled"] = True
            if zones_ok:
                climate["control_enabled"] = True
            options["smart_climate"] = climate
        dhw = deepcopy(options.get("dhw", {})) if isinstance(options.get("dhw", {}), dict) else {}
        if dhw.get("target_entity") and dhw.get("temperature_entity") and dhw.get("safety_confirmed") is True:
            dhw["enabled"] = True
            options["dhw"] = dhw
        batteries = [b for b in options.get("batteries", []) if isinstance(b, dict)]
        if batteries:
            fleet = deepcopy(options.get("battery_fleet", {})) if isinstance(options.get("battery_fleet", {}), dict) else {}
            fleet["enabled"] = True
            fleet["control_enabled"] = bool(fleet.get("control_enabled", False))
            options["battery_fleet"] = fleet
        reserved = {self.settings.get("grid_entity"), self.settings.get("export_entity"), self.settings.get("pv_entity"), wallbox.get("power_entity"), dhw.get("power_entity")}
        devices = []
        for row in options.get("devices", []) or []:
            if not isinstance(row, dict):
                continue
            item = deepcopy(row)
            meter = item.get("power_entity")
            if meter and meter not in reserved:
                item["cycle_learning_enabled"] = True
            devices.append(item)
        if devices or "devices" in options:
            options["devices"] = devices
        options["_beta37_activation_profile"] = 1
        await self.live_options.accept(options)
        updater = getattr(getattr(self.hass, "config_entries", None), "async_update_entry", None)
        if updater is not None:
            updater(self.entry, options=options)
        else:
            self.entry.options = options
        self.learning.enabled = True
        self.learning_hub.policy.update(sampling="metered", adaptation="automatic", notifications=True)
        self.learning_hub.last_notification = time.time()
        self.unified_planner.base_load.adaptive_enabled = True
        self.note("Beta.37 startprofiel toegepast: beschikbare regelingen en leermodules zijn actief; ontbrekende bronnen en rechten zijn niet verzonnen.")
        return True

    async def start(self):
        data = await self.store.async_load() or {}
        self.live_options.restore(data.get("live_options", {}))
        await self.consumer_history.start()
        await self.analysis.start()
        self.dishwasher.restore(data.get("dishwasher", {}))
        self.dishwasher_app.restore(data.get("dishwasher_app", {}))
        self.dishwasher_priority.restore(data.get("dishwasher_priority", {}), self.configs)
        self.dhw.restore(data.get("dhw", {}))
        await self.dhw.migrate_beta36(data.get("dhw", {}))
        await self.dhw.migrate_beta56()
        self.electricity_cost.restore(data.get("electricity_cost", {}))
        self.others_first = data.get("others_first", True) is True
        self.learning.restore(data.get("learning", {}), self.configs)
        heatpump_ok = self.heatpump_learning.restore(data.get("heatpump_learning", {}))
        if not heatpump_ok:
            self.note(self.heatpump_learning.restore_note or "Warmtepompleermodel leert opnieuw.")
        self.local_pv.restore(data.get("local_pv", {}))
        self.pv_forecast.restore(data.get("pv_forecast", {}))
        self.phase_learning.restore(data.get("phase_learning", {}), list(self.configs) + list(self._phase_monitor_configs()))
        self.battery_analysis.restore(data.get("battery_analysis", {}))
        self.battery_fleet.restore(data.get("battery_fleet", {}))
        self.smart_climate.restore(data.get("smart_climate", {}))
        self.unified_planner.restore(data.get("unified_planner", {}))
        self.learning_hub.restore(data.get("learning_hub", {}))
        self.cycle_learning.restore(data.get("cycle_learning", {}))
        activated_beta37 = await self._migrate_beta37_activation_profile()
        self.reclaim_blocks = {i: str(reason) for i, reason in data.get("reclaim_blocks", {}).items() if i in self.configs}
        self.priorities = {i: p for i, p in data.get("priorities", {}).items() if i in self.configs}
        self.device_modes = {i: m for i, m in data.get("device_modes", {}).items() if i in self.configs}
        # beta.38 legacy recovery: only a profile that was reconstructed from the
        # old dishwasher dashboard may inherit Auto once. If the user has ever
        # stored a mode for it, that later choice always wins. APP still requires
        # a fresh exact Enabled transition, so setup itself never starts a cycle.
        stored_modes = data.get("device_modes", {}) if isinstance(data.get("device_modes", {}), dict) else {}
        recovery_meta = self.entry.options.get(RECOVERY_KEY, {})
        exact_recovered_id = recovery_meta.get("device_id") if (
            isinstance(recovery_meta, dict)
            and recovery_meta.get("schema") == 1
            and recovery_meta.get("status") == "recovered"
            and recovery_meta.get("source") == RECOVERY_SOURCE
        ) else None
        for recovered_id in self.entry.options.get(RECOVERED_AUTO_KEY, []) or []:
            if recovered_id != exact_recovered_id:
                continue
            if recovered_id in self.configs and recovered_id not in stored_modes:
                self.device_modes[recovered_id] = "auto"
                self.note(f'{self.configs[recovered_id]["name"]}: beta.38 herstelde de afgesproken Auto-deelname; APP-vrijgave blijft per belading verplicht.')
        migrated_priority_board = await self.priority_board.migrate_beta36()
        migrated_heat_priority = await self.priority_board.migrate_beta57()
        # Build the guard after migration so schema-2 per-device Wallbox rights
        # are active immediately after a beta.35 restart, not one reload later.
        self.wallbox_guard = self._make_wallbox_guard()
        if migrated_priority_board:
            self.note("Beta.36-migratie: bestaande flexibele voorrang exact vastgelegd als centrale prioriteitenlijst.")
        if migrated_heat_priority:
            self.note("Beta.57: extra warm water krijgt voorrang op onderbreekbare toestellen; afwas, ruimtecomfort en autoladen blijven beschermd.")
        if activated_beta37:
            self.note("Beta.37: veilige automatische activering is éénmalig toegepast; latere keuzes blijven behouden.")
        self.energy_kwh = max(0, float(data.get("energy_kwh", 0)))
        stored_stats = data.get("ems_stats", {})
        self.ems_stats = dict(stored_stats) if isinstance(stored_stats, dict) else fresh_daily_stats()
        self.savings_history.restore(data.get("savings_history"))
        self.wallbox_activity.restore(data.get("wallbox_activity"))
        daily = data.get("daily_runtime", {})
        dates = {str(v.get("date", "")) for v in daily.values() if isinstance(v, dict)}
        self.runtime_day = next(iter(dates)) if len(dates) == 1 else ""
        for i, value in daily.items():
            if i in self.states and isinstance(value, dict):
                try:
                    self.states[i].daily_runtime_s = max(0.0, float(value.get("seconds", 0)))
                    self.states[i].daily_energy_kwh = max(0.0, float(value.get("energy_kwh", 0)))
                except (TypeError, ValueError):
                    pass
        leases = data.get("leases", {}) if isinstance(data.get("leases", {}), dict) else {}
        self.recovery = {}
        self.data_loaded = True
        for i, armed in data.get("cycle_armed", {}).items():
            if i in self.states:
                self.states[i].cycle_armed = bool(armed)
        for i, forced in (data.get("manual_forced", {}) or {}).items():
            if i in self.states:
                self.states[i].manual_forced = bool(forced)
        for i, requested in (data.get("manual_stop_requested", {}) or {}).items():
            if i in self.states:
                self.states[i].manual_stop_requested = bool(requested)

        stored_faults = data.get("faults", {})
        self.faults = {i: str(reason) for i, reason in stored_faults.items()
                       if i in self.configs and reason} if isinstance(stored_faults, dict) else {}
        stored_restart_faults = data.get("restart_faults", {})
        self._restart_faults = {i: reason for i, reason in stored_restart_faults.items()
                               if self.faults.get(i) == reason} if isinstance(stored_restart_faults, dict) else {}
        # A consumed START ticket is also durable evidence of an interrupted
        # transaction, even if an older store did not contain its lease.
        leases = dict(leases)
        for i, cfg in self.configs.items():
            if cfg.get("kind") == "dishwasher" and self.dishwasher.tickets.get(i, {}).get("attempted"):
                leases.setdefault(i, {"watts": cfg["nominal_w"], "name": cfg["name"]})
        clean_interruption = (not self.faults and not self.dhw.fault and not self.dhw.manual_hold
                              and not self.dhw.needs_review
                              and (any(i in self.configs and self.device_modes.get(i) == "auto" for i in leases)
                                   or bool(getattr(self.dhw, "restart_recovery", None))))
        requested_mode = data.get("restart_requested_mode") or str(data.get("mode", "observe"))
        if requested_mode not in ("observe", "solar", "paused"):
            requested_mode = "observe"
        # beta.46 stored its temporary Observe mode and lost the previous intent.
        # Recover that interrupted installation once; later explicit choices have
        # the new journal key (including null) and are never inferred again.
        if "restart_requested_mode" not in data and requested_mode == "observe" and clean_interruption:
            requested_mode = "solar"
            self.note("Beta.47: door herstartcontrole onderbroken regeling automatisch hervatten zodra de gegevens betrouwbaar zijn.")
        self.restart_requested_mode = requested_mode
        reconcile_now = time.monotonic()
        for i, lease in leases.items():
            if i not in self.configs:
                continue
            if not self._reconcile_restart_lease(i, lease, reconcile_now):
                self.recovery[i] = lease
                self.note(f'{self.configs[i]["name"]}: herstartcontrole wacht automatisch op betrouwbare toestelstatus.')

        for i, cfg in self.configs.items():
            if cfg.get("kind") == "dishwasher":
                self.states[i].cycle_armed = bool(self.dishwasher.tickets.get(i, {}).get("armed"))
                self.states[i].manual_forced = False
                self.states[i].manual_stop_requested = False
        if self.restart_blocking:
            self.mode = "observe"
        elif requested_mode == "solar" and not self.dhw.needs_review and not self.legacy_conflicts():
            self.mode = "solar"
            self.restart_requested_mode = None
            self.note("Zonnestroommodus hervat; alleen toestellen met betrouwbare bronnen mogen opdrachten ontvangen.")
        else:
            self.mode = requested_mode if requested_mode != "solar" else "observe"
            if requested_mode != "solar":
                self.restart_requested_mode = None
            self.note(f"Herstartcontrole automatisch afgerond; modus {self.mode} hervat.")
        if self.recovery:
            names = ", ".join(self.configs[i]["name"] for i in self.recovery)
            continuation = ("Nieuwe automatische starts blijven geblokkeerd zolang een opdrachtuitkomst onzeker is. "
                            if self.restart_blocking else
                            "Andere betrouwbare regelingen mogen doorgaan binnen de net- en veiligheidslimieten. ")
            await self.notify("SolarPilot houdt na de herstart tijdelijk apart: " + names + ". " + continuation + "De controle wordt automatisch herhaald; beschermde programma's worden niet gestopt en eerdere opdrachten worden niet opnieuw verzonden.", restart=True)
        await self.store.async_save(self._snapshot())
        self.dishwasher_app.start()
        self.smart_climate.start()
        await self.tick()
        self._remove_timer = async_track_time_interval(self.hass, self.tick, timedelta(seconds=self.settings["interval_s"]))

    def _restart_active(self, cfg):
        """Read real state without trusting a restored actuator placeholder.

        Switches are stateful: a long unchanged ON report is valid. Appliance
        heartbeats and number bounds keep their existing adapter contracts.
        """
        if cfg.get("kind") == "dishwasher":
            return self._active(cfg)
        key = "active_entity" if cfg["kind"] == "script" else "control_entity"
        obj = self.hass.states.get(cfg.get(key, ""))
        if obj is None or obj.attributes.get("restored"):
            return None
        active = self._active(cfg)
        if active and cfg["kind"] == "number":
            number_obj = self.hass.states.get(cfg.get("number_entity", ""))
            value = self._number(cfg.get("number_entity"))
            if number_obj is None or number_obj.attributes.get("restored") or value is None:
                return None
            if cfg.get("control_unit") and number_obj.attributes.get("unit_of_measurement") != cfg["control_unit"]:
                return None
            try:
                if not (float(number_obj.attributes["min"]) <= cfg["min_units"] <= value
                        <= cfg["max_units"] <= float(number_obj.attributes["max"])):
                    return None
            except (KeyError, TypeError, ValueError):
                return None
        return active

    @property
    def restart_recovery_pending(self):
        return bool(self.recovery) and not self._restart_faults and not self.faults

    @property
    def restart_blocking(self):
        """Only unresolved command outcomes require a site-wide restart hold."""
        return bool(set(self.recovery) & set(self.faults))

    @property
    def source_isolated_devices(self):
        """Quarantine missing device sources without crediting unknown power.

        The original lease remains durable. A valid dedicated power reading may
        cover part of the maximum future load already present in the real P1
        measurement; otherwise reserve the full possible load conservatively.
        """
        isolated = {}
        devices = {d.id: d for d in self.devices()}
        for device_id, st in self.states.items():
            if device_id in self.faults:
                continue
            lease = self.recovery.get(device_id)
            if lease is None and not st.owned:
                continue
            cfg = self.configs[device_id]
            control_missing = self._restart_active(cfg) is None
            source_fault = st.fault
            if cfg.get("power_entity"):
                current_power, _ = self._power(cfg["power_entity"])
                if not self._dedicated_meter(device_id):
                    source_fault = source_fault or "Vermogensmeter is niet exclusief voor dit toestel"
                elif current_power is None or current_power < -1:
                    source_fault = source_fault or "Vermogensmeting onbetrouwbaar"
            if lease is None and st.available and not source_fault and not control_missing:
                continue
            reasons = []
            if lease is not None or not st.available or control_missing:
                reasons.append("toestelstatus of regelaarwaarde ontbreekt of is onbruikbaar")
            if source_fault:
                reasons.append(source_fault)
            maximum = max(0.0, float(devices[device_id].maximum))
            for value in (st.target_w, lease.get("watts", 0) if isinstance(lease, dict) else 0):
                try:
                    watts = float(value)
                except (TypeError, ValueError):
                    continue
                if math.isfinite(watts):
                    maximum = max(maximum, watts)
            measured = None
            if cfg.get("power_entity") and self._reclaim_meter(device_id):
                measured, _ = self._power(cfg["power_entity"])
            present = max(0.0, measured) if measured is not None and measured >= 0 else 0.0
            isolated[device_id] = {"id": device_id, "name": cfg["name"],
                "reason": "; ".join(reasons), "reserve_w": max(0.0, maximum - present)}
        return isolated

    @property
    def isolated_reserve_w(self):
        return sum(info["reserve_w"] for info in self.source_isolated_devices.values())

    def _owned_source_problem(self):
        """Describe derived source guards separately from durable command faults.

        These guards are re-evaluated by _observe every round. Resetting the
        command journal cannot repair an unavailable state or power report.
        """
        descriptions = []
        configuration = False
        for device_id, st in self.states.items():
            if not st.owned or device_id in self.faults or (st.available and not st.fault):
                continue
            reasons = []
            if not st.available:
                reasons.append("toestelstatus of regelaarwaarde ontbreekt of is onbruikbaar")
            if st.fault:
                reasons.append(st.fault)
                configuration |= st.fault != "Vermogensmeting onbetrouwbaar"
            descriptions.append(self.configs[device_id]["name"] + ": " + "; ".join(reasons))
        if not descriptions:
            return "", ""
        if configuration:
            return "source_configuration", "Controleer de gekoppelde toestelbronnen en instellingen — " + " · ".join(descriptions)
        return "source_wait", "Wacht automatisch op betrouwbare toestelgegevens — " + " · ".join(descriptions)

    def _reconcile_restart_lease(self, device_id, lease, now):
        """Adopt a durable lease from current evidence; never issue a command."""
        cfg, st = self.configs[device_id], self.states[device_id]
        active = self._restart_active(cfg)
        ticket = self.dishwasher.tickets.get(device_id, {}) if cfg.get("kind") == "dishwasher" else {}
        if ticket.get("attempted"):
            reading = self.dishwasher.readings[device_id]
            try:
                sent_at, reported_at = float(ticket.get("sent_at")), float(reading.stamp)
                post_command = math.isfinite(sent_at) and math.isfinite(reported_at) and reported_at > sent_at
            except (TypeError, ValueError):
                post_command = False
            if not post_command:
                reason = "START-uitkomst onzeker na herstart; wacht op een nieuwe cyclusrapportage na de opdracht"
                if device_id not in self.faults:
                    self.faults[device_id] = reason
                    self._restart_faults[device_id] = reason
                return False
        if cfg.get("kind") == "dishwasher":
            reading = self.dishwasher.readings[device_id]
            if active is True or (active is False and reading.finished):
                # START may have been saved before the native event consumed its
                # APP request. A completed/restored running cycle must consume
                # that request too, or a later Idle report could re-arm it.
                self.dishwasher_app.event(cfg, cfg.get("dishwasher_state_entity"), reading.raw, time.time())
                self.dishwasher_app.cancel(cfg, "Herstart: APP-aanvraag verbruikt door bevestigde cyclus")
        if cfg.get("kind") == "dishwasher" and self.dishwasher.tickets.get(device_id, {}).get("attempted"):
            reading = self.dishwasher.readings[device_id]
            if active is True:
                self.dishwasher.confirmed(device_id)
            elif active is False and reading.finished:
                self.dishwasher.review(device_id)
            else:
                reason = "START-uitkomst onzeker na herstart; wacht op bevestigde cyclus of controleer de afwasmachine"
                if device_id not in self.faults:
                    self.faults[device_id] = reason
                    self._restart_faults[device_id] = reason
                return False
            reason = self._restart_faults.pop(device_id, None)
            if reason and self.faults.get(device_id) == reason:
                self.faults.pop(device_id, None)
        if active is None:
            return False
        if active:
            try:
                target = max(float(lease.get("watts", 0) or 0), float(cfg["nominal_w"]))
            except (AttributeError, TypeError, ValueError):
                target = float(cfg["nominal_w"])
            if not math.isfinite(target):
                target = float(cfg["nominal_w"])
            if cfg["kind"] == "number" and not self._target_matches(cfg, target):
                # A changed physical setpoint belongs to its current operator.
                # Reading it is not permission to adopt it and immediately
                # reduce it under SolarPilot's normal minimum-power plan.
                st.owned, st.on, st.available = False, True, True
                st.target_w = 0
                st.last_on = now
                st.manual_until = now + cfg["manual_hold_s"]
                st.manual_forced = st.manual_stop_requested = False
                st.observed_once = True
                self.note(f'{cfg["name"]}: instelling tijdens herstart gewijzigd; huidige bediening blijft vrij zonder opdracht.')
                return True
            st.owned, st.on, st.available = True, True, True
            st.target_w = target
            st.last_on = now
            if cfg["non_interruptible"]:
                st.cycle_armed = False
            self.note(f'{cfg["name"]}: herstartcontrole automatisch — toestel staat aan; beheer hervat zonder schakelopdracht.')
        else:
            st.owned, st.on, st.available = False, False, True
            st.target_w = 0
            st.last_off = now
            st.manual_forced = st.manual_stop_requested = False
            self.note(f'{cfg["name"]}: herstartcontrole automatisch — toestel staat uit; normale regeling hervat.')
        st.observed_once = True
        return True

    async def _retry_restart_recovery(self, now):
        changed = False
        for device_id, lease in tuple(self.recovery.items()):
            if device_id in self.configs and self._reconcile_restart_lease(device_id, lease, now):
                self.recovery.pop(device_id, None)
                changed = True
        requested = self.restart_requested_mode
        if not self.restart_blocking and requested is not None:
            if requested != "solar" or (not self.dhw.needs_review and not self.legacy_conflicts()):
                self.mode = requested
                self.restart_requested_mode = None
                for st in self.states.values():
                    st.start_since = None
                self.note(f"Herstartcontrole automatisch afgerond; modus {self.mode} hervat.")
                changed = True
        if changed:
            await self.store.async_save(self._snapshot())
        if not self.recovery and self._restart_notice and not self.dhw.needs_review and not self.faults:
            self._restart_notice = False
            if self.hass.services.has_service("persistent_notification", "dismiss"):
                await self.hass.services.async_call("persistent_notification", "dismiss", {
                    "notification_id": f"{DOMAIN}_{self.entry.entry_id}"}, blocking=False)

    async def close(self, *, persist=True):
        self._closed = True
        self.dishwasher_app.close()
        self.smart_climate.close()
        if self._remove_timer:
            self._remove_timer()
            self._remove_timer = None
        async with self._lock:
            if not persist:
                # A failed setup must not flush partly restored models/leases.
                # HA Store has no public cancel-only operation; these bounded
                # cleanup hooks remove its delayed and final-write listeners
                # without deleting or replacing any saved data.
                for store in (self.store, self.consumer_history.store, self.analysis.store):
                    for name in ("_async_cleanup_delay_listener", "_async_cleanup_final_write_listener"):
                        cleanup = getattr(store, name, None)
                        if callable(cleanup):
                            cleanup()
            await self.consumer_history.close(persist=persist)
            await self.analysis.close(persist=persist)
            if persist:
                await self.store.async_save(self._snapshot())

    @callback
    def subscribe(self, listener):
        self.listeners.add(listener)
        return lambda: self.listeners.discard(listener)

    @callback
    def publish(self):
        for listener in tuple(self.listeners):
            listener()

    def note(self, message):
        self.logs.appendleft({"time": datetime.now(timezone.utc).isoformat(timespec="seconds"), "message": message})
        _LOGGER.info("%s: %s", NAME, message)
        if hasattr(self, "analysis"):
            self.analysis.event("runtime", message)

    async def notify(self, message, restart=False):
        self._restart_notice = restart
        if self.hass.services.has_service("persistent_notification", "create"):
            await self.hass.services.async_call("persistent_notification", "create", {
                "title": NAME, "message": message,
                "notification_id": f"{DOMAIN}_{self.entry.entry_id}",
            }, blocking=False)

    def legacy_conflicts(self):
        conflicts = []
        for entity_id, label in KNOWN_LEGACY_CONFLICTS.items():
            obj = self.hass.states.get(entity_id)
            if obj is not None and obj.state == "on":
                conflicts.append({"entity_id": entity_id, "name": label})
        return conflicts

    def _scalar(self, entity_id, allowed_units=None, stale_s=None):
        if not entity_id:
            return None
        obj = self.hass.states.get(entity_id)
        if obj is None or obj.state in ("unknown", "unavailable", "") or self._reported_wall(obj) is None:
            return None
        try:
            value = float(obj.state)
        except (TypeError, ValueError):
            return None
        if not math.isfinite(value):
            return None
        if allowed_units is not None and obj.attributes.get("unit_of_measurement") not in allowed_units:
            return None
        if stale_s is not None:
            stamp = self._reported_wall(obj)
            if not -5 <= time.time() - stamp <= stale_s:
                return None
        return value

    def _economy_prices(self):
        e = self.economy_settings
        if not e["enabled"]:
            return None, None
        imp = self._scalar(e.get("import_price_entity"))
        exp = self._scalar(e.get("export_price_entity"))
        imp = e["fixed_import_eur_kwh"] if imp is None else imp
        exp = e["fixed_export_eur_kwh"] if exp is None else exp
        return imp, exp

    def _forecast_values(self):
        f = self.forecast_settings
        values = {}
        modern = self.pv_forecast.cached
        if modern.get("available"):
            return {key+"_kwh": modern.get("raw_"+key+"_kwh") for key in ("current_hour", "next_hour", "remaining_today", "tomorrow")}
        if f["enabled"]:
            for key in ("current_hour_entity", "next_hour_entity", "remaining_today_entity", "tomorrow_entity"):
                value = self._scalar(f.get(key), {"Wh", "kWh"}, f["stale_s"])
                obj = self.hass.states.get(f.get(key)) if f.get(key) else None
                values[key.replace("_entity", "_kwh")] = (value * (.001 if obj and obj.attributes.get("unit_of_measurement") == "Wh" else 1)) if value is not None else None
        return values

    def _sun_position(self):
        entity_id = self.local_pv_settings.get("sun_entity", "sun.sun")
        obj = self.hass.states.get(entity_id) if entity_id else None
        if obj is None:
            return None, None
        try:
            az = float(obj.attributes.get("azimuth"))
            el = float(obj.attributes.get("elevation"))
        except (TypeError, ValueError):
            return None, None
        return (az if math.isfinite(az) else None, el if math.isfinite(el) else None)

    def _forecast_power(self):
        modern = self.pv_forecast.cached
        if modern.get("available") and modern.get("horizon"):
            return modern["horizon"][0]["raw_w"]
        entity_id = self.local_pv_settings.get("forecast_power_entity")
        if not entity_id:
            return None
        value = self._scalar(entity_id, {"W", "kW"}, self.forecast_settings.get("stale_s", 7200))
        obj = self.hass.states.get(entity_id)
        if value is None or obj is None:
            return None
        return value * (1000 if obj.attributes.get("unit_of_measurement") == "kW" else 1)

    def _local_pv_update(self, local_now):
        self.pv_forecast.update(local_now)
        modern = self.pv_forecast.cached
        if modern.get("available"):
            rows = modern.get("horizon", [])
            p = PVPrediction(factor=modern["factor"], confidence=modern["confidence"],
                source=modern["model_source"], corrected_power_w=rows[0]["corrected_w"] if rows else None,
                corrected_current_hour_kwh=modern.get("corrected_current_hour_kwh"),
                corrected_next_hour_kwh=modern.get("corrected_next_hour_kwh"),
                next_factor=rows[1]["factor"] if len(rows)>1 else 1.,
                next_confidence=rows[1]["confidence"] if len(rows)>1 else 0.,
                state="learning" if modern["confidence"]<.55 else "normal",
                reason=f"Lokale PV-kalibratie: {modern['model']['days']} geldige dagen; {modern['model']['last_reason']}")
            self.local_pv.last_prediction=p
            return p
        forecast = self._forecast_values()
        forecast_power = self._forecast_power()
        azimuth, elevation = self._sun_position()
        if not self.pv_forecast.settings.get("enabled"):
            self.local_pv.observe(
                wall_stamp=time.time(), local_now=local_now, actual_w=self.pv_w,
                forecast_w=forecast_power, azimuth=azimuth, elevation=elevation)
        return self.local_pv.prediction(
            local_now=local_now, forecast_power_w=forecast_power,
            current_hour_kwh=forecast.get("current_hour_kwh"),
            next_hour_kwh=forecast.get("next_hour_kwh"),
            azimuth=azimuth, elevation=elevation)

    def _phase_monitor_configs(self):
        """Read-only power sensors explicitly selected for passive phase fingerprinting."""
        out = {}
        configured_power = {cfg.get("power_entity") for cfg in self.configs.values() if cfg.get("power_entity")}
        for entity_id in self.phase_settings.get("monitor_power_entities", []) or []:
            if not entity_id or entity_id in configured_power:
                continue
            obj = self.hass.states.get(entity_id)
            name = (obj.attributes.get("friendly_name") if obj is not None else None) or entity_id
            out[f"monitor::{entity_id}"] = {"name": name, "power_entity": entity_id, "phase_hint": "auto", "monitor_only": True}
        return out

    def _phase_battery_configs(self):
        """Battery profiles as signed net contributors for phase dashboards."""
        out = {}
        for battery_id, cfg in self.battery_fleet.configs.items():
            if not cfg.get("enabled", True) or not cfg.get("power_entity"):
                continue
            out[f"battery::{battery_id}"] = {**cfg, "name": cfg.get("name", battery_id), "monitor_only": True, "is_battery": True}
        return out

    def _phase_device_limits(self):
        if not (self.phase_settings.get("enabled") and self.phase_settings.get("control_starts") and self.phase.valid):
            return {}
        use_learned = bool(self.phase_settings.get("use_learned_device_map", False))
        minimum_confidence = float(self.phase_settings.get("learning_min_confidence", .75))
        limits = {}
        for device_id, cfg in self.configs.items():
            hint = cfg.get("phase_hint", "auto")
            learned = self.phase_learning.profile(device_id)
            shares, _source = phase_allocation_from_hint(
                hint, learned if use_learned else {}, minimum_confidence)
            if shares is None:
                limits[device_id] = self.phase.headroom_w
            else:
                headroom = phase_total_headroom_w(self.phase.phase_w, self.phase.guarded_limit_w, shares)
                limits[device_id] = self.phase.headroom_w if headroom is None else headroom
        return limits

    def _phase_attribution(self):
        result = {
            "enabled": bool(self.phase_settings.get("enabled")),
            "valid": bool(self.phase.valid), "phases": [],
            "mapped_devices": 0, "unmapped_measured_devices": 0,
            "note": ("P1-fasewaarden zijn netto import/injectie. Bekende toestelvermogens zijn bruto verbruik; "
                     "de restwaarde kan door PV negatief zijn en is geen gecertificeerde circuitmeting."),
        }
        vals = tuple(self.phase.phase_w or ())
        if not result["enabled"] or not result["valid"] or len(vals) != 3 or any(v is None for v in vals):
            return result
        rows = [{"name": f"L{i+1}", "net_w": round(float(vals[i]), 1),
                 "known_device_w": 0.0, "battery_net_w": 0.0,
                 "residual_net_w": round(float(vals[i]), 1), "devices": [], "batteries": []}
                for i in range(3)]
        min_conf = float(self.phase_settings.get("learning_min_confidence", .75))
        all_phase_configs = {**self.configs, **self._phase_monitor_configs(), **self._phase_battery_configs()}
        for device_id, cfg in all_phase_configs.items():
            if not cfg.get("power_entity"):
                continue
            if cfg.get("is_battery"):
                raw, _stamp = self._power(cfg.get("power_entity"), self.phase_settings.get("stale_s", 120))
                if raw is None:
                    continue
                signed_discharge = raw if cfg.get("power_sign") == "discharge_positive" else -raw
                # Net contribution: charging increases import (+), discharging reduces import (-).
                watts = -signed_discharge
            elif device_id in self.states:
                state = self.states.get(device_id)
                watts = None if state is None else float(state.measured_w or 0.0)
            else:
                watts, _stamp = self._power(cfg.get("power_entity"), self.phase_settings.get("stale_s", 120))
            if watts is None or (not cfg.get("is_battery") and watts < 0):
                continue
            learned = self.phase_learning.profile(device_id)
            shares, source = phase_allocation_from_hint(cfg.get("phase_hint", "auto"), learned, min_conf)
            if shares is None:
                result["unmapped_measured_devices"] += 1
                continue
            result["mapped_devices"] += 1
            confidence = 1.0 if source == "handmatig" else float(learned.get("confidence", 0) or 0)
            for idx, share in enumerate(shares):
                if share <= 0:
                    continue
                allocated = float(watts) * float(share)
                if cfg.get("is_battery"):
                    rows[idx]["battery_net_w"] += allocated
                    rows[idx]["batteries"].append({
                        "id": device_id, "name": cfg.get("name", device_id),
                        "net_w": round(allocated, 1), "total_net_w": round(float(watts), 1),
                        "share": round(float(share), 3), "source": source})
                else:
                    allocated = max(0.0, allocated)
                    rows[idx]["known_device_w"] += allocated
                    rows[idx]["devices"].append({
                        "id": device_id, "name": cfg.get("name", device_id),
                        "power_w": round(allocated, 1), "total_power_w": round(max(0.0, watts), 1),
                        "share": round(float(share), 3), "source": source, "confidence": round(confidence, 3)})
        for row in rows:
            row["known_device_w"] = round(row["known_device_w"], 1)
            row["battery_net_w"] = round(row["battery_net_w"], 1)
            row["residual_net_w"] = round(row["net_w"] - row["known_device_w"] - row["battery_net_w"], 1)
            row["devices"].sort(key=lambda x: x["power_w"], reverse=True)
            row["batteries"].sort(key=lambda x: abs(x["net_w"]), reverse=True)
        result["phases"] = rows
        return result

    def _planner_device_configs_for_overview(self):
        effective={d.id:d for d in self.devices()}
        out=[]
        for i,cfg in self.configs.items():
            st=self.states[i]; p=effective.get(i).nominal_w if i in effective else float(cfg.get("nominal_w",0) or 0)
            program=self._cycle_program(cfg)
            cyc=self.cycle_learning.estimate(i,program,fallback_energy_kwh=cfg.get("cycle_energy_kwh",0),
                fallback_duration_min=cfg.get("cycle_duration_min",0),fallback_peak_w=max(p,float(cfg.get("nominal_w",0) or 0)))
            out.append({**cfg,"priority": effective[i].priority if self.priority_board.active else cfg.get("priority",50),"power_w":p,"enabled":self.device_modes.get(i,"auto")!="disabled",
                        "contiguous_cycle":bool(cfg.get("non_interruptible")),
                        "cycle_energy_kwh":cyc.energy_kwh,"cycle_duration_min":cyc.duration_min,"cycle_peak_w":cyc.peak_w,
                        "cycle_program":cyc.program,"cycle_confidence":cyc.confidence})
        return out

    def ems_overview(self):
        e = self.economy_settings
        f = self.forecast_settings
        imp, exp = self._economy_prices()
        if imp is None:
            imp = e["fixed_import_eur_kwh"]
        if exp is None:
            exp = e["fixed_export_eur_kwh"]
        forecast = self._forecast_values()
        local_pv = self.local_pv.overview()
        phase_learning = self.phase_learning.overview(self.configs, self._phase_monitor_configs())
        battery_analysis = self.battery_analysis.overview(
            imp, exp, existing_battery=bool(self.settings.get("battery_power_entity") or self.battery_fleet.configured))
        battery_fleet = self.battery_fleet.overview()
        smart_climate = self.smart_climate.overview()
        conflicts = self.legacy_conflicts()
        warnings = []
        if conflicts:
            warnings.append("Vervangen regelaar/automatisering nog actief")
        if self.capacity_settings["enabled"] and not self.capacity.valid:
            warnings.append("Kwartierpiekmeting onbetrouwbaar; optionele netlast wordt beperkt")
        if self.phase_settings["enabled"] and not self.phase.valid:
            warnings.append("Fasevermogens onbetrouwbaar of onvolledig")
        elif self.phase.release_flexible:
            warnings.append(self.phase.reason)
        elif self.phase.block_increase:
            warnings.append("Fasebewaking blokkeert nieuwe flexibele starts: " + self.phase.reason)
        if f["enabled"] and forecast and all(v is None for v in forecast.values()):
            warnings.append("Zonnevoorspelling niet beschikbaar of te oud")
        if self.battery_fleet.settings.get("control_enabled") and self.battery_fleet.state.faults:
            warnings.append("Batterijbediening heeft een fout en is voor het betrokken profiel geblokkeerd")
        if self.smart_climate.settings.get("enabled") and self.smart_climate.last_forecast_error:
            warnings.append(self.smart_climate.last_forecast_error)
        if self.smart_climate.settings.get("enabled") and self.smart_climate.state.fault:
            warnings.append(self.smart_climate.state.fault)
        value = imp - exp
        advice = []
        if e["enabled"]:
            if value > 0.001:
                advice.append(f"Eigen PV gebruiken vermijdt ongeveer € {value:.3f}/kWh aan marginale energiekost tegenover injecteren")
            elif value < -0.001:
                advice.append("Injectievergoeding ligt boven afnameprijs; prijsoptimalisatie kan afwijken van maximale zelfconsumptie")
        current = forecast.get("current_hour_kwh")
        nxt = forecast.get("next_hour_kwh")
        if (self.local_pv_settings.get("enabled")
                and local_pv.get("confidence", 0) >= float(self.local_pv_settings.get("min_confidence", .55))):
            current = local_pv.get("corrected_current_hour_kwh") if local_pv.get("corrected_current_hour_kwh") is not None else current
            nxt = local_pv.get("corrected_next_hour_kwh") if local_pv.get("corrected_next_hour_kwh") is not None else nxt
            if local_pv.get("state") in ("shadow_expected", "recovery_expected"):
                advice.append(local_pv.get("reason", "Lokaal PV-profiel verandert"))
        if smart_climate.get("enabled"):
            advice.append("Klimaat: " + smart_climate.get("decision", {}).get("reason", "thermisch model verzamelt data"))
        if battery_fleet.get("enabled"):
            advice.append("Batterijvloot: " + battery_fleet.get("reason", "alleen monitoren"))
        # De Unified Planner beoordeelt de volledige horizon; geen losse één-uurregel
        # meer in de actuele beslislaag. Vat alleen het huidige plan samen.
        if self.unified_plan is not None:
            for finding in self.unified_plan.findings[:2]:
                advice.append("Planning: " + finding)
            future_devices=[]
            for device_id, dp in self.unified_plan.devices.items():
                if dp.selected_slots:
                    idx=dp.selected_slots[0]
                    if 0 <= idx < len(self.unified_plan.slots):
                        future_devices.append((self.unified_plan.slots[idx].start, dp.name))
            if future_devices:
                future_devices.sort(key=lambda x:x[0])
                when,name=future_devices[0]
                advice.append(f"Eerstvolgende geplande flexlast: {name} rond {when.strftime('%H:%M')}")
        holds = [c["name"] for i, c in self.configs.items() if self.states[i].planner_hold]
        early = [c["name"] for i, c in self.configs.items() if self.states[i].planner_grid_force]
        stats = dict(self.ems_stats)
        pv = stats.get("pv_kwh", 0.0) or 0.0
        stats["self_consumption_pct"] = None if pv <= 0 else round(100 * (stats.get("pv_self_used_kwh", 0.0) or 0.0) / pv, 1)
        try:
            value_day = datetime.now(ZoneInfo(getattr(getattr(self.hass, "config", None),
                                                     "time_zone", "Europe/Brussels"))).date().isoformat()
        except (TypeError, ValueError, KeyError):
            value_day = datetime.now().astimezone().date().isoformat()
        return {
            "capacity": self.capacity.__dict__, "phase": self.phase.__dict__,
            "legacy_conflicts": conflicts, "ready": not warnings, "warnings": warnings, "advice": advice,
            "economy": {"enabled": e["enabled"], "import_eur_kwh": imp, "export_eur_kwh": exp, "self_use_value_eur_kwh": value},
            "forecast": {"enabled": f["enabled"], **forecast}, "local_pv": local_pv, "pv_forecast": self.pv_forecast.cached,
            "phase_learning": phase_learning, "phase_attribution": self._phase_attribution(),
            "historical_phase_profile": self.historical_seed.get("phases", {}),
            "battery_analysis": battery_analysis, "battery_fleet": battery_fleet,
            "smart_climate": smart_climate,
            "cycle_learning": self.cycle_learning.overview(self.configs),
            "planner": {**self.unified_planner.overview(self._planner_device_configs_for_overview()),
                        "settings": dict(self.planner_settings),
                        "settings_catalog": planner_settings_catalog(self.planner_settings),
                        "held_devices": holds, "early_grid_devices": early,
                        "price_sources": dict(getattr(self, "planner_price_sources", {"import":"vaste prijs","export":"vaste prijs"})),
                        "adaptive_power_guard": self.planner_settings.get("adaptive_power_guard", True)},
            "today": stats,
            "savings": self.savings_history.report(stats, economy_enabled=e["enabled"],
                power_estimated=self.energy_estimated,
                current_date=value_day),
            "electricity_today": dict(self.electricity_cost.cached),
        }

    def _bool(self, entity_id):
        if not entity_id:
            return True
        obj = self.hass.states.get(entity_id)
        if obj is None or obj.state not in ("on", "off") or self._reported_wall(obj) is None:
            return None
        return obj.state == "on"

    def _active(self, cfg):
        if cfg.get("kind") == "dishwasher":
            reading = read_dishwasher(self.hass, cfg)
            reading = self.dishwasher_app.overlay(cfg, reading)
            self.dishwasher.readings[cfg["id"]] = reading
            return reading.active
        return self._bool(cfg.get("active_entity") if cfg["kind"] == "script" else cfg.get("control_entity"))

    def _number(self, entity_id):
        obj = self.hass.states.get(entity_id) if entity_id else None
        if obj is None or self._reported_wall(obj) is None:
            return None
        try:
            value = float(obj.state)
        except (TypeError, ValueError):
            return None
        return value if math.isfinite(value) else None

    @staticmethod
    def _reported_wall(obj):
        """Reject placeholders and invalid reports without aging static helpers."""
        if obj is None or obj.attributes.get("restored"):
            return None
        stamp = getattr(obj, "last_reported", None) or getattr(obj, "last_updated", None)
        try:
            wall = stamp.timestamp()
            if isinstance(wall, bool) or not isinstance(wall, (int, float)):
                return None
            return wall if math.isfinite(wall) and 0 <= wall <= time.time() + 5 else None
        except (AttributeError, TypeError, ValueError, OSError, OverflowError):
            return None

    def _power(self, entity_id, stale_s=None):
        """Power only. Never silently interpret kWh as kW or refresh frozen data."""
        if not entity_id:
            return None, 0.0
        obj = self.hass.states.get(entity_id)
        value = self._number(entity_id)
        if obj is None or value is None:
            return None, 0.0
        unit = obj.attributes.get("unit_of_measurement")
        if unit not in ("W", "kW"):
            return None, 0.0
        stamp = self._reported_wall(obj)
        if stamp is None:
            return None, 0.0
        age = time.time() - stamp
        if age > (self.settings["stale_s"] if stale_s is None else stale_s) or age < -5:
            return None, stamp
        watts = value * (1000 if unit == "kW" else 1)
        return watts, stamp

    def _wallbox_text_report(self, entity_id, require_fresh=True):
        obj = self.hass.states.get(entity_id) if entity_id else None
        if obj is None or obj.state in ("unknown", "unavailable", ""):
            return None, None
        stamp = self._reported_wall(obj)
        if stamp is None:
            return None, None
        age = time.time() - stamp
        if require_fresh and (age > self.wallbox_settings["stale_s"] or age < -5):
            return None, stamp
        return obj.state, stamp

    def _wallbox_text(self, entity_id, require_fresh=True):
        value, _stamp = self._wallbox_text_report(entity_id, require_fresh)
        return value

    def _wallbox_reading(self):
        c = self.wallbox_settings
        if not c["enabled"]:
            return Reading()
        power, stamp = self._power(c.get("power_entity"), c["stale_s"])
        status, status_stamp = self._wallbox_text_report(c.get("status_entity"))
        mode = self._wallbox_text(c.get("mode_entity"))
        if c.get("demand_entity"):
            # Explicit binary/manual request. Its template must propagate source
            # availability; a legitimately unchanged helper is not a stale meter.
            demand = self._bool(c["demand_entity"])
        elif status is None:
            demand = None
        elif status.casefold() in state_set(c["demand_states"]):
            demand = True
        elif status.casefold() in state_set(c["idle_states"]):
            demand = False
        else:
            demand = None
        issue = ""
        if power is None or power < 0:
            issue = "Wallbox-laadvermogen ontbreekt, is te oud of is geen geldig verbruik in W/kW"
        elif demand is None:
            issue = "Wallbox-laadvraag onbekend: controleer statuskoppeling of vraagsensor"
        if conflicting_devices(self.hass, c, list(self.configs.values())):
            issue = "Wallbox is ook als bestuurbaar toestel gekoppeld; verwijder die dubbele koppeling"
        connected = None
        if c.get("connected_entity"):
            text = self._wallbox_text(c["connected_entity"])
            connected = {"on": True, "off": False}.get(text)
            if connected is None:
                issue = issue or "Wallbox-aansluitsignaal onbekend of te oud"
        elif demand is True or (power or 0) >= c["charging_threshold_w"]:
            connected = True  # Waiting/charging status is evidence at this charger.
        session_value = self._wallbox_text(c.get("session_mode_entity"))
        session = classify_session(c, mode, session_value)
        return Reading(power, stamp, demand, status, session.mode, not bool(issue), issue,
                       max(0, time.time()-stamp) if stamp else math.inf, connected,
                       raw_mode=mode, session_reason=session.reason, session_confirmed=session.confirmed,
                       session_value=session_value, status_stamp=status_stamp)

    def _observe_wallbox_activity(self, reading, grid_w, discharge_w):
        """Record native reports only; do not influence charging or priority."""
        history = self.wallbox_activity
        previous_end = history.events[-1] if history.events else None
        was_ongoing = history.ongoing is not None
        history.stale_s = self.wallbox_settings["stale_s"]
        history.charging_threshold_w = self.wallbox_settings["charging_threshold_w"]
        history.update(reading, time.time(), grid_w=grid_w, pv_w=self.pv_w,
            free_w=max(0.0, -grid_w-discharge_w-self.settings["reserve_w"]) if grid_w is not None else None,
            enabled=self.wallbox_settings["enabled"])
        latest_end = history.events[-1] if history.events else None
        if self.data_loaded and (latest_end != previous_end or was_ongoing != (history.ongoing is not None)):
            self.store.async_delay_save(self._snapshot, 1)

    def wallbox_overview(self):
        c, g = self.wallbox_settings, self.wallbox_guard
        r, v = g.reading, g.result
        raw_age = time.time() - r.stamp if r.stamp else None
        age = max(0, int(raw_age)) if raw_age is not None and math.isfinite(raw_age) else None
        full_solar = bool(r.session_confirmed and (r.mode or "").casefold() in state_set(c.get("full_solar_states", "")))
        reclaimable = round(getattr(g, "reclaimable_w", 0), 1)
        reclaim_now = bool(full_solar and r.valid and reclaimable > 0)
        no_request = confirmed_no_active_request(r, c)
        activity_known = bool(r.valid and r.power_w is not None and math.isfinite(r.power_w)
                              and r.power_w >= 0 and raw_age is not None and math.isfinite(raw_age)
                              and -5 <= raw_age <= c["stale_s"] and math.isfinite(r.age_s)
                              and -5 <= r.age_s <= c["stale_s"])
        charging_now = bool(activity_known and r.power_w >= c["charging_threshold_w"])
        native_activity = classify_native_status(r.status, r.demand)[0]
        activity = ("unknown" if not activity_known else "charging" if charging_now
                    else "waiting" if native_activity == "waiting" else "stopped")
        reclaim_reason = (
            "Geen actieve Wallbox-laadvraag: geen vermogen gereserveerd"
            if no_request else
            "Effectieve zonnelaadsessie bevestigd en stabiel terugneembaar laadvermogen gemeten"
            if reclaim_now else
            r.session_reason if not full_solar else
            "Zonnelaadsessie bevestigd, maar nog geen stabiel terugneembaar laadvermogen beschikbaar"
        )
        return {"enabled": c["enabled"], "name": c["name"], "policy": "house_first" if self.others_first else "priority",
                "others_first": self.others_first,
                "per_device_priority": self._per_device_wallbox_enabled(),
                "consumer_priority": self.consumer_wallbox.result.__dict__,
                "connected": r.connected, "effective_mode": r.mode, "configured_mode": r.raw_mode,
                "session_entity": c.get("session_mode_entity") or "",
                "session_value": r.session_value,
                "session_confirmed": r.session_confirmed, "session_reason": r.session_reason,
                "reclaim_allowed_now": reclaim_now, "reclaim_reason": reclaim_reason,
                "priority_min_power_w": self.consumer_wallbox.settings["priority_min_power_w"],
                "charging_profile": self.wallbox_profile.cached,
                "comfort_priority": "Warmtepompcomfort vóór Wallbox; extra 60 °C ná Wallbox",
                "priority_switch": self.entity_id("switch", "others_first"),
                "reclaimable_w": reclaimable,
                "handover": self.handover.overview(time.monotonic()) if self.handover else self.last_handover,
                "reclaim_blocks": dict(self.reclaim_blocks),
                "read_only": True, "state": v.state, "reason": v.reason,
                "activity": activity, "active": charging_now, "activity_known": activity_known,
                "activity_details": self.wallbox_activity.overview(),
                "charging_threshold_w": c["charging_threshold_w"],
                "power_w": r.power_w if r.valid else None, "last_report_age_s": age,
                "demand": r.demand, "reported_status": r.status, "reported_mode": r.mode,
                "warning": v.warning, "block_increase": v.block_increase,
                "release_flexible": v.release_flexible, "stable_extra_w": v.max_increase_w,
                "remaining_s": v.remaining_s, "possible_interactions": g.conflict_count,
                "stable_s": g.settings["stable_s"], "stale_s": c["stale_s"],
                "meter_note": "Laatste HA-rapport is niet noodzakelijk het fysieke meettijdstip"}

    def _site_data(self):
        stamps = []
        grid, stamp = self._power(self.settings.get("grid_entity"))
        stamps.append(stamp)
        if self.settings["grid_sign"] == "separate":
            export, exp_stamp = self._power(self.settings.get("export_entity"))
            stamps.append(exp_stamp)
            if grid is None or export is None or grid < 0 or export < 0:
                grid = None
            else:
                grid -= export
        elif grid is not None and self.settings["grid_sign"] == "export_positive":
            grid = -grid
        discharge = 0.0
        valid = grid is not None
        ready = True
        if self.battery_fleet.settings.get("enabled") and self.battery_fleet.configured:
            readings = self.battery_fleet.read()
            good = [r for r in readings if r.valid]
            valid = valid and bool(good)
            discharge = sum(r.discharge_w for r in good)
            ready = any(r.discharge_available_w > 0 for r in good) if good else False
        else:
            if self.settings.get("battery_power_entity"):
                value, stamp = self._power(self.settings["battery_power_entity"])
                stamps.append(stamp)
                valid = valid and value is not None
                if value is not None:
                    discharge = max(0.0, value if self.settings["battery_sign"] == "discharge_positive" else -value)
            if self.settings.get("battery_soc_entity"):
                obj = self.hass.states.get(self.settings["battery_soc_entity"])
                soc = self._number(self.settings["battery_soc_entity"])
                # SoC may legitimately remain unchanged for a long time. Availability,
                # range and unit are checked; live battery power freshness is separate.
                valid = valid and soc is not None and 0 <= soc <= 100 and obj.attributes.get("unit_of_measurement") == "%"
                ready = soc is not None and soc >= self.settings["battery_min_soc"]
        self.pv_w, _ = self._power(self.settings.get("pv_entity"))
        return grid, bool(valid), discharge, ready, min(stamps)

    def _dedicated_meter(self, device_id):
        meter = self.configs[device_id].get("power_entity")
        reserved = {self.settings.get(k) for k in ("grid_entity", "export_entity", "pv_entity", "battery_power_entity")}
        reserved.update(c.get("power_entity") for c in self.battery_fleet.configs.values())
        if self.wallbox_settings["enabled"]:
            reserved.add(self.wallbox_settings.get("power_entity"))
        reserved.update(c.get("power_entity") for i, c in self.configs.items() if i != device_id)
        if self.dhw.configured:
            reserved.add(self.dhw.config.get("power_entity"))
        return bool(meter) and meter not in reserved

    def _reclaim_meter(self, device_id):
        """Reject explicitly estimated meters for default priority handover."""
        if not self._dedicated_meter(device_id):
            return False
        cfg=self.configs[device_id];obj=self.hass.states.get(cfg.get("power_entity"))
        attrs=obj.attributes if obj else {}
        if attrs.get("restored") or attrs.get("estimated") is True or attrs.get("is_estimated") is True:
            return False
        if any(w in str(attrs.get("friendly_name", "")).casefold() for w in ("geschat", "estimated")):
            return False
        return True  # Physical identity/overlap still requires user's mapping check.

    def _power_is_estimated(self, device_id):
        """Qualify presentation/accounting only; never alter control eligibility."""
        state = self.states.get(device_id)
        return bool(state and state.fault) or not self._reclaim_meter(device_id)

    def devices(self):
        valid_fields = {f.name for f in fields(Device)}
        result = []
        for i, c in self.configs.items():
            kwargs = {k: v for k, v in c.items() if k in valid_fields}
            c = self.priority_board.effective_config(i, c)
            kwargs["priority"] = c["priority"] if self.priority_board.active else self.priorities.get(i, c["priority"])
            if (self.planner_settings.get("adaptive_power_guard") and c.get("kind") != "number"
                    and c.get("power_entity") and self._dedicated_meter(i)):
                kwargs["nominal_w"] = self.learning.conservative_power(
                    i, c, self.planner_settings.get("adaptive_power_min_samples", 10),
                    self.planner_settings.get("adaptive_power_max_multiplier", 2.0))
            reclaim, longer, _ = reclaim_permission(c,
                before_wallbox=not follows_wallbox(c, self.others_first),
                dedicated_meter=self._reclaim_meter(i), blocked=i in self.reclaim_blocks)
            kwargs["allow_wallbox_reclaim"] = reclaim
            kwargs["priority_reclaim"] = longer
            if self.dishwasher_app.enabled(c) and self.dishwasher_app.due(c, time.time()):
                kwargs["start_delay_s"] = 0  # Only solar persistence is waived at the agreed deadline.
            result.append(Device(**kwargs))
        return result

    def _wallbox_device_constraints(self, now, reading, grid, valid, discharge):
        if not self._per_device_wallbox_enabled() or not self.wallbox_settings.get("enabled"):
            return {}, {}, set()
        lower = {i for i, cfg in self.priority_board.configs().items() if follows_wallbox(cfg, self.others_first)}
        # Explicit user boosts and hard day-minimum grid permissions remain higher
        # precedence. A Wallbox preference is never permission to override them.
        controlled = {i for i in lower if self.states[i].boost_until <= now
                      and not self.states[i].deadline_force and not self.states[i].planner_grid_force}
        owned = {i: (max(0.0, self.states[i].measured_w) if self._dedicated_meter(i) else 0.0)
                 for i in controlled if self.states[i].owned and self.states[i].on
                 and self.states[i].available and not self.states[i].fault}
        p = self.consumer_wallbox.update(
            now=now, reading=reading, grid_w=grid if valid else None,
            filtered_grid_w=self.filtered if valid else None, discharge_w=discharge,
            owned_lower=owned, has_lower=bool(controlled),
            sample_gap_s=max(30, 2*self.settings["interval_s"]))
        holds = {i: p.reason for i in controlled} if p.yield_loads else {}
        blocks = {i: p.reason for i in controlled} if p.block_starts else {}
        if self.priority_board.active:
            # The visible central order is authoritative: everything below the
            # Wallbox keeps the car's solar power. A stored permission is only
            # effective after the user also moves that device above the Wallbox.
            no_reclaim = set(lower)
        else:
            no_reclaim = set(lower)
        return holds, blocks, no_reclaim

    @staticmethod
    def _time_window_active(local_now, cfg):
        if not cfg.get("time_window_enabled", False):
            return True
        try:
            def seconds(value):
                parts = [int(x) for x in str(value).split(":")]
                if len(parts) not in (2, 3):
                    raise ValueError
                h, m = parts[0], parts[1]
                sec = parts[2] if len(parts) == 3 else 0
                if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= sec <= 59):
                    raise ValueError
                return h * 3600 + m * 60 + sec
            start, end = seconds(cfg.get("time_window_start", "00:00:00")), seconds(cfg.get("time_window_end", "23:59:00"))
            now = local_now.hour * 3600 + local_now.minute * 60 + local_now.second
            if start == end:
                return True
            return start <= now < end if start < end else now >= start or now < end
        except (TypeError, ValueError):
            return False

    @staticmethod
    def _day_window_end_seconds(local_now, cfg):
        """Seconds until a same-day window ends; None for disabled/overnight windows.

        Daily runtime targets reset at local midnight. For simple daytime windows
        (for example 11:00-18:00), the window end is an implicit latest deadline.
        Overnight windows intentionally keep the explicit daily deadline because
        their accounting spans two local dates.
        """
        if not cfg.get("time_window_enabled", False):
            return None
        try:
            def seconds(value):
                parts = [int(x) for x in str(value).split(":")]
                if len(parts) not in (2, 3):
                    raise ValueError
                h, m = parts[0], parts[1]
                sec = parts[2] if len(parts) == 3 else 0
                if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= sec <= 59):
                    raise ValueError
                return h*3600 + m*60 + sec
            start = seconds(cfg.get("time_window_start", "00:00:00"))
            end = seconds(cfg.get("time_window_end", "23:59:00"))
            if start >= end:  # 24h or overnight: explicit deadline remains authoritative.
                return None
            now = local_now.hour*3600 + local_now.minute*60 + local_now.second
            return max(0.0, end-now)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _deadline_seconds(local_now, value):
        try:
            parts = [int(x) for x in str(value).split(":")]
            if len(parts) not in (2, 3):
                return 0
            h, m = parts[0], parts[1]
            sec = parts[2] if len(parts) == 3 else 0
            if not (0 <= h <= 23 and 0 <= m <= 59 and 0 <= sec <= 59):
                return 0
            deadline = local_now.replace(hour=h, minute=m, second=sec, microsecond=0)
            return max(0.0, (deadline-local_now).total_seconds())
        except (TypeError, ValueError):
            return 0

    def _cycle_program(self, cfg):
        entity_id = cfg.get("cycle_program_entity")
        if entity_id:
            obj = self.hass.states.get(entity_id)
            if obj is not None and str(obj.state).lower() not in ("unknown", "unavailable", "none", ""):
                return str(obj.state)[:80]
        return str(cfg.get("cycle_program", "standaard") or "standaard")[:80]

    def _update_daily_runtime(self, local_now, dt):
        today = local_now.date().isoformat()
        if self.runtime_day != today:
            self.runtime_day = today
            for state in self.states.values():
                state.daily_runtime_s = 0.0
                state.daily_energy_kwh = 0.0
                state.deadline_urgent = False
                state.deadline_force = False
            if self.data_loaded:
                self.store.async_delay_save(self._snapshot, 1)
        countable = 0 < dt <= max(30, self.settings["interval_s"] * 2)
        isolated_ids = set(self.source_isolated_devices)
        for i, cfg in self.configs.items():
            state = self.states[i]
            if countable and state.on and i not in isolated_ids and (cfg.get("kind") != "dishwasher" or state.available):
                state.daily_runtime_s += dt
                # Integrate the actual dedicated device meter when available. When no
                # meter exists, measured_w is the configured/owned conservative estimate.
                # This makes kWh day goals materially better than runtime×nominal while
                # keeping the estimate explainable.
                state.daily_energy_kwh += max(0.0, float(state.measured_w or 0.0)) * dt / 3_600_000.0
                if cfg.get("cycle_learning_enabled") and cfg.get("power_entity"):
                    self.cycle_learning.observe(i, state.measured_w, dt)
            minimum = max(0.0, float(cfg.get("min_daily_runtime_s", 0) or 0))
            maximum = max(0.0, float(cfg.get("max_daily_runtime_s", 0) or 0))
            if maximum and state.daily_runtime_s >= maximum:
                state.deadline_urgent = state.deadline_force = False
                continue
            remaining = max(0.0, minimum-state.daily_runtime_s)
            until = self._deadline_seconds(local_now, cfg.get("daily_deadline", "23:59:00"))
            window_until = self._day_window_end_seconds(local_now, cfg)
            if window_until is not None:
                until = min(until, window_until)
            # Include known scheduling friction so a daily minimum does not become
            # urgent only when it is already impossible to start in time.
            off_wait = max(0.0, float(cfg.get("min_off_s", 0)) - max(0.0, time.monotonic()-state.last_off)) if not state.on else 0.0
            lead = max(0.0, float(cfg.get("start_delay_s", 0))) + off_wait
            state.deadline_urgent = remaining > 0 and until <= remaining + lead
            state.deadline_force = state.deadline_urgent and bool(cfg.get("deadline_grid_allowed", False))

    def _planner_pv_hourly(self, local_now):
        hours=max(6,int(self.planner_settings.get("horizon_h",36)))
        slot_min=max(5,int(self.planner_settings.get("slot_min",15)))
        start=local_now.replace(minute=(local_now.minute//slot_min)*slot_min,second=0,microsecond=0)
        fallback=self._legacy_planner_pv_hourly(start)
        covered=self.pv_forecast.hourly(start,hours)
        return [(covered[i] if i<len(covered) and covered[i] is not None else fallback[i])
                for i in range(hours)]

    def _legacy_planner_pv_hourly(self, local_now, hours=None):
        """Use only independently configured legacy forecasts for missing hours.

        A missing modern interval cannot be filled from its own aggregate totals
        or a weather proxy which silently substitutes zero for unknown PV.
        """
        hours=max(1,int(hours)) if hours is not None else max(6,int(self.planner_settings.get("horizon_h",36)))
        out=[None]*hours
        settings=self.forecast_settings
        if not settings.get("enabled"):
            return out
        values={}
        for key in ("current_hour", "next_hour", "remaining_today", "tomorrow"):
            eid=settings.get(key+"_entity")
            value=self._scalar(eid,{"Wh","kWh"},settings.get("stale_s",7200))
            obj=self.hass.states.get(eid) if eid else None
            values[key]=(value*(.001 if obj.attributes.get("unit_of_measurement")=="Wh" else 1.)
                         if value is not None and value>=0 else None)
        pv_seed=self.historical_seed.get("pv_profile",{})
        raw_seed=(pv_seed.get("median_normalized_pct_by_hour",{}) if isinstance(pv_seed,dict) else {})
        seed=raw_seed if isinstance(raw_seed,dict) else {}
        def weight(dt):
            raw=seed.get(str(dt.hour))
            try:value=float(raw) if not isinstance(raw,bool) else float("nan")
            except (TypeError,ValueError,OverflowError):return None
            return value if math.isfinite(value) and value>=0 else None
        instants=[datetime.fromtimestamp(local_now.timestamp()+i*3600,tz=local_now.tzinfo) for i in range(hours)]
        for dayoff,key in ((0,"remaining_today"),(1,"tomorrow")):
            energy=values[key]
            date_value=local_now.date()+timedelta(days=dayoff)
            indices=[i for i,dt in enumerate(instants) if dt.date()==date_value]
            if energy is None or not indices:
                continue
            if energy==0:
                for i in indices:out[i]=0.
                continue
            start=local_now if dayoff==0 else local_now.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=dayoff)
            end=start.replace(hour=0,minute=0,second=0,microsecond=0)+timedelta(days=1)
            count=int((end.timestamp()-start.timestamp()+3599)//3600)
            all_weights=[weight(datetime.fromtimestamp(start.timestamp()+i*3600,tz=start.tzinfo)) for i in range(count)]
            if not all_weights or any(v is None for v in all_weights) or sum(all_weights)<=0:
                continue
            total=sum(all_weights)
            for i in indices:
                w=weight(instants[i])
                if w is not None:out[i]=energy*1000*w/total
        for i,key in enumerate(("current_hour","next_hour")):
            if i<hours and values[key] is not None:
                out[i]=values[key]*1000.
        return out

    @staticmethod
    def _price_value(row):
        if isinstance(row, bool):
            return None
        if isinstance(row, (int, float)):
            try:
                value = float(row)
                return value if math.isfinite(value) else None
            except (ValueError, OverflowError):
                return None
        if isinstance(row, dict):
            for key in ("price", "value", "total", "energy_price", "marketprice"):
                if key in row:
                    try:
                        if isinstance(row[key], bool):
                            return None
                        value = float(row[key])
                        return value if math.isfinite(value) else None
                    except (TypeError, ValueError, OverflowError):
                        pass
        return None

    @staticmethod
    def _price_timestamp(row, tzinfo):
        if not isinstance(row, dict):
            return None
        for key in ("start", "start_time", "datetime", "time", "timestamp", "date"):
            raw = row.get(key)
            if raw is None:
                continue
            try:
                if isinstance(raw, (int, float)):
                    dt = datetime.fromtimestamp(float(raw), tz=timezone.utc)
                else:
                    text = str(raw).strip().replace("Z", "+00:00")
                    dt = datetime.fromisoformat(text)
                    if dt.tzinfo is None:
                        dt = dt.replace(tzinfo=tzinfo)
                return dt.astimezone(tzinfo) if tzinfo else dt
            except (TypeError, ValueError, OverflowError, OSError):
                continue
        return None

    def _planner_prices(self, slots, local_now):
        """Return timestamp-aligned price arrays with a safe fixed-price fallback.

        Supports common HA price attributes (today/tomorrow/raw_today/raw_tomorrow/
        prices) as timestamped dicts or regular 24/48/96-point arrays. A malformed
        or stale price source never blocks planning; the configured fixed price wins.
        """
        imp, exp = self._economy_prices()
        imp = float(self.economy_settings.get("fixed_import_eur_kwh", .30)) if imp is None else float(imp)
        exp = float(self.economy_settings.get("fixed_export_eur_kwh", .03)) if exp is None else float(exp)
        imports, exports = [imp] * slots, [exp] * slots
        slot_min = max(5, int(self.planner_settings.get("slot_min", 15)))
        minute = (local_now.minute // slot_min) * slot_min
        plan_start = local_now.replace(minute=minute, second=0, microsecond=0)
        starts = [datetime.fromtimestamp(plan_start.timestamp()+i*slot_min*60,tz=plan_start.tzinfo)
                  for i in range(slots)]

        def parse(entity_id, fallback):
            obj = self.hass.states.get(entity_id) if entity_id else None
            if obj is None:
                return None, "vaste prijs"
            attrs = obj.attributes
            report = self._reported_wall(obj)
            dynamic = any(isinstance(attrs.get(key), (list, dict)) for key in (
                "raw_today", "today", "raw_tomorrow", "tomorrow", "prices"))
            if (report is None or obj.state in ("unknown", "unavailable", "")
                    or (dynamic and time.time() - report > 36 * 3600)):
                return [fallback] * slots, "vaste prijs"
            tzinfo = local_now.tzinfo
            timestamped = []
            simple_by_day = {}
            generic_simple = []
            for key in ("raw_today", "today", "raw_tomorrow", "tomorrow", "prices"):
                rows = attrs.get(key)
                if isinstance(rows, dict):
                    # Some integrations expose {timestamp: price}.
                    rows = [{"start": k, "value": v} for k, v in rows.items()]
                if not isinstance(rows, list) or not rows:
                    continue
                has_ts = any(isinstance(row, dict) and any(key in row for key in (
                    "start", "start_time", "datetime", "time", "timestamp", "date")) for row in rows)
                for row in rows:
                    value = self._price_value(row)
                    stamp = self._price_timestamp(row, tzinfo)
                    if stamp is not None:
                        end = None
                        if isinstance(row, dict):
                            end = self._price_timestamp({"start": row.get("end", row.get("end_time"))}, tzinfo)
                            if end is not None and end.timestamp() <= stamp.timestamp():
                                end = stamp  # Explicit invalid duration has no coverage.
                        timestamped.append((stamp, value, end)); has_ts = True
                if has_ts:
                    continue
                vals = [self._price_value(row) for row in rows]
                if not vals or not any(v is not None for v in vals):
                    continue
                if "tomorrow" in key:
                    simple_by_day[1] = vals
                elif key in ("today", "raw_today"):
                    simple_by_day[0] = vals
                else:
                    generic_simple = vals

            if timestamped:
                timestamped.sort(key=lambda x: x[0].timestamp())
                steps = [b[0].timestamp()-a[0].timestamp() for a,b in zip(timestamped,timestamped[1:])
                         if b[0].timestamp()>a[0].timestamp()]
                last_duration = min(3600, min(steps)) if steps else slot_min * 60
                result = []
                for start_dt in starts:
                    candidates = [(i,x) for i,x in enumerate(timestamped) if x[0].timestamp()<=start_dt.timestamp()]
                    if candidates:
                        index, row = candidates[-1]
                        end = (row[2].timestamp() if row[2] is not None else
                               timestamped[index+1][0].timestamp() if index+1<len(timestamped)
                               else row[0].timestamp()+last_duration)
                        result.append(row[1] if start_dt.timestamp()<end and row[1] is not None else fallback)
                    else:
                        result.append(fallback)
                return result, "tijdgestempelde prijsreeks"

            if simple_by_day:
                result = []
                today = local_now.date()
                for start_dt in starts:
                    dayoff = (start_dt.date() - today).days
                    vals = simple_by_day.get(dayoff)
                    if not vals:
                        result.append(fallback); continue
                    midnight=start_dt.replace(hour=0,minute=0,second=0,microsecond=0)
                    day_s=(midnight+timedelta(days=1)).timestamp()-midnight.timestamp()
                    cadence=day_s/len(vals)
                    if day_s!=86400 and cadence not in (900,1800,3600):
                        result.append(fallback);continue  # Ambiguous DST array: require real time positions.
                    idx=min(len(vals)-1,max(0,int((start_dt.timestamp()-midnight.timestamp())//cadence)))
                    result.append(vals[idx] if vals[idx] is not None else fallback)
                return result, "dagprijsreeks"

            if generic_simple:
                # Last-resort generic array. 24/48/96 entries are treated as a
                # day profile; other lengths are sequential from now.
                result = []
                if len(generic_simple) in (24, 48, 96):
                    cadence = 1440.0 / len(generic_simple)
                    for start_dt in starts:
                        midnight=start_dt.replace(hour=0,minute=0,second=0,microsecond=0)
                        if (midnight+timedelta(days=1)).timestamp()-midnight.timestamp()!=86400:
                            result.append(fallback);continue
                        idx = min(len(generic_simple) - 1, int((start_dt.hour * 60 + start_dt.minute) // cadence))
                        result.append(generic_simple[idx] if generic_simple[idx] is not None else fallback)
                else:
                    for i in range(slots):
                        idx = int(i * slot_min / 60)
                        result.append(generic_simple[idx] if idx<len(generic_simple) and generic_simple[idx] is not None else fallback)
                return result, "generieke prijsreeks"
            return ([fallback] * slots if dynamic else None), "vaste prijs"

        dyn, import_source = parse(self.economy_settings.get("import_price_entity"), float(self.economy_settings.get("fixed_import_eur_kwh", .30)))
        if dyn:
            imports = dyn
        dyn, export_source = parse(self.economy_settings.get("export_price_entity"), float(self.economy_settings.get("fixed_export_eur_kwh", .03)))
        if dyn:
            exports = dyn
        self.planner_price_sources = {"import": import_source, "export": export_source}
        return imports, exports

    def _update_planner(self, local_now, now):
        if not self.planner_settings.get("enabled",True):
            for state in self.states.values(): state.planner_hold=False; state.planner_grid_force=False
            return
        # A reliable measured decomposition remains useful during EV/own loads.
        # Unavailable/estimated/duplicate sources stay unknown, not fake zeroes.
        try:
            learning_sample = self.learning_hub.observe(local_now, now)
        except Exception as err:
            self.learning_hub.error = "Basislastanalyse overgeslagen: " + type(err).__name__
            learning_sample = {"valid": False, "watts": None, "context": "unknown"}
            # Failing an advisory observation is not a reason to interrupt a
            # protected cycle or change the runtime mode. Real meter guards stay.
            _LOGGER.warning("SolarPilot basislastanalyse overgeslagen: %s", type(err).__name__)
        if self.unified_planner.due(time.time()):
            slot_min=max(5,int(self.planner_settings.get("slot_min",15))); horizon=max(6,int(self.planner_settings.get("horizon_h",36))); n=max(1,int(horizon*60/slot_min))
            pv_hourly=self._planner_pv_hourly(local_now); prices_in,prices_out=self._planner_prices(n, local_now)
            effective={d.id:d for d in self.devices()}; devs=[]
            for i,cfg in self.configs.items():
                st=self.states[i]; p=effective.get(i).nominal_w if i in effective else float(cfg.get("nominal_w",0) or 0)
                runtime_goal=max(0.0,float(cfg.get("min_daily_runtime_s",0) or 0))*p/3_600_000
                energy_goal=max(0.0,float(cfg.get("daily_energy_goal_kwh",0) or 0))
                delivered=max(0.0,float(st.daily_energy_kwh))
                # Backward-compatible fallback for installations upgraded before daily
                # energy integration existed. The live counter takes over immediately.
                if delivered <= 0 and st.daily_runtime_s > 0:
                    delivered=max(0.0,float(st.daily_runtime_s))*p/3_600_000
                required=max(0.0,max(runtime_goal,energy_goal)-delivered)
                program=self._cycle_program(cfg)
                cycle=self.cycle_learning.estimate(i, program,
                    fallback_energy_kwh=cfg.get("cycle_energy_kwh",0),
                    fallback_duration_min=cfg.get("cycle_duration_min",0),
                    fallback_peak_w=max(p,float(cfg.get("nominal_w",0) or 0)))
                # A protected cycle must be planned as one block whether its
                # profile is learned or manually configured. The learning toggle
                # controls only observation, not the safety semantics of a
                # non-interruptible device.
                cycle_ready=bool(cfg.get("non_interruptible") and st.demand and st.interlock and st.cycle_armed and not st.on)
                if cycle_ready and cycle.energy_kwh>0:
                    required=max(required,cycle.energy_kwh)
                active_cycle=bool(cfg.get("non_interruptible") and st.on)
                elapsed_min=max(0.0,(now-st.last_on)/60.0) if active_cycle and st.last_on else 0.0
                remaining_min=max(0.0,cycle.duration_min-elapsed_min) if cycle.duration_min>0 else 0.0
                active_avg=max(1.0,cycle.average_w or st.measured_w or p) if active_cycle else 0.0
                devs.append({**cfg,"priority": effective[i].priority if self.priority_board.active else cfg.get("priority",50),"power_w":p,"required_kwh":required,
                    "enabled":self.device_modes.get(i,"auto")!="disabled" and st.available and st.demand and st.interlock and not bool(st.fault),
                    "contiguous_cycle":cycle_ready,
                    "cycle_program":cycle.program,"cycle_energy_kwh":cycle.energy_kwh,
                    "cycle_duration_min":cycle.duration_min,"cycle_peak_w":cycle.peak_w,
                    "cycle_average_w":cycle.average_w,"cycle_confidence":cycle.confidence,
                    "fixed_active_cycle":active_cycle,"active_cycle_remaining_min":remaining_min,
                    "active_cycle_average_w":active_avg})
            capacity_target=self.capacity.effective_target_w if self.capacity_settings.get("enabled") and self.capacity.valid else None
            batt=None
            agg=self.battery_fleet.overview().get("aggregate",{}) if self.battery_fleet.settings.get("enabled") else {}
            if agg.get("capacity_kwh") and agg.get("soc_pct") is not None:
                batt={"available_kwh":agg.get("capacity_kwh"),"soc_pct":agg.get("soc_pct"),"power_w":min(float(agg.get("charge_headroom_w") or 0),5000) or 3000,"min_soc_pct":20,"max_soc_pct":95}
            self.unified_plan=self.unified_planner.build(local_now=local_now,pv_hourly_w=pv_hourly,import_prices=prices_in,export_prices=prices_out,devices=devs,capacity_target_w=capacity_target,battery=batt)
        plan=self.unified_plan
        for i,cfg in self.configs.items():
            st=self.states[i]
            has_goal = (float(cfg.get("min_daily_runtime_s", 0) or 0) > 0
                        or float(cfg.get("daily_energy_goal_kwh", 0) or 0) > 0
                        or cfg.get("non_interruptible", False))
            if not cfg.get("forecast_deferrable",False) or plan is None or not has_goal:
                st.planner_hold=False; st.planner_grid_force=False; st.planner_reason="Niet door rolling planner uitgesteld"; continue
            run,grid,reason=plan.current_device_state(i,local_now)
            # Planning can only hold a new optional start. It never stops a running load or overrides urgent/manual behaviour.
            st.planner_hold=bool(not run and not st.on and not st.deadline_urgent and st.boost_until<=now)
            st.planner_grid_force=bool(run and grid and cfg.get("cheap_grid_allowed") and cfg.get("deadline_grid_allowed"))
            st.planner_reason=reason

        # Score the plan against reality and feed a bounded 15-minute what-if replay.
        if self.grid_w is not None and self.pv_w is not None:
            actual_base = learning_sample["watts"] if learning_sample["valid"] else None
            planned_ids=set()
            current=self.unified_planner.current_slot(local_now)
            if current: planned_ids=set(current.devices)
            considered=[i for i,cfg in self.configs.items() if cfg.get("forecast_deferrable") and self.device_modes.get(i,"auto")!="disabled"]
            matches=sum(1 for i in considered if ((i in planned_ids) == bool(self.states[i].on)))
            imp_price,exp_price=self._economy_prices()
            cap_target=self.capacity.effective_target_w if self.capacity_settings.get("enabled") and self.capacity.valid else None
            self.unified_planner.observe_actual(wall_ts=time.time(),local_now=local_now,actual_pv_w=self.pv_w,actual_base_w=actual_base,
                actual_grid_w=self.grid_w,import_price=imp_price if imp_price is not None else self.economy_settings.get("fixed_import_eur_kwh",.30),
                export_price=exp_price if exp_price is not None else self.economy_settings.get("fixed_export_eur_kwh",.03),
                capacity_target_w=cap_target,execution_total=len(considered),execution_matches=matches,context=learning_sample.get("context", "normal"))

    async def async_set_planner_setting(self, key, value):
        if key not in PLANNER_SETTING_SPECS:
            raise HomeAssistantError("Onbekende plannerinstelling")
        spec=PLANNER_SETTING_SPECS[key]
        if spec.get("type")=="boolean":
            if isinstance(value,str):
                text=value.strip().casefold()
                if text in ("true","1","yes","on","aan"):value=True
                elif text in ("false","0","no","off","uit"):value=False
                else:raise HomeAssistantError("Ongeldige aan/uit-keuze")
            elif not isinstance(value,bool):
                if isinstance(value,(int,float)) and value in (0,1):value=bool(value)
                else:raise HomeAssistantError("Ongeldige aan/uit-keuze")
        elif spec.get("type")=="number":
            if isinstance(value,bool):raise HomeAssistantError("Ongeldige numerieke waarde")
            try:value=float(value)
            except (TypeError,ValueError,OverflowError):raise HomeAssistantError("Ongeldige numerieke waarde")
            if not math.isfinite(value):raise HomeAssistantError("Ongeldige numerieke waarde")
            if value<float(spec.get("min",value)) or value>float(spec.get("max",value)):
                raise HomeAssistantError("Waarde buiten toegestane grens")
            if key in ("horizon_h","slot_min","replan_min","base_load_min_days","quality_retention_days","replay_retention_days"): value=int(round(value))
        self.planner_settings={**self.planner_settings,key:value}
        self.unified_planner.settings={**self.unified_planner.settings,key:value}
        if key=="quality_retention_days": self.unified_planner.quality.retention_days=int(value)
        if key=="replay_retention_days": self.unified_planner.replay.retention_days=int(value)
        self.unified_plan=None; self.unified_planner.plan=None; self.unified_planner.last_plan_wall=0
        opts=dict(self.entry.options); opts["planner"]={**opts.get("planner",{}),key:value}
        ce=getattr(self.hass,"config_entries",None)
        if ce is not None and hasattr(ce,"async_update_entry"):
            self._skip_options_reload_once=True; ce.async_update_entry(self.entry,options=opts)
        else:self.entry.options=opts
        self.store.async_delay_save(self._snapshot,1)
        self.note(f"Plannerinstelling '{spec['label']}' gewijzigd naar {value}.")
        self.publish(); return value

    def _target_matches(self, cfg, watts):
        active = self._active(cfg)
        if watts == 0:
            return active is False
        if active is not True:
            return False
        if cfg["kind"] == "number":
            actual = self._number(cfg.get("number_entity"))
            expected = watts / cfg["watts_per_unit"]
            return actual is not None and abs(actual - expected) <= max(0.01, cfg["step_units"] / 4)
        return True

    async def _confirm_pending(self, now):
        if not self.pending:
            return
        p = self.pending
        i = p["id"]
        cfg, s = self.configs[i], self.states[i]
        matches = self._target_matches(cfg, p["watts"])
        if cfg.get("kind") == "dishwasher":
            reading = read_dishwasher(self.hass, cfg)
            if self.dishwasher_app.enabled(cfg):
                reported_running = self.dishwasher_app.data.get(i, {}).get("running_report", 0)
                live_running = reading.raw == "Running" and reading.stamp > p.get("issued_wall", float("inf"))
                matches = live_running or reported_running > p.get("issued_wall", float("inf"))
            else:
                matches = matches and reading.stamp > p.get("issued_wall", float("inf"))
        if matches:
            self.consumer_history.confirm(i)
            if cfg.get("kind") == "dishwasher":
                self.dishwasher.confirmed(i)
            if p["watts"] == 0:
                s.owned = False
                s.target_w = 0
                s.last_off = now
                s.boost_until = 0
                s.manual_forced = False
                s.manual_stop_requested = False
                if p.get("max_runtime"):
                    self.faults[i] = "Maximale looptijd bereikt: controleer en wis de melding"
            else:
                s.owned = True
                s.target_w = p["watts"]
            self.pending = None
            s.stop_since = None
            self.note(f'{cfg["name"]}: opdracht bevestigd ({p["watts"]:.0f} W).')
            await self.store.async_save(self._snapshot())
        elif now - p["issued"] >= cfg["ack_timeout_s"]:
            self.faults[i] = "Geen opdrachtbevestiging: handmatige controle nodig"
            self.consumer_history.failure(i, self.faults[i])
            self.pending = None
            self.note(f'{cfg["name"]}: bevestiging ontbreekt. Nieuwe starts geblokkeerd.')
            await self.notify(f'{cfg["name"]}: een opdracht werd niet bevestigd. Controleer de fysieke toestand en de gekoppelde entiteiten. SolarPilot neemt niet aan dat het toestel geschakeld is.')

    def _observe(self, now, local_now=None):
        changed = False
        for i, cfg in self.configs.items():
            s = self.states[i]
            if i in self.recovery:
                # The durable lease has not yet been reconciled. Do not let a
                # restored/default state masquerade as OFF or consume a ticket.
                s.available = False
                s.enabled = self.device_modes.get(i, "disabled") == "auto"
                s.start_since = None
                s.fault = self.faults.get(i, "")
                continue
            active = self._active(cfg)
            previous_on = s.on
            was_available = s.available
            is_pending = self.pending is not None and self.pending["id"] == i
            s.available = active is not None
            s.enabled = self.device_modes.get(i, "disabled") == "auto"
            condition_ok = self._bool(cfg.get("condition_entity")) is True
            window_ok = self._time_window_active(local_now, cfg) if local_now is not None else True
            s.demand = condition_ok and window_ok
            if cfg.get("kind") == "dishwasher":
                reading = self.dishwasher.readings[i]
                self.dishwasher_app.prepare(cfg, reading, time.time())
                permit, _ = self.dishwasher.permitted(cfg, reading, time.time())
                s.cycle_armed = bool(self.dishwasher.tickets.get(i, {}).get("armed"))
                s.demand = s.demand and (active is True or permit)
            s.interlock = self._bool(cfg.get("interlock_entity")) is True
            s.fault = self.faults.get(i, "")
            if cfg["kind"] == "number":
                number = self._number(cfg.get("number_entity"))
                obj = self.hass.states.get(cfg.get("number_entity"))
                s.available = s.available and number is not None and obj is not None
                if obj is not None:
                    unit = obj.attributes.get("unit_of_measurement")
                    if cfg.get("control_unit") and unit != cfg["control_unit"]:
                        s.fault = s.fault or "Eenheid van vermogensregelaar is gewijzigd"
                    try:
                        allowed = float(obj.attributes["min"]) <= cfg["min_units"] <= cfg["max_units"] <= float(obj.attributes["max"])
                    except (KeyError, TypeError, ValueError):
                        allowed = False
                    if not allowed:
                        s.fault = s.fault or "Bereik van vermogensregelaar is gewijzigd"
            had_observation = getattr(s, "observed_once", False)
            if active is not None:
                s.on = active
                if active and s.owned and not was_available and previous_on:
                    # During a lost status interval the compressor may have
                    # cycled. Protect one full minimum run from its return.
                    s.last_on = now
                if previous_on != active:
                    if active:
                        s.last_on = now
                        if had_observation and cfg.get("kind") != "dishwasher" and cfg.get("cycle_learning_enabled") and cfg.get("power_entity"):
                            self.cycle_learning.begin(i, self._cycle_program(cfg), time.time(), (local_now or datetime.now().astimezone()).date().isoformat())
                    else:
                        s.last_off = now
                        s.manual_forced = False
                        s.manual_stop_requested = False
                        if had_observation and cfg.get("kind") != "dishwasher" and cfg.get("cycle_learning_enabled") and cfg.get("power_entity"):
                            finished = cfg.get("kind") != "dishwasher" or self.dishwasher.readings[i].finished
                            learned = self.cycle_learning.finish(i, time.time()) if finished else None
                            if not finished:
                                self.cycle_learning.active.pop(i, None)
                            if learned:
                                self.note(f'{cfg["name"]}: volledige cyclus geleerd ({learned["energy_kwh"]:.2f} kWh, {learned["duration_min"]:.0f} min).')
                                changed = True
                s.observed_once = True
            # Never adopt an external start. Relinquish a mismatching owned setting.
            # A latched ambiguous command is retained until verified off/reset.
            if s.owned and not is_pending and not self.faults.get(i) and active is not None and not self._target_matches(cfg, s.target_w):
                s.owned = False
                s.target_w = 0
                s.boost_until = 0
                s.manual_until = now + cfg["manual_hold_s"]
                self.note(f'{cfg["name"]}: extern gewijzigd of taak voltooid; regeling laat dit toestel met rust.')
                changed = True
            if cfg["non_interruptible"] and cfg.get("kind") != "dishwasher" and not s.owned and active is False and not s.demand and not s.cycle_armed:
                s.cycle_armed = True
                changed = True
            if cfg.get("power_entity"):
                if not self._dedicated_meter(i):
                    s.fault = s.fault or "Vermogensmeter is niet exclusief voor dit toestel"
                watts, _ = self._power(cfg["power_entity"])
                if watts is None or watts < -1:
                    s.fault = s.fault or "Vermogensmeting onbetrouwbaar"
                    # Conservative reservation, not a claim of measured power.
                    s.measured_w = max(s.target_w, cfg["nominal_w"]) if s.on else 0
                else:
                    s.measured_w = max(0.0, watts) if s.on else 0.0
            else:
                s.measured_w = (s.target_w if s.owned and s.target_w else cfg["nominal_w"]) if s.on else 0.0
            # Record observed state, not allocated watts or an unconfirmed request.
            # This read-only path also includes external/manual activity in Observatie.
            completion = self.dishwasher_app.data.get(i, {}).get("end_pending") if cfg.get("kind") == "dishwasher" else None
            observed_time = datetime.fromtimestamp(completion["ended_at"], timezone.utc) if completion else (local_now or datetime.now(timezone.utc))
            self.consumer_history.observe(i, active, observed_time)
            if cfg.get("kind") == "dishwasher":
                measured, _ = self._power(cfg.get("power_entity"))
                if not self._dedicated_meter(i):
                    measured = None
                ticket_before = dict(self.dishwasher.tickets.get(i, {}))
                learned = self.dishwasher.observe(cfg, self.dishwasher.readings[i], measured, observed_time.timestamp(),
                                        max(30, self.settings["interval_s"] * 2))
                if completion:
                    self.dishwasher_app.data[i].pop("end_pending", None)
                    changed = True
                if ticket_before != self.dishwasher.tickets.get(i, {}):
                    changed = True
                if learned and cfg.get("cycle_learning_enabled"):
                    program = learned["program"]
                    cycles = self.cycle_learning.profiles.setdefault(i, {}).setdefault(program, [])
                    cycles.append({"day": (local_now or datetime.now().astimezone()).date().isoformat(),
                                   "energy_kwh": learned["energy_kwh"], "duration_min": learned["duration_s"]/60,
                                   "peak_w": max(x["peak_w"] for x in learned["stages"].values())})
                    del cycles[:-24]
                    self.cycle_learning.accepted += 1
                    self.note(f'{cfg["name"]}: complete afwascyclus met exclusieve vermogensmeter geleerd.')
                    changed = True
        if changed:
            self.store.async_delay_save(self._snapshot, 1)

    async def tick(self, _now=None):
        if self._closed or self._lock.locked():
            return
        async with self._lock:
            started = perf_counter()
            try:
                await self._tick()
            except Exception:
                _LOGGER.exception("SolarPilot regelcyclus gestopt door fout")
                self.problem = "Interne fout: regeling gepauzeerd; controleer het Home Assistant-logboek"
                self.problem_kind = "internal_fault"
                self.mode = "paused"
                self.restart_requested_mode = None
                try:
                    self.dhw.diagnose_runtime_block(time.monotonic(), None, False, 0,
                        code="internal_fault", reason=self.problem)
                except Exception:
                    # Diagnostics must never hide the original controller fault.
                    _LOGGER.debug("Warmwaterdiagnose na regelcyclusfout niet beschikbaar", exc_info=True)
            try:
                await self.learning_hub.tick()
            except Exception as err:
                # An advisory inbox failure must never halt the existing EMS.
                self.learning_hub.error = "Leeranalyse onvolledig: " + type(err).__name__
                _LOGGER.warning("SolarPilot leeranalyse overgeslagen: %s", type(err).__name__)
            try:
                self.analysis.capture((perf_counter()-started)*1000)
            except Exception as err:
                self.analysis.error = "Analysemeting onvolledig: " + type(err).__name__
            self.publish()

    async def _tick(self):
        now = time.monotonic()
        dt = max(0.0, now - self.last_tick)
        self.last_tick = now
        await self._confirm_pending(now)
        await self._retry_restart_recovery(now)
        zone = getattr(getattr(self.hass, "config", None), "time_zone", "Europe/Brussels")
        try:
            from zoneinfo import ZoneInfo
            local_now = datetime.now(ZoneInfo(zone))
        except Exception:
            local_now = datetime.now().astimezone()
        self._observe(now, local_now)
        try:
            await self.live_options.process_pending()
        except Exception as err:
            # A pending configuration/virtual-entity failure is not a reason to
            # stop unrelated, already verified controllers.
            message = "Wachtende configuratie niet toegepast: " + type(err).__name__
            if self.live_options.error != message:
                self.live_options.error = message
                self.note(message)
                _LOGGER.exception("SolarPilot wachtende configuratie vereist controle")
        grid, valid, discharge, ready, reported = self._site_data()
        self.grid_w = grid
        self._local_pv_update(local_now)
        self._update_daily_runtime(local_now, dt)
        self._update_planner(local_now, now)
        for i, cfg in self.configs.items():
            if self.dishwasher_app.enabled(cfg):
                st = self.states[i]
                st.deadline_force = self.dishwasher_app.due(cfg, time.time()) and not st.on
                st.deadline_urgent = st.deadline_force
                # APP requests have their own START deadline, not a daily-runtime target.
                st.planner_hold = st.planner_grid_force = False
        avg_w, _ = self._power(self.capacity_settings.get("average_demand_entity"), self.capacity_settings["stale_s"])
        month_w, _ = self._power(self.capacity_settings.get("monthly_peak_entity"), max(self.capacity_settings["stale_s"], 3600))
        self.capacity = capacity_decision(local_now, avg_w, month_w, grid if valid else None, self.capacity_settings)
        phase_values = []
        if self.phase_settings["enabled"]:
            for key in ("phase_1_entity", "phase_2_entity", "phase_3_entity"):
                value, _ = self._power(self.phase_settings.get(key), self.phase_settings["stale_s"])
                phase_values.append(value)
        else:
            phase_values = [None, None, None]
        self.phase = phase_decision(tuple(phase_values), self.phase_settings)
        if self.phase_settings.get("enabled") and self.phase_settings.get("learning_enabled", True):
            device_powers = {}
            all_phase_configs = {**self.configs, **self._phase_monitor_configs()}
            for device_id, cfg in all_phase_configs.items():
                if cfg.get("power_entity"):
                    watts, _ = self._power(cfg.get("power_entity"), self.phase_settings.get("stale_s", 120))
                    if watts is not None:
                        device_powers[device_id] = max(0.0, watts)
            self.phase_learning.observe(now=now, day=local_now.date().isoformat(),
                                        phase_values=tuple(phase_values), device_powers=device_powers)
        if valid:
            # Fresh-start the filter after command settling to avoid load-change
            # transients being interpreted as additional photovoltaic production.
            if self.filtered is None or self.last_issued > now - self.settings["settle_s"]:
                self.filtered = grid
            else:
                alpha = 1 - math.exp(-dt / max(1.0, self.settings["filter_s"]))
                self.filtered += alpha * (grid - self.filtered)
            self.invalid_since = None
        elif self.invalid_since is None:
            self.invalid_since = now
        isolated = self.source_isolated_devices
        isolated_ids = set(isolated)
        isolated_reserve = sum(info["reserve_w"] for info in isolated.values())
        ambiguous = bool(self.faults)
        can_increase = (not self.pending and not self.battery_fleet.busy and not self.restart_blocking and not ambiguous
                        and now - self.last_issued >= self.settings["settle_s"]
                        and reported > self.last_issued_wall)
        profile = self.wallbox_profile.update()
        self.consumer_wallbox.settings["priority_min_power_w"] = (
            profile["minimum_power_w"] if self.wallbox_settings.get("minimum_from_profile")
            else self.wallbox_settings["priority_min_power_w"])
        self.consumer_wallbox.settings["priority_max_power_w"] = (
            profile["maximum_power_w"] if profile["current_source"] == "Wallbox-integratie" else None)
        previous_wb_state = self.wallbox_guard.result.state
        wallbox_reading = self._wallbox_reading()
        self._observe_wallbox_activity(wallbox_reading, grid if valid else None, discharge)
        if wallbox_reading.valid:
            self.learning.observe_report(wallbox_reading.stamp)
        self.wallbox_guard.settings["stable_s"] = self.learning.effective_stable_s(self.wallbox_settings["stable_s"])
        wb = self.wallbox_guard.update(now, wallbox_reading,
                                       grid if valid else None,
                                       self.settings["reserve_w"], discharge)
        if wb.state != previous_wb_state and wb.state in ("waiting", "cooldown", "unavailable", "idle", "charging"):
            self.note(f'Wallbox-monitor: {wb.reason}.')
        await self._advance_handover(now, wallbox_reading, grid if valid else None, reported, discharge, ready)
        wb = self.wallbox_guard.result
        if self._yield_to_wallbox:
            if not any(s.owned for s in self.states.values()) and not self.pending:
                self._yield_to_wallbox = False
                self.wallbox_guard.note_action(now, time.time(), 0, 0)
            wb = replace(wb, block_increase=True, release_flexible=True, max_increase_w=0,
                         reason="Voorrang gewijzigd: eigen lasten veilig vrijgeven voor Wallbox")
            self.wallbox_guard.result = wb
        device_holds, device_start_blocks, subordinate_ids = self._wallbox_device_constraints(now, wallbox_reading, grid, valid, discharge)
        wallbox_start_blocks = dict(device_start_blocks)
        priority = self._update_dishwasher_priority(now, local_now, grid, valid, discharge, ready, wallbox_reading)
        device_holds.update(priority.holds)
        runtime_start_blocks = dict(priority.blocks)
        device_start_blocks.update(runtime_start_blocks)
        for device_id, message in self.dishwasher_priority.observe(wall=time.time(),
                readings=self.dishwasher.readings, grid_w=grid if valid else None,
                grid_stamp=reported, wb=wallbox_reading):
            self.note(self.configs[device_id]["name"]+": "+message)
            await self.notify(message)
            self.store.async_delay_save(self._snapshot, 1)
        dhw_dispatch_blocks = [
            (bool(self.pending), "load_confirmation", "Wacht op bevestiging van een eerdere toestelopdracht"),
            (bool(self.handover), "power_transfer", "Wacht tot de verdeling van zonnestroom is afgerond"),
            (self.smart_climate.busy, "climate_confirmation", "Wacht op bevestiging van de ruimteregeling"),
            (self.battery_fleet.busy, "battery_confirmation", "Wacht op bevestiging van de batterijregeling"),
            (now - self.last_issued < self.settings["settle_s"], "settling",
             f"Wacht nog {max(0, math.ceil(self.settings['settle_s'] - (now - self.last_issued)))} s op stabiele metingen na de laatste opdracht"),
        ]
        dhw_block = next(((code, reason) for blocked, code, reason in dhw_dispatch_blocks if blocked), ("", ""))
        dhw_sent = await self.dhw.tick(now, grid, valid, discharge,
            allow_command=not bool(dhw_block[0]), local_now=local_now,
            dispatch_block_code=dhw_block[0], dispatch_block_reason=dhw_block[1])
        extra_reclaim = None
        wash_due = any(self.dishwasher_app.due(cfg, time.time()) and not self.states[i].on
                       for i, cfg in self.configs.items())
        if (can_increase and valid and ready and not dhw_sent and not self.dhw.pending
                and not self.smart_climate.busy and not self.handover and not wash_due):
            allowed, _reason = self.heat_pump_increase_allowed(check_capacity=False)
            if allowed:
                extra_reclaim = self.priority_board.extra_reclaim_action(now, local_now)
        extra_start_blocks = self.priority_board.extra_start_blocks(now)
        runtime_start_blocks.update(extra_start_blocks)
        device_start_blocks.update(extra_start_blocks)
        climate_dispatch_blocks = [
            (self.mode != "solar", "operating_mode", "Automatisch regelen staat niet aan"),
            (bool(self.pending), "load_confirmation", "Wacht op bevestiging van een eerdere toestelopdracht"),
            (bool(self.handover), "power_transfer", "Wacht tot de verdeling van zonnestroom is afgerond"),
            (self.battery_fleet.busy, "battery_confirmation", "Wacht op bevestiging van de batterijregeling"),
            (bool(dhw_sent), "dhw_issued", "Warm water kreeg zojuist een opdracht; ruimtebediening wacht"),
            (bool(extra_reclaim), "dhw_reclaim", "Een onderbreekbaar toestel maakt eerst zonnestroom vrij voor extra warm water"),
            (bool(self.dhw.pending), "dhw_confirmation", "Wacht op bevestiging van het warmwaterdoel"),
            (self.dhw.blocks_increase, "dhw_review", "Warmwaterregeling vraagt eerst controle"),
            (self.dhw.reading.protected, "dhw_protection", self.dhw.status or "Beschermde warmwaterfunctie actief; ruimtebediening wacht"),
            (self.restart_blocking, "restart_recovery", "Wacht op afronding van de herstartcontrole"),
        ]
        climate_block = next(((code, reason) for blocked, code, reason in climate_dispatch_blocks if blocked), ("", ""))
        climate_sent = await self.smart_climate.tick(
            local_now=local_now, allow_command=not bool(climate_block[0]),
            dispatch_block_code=climate_block[0], dispatch_block_reason=climate_block[1])
        if ((self.removal_requested or self.mode == "paused") and not climate_sent and not dhw_sent and not self.pending
                and not self.handover and not self.dhw.busy and not self.battery_fleet.busy):
            climate_sent = await self.smart_climate.prepare_for_removal()
        use_phase_map = bool(self.phase_settings.get("use_learned_device_map", False))
        phase_global_block = self.phase.block_increase and (not use_phase_map or not self.phase.valid)
        non_ev_can_increase = can_increase
        can_increase = (can_increase and not wb.block_increase and not phase_global_block and not self.handover
                        and not dhw_sent and not climate_sent and not self.smart_climate.busy and not self.dhw.blocks_increase)
        transfer = self.handover
        waiting = transfer is not None and transfer.status == "waiting"
        rollback = transfer is not None and transfer.status == "rollback"
        effective_mode = "paused" if self.restart_blocking else self.mode
        capacity_limit = self.settings["max_import_w"]
        if self.capacity_settings["enabled"]:
            if not self.capacity.valid:
                capacity_limit = 0.0
            elif self.capacity.allowed_grid_w is not None:
                capacity_limit = min(capacity_limit, self.capacity.allowed_grid_w)
            else:
                capacity_limit = min(capacity_limit, self.capacity.effective_target_w or capacity_limit)
        phase_max_increase = (self.phase.headroom_w if self.phase_settings.get("control_starts") and self.phase.enabled and not use_phase_map else None)
        phase_device_limits = self._phase_device_limits() if use_phase_map else {}
        if isolated_reserve:
            # An unobserved load can return at its maximum on any phase. Global
            # P1 headroom alone does not protect an individual phase boundary.
            if phase_max_increase is not None:
                phase_max_increase = max(0.0, phase_max_increase - isolated_reserve)
            phase_device_limits = {i: max(0.0, limit - isolated_reserve)
                                   for i, limit in phase_device_limits.items()}
        max_increase = wb.max_increase_w
        if phase_max_increase is not None:
            max_increase = phase_max_increase if max_increase is None else min(max_increase, phase_max_increase)
        external_hold = wb.release_flexible or self.phase.release_flexible
        external_reason = self.phase.reason if self.phase.release_flexible else wb.reason
        increase_reason = self.phase.reason if phase_global_block else (wb.reason if wb.block_increase else "")
        site = Site(now=now, grid_w=grid or 0.0, filtered_grid_w=self.filtered or 0.0,
                    valid=valid, mode=effective_mode,
                    reserve_w=self.settings["reserve_w"], max_import_w=capacity_limit,
                    battery_discharge_w=discharge, battery_ready=ready,
                    fault_elapsed_s=0 if self.invalid_since is None else now - self.invalid_since,
                    fault_grace_s=self.settings["fault_grace_s"], can_increase=can_increase,
                    external_hold=external_hold, external_reason=external_reason,
                    increase_reason=increase_reason,
                    max_increase_w=max_increase, device_increase_limits=phase_device_limits,
                    device_holds=device_holds, device_start_blocks=device_start_blocks,
                    no_reclaim_ids=subordinate_ids, subordinate_ids=subordinate_ids,
                    ordered_priorities=self.priority_board.active,
                    priority_ids={i for i,c in self.configs.items() if dishwasher_has_priority(c)},
                    protected_ev_credit=priority.ev_credit,
                    comfort_reserve_w=getattr(self,"_dishwasher_comfort_reserve",0) + isolated_reserve,
                    reclaimable_w=getattr(self.wallbox_guard, "reclaimable_w", 0),
                    max_takeover_w=self.wallbox_settings["max_takeover_w"],
                    handover_s=self.wallbox_settings["handover_s"],
                    handover_device=transfer.device_id if waiting else "",
                    handover_target_w=transfer.new_w if waiting else 0,
                    bridge_w=(min(transfer.borrowed_w, max(0, (grid or 0) + self.settings["reserve_w"] + discharge)) if waiting else 0),
                    rollback_device=transfer.device_id if rollback else "",
                    rollback_target_w=transfer.old_w if rollback else 0,
                    rollback_reason=transfer.reason if rollback else "")
        self._start_context = {
            "measurement_valid": bool(valid),
            # Keep source attribution separate for the UI.  The Site still gets
            # the combined map above, so this changes no planning decision.
            "device_start_blocks": dict(runtime_start_blocks),
            "wallbox_start_blocks": wallbox_start_blocks,
            "wallbox_global_block": bool(wb.block_increase),
            "wallbox_reason": wb.reason if wb.block_increase else "",
            "can_increase": bool(site.can_increase),
            "increase_reason": str(site.increase_reason or ""),
            "effective_import_limit_w": float(site.max_import_w),
            "max_increase_w": site.max_increase_w,
            "device_increase_limits": dict(site.device_increase_limits),
        }
        operational_devices = [d for d in self.devices() if d.id not in isolated_ids]
        self.result = plan(site, operational_devices, self.states)
        if extra_reclaim and (self.result.action is None or self.result.action.watts > 0):
            self.result.action = extra_reclaim
            self.result.targets[extra_reclaim.id] = 0.0
            self.result.reasons[extra_reclaim.id] = extra_reclaim.reason
        # Deadline permission buys grid energy; it is not permission to borrow EV
        # watts or exceed phase/quarter-hour/import limits. EV solar preference
        # alone may not postpone this explicitly authorised deadline indefinitely.
        due_devices = [d for d in operational_devices if self.dishwasher_app.due(self.configs[d.id], time.time()) and not self.states[d.id].on]
        if due_devices and (self.result.action is None or self.result.action.watts > 0):
            from copy import deepcopy
            due_ids = {d.id for d in due_devices}
            other_commitment = sum(max(0.0, st.target_w-st.measured_w)
                for i, st in self.states.items() if i not in due_ids and i not in isolated_ids and st.owned and st.on)
            deadline_site = replace(site, external_hold=self.phase.release_flexible,
                external_reason=self.phase.reason, device_holds=priority.holds, device_start_blocks=priority.blocks,
                protected_ev_credit={},
                max_import_w=max(0.0, site.max_import_w-other_commitment),
                max_increase_w=(max(0.0, phase_max_increase-other_commitment) if phase_max_increase is not None else None),
                device_increase_limits={i:max(0.0,v-other_commitment) for i,v in site.device_increase_limits.items()},
                reclaimable_w=0, bridge_w=0,
                can_increase=(non_ev_can_increase and not phase_global_block and not self.handover
                              and not dhw_sent and not climate_sent and not self.smart_climate.busy
                              and not self.dhw.blocks_increase))
            candidate = plan(deadline_site, due_devices, deepcopy(self.states))
            if candidate.action and candidate.action.watts > 0:
                self.result.action = replace(candidate.action, reason="AEG-startdeadline bereikt; zo nodig netstroom toegestaan")
                self.result.reasons[candidate.action.id] = self.result.action.reason
                self.result.targets[candidate.action.id] = candidate.action.watts
        for device_id, cfg in self.configs.items():
            if device_id in isolated_ids:
                continue
            if cfg.get("kind") == "dishwasher" and not self.states[device_id].on and self.states[device_id].enabled and not self.states[device_id].fault:
                permit, why = self.dishwasher.permitted(cfg, read_dishwasher(self.hass, cfg), time.time())
                if not permit:
                    self.result.reasons[device_id] = why
        for i, cfg in self.configs.items():
            if not self.dishwasher_app.enabled(cfg):
                continue
            info = self.dishwasher_app.data.get(i, {})
            req = info.get("request", {})
            if (req and time.time() > req["deadline"] + 30 and not self.states[i].on
                    and not (self.pending and self.pending["id"] == i)
                    and info.get("notified_deadline") != req["created"]):
                info["notified_deadline"] = req["created"]
                await self.hass.services.async_call("persistent_notification", "create", {
                    "notification_id": f"{DOMAIN}_{self.entry.entry_id}_{i}_deadline",
                    "title": "Afwasmachine: startdeadline niet gehaald",
                    "message": self.result.reasons.get(i, "Controleer vrijgave, deur, verbinding en energielimieten")}, blocking=False)
                self.dishwasher_app._dirty()
        if transfer:
            self.result.reasons[transfer.device_id] = (self.result.reasons.get(transfer.device_id, "")
                                                       if rollback else transfer.reason)
        for device_id, info in isolated.items():
            self.result.targets[device_id] = self.states[device_id].target_w
            self.result.reasons[device_id] = "Tijdelijk apart gehouden: " + info["reason"]
        self.managed_w = sum(s.measured_w for i, s in self.states.items()
                             if s.owned and s.on and i not in isolated_ids)
        for i, state in self.states.items():
            if (state.owned and state.on and not state.fault and state.available
                    and not self.pending and now-state.last_on >= 60
                    and now-self.last_issued >= 30 and self.configs[i].get("power_entity")):
                watts, stamp = self._power(self.configs[i]["power_entity"])
                if watts is not None:
                    self.learning.observe_device(i, self.configs[i], watts, now, stamp)
        self.energy_estimated = bool(isolated) or any(s.owned and s.on and self._power_is_estimated(i)
                                                    for i, s in self.states.items())
        if valid and 0 < dt <= max(30, self.settings["interval_s"] * 2) and not self.pending:
            self.energy_kwh += max(0, self.managed_w) * dt / 3_600_000
        imp_price, exp_price = self._economy_prices()
        storage_present = bool(self.settings.get("battery_power_entity") or self.battery_fleet.configured)
        self.electricity_cost.seed_legacy(self.ems_stats, local_now, imp_price, exp_price, storage_present)
        self.electricity_cost.update(now=local_now, grid_w=grid if valid else None, pv_w=self.pv_w,
            import_price=imp_price, export_price=exp_price, storage_present=storage_present,
            max_gap_s=max(30, self.settings["interval_s"]*2))
        self.savings_history.capture(self.ems_stats, economy_enabled=self.economy_settings["enabled"],
                                    power_estimated=self.energy_estimated)
        self.ems_stats = accounting_step(
            self.ems_stats, day=local_now.date().isoformat(), dt_s=dt,
            grid_w=grid if valid else None, pv_w=self.pv_w, managed_w=self.managed_w,
            battery_discharge_w=discharge,
            import_price_eur_kwh=imp_price or 0.0, export_price_eur_kwh=exp_price or 0.0)
        self.savings_history.capture(self.ems_stats, economy_enabled=self.economy_settings["enabled"],
                                    power_estimated=self.energy_estimated)
        self._record_automatic_value(local_now, dt, grid, valid, discharge, imp_price, exp_price)
        if valid:
            self.battery_analysis.step(dt, grid)
        if (self.removal_requested and not self.pending and not self.handover and not dhw_sent
                and not climate_sent and not self.smart_climate.busy and not self.battery_fleet.busy
                and not self.result.action):
            battery_sent = await self.battery_fleet.prepare_for_removal()
        elif (self.mode == "paused" and not self.pending and not self.handover and not dhw_sent
                and not climate_sent and not self.smart_climate.busy and not self.battery_fleet.busy
                and not self.result.action):
            battery_sent = await self.battery_fleet.release_owned_targets()
        else:
            battery_sent = await self.battery_fleet.tick(
                grid_w=grid if valid else None,
                capacity_allowed_grid_w=(self.capacity.allowed_grid_w if self.capacity_settings.get("enabled") and self.capacity.valid else None),
                allow_command=(self.mode == "solar" and not self.removal_requested
                               and valid and not self.pending and not self.handover
                               and not dhw_sent and not climate_sent and not self.smart_climate.busy
                               and not self.result.action and not self.restart_blocking))
        if now - self.energy_saved_at >= 300:
            self.energy_saved_at = now
            self.store.async_delay_save(self._snapshot, 1)
        self.problem_kind = ""
        if self.restart_recovery_pending:
            self.problem_kind = "restart_wait"
            self.problem = ("Tijdelijk apart gehouden; herstartcontrole wordt automatisch herhaald — "
                            + ", ".join(self.configs[i]["name"] for i in self.recovery))
        elif self.recovery:
            self.problem_kind = "restart_review"
            self.problem = "Herstartcontrole vereist"
        elif self.faults:
            self.problem_kind = "command_fault"
            self.problem = "Opdrachtfout: handmatige controle nodig"
        else:
            self.problem_kind, self.problem = self._owned_source_problem()
            if not self.problem and not valid:
                self.problem = "Net- of batterijmeting ontbreekt, is te oud of heeft een verkeerde eenheid"
        if not self.problem and wb.state == "unavailable":
            self.problem = wb.reason
        if not self.problem and self.reclaim_blocks:
            self.problem = "Vermogensovername geblokkeerd: controleer het betrokken toestel en rond de foutcontrole af"
        if not self.problem:
            overdue_cycles = [c["name"] for i, c in self.configs.items()
                              if c["non_interruptible"] and c["max_on_s"] > 0 and self.states[i].owned
                              and now - self.states[i].last_on > c["max_on_s"]]
            if overdue_cycles:
                self.problem = "Cyclus langer actief dan verwacht: " + ", ".join(overdue_cycles)
        if not self.problem and (self.dhw.fault or self.dhw.needs_review):
            self.problem = self.dhw.status
        if self.pending:
            self.result.reasons[self.pending["id"]] = "Wacht op opdrachtbevestiging"
        if self.result.action and self.mode != "observe" and not self.restart_blocking and not self.pending and not self.dhw.pending and not climate_sent and not battery_sent:
            # Even reductions are serialized and rate-limited. Stale data can
            # still trigger a safe release without waiting for a new grid sample.
            if now - self.last_issued >= self.settings["settle_s"]:
                await self._send(self.result.action, now)
        if self.removal_requested:
            removal = self.removal_overview()
            if removal["ready"] and not self._removal_ready_noted:
                self._removal_ready_noted = True
                self.note("Verwijderen gereed: SolarPilot bezit geen actieve regeling meer.")
                await self.notify("SolarPilot is veilig vrijgegeven en kan nu via Instellingen → Apparaten & diensten worden verwijderd.")

    async def _call(self, entity_id, service, extra=None):
        if protected_entity(self.hass, self.wallbox_settings, entity_id):
            raise HomeAssistantError("Wallbox-monitor is alleen-lezen: deze opdracht is geblokkeerd")
        domain = entity_id.split(".", 1)[0]
        if not self.hass.services.has_service(domain, service):
            raise HomeAssistantError(f"Actie {domain}.{service} niet beschikbaar")
        await self.hass.services.async_call(domain, service,
                                           {"entity_id": entity_id, **(extra or {})}, blocking=True)

    async def _send(self, action, now):
        i = action.id
        cfg, s = self.configs[i], self.states[i]
        extra_stop = action.reason.startswith("Zonnestroom vrijmaken voor extra warm water")
        if extra_stop:
            allowed, _reason = self.heat_pump_increase_allowed(check_capacity=False)
            candidate = self.priority_board.extra_reclaim_action(now, self._local_now()) if allowed else None
            if candidate is None or candidate.id != i or action.watts != 0:
                self.result.reasons[i] = "Extra warm water wacht: vermogen of toestelbescherming is veranderd"
                return
        isolated = self.source_isolated_devices
        if i in isolated:
            self.result.reasons[i] = "Tijdelijk apart gehouden: " + isolated[i]["reason"]
            return
        # Re-read required sources at the last boundary: an unowned device can
        # lose its meter or regulator after planning but before this dispatch.
        source_reason = ""
        if self._restart_active(cfg) is None:
            source_reason = "Toestelstatus ontbreekt of is onbruikbaar vóór opdracht"
        if cfg.get("power_entity"):
            watts, _ = self._power(cfg["power_entity"])
            if not self._dedicated_meter(i):
                source_reason = "Vermogensmeter is niet exclusief voor dit toestel"
            elif watts is None or watts < -1:
                source_reason = "Vermogensmeting onbetrouwbaar vóór opdracht"
        if cfg.get("kind") == "number":
            obj = self.hass.states.get(cfg.get("number_entity", ""))
            number = self._number(cfg.get("number_entity"))
            valid_regulator = obj is not None and not obj.attributes.get("restored") and number is not None
            if valid_regulator and cfg.get("control_unit"):
                valid_regulator = obj.attributes.get("unit_of_measurement") == cfg["control_unit"]
            try:
                native_min, native_max = float(obj.attributes["min"]), float(obj.attributes["max"])
                valid_regulator = valid_regulator and (native_min <= cfg["min_units"]
                    <= cfg["max_units"] <= native_max and native_min <= number <= native_max)
            except (AttributeError, KeyError, TypeError, ValueError):
                valid_regulator = False
            if not valid_regulator:
                source_reason = "Vermogensregelaar is niet betrouwbaar vóór opdracht"
        if source_reason:
            self.result.reasons[i] = source_reason
            s.start_since = None
            return
        if action.reclaimed_w > 0:
            fresh_wb = self._wallbox_reading()
            if not fresh_wb.valid or (fresh_wb.mode or "").casefold() not in state_set(self.wallbox_settings["full_solar_states"]):
                self.result.reasons[i] = "Laadsessie gewijzigd vóór opdracht; geen EV-vermogen overnemen"
                return
        if cfg.get("kind") == "dishwasher":
            # Defensive boundary: no engine/manual/phase path can send STOP, reset,
            # pause or a plug command. Re-evaluate physical interlocks at dispatch.
            permit, why = self.dishwasher.permitted(cfg, read_dishwasher(self.hass, cfg), time.time())
            if self.mode != "solar" or action.watts <= 0 or s.on or not permit:
                self.result.reasons[i] = why if action.watts > 0 else "Beschermd afwasprogramma: geen stopopdracht toegestaan"
                return
        if action.protected_ev_w > 0:
            wb_now = self._wallbox_reading()
            grid_now, valid_now, discharge_now, ready_now, grid_stamp = self._site_data()
            pv_now, _ = self._power(self.settings.get("pv_entity"))
            credit = min(max(0.0, wb_now.power_w or 0.0), max(0.0, getattr(self.wallbox_guard,"reclaimable_w",0)),
                         float(self.wallbox_settings["max_takeover_w"]))
            cap = self.settings["max_import_w"]
            if self.capacity_settings["enabled"]:
                cap = (0 if not self.capacity.valid else min(cap,
                    self.capacity.allowed_grid_w if self.capacity.allowed_grid_w is not None
                    else self.capacity.effective_target_w or cap))
            commitment = sum(max(0.0, st.target_w-st.measured_w) for key,st in self.states.items()
                             if key != i and key not in isolated and st.owned and st.on)
            isolated_reserve = sum(info["reserve_w"] for info in isolated.values())
            reserved = getattr(self,"_dishwasher_comfort_reserve",0)+commitment+isolated_reserve
            full = (wb_now.mode or "").casefold() in state_set(self.wallbox_settings["full_solar_states"])
            actual_free = -max(grid_now or 0,self.filtered if self.filtered is not None else grid_now or 0)-(discharge_now or 0)-self.settings["reserve_w"]-reserved
            allocation_cfg = self.priority_board.effective_config(i, cfg)
            permissible = (cfg.get("kind") == "dishwasher" and dishwasher_has_priority(cfg)
                and allocation_cfg.get("dishwasher_ev_solar_priority",True) and i not in self.dishwasher_priority.ev_blocks
                and valid_now and ready_now and wb_now.valid and full and wb_now.connected is not False
                and wb_now.demand is not False and wb_now.age_s <= self.wallbox_settings["reclaim_max_age_s"]
                and pv_now is not None and pv_now-(discharge_now or 0)-self.settings["reserve_w"]-isolated_reserve >= action.watts+cfg["start_margin_w"]
                and grid_now+action.watts+reserved <= cap
                and actual_free+credit >= action.watts+cfg["start_margin_w"]
                and action.protected_ev_w <= credit+.01)
            if not permissible:
                self.result.reasons[i] = "Afwasstart uitgesteld: Wallbox-/zonne- of netruimte gewijzigd bij laatste controle"
                s.start_since = None
                return
        # Ambiguous failed stops are not retried blindly; an operator must check.
        if self.faults.get(i):
            return
        if action.watts > 0 and not self._target_matches(cfg, 0) and not s.owned:
            return
        if i in conflicting_devices(self.hass, self.wallbox_settings, [cfg]):
            self.faults[i] = "Dubbele Wallbox-koppeling: alleen-lezen monitor blokkeert bediening"
            return
        old_on = s.on
        old_owned = s.owned
        old_target = s.target_w if s.owned else 0.0
        previous_issued, previous_issued_wall = self.last_issued, self.last_issued_wall
        previous_guards = (deepcopy(self.wallbox_guard), deepcopy(self.consumer_wallbox),
                           deepcopy(self.phase_learning)) if extra_stop else None
        # A binary switch has no physical watt setpoint. If it is already ON and
        # confirmed as SolarPilot-owned, a changed learned/planning watt estimate
        # only updates accounting; it must never cause a duplicate turn_on call.
        if cfg.get("kind") == "switch" and action.watts > 0 and old_on and s.owned:
            if abs(float(s.target_w or 0) - float(action.watts)) > 0.5:
                s.target_w = float(action.watts)
                self.result.targets[i] = float(action.watts)
                self.result.reasons[i] = "Reeds ingeschakeld; alleen planningsvermogen bijgewerkt"
                self.store.async_delay_save(self._snapshot, 1)
            return
        if self.phase_settings.get("enabled") and self.phase_settings.get("learning_enabled", True) and cfg.get("power_entity"):
            before_w, _ = self._power(cfg.get("power_entity"))
            if before_w is not None:
                self.phase_learning.begin_controlled(i, now, self.phase.phase_w, before_w)
        s.owned = True
        s.target_w = action.watts
        if action.watts > 0 and not old_on:
            s.last_on = now
            if cfg["non_interruptible"]:
                s.cycle_armed = False
        self.last_issued = now
        self.last_issued_wall = time.time()
        if action.reclaimed_w > 0:
            self.handover = Handover(i, old_target, action.watts, action.reclaimed_w,
                                     self.wallbox_guard.reading.power_w or 0, now,
                                     self.last_issued_wall, self.wallbox_settings["handover_s"])
            self.note(f'{cfg["name"]}: gecontroleerd {action.reclaimed_w:.0f} W van autonoom laden overnemen; geen Wallbox-opdracht.')
        self.wallbox_guard.note_action(now, self.last_issued_wall, old_target, action.watts)
        if self._per_device_wallbox_enabled() and follows_wallbox(self.priority_board.effective_config(i, cfg), self.others_first):
            self.consumer_wallbox.note_action(now, self.last_issued_wall, i, old_target, action.watts, self.wallbox_guard.reading)
        if cfg.get("kind") == "dishwasher":
            self.dishwasher_priority.started(i, self.last_issued_wall, action.protected_ev_w,
                self.wallbox_guard.reading.power_w or 0)
            self.dishwasher.sent(cfg, self.last_issued_wall)
        self.pending = {"id": i, "watts": action.watts, "issued": now, "issued_wall": self.last_issued_wall,
                        "reason": action.reason,
                        "max_runtime": action.reason.startswith("Maximale looptijd")}
        if action.reason.startswith("Zonnestroom vrijmaken voor extra warm water"):
            self.priority_board.extra_reclaim_sent(action, now)
        self.consumer_history.command(i, action.watts, action.reason)
        # Durable intent BEFORE any physical command, including an uncertain result.
        await self.store.async_save(self._snapshot())
        if extra_stop:
            # The storage await can deliver a manual choice or a source change.
            # Evaluate current inputs while excluding this known-unsent journal;
            # no requested OFF watts become real power in this check.
            trial = copy(self)
            trial.states = deepcopy(self.states)
            trial.states[i].target_w = old_target
            trial.pending = None
            trial.last_issued, trial.last_issued_wall = previous_issued, previous_issued_wall
            trial.priority_board = copy(self.priority_board)
            trial.priority_board.r = trial
            allowed, _reason = trial.heat_pump_increase_allowed(check_capacity=False)
            candidate = trial.priority_board.extra_reclaim_action(now, trial._local_now()) if allowed else None
            if candidate is None or candidate.id != i:
                self.pending = None
                s.target_w, s.owned = old_target, old_owned
                self.last_issued, self.last_issued_wall = previous_issued, previous_issued_wall
                self.wallbox_guard, self.consumer_wallbox, self.phase_learning = previous_guards
                self.priority_board._clear_extra_reclaim()
                self.priority_board._extra_lease_until = 0.0
                message = "Extra warm water uitgesteld: vrijmaken geannuleerd vóór uitvoering omdat de toestand is veranderd"
                self.result.action = None
                self.result.targets[i] = old_target
                self.result.reasons[i] = message
                self.consumer_history.failure(i, message)
                await self.store.async_save(self._snapshot())
                self.note(message)
                return
        self.note(f'{cfg["name"]}: {action.watts:.0f} W aangevraagd — {action.reason}.')
        try:
            async with asyncio.timeout(20):
                if cfg["kind"] == "dishwasher":
                    await self._call(cfg["start_button"], "press")
                elif cfg["kind"] == "script":
                    await self._call(cfg["start_script"] if action.watts else cfg["stop_script"], "turn_on")
                elif cfg["kind"] == "number":
                    if action.watts:
                        units = round(action.watts / cfg["watts_per_unit"], 6)
                        if not cfg["min_units"] <= units <= cfg["max_units"]:
                            raise HomeAssistantError("Doelwaarde buiten geconfigureerd bereik")
                        await self._call(cfg["number_entity"], "set_value", {"value": units})
                        if not old_on:
                            await self._call(cfg["control_entity"], "turn_on")
                    else:
                        # Never write 0 A into an EVSE with a 6 A minimum. Pause via
                        # its explicit enable switch; retain the last safe setpoint.
                        await self._call(cfg["control_entity"], "turn_off")
                else:
                    await self._call(cfg["control_entity"], "turn_on" if action.watts else "turn_off")
        except (HomeAssistantError, TimeoutError, ValueError) as err:
            self.faults[i] = f"Opdrachtfout: {type(err).__name__}; controleer het toestel"
            self.consumer_history.failure(i, self.faults[i])
            self.pending = None
            self.note(f'{cfg["name"]}: opdrachtuitkomst onzeker.')
            _LOGGER.warning("Command failed for %s: %s", cfg["name"], err)
            await self.notify(f'{cfg["name"]}: opdracht mislukt of vertraagd. Controleer de fysieke toestand. De regelaar probeert dit niet onbeperkt opnieuw.')

    def removal_overview(self):
        blockers = []
        if self.pending:
            blockers.append("Wacht op bevestiging van een lopende toestelopdracht")
        if self.handover:
            blockers.append("Wacht tot de Wallbox-vermogensovername is afgerond")
        if self.recovery:
            blockers.append("Rond eerst de herstartcontrole af")
        owned = [self.configs[i]["name"] for i, st in self.states.items() if st.owned]
        if owned:
            blockers.append("Nog door SolarPilot beheerd: " + ", ".join(owned))
        if self.dhw.busy:
            blockers.append("Boilerdoel wordt nog veilig vrijgegeven")
        if self.smart_climate.removal_blocked():
            blockers.append("Ruimteklimaat wordt nog terug vrijgegeven aan Panasonic AUTO")
        if self.battery_fleet.removal_blocked():
            blockers.append("Batterijopdracht of batterijvermogen is nog niet neutraal")
        ready = self.mode != "solar" and not blockers
        return {
            "requested": bool(self.removal_requested),
            "ready": bool(ready),
            "blockers": blockers,
            "status": "Verwijderen gereed" if ready else ("Veilig vrijgeven bezig" if self.removal_requested else "Niet voorbereid"),
            "prepare_entity": self.entity_id("button", "prepare_remove"),
            "note": "Onderliggende Home Assistant-apparaten worden nooit verwijderd.",
        }

    async def prepare_removal(self):
        """Enter a safe release state without deleting anything.

        The routine never hard-stops protected cycles. It merely starts the same
        safe release logic used by Pause and lets later ticks finish the handover.
        """
        async with self._lock:
            self.removal_requested = True
            self._removal_ready_noted = False
            self.mode = "paused"
            self.restart_requested_mode = None
            for st in self.states.values():
                st.boost_until = 0
                st.start_since = None
            self.dhw.auto_enabled = False
            self.note("Verwijderen voorbereid: Pauze actief; SolarPilot geeft eigen regelingen veilig vrij.")
            self.store.async_delay_save(self._snapshot, 1)
        await self.tick()

    async def set_mode(self, mode):
        async with self._lock:
            if mode not in ("observe", "solar", "paused"):
                raise HomeAssistantError("Onbekende modus")
            if mode == "solar" and (self.restart_blocking or self.dhw.needs_review):
                raise HomeAssistantError("Rond eerst de herstartcontrole af")
            if mode == "solar" and self.legacy_conflicts():
                names = ", ".join(x["name"] for x in self.legacy_conflicts())
                raise HomeAssistantError("Schakel eerst de vervangen regelaars uit: " + names)
            if mode == "observe" and (self.dhw.busy or self.pending
                    or self.smart_climate.removal_blocked() or self.battery_fleet.removal_blocked()
                    or any(s.owned for s in self.states.values())):
                raise HomeAssistantError("Kies eerst Pauze. Wacht tot de beheerde toestellen veilig zijn vrijgegeven.")
            if mode != self.mode:
                for s in self.states.values():
                    s.start_since = None
                    if mode != "solar":
                        s.boost_until = 0
                        s.manual_forced = False
            self.mode = mode
            self.restart_requested_mode = None
            self.store.async_delay_save(self._snapshot, 1)
            self.note(f"Modus: {mode}.")
        await self.tick()

    async def set_priority(self, device_id, value):
        async with self._lock:
            if self.priority_board.active:
                raise HomeAssistantError("Gebruik SolarPilot → Voorrang om de centrale volgorde te wijzigen; losse prioriteitsgetallen zijn niet meer leidend.")
            self.priorities[device_id] = max(1, min(100, int(value)))
            self.store.async_delay_save(self._snapshot, 1)
        await self.tick()

    async def set_device_mode(self, device_id, value):
        async with self._lock:
            if value not in ("auto", "disabled"):
                raise HomeAssistantError("Onbekende toestelmodus")
            self.device_modes[device_id] = value
            self.states[device_id].start_since = None
            if value == "disabled":
                self.states[device_id].boost_until = 0
            self.store.async_delay_save(self._snapshot, 1)
        await self.tick()

    async def arm_dishwasher(self, device_id):
        if self.dishwasher_app.enabled(self.configs[device_id]):
            raise HomeAssistantError("Gebruik Delay Start / APP op de afwasmachine; geen extra klaarzetknop nodig")
        async with self._lock:
            cfg = self.configs[device_id]
            if cfg.get("kind") != "dishwasher" or self.pending or self.faults.get(device_id):
                raise HomeAssistantError("Controleer eerst de bestaande opdracht of fout")
            try:
                self.dishwasher.arm(cfg, read_dishwasher(self.hass, cfg), time.time())
            except ValueError as err:
                raise HomeAssistantError(str(err)) from err
            self.states[device_id].cycle_armed = True
            self.states[device_id].start_since = None
            self.unified_plan = None
            self.unified_planner.last_plan_wall = 0
            await self.store.async_save(self._snapshot())
            self.consumer_history.event(device_id, "Eén afwasbeurt door gebruiker klaargezet; geselecteerd programma behouden")
            self.note(f'{cfg["name"]}: één automatische afwasbeurt klaargezet.')
        await self.tick()

    async def cancel_dishwasher(self, device_id):
        async with self._lock:
            self.dishwasher_app.cancel(self.configs[device_id])
            self.dishwasher.cancel(device_id)
            self.states[device_id].cycle_armed = False
            await self.store.async_save(self._snapshot())
            self.note(f'{self.configs[device_id]["name"]}: toekomstige start ingetrokken; lopend programma niet onderbroken.')
        await self.tick()

    async def boost(self, device_id, minutes=30):
        if self.configs[device_id].get("kind") == "dishwasher":
            raise HomeAssistantError("Gebruik Eén beurt klaarzetten; geen netboost voor deze beschermde afwasbeurt")
        async with self._lock:
            if device_id in self.source_isolated_devices:
                raise HomeAssistantError("Toestel wordt tijdelijk apart gehouden tot de bronnen betrouwbaar zijn")
            if self.mode != "solar" or self.restart_blocking:
                raise HomeAssistantError("Boost vereist Zonnestroommodus en een afgeronde herstartcontrole")
            if self.capacity_settings["enabled"] and not self.capacity.valid:
                raise HomeAssistantError("Boost geblokkeerd: kwartierpiekmeting is niet betrouwbaar")
            s = self.states[device_id]
            if not s.enabled or s.fault or s.manual_until > time.monotonic() or not s.interlock or not s.demand:
                raise HomeAssistantError("Toestel is niet vrijgegeven. Controleer modus, vraag, handmatige overname en eventuele fouten.")
            s.boost_until = time.monotonic() + minutes * 60
            s.start_since = None
            self.note(f'{self.configs[device_id]["name"]}: boost {minutes} min aangevraagd; netverbruik toegestaan binnen de ingestelde grens.')
        await self.tick()

    async def manual_start(self, device_id):
        if self.configs[device_id].get("kind") == "dishwasher":
            raise HomeAssistantError("Gebruik Eén beurt klaarzetten; de AEG-startvoorwaarden blijven verplicht")
        """Explicitly keep a consumer on until the user releases it or safety wins."""
        async with self._lock:
            if device_id in self.source_isolated_devices:
                raise HomeAssistantError("Toestel wordt tijdelijk apart gehouden tot de bronnen betrouwbaar zijn")
            if self.mode != "solar" or self.restart_blocking:
                raise HomeAssistantError("Manuele start vereist Zonnestroommodus en een afgeronde herstartcontrole")
            if self.pending or self.handover:
                raise HomeAssistantError("Wacht eerst tot de lopende SolarPilot-opdracht is afgerond")
            cfg, st = self.configs[device_id], self.states[device_id]
            active = self._active(cfg)
            if active is None or st.fault or not st.interlock:
                raise HomeAssistantError("Toestel kan niet veilig manueel worden gestart; controleer beschikbaarheid, vrijgave en fouten")
            st.manual_forced = True
            st.manual_stop_requested = False
            st.manual_until = 0
            # Explicit user confirmation replaces the normal solar start-delay,
            # while min-off and software import limits remain enforced by engine.
            st.start_since = time.monotonic() - float(cfg.get("start_delay_s", 0))
            self.consumer_history.event(device_id, "Manuele start door gebruiker bevestigd")
            self.note(f'{cfg["name"]}: manuele start bevestigd; normale veiligheids- en vermogensgrenzen blijven gelden.')
            self.store.async_delay_save(self._snapshot, 1)
        await self.tick()

    async def manual_stop(self, device_id):
        if self.configs[device_id].get("kind") == "dishwasher":
            return await self.cancel_dishwasher(device_id)
        """Request release/off after the configured minimum run time."""
        async with self._lock:
            if device_id in self.source_isolated_devices:
                raise HomeAssistantError("Toestel wordt tijdelijk apart gehouden tot de bronnen betrouwbaar zijn")
            if self.pending or self.handover:
                raise HomeAssistantError("Wacht eerst tot de lopende SolarPilot-opdracht is afgerond")
            cfg, st = self.configs[device_id], self.states[device_id]
            st.manual_forced = False
            st.manual_stop_requested = bool(st.on and st.owned)
            st.boost_until = 0
            self.consumer_history.event(device_id, "Manuele stop/vrijgave door gebruiker bevestigd")
            self.note(f'{cfg["name"]}: manuele stop/vrijgave bevestigd; minimale looptijd blijft gerespecteerd.')
            self.store.async_delay_save(self._snapshot, 1)
        await self.tick()

    async def cancel_boost(self, device_id):
        async with self._lock:
            self.states[device_id].boost_until = 0
        await self.tick()

    async def takeover(self, device_id):
        """Explicit manual handover. This DOES NOT switch off physical equipment.

        Useful for a disconnected/replaced device or a deliberately continuing
        cycle. Only permitted while not in automatic mode, with no pending call.
        """
        async with self._lock:
            if self.mode == "solar" or self.pending:
                raise HomeAssistantError("Kies eerst Pauze en wacht op lopende opdrachten")
            s = self.states[device_id]
            self.recovery.pop(device_id, None)
            self._restart_faults.pop(device_id, None)
            self.faults.pop(device_id, None)
            s.owned = False
            s.target_w = 0
            s.boost_until = 0
            s.manual_forced = False
            s.manual_stop_requested = False
            s.fault = ""
            s.manual_until = time.monotonic() + self.configs[device_id]["manual_hold_s"]
            self.device_modes[device_id] = "disabled"
            await self.store.async_save(self._snapshot())
            self.consumer_history.event(device_id, "Expliciet handmatig overgenomen; GEEN uitschakelopdracht verzonden")
            self.note(f'{self.configs[device_id]["name"]}: expliciet handmatig overgenomen; GEEN uitschakelopdracht verzonden.')
        await self.tick()

    async def reset(self):
        async with self._lock:
            if self.pending:
                raise HomeAssistantError("Wacht eerst op de lopende opdracht")
            ids = set(self.recovery) | set(self.faults) | set(self.reclaim_blocks) | set(self.dishwasher_priority.ev_blocks)
            if not ids and self.problem_kind in ("source_wait", "source_configuration"):
                # A stale page or direct button call must not claim all devices
                # were verified OFF when only a derived source guard exists.
                raise HomeAssistantError(self.problem)
            not_off = [self.configs[i]["name"] if i in self.configs else i for i in ids
                       if i not in self.configs or self._active(self.configs[i]) is not False]
            if not_off:
                raise HomeAssistantError("Controleer en schakel eerst veilig uit: " + ", ".join(not_off))
            for i in ids:
                if i in self.states:
                    self.states[i].owned = False
                    self.states[i].target_w = 0
                    self.states[i].last_off = time.monotonic()
                    self.states[i].fault = ""
                    self.states[i].manual_forced = False
                    self.states[i].manual_stop_requested = False
                    if self.configs[i].get("kind") == "dishwasher":
                        self.dishwasher.review(i)
                        self.states[i].cycle_armed = False
            self.faults.clear()
            self.recovery.clear()
            self._restart_faults.clear()
            self.reclaim_blocks.clear()
            self.dishwasher_priority.ev_blocks.clear()
            self.dishwasher_priority.watches = {i:v for i,v in self.dishwasher_priority.watches.items()
                if v.get("status") != "attention"}
            self.battery_fleet.state.faults.clear()
            self.battery_fleet.state.pending = None
            await self.store.async_save(self._snapshot())
            self.note("Herstart- en foutcontrole afgerond. Alle betrokken toestellen zijn als uit bevestigd.")
        await self.tick()

    def entity_id(self, kind, suffix, device_id=None):
        unique = f'{self.entry.entry_id}_{device_id + "_" if device_id else ""}{suffix}'
        return er.async_get(self.hass).async_get_entity_id(kind, DOMAIN, unique)

    def _record_automatic_value(self, local_now, dt, grid, valid, discharge, import_price, export_price):
        """Account only current automatic consumer intervals, never issue a command."""
        if self.mode != "solar" or not valid or self.pending or self.restart_blocking or self.faults:
            return
        now = time.monotonic()
        isolated_ids = set(self.source_isolated_devices)
        active = [i for i, s in self.states.items() if s.owned and s.on and s.available
                  and not s.fault and not s.manual_forced and s.boost_until <= now
                  and self.device_modes.get(i) == "auto" and i not in isolated_ids]
        if isolated_ids and not active:
            return
        self.savings_history.record_automatic_interval(
            day=local_now.date().isoformat(), dt_s=dt, grid_w=grid, pv_w=self.pv_w,
            automatic_w=sum(max(0.0, self.states[i].measured_w) for i in active),
            battery_discharge_w=discharge, import_price_eur_kwh=import_price,
            export_price_eur_kwh=export_price,
            power_estimated=any(self._power_is_estimated(i) for i in active),
            timestamp=local_now.timestamp(), max_gap_s=max(30, self.settings["interval_s"]*2))

    def _device_start_diagnostics(self, d, s, cfg, now):
        """Explain current start inputs without replacing the engine verdict."""
        mode = self.device_modes.get(d.id, "disabled")
        solar_mode = self.mode == "solar"
        recovery_active = self.restart_blocking or d.id in self.source_isolated_devices
        observed = bool(s.observed_once)
        rest_remaining = (0 if s.on else
                          max(0, math.ceil(float(d.min_off_s) - (now - s.last_off))))
        cycle_met = not d.non_interruptible or (observed and (s.on or s.cycle_armed))
        daily_limit = max(0.0, float(d.max_daily_runtime_s))
        daily_used = max(0.0, float(s.daily_runtime_s))
        daily_remaining = max(0.0, daily_limit - daily_used) if daily_limit else None
        planner_blocked = bool(s.planner_hold and not s.on)
        context = self._start_context if isinstance(self._start_context, dict) else {}
        device_blocks = context.get("device_start_blocks", {})
        wallbox_blocks = context.get("wallbox_start_blocks", {})
        runtime_block_reason = str(device_blocks.get(d.id, ""))
        wallbox_reason = str(wallbox_blocks.get(d.id, ""))
        wallbox_blocked = bool(not s.on and (wallbox_reason or context.get("wallbox_global_block")))
        if wallbox_blocked and not wallbox_reason:
            wallbox_reason = str(context.get("wallbox_reason", ""))
        runtime_blocked = bool(not s.on and runtime_block_reason)
        measurement_valid = bool(context.get("measurement_valid", self.grid_w is not None))
        increase_known = "can_increase" in context
        increase_allowed = bool(context.get("can_increase")) if increase_known else None
        increase_reason = str(context.get("increase_reason", ""))
        window_enabled = bool(cfg.get("time_window_enabled", False))
        try:
            from zoneinfo import ZoneInfo
            zone = getattr(getattr(self.hass, "config", None), "time_zone", "Europe/Brussels")
            local_now = datetime.now(ZoneInfo(zone))
        except Exception:
            local_now = datetime.now().astimezone()
        window_active = self._time_window_active(local_now, cfg)

        requirements = {
            "global_solar_mode": {
                "met": solar_mode, "required_mode": "solar", "current_mode": self.mode,
            },
            "recovery_clear": {
                "met": not recovery_active, "active": recovery_active,
            },
            "automatic_participation": {
                "met": mode == "auto", "required_mode": "auto", "current_mode": mode,
            },
            "reliable_energy_measurement": {
                "met": measurement_valid, "valid": measurement_valid,
            },
            "availability_and_fault": {
                "met": bool(observed and s.available and not s.fault),
                "available": bool(s.available) if observed else None,
                "fault": str(s.fault or ""), "observed": observed,
            },
            "release": {"met": bool(observed and s.interlock),
                        "released": bool(s.interlock) if observed else None},
            "demand_or_time_window": {
                "met": bool(observed and s.demand),
                "demand": bool(s.demand) if observed else None,
                "time_window_enabled": window_enabled, "time_window_active_now": bool(window_active),
                "time_window_start": cfg.get("time_window_start", "00:00:00"),
                "time_window_end": cfg.get("time_window_end", "23:59:00"),
            },
            "minimum_rest": {
                "met": rest_remaining == 0, "configured_s": float(d.min_off_s),
                "remaining_s": rest_remaining,
            },
            "non_interruptible_cycle_release": {
                "met": bool(cycle_met), "required": bool(d.non_interruptible),
                "armed": bool(s.cycle_armed),
            },
            "daily_maximum": {
                "met": not daily_limit or daily_used < daily_limit,
                "configured": bool(daily_limit), "limit_s": daily_limit,
                "used_s": round(daily_used, 1), "remaining_s": (round(daily_remaining, 1)
                                                                  if daily_remaining is not None else None),
            },
            "planner_start_block": {
                "met": not planner_blocked, "blocked": planner_blocked,
                "reason": str(s.planner_reason or "") if planner_blocked else "",
            },
            "wallbox_start_block": {
                "met": not wallbox_blocked, "blocked": wallbox_blocked,
                "reason": wallbox_reason,
            },
            "runtime_start_block": {
                "met": not runtime_blocked, "blocked": runtime_blocked,
                "reason": runtime_block_reason,
            },
            "general_increase_permission": {
                "met": bool(increase_known and increase_allowed),
                "known": increase_known, "allowed": increase_allowed,
                "reason": increase_reason,
            },
        }
        allocation = getattr(self.result, "start_power", {}).get(d.id)
        if not s.on and allocation is not None:
            requirements["allocated_start_power"] = {
                "met": bool(measurement_valid and allocation["sufficient"]),
                **allocation,
            }
        missing = [key for key, value in requirements.items() if not value["met"]]
        building = bool(not s.on and s.start_since is not None)
        elapsed = max(0.0, now - s.start_since) if building else None
        stable_remaining = (max(0, math.ceil(float(d.start_delay_s) - elapsed))
                            if elapsed is not None else None)
        reason = self.result.reasons.get(d.id, "Initialiseren")
        selected = bool(self.result.action and self.result.action.id == d.id
                        and self.result.action.watts > 0)
        diagnostics = {
            # This is deliberately the decisive summary. The structured values
            # below expose inputs; they do not invent a competing root cause.
            "summary": reason, "summary_source": "result.reason",
            "missing": missing, "listed_requirements_met": not missing,
            "listed_requirements_are_not_a_start_guarantee": True,
            "selected_for_command": selected,
            "allocated_target_w": round(self.result.targets.get(d.id, 0.0), 1),
            "power": {
                "minimum_w": round(d.minimum, 1),
                "start_margin_w": round(d.start_margin_w, 1),
                "required_start_w": round(d.minimum + d.start_margin_w, 1),
                "measured_free_w": (round(self.result.free_w, 1) if measurement_valid else None),
                "measurement_valid": measurement_valid,
                "effective_import_limit_w": (round(float(context["effective_import_limit_w"]), 1)
                                               if context.get("effective_import_limit_w") is not None else None),
                "maximum_general_increase_w": (round(float(context["max_increase_w"]), 1)
                                                if context.get("max_increase_w") is not None else None),
                "device_increase_limit_w": (round(float(context.get("device_increase_limits", {}).get(d.id)), 1)
                                             if context.get("device_increase_limits", {}).get(d.id) is not None else None),
                "allocation": dict(allocation) if measurement_valid and allocation is not None else None,
                "note": ("Actuele vrije netinjectie na batterijontlading en huisreserve; "
                         "hogere prioriteiten, reeds toegezegd vermogen en andere reserves kunnen minder vrijlaten."),
            },
            "stable_start": {
                "building": building, "configured_s": float(d.start_delay_s),
                "elapsed_s": round(elapsed, 1) if elapsed is not None else None,
                "remaining_s": stable_remaining,
            },
        }
        if cfg.get("kind") == "dishwasher":
            pool = self.dishwasher_priority.view.start_power.get(d.id)
            diagnostics["power"]["solar_start_pool"] = dict(pool) if measurement_valid and pool else None
        return requirements, diagnostics

    def overview(self):
        now = time.monotonic()
        result = []
        profiles = self.learning.overview(self.wallbox_settings["stable_s"])["profiles"]
        for d in sorted(self.devices(), key=lambda x: (x.priority, x.id)):
            s, cfg = self.states[d.id], self.priority_board.effective_config(d.id)
            start_requirements, start_diagnostics = self._device_start_diagnostics(d, s, cfg, now)
            result.append({
                "id": d.id, "name": d.name, "priority": d.priority, "kind": d.kind,
                "dishwasher": {**self.dishwasher.overview(cfg, time.time()), **self.dishwasher_app.overview(cfg, time.time()),
                    "priority_policy": {**self.dishwasher_priority.overview(d.id), "configured": dishwasher_has_priority(cfg),
                        "ev_solar_priority": bool(cfg.get("dishwasher_ev_solar_priority", True)),
                        "unmetered_reserve_w": getattr(self,"_dishwasher_unmetered_reserve",0)}} if cfg.get("kind") == "dishwasher" else None,
                "dishwasher_arm_entity": self.entity_id("button", "dishwasher_arm", d.id) if cfg.get("kind") == "dishwasher" else None,
                "dishwasher_cancel_entity": self.entity_id("button", "dishwasher_cancel", d.id) if cfg.get("kind") == "dishwasher" else None,
                "mode": self.device_modes.get(d.id, "disabled"),
                "owned": s.owned, "on": s.on, "available": s.available,
                "power_w": round(s.measured_w, 1), "estimated": self._power_is_estimated(d.id),
                "target_w": round(self.result.targets.get(d.id, 0), 1),
                "reason": self.result.reasons.get(d.id, "Initialiseren"),
                "start_requirements": start_requirements,
                "start_diagnostics": start_diagnostics,
                "boost_seconds": max(0, int(s.boost_until - now)),
                "manual_forced": bool(s.manual_forced),
                "manual_stop_requested": bool(s.manual_stop_requested),
                "manual_seconds": max(0, int(s.manual_until - now)),
                "non_interruptible": d.non_interruptible,
                "daily_runtime_s": round(s.daily_runtime_s, 1),
                "history": self.consumer_history.brief(d.id),
                "daily_energy_kwh": round(s.daily_energy_kwh, 4),
                "min_daily_runtime_s": d.min_daily_runtime_s,
                "max_daily_runtime_s": d.max_daily_runtime_s,
                "daily_deadline": d.daily_deadline,
                "deadline_urgent": s.deadline_urgent,
                "deadline_grid_allowed": d.deadline_grid_allowed,
                "allow_wallbox_reclaim": d.allow_wallbox_reclaim,
                "wallbox_power_policy": cfg.get("wallbox_power_policy", "priority"),
                "wallbox_power_reason": reclaim_permission(cfg,before_wallbox=not follows_wallbox(cfg,self.others_first),
                    dedicated_meter=self._reclaim_meter(d.id),blocked=d.id in self.reclaim_blocks)[2],
                "wallbox_precedence": cfg.get("wallbox_precedence", "global"),
                "wallbox_first": follows_wallbox(cfg, self.others_first),
                "reclaim_block": self.reclaim_blocks.get(d.id, ""),
                "time_window_enabled": bool(cfg.get("time_window_enabled", False)),
                "time_window_start": cfg.get("time_window_start", "00:00:00"),
                "time_window_end": cfg.get("time_window_end", "23:59:00"),
                "forecast_deferrable": bool(cfg.get("forecast_deferrable", False)),
                "planner_hold": s.planner_hold, "planner_reason": s.planner_reason,
                "planner_grid_force": s.planner_grid_force,
                "cycle_learning": self.cycle_learning.estimate(d.id,self._cycle_program(cfg),fallback_energy_kwh=cfg.get("cycle_energy_kwh",0),fallback_duration_min=cfg.get("cycle_duration_min",0),fallback_peak_w=d.nominal_w).as_dict(),
                "configured_nominal_w": cfg.get("nominal_w"), "effective_nominal_w": d.nominal_w,
                "learning": profiles.get(d.id, {}),
                "phase": {**self.phase_learning.profile(d.id), "hint": cfg.get("phase_hint", "auto")},
                "priority_entity": self.entity_id("number", "priority", d.id),
                "mode_entity": self.entity_id("select", "mode", d.id),
                "boost_entity": self.entity_id("button", "boost", d.id),
                "cancel_entity": self.entity_id("button", "cancel_boost", d.id),
                "manual_start_entity": self.entity_id("button", "manual_start", d.id),
                "manual_stop_entity": self.entity_id("button", "manual_stop", d.id),
                "status_entity": self.entity_id("sensor", "status", d.id),
                "takeover_entity": self.entity_id("button", "takeover", d.id),
            })
        return result


    async def _advance_handover(self, now, reading, grid, grid_stamp, discharge, battery_ready):
        t = self.handover
        if not t:
            return
        s, cfg = self.states[t.device_id], self.priority_board.effective_config(t.device_id)
        watts, stamp = self._power(cfg.get("power_entity"))
        has_precedence = (self.others_first if not self._per_device_wallbox_enabled()
                          else not follows_wallbox(cfg, self.others_first))
        allowed = (self.mode == "solar" and has_precedence and s.enabled and s.demand and s.interlock
                   and battery_ready and reading.mode is not None
                   and reading.mode.casefold() in state_set(self.wallbox_settings["full_solar_states"])
                   and reading.age_s <= self.wallbox_settings["reclaim_max_age_s"])
        if t.status == "waiting" and not s.owned and not self.pending:
            t.fail("Overname beëindigd: toestel extern gewijzigd; geen verdere bediening")
        t.evaluate(now, grid_w=grid, grid_stamp=grid_stamp, reading=reading,
                   measured_w=watts or 0, measured_stamp=stamp,
                   available=s.available and not s.fault and watts is not None,
                   allowed=allowed, discharge_w=discharge, ceiling_w=self.settings["max_import_w"],
                   import_tolerance_w=self.wallbox_settings["handover_import_w"],
                   confirm_s=self.wallbox_settings["handover_confirm_s"])
        if t.status == "waiting":
            return
        if not t.outcome_recorded:
            t.outcome_recorded = True
            self.learning.record_handover(t.status == "success", now-t.issued)
            self.note(f'{cfg["name"]}: {t.reason}.')
            if t.status == "rollback":
                self.reclaim_blocks[t.device_id] = t.reason
                self.wallbox_guard.cooldown_until = now+self.wallbox_settings["cooldown_s"]
                self.wallbox_guard.conflict_count += 1
            self.store.async_delay_save(self._snapshot, 1)
        self.last_handover = {**t.overview(now), "device_name": cfg["name"]}
        if t.status == "success":
            self.handover = None
            self.filtered = grid
            self.wallbox_guard.history.clear()
            self.wallbox_guard.result = replace(self.wallbox_guard.result, block_increase=True, max_increase_w=0)
        elif not self.pending and (not s.owned or self._target_matches(cfg, t.old_w)):
            # A failed transfer is not automatically tried again for this device.
            # Normal, genuinely available export can still be used after cooldown.
            self.handover = None
            self.wallbox_guard.cooldown_until = now+self.wallbox_settings["cooldown_s"]
            self.wallbox_guard.history.clear()

    async def set_others_first(self, enabled):
        async with self._lock:
            if self.priority_board.active:
                raise HomeAssistantError("Gebruik SolarPilot → Voorrang om de plaats van de Wallbox te wijzigen.")
            enabled = bool(enabled)
            if self.others_first == enabled:
                return
            self.others_first = enabled
            self.wallbox_guard = self._make_wallbox_guard()
            self._yield_to_wallbox = (not self._per_device_wallbox_enabled() and not enabled and self.wallbox_settings["enabled"]
                                      and any(s.owned for s in self.states.values()))
            for state in self.states.values():
                state.start_since = None
            if self.handover:
                self.handover.fail("Voorrang gewijzigd tijdens overname: eigen verhoging terugnemen")
            await self.store.async_save(self._snapshot())
            self.note(("Globale voorkeur bijgewerkt; afzonderlijke toestelkeuzes blijven leidend.")
                      if self._per_device_wallbox_enabled() else
                      "Andere toestellen eerst; Wallbox neemt de rest." if enabled else
                      "Wallbox eerst; eigen lasten worden veilig vrijgegeven.")
        await self.tick()

    async def set_learning(self, enabled):
        async with self._lock:
            self.learning.enabled = bool(enabled)
            await self.store.async_save(self._snapshot())
            self.note("Leren van toestelvermogen en Wallbox-respons ingeschakeld."
                      if enabled else
                      "Leren van toestelvermogen en Wallbox-respons uitgeschakeld; vaste instellingen.")
        await self.tick()

    async def reset_learning(self):
        async with self._lock:
            self.learning.reset()
            self.local_pv.reset_live()
            self.phase_learning.reset()
            self.smart_climate.state.reset_learning()
            await self.store.async_save(self._snapshot())
            self.note("Apparaat-, lokale PV-, fase- en klimaatleerdata gewist. Operationele toestand, historische PV-bootstrap en veiligheidsinstellingen blijven behouden.")
        self.publish()

    def learning_overview(self):
        return {**self.learning.overview(self.wallbox_settings["stable_s"]),
                "pv_model": self.local_pv.overview(),
                "phase_learning": self.phase_learning.overview(self.configs, self._phase_monitor_configs()),
                "thermal_model": self.smart_climate.overview(),
                "switch_entity": self.entity_id("switch", "learning"),
                "reset_entity": self.entity_id("button", "reset_learning")}
