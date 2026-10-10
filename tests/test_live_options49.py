"""Bad deferred proposals and unresolved leases never change active bindings."""
from copy import deepcopy

import pytest

from custom_components.solar_pilot.live_options import ARCHIVED, PENDING, keyed
from test_live_config34 import flow_class
from test_live_options34 import desired
from test_runtime import build


@pytest.mark.parametrize("archives", [None, [], "invalid"])
@pytest.mark.asyncio
async def test_malformed_archive_collection_does_not_leave_retirement_partly_applied(archives):
    runtime, hass = build()
    runtime.live_options.restore({"archives": archives})
    before = deepcopy(runtime.entry.options)

    await runtime.live_options.submit(before, {**before, "devices": []})

    assert not runtime.configs and not runtime.entry.options["devices"]
    assert runtime.live_options.archives["a"]["id"] == "a"
    assert not hass.services.calls


def test_archive_restore_preserves_valid_sibling_and_skips_damaged_row():
    runtime, _ = build()
    good = {"id": "old", "power_profile": {"watts": [300, 350]}}
    runtime.live_options.restore({"archives": {"old": good, "bad": None}})
    assert runtime.live_options.archives == {"old": good}


@pytest.mark.asyncio
async def test_bad_pending_sibling_cannot_block_a_safe_binding_edit_or_send_commands():
    runtime, hass = build()
    runtime.states["a"].on = True
    before, after = desired(runtime, control_entity="switch.new")
    await runtime.live_options.submit(before, after)
    runtime.entry.options[PENDING]["device:broken"] = None
    runtime.states["a"].on = runtime.states["a"].owned = False
    hass.states.set("switch.load", "off")

    await runtime.live_options.process_pending()

    assert runtime.configs["a"]["control_entity"] == "switch.new"
    assert set(runtime.entry.options[PENDING]) == {"device:broken"}
    assert runtime.live_options.overview()["pending"][0]["reason"].startswith("Opgeslagen voorstel ongeldig")
    assert not hass.services.calls
    await runtime.live_options.cancel_pending(["device:broken"])
    assert not runtime.entry.options[PENDING]


@pytest.mark.parametrize("bad", [
    {"kind": "device", "id": "a"},
    {"kind": "device", "id": "a", "new": None},
    {"kind": "device", "id": "a", "new": {"id": "other"}},
    {"kind": "device", "id": "a", "new": {"id": []}},
])
@pytest.mark.asyncio
async def test_damaged_device_proposal_cannot_become_an_implicit_removal_or_replacement(bad):
    runtime, hass = build()
    old = deepcopy(runtime.entry.options["devices"][0])
    row = {**bad}
    if "new" in bad and bad != {"kind": "device", "id": "a", "new": None}:
        row["old"] = old
    runtime.entry.options[PENDING] = {"device:a": row}

    await runtime.live_options.process_pending()

    assert runtime.configs["a"]["control_entity"] == "switch.load"
    assert runtime.entry.options["devices"] == [old]
    assert runtime.live_options.overview()["pending"]
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_pending_options_form_can_cancel_a_malformed_top_level_collection(flow_class):
    runtime, hass = build()
    before = deepcopy(runtime.entry.options)
    runtime.entry.options[PENDING] = None
    flow = flow_class(runtime)

    result = await flow.async_step_pending_changes()
    assert result["data_schema"]["cancel"]["options"][0]["value"] == "invalid:stored"
    result = await flow.async_step_pending_changes({"cancel": ["invalid:stored"]})

    assert result["type"] == "create_entry"
    assert runtime.entry.options["devices"] == before["devices"]
    assert not runtime.entry.options[PENDING] and not hass.services.calls








def test_invalid_archived_option_rows_do_not_break_management_overview():
    runtime, _ = build()
    runtime.entry.options[ARCHIVED] = [None, {"id": []}, {"id": "old", "name": "Old"}]
    assert keyed(runtime.entry.options[ARCHIVED]) == {"old": {"id": "old", "name": "Old"}}
    assert runtime.live_options.overview()["archives"][0]["id"] == "old"
