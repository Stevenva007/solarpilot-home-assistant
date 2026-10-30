"""Fifteen-minute cloud policy migrates once without extending local leases."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.panasonic_migration import (
    ARCHIVE_KEY, MARKER, SG_CLOUD_BUFFER_MARKER, migrate_panasonic,
)
from custom_components.solar_pilot.sg_boost import SGBoostManager
from custom_components.solar_pilot.sg_config import SG_DEFAULTS, control_identity, normalize_config, validate_config
from custom_components.solar_pilot.sg_investigation import (
    clean_session_provenance, effective_session_policy, session_policy_hash,
)
from test_sg_config62 import flow
from test_sg_controller62 import fixture, tick
from test_sg_external106 import external
from test_sg_migration62 import legacy


def installed(delay=300):
    options, stored = legacy()
    options, stored, _ = migrate_panasonic(options, stored)
    options.pop(SG_CLOUD_BUFFER_MARKER)
    options["sg_boost"].update(stop_delay_s=delay, enabled=True,
        entity_id="switch.fictional_sg", commissioning_confirmed=True,
        watchdog_confirmed=True, profile="general", profile_confirmed=True,
        cooling_protection_confirmed=True)
    stored["sg_boost"] = {"session_checkpoint": {"joint_solar_deficit": {
        "started_at": 1800000000, "deadline": 1800000300, "remaining_cap_s": 120}}}
    return options, stored


def test_defaults_keep_short_lease_and_twenty_minute_minimum():
    assert SG_DEFAULTS["stop_delay_s"] == 900
    assert SG_DEFAULTS["lease_s"] == 300 and SG_DEFAULTS["renew_s"] == 60
    assert SG_DEFAULTS["min_session_s"] == 1200 and SG_DEFAULTS["import_threshold_w"] == 600
    assert not validate_config(normalize_config())
    assert normalize_config({"stop_delay_s": 300, "import_threshold_w": 600})["stop_delay_s"] == 300
    assert not validate_config({"stop_delay_s": 900})
    assert validate_config({"stop_delay_s": 901}) == {"stop_delay_s": "range"}


@pytest.mark.parametrize("delay", [300, "300", None])
@pytest.mark.parametrize("import_limit", [0, 450, 600])
def test_old_default_or_missing_delay_upgrades_once_with_other_choices_intact(delay, import_limit):
    options, stored = installed(delay)
    if delay is None:
        options["sg_boost"].pop("stop_delay_s")
    options["sg_boost"]["import_threshold_w"] = import_limit
    before = deepcopy((options, stored))
    upgraded, journal, report = migrate_panasonic(options, stored)
    assert (options, stored) == before and report["changed"] is True
    assert upgraded["sg_boost"]["stop_delay_s"] == 900
    assert upgraded[SG_CLOUD_BUFFER_MARKER] == 1
    assert {key: value for key, value in upgraded["sg_boost"].items() if key != "stop_delay_s"} == {
        key: value for key, value in options["sg_boost"].items() if key != "stop_delay_s"}
    assert journal == stored  # Original history, deadline and rollback backup stay exact.
    again, again_store, report = migrate_panasonic(upgraded, journal)
    assert (again, again_store) == (upgraded, journal) and report["changed"] is False


@pytest.mark.parametrize("delay", [60, 420, 600, 900, "420", None, True, "invalid"])
def test_custom_or_damaged_delay_is_not_replaced(delay):
    options, stored = installed(delay)
    upgraded, journal, report = migrate_panasonic(options, stored)
    assert upgraded["sg_boost"] == options["sg_boost"]
    assert upgraded[SG_CLOUD_BUFFER_MARKER] == 1 and report["changed"] is True
    assert journal == stored


def test_later_explicit_five_minute_choice_survives_restart():
    options, stored = installed()
    options, stored, _ = migrate_panasonic(options, stored)
    options["sg_boost"]["stop_delay_s"] = 300
    upgraded, journal, report = migrate_panasonic(options, stored)
    assert upgraded == options and journal == stored and report["changed"] is False


@pytest.mark.parametrize("hysteresis,expected_import", [(300, 600), (450, 450)])
def test_missing_delay_does_not_change_legacy_effective_import_limit(hysteresis, expected_import):
    options, stored = installed()
    options["sg_boost"].pop("stop_delay_s")
    options["sg_boost"].pop("import_threshold_w")
    options["sg_boost"]["hysteresis_w"] = hysteresis
    assert normalize_config(options["sg_boost"])["import_threshold_w"] == expected_import
    upgraded, _journal, _report = migrate_panasonic(options, stored)
    assert upgraded["sg_boost"]["stop_delay_s"] == 900
    assert normalize_config(upgraded["sg_boost"])["import_threshold_w"] == expected_import


def test_crash_before_options_save_retries_without_nested_or_changed_archive():
    options, stored = installed()
    upgraded, saved_store, _ = migrate_panasonic(options, stored)
    retry, retry_store, _ = migrate_panasonic(options, saved_store)
    assert retry == upgraded and retry_store == saved_store
    assert retry_store[ARCHIVE_KEY] == stored[ARCHIVE_KEY]
    assert retry_store["sg_boost"] == stored["sg_boost"]


def test_new_install_receives_policy_marker_without_relay_authority():
    options, stored, _ = migrate_panasonic({}, {})
    assert options[SG_CLOUD_BUFFER_MARKER] == 1 and options["sg_boost"]["stop_delay_s"] == 900
    assert not options["sg_boost"]["enabled"] and options["sg_boost"]["entity_id"] == ""
    assert stored[ARCHIVE_KEY]["backup_options"] == {}


@pytest.mark.asyncio
async def test_advanced_form_accepts_fifteen_minutes_and_keeps_short_lease(flow):
    form = await flow.async_step_sg_advanced()
    assert form["data_schema"]["stop_delay_s"] == (5, 900, 5)
    before = deepcopy(flow.options["sg_boost"])
    result = await flow.async_step_sg_advanced({"stop_delay_s": 900})
    saved = result["saved"]["sg_boost"]
    assert saved["stop_delay_s"] == 900 and saved["lease_s"] == before["lease_s"]
    assert not flow.hass.services.calls


@pytest.mark.parametrize("delay,accepted", [(300, True), (600, True), (900, True), (901, False)])
def test_original_session_policy_supports_fifteen_minute_evidence(delay, accepted):
    policy = effective_session_policy({**SG_DEFAULTS, "stop_delay_s": delay}, 1200, 3500)
    provenance = {"schema": 1, "release": "1.0.0-beta.112", "policy": policy,
        "policy_hash": session_policy_hash(policy), "command_identity": "a"*32,
        "owner": "solarpilot", "started_at": 1800000000}
    clean = clean_session_provenance(provenance)
    assert (clean is not None) is accepted
    if accepted:
        assert clean["policy"]["stop_delay_s"] == delay and clean["policy"] == policy


def migrate_intent(manager, runtime, *, raw=None, snapshot=None):
    options = {MARKER: 1, "sg_boost": deepcopy(manager.settings if raw is None else raw)}
    stored = {ARCHIVE_KEY: {"version": 1, "read_only": True,
        "backup_options": {}, "backup_store": {}, "assessment": {}},
        "sg_boost": deepcopy(manager.snapshot() if snapshot is None else snapshot)}
    options, stored, _report = migrate_panasonic(options, stored)
    runtime.entry.options = options
    return options, stored


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_kind", ["current", "missing_delay", "legacy_default", "legacy_custom"])
async def test_migration_retains_timed_manual_off_until_original_expiry(raw_kind):
    old_delay, old_import = (60, 450) if raw_kind == "legacy_custom" else (300, 600.0)
    manager, adapter, clock, runtime = fixture(stop_delay_s=old_delay, import_threshold_w=old_import,
        hysteresis_w=450 if raw_kind == "legacy_custom" else 300)
    await manager.set_manual_control("off", 1800)
    original = deepcopy(manager._manual_control)
    raw = deepcopy(manager.settings)
    if raw_kind in {"missing_delay", "legacy_custom"}:
        raw.pop("stop_delay_s")
    if raw_kind in {"legacy_default", "legacy_custom"}:
        raw.pop("import_threshold_w")
    if raw_kind == "legacy_default":
        raw["stop_delay_s"] = 60
    clock.advance(600)
    options, stored = migrate_intent(manager, runtime, raw=raw)
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = restored
    runtime._snapshot = lambda: {"sg_boost": restored.snapshot()}
    restored.restore(stored["sg_boost"])
    assert restored.manual_mode == "off" and restored._manual_deadline == original["expires_at"]
    assert restored.settings["stop_delay_s"] == 900
    assert restored.settings["import_threshold_w"] == old_import
    assert {key: value for key, value in restored._manual_control.items() if key != "control_identity"} == {
        key: value for key, value in original.items() if key != "control_identity"}
    while clock() < original["expires_at"]-1:
        clock.advance(min(30, original["expires_at"]-1-clock()))
        await tick(restored)
        assert restored.manual_mode == "off" and not restored.owned
    assert not any(action == "on" for action, _lease in adapter.calls)
    assert options[SG_CLOUD_BUFFER_MARKER] == 1


@pytest.mark.asyncio
async def test_migration_retains_original_external_reassessment_deadline():
    manager, adapter, clock, runtime = await external(stop_delay_s=300)
    original = deepcopy(manager._external_control)
    clock.advance(600)
    _options, stored = migrate_intent(manager, runtime)
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = restored
    runtime._snapshot = lambda: {"sg_boost": restored.snapshot()}
    restored.restore(stored["sg_boost"])
    await restored.start()
    assert restored.external_control_overview()["remaining_s"] == 300
    assert restored._external_control["expires_at"] == original["expires_at"]
    assert restored._external_control["created_at"] == original["created_at"]
    assert not restored.owned and not adapter.calls
    clock.advance(299)
    await tick(restored, surplus=0)
    assert restored.external_control_overview()["remaining_s"] == 1 and not adapter.calls
    clock.advance(1)
    await tick(restored, surplus=0)
    assert not adapter.on and adapter.calls == [("off", None)]


@pytest.mark.asyncio
async def test_migration_retains_manual_on_origin_without_upgrading_lease_checkpoint():
    manager, adapter, clock, runtime = fixture(stop_delay_s=300, min_session_s=0, max_session_s=300)
    await manager.set_manual_control("on", 1800)
    await tick(manager, surplus=0)
    origin = manager._session_started
    original = manager.snapshot()
    clock.advance(60)
    _options, stored = migrate_intent(manager, runtime, snapshot=original)
    assert stored["sg_boost"]["session_checkpoint"] == original["session_checkpoint"]
    assert stored["sg_boost"]["session_provenance"] == original["session_provenance"]
    restored = SGBoostManager(runtime, adapter=adapter, clock=clock)
    runtime.sg_boost = restored
    runtime._snapshot = lambda: {"sg_boost": restored.snapshot()}
    before = list(adapter.calls)
    restored.restore(stored["sg_boost"])
    assert adapter.calls == before and not restored.owned
    assert restored.manual_mode == "on" and restored._manual_session_started == origin
    assert restored._manual_control["expires_at"] == original["manual_control"]["expires_at"]
    await restored.start()
    while clock() < origin+300:
        clock.advance(30)
        await tick(restored, surplus=0)
        if adapter.expiry is not None:
            assert adapter.expiry <= origin+300
    assert not restored.owned and not adapter.on


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatch", ["identity", "relay", "other_policy"])
async def test_migration_does_not_rebind_an_unrelated_manual_intent(mismatch):
    manager, _adapter, _clock, runtime = fixture(stop_delay_s=300)
    await manager.set_manual_control("off", 1800)
    snapshot = manager.snapshot()
    raw = deepcopy(manager.settings)
    if mismatch == "identity":
        snapshot["manual_control"]["control_identity"] = "0"*64
    elif mismatch == "relay":
        snapshot["relay_entity"] = "switch.fictional_other"
    else:
        raw["threshold_w"] = 3500
    original = deepcopy(snapshot["manual_control"])
    _options, stored = migrate_intent(manager, runtime, raw=raw, snapshot=snapshot)
    assert stored["sg_boost"]["manual_control"] == original


@pytest.mark.asyncio
async def test_intent_remap_is_idempotent_after_store_saved_before_options():
    manager, _adapter, _clock, runtime = fixture(stop_delay_s=300)
    await manager.set_manual_control("off", 1800)
    raw = deepcopy(manager.settings)
    first_options, first_store = migrate_intent(manager, runtime)
    second_options, second_store = migrate_intent(manager, runtime, raw=raw, snapshot=first_store["sg_boost"])
    assert second_options == first_options and second_store == first_store
    assert second_store["sg_boost"]["manual_control"]["control_identity"] == control_identity(
        normalize_config(second_options["sg_boost"]))
