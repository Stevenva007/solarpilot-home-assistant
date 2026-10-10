"""SG notices are local and genuine faults survive a real HA restart."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot.action_notifications import ActionRequiredNotifications


class Services:
    def __init__(self):
        self.calls = []
        self.failure = False
        self.available = True

    def has_service(self, domain, service):
        return self.available

    async def async_call(self, domain, service, data, blocking=False):
        self.calls.append((domain, service, deepcopy(data)))
        if self.failure:
            raise RuntimeError("notification transport failed")


class Store:
    def __init__(self):
        self.calls = 0
        self.failure = False

    def async_delay_save(self, fn, delay):
        self.calls += 1
        if self.failure:
            raise RuntimeError("receipt store failed")


def runtime(view=None):
    services, store = Services(), Store()
    r = SimpleNamespace(
        entry=SimpleNamespace(entry_id="test-entry"),
        hass=SimpleNamespace(services=services, states=SimpleNamespace(get=lambda _: None)),
        store=store, _snapshot=lambda: {}, configs={}, faults={}, reclaim_blocks={},
        battery_fleet=SimpleNamespace(configs={}, state=SimpleNamespace(faults={})),
        problem_kind="", problem="", legacy_conflicts=lambda: [], pause_cause="",
        sg_boost=SimpleNamespace(overview=lambda: deepcopy(view or {})),
        # Retired controllers may appear in archived/mock input; never read them.
        dhw=SimpleNamespace(fault="old retired tank ACK", needs_review=True),
        smart_climate=SimpleNamespace(command_faults={"climate.test": "retired climate ACK"}),
    )
    r.notice = ActionRequiredNotifications(r)
    return r


@pytest.mark.parametrize("state", ["normal", "waiting_surplus", "rest", "blocked", "boost_requested"])
@pytest.mark.asyncio
async def test_routine_sg_states_and_retired_writers_do_not_create_notice(state):
    r = runtime({"state": state, "fault": "", "reason": "Routine condition", "action_required": False})
    await r.notice.sync()
    assert r.hass.services.calls == []
    assert r.notice.message() == ""


@pytest.mark.parametrize("flag", [None, False, 1, "true"])
def test_sg_notice_requires_exact_action_flag(flag):
    r = runtime({"fault": "Local error", "action_required": flag})
    assert r.notice.message() == ""


@pytest.mark.asyncio
async def test_actual_sg_fault_calls_only_notification_and_does_not_pause_devices():
    r = runtime({"fault": "De lokale aflooptimer is niet bevestigd", "action_required": True})
    r.mode = "solar"
    await r.notice.sync()
    assert r.mode == "solar"
    assert r.hass.services.calls[0][:2] == ("persistent_notification", "create")
    data = r.hass.services.calls[0][2]
    assert data["title"] == "SolarPilot: controle nodig"
    assert "Extra zonneboost via SG" in data["message"]
    assert "lokale timer" in data["message"]
    assert "Boilercontrole afronden" not in data["message"]
    assert "Panasonic en de overige" in data["message"]
    await r.notice.sync()
    assert len(r.hass.services.calls) == 1


@pytest.mark.asyncio
async def test_sg_fault_notice_updates_on_change_and_dismisses_after_recovery():
    view = {"fault": "First fault", "action_required": True}
    r = runtime()
    r.sg_boost.overview = lambda: dict(view)
    await r.notice.sync()
    view["fault"] = "Changed fault"
    await r.notice.sync()
    view.update(fault="", action_required=False)
    await r.notice.sync()
    assert [x[1] for x in r.hass.services.calls] == ["create", "create", "dismiss"]
    assert len({x[2]["notification_id"] for x in r.hass.services.calls}) == 1
    await r.notice.sync()
    assert len(r.hass.services.calls) == 3


@pytest.mark.asyncio
async def test_restored_active_receipt_recreates_notice_once_after_restart():
    view = {"fault": "Timer check required", "action_required": True}
    first = runtime(view)
    await first.notice.sync()
    receipt = first.notice.snapshot()
    restarted = runtime(view)
    restarted.notice.restore(receipt)
    assert restarted.notice.snapshot() == receipt
    await restarted.notice.sync()
    await restarted.notice.sync()
    assert [x[1] for x in restarted.hass.services.calls] == ["create"]
    assert restarted.hass.services.calls[0][2] == first.hass.services.calls[0][2]


@pytest.mark.asyncio
async def test_restored_resolved_notice_dismisses_old_stable_id():
    first = runtime({"fault": "Timer check", "action_required": True})
    await first.notice.sync()
    second = runtime()
    second.notice.restore(first.notice.snapshot())
    await second.notice.sync()
    await second.notice.sync()
    assert [x[1] for x in second.hass.services.calls] == ["dismiss"]
    assert not second.notice.snapshot()["active"]


@pytest.mark.asyncio
async def test_transport_failure_during_restart_retries_without_losing_action():
    first = runtime({"fault": "Timer check", "action_required": True})
    await first.notice.sync()
    second = runtime({"fault": "Timer check", "action_required": True})
    second.notice.restore(first.notice.snapshot())
    second.hass.services.failure = True
    await second.notice.sync()
    second.hass.services.failure = False
    await second.notice.sync()
    await second.notice.sync()
    assert [x[1] for x in second.hass.services.calls] == ["create", "create"]


@pytest.mark.asyncio
async def test_receipt_storage_failure_does_not_repeat_accepted_notice():
    r = runtime({"fault": "Timer check", "action_required": True})
    r.store.failure = True
    await r.notice.sync()
    r.store.failure = False
    await r.notice.sync()
    assert len(r.hass.services.calls) == 1
    assert r.store.calls == 2


@pytest.mark.asyncio
async def test_sg_and_ordinary_faults_remain_separate_and_ordinary_can_clear():
    r = runtime({"fault": "Timer check", "action_required": True})
    r.configs = {"a": {"name": "Generic device"}}
    r.faults = {"a": "Ordinary source uncertain"}
    r.battery_fleet.state.faults = {"b": "Battery target uncertain"}
    await r.notice.sync()
    text = r.hass.services.calls[-1][2]["message"]
    assert "Generic device" in text and "Battery target uncertain" in text and "Timer check" in text
    r.faults.clear()
    await r.notice.sync()
    text = r.hass.services.calls[-1][2]["message"]
    assert "Generic device" not in text
    assert "Battery target uncertain" in text and "Timer check" in text


def test_notification_text_is_inert_and_bounded():
    r = runtime({"fault": "<script>[bad](https://example.invalid)" + "x" * 1000, "action_required": True})
    text = r.notice.message()
    assert "\\<script\\>" in text
    assert "\\[bad\\]" in text
    assert "x" * 250 not in text
