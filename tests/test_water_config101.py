"""Exercise the actual Water options form with explicit, metadata-bound sources."""
import ast
from collections.abc import Mapping
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace as NS

import pytest

from custom_components.solar_pilot.water import WATER_DEFAULTS, normalize_config, source_errors


ROOT = Path(__file__).resolve().parents[1]
C = ROOT / "custom_components/solar_pilot"
SOURCES = ("volume_entity", "flow_entity", "leak_entity")


def actual_options_class():
    """Use production method bodies; doubles replace only the native form widgets."""
    path = C / "config_flow.py"
    tree = ast.parse(path.read_text())
    cls = next(node for node in tree.body if isinstance(node, ast.ClassDef)
               and node.name == "SolarPilotOptions")
    cls.bases = []
    cls.keywords = []
    env = {
        "Mapping": Mapping, "deepcopy": deepcopy, "WATER_DEFAULTS": WATER_DEFAULTS,
        "normalize_water": normalize_config, "water_errors": source_errors,
        "vol": NS(Required=lambda key, **kw: key, Schema=lambda data: data),
        "selector": NS(BooleanSelector=lambda: "bool"),
        "optional": lambda key, values: key, "entity": lambda domains: domains,
        "num": lambda low, high, step=1: (low, high, step),
    }
    exec(compile(ast.fix_missing_locations(ast.Module(body=[cls], type_ignores=[])),
                 str(path), "exec"), env)
    return env["SolarPilotOptions"]


@pytest.fixture
def flow():
    class Flow(actual_options_class()):
        def _base_options(self):
            return self.options

        def async_show_form(self, **kwargs):
            return kwargs

        def async_show_menu(self, **kwargs):
            return kwargs

        async def _save(self, options):
            self.saved = options
            return {"saved": options}

    f = Flow()
    f.options = {"settings": {"grid_entity": "sensor.example_grid"},
                 "devices": [{"id": "retained_device", "enabled": False}],
                 "_private_unknown": {"keep": [1, 2, 3]}}
    f.saved = None
    f.reads = []
    f.states = {
        "sensor.example_water_total": NS(state="12.3", attributes={
            "device_class": "water", "state_class": "total_increasing", "unit_of_measurement": "m³"}),
        "sensor.example_water_flow": NS(state="0", attributes={
            "device_class": "volume_flow_rate", "state_class": "measurement", "unit_of_measurement": "L/min"}),
        "binary_sensor.example_water_leak": NS(state="off", attributes={"device_class": "moisture"}),
    }

    def read(entity_id):
        f.reads.append(entity_id)
        return f.states.get(entity_id)

    def forbidden(*args, **kwargs):
        raise AssertionError("A settings form cannot operate a device or auto-discover unrelated sources")

    f.hass = NS(states=NS(get=read, async_all=forbidden),
                services=NS(async_call=forbidden, call=forbidden))
    return f


@pytest.mark.asyncio
async def test_water_is_its_own_options_step_and_opening_selects_nothing(flow):
    before = deepcopy(flow.options)
    menu = await flow.async_step_init()
    form = await flow.async_step_water()
    assert menu["menu_options"].count("water") == 1
    assert form["step_id"] == "water" and not form["errors"]
    assert set(form["data_schema"]) == set(WATER_DEFAULTS)
    assert form["data_schema"]["volume_entity"] == ["sensor"]
    assert form["data_schema"]["flow_entity"] == ["sensor"]
    assert form["data_schema"]["leak_entity"] == ["binary_sensor"]
    assert flow.options == before and flow.saved is None and not flow.reads
    assert WATER_DEFAULTS["enabled"] is False
    assert all(WATER_DEFAULTS[key] == "" for key in SOURCES)


@pytest.mark.asyncio
@pytest.mark.parametrize("key,entity_id", [
    ("volume_entity", "sensor.example_water_total"),
    ("flow_entity", "sensor.example_water_flow"),
    ("leak_entity", "binary_sensor.example_water_leak"),
])
async def test_each_explicit_source_can_enable_the_independent_read_only_monitor(flow, key, entity_id):
    before = deepcopy(flow.options)
    result = await flow.async_step_water({"enabled": True, key: entity_id})
    saved = result["saved"]
    assert saved["water"]["enabled"] is True and saved["water"][key] == entity_id
    assert {name: saved[name] for name in before} == before == flow.options
    assert set(flow.reads) == {entity_id}


@pytest.mark.asyncio
async def test_enabled_monitor_needs_an_explicit_source_even_when_discoverable_sensors_exist(flow):
    form = await flow.async_step_water({"enabled": True})
    assert form["errors"] and flow.saved is None and not flow.reads


@pytest.mark.asyncio
async def test_completed_form_clears_omitted_sources_and_preserves_unknown_private_fields(flow):
    flow.options["water"] = {**WATER_DEFAULTS,
        "volume_entity": "sensor.example_water_total", "flow_entity": "sensor.example_water_flow",
        "leak_entity": "binary_sensor.example_water_leak", "future_private_schema": {"keep": [1, 2]}}
    before = deepcopy(flow.options)
    result = await flow.async_step_water({"enabled": True, "flow_entity": "sensor.example_water_flow"})
    saved = result["saved"]["water"]
    assert saved["volume_entity"] == saved["leak_entity"] == ""
    assert saved["flow_entity"] == "sensor.example_water_flow"
    assert saved["future_private_schema"] == {"keep": [1, 2]}
    assert flow.options == before


@pytest.mark.asyncio
@pytest.mark.parametrize("source_state", ["unavailable", "unknown"])
@pytest.mark.parametrize("key,entity_id", [
    ("volume_entity", "sensor.example_water_total"),
    ("flow_entity", "sensor.example_water_flow"),
    ("leak_entity", "binary_sensor.example_water_leak"),
])
async def test_temporarily_offline_source_with_correct_metadata_remains_configurable(flow, source_state, key, entity_id):
    flow.states[entity_id].state = source_state
    result = await flow.async_step_water({"enabled": True, key: entity_id})
    assert result["saved"]["water"][key] == entity_id


@pytest.mark.asyncio
@pytest.mark.parametrize("key,entity_id,attributes", [
    ("volume_entity", "sensor.wrong", {"device_class": "energy", "state_class": "total_increasing", "unit_of_measurement": "kWh"}),
    ("flow_entity", "sensor.wrong", {"device_class": "water", "state_class": "total_increasing", "unit_of_measurement": "L"}),
    ("leak_entity", "binary_sensor.wrong", {"device_class": "motion"}),
    ("flow_entity", "number.wrong", {"device_class": "volume_flow_rate", "unit_of_measurement": "L/min"}),
    ("leak_entity", "switch.wrong", {"device_class": "moisture"}),
])
async def test_wrong_metadata_or_domain_cannot_be_saved_as_water_source(flow, key, entity_id, attributes):
    flow.states[entity_id] = NS(state="0", attributes=attributes)
    before = deepcopy(flow.options)
    form = await flow.async_step_water({"enabled": True, key: entity_id})
    assert key in form["errors"] and flow.saved is None and flow.options == before


@pytest.mark.asyncio
@pytest.mark.parametrize("key,value", [
    ("enabled", "true"), ("enabled", 0), ("enabled", 0.0),
    ("notifications", 1), ("notifications", 1.0),
    ("source_stale_s", float("nan")), ("source_stale_s", True),
    ("continuous_flow_l_min", -1), ("continuous_flow_l_min", float("inf")),
    ("continuous_flow_minutes", 0), ("continuous_flow_minutes", False),
])
async def test_invalid_settings_are_reported_without_replacing_existing_options(flow, key, value):
    before = deepcopy(flow.options)
    form = await flow.async_step_water({key: value})
    assert key in form["errors"] and flow.saved is None and flow.options == before


@pytest.mark.asyncio
async def test_disabling_and_turning_off_notifications_stays_a_settings_change_only(flow):
    flow.options["water"] = {**WATER_DEFAULTS, "enabled": True,
                             "volume_entity": "sensor.example_water_total"}
    result = await flow.async_step_water({"enabled": False, "notifications": False})
    assert result["saved"]["water"]["enabled"] is False
    assert result["saved"]["water"]["notifications"] is False
    assert result["saved"]["water"]["volume_entity"] == ""


def test_water_labels_help_and_errors_match_the_actual_form_contract():
    nl = json.loads((C / "translations/nl.json").read_text())
    en = json.loads((C / "translations/en.json").read_text())
    fields = set(WATER_DEFAULTS)
    assert set(nl["options"]["step"]["water"]["data"]) == fields
    assert set(en["options"]["step"]["water"]["data"]) == fields
    assert "water" in nl["options"]["step"]["init"]["menu_options"]
    assert "water" in en["options"]["step"]["init"]["menu_options"]
    spec = importlib.util.spec_from_file_location("water_help101", C / "option_help.py")
    help_module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(help_module)
    for field, label in nl["options"]["step"]["water"]["data"].items():
        help_text = " ".join(help_module.help_for("water", field, label)["paragraphs"])
        assert len(help_text) > 180
        assert "water" in help_text.lower()


def test_every_water_source_validation_error_has_native_nl_and_en_text(flow):
    samples = [{"enabled": True}, {"notifications": 1},
               {"enabled": True, "volume_entity": "sensor.missing_volume"},
               {"enabled": True, "flow_entity": "sensor.missing_flow"},
               {"enabled": True, "leak_entity": "binary_sensor.missing_leak"}]
    codes = {code for sample in samples for code in source_errors(flow.hass, sample).values()}
    assert {"invalid_water_setting", "water_source_required", "water_volume_source",
            "water_flow_source", "water_leak_source"} <= codes
    for language in ("nl", "en"):
        errors = json.loads((C / f"translations/{language}.json").read_text())["options"]["error"]
        assert codes <= set(errors)
        assert all(len(errors[code]) > 30 for code in codes)

