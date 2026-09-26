"""Intentionally omit entity IDs, device names, logs, and HA configuration."""
from .const import VERSION


async def async_get_config_entry_diagnostics(hass, entry):
    r = entry.runtime_data
    return {"version": VERSION, "mode": r.mode, "device_count": len(r.configs),
            "recovery_count": len(r.recovery), "fault_count": len(r.faults),
            "pending": r.pending is not None, "meter_valid": r.grid_w is not None,
            "wallbox": {"enabled": r.wallbox_settings["enabled"],
                        "policy": "house_first" if r.others_first else "priority",
                        "learning": {k: v for k, v in r.learning_overview().items() if k not in ("profiles", "switch_entity", "reset_entity")},
                        "state": r.wallbox_guard.result.state,
                        "block_increase": r.wallbox_guard.result.block_increase,
                        "possible_interactions": r.wallbox_guard.conflict_count},
            "dhw": {"configured": r.dhw.configured, "enabled": r.dhw.auto_enabled,
                    "pending": bool(r.dhw.pending), "owned": r.dhw.owned_target is not None,
                    "needs_review": r.dhw.needs_review, "manual_hold": r.dhw.manual_hold,
                    "fault": bool(r.dhw.fault), "cooling_sources": len(r.dhw.config.get("cooling_entities", [])),
                    "exclusive_power_meter": r.dhw.exclusive_meter()},
            "ems": {"capacity_enabled": r.capacity_settings["enabled"],
                    "phase_enabled": r.phase_settings["enabled"],
                    "phase_control_starts": r.phase_settings.get("control_starts", False),
                    "phase_shed": r.phase_settings.get("shed_on_overlimit", False),
                    "forecast_enabled": r.forecast_settings["enabled"],
                    "economy_enabled": r.economy_settings["enabled"],
                    "planner_enabled": r.planner_settings["enabled"],
                    "cheap_grid_enabled": r.planner_settings.get("early_grid_enabled", False)},
            "timing": {k: r.settings[k] for k in ("interval_s", "settle_s", "stale_s", "filter_s")},
            "devices": [{"kind": c["kind"], "measured": bool(c.get("power_entity")),
                         "non_interruptible": c["non_interruptible"],
                         "owned": r.states[i].owned, "available": r.states[i].available}
                        for i, c in r.configs.items()]}
