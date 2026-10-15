"""Synthetic HA integration evidence for isolated, read-only HP history."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from test_runtime import build
from test_sensor_recorder59 import sensor, recorder_payload
from custom_components.solar_pilot.heatpump_history_runtime import (
    CHECKPOINT_S, HeatpumpHistoryRecorder, configured_history_sources,
    heatpump_history_storage_key, history_binding,
)

BASE = datetime(2026, 10, 11, 8, tzinfo=timezone.utc)


def sample(when=BASE, watts=1800):
    return {"configured": True, "power_entity": "sensor.hp_total", "power_kind": "measured",
            "power_scope": "total", "power_complete": True, "power_w": watts,
            "power_observed_at": when.timestamp(), "source_stale_s": 120,
            "power_activity": {"threshold_w": 100, "state": "active", "active": watts >= 100}}


async def recorder():
    r, h = build()
    rec = r.heatpump_history
    rec.now = lambda: BASE
    await rec.start()
    return r, h, rec


def observe(rec, when, *, watts=1800, binding="synthetic-a", sources=()):
    rec.observe(sample(when, watts), {}, when, binding=binding, sources=sources)


@pytest.mark.asyncio
async def test_separate_checkpoint_restores_without_counting_unobserved_downtime():
    r, h, rec = await recorder()
    before = deepcopy((r.entry.data, r.entry.options, r._snapshot()))
    observe(rec, BASE)
    observe(rec, BASE+timedelta(seconds=20))
    await rec.close()
    saved = deepcopy(rec.store.data)
    assert heatpump_history_storage_key(r.entry.entry_id) == "solar_pilot.test.heatpump_history"
    assert "heatpump_history" not in r._snapshot()
    assert saved["access_sources"] == ["sensor.hp_total"]
    assert (r.entry.data, r.entry.options, r._snapshot()) == before
    other = HeatpumpHistoryRecorder(h, r.entry)
    other.now = lambda: BASE+timedelta(hours=1)
    other.store.data = saved
    await other.start()
    observe(other, BASE+timedelta(hours=1))
    detail = other.detail()
    assert detail["on_s"] == 20 and detail["energy_known_s"] == 20
    assert detail["energy_kwh"] == pytest.approx(.01)
    assert detail["sessions"][0]["stop_confirmed"] is False
    assert not h.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["observe", "paused", "manual", "solar"])
async def test_recording_poll_is_independent_of_analysis_and_control_mode(monkeypatch, mode):
    r, h, rec = await recorder()
    r.mode = mode
    r.analysis.settings["enabled"] = False
    rec.now = lambda: BASE+timedelta(seconds=5)
    calls = []
    p, sg = sample(), {"configured": False}
    monkeypatch.setattr(r.panasonic, "overview", lambda: calls.append("hp") or p)
    monkeypatch.setattr(r.sg_boost, "overview", lambda: calls.append("sg") or sg)
    accepted = []
    monkeypatch.setattr(rec.model, "observe", lambda hp, relay, when, **kw: accepted.append((hp, relay, when, kw)))
    async def no_control():
        pass
    monkeypatch.setattr(r, "_tick", no_control)
    monkeypatch.setattr(r.learning_hub, "tick", no_control)
    monkeypatch.setattr(r.action_notifications, "sync", no_control)
    monkeypatch.setattr(r.compatibility_notifications, "sync", no_control)
    monkeypatch.setattr(r, "publish", lambda: None)
    await r.tick()
    assert calls == ["hp", "sg"]
    assert len(accepted) == 1 and accepted[0][:3] == (p, sg, BASE+timedelta(seconds=5))
    assert r.mode == mode and not h.services.calls


@pytest.mark.asyncio
async def test_batched_checkpoint_is_not_postponed_by_five_second_samples(monkeypatch):
    _, _, rec = await recorder()
    clock = [1000.0]
    monkeypatch.setattr(rec._maybe_save.__globals__["time"], "monotonic", lambda: clock[0])
    rec._last_checkpoint = clock[0]-CHECKPOINT_S
    callbacks = []
    rec.store.async_delay_save = lambda cb, delay: callbacks.append((cb, delay))
    for n in range(12):
        clock[0] += 5
        observe(rec, BASE+timedelta(seconds=n*5))
    assert len(callbacks) == 1 and callbacks[0][1] == 5
    data = callbacks.pop()[0]()
    assert data["history"]["energy_days"]["2026-10-11"]["energy_known_s"] == 55
    for n in range(12, 23):
        clock[0] += 5
        observe(rec, BASE+timedelta(seconds=n*5))
    assert not callbacks
    clock[0] += 5
    observe(rec, BASE+timedelta(seconds=115))
    assert len(callbacks) == 1


@pytest.mark.asyncio
async def test_close_cancels_own_hooks_then_flushes_once_and_never_controls():
    _, h, rec = await recorder()
    observe(rec, BASE)
    observe(rec, BASE+timedelta(seconds=5))
    cleaned = []
    rec.store._async_cleanup_delay_listener = lambda: cleaned.append("delay")
    rec.store._async_cleanup_final_write_listener = lambda: cleaned.append("final")
    await rec.close()
    await rec.close()
    assert cleaned == ["delay", "final"] and len(rec.store.saves) == 1
    assert rec.store.saves[0]["history"]["energy_days"]["2026-10-11"]["energy_known_s"] == 5
    assert rec.model._last_energy is None and not h.services.calls


@pytest.mark.asyncio
async def test_failed_setup_close_never_overwrites_loaded_checkpoint():
    _, _, rec = await recorder()
    old = {"kept": "synthetic prior checkpoint"}
    rec.store.data = deepcopy(old)
    calls = []
    rec.store._async_cleanup_delay_listener = lambda: calls.append("delay")
    rec.store._async_cleanup_final_write_listener = lambda: calls.append("final")
    await rec.close(persist=False)
    assert rec.store.data == old and not rec.store.saves and calls == ["delay", "final"]


@pytest.mark.asyncio
@pytest.mark.parametrize("stored", [
    {"version": 2, "history": {}, "access_sources": []},
    {"version": True, "history": {}, "access_sources": []},
    {"version": 1, "history": {"version": 99}, "access_sources": []},
    {"version": 1, "history": {}, "access_sources": ["not-an-entity"]},
    ["unexpected", "storage"],
])
async def test_corrupt_or_future_storage_is_preserved_and_never_replaced(stored):
    r, _ = build()
    rec = r.heatpump_history
    rec.now = lambda: BASE
    rec.store.data = deepcopy(stored)
    await rec.start()
    observe(rec, BASE)
    observe(rec, BASE+timedelta(seconds=5))
    assert rec.loaded and rec.error and rec.detail()["energy_known_s"] == 5
    assert rec.brief()["storage_available"] is False
    await rec.close()
    assert rec.store.data == stored and not rec.store.saves


@pytest.mark.asyncio
async def test_load_failure_is_ephemeral_without_disabling_controller(monkeypatch):
    r, _, rec = await recorder()
    rec.loaded = rec._writable = False
    async def failed_load():
        raise OSError("synthetic storage outage")
    monkeypatch.setattr(rec.store, "async_load", failed_load)
    await rec.start()
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    await r.tick()
    assert r.mode == "solar" and r.pending and rec.error
    await rec.close()
    assert not rec.store.saves


@pytest.mark.asyncio
async def test_observation_failure_is_isolated_and_breaks_next_interval(monkeypatch):
    r, _, rec = await recorder()
    observe(rec, BASE)
    observe(rec, BASE+timedelta(seconds=5))
    actual = rec.model.observe
    def failed(*args, **kwargs):
        raise ValueError("synthetic telemetry failure")
    monkeypatch.setattr(rec.model, "observe", failed)
    observe(rec, BASE+timedelta(seconds=10))
    monkeypatch.setattr(rec.model, "observe", actual)
    observe(rec, BASE+timedelta(seconds=15))
    rec.now = lambda: BASE+timedelta(seconds=15)
    assert rec.detail()["energy_known_s"] == 5 and rec.detail()["on_s"] == 5
    assert rec.error and r.mode == "observe"


@pytest.mark.asyncio
async def test_source_or_optional_save_failure_cannot_stop_core_controller(monkeypatch):
    r, _, rec = await recorder()
    def failed(*args, **kwargs):
        raise ValueError("synthetic optional source outage")
    r.mode = "solar"
    r.device_modes["a"] = "auto"
    monkeypatch.setattr(rec, "observe", failed)
    await r.tick()
    assert r.mode == "solar" and r.pending and rec.error
    async def failed_save(_):
        raise OSError("synthetic optional storage outage")
    monkeypatch.setattr(rec.store, "async_save", failed_save)
    await r.close()
    assert r.store.data is not None and rec.error


@pytest.mark.asyncio
async def test_rebinding_preserves_old_history_and_old_source_permissions(monkeypatch):
    r, _, rec = await recorder()
    r.panasonic.settings.update(power_entity="sensor.hp_total", power_scope="total")
    old = history_binding(r, sample())
    observe(rec, BASE, binding=old, sources=configured_history_sources(r))
    observe(rec, BASE+timedelta(seconds=5), binding=old)
    r.panasonic.settings["power_entity"] = "sensor.hp_replacement"
    p = sample(BASE+timedelta(seconds=10))
    p["power_entity"] = "sensor.hp_replacement"
    new = history_binding(r, p)
    rec.observe(p, {}, BASE+timedelta(seconds=10), binding=new)
    rec.now = lambda: BASE+timedelta(seconds=10)
    detail = rec.detail()
    assert old != new and len(old) == len(new) == 64
    assert detail["on_s"] == 5 and detail["energy_known_s"] == 5
    assert len(detail["sessions"]) == 2 and not detail["sessions"][0]["stop_confirmed"]
    assert rec.access_sources == {"sensor.hp_total", "sensor.hp_replacement"}
    assert "sensor.hp_total" not in json.dumps(detail)
    r.sg_boost.settings["entity_id"] = "switch.new_sg"
    assert history_binding(r, p) != new


@pytest.mark.asyncio
async def test_missing_retained_acl_preserves_evidence_but_never_borrows_new_source_access():
    r, h, rec = await recorder()
    observe(rec, BASE)
    observe(rec, BASE+timedelta(seconds=5))
    await rec.close()
    saved = deepcopy(rec.store.data)
    saved["access_sources"] = []
    other = HeatpumpHistoryRecorder(h, r.entry)
    other.now = lambda: BASE+timedelta(seconds=20)
    other.store.data = saved
    await other.start()
    assert other.detail()["energy_known_s"] == 5 and other.access_sources_complete is False
    observe(other, BASE+timedelta(seconds=20), sources={"sensor.new_allowed_meter"})
    assert other.access_sources_complete is False
    await other.close()
    assert other.store.data["access_sources_complete"] is False


@pytest.mark.asyncio
async def test_ha_timezone_checkpoint_is_preserved_if_local_timezone_changes():
    r, h = build()
    h.config = SimpleNamespace(time_zone="Europe/Amsterdam")
    rec = HeatpumpHistoryRecorder(h, r.entry)
    rec.now = lambda: BASE
    await rec.start()
    observe(rec, BASE)
    observe(rec, BASE+timedelta(seconds=5))
    await rec.close()
    saved = deepcopy(rec.store.data)
    assert saved["history"]["timezone"] == "Europe/Amsterdam"
    h.config.time_zone = "UTC"
    changed = HeatpumpHistoryRecorder(h, r.entry)
    changed.now = lambda: BASE
    changed.store.data = deepcopy(saved)
    await changed.start()
    assert changed.error and changed.brief()["storage_available"] is False
    await changed.close()
    assert changed.store.data == saved


def test_binding_changes_with_registry_device_identity(monkeypatch):
    from homeassistant.helpers import entity_registry
    r, _ = build()
    r.panasonic.settings["power_entity"] = "sensor.hp_total"
    identity = SimpleNamespace(config_entry_id="native-entry", device_id="physical-unit-a", unique_id="meter-a")
    monkeypatch.setattr(entity_registry, "async_get", lambda hass: SimpleNamespace(async_get=lambda entity: identity))
    first = history_binding(r, sample())
    identity.device_id = "physical-unit-b"
    assert history_binding(r, sample()) != first


@pytest.mark.asyncio
async def test_live_brief_and_recorder_attributes_never_publish_historical_totals():
    r, h, rec = await recorder()
    observe(rec, BASE)
    observe(rec, BASE+timedelta(seconds=5))
    rec.now = lambda: BASE+timedelta(seconds=5)
    brief = rec.brief()
    assert set(brief) <= {"date", "recording", "ongoing", "revision", "recording_error", "storage_available"}
    assert len(json.dumps(brief)) < 300
    h.states.set("sensor.hp_total", 1800, {"unit_of_measurement": "W"})
    r.panasonic.settings.update(power_entity="sensor.hp_total", power_scope="total")
    for suffix in ("panasonic_power", "panasonic_status", "dhw_temperature"):
        entity = sensor(r, suffix)
        live = entity.extra_state_attributes
        assert live["history"] == brief
        assert "history" not in recorder_payload(entity, live)
    power = sensor(r, "panasonic_power")
    assert power.native_value == 1800
    assert power._unrecorded_attributes is not None  # Only attrs excluded: native numeric state still emitted.
    assert r.ems_overview()["panasonic"]["history"] == brief
    assert not h.services.calls


@pytest.mark.asyncio
async def test_history_read_failure_does_not_break_read_only_monitor(monkeypatch):
    r, h = build()
    def failed():
        raise ValueError("synthetic optional display error")
    monkeypatch.setattr(r.heatpump_history, "brief", failed)
    assert r.panasonic.overview()["history"] == {}
    del r.heatpump_history
    assert r.panasonic.overview()["history"] == {} and not h.services.calls


@pytest.mark.asyncio
async def test_explicit_private_export_is_bounded_without_store_acl_or_binding(monkeypatch):
    r, _, rec = await recorder()
    observe(rec, BASE-timedelta(days=8))
    observe(rec, BASE-timedelta(days=8)+timedelta(seconds=5))
    observe(rec, BASE)
    observe(rec, BASE+timedelta(seconds=5))
    rec.now = lambda: BASE+timedelta(seconds=5)
    data = rec.export()
    assert len(data["days"]) == 8 and data["days"][0]["date"] == "2026-10-04"
    assert data["retention_days"] == 30 and data["requested_hours"] == 168
    assert data["exported_days"] == 8
    assert data["days"][-1]["energy_known_s"] == 5
    assert all("days" not in day for day in data["days"])
    assert all("days" not in lane for day in data["days"] for lane in day["sg"].values())
    text = json.dumps(data)
    assert "sensor.hp_total" not in text and "synthetic-a" not in text and "access_sources" not in text
    from custom_components.solar_pilot import analysis_export
    monkeypatch.setattr(analysis_export.time, "time", lambda: (BASE+timedelta(seconds=5)).timestamp())
    components = r.analysis.prepare(hours=168)["components"]
    assert components["heatpump_history"] == data
    assert "heatpump_history" not in r._snapshot()


def test_remove_hook_only_removes_own_history_store():
    text = (Path(__file__).resolve().parents[1]/"custom_components/solar_pilot/__init__.py").read_text()
    assert "Store(hass, 1, heatpump_history_storage_key(entry.entry_id)).async_remove()" in text
