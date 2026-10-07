"""SolarPilot constants. No network or third-party Python dependencies."""
DOMAIN = "solar_pilot"
NAME = "SolarPilot"
VERSION = "1.0.0-beta.61"
PLATFORMS = ["sensor", "binary_sensor", "select", "number", "button", "switch"]
MODES = ["observe", "solar", "paused"]
DEVICE_MODES = ["auto", "disabled"]
DEFAULTS = {
    "grid_sign": "import_positive", "reserve_w": 150.0,
    "max_import_w": 3500.0, "interval_s": 5,
    "settle_s": 15, "stale_s": 120, "filter_s": 15,
    "fault_grace_s": 30, "battery_sign": "discharge_positive",
    "battery_min_soc": 0.0,
}
DEVICE_DEFAULTS = {
    "kind": "switch", "priority": 50, "nominal_w": 1000.0,
    "min_units": 6.0, "max_units": 16.0, "step_units": 1.0,
    "watts_per_unit": 230.0, "start_delay_s": 60,
    "stop_delay_s": 60, "min_on_s": 180, "min_off_s": 180,
    "start_margin_w": 100.0, "ack_timeout_s": 60,
    "manual_hold_s": 3600, "max_on_s": 14400,
    "min_daily_runtime_s": 0, "max_daily_runtime_s": 0,
    "daily_deadline": "23:59:00", "deadline_grid_allowed": False,
    "non_interruptible": False, "allow_wallbox_reclaim": False,
    "time_window_enabled": False, "time_window_start": "00:00:00",
    "time_window_end": "23:59:00",
    "forecast_deferrable": False, "cheap_grid_allowed": False,
    "daily_energy_goal_kwh": 0.0,
    "cycle_learning_enabled": False, "cycle_energy_kwh": 0.0,
    "cycle_duration_min": 0.0, "cycle_program": "standaard",
    "cycle_program_entity": "",
    "phase_hint": "auto",
    "wallbox_precedence": "global",
}
