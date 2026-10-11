"""SG minimum preference upgrades without extending saved maximum authority."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot.sg_config import SG_DEFAULTS, normalize_config, validate_config
from custom_components.solar_pilot.panasonic_migration import migrate_panasonic
from test_sg_config62 import flow, live_sg_runtime
from test_sg_migration62 import legacy


def old_config(maximum=3600):
    result = normalize_config({"entity_id": "switch.sg_contact", "enabled": True,
        "commissioning_confirmed": True, "watchdog_confirmed": True,
        "profile": "general", "profile_confirmed": True,
        "threshold_w": 2500, "expected_power_w": 3000,
        "start_delay_s": 180, "stop_delay_s": 90, "rest_s": 1200,
        "max_session_s": maximum, "lease_s": 240, "renew_s": 30})
    result.pop("min_session_s")
    return result


@pytest.mark.parametrize("maximum", [300, 600, 900, 1199, 1200, 3600, 14400])
def test_missing_minimum_defaults_to_twenty_minutes_without_rewriting_old_config(maximum):
    saved = old_config(maximum)
    before = deepcopy(saved)
    normalized = normalize_config(saved)
    assert normalized["min_session_s"] == SG_DEFAULTS["min_session_s"] == 1200
    assert {key: normalized[key] for key in saved} == saved == before
    assert normalized["max_session_s"] == maximum and normalized["enabled"] is True
    assert not validate_config(saved)


@pytest.mark.parametrize("minimum", [0, 60, 1200, 1200.5, 5400, 14400])
def test_explicit_minimum_is_preserved_even_above_saved_hard_maximum(minimum):
    saved = {**old_config(300), "min_session_s": minimum}
    assert normalize_config(saved) == saved
    assert not validate_config(saved)


@pytest.mark.parametrize("minimum", [-1, 14401, True, None, "invalid", float("nan"), float("inf")])
def test_invalid_minimum_remains_visible_in_validation_instead_of_being_coerced(minimum):
    saved = {**old_config(), "min_session_s": minimum}
    assert validate_config(saved) == {"min_session_s": "range"}


@pytest.mark.parametrize("minimum", [None, 0])
def test_completed_panasonic_migration_keeps_existing_settings_and_archive_exact(minimum):
    options, stored = legacy()
    options, stored, _ = migrate_panasonic(options, stored)
    options["sg_boost"] = old_config(300)
    if minimum is not None:
        options["sg_boost"]["min_session_s"] = minimum
    before = deepcopy((options, stored))
    upgraded, journal, assessment = migrate_panasonic(options, stored)
    assert (upgraded, journal) == before and assessment["changed"] is False
    effective = normalize_config(upgraded["sg_boost"])
    assert effective["min_session_s"] == (1200 if minimum is None else minimum)
    assert effective["max_session_s"] == 300 and effective["enabled"] is True
    assert not validate_config(effective)


@pytest.mark.asyncio
async def test_native_advanced_form_exposes_minimum_range_without_saving_on_open(flow):
    flow.options["sg_boost"] = old_config(300)
    before = deepcopy(flow.options)
    form = await flow.async_step_sg_advanced()
    assert form["data_schema"]["min_session_s"] == (0, 14400, 60)
    assert form["data_schema"]["max_session_s"] == (300, 14400, 60)
    assert flow._sg_values()["min_session_s"] == 1200
    assert flow.options == before and flow.saved is None and not flow.hass.services.calls


@pytest.mark.asyncio
@pytest.mark.parametrize("minimum", [0, 1200, 5400])
async def test_explicit_advanced_save_preserves_short_maximum_and_other_options(flow, minimum):
    flow.options["sg_boost"] = old_config(300)
    before = deepcopy(flow.options["sg_boost"])
    result = await flow.async_step_sg_advanced({"min_session_s": minimum})
    saved = result["saved"]["sg_boost"]
    assert saved["min_session_s"] == minimum
    assert {key: saved[key] for key in before} == before
    assert saved["max_session_s"] == 300 and saved["enabled"] is True
    assert not flow.hass.services.calls


@pytest.mark.asyncio
async def test_invalid_native_minimum_does_not_replace_current_options(flow):
    flow.options["sg_boost"] = old_config(300)
    before = deepcopy(flow.options)
    form = await flow.async_step_sg_advanced({"min_session_s": 14401})
    assert form["errors"] == {"min_session_s": "range"}
    assert flow.options == before and flow.saved is None and not flow.hass.services.calls


@pytest.mark.asyncio
async def test_stale_minimum_form_cannot_overwrite_a_concurrent_timing_edit(flow):
    flow.options["sg_boost"] = old_config(300)
    flow.config_entry = SimpleNamespace(options=deepcopy(flow.options))
    await flow.async_step_sg_advanced()
    flow.config_entry.options["sg_boost"]["max_session_s"] = 600
    form = await flow.async_step_sg_advanced({"min_session_s": 1800})
    assert form["errors"] == {"base": "sg_reopen"}
    assert flow.options["sg_boost"]["max_session_s"] == 600
    assert flow._sg_values()["min_session_s"] == 1200
    assert flow.saved is None and not flow.hass.services.calls


@pytest.mark.asyncio
async def test_minimum_edit_waits_for_owned_lease_release_without_actuating():
    r, h = live_sg_runtime()
    config = normalize_config({**r.entry.options["sg_boost"], "max_session_s": 300})
    r.entry.options["sg_boost"] = deepcopy(config)
    r.sg_boost.update_config(config)
    r.live_options.applied = deepcopy(r.entry.options)
    r.sg_boost.owned = r.sg_boost.relay_on = True
    r.sg_boost._lease_deadline = r.sg_boost._clock()+60
    base = deepcopy(r.entry.options)
    desired = deepcopy(base)
    desired["sg_boost"]["min_session_s"] = 1800
    await r.live_options.submit(base, desired)
    assert r.sg_boost.settings["min_session_s"] == 1200
    assert r.entry.options["sg_boost"]["min_session_s"] == 1200
    assert "group:sg_boost" in r.entry.options["_live_pending"]
    assert not h.services.calls
    r.sg_boost.owned = r.sg_boost.relay_on = False
    await r.live_options.process_pending()
    assert r.sg_boost.settings["min_session_s"] == 1800
    assert r.entry.options["sg_boost"]["max_session_s"] == 300
    assert not r.entry.options["_live_pending"] and not h.services.calls
