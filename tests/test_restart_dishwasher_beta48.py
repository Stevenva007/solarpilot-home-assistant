"""An uncertain START requires post-command native evidence after restart."""
import pytest

from test_dishwasher import setup
from test_dishwasher_runtime import arm


@pytest.mark.asyncio
@pytest.mark.parametrize("phase", ["Finished", "Washing"])
async def test_restart_old_appliance_phase_cannot_confirm_uncertain_start(phase):
    runtime, hass, cfg = setup()
    await arm(runtime)
    stored = runtime._snapshot()
    resumed, new_hass, new_cfg = setup()
    # Connectivity is current, but this appliance phase predates the saved
    # START intent. It cannot settle that command's outcome.
    new_hass.states.set("sensor.dw_phase", phase, reported_age=5)
    resumed.store.data = stored
    await resumed.start()
    assert resumed.dishwasher.tickets["a"]["attempted"]
    assert "a" in resumed.faults and "a" in resumed.recovery
    assert not [call for call in new_hass.services.calls if call[0] == "button"]
    # A genuine later appliance report resolves the same saved transaction.
    new_hass.states.set("sensor.dw_phase", phase)
    await resumed.tick()
    assert not resumed.dishwasher.tickets["a"]["attempted"]
    assert "a" not in resumed.faults and "a" not in resumed.recovery
    assert not [call for call in new_hass.services.calls if call[0] == "button"]
    await resumed.close()
