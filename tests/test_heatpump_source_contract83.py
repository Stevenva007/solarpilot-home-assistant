"""New source semantics remain bound to captured points, without rewriting old fields."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import pytest

from custom_components.solar_pilot.heatpump_history import HeatpumpHistory
from test_heatpump_history70 import observe
from test_heatpump_history81 import tank_source
from test_operation_source_evidence83 import NOW, raw_contract

AT = datetime.fromtimestamp(NOW, timezone.utc)


def snapshot(at=AT):
    p = tank_source(at)
    p["source_contract"] = raw_contract()
    return p


def test_native_history_retains_closed_contract_and_original_sources_without_mutation():
    model = HeatpumpHistory(); p = snapshot(); before = deepcopy(p)
    observe(model, AT, p=p)
    point = model.detail(None, AT)["native_evidence"]["points"][0]
    contract = point["source_contract"]
    assert contract["verified"] is True and contract["action_semantics"] == "special_status"
    assert contract["raw_device_action"] == "OFF" and contract["pump"]["state"] == "on"
    assert contract["pump"]["observed_at"] == NOW-2
    assert point["captured_at"] == NOW and p == before
    assert not point["native"]["global_off"]
    for private in ("PRIVATE", "private_device", "Private room", "friendly_name", "unique_id", "device_id"):
        assert private not in json.dumps(point)
    stored = model.snapshot(); restored = HeatpumpHistory()
    restored.restore(stored, AT+timedelta(seconds=5))
    assert restored.detail(None, AT+timedelta(seconds=5))["native_evidence"]["points"][0]["source_contract"] == contract


def test_contract_state_change_creates_new_context_point_even_when_existing_task_stays_same():
    model = HeatpumpHistory(); observe(model, AT, p=snapshot())
    after = AT+timedelta(seconds=5); p = snapshot(after)
    p["source_contract"]["pump"].update(state="off", observed_at=after.timestamp()-1)
    observe(model, after, p=p)
    points = model.detail(None, after)["native_evidence"]["points"]
    assert len(points) == 2 and [row["source_contract"]["pump"]["state"] for row in points] == ["on", "off"]
    assert points[0]["native"]["function"] == points[1]["native"]["function"]


def test_legacy_history_without_source_contract_cannot_acquire_current_sdk_semantics():
    model = HeatpumpHistory(); observe(model, AT, p=tank_source(AT))
    old = model.snapshot()
    for point in old["native_evidence"]["points"]:
        point.pop("source_contract", None)
    restored = HeatpumpHistory(); restored.restore(old, AT+timedelta(seconds=5))
    assert restored.detail(None, AT+timedelta(seconds=5))["native_evidence"]["points"][0]["source_contract"] is None


@pytest.mark.parametrize("corrupt", ["stale", "optimistic", "private"])
def test_source_contract_restore_rejects_stale_forged_or_private_rows(corrupt):
    model = HeatpumpHistory(); observe(model, AT, p=snapshot())
    stored = model.snapshot(); row = stored["native_evidence"]["points"][0]["source_contract"]
    if corrupt == "stale":
        row["pump"]["observed_at"] = NOW-121
    elif corrupt == "optimistic":
        row["verified"] = 1
    else:
        row["pump"]["entity_id"] = "sensor.private"
    with pytest.raises(ValueError):
        HeatpumpHistory().restore(stored, AT+timedelta(seconds=5))
