"""Bounded comparisons of recorded household water and appliance reports.

No water is assigned to an appliance. Counter intervals that only partly overlap
a comparison stay unassigned; flow is never integrated to fabricate litres.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import deque
from collections.abc import Mapping
import math
import re

_BINDING = re.compile(r"^[a-f0-9]{64}$")
_MAX_RESULTS = 128
_BREAKS = frozenset({"binding_changed", "counter_reset", "counter_gap", "clock_reversal",
                     "source_gap", "disabled", "restart", "collecting"})


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (float, int)):
        return None
    try:
        value = float(value)
    except (ValueError, OverflowError):
        return None
    return value if math.isfinite(value) else None


def _observation(row, captured_at, *, boolean=False):
    if not isinstance(row, Mapping):
        return None
    value, stamp, until = row.get("value"), _number(row.get("reported_at")), _number(row.get("valid_until"))
    if stamp is None or until is None or not 0 < stamp <= captured_at <= until:
        return None
    if boolean:
        return (value, stamp) if type(value) is bool else None
    value = _number(value)
    return (value, stamp) if value is not None and 0 <= value <= 100 else None


def correlate_water_history(detail):
    """Produce bounded, read-only comparisons from the selected day's evidence."""
    result = {"boiler_drops": [], "dishwasher_intervals": [], "truncated": False,
              "read_only": True, "scope": "household_water",
              "note": "Samenloop van bronrapporten; geen bewezen oorzaak, warmwaterliters of afwasmachineverbruik."}
    if not isinstance(detail, Mapping):
        return result
    rows = detail.get("intervals", [])
    rows = rows if isinstance(rows, list) else []
    valid = []
    for row in rows[:16384]:
        if not isinstance(row, Mapping):
            continue
        if row.get("reason") not in ("counter_delta", "cross_local_day"):
            continue
        start, end, volume = (_number(row.get(key)) for key in ("start", "end", "volume_l"))
        if start is not None and end is not None and volume is not None and 0 < start < end and volume >= 0:
            valid.append((start, end, volume))
    # The source model emits non-overlapping counter intervals. A malformed
    # overlapping record must not be double-counted by this optional comparison.
    intervals, previous_end = [], 0
    for row in sorted(valid):
        if row[0] >= previous_end:
            intervals.append(row)
            previous_end = row[1]
    starts, ends, volumes = [], [], []
    for start, end, volume in intervals:
        starts.append(start)
        ends.append(end)
        volumes.append(volume)

    def volume_between(start, end):
        low, high = bisect_left(starts, start), bisect_right(ends, end)
        if high <= low:
            return None
        try:
            value = math.fsum(volumes[low:high])
        except (OverflowError, ValueError):
            return None
        return value if math.isfinite(value) else None

    points = detail.get("points", [])
    points = points if isinstance(points, list) else []
    points = [row for row in points[:8192] if isinstance(row, Mapping)
              and _number(row.get("captured_at")) is not None]
    points.sort(key=lambda row: row["captured_at"])
    flow_times = []
    for row in points:
        flow = row.get("flow")
        if isinstance(flow, Mapping) and flow.get("fresh") is True:
            value, stamp, until = (_number(flow.get(key)) for key in ("value", "reported_at", "valid_until"))
            if (value is not None and value > 0 and stamp is not None and until is not None
                    and 0 < stamp <= row["captured_at"] <= until):
                flow_times.append(stamp)
    flow_times.sort()
    events = detail.get("events", [])
    events = events if isinstance(events, list) else []
    breaks, wash_breaks = [], []
    for event in events[:512]:
        if not isinstance(event, Mapping) or event.get("kind") not in _BREAKS:
            continue
        stamp = _number(event.get("at"))
        if stamp is None:
            continue
        role = event.get("source_role") if event["kind"] == "source_gap" else None
        # Only explicit new provenance narrows a gap. Old/unrecognized gap
        # evidence stays a barrier; it is never relabelled from today's setup.
        if role != "flow":
            breaks.append(stamp)
        if role not in ("flow", "boiler_temperature"):
            wash_breaks.append(stamp)
    breaks.sort()
    wash_breaks.sort()

    def broken(start, end, source_breaks):
        index = bisect_right(source_breaks, start)
        return index < len(source_breaks) and source_breaks[index] <= end

    drops, washing, count = deque(maxlen=_MAX_RESULTS), deque(maxlen=_MAX_RESULTS), 0
    # A monotonic deque keeps the highest fresh reference in the rolling
    # thirty-minute segment, with the earliest timestamp on equal peaks.
    # Each reference enters/leaves once; capture density cannot make this an
    # unbounded pair search on HA's event loop.
    temperatures = deque()
    temp_binding, last_temp, previous_wash = None, None, None
    temp_fence, last_temp_capture, last_break = 0, 0, 0
    for point in points:
        captured, binding = point["captured_at"], point.get("context_binding")
        if not isinstance(binding, str) or not _BINDING.fullmatch(binding):
            temperatures.clear()
            temp_fence = max(temp_fence, captured)
            temp_binding = last_temp = previous_wash = None
            last_temp_capture = captured
            continue
        if temp_binding is not None and temp_binding != binding:
            temperatures.clear()
            temp_fence = max(temp_fence, last_temp_capture)
            last_temp = None
        temp_binding = binding
        last_temp_capture = captured
        event_index = bisect_right(breaks, captured)
        relevant_break = breaks[event_index-1] if event_index else 0
        if relevant_break > last_break:
            temperatures.clear()
            last_temp = None
            temp_fence = max(temp_fence, relevant_break)
            last_break = relevant_break
        context = point.get("context")
        context = context if isinstance(context, Mapping) else {}
        boiler = context.get("boiler")
        boiler = boiler if isinstance(boiler, Mapping) else {}
        temperature = _observation(boiler.get("temperature"), captured)
        if temperature is None:
            temperatures.clear()
            last_temp = None
            temp_fence = max(temp_fence, captured)
        else:
            value, stamp = temperature
            if last_temp is not None and (stamp < last_temp[0] or stamp == last_temp[0] and value != last_temp[1]):
                temperatures.clear()
                temp_fence = max(temp_fence, last_temp[0])
                last_temp = None
            elif stamp <= temp_fence:
                temperatures.clear()
                last_temp = None
            elif last_temp is None or stamp > last_temp[0]:
                while temperatures and temperatures[0][0] < stamp-1800:
                    temperatures.popleft()
                if temperatures and temperatures[0][1]-value >= 2:
                    old_stamp, old_value = temperatures[0]
                    volume = volume_between(old_stamp, stamp)
                    at = bisect_left(flow_times, old_stamp)
                    flow_seen = at < len(flow_times) and flow_times[at] <= stamp
                    drops.append({"start": old_stamp, "end": stamp,
                                  "temperature_start_c": old_value, "temperature_end_c": value,
                                  "drop_c": old_value-value, "observed_volume_l": volume,
                                  "volume_partial": True, "water_observed": True if flow_seen or volume and volume > 0 else None,
                                  "flow_observed": flow_seen})
                    count += 1
                    # The endpoint may anchor the next decline. Everything
                    # before it is consumed, so output windows never overlap.
                    temperatures.clear()
                while temperatures and temperatures[-1][1] < value:
                    temperatures.pop()
                temperatures.append((stamp, value))
                last_temp = stamp, value
        dish = _observation(context.get("dishwasher"), captured, boolean=True)
        if dish is None or dish[0] is not True:
            previous_wash = None
        else:
            stamp = dish[1]
            if previous_wash is not None:
                old_binding, old_stamp = previous_wash
                if binding == old_binding and 0 < stamp-old_stamp <= 300 and not broken(old_stamp, stamp, wash_breaks):
                    volume = volume_between(old_stamp, stamp)
                    if volume is not None and volume > 0:
                        washing.append({"start": old_stamp, "end": stamp, "observed_volume_l": volume,
                                        "volume_partial": True, "scope": "household_during_observed_dishwasher"})
                        count += 1
            previous_wash = binding, stamp
    result.update(boiler_drops=list(drops), dishwasher_intervals=list(washing),
                  truncated=count > len(drops)+len(washing))
    return result
