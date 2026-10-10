"""Intentionally omit entity IDs, device names, logs, and HA configuration."""
from .const import VERSION


async def async_get_config_entry_diagnostics(hass, entry):
    r = entry.runtime_data
    sg = r.sg_boost.overview()
    return {"version": VERSION, "mode": r.mode, "device_count": len(r.configs),
            "recovery_count": len(r.recovery), "fault_count": len(r.faults),
            "pending": r.pending is not None, "meter_valid": r.grid_w is not None,
            "wallbox": {"enabled": r.wallbox_settings["enabled"],
                        "policy": "house_first" if r.others_first else "priority",
                        "learning": {k: v for k, v in r.learning_overview().items() if k not in ("profiles", "switch_entity", "reset_entity")},
                        "state": r.wallbox_guard.result.state,
                        "block_increase": r.wallbox_guard.result.block_increase,
                        "possible_interactions": r.wallbox_guard.conflict_count},
            "panasonic": {"configured": r.panasonic.configured, "read_only": True,
                          "power_scope": r.panasonic.settings.get("power_scope", "unconfirmed"),
                          "power_meter": bool(r.panasonic.settings.get("power_entity")),
                          "zone_count": len(r.panasonic.settings.get("zone_entities", []))},
            "sg_boost": {key: sg.get(key) for key in (
                "configured", "enabled", "state", "desired_on", "relay_on",
                "action_required", "commissioning_confirmed", "watchdog_confirmed")},
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
