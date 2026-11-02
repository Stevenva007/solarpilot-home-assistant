"""A monitored battery's explicitly bound meter device has no SG writer.

These are native transport doubles, with no network or real Home Assistant.
"""
import asyncio
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot.sg_boost import SGBoostManager
from custom_components.solar_pilot.sg_transport import ShellyLeaseError
from test_marstek_authority113 import monitor_profile
from test_sg_transport62 import native, writes  # noqa: F401


def manager_for(native, *, same_device=True, enabled=True):
    native.rows["sensor.monitor_ac"] = SimpleNamespace(
        entity_id="sensor.monitor_ac", platform="shelly", disabled_by=None,
        device_id="public-relay-device" if same_device else "different-device",
        config_entry_id="public-shelly-entry", unique_id="fictional-ac-meter",
    )
    runtime = SimpleNamespace(
        hass=native.hass,
        entry=SimpleNamespace(options={
            "sg_boost": {"entity_id": "switch.public_sg"},
            "batteries": [monitor_profile(enabled=enabled, soc_entity="")],
        }),
    )
    return SGBoostManager(runtime)


async def send(adapter, on):
    return await adapter.set_on(300) if on else await adapter.set_off()


@pytest.mark.asyncio
@pytest.mark.parametrize("on", [False, True])
@pytest.mark.parametrize("enabled", [False, True])
async def test_native_sg_manager_protects_monitor_device_for_both_commands(
    native, on, enabled,
):
    manager = manager_for(native, enabled=enabled)
    adapter = manager._transport()
    assert adapter.before_write is not None
    with pytest.raises(ShellyLeaseError) as error:
        await send(adapter, on)
    assert error.value.code == "dispatch_changed"
    assert error.value.command_attempted is False
    assert writes(native) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("on", [False, True])
async def test_native_sg_checks_monitor_binding_after_async_preflight(native, on):
    manager = manager_for(native, same_device=False)
    adapter = manager._transport()
    assert adapter.before_write() is True
    original_rpc = native.device.call_rpc

    async def rebind_during_read(method, params=None, timeout=None):
        result = await original_rpc(method, params=params, timeout=timeout)
        if method == "Shelly.GetDeviceInfo":
            await asyncio.sleep(0)
            native.rows["sensor.monitor_ac"].device_id = "public-relay-device"
        return result

    native.device.call_rpc = rebind_during_read
    with pytest.raises(ShellyLeaseError) as error:
        await send(adapter, on)
    assert error.value.code == "dispatch_changed"
    assert error.value.command_attempted is False
    assert writes(native) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("on", [False, True])
async def test_unrelated_native_sg_remains_available(native, on):
    manager = manager_for(native, same_device=False)
    status = await send(manager._transport(), on)
    assert status["output"] is on
    assert len(writes(native)) == 1
    assert writes(native)[0][1]["on"] is on


@pytest.mark.asyncio
@pytest.mark.parametrize("on", [False, True])
@pytest.mark.parametrize("callback_kind", ["raises", "awaitable"])
async def test_native_write_guard_failure_does_not_attempt_rpc(
    native, on, callback_kind,
):
    def raises():
        raise RuntimeError("Fictional authority lookup failure")

    async def awaitable():
        return True

    native.adapter.before_write = raises if callback_kind == "raises" else awaitable
    with pytest.raises(ShellyLeaseError) as error:
        await send(native.adapter, on)
    assert error.value.code == "dispatch_changed"
    assert error.value.command_attempted is False
    assert writes(native) == []
