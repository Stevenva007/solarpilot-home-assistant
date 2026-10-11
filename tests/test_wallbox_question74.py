"""Session questions diagnose explicit sources and grant no EV authority."""
from copy import deepcopy

import pytest

from test_runtime import build


def session_runtime(*, bound=True, value="unavailable", age=0, mode="Full solar", enabled=True):
    runtime, hass = build()
    runtime.wallbox_settings.update(enabled=enabled, power_entity="sensor.ev_power",
        status_entity="sensor.ev_status", mode_entity="sensor.ev_mode",
        session_mode_entity="sensor.ev_session" if bound else "", trust_solar_setting=False)
    hass.states.set("sensor.ev_power", 1300, {"unit_of_measurement": "W"})
    hass.states.set("sensor.ev_status", "Charging")
    hass.states.set("sensor.ev_mode", mode)
    hass.states.set("sensor.ev_session", value, reported_age=age)
    return runtime, hass


def question(runtime):
    return next((row for row in runtime.learning_hub.refresh(force=True)["questions"]
                 if row["id"] == "wallbox_session"), None)


def assert_read_only_unknown(runtime, hass, before):
    reading = runtime._wallbox_reading()
    assert reading.mode == "unknown" and reading.session_confirmed is False
    runtime.wallbox_guard.update(1000, reading, -500, 150)
    assert getattr(runtime.wallbox_guard, "reclaimable_w", 0) == 0
    assert runtime.wallbox_settings == before and not hass.services.calls


def test_missing_binding_asks_for_configuration_and_does_not_discover_existing_candidate():
    runtime, hass = session_runtime(bound=False, value="Zonne-auto · laden")
    before = deepcopy(runtime.wallbox_settings)
    finding = question(runtime)
    assert "Koppel onder Opslag & laden" in finding["message"]
    assert "al gekoppeld" not in finding["message"]
    assert finding["id"] == "wallbox_session"
    assert [choice["id"] for choice in finding["choices"]] == ["configure", "keep", "later"]
    assert_read_only_unknown(runtime, hass, before)


def test_old_real_report_is_diagnosed_even_when_last_updated_is_recent():
    runtime, hass = session_runtime(value="Laden gestopt", age=4900)
    before = deepcopy(runtime.wallbox_settings)
    finding = question(runtime)
    assert "al gekoppeld" in finding["message"]
    assert "ouder dan de ingestelde grens van 300 seconden" in finding["message"]
    assert "Koppel onder" not in finding["message"]
    assert "actualiteit" in finding["message"]
    assert_read_only_unknown(runtime, hass, before)


@pytest.mark.parametrize("value", ["unknown", "unavailable", ""])
def test_unknown_bound_sensor_is_not_described_as_an_absent_binding(value):
    runtime, hass = session_runtime(value=value)
    before = deepcopy(runtime.wallbox_settings)
    finding = question(runtime)
    assert "al gekoppeld" in finding["message"]
    assert "onbekend, onbeschikbaar" in finding["message"]
    assert "Koppel onder" not in finding["message"]
    assert_read_only_unknown(runtime, hass, before)


def test_bound_entity_missing_in_ha_reports_broken_existing_source():
    runtime, hass = session_runtime()
    hass.states.data.pop("sensor.ev_session")
    before = deepcopy(runtime.wallbox_settings)
    assert "gekoppelde bron ontbreekt in Home Assistant" in question(runtime)["message"]
    assert_read_only_unknown(runtime, hass, before)


def test_restored_bound_value_is_not_promoted_to_session_confirmation():
    runtime, hass = session_runtime(value="Zonne-auto · laden")
    hass.states.get("sensor.ev_session").attributes["restored"] = True
    before = deepcopy(runtime.wallbox_settings)
    assert "herstelde waarde" in question(runtime)["message"]
    assert_read_only_unknown(runtime, hass, before)


@pytest.mark.parametrize("kind", ["missing", "future"])
def test_invalid_source_time_stays_unknown_and_is_explained(kind):
    runtime, hass = session_runtime(value="Zonne-auto · laden", age=-60 if kind == "future" else 0)
    if kind == "missing":
        hass.states.get("sensor.ev_session").last_reported = None
        hass.states.get("sensor.ev_session").last_updated = None
    before = deepcopy(runtime.wallbox_settings)
    assert "geen betrouwbaar rapporttijdstip" in question(runtime)["message"]
    assert_read_only_unknown(runtime, hass, before)


@pytest.mark.parametrize("value,mode", [("anders", "Full solar"), ("Zonne-auto · laden", "off")])
def test_fresh_unmapped_or_contradictory_session_requests_mapping_review(value, mode):
    runtime, hass = session_runtime(value=value, mode=mode)
    before = deepcopy(runtime.wallbox_settings)
    finding = question(runtime)
    assert "al gekoppeld en actueel" in finding["message"]
    assert "niet herkend of is strijdig" in finding["message"]
    assert "statuslijsten" in finding["message"]
    assert_read_only_unknown(runtime, hass, before)


@pytest.mark.parametrize("value,expected", [("Manueel laden", "manual"), ("Laden gestopt", "stopped"),
                                          ("Zonne-auto · laden", "Full solar")])
def test_fresh_consistent_session_does_not_create_a_failure_question(value, expected):
    runtime, hass = session_runtime(value=value)
    before = deepcopy(runtime.wallbox_settings)
    assert question(runtime) is None
    reading = runtime._wallbox_reading()
    assert reading.mode == expected and reading.session_confirmed is True
    assert runtime.wallbox_settings == before and not hass.services.calls


def test_disabled_wallbox_does_not_raise_a_session_configuration_question():
    runtime, hass = session_runtime(enabled=False)
    assert question(runtime) is None and not hass.services.calls


def test_question_revision_changes_with_cause_and_stays_stable_while_a_report_ages():
    runtime, hass = session_runtime(value="Zonne-auto · laden", age=1000)
    first = question(runtime)
    hass.states.set("sensor.ev_session", "Zonne-auto · laden", reported_age=2000)
    second = question(runtime)
    assert second["revision"] == first["revision"] and second["message"] == first["message"]
    hass.states.set("sensor.ev_session", "unavailable")
    changed = question(runtime)
    assert changed["id"] == first["id"]
    assert changed["revision"] != first["revision"]
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_old_question_answer_cannot_suppress_a_changed_source_failure():
    runtime, hass = session_runtime(value="Zonne-auto · laden", age=1000)
    before = deepcopy(runtime.wallbox_settings)
    first = question(runtime)
    await runtime.learning_hub.answer(first["id"], first["revision"], "keep")
    assert question(runtime) is None
    hass.states.set("sensor.ev_session", "unavailable")
    changed = question(runtime)
    assert changed["id"] == first["id"] and changed["revision"] != first["revision"]
    with pytest.raises(ValueError, match="stale_question"):
        await runtime.learning_hub.answer(first["id"], first["revision"], "keep")
    assert_read_only_unknown(runtime, hass, before)


def test_diagnostic_refresh_keeps_idle_activity_separate_from_unknown_session():
    runtime, hass = session_runtime(value="Laden gestopt", age=4900)
    hass.states.set("sensor.ev_power", 0, {"unit_of_measurement": "W"})
    hass.states.set("sensor.ev_status", "Ready")
    before = deepcopy(runtime.wallbox_settings)
    reading = runtime._wallbox_reading()
    runtime.wallbox_guard.update(1000, reading, 500, 150)
    overview = runtime.wallbox_overview()
    assert overview["activity_known"] is True and overview["active"] is False
    assert overview["effective_mode"] == "unknown" and overview["reclaim_allowed_now"] is False
    assert "ouder dan" in question(runtime)["message"]
    assert_read_only_unknown(runtime, hass, before)


def test_learning_model_description_names_native_transitions_without_compressor_claim():
    runtime, hass = session_runtime()
    model = next(row for row in runtime.learning_hub.refresh(force=True)["models"] if row["id"] == "heatpump")
    assert "bevestigde native taakovergangen" in model["effect"]
    assert "compressorstarts" not in model["effect"]
    assert not hass.services.calls
