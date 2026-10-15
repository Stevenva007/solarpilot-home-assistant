"""Live controls and private analysis share the authoritative deadline journal."""
import pytest

from test_sensor_recorder59 import sensor, recorder_payload
from test_wallbox_priority88 import ready


@pytest.mark.asyncio
async def test_timed_priority_reaches_live_dashboard_and_export_without_recorder_clock_noise(monkeypatch):
    runtime, hass, clock = ready(monkeypatch)
    await runtime.async_set_wallbox_priority("global", "2h")
    clock.value += 73
    status = sensor(runtime, "status")
    live = status.extra_state_attributes
    choice = live["wallbox_priority"]["general"]
    assert choice["option"] == "2h"
    assert choice["remaining_s"] == 7200 - 73
    assert choice["expires_at"] == clock.value + choice["remaining_s"]
    assert "wallbox_priority" not in recorder_payload(status, live)

    exported = runtime.analysis.prepare(hours=1)
    assert exported["components"]["wallbox_priority"]["general"] == choice
    assert exported["components"]["runtime_and_models"]["wallbox_priority"] == runtime.wallbox_priority.snapshot()
    assert runtime.wallbox_priority.snapshot()["general"]["expires_at"] == choice["expires_at"]
    assert not hass.services.calls
