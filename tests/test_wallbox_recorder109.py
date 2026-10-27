"""Large live Wallbox profiles must not flood recorder or scalar sensors."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from test_sensor_recorder59 import sensor, recorder_payload, payload_bytes, RECORDER_ATTRIBUTE_LIMIT
from test_runtime import build


@pytest.mark.parametrize("power", [0.0, 4200.0, None])
def test_power_sensor_publishes_only_scalar_evidence_without_changing_source(power):
    runtime, hass = build()
    overview = {
        "power_w": power,
        "charging_profile": {"samples": [{"power_w": 4200}] * 2000},
        "activity_details": {"history": ["charging"] * 2000},
        "reclaim_blocks": {"example": {"reason": "waiting"}},
        "consumer_priority": {"devices": ["example"] * 2000},
        "state": "unknown" if power is None else "charging",
    }
    original = deepcopy(overview)
    runtime.wallbox_overview = lambda: overview
    entity = sensor(runtime, "wallbox_power")

    assert entity.native_value == power
    assert entity.extra_state_attributes == {"power_w": power}
    assert payload_bytes(entity.extra_state_attributes) < 100
    assert overview == original
    assert not hass.services.calls


def test_status_preserves_live_profiles_but_records_only_small_status_fields():
    runtime, hass = build()
    overview = {
        "power_w": 4200.0, "state": "charging", "reason": "Solar session",
        "charging_profile": {"samples": [{"power_w": 4200}] * 2000},
        "activity_details": {"history": ["charging"] * 2000},
        "reclaim_blocks": {"example": {"samples": [0] * 10000}},
        "consumer_priority": {"devices": ["example"] * 2000},
    }
    runtime.wallbox_overview = lambda: overview
    entity = sensor(runtime, "wallbox_status")

    assert entity.extra_state_attributes is overview
    assert payload_bytes(overview) > RECORDER_ATTRIBUTE_LIMIT
    assert recorder_payload(entity, overview) == {
        "power_w": 4200.0, "state": "charging", "reason": "Solar session",
    }
    assert not hass.services.calls


def test_wallbox_power_constructor_retains_watt_measurement_metadata():
    from test_electricity_sensor import sensor_class
    cls = sensor_class()
    namespace = cls.__init__.__globals__
    namespace["SensorDeviceClass"] = SimpleNamespace(POWER="power")
    namespace["SensorStateClass"] = SimpleNamespace(MEASUREMENT="measurement")
    entity = cls(SimpleNamespace(), "wallbox_power", "Wallbox power")
    assert entity._attr_native_unit_of_measurement == "W"
    assert entity._attr_device_class == "power"
    assert entity._attr_state_class == "measurement"
