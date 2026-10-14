"""Private source identities and optimistic flags cannot become retained proof."""
from copy import deepcopy
import json

import pytest

from custom_components.solar_pilot.operation_source_evidence import contract_evidence, retained_contract_evidence
from test_display_operation83 import NOW, contract_snapshot


def raw_contract():
    raw=contract_snapshot()["source_contract"]
    raw.update(reason_code="known_special_status_action_mapping",source="aquarea_contract")
    for row in [raw["pump"],raw["direction"],raw["program"],raw["tank"],*raw["zones"]]:
        row.update(entity_id="sensor.private_device",device_id="PRIVATE_DEVICE",config_entry_id="PRIVATE_ENTRY",
                   unique_id="PRIVATE_UID",friendly_name="Private room")
        row["native_observed_at"]=NOW-1
    raw.update(device_id="PRIVATE_DEVICE",entity_id="sensor.private",config_entry_id="PRIVATE_ENTRY")
    raw["provider"]["entry_id"]="PRIVATE_ENTRY"
    return raw


def test_projection_retains_original_typed_sources_but_no_private_identity_or_task_claim():
    raw=raw_contract(); before=deepcopy(raw)
    clean=contract_evidence(raw,NOW,120)
    assert raw==before and clean["verified"] is True and clean["fresh"] is True
    assert clean["action_semantics"]=="special_status" and clean["raw_device_action"]=="OFF"
    assert clean["pump"]["state"]=="on" and clean["direction"]["state"]=="PUMP"
    assert clean["program"]["state"]=="heating" and clean["zones"][0]["enabled"] is True
    assert clean["pump"]["observed_at"]==NOW-2 and clean["zones"][0]["observed_at"]==NOW-3
    serialized=json.dumps(clean,allow_nan=False)
    for forbidden in ("PRIVATE", "private", "entity_id", "device_id", "entry_id", "unique_id", "friendly_name",
                      "global_off", "compressor", "function", "confirmed"):
        assert forbidden not in serialized
    restored=retained_contract_evidence(json.loads(serialized),NOW,120)
    assert restored==clean


@pytest.mark.parametrize("raw", [None,False,[],"private"])
def test_absent_contract_does_not_acquire_current_source_metadata(raw):
    assert contract_evidence(raw,NOW,120) is None
    if raw is None:
        assert retained_contract_evidence(raw,NOW,120) is None
    else:
        with pytest.raises(ValueError):retained_contract_evidence(raw,NOW,120)


@pytest.mark.parametrize("change", ["schema_bool","read_only_number","provider_number","registered_number","unknown_version",
                                   "unknown_contract","unknown_semantics","unknown_status","pump_unknown","pump_type",
                                   "direction_unknown","wrong_program","tank_number","zone_number","zone_state",
                                   "zones_overflow","original_string","pump_time_bool","zone_stale","source_stale_number",
                                   "original_zero","original_future","invalid_native_time"])
def test_malformed_unknown_stale_context_is_never_verified(change):
    raw=raw_contract()
    if change=="schema_bool":raw["schema"]=True
    elif change=="read_only_number":raw["read_only"]=1
    elif change=="provider_number":raw["provider_loaded"]=1
    elif change=="registered_number":raw["native_device_registered"]=1
    elif change=="unknown_version":raw["provider"]["library_version"]="9.9.9"
    elif change=="unknown_contract":raw["contract_id"]="unknown"
    elif change=="unknown_semantics":raw["action_semantics"]="global_off"
    elif change=="unknown_status":raw["status"]="unknown"
    elif change=="pump_unknown":raw["pump"]["state"]="unknown"
    elif change=="pump_type":raw["pump"]["state"]=True
    elif change=="direction_unknown":raw["direction"]["state"]="REVERSE"
    elif change=="wrong_program":raw["program"]["raw_mode"]="COOL"
    elif change=="tank_number":raw["tank"]["enabled"]=0
    elif change=="zone_number":raw["zones"][0]["enabled"]=1
    elif change=="zone_state":raw["zones"][0]["state"]="private state"
    elif change=="zones_overflow":raw["zones"]*=3
    elif change=="original_string":raw["observed_at"]=str(NOW-1)
    elif change=="pump_time_bool":raw["pump"]["observed_at"]=True
    elif change=="zone_stale":raw["zones"][0]["observed_at"]=NOW-121
    elif change=="source_stale_number":raw["stale_s"]=True
    elif change=="original_zero":raw["observed_at"]=0
    elif change=="original_future":raw["observed_at"]=NOW+6
    elif change=="invalid_native_time":raw["pump"]["native_observed_at"]="private"
    clean=contract_evidence(raw,NOW,120)
    assert clean["verified"] is False
    assert len(clean["zones"])<=2
    assert "global_off" not in json.dumps(clean)
    assert retained_contract_evidence(json.loads(json.dumps(clean,allow_nan=False)),NOW,120)==clean


@pytest.mark.parametrize("change", ["verified_number","fresh_number","read_only_number","schema_bool","stale_fresh",
                                   "future_fresh","unknown_verified","row_fresh_number","enabled_number","zone_number_bool",
                                   "private_extra","nested_private","unknown_enum","report_string"])
def test_restore_rejects_forged_or_open_stored_proof(change):
    clean=contract_evidence(raw_contract(),NOW,120)
    if change=="verified_number":clean["verified"]=1
    elif change=="fresh_number":clean["fresh"]=1
    elif change=="read_only_number":clean["read_only"]=1
    elif change=="schema_bool":clean["schema"]=True
    elif change=="stale_fresh":clean["pump"]["observed_at"]=NOW-121
    elif change=="future_fresh":clean["observed_at"]=NOW+6
    elif change=="unknown_verified":clean["provider"]["library_version"]="9.9.9"
    elif change=="row_fresh_number":clean["pump"]["fresh"]=1
    elif change=="enabled_number":clean["zones"][0]["enabled"]=1
    elif change=="zone_number_bool":clean["zones"][0]["number"]=True
    elif change=="private_extra":clean["device_id"]="PRIVATE"
    elif change=="nested_private":clean["pump"]["entity_id"]="sensor.private"
    elif change=="unknown_enum":clean["raw_device_action"]="global_off"
    elif change=="report_string":clean["zones"][0]["observed_at"]=str(NOW-3)
    with pytest.raises(ValueError):retained_contract_evidence(clean,NOW,120)


def test_stale_original_context_keeps_times_without_optimistic_freshness_or_rewriting_raw_off():
    raw=raw_contract(); original=raw["observed_at"]
    clean=contract_evidence(raw,NOW+121,120)
    assert clean["verified"] is False and clean["fresh"] is False
    assert clean["observed_at"]==original and clean["raw_device_action"]=="OFF"
    assert clean["action_semantics"]=="special_status"
    assert retained_contract_evidence(clean,NOW+121,120)==clean
    with pytest.raises(ValueError):retained_contract_evidence(clean,NOW,120)


def test_restore_does_not_apply_wider_new_source_stale_policy_to_old_capture():
    raw=raw_contract(); raw["stale_s"]=60
    clean=contract_evidence(raw,NOW,120)
    assert clean["stale_s"]==60
    assert retained_contract_evidence(clean,NOW,300)==clean
    with pytest.raises(ValueError):retained_contract_evidence(clean,NOW,30)


def test_overflow_and_nonfinite_numeric_contexts_are_unknown_not_raised():
    for bad in (10**1000,float("nan"),float("inf"),float("-inf"),True,"123"):
        raw=raw_contract(); raw["observed_at"]=bad
        clean=contract_evidence(raw,NOW,120)
        assert clean["observed_at"] is None and clean["verified"] is False
        assert retained_contract_evidence(clean,NOW,120)==clean
