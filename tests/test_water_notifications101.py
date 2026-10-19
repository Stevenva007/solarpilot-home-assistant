"""Water notices follow fresh episode proof, with durable delivery deduplication."""
import asyncio
from copy import deepcopy
from types import SimpleNamespace as NS

import pytest

from custom_components.solar_pilot.water import WATER_DEFAULTS, WaterModel, source_reading
from custom_components.solar_pilot.water_notifications import WaterNotifications


def view(*, episode="a" * 24, cause="native_leak", active=True, current=True):
    return {"schema": 1, "read_only": True, "enabled": True,
            "alert": {"active": active, "cause": cause, "episode_id": episode,
                      "started_at": 1800000000, "last_evidence_at": 1800000000,
                      "evidence_current": current}}


class Services:
    def __init__(self):
        self.calls, self.successes = [], []
        self.available, self.fail = True, False
        self.entered = self.release = None

    def has_service(self, domain, service):
        assert domain == "persistent_notification" and service in ("create", "dismiss")
        return self.available

    async def async_call(self, domain, service, data, **kwargs):
        assert domain == "persistent_notification" and service in ("create", "dismiss")
        assert kwargs == {"blocking": False}
        self.calls.append((domain, service, deepcopy(data)))
        if self.entered is not None:
            self.entered.set()
            await self.release.wait()
        if self.fail:
            raise OSError("Notification transport unavailable")
        self.successes.append((domain, service, deepcopy(data)))


def setup():
    services = Services()
    saves = []
    water = NS(settings={**WATER_DEFAULTS, "enabled": True}, view=view(), reads=0)

    def overview():
        water.reads += 1
        return deepcopy(water.view)

    water.overview = overview
    runtime = NS(entry=NS(entry_id="example_entry"), water=water,
                 hass=NS(services=services), mode="observe", faults={},
                 sg={"lease": "unchanged"}, dishwasher={"ticket": "unchanged"})
    reporter = WaterNotifications(runtime)
    runtime.store = NS(async_delay_save=lambda callback, delay: saves.append((callback, delay)))
    runtime._snapshot = lambda: {"water_notifications": reporter.snapshot()}
    return runtime, services, saves, reporter


@pytest.mark.asyncio
@pytest.mark.parametrize("cause", ["native_leak", "continuous_flow", "both"])
async def test_fresh_episode_creates_one_dedicated_notice_without_controller_changes(cause):
    runtime, services, saves, reporter = setup()
    before = deepcopy((runtime.mode, runtime.faults, runtime.sg, runtime.dishwasher))
    proof = view(cause=cause)
    for _ in range(20):
        await reporter.sync(proof)
    assert len(services.calls) == 1 and services.calls[0][1] == "create"
    data = services.calls[0][2]
    assert data["notification_id"] == reporter.notification_id
    assert "Water" in data["message"] and "geen toestel" in data["message"]
    assert "example_entry" not in data["message"] and "a" * 24 not in data["message"]
    if cause == "continuous_flow":
        assert "geen fysiek lek vastgesteld" in data["message"]
        assert "watermeter meldt een mogelijk lek" not in data["message"]
    else:
        assert "watermeter meldt een mogelijk lek" in data["message"]
    assert deepcopy((runtime.mode, runtime.faults, runtime.sg, runtime.dishwasher)) == before
    assert reporter.snapshot()["delivered_episodes"] == ["a" * 24]
    assert [delay for _callback, delay in saves] == [1]


@pytest.mark.asyncio
async def test_pure_overview_default_path_has_no_source_or_controller_writes():
    runtime, services, _saves, reporter = setup()
    await reporter.sync()
    assert runtime.water.reads == 1
    assert services.calls[0][0:2] == ("persistent_notification", "create")


@pytest.mark.asyncio
@pytest.mark.parametrize("proof", [None, {}, [], {"alert": None},
    view(current=False), view(active=False, current=False),
    {**view(), "alert": {**view()["alert"], "active": 1}},
    {**view(), "alert": {**view()["alert"], "evidence_current": 1}},
    view(cause="pending"), view(cause="clear"), view(cause="unknown"), view(cause=[]),
    view(episode="bad"), view(episode="A" * 24), view(episode=None),
])
async def test_unknown_pending_malformed_or_stale_proof_cannot_create_or_clear(proof):
    runtime, services, _saves, reporter = setup()
    runtime.water.view = proof
    await reporter.sync(proof)
    assert not services.calls
    await reporter.sync(view())
    count = len(services.calls)
    runtime.water.view = proof
    await reporter.sync(proof)
    assert len(services.calls) == count and reporter.snapshot()["active"] is True


@pytest.mark.asyncio
async def test_fresh_resolution_dismisses_only_the_own_notice_and_keeps_episode_receipt():
    _runtime, services, _saves, reporter = setup()
    await reporter.sync(view())
    await reporter.sync(view(active=False))
    await reporter.sync(view(active=False))
    assert [call[1] for call in services.calls] == ["create", "dismiss"]
    assert services.calls[-1][2] == {"notification_id": reporter.notification_id}
    assert reporter.snapshot() == {"schema": 1, "active": False, "episode_id": None,
                                   "delivered_episodes": ["a" * 24]}
    # A stale/replayed activation of the same episode is not a new incident.
    await reporter.sync(view())
    assert len(services.calls) == 2
    await reporter.sync(view(episode="b" * 24))
    assert services.calls[-1][1] == "create"


@pytest.mark.asyncio
async def test_fresh_resolution_of_a_different_episode_cannot_dismiss_the_retained_notice():
    runtime, services, _saves, reporter = setup()
    await reporter.sync(view())
    restored = WaterNotifications(runtime)
    restored.restore(reporter.snapshot())
    await restored.sync(view(episode="b" * 24, active=False))
    assert [call[1] for call in services.calls] == ["create"]
    assert restored.snapshot()["active"] is True
    assert restored.snapshot()["episode_id"] == "a" * 24
    await restored.sync(view(active=False))
    assert [call[1] for call in services.calls] == ["create", "dismiss"]


@pytest.mark.asyncio
@pytest.mark.parametrize("field", ["enabled", "notifications"])
async def test_explicit_setting_off_dismisses_own_notice_without_reenabling_same_episode(field):
    runtime, services, _saves, reporter = setup()
    await reporter.sync(view())
    runtime.water.settings[field] = False
    await reporter.sync(view(current=False))
    await reporter.sync(view())
    assert [call[1] for call in services.calls] == ["create", "dismiss"]
    runtime.water.settings[field] = True
    await reporter.sync(view())
    assert len(services.calls) == 2
    await reporter.sync(view(episode="b" * 24))
    assert services.calls[-1][1] == "create"


@pytest.mark.asyncio
@pytest.mark.parametrize("field,value", [("enabled", None), ("enabled", 1),
                                        ("notifications", "true"), ("notifications", 0)])
async def test_unknown_settings_neither_authorize_delivery_nor_claim_resolution(field, value):
    runtime, services, _saves, reporter = setup()
    await reporter.sync(view())
    runtime.water.settings[field] = value
    await reporter.sync(view(active=False))
    await reporter.sync(view(episode="b" * 24))
    assert [call[1] for call in services.calls] == ["create"]


@pytest.mark.asyncio
@pytest.mark.parametrize("active_before_restart", [True, False])
async def test_restart_receipt_never_recreates_same_episode_even_when_ha_lost_the_notice(active_before_restart):
    runtime, services, _saves, reporter = setup()
    await reporter.sync(view())
    if not active_before_restart:
        await reporter.sync(view(active=False))
    receipt = reporter.snapshot()
    services.calls.clear()
    restored = WaterNotifications(runtime)
    restored.restore(receipt)
    await restored.sync(view(current=False))
    await restored.sync(view())
    await restored.sync(view(cause="both"))
    assert not services.calls
    assert restored.snapshot() == receipt
    await restored.sync(view(episode="b" * 24))
    assert [call[1] for call in services.calls] == ["create"]


@pytest.mark.asyncio
async def test_transport_retries_until_success_without_pausing_or_spamming_logs(caplog):
    runtime, services, _saves, reporter = setup()
    services.fail = True
    for _ in range(3):
        await reporter.sync(view())
    assert reporter.snapshot()["delivered_episodes"] == []
    assert len([row for row in caplog.records if "waterbericht" in row.message]) == 1
    services.fail = False
    await reporter.sync(view())
    await reporter.sync(view())
    assert len(services.calls) == 4 and len(services.successes) == 1
    services.fail = True
    await reporter.sync(view(active=False))
    assert reporter.snapshot()["active"] is True
    services.fail = False
    await reporter.sync(view(active=False))
    assert reporter.snapshot()["active"] is False
    assert runtime.mode == "observe" and runtime.faults == {}


@pytest.mark.asyncio
async def test_missing_service_waits_for_transport_without_consuming_episode():
    _runtime, services, _saves, reporter = setup()
    services.available = False
    await reporter.sync(view())
    assert not services.calls and not reporter.snapshot()["delivered_episodes"]
    services.available = True
    await reporter.sync(view())
    assert len(services.calls) == 1


@pytest.mark.asyncio
async def test_delivery_receipt_save_retry_does_not_send_another_notice():
    runtime, services, saves, reporter = setup()
    original = runtime.store.async_delay_save
    attempts = []

    def fail_once(callback, delay):
        attempts.append(delay)
        if len(attempts) == 1:
            raise OSError("Receipt scheduling unavailable")
        original(callback, delay)

    runtime.store.async_delay_save = fail_once
    await reporter.sync(view())
    assert reporter.snapshot()["active"] is True
    await reporter.sync(view(current=False))
    assert len(services.calls) == 1 and attempts == [1, 1]
    assert len(saves) == 1


@pytest.mark.asyncio
async def test_concurrent_sync_calls_cannot_deliver_the_same_episode_twice():
    _runtime, services, _saves, reporter = setup()
    services.entered, services.release = asyncio.Event(), asyncio.Event()
    first = asyncio.create_task(reporter.sync(view()))
    await services.entered.wait()
    second = asyncio.create_task(reporter.sync(view()))
    services.release.set()
    await asyncio.gather(first, second)
    assert len(services.calls) == 1


@pytest.mark.asyncio
async def test_delivery_ledger_records_the_episode_that_was_actually_submitted():
    _runtime, services, _saves, reporter = setup()
    services.entered, services.release = asyncio.Event(), asyncio.Event()
    mutable = view()
    task = asyncio.create_task(reporter.sync(mutable))
    await services.entered.wait()
    mutable["alert"]["episode_id"] = "b" * 24
    services.release.set()
    await task
    assert reporter.snapshot()["delivered_episodes"] == ["a" * 24]


@pytest.mark.parametrize("receipt", [None, [], {},
    {"schema": True, "active": True, "episode_id": "a" * 24, "delivered_episodes": ["a" * 24]},
    {"schema": 1, "active": 1, "episode_id": "a" * 24, "delivered_episodes": ["a" * 24]},
    {"schema": 1, "active": True, "episode_id": "b" * 24, "delivered_episodes": ["a" * 24]},
    {"schema": 1, "active": False, "episode_id": "a" * 24, "delivered_episodes": ["a" * 24]},
    {"schema": 1, "active": True, "episode_id": "a" * 24, "delivered_episodes": ["a" * 24] * 2},
    {"schema": 1, "active": False, "episode_id": None, "delivered_episodes": [None]},
    {"schema": 1, "active": False, "episode_id": None, "delivered_episodes": ["A" * 24]},
])
def test_malformed_receipt_cannot_hide_a_new_water_episode(receipt):
    _runtime, _services, _saves, reporter = setup()
    initial = reporter.snapshot()
    reporter.restore(receipt)
    assert reporter.snapshot() == initial


@pytest.mark.asyncio
async def test_receipts_are_bounded_and_detached_from_snapshot_and_restore_inputs():
    runtime, _services, _saves, reporter = setup()
    for index in range(520):
        await reporter.sync(view(episode=f"{index:024x}"))
    receipt = reporter.snapshot()
    assert len(receipt["delivered_episodes"]) == 512
    assert receipt["episode_id"] == f"{519:024x}"
    restored = WaterNotifications(runtime)
    restored.restore(receipt)
    receipt["delivered_episodes"].clear()
    assert len(restored.snapshot()["delivered_episodes"]) == 512
    snapshot = restored.snapshot()
    snapshot["delivered_episodes"].clear()
    assert len(restored.snapshot()["delivered_episodes"]) == 512


def model_readings(stamp, *, leak=None, flow=None):
    result = {"volume": source_reading(None, "volume", stamp, 300, configured=False)}
    for role, value, attributes in (
            ("native_leak", leak, {"device_class": "moisture"}),
            ("flow", flow, {"device_class": "volume_flow_rate", "unit_of_measurement": "L/min"})):
        obj = NS(state=value, attributes=attributes, last_reported=stamp) if value is not None else None
        result[role] = source_reading(obj, role, stamp, 300, configured=value is not None)
    return result


@pytest.mark.asyncio
async def test_actual_model_stale_old_resolution_cannot_dismiss_until_new_fresh_clear():
    runtime, services, _saves, reporter = setup()
    model = WaterModel({"enabled": True, "leak_entity": "binary_sensor.example_leak"})
    runtime.water.settings = model.settings
    start = 1800000000
    model.observe(model_readings(start, leak="on"), start, binding="original")
    await reporter.sync(model.overview(start))
    model.observe(model_readings(start+60, leak="off"), start+60, binding="original")
    assert model.overview(start+60)["alert"]["active"] is False
    # The reporter did not run while the positive clearing report was current.
    await reporter.sync(model.overview(start+1000))
    assert [call[1] for call in services.calls] == ["create"]
    model.observe(model_readings(start+1001, leak="off"), start+1001, binding="original")
    await reporter.sync(model.overview(start+1001))
    assert [call[1] for call in services.calls] == ["create", "dismiss"]


@pytest.mark.asyncio
async def test_actual_model_rebound_sensor_off_does_not_clear_old_source_incident():
    runtime, services, _saves, reporter = setup()
    model = WaterModel({"enabled": True, "leak_entity": "binary_sensor.example_leak"})
    runtime.water.settings = model.settings
    start = 1800000000
    model.observe(model_readings(start, leak="on"), start, binding="original")
    await reporter.sync(model.overview(start))
    original_episode = model.overview(start)["alert"]["episode_id"]
    model.observe(model_readings(start+60, leak="off"), start+60, binding="different-source")
    await reporter.sync(model.overview(start+60))
    assert [call[1] for call in services.calls] == ["create"]
    model.observe(model_readings(start+90, leak="on"), start+90, binding="different-source")
    proof = model.overview(start+90)
    assert proof["alert"]["episode_id"] != original_episode
    await reporter.sync(proof)
    assert [call[1] for call in services.calls] == ["create", "create"]


@pytest.mark.asyncio
async def test_actual_flow_model_pending_gap_and_zero_remain_distinct_notification_states():
    runtime, services, _saves, reporter = setup()
    model = WaterModel({"enabled": True, "flow_entity": "sensor.example_flow", "continuous_flow_minutes": 1})
    runtime.water.settings = model.settings
    start = 1800000000
    for offset in (0, 30):
        model.observe(model_readings(start+offset, flow="0.2"), start+offset, binding="same-source")
        await reporter.sync(model.overview(start+offset))
    assert not services.calls
    model.observe(model_readings(start+60, flow="0.2"), start+60, binding="same-source")
    await reporter.sync(model.overview(start+60))
    assert [call[1] for call in services.calls] == ["create"]
    await reporter.sync(model.overview(start+400))
    model.observe(model_readings(start+400, flow="0.2"), start+400, binding="same-source")
    await reporter.sync(model.overview(start+400))
    assert [call[1] for call in services.calls] == ["create"]
    model.observe(model_readings(start+430, flow="0"), start+430, binding="same-source")
    await reporter.sync(model.overview(start+430))
    assert [call[1] for call in services.calls] == ["create", "dismiss"]


@pytest.mark.asyncio
async def test_actual_model_and_delivery_restore_require_new_episode_for_another_notice():
    runtime, services, _saves, reporter = setup()
    settings = {"enabled": True, "leak_entity": "binary_sensor.example_leak"}
    model = WaterModel(settings)
    runtime.water.settings = model.settings
    start = 1800000000
    model.observe(model_readings(start, leak="on"), start, binding="same-source")
    await reporter.sync(model.overview(start))
    restored_model = WaterModel(settings)
    assert restored_model.restore(model.snapshot(), start+30) is True
    restored_reporter = WaterNotifications(runtime)
    restored_reporter.restore(reporter.snapshot())
    await restored_reporter.sync(restored_model.overview(start+30))
    restored_model.observe(model_readings(start+60, leak="on"), start+60, binding="same-source")
    await restored_reporter.sync(restored_model.overview(start+60))
    assert [call[1] for call in services.calls] == ["create"]
    restored_model.observe(model_readings(start+90, leak="off"), start+90, binding="same-source")
    await restored_reporter.sync(restored_model.overview(start+90))
    restored_model.observe(model_readings(start+120, leak="on"), start+120, binding="same-source")
    await restored_reporter.sync(restored_model.overview(start+120))
    assert [call[1] for call in services.calls] == ["create", "dismiss", "create"]

