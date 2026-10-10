"""Native Shelly protocol/binding doubles; no real HA or hardware commissioning.

The fictitious MAC and entity IDs below are public test data. The fixture models
the official coordinator's already-authenticated call_rpc transport rather than
pretending that generic switch services support a native local lease.
"""
import asyncio
from copy import deepcopy
import sys
from types import ModuleType, SimpleNamespace

import pytest
from homeassistant.helpers import entity_registry as er

from custom_components.solar_pilot.sg_transport import (
    ShellyLeaseAdapter, ShellyLeaseError, shelly_mapping_error,
)


class NativeRPCDevice:
    def __init__(self):
        self.calls = []
        self.clock = 1000.0
        self.output = False
        self.started = self.duration = None
        self.info = {"id": "shelly1g4-020000000001", "mac": "020000000001",
                     "gen": 4, "model": "S4SW-001X16EU", "ver": "1.7.0",
                     "fw_id": "public-fixture/1.7.0", "app": "S1G4"}
        self.config = {"id": 0, "in_mode": "detached", "initial_state": "off", "auto_on": False}
        self.error_method = None
        self.errors = []
        self.refresh = True
        self.reject_output = False
        self.bad_status = {}
        self.invalid_ack = False
        self.fail_read_after_set = False
        self.did_set = False
        self.pause_read = self.release_read = None

    async def call_rpc(self, method, params=None, timeout=None):
        self.calls.append((method, deepcopy(params), timeout))
        if method == self.error_method:
            raise ConnectionError("private-host-and-credential-must-not-appear-in-UI")
        if method == "Shelly.GetDeviceInfo":
            return deepcopy(self.info)
        if method == "Switch.GetConfig":
            return deepcopy(self.config)
        if method == "Sys.GetStatus":
            return {"unixtime": self.clock}
        if method == "Switch.GetStatus":
            if self.pause_read is not None:
                self.pause_read.set()
                await self.release_read.wait()
                self.pause_read = None
            if self.did_set and self.fail_read_after_set:
                raise ConnectionError("readback unavailable")
            status = {"id": 0, "output": self.output, "errors": list(self.errors)}
            if self.started is not None:
                status.update(timer_started_at=self.started, timer_duration=self.duration)
            status.update(self.bad_status)
            return status
        if method == "Switch.Set":
            self.did_set = True
            was_on = self.output
            if not self.reject_output:
                self.output = params["on"]
            if params["on"] and self.refresh:
                self.started, self.duration = self.clock, params["toggle_after"]
            elif not params["on"]:
                self.started = self.duration = None
            return {"was_on": "invalid" if self.invalid_ack else was_on}
        raise AssertionError(f"unexpected RPC method {method}")


@pytest.fixture
def native(monkeypatch):
    device = NativeRPCDevice()
    coordinator = SimpleNamespace(device=device, mac="02:00:00:00:00:01")
    entry = SimpleNamespace(platform="shelly", device_id="public-relay-device",
                            config_entry_id="public-shelly-entry", disabled_by=None,
                            unique_id="02:00:00:00:00:01-switch:0")
    rows = {"switch.public_sg": entry}
    monkeypatch.setattr(er, "async_get", lambda hass: SimpleNamespace(async_get=rows.get))
    components = ModuleType("homeassistant.components")
    components.__path__ = []
    shelly = ModuleType("homeassistant.components.shelly")
    shelly.__path__ = []
    module = ModuleType("homeassistant.components.shelly.coordinator")
    resolutions = []

    def get_rpc_coordinator_by_device_id(hass, device_id):
        resolutions.append(device_id)
        return coordinator if device_id == "public-relay-device" else None

    module.get_rpc_coordinator_by_device_id = get_rpc_coordinator_by_device_id
    monkeypatch.setitem(sys.modules, components.__name__, components)
    monkeypatch.setitem(sys.modules, shelly.__name__, shelly)
    monkeypatch.setitem(sys.modules, module.__name__, module)
    hass = SimpleNamespace(services=SimpleNamespace(calls=[]))
    adapter = ShellyLeaseAdapter(hass, "switch.public_sg")
    return SimpleNamespace(device=device, coordinator=coordinator, entry=entry,
                           rows=rows, resolutions=resolutions, module=module,
                           hass=hass, adapter=adapter)


def writes(native):
    return [(method, params) for method, params, _timeout in native.device.calls if method == "Switch.Set"]


@pytest.mark.asyncio
async def test_off_read_has_explicit_missing_timer_without_inventing_water_power(native):
    status = await native.adapter.get_status()
    assert status["known"] and status["output"] is False and status["setup_valid"]
    assert status["timer_started_at"] is None and status["timer_duration"] is None
    assert status["lease_remaining_s"] is None and not status["lease_proven"]
    assert status["source"] == "homeassistant_shelly_rpc"
    assert status["fingerprint"]["model"] == "S4SW-001X16EU"
    assert status["fingerprint"]["component"] == "switch:0"
    assert not {"power_w", "tank_temperature", "current_temperature"}.intersection(status)
    assert writes(native) == [] and native.hass.services.calls == []
    assert native.resolutions == ["public-relay-device"]


@pytest.mark.asyncio
async def test_on_has_native_five_minute_lease_and_actual_readback(native):
    status = await native.adapter.set_on(300)
    assert status["output"] is True and status["lease_proven"]
    assert status["timer_expires_at"] == 1300 and status["lease_remaining_s"] == 300
    assert writes(native) == [("Switch.Set", {"id": 0, "on": True, "toggle_after": 300.0})]
    methods = [method for method, _params, _timeout in native.device.calls]
    assert methods[-3:] == ["Switch.Set", "Switch.GetStatus", "Sys.GetStatus"]
    assert all(timeout == 3.0 for _method, _params, timeout in native.device.calls)
    assert native.hass.services.calls == []


@pytest.mark.asyncio
async def test_renew_advances_timer_without_any_off_or_toggle(native):
    first = await native.adapter.set_output(True, lease_s=300)
    native.device.clock += 60
    second = await native.adapter.set_output(True, lease_s=300)
    assert second["timer_expires_at"] == first["timer_expires_at"] + 60
    assert len(writes(native)) == 2
    assert all(params["on"] is True for _method, params in writes(native))
    assert all("Toggle" not in method for method, _params, _timeout in native.device.calls)


@pytest.mark.asyncio
async def test_false_command_omits_timer_to_avoid_scheduling_a_future_on(native):
    await native.adapter.set_on(300)
    status = await native.adapter.set_output(False)
    assert status["output"] is False
    assert writes(native)[-1] == ("Switch.Set", {"id": 0, "on": False})


@pytest.mark.asyncio
@pytest.mark.parametrize("value", [True, False, 0, -1, 59, 601, float("inf"), float("nan"), "300", None])
async def test_invalid_lease_never_writes(native, value):
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(value)
    assert caught.value.code == "invalid_lease" and not caught.value.command_attempted
    assert native.device.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("on,lease", [(1, 300), ("on", 300), (True, None), (False, 300)])
async def test_set_output_is_explicit_and_typed(native, on, lease):
    with pytest.raises(ShellyLeaseError):
        await native.adapter.set_output(on, lease)
    assert native.device.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value,code", [
    ("platform", "mqtt", "unsupported_source"),
    ("device_id", "", "unverified_mapping"),
    ("config_entry_id", "", "unverified_mapping"),
    ("unique_id", "02:00:00:00:00:01-switch:1", "wrong_channel"),
    ("unique_id", "familiar-name-switch:0", "wrong_channel"),
    ("disabled_by", "user", "entity_disabled"),
])
async def test_registry_identity_not_friendly_name_selects_the_native_channel(native, field, value, code):
    setattr(native.entry, field, value)
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code == code and native.device.calls == []
    assert shelly_mapping_error(native.hass, "switch.public_sg")


@pytest.mark.asyncio
async def test_missing_official_loaded_coordinator_has_no_generic_fallback(native):
    native.module.get_rpc_coordinator_by_device_id = lambda hass, device_id: None
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.get_status()
    assert caught.value.code == "unavailable"
    assert native.device.calls == [] and native.hass.services.calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value,code", [
    ("gen", 3, "unsupported_device"), ("gen", "4", "unsupported_device"),
    ("model", "S4SW-001P16EU", "unsupported_device"),
    ("id", "shelly1g4-020000000002", "unsupported_device"),
    ("mac", "not-a-mac", "unsupported_device"),
    ("profile", "cover", "wrong_role"),
    ("ver", None, "firmware_unknown"), ("fw_id", "", "firmware_unknown"),
])
async def test_real_device_information_must_match_exact_supported_hardware(native, field, value, code):
    native.device.info[field] = value
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code == code and writes(native) == []


@pytest.mark.asyncio
async def test_mac_of_actual_device_must_equal_mac_from_registry_and_coordinator(native):
    native.device.info.update(id="shelly1g4-020000000002", mac="020000000002")
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code == "unverified_mapping" and writes(native) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("in_mode", "follow"), ("initial_state", "restore_last"), ("auto_on", True), ("id", 1)])
async def test_unsafe_local_settings_block_only_on_and_are_visible(native, field, value):
    native.device.config[field] = value
    status = await native.adapter.get_status()
    assert not status["setup_valid"] and status["configuration_error"]
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert not caught.value.command_attempted and writes(native) == []
    native.device.output = True
    assert (await native.adapter.set_off())["output"] is False
    assert writes(native) == [("Switch.Set", {"id": 0, "on": False})]


@pytest.mark.asyncio
async def test_firmware_change_requires_rechecking_lease_but_allows_same_contact_off(native):
    await native.adapter.get_status()
    native.device.info.update(ver="2.0.0", fw_id="public-fixture/2.0.0")
    status = await native.adapter.get_status()
    assert status["firmware"] == "2.0.0" and not status["setup_valid"]
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code == "configuration_invalid" and writes(native) == []
    assert (await native.adapter.set_off())["output"] is False


@pytest.mark.asyncio
async def test_binding_change_after_first_success_requires_new_verification(native):
    await native.adapter.get_status()
    native.entry.config_entry_id = "different-public-entry"
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code == "binding_changed" and writes(native) == []


@pytest.mark.asyncio
async def test_device_clock_proves_lease_even_if_its_time_differs_from_ha_clock(native):
    native.device.clock = 456789.0
    status = await native.adapter.set_on(300)
    assert status["lease_remaining_s"] == 300 and status["lease_proven"]


@pytest.mark.asyncio
@pytest.mark.parametrize("clock", [None, float("nan"), 0, "1000"])
async def test_clock_unknown_does_not_grant_an_on_permission(native, clock):
    native.device.clock = clock
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code == "clock_unknown" and writes(native) == []


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [{"output": None}, {"output": "false"}, {"id": 1}])
async def test_unreadable_contact_is_explicit_unknown_never_assumed_off(native, status):
    native.device.bad_status = status
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.get_status()
    assert caught.value.code == "status_unknown" and writes(native) == []


@pytest.mark.asyncio
async def test_native_device_error_blocks_new_on_without_blocking_off(native):
    native.device.errors = ["overtemp"]
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code == "configuration_invalid" and writes(native) == []
    assert (await native.adapter.set_off())["output"] is False


@pytest.mark.asyncio
async def test_unleased_manual_on_is_not_taken_over(native):
    native.device.output = True
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code == "unleased_on" and writes(native) == []


@pytest.mark.asyncio
async def test_acknowledgement_is_not_physical_state_evidence(native):
    native.device.reject_output = True
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code == "lease_unconfirmed"
    assert caught.value.command_attempted and caught.value.command_applied
    assert len(writes(native)) == 1


@pytest.mark.asyncio
async def test_timer_not_refreshed_fails_without_off_on_workaround(native):
    await native.adapter.set_on(300)
    native.device.clock += 60
    native.device.refresh = False
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code in {"lease_unconfirmed", "lease_not_renewed"}
    assert len(writes(native)) == 2 and all(params["on"] for _method, params in writes(native))


@pytest.mark.asyncio
async def test_rpc_connection_failure_is_visible_bounded_and_not_replayed(native):
    native.device.error_method = "Switch.Set"
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code == "write_uncertain"
    assert caught.value.command_attempted and not caught.value.command_applied
    assert "private-host" not in str(caught.value)
    assert len(writes(native)) == 1


@pytest.mark.asyncio
async def test_lost_readback_retains_uncertain_ownership_and_does_not_resend(native):
    native.device.fail_read_after_set = True
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.command_attempted and caught.value.command_applied
    assert len(writes(native)) == 1


@pytest.mark.asyncio
async def test_registry_edit_while_reading_is_checked_before_the_write(native):
    native.device.pause_read = asyncio.Event()
    native.device.release_read = asyncio.Event()
    task = asyncio.create_task(native.adapter.set_on(300))
    await native.device.pause_read.wait()
    native.entry.unique_id = "02:00:00:00:00:02-switch:0"
    native.device.release_read.set()
    with pytest.raises(ShellyLeaseError):
        await task
    assert writes(native) == []


@pytest.mark.asyncio
async def test_firmware_fingerprint_is_stable_and_changes_on_upgrade(native):
    first = (await native.adapter.get_status())["fingerprint"]
    assert first == (await native.adapter.get_status())["fingerprint"]
    native.device.info.update(ver="2.0.0", fw_id="public-fixture/2.0.0")
    upgraded = await native.adapter.get_status()
    assert upgraded["fingerprint"] != first and not upgraded["setup_valid"]
    fresh_adapter = ShellyLeaseAdapter(native.hass, "switch.public_sg")
    # A fresh adapter exposes the new fingerprint; controller's persisted
    # commissioning must compare it with first before permitting ON.
    assert (await fresh_adapter.get_status())["fingerprint"] != first


@pytest.mark.asyncio
async def test_off_with_remaining_timer_does_not_claim_stable_normal_operation(native):
    native.device.bad_status = {"timer_started_at": 1000.0, "timer_duration": 300.0}
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_off()
    assert caught.value.code == "off_timer_active" and caught.value.command_applied
    assert writes(native) == [("Switch.Set", {"id": 0, "on": False})]


@pytest.mark.asyncio
async def test_final_policy_guard_refuses_on_after_async_preflight(native):
    native.adapter.before_on = lambda: False
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code == "dispatch_changed" and not caught.value.command_attempted
    assert any(method == "Sys.GetStatus" for method, _params, _timeout in native.device.calls)
    assert writes(native) == []


@pytest.mark.asyncio
async def test_policy_changed_while_native_read_awaits_is_checked_at_final_on_boundary(native):
    allowed = {"on": True}
    native.adapter.before_on = lambda: allowed["on"]
    native.device.pause_read = asyncio.Event()
    native.device.release_read = asyncio.Event()
    task = asyncio.create_task(native.adapter.set_on(300))
    await native.device.pause_read.wait()
    allowed["on"] = False
    native.device.release_read.set()
    with pytest.raises(ShellyLeaseError) as caught:
        await task
    assert caught.value.code == "dispatch_changed" and not caught.value.command_attempted
    assert writes(native) == []


@pytest.mark.asyncio
async def test_final_policy_guard_cannot_block_a_safe_off(native):
    native.adapter.before_on = lambda: False
    assert (await native.adapter.set_off())["output"] is False
    assert writes(native) == [("Switch.Set", {"id": 0, "on": False})]


@pytest.mark.asyncio
async def test_awaitable_policy_is_rejected_without_running_external_work(native):
    async def bad_callback():
        raise AssertionError("an async dispatch check must never be awaited")
    native.adapter.before_on = bad_callback
    with pytest.raises(ShellyLeaseError) as caught:
        await native.adapter.set_on(300)
    assert caught.value.code == "dispatch_changed" and writes(native) == []
