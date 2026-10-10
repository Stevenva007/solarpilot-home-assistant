"""Production options and frontend evidence boundaries for SG scope/split meters."""
import ast
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from custom_components.solar_pilot.sg_config import normalize_config, actuator_conflicts
from test_sg_config62 import actual_flow_class, hass_with
from test_sg_ui_platforms62 import attributes, execute, text, Markup


@pytest.fixture
def flow():
    class Flow(actual_flow_class()):
        def _base_options(self):
            return self.options

        def _site(self):
            return {"pv_entity": "sensor.pv"}

        def async_show_form(self, **kwargs):
            return kwargs

        async def _save(self, options):
            self.saved = options
            return {"saved": options}

    result = Flow()
    result.options = {"sg_boost": normalize_config({"entity_id": "switch.sg_contact",
        "commissioning_confirmed": True, "watchdog_confirmed": True,
        "profile_confirmed": True, "cooling_protection_confirmed": True})}
    result.saved = None
    result.hass = hass_with(**{"switch.sg_contact": {}, "switch.sg_other": {},
        "sensor.pv": {"unit_of_measurement": "W"},
        "sensor.supply1": {"unit_of_measurement": "W"},
        "sensor.supply2": {"unit_of_measurement": "kW"},
        "sensor.supply3": {"unit_of_measurement": "W"},
        "sensor.native_activity": {}})
    return result


@pytest.mark.asyncio
async def test_new_profile_does_not_inherit_checked_scope_or_cooling_proof(flow):
    submission = {"entity_id": "switch.sg_contact", "profile": "general",
        "profile_confirmed": True, "cooling_protection_confirmed": True,
        "enabled": True, "commissioning_confirmed": True, "watchdog_confirmed": True}
    first = await flow.async_step_sg_boost(submission)
    assert first["errors"]["profile_confirmed"] == "sg_profile_review"
    assert flow.saved is None
    # The second explicit submission belongs to the fresh review, rather than
    # an old checked checkbox carried over from the previous scope.
    second = await flow.async_step_sg_boost(submission)
    assert second["saved"]["sg_boost"]["profile"] == "general"
    assert second["saved"]["sg_boost"]["profile_confirmed"] is True
    assert not flow.hass.services.calls


@pytest.mark.asyncio
async def test_changed_scope_cannot_be_saved_without_new_explicit_confirmation(flow):
    first = await flow.async_step_sg_boost({"entity_id": "switch.sg_contact", "profile": "general"})
    second = await flow.async_step_sg_boost({"entity_id": "switch.sg_contact", "profile": "general"})
    assert first["errors"]["profile_confirmed"] == second["errors"]["profile_confirmed"] == "sg_profile_review"
    assert flow.saved is None


@pytest.mark.asyncio
async def test_changed_physical_binding_revokes_profile_and_cooling_proof(flow):
    result = await flow.async_step_sg_boost({"entity_id": "switch.sg_other",
        "profile_confirmed": True, "cooling_protection_confirmed": True,
        "enabled": True, "commissioning_confirmed": True, "watchdog_confirmed": True})
    saved = result["saved"]["sg_boost"]
    assert all(saved[key] is False for key in ("enabled", "commissioning_confirmed",
        "watchdog_confirmed", "profile_confirmed", "cooling_protection_confirmed"))


@pytest.mark.asyncio
async def test_changed_split_pair_does_not_inherit_checked_coverage_proof(flow):
    flow.options["sg_boost"].update(power_supply1_entity="sensor.supply1",
        power_supply2_entity="sensor.supply2", split_power_confirmed=True)
    submission = {"power_supply1_entity": "sensor.supply1", "power_supply2_entity": "sensor.supply3",
        "split_power_confirmed": True, "power_scope": "unconfirmed"}
    first = await flow.async_step_sg_sources(submission)
    assert first["errors"]["split_power_confirmed"] == "sg_split_review" and flow.saved is None
    second = await flow.async_step_sg_sources(submission)
    assert second["saved"]["sg_boost"]["split_power_confirmed"] is True


@pytest.mark.asyncio
async def test_changed_native_source_revokes_cooling_proof(flow):
    result = await flow.async_step_sg_sources({"power_scope": "unconfirmed",
        "activity_entity": "sensor.native_activity"})
    assert result["saved"]["sg_boost"]["cooling_protection_confirmed"] is False
    assert not flow.hass.services.calls


def live_flow(options):
    path = Path(__file__).parents[1] / "custom_components/solar_pilot/live_config.py"
    cls = next(node for node in ast.parse(path.read_text()).body if isinstance(node, ast.ClassDef))
    env = {"deepcopy": deepcopy, "normalize_sg": normalize_config,
        "actuator_conflicts": actuator_conflicts, "HomeAssistantError": RuntimeError}
    exec(compile(ast.Module(body=[cls], type_ignores=[]), str(path), "exec"), env)

    class Flow(env["LiveOptionsMixin"]):
        async def async_step_apply_changes(self, user_input=None):
            return self._live_desired

    result = Flow()
    result.config_entry = SimpleNamespace(options=options)
    return result


@pytest.mark.asyncio
async def test_imported_scope_and_meter_proof_do_not_grant_new_authority():
    current = {"sg_boost": normalize_config({"entity_id": "switch.sg_contact", "profile_confirmed": True})}
    flow = live_flow(current)
    desired = deepcopy(current)
    desired["sg_boost"].update(profile="general", profile_confirmed=True,
        cooling_protection_confirmed=True, enabled=True, split_power_confirmed=True,
        power_supply1_entity="sensor.supply1", power_supply2_entity="sensor.supply2")
    result = await flow._live_save(desired)
    assert all(result["sg_boost"][key] is False for key in ("enabled", "profile_confirmed",
        "cooling_protection_confirmed", "split_power_confirmed"))
    assert desired["sg_boost"]["enabled"] is True  # input not mutated


@pytest.mark.parametrize("running,frequency,label", [(True, 31, "compressor draait"),
    (False, 0, "compressor stil"), (None, None, None)])
def test_compressor_and_received_sg_are_separate_evidence(running, frequency, label):
    data = attributes(desired_on=True, relay_on=True, owner="solarpilot", lease_confirmed=True, lease_remaining_s=170)
    data["panasonic"].update(compressor_running=running, compressor_frequency_hz=frequency,
        sg_status="unknown", sg_status_confirmed=False,
        operation={"state": "active" if running is True else "idle" if running is False else "unknown",
                   "label": label or "Werking onbekend", "evidence": "compressor_frequency" if running is not None else "none",
                   "observed_at": data["panasonic"]["compressor_stamp"], "stale_s": 120})
    result = execute(data)
    rendered = text(result["initial"])
    root = Markup(result["initial"]).root
    if label:
        assert label in rendered and f"{frequency} Hz" in rendered
        operation = next(n for n in root.walk() if "data-heatpump-operation" in n.attributes)
        assert operation.attributes["data-compressor-running"] == ("true" if running else "false")
    else:
        assert "compressorstatus onbekend" not in rendered and "Werking onbekend" not in rendered
        assert not any("data-heatpump-operation" in n.attributes for n in root.walk())
    assert [n.attributes["data-sg-stage"] for n in root.walk() if "data-sg-stage" in n.attributes] == ["relay"]
    assert "Ontvangen SG-status" not in rendered
    assert "Compressorbedrijf bewijst geen extra verbruik door SG" in rendered
    assert "SolarPilot-aanvraag Aangevraagd" in rendered
    assert "Eigenaar SG-aanvraag SolarPilot" in rendered
    assert not result["calls"]


def test_manual_contact_has_no_invented_local_permission_or_compressor_start():
    data = attributes(desired_on=False, relay_on=True, manual_hold=True,
        owner="manual", lease_confirmed=False, lease_remaining_s=300)
    data["panasonic"].update(program="dhw", activity="WATER", compressor_running=None)
    result = execute(data)
    rendered = text(result["initial"])
    root = Markup(result["initial"]).root
    assert "Bevestigde lokale toestemming Niet bevestigd" in rendered
    assert "compressorstatus onbekend" not in rendered and "Werking onbekend" not in rendered
    assert not any("data-heatpump-operation" in n.attributes for n in root.walk())
    assert next(n for n in root.walk() if "data-activity" in n.attributes).attributes["data-activity"] == "unknown"
    assert "Geen zonneboost aangevraagd; het SG-contact is nog actief" in rendered
    assert "Handmatige overname" in rendered
    assert not result["calls"]


@pytest.mark.parametrize("view", ["comfort", "board"])
def test_missing_relay_value_never_becomes_an_open_contact_in_summary(view):
    rendered = text(execute(attributes(relay_on=None, relay_confirmed=True), view=view)["initial"])
    assert "SG-contact open" not in rendered
    assert "Onbekend" in rendered or "onbekend" in rendered


def test_complete_split_shows_known_zero_and_one_total_without_sg_causation():
    data = attributes()
    data["panasonic"].update(power_scope="split", power_w=1450, power_complete=True,
        power_supply1_w=1450, power_supply2_w=0, power_supply1_valid=True, power_supply2_valid=True,
        compressor_running=True, sg_status="active", sg_status_confirmed=True)
    rendered = text(execute(data)["initial"])
    assert "voeding 1 1,45 kW · voeding 2 0 W" in rendered
    assert "Totaal voeding 1 + voeding 2" in rendered
    assert "Ontvangen SG-status Actief · afzonderlijk bevestigd" in rendered
    assert "SG-effect op verbruik" not in rendered
    assert "Compressorbedrijf bewijst geen extra verbruik door SG" in rendered


def test_incomplete_split_retains_one_part_and_marks_total_unknown():
    data = attributes()
    data["panasonic"].update(power_scope="split", power_w=None, power_kind="unknown", power_complete=False,
        power_supply1_w=650, power_supply2_w=None, power_supply1_valid=True, power_supply2_valid=False)
    rendered = text(execute(data)["initial"])
    assert "voeding 1 650 W · voeding 2 onbekend" in rendered
    assert "Totaal onbekend · deelmeting onvolledig" in rendered
    assert "Vermogen nog niet bekend" in rendered


def test_general_profile_and_cooling_check_are_independent_visible_facts():
    data = attributes(profile="general", profile_confirmed=True, cooling_protection_confirmed=False,
        reason="Extra SG-koeling geblokkeerd: condensbeveiliging niet bevestigd")
    rendered = text(execute(data)["initial"])
    assert "Toepassingsbereik Algemene SG-boost" in rendered
    assert "Profiel lokaal bevestigd Ja" in rendered
    assert "Extra-koelbeveiliging Niet bevestigd" in rendered
    assert "condensbeveiliging niet bevestigd" in rendered
