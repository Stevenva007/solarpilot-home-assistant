"""Manual Panasonic intent and per-zone climate ownership regressions."""
from copy import deepcopy
from datetime import datetime, timezone
import time
from types import SimpleNamespace
from zoneinfo import ZoneInfo

import pytest

from custom_components.solar_pilot import thermal_runtime as runtime_module
from custom_components.solar_pilot.thermal_climate import ClimateDecision
from test_thermal_runtime import ClimateServices, mature, setup_climate


ZONE = ZoneInfo("Europe/Brussels")


def climate_calls(hass):
    return [call for call in hass.services.calls if call[0] == "climate"]


class QuietCloudServices(ClimateServices):
    """Accept a command without inventing an optimistic HA state update."""
    async def async_call(self, domain, action, data=None, blocking=False, **kwargs):
        if domain == "climate" and action == "set_hvac_mode":
            self.calls.append((domain, action, data))
            return None
        return await super().async_call(domain, action, data, blocking, **kwargs)


class EventCloudServices(QuietCloudServices):
    def __init__(self, states, handler):
        super().__init__(states)
        self.handler = handler

    async def async_call(self, domain, action, data=None, blocking=False, **kwargs):
        result = await super().async_call(domain, action, data, blocking, **kwargs)
        if domain == "climate" and action == "set_hvac_mode":
            self.handler(data, kwargs.get("context"))
        return result


def clock(monkeypatch, hass):
    # Whole seconds keep precise +10 s confirmations independent of datetime's
    # microsecond rounding, while exercising the actual report-delay boundary.
    wall = [float(int(time.time()))]
    monkeypatch.setattr(time, "time", lambda: wall[0])

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime.fromtimestamp(wall[0], tz or timezone.utc)

    monkeypatch.setattr(runtime_module, "datetime", Clock)
    original_set = hass.states.set

    def set_state(entity_id, state, attrs=None, age=0, reported_age=None):
        original_set(entity_id, state, attrs, age, reported_age)
        obj = hass.states.get(entity_id)
        obj.last_updated = datetime.fromtimestamp(wall[0] - age, timezone.utc)
        obj.last_reported = datetime.fromtimestamp(
            wall[0] - (reported_age if reported_age is not None else age), timezone.utc)

    hass.states.set = set_state
    for entity_id, obj in list(hass.states.data.items()):
        set_state(entity_id, obj.state, obj.attributes)
    return wall


def forecast(hass, wall, temperature=21):
    hass.services.forecast = [{
        "datetime": datetime.fromtimestamp(wall + (hour + 1) * 3600, ZONE).isoformat(),
        "temperature": temperature, "condition": "partlycloudy", "humidity": 60,
    } for hour in range(48)]


def report(hass, entity_id, mode=None, **attrs):
    obj = hass.states.get(entity_id)
    hass.states.set(entity_id, mode or obj.state, {**obj.attributes, **attrs})


def user_mode_event(manager, entity_id, mode):
    manager.on_service_event(SimpleNamespace(
        data={"domain": "climate", "service": "set_hvac_mode", "service_data": {
            "entity_id": entity_id, "hvac_mode": mode,
        }},
        context=SimpleNamespace(user_id="test_user", id="user-mode-event", parent_id=None),
    ))


async def tick(manager, wall):
    return await manager.tick(local_now=datetime.fromtimestamp(wall, ZONE), allow_command=True)


@pytest.mark.asyncio
@pytest.mark.parametrize("temperature", [19.5, 23])
async def test_unowned_manual_off_never_wakes_at_cold_or_hot_comfort_breach(
        monkeypatch, temperature):
    runtime, hass = setup_climate(control=True, temp=temperature, target=21, mode="off")
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])

    await tick(runtime.smart_climate, wall[0])

    assert not climate_calls(hass)
    assert hass.states.get("climate.home").state == "off"
    assert hass.states.get("climate.salon").state == "off"
    assert hass.states.get("climate.home").attributes["temperature"] == 21


@pytest.mark.asyncio
async def test_salon_23_target_21_and_living_22_both_preserve_user_off(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=22, target=21, mode="off")
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    report(hass, "climate.salon", current_temperature=23)

    await tick(runtime.smart_climate, wall[0])

    assert not climate_calls(hass)
    assert hass.states.get("climate.salon").state == "off"
    assert hass.states.get("climate.home").state == "off"


@pytest.mark.asyncio
async def test_user_off_eleven_seconds_after_confirmed_auto_is_respected_even_if_cold(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=21, target=21, mode="auto")
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    report(hass, "climate.home", "off", current_temperature=19.5)
    manager = runtime.smart_climate
    manager.state.expected_mode = {"climate.home": "off"}
    await tick(manager, wall[0])
    assert hass.states.get("climate.home").state == "auto"
    wall[0] += 10
    report(hass, "climate.home", "auto")
    await tick(manager, wall[0])  # Fresh later AUTO acknowledgement.
    hass.services.calls.clear()

    wall[0] += 1
    report(hass, "climate.home", "off", current_temperature=19.5)
    await tick(manager, wall[0])
    await tick(manager, wall[0])

    assert not climate_calls(hass)
    assert hass.states.get("climate.home").state == "off"
    assert "climate.home" not in manager.state.expected_mode
    assert "climate.home" in manager.manual_off
    assert manager.zone_holds["climate.home"] > wall[0]


@pytest.mark.asyncio
async def test_cached_hard_decision_inside_current_band_cannot_bypass_manual_hold(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=21, target=21, mode="auto")
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    report(hass, "climate.home", "off")
    manager = runtime.smart_climate
    manager.state.expected_mode = {"climate.home": "off"}
    manager.state.last_decision = ClimateDecision(
        "auto", "Vorige harde comfortgrens", hard_override=True,
        comfort_direction="heating")
    manager.state.last_decision_wall = wall[0]
    manager.state.last_guard_wall = wall[0]
    manager.state.manual_hold_until = wall[0] + 3600

    await tick(manager, wall[0])

    assert not climate_calls(hass)
    assert hass.states.get("climate.home").state == "off"


@pytest.mark.asyncio
@pytest.mark.parametrize("waiting_s", [40, 200])
async def test_cloud_off_without_auto_echo_never_repeats_release_command(monkeypatch, waiting_s):
    runtime, hass = setup_climate(control=True, temp=21, target=21, mode="auto")
    hass.services = QuietCloudServices(hass.states)
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    report(hass, "climate.home", "off", current_temperature=19.5)
    manager = runtime.smart_climate
    manager.state.expected_mode = {"climate.home": "off"}

    await tick(manager, wall[0])
    for _ in range(waiting_s // 5):
        wall[0] += 5
        await tick(manager, wall[0])

    assert climate_calls(hass) == [
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "auto"}),
    ]
    assert hass.states.get("climate.home").state == "off"
    if waiting_s > 180:
        assert "climate.home" not in manager.pending_commands
        assert "climate.home" in manager.manual_off


@pytest.mark.asyncio
async def test_explicit_user_off_wins_while_auto_command_has_no_cloud_echo(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=21, target=21, mode="auto")
    hass.services = QuietCloudServices(hass.states)
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    report(hass, "climate.home", "off", current_temperature=19.5)
    manager = runtime.smart_climate
    manager.state.expected_mode = {"climate.home": "off"}
    await tick(manager, wall[0])

    # The reported zone is already OFF, so this explicit user action need not
    # produce a state-value transition. The service event must still win.
    user_mode_event(manager, "climate.home", "off")
    for _ in range(4):
        wall[0] += 5
        await tick(manager, wall[0])

    assert "climate.home" in manager.manual_off
    assert "climate.home" not in manager.pending_commands
    assert "climate.home" not in manager.state.expected_mode
    assert climate_calls(hass) == [
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "auto"}),
    ]
    assert hass.states.get("climate.home").state == "off"


@pytest.mark.asyncio
async def test_own_context_mode_echo_does_not_create_manual_off_intent(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=21, target=21, mode="auto")
    wall = clock(monkeypatch, hass)
    manager = runtime.smart_climate
    report(hass, "climate.home", "off", current_temperature=19.5)
    manager.state.expected_mode = {"climate.home": "off"}

    def own_echo(data, context):
        entity_id = data["entity_id"]
        previous = deepcopy(hass.states.get(entity_id))
        report(hass, entity_id, data["hvac_mode"])
        current = hass.states.get(entity_id)
        current.context = context
        manager.on_event(SimpleNamespace(data={
            "entity_id": entity_id, "old_state": previous, "new_state": current,
        }, context=context))

    hass.services = EventCloudServices(hass.states, own_echo)
    forecast(hass, wall[0])
    await tick(manager, wall[0])
    wall[0] += 10
    report(hass, "climate.home", "auto")
    await tick(manager, wall[0])

    assert "climate.home" not in manager.manual_off
    assert manager.zone_holds.get("climate.home", 0) <= wall[0]
    assert "climate.home" not in manager.pending_commands
    assert climate_calls(hass) == [
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "auto"}),
    ]


@pytest.mark.asyncio
async def test_user_off_during_service_yield_is_not_overwritten_after_call_returns(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=21, target=21, mode="auto")
    wall = clock(monkeypatch, hass)
    manager = runtime.smart_climate
    report(hass, "climate.home", "off", current_temperature=19.5)
    manager.state.expected_mode = {"climate.home": "off"}
    hass.services = EventCloudServices(hass.states,
        lambda _data, _context: user_mode_event(manager, "climate.home", "off"))
    forecast(hass, wall[0])

    await tick(manager, wall[0])
    await tick(manager, wall[0])

    assert "climate.home" in manager.manual_off
    assert "climate.home" not in manager.pending_commands
    assert "climate.home" not in manager.state.expected_mode
    assert "climate.home" in manager.snapshot()["manual_off"]
    assert climate_calls(hass) == [
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "auto"}),
    ]


@pytest.mark.asyncio
async def test_late_own_auto_echo_cannot_revoke_user_off_after_pending_command_cancel(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=21, target=21, mode="auto")
    wall = clock(monkeypatch, hass)
    manager = runtime.smart_climate
    report(hass, "climate.home", "off", current_temperature=19.5)
    manager.state.expected_mode = {"climate.home": "off"}
    captured = {}
    hass.services = EventCloudServices(hass.states,
        lambda _data, context: captured.update(context=context))
    forecast(hass, wall[0])
    await tick(manager, wall[0])
    user_mode_event(manager, "climate.home", "off")
    previous = deepcopy(hass.states.get("climate.home"))

    # A delayed response to the already-cancelled SolarPilot command is not a
    # second user AUTO choice, even if subsequent cloud refreshes lack context.
    wall[0] += 11
    report(hass, "climate.home", "auto")
    current = hass.states.get("climate.home")
    current.context = captured["context"]
    manager.on_event(SimpleNamespace(data={
        "entity_id": "climate.home", "old_state": previous, "new_state": current,
    }, context=captured["context"]))
    await tick(manager, wall[0])
    for _ in range(3):
        wall[0] += 5
        report(hass, "climate.home", "auto")
        await tick(manager, wall[0])

    # Expiry alone cannot turn the continuously observed cancelled response
    # into a new manual AUTO transition.
    wall[0] += 200
    report(hass, "climate.home", "auto")
    await tick(manager, wall[0])

    assert "climate.home" in manager.manual_off
    assert manager.zone_holds["climate.home"] > wall[0]
    assert "climate.home" not in manager.pending_commands
    assert "climate.home" not in manager.state.expected_mode
    assert climate_calls(hass) == [
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "auto"}),
    ]


@pytest.mark.asyncio
async def test_user_off_for_second_zone_while_first_call_yields_cancels_second_write(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=19.5, target=21, mode="off")
    wall = clock(monkeypatch, hass)
    manager = runtime.smart_climate
    manager.state.expected_mode = {"climate.home": "off", "climate.salon": "off"}
    hass.services = EventCloudServices(hass.states,
        lambda _data, _context: user_mode_event(manager, "climate.salon", "off"))
    forecast(hass, wall[0])

    await tick(manager, wall[0])

    assert "climate.salon" in manager.manual_off
    assert "climate.salon" not in manager.pending_commands
    assert "climate.salon" not in manager.state.expected_mode
    assert hass.states.get("climate.salon").state == "off"
    assert climate_calls(hass) == [
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "auto"}),
    ]


@pytest.mark.asyncio
async def test_pending_auto_journal_never_replays_command_after_manager_restart(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=21, target=21, mode="auto")
    hass.services = QuietCloudServices(hass.states)
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    report(hass, "climate.home", "off", current_temperature=19.5)
    manager = runtime.smart_climate
    manager.state.expected_mode = {"climate.home": "off"}
    await tick(manager, wall[0])
    saved = deepcopy(manager.snapshot())
    assert "climate.home" in saved["pending_commands"]

    other = runtime_module.SmartClimateManager(runtime)
    other.restore(saved)
    for _ in range(4):
        wall[0] += 5
        await tick(other, wall[0])

    assert climate_calls(hass) == [
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "auto"}),
    ]
    assert hass.states.get("climate.home").state == "off"


@pytest.mark.asyncio
async def test_per_zone_manual_off_hold_survives_manager_restart(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=21, target=21, mode="auto")
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    report(hass, "climate.home", "off", current_temperature=19.5)
    manager = runtime.smart_climate
    manager.state.expected_mode = {"climate.home": "off"}
    await tick(manager, wall[0])
    wall[0] += 10
    report(hass, "climate.home", "auto")
    await tick(manager, wall[0])
    wall[0] += 1
    report(hass, "climate.home", "off", current_temperature=19.5)
    await tick(manager, wall[0])
    saved = deepcopy(manager.snapshot())
    assert "climate.home" in saved["manual_off"]
    assert saved["zone_holds"]["climate.home"] > wall[0]

    other = runtime_module.SmartClimateManager(runtime)
    other.restore(saved)
    hass.services.calls.clear()
    await tick(other, wall[0])

    assert not climate_calls(hass)
    assert hass.states.get("climate.home").state == "off"
    assert "climate.home" not in other.state.expected_mode
    assert "climate.home" in other.manual_off
    assert other.zone_holds["climate.home"] == saved["zone_holds"]["climate.home"]


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid", [
    "missing", "unavailable", "restored", "stale", "future", "missing_stamp", "wrong_unit",
])
async def test_invalid_selected_zone_blocks_commands_to_other_owned_zone(monkeypatch, invalid):
    runtime, hass = setup_climate(control=True, temp=19.5, target=21, mode="off")
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    manager = runtime.smart_climate
    manager.state.expected_mode = {"climate.home": "off", "climate.salon": "off"}
    obj = hass.states.get("climate.salon")
    if invalid == "missing":
        del hass.states.data["climate.salon"]
    elif invalid == "unavailable":
        hass.states.set("climate.salon", "unavailable")
    elif invalid == "restored":
        report(hass, "climate.salon", restored=True)
    elif invalid == "stale":
        hass.states.set("climate.salon", obj.state, obj.attributes, age=3601)
    elif invalid == "future":
        hass.states.set("climate.salon", obj.state, obj.attributes, age=-120)
    elif invalid == "missing_stamp":
        obj.last_updated = obj.last_reported = None
    else:
        report(hass, "climate.salon", temperature_unit="°F")

    await tick(manager, wall[0])

    assert not climate_calls(hass)
    assert manager.state.fault
    assert hass.states.get("climate.home").state == "off"


@pytest.mark.asyncio
async def test_owned_coast_release_preserves_other_zone_manual_off(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=19.5, target=21, mode="off")
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    manager = runtime.smart_climate
    manager.state.expected_mode = {"climate.home": "off"}

    await tick(manager, wall[0])

    assert climate_calls(hass) == [
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "auto"}),
    ]
    assert hass.states.get("climate.home").state == "auto"
    assert hass.states.get("climate.salon").state == "off"


@pytest.mark.asyncio
async def test_explicit_user_auto_returns_control_for_that_zone_only(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=21, target=21, mode="off")
    runtime.smart_climate.settings["solar_gain_enabled"] = False  # Ownership fixture without PV.
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    manager = runtime.smart_climate
    await tick(manager, wall[0])
    assert not climate_calls(hass)

    user_mode_event(manager, "climate.home", "auto")
    report(hass, "climate.home", "auto")
    mature(manager)
    manager.state.last_decision_wall = 0
    manager.state.last_guard_wall = 0
    await tick(manager, wall[0])

    assert climate_calls(hass) == [
        ("climate", "set_hvac_mode", {"entity_id": "climate.home", "hvac_mode": "off"}),
    ]
    assert hass.states.get("climate.salon").state == "off"
    assert "climate.home" not in manager.manual_off
    assert "climate.salon" in manager.manual_off


@pytest.mark.asyncio
async def test_owned_coast_can_return_to_auto_and_later_model_can_coast_again(monkeypatch):
    runtime, hass = setup_climate(control=True, temp=21, target=21, mode="auto")
    runtime.smart_climate.settings["solar_gain_enabled"] = False  # Ownership fixture without PV.
    wall = clock(monkeypatch, hass)
    forecast(hass, wall[0])
    manager = runtime.smart_climate
    manager.settings["zone_entities"] = ["climate.home"]
    mature(manager)
    await tick(manager, wall[0])
    assert hass.states.get("climate.home").state == "off"
    wall[0] += 10
    report(hass, "climate.home", "off")
    await tick(manager, wall[0])

    wall[0] += 1
    report(hass, "climate.home", current_temperature=19.5)
    await tick(manager, wall[0])
    assert hass.states.get("climate.home").state == "auto"
    wall[0] += 10
    report(hass, "climate.home", "auto")
    await tick(manager, wall[0])

    wall[0] += 25 * 3600
    for entity_id, obj in list(hass.states.data.items()):
        hass.states.set(entity_id, obj.state, obj.attributes)
    report(hass, "climate.home", current_temperature=21)
    forecast(hass, wall[0])
    await tick(manager, wall[0])

    assert [call[2]["hvac_mode"] for call in climate_calls(hass)] == ["off", "auto", "off"]
    assert hass.states.get("climate.home").state == "off"
    assert hass.states.get("climate.home").attributes["temperature"] == 21
