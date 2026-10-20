"""Small read-only coverage projection for the configured water detectors.

An available counter never refreshes a separate flow or leak report. These
diagnostics describe usable detector inputs, not a completed duration or proof
that the installation is free from leaks.
"""
from __future__ import annotations

from collections.abc import Mapping
import math


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    try:
        result = float(value)
    except (ValueError, OverflowError):
        return None
    return result if math.isfinite(result) else None


def water_monitor_diagnostic(view, settings):
    """Describe only the current detached snapshot, with no sampling or writes."""
    view = view if isinstance(view, Mapping) else {}
    settings = settings if isinstance(settings, Mapping) else {}
    enabled = settings.get("enabled") is True
    now = _number(view.get("observed_at"))

    def channel(role, option, *, boolean=False):
        configured = isinstance(settings.get(option), str) and bool(settings[option])
        raw = view.get(role)
        raw = raw if isinstance(raw, Mapping) else {}
        reported, until = (_number(raw.get(key)) for key in ("reported_at", "valid_until"))
        value = raw.get("value")
        valid_value = type(value) is bool if boolean else _number(value) is not None and value >= 0
        valid_times = (now is not None and reported is not None and until is not None
                       and 0 < reported <= until and reported <= now+5 and now <= until)
        current = bool(enabled and configured and raw.get("fresh") is True and valid_value and valid_times)
        reason = ("monitoring_disabled" if not enabled else "not_configured" if not configured else
                  "current" if current else "invalid")
        if enabled and configured and not current:
            supplied = raw.get("reason")
            if isinstance(supplied, str) and supplied and supplied != "current" and len(supplied) <= 80:
                reason = supplied
        return {"configured": configured, "current": current, "reason": reason,
                "reported_at": reported, "valid_until": until}

    flow = channel("flow", "flow_entity")
    leak = channel("native_leak", "leak_entity", boolean=True)
    selected = [row for row in (flow, leak) if row["configured"]]
    if not enabled:
        state, code, summary = ("disabled", "monitoring_disabled", "De watermonitor staat uit.")
    elif not selected:
        state, code, summary = ("not_configured", "detectors_not_configured",
                                "Geen bron voor stromingsbewaking of een eigen lekmelding gekoppeld.")
    elif all(row["current"] for row in selected):
        state, code, summary = ("current", "detector_sources_current",
                                "De gekoppelde bewakingsbronnen hebben actuele bruikbare rapporten.")
    elif any(row["current"] for row in selected):
        state, code, summary = ("incomplete", "detector_sources_incomplete",
                                "Een deel van de gekoppelde waterbewaking mist actuele bruikbare rapporten.")
    else:
        state, code, summary = ("unavailable", "detector_sources_unavailable",
                                "De gekoppelde waterbewaking mist actuele bruikbare rapporten.")
    return {"schema": 1, "read_only": True, "state": state, "code": code, "summary": summary,
            "flow_monitoring": flow, "native_leak_monitoring": leak,
            "continuous_flow_ready": flow["current"], "native_leak_ready": leak["current"],
            "note": "Actuele brongegevens bewijzen geen lekvrijheid of voltooide duurbevestiging. Een verse meterstand maakt een ander bronrapport niet actueel."}
