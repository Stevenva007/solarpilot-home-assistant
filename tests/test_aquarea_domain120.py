"""Read-only compatibility with the exact Aquarea v3 prerelease domain.

Upstream v3.0.0 only moved the provider package and registry domain to
``aquarea_smart_cloud``; a same-day main-branch revert did not alter the tagged
package.  These regressions never install that prerelease or call a service.
"""
import importlib.metadata
import json
import sys
from types import ModuleType, SimpleNamespace as NS

from custom_components.solar_pilot import analysis_export as ae
from custom_components.solar_pilot.cloud_energy_period import cloud_energy_periods
from custom_components.solar_pilot.operation_source_evidence import contract_evidence
from test_aquarea_display_snapshot86 import AquareaDataUpdateCoordinator, modern_setup
from test_cloud_energy_period91 import setup_source


DOMAIN = "aquarea_smart_cloud"


def v3_setup(monkeypatch):
    env = modern_setup(monkeypatch, version="3.0.0")
    provider = ModuleType(f"custom_components.{DOMAIN}")
    monkeypatch.delitem(sys.modules, "custom_components.aquarea", raising=False)
    monkeypatch.setitem(sys.modules, provider.__name__, provider)
    monkeypatch.setattr(AquareaDataUpdateCoordinator, "__module__", f"custom_components.{DOMAIN}.coordinator")
    env.entries["native"].domain = DOMAIN
    env.devices["registry_pump"].identifiers = {(DOMAIN, "pump")}
    for row in env.rows.values():
        row.platform = DOMAIN

    old_id = env.sources["pump_status_entity"]
    row = env.rows.pop(old_id)
    pump_id = old_id.replace("sensor.", "binary_sensor.", 1)
    env.rows[pump_id] = NS(**{**vars(row), "entity_id": pump_id})
    state = env.helper.runtime.hass.states.data.pop(old_id)
    state.entity_id = pump_id
    env.helper.runtime.hass.states.data[pump_id] = state
    env.state(pump_id, "on")
    env.state(env.sources["direction_entity"], "pump")

    env.helper._display_metadata.update(integration_domain=DOMAIN, integration_version="3.0.0")
    env.helper._display_metadata_domain = DOMAIN
    env.helper._display_metadata_module = provider
    env.sources = env.helper.display_sources()
    return env, pump_id


def test_v3_domain_keeps_exact_read_only_live_contract(monkeypatch):
    env, pump_id = v3_setup(monkeypatch)
    assert env.sources["pump_status_entity"] == pump_id
    assert env.helper.read_source_contract(env.sources)["status"] == "unknown"

    env.coordinator.poll()
    result = env.helper.read_source_contract(env.sources)
    assert result["status"] == "verified"
    assert result["provider"]["integration_domain"] == DOMAIN
    assert result["provider"]["integration_version"] == "3.0.0"
    assert result["read_only"] is True
    assert contract_evidence(result, 1000, 120)["verified"] is True
    assert env.coordinator.api_calls == []
    assert env.helper.runtime.hass.services.calls == []


def test_v3_domain_never_borrows_old_domain_registry_identity(monkeypatch):
    env, _pump_id = v3_setup(monkeypatch)
    direction = env.sources["direction_entity"]
    env.rows[direction].platform = "aquarea"
    env.coordinator.poll()
    sources = env.helper.display_sources()
    assert sources["direction_entity"] == ""
    result = env.helper.read_source_contract(sources)
    assert result["status"] == "unknown"
    assert result["reason_code"] == "native_source_mapping_unverified"


def test_v3_domain_preserves_existing_native_cloud_period_contract(monkeypatch):
    env = setup_source(monkeypatch)
    env.row.platform = env.entry.domain = DOMAIN
    env.device.identifiers = {(DOMAIN, "pump")}
    monkeypatch.setattr(env.entity.__class__, "__module__", f"custom_components.{DOMAIN}.sensor")
    monkeypatch.setattr(env.coordinator.__class__, "__module__", f"custom_components.{DOMAIN}.coordinator")
    provider = {"integration_loaded": True, "integration_domain": DOMAIN,
                "integration_version": "3.0.0", "library_distribution": "aioaquarea-ng",
                "library_version": "1.6.0"}
    result = cloud_energy_periods(env.hass, [env.eid], provider, captured_at=env.captured)[env.eid]
    assert result["status"] == "known_period"
    assert result["provider"]["integration_domain"] == DOMAIN
    assert result["period_start"] == env.entity.period_being_processed.isoformat()


def test_v3_loaded_manifest_reports_actual_domain_and_sdk(monkeypatch, tmp_path):
    provider = ModuleType(f"custom_components.{DOMAIN}")
    provider.__file__ = str(tmp_path / "__init__.py")
    monkeypatch.delitem(sys.modules, "custom_components.aquarea", raising=False)
    monkeypatch.setitem(sys.modules, provider.__name__, provider)
    (tmp_path / "manifest.json").write_text(json.dumps({
        "domain": DOMAIN, "version": "3.0.0", "requirements": ["aioaquarea-ng>=1.6.0"]
    }), encoding="utf-8")
    monkeypatch.setattr(importlib.metadata, "version", lambda name: "1.6.0" if name == "aioaquarea-ng"
                        else (_ for _ in ()).throw(importlib.metadata.PackageNotFoundError(name)))
    result = ae.installed_aquarea_metadata()
    assert result["integration_loaded"] is True
    assert result["integration_domain"] == DOMAIN
    assert result["integration_version"] == "3.0.0"
    assert result["library_distribution"] == "aioaquarea-ng"
    assert result["library_version"] == "1.6.0"


def test_two_loaded_provider_domains_are_ambiguous(monkeypatch):
    monkeypatch.setitem(sys.modules, "custom_components.aquarea", ModuleType("custom_components.aquarea"))
    monkeypatch.setitem(sys.modules, f"custom_components.{DOMAIN}", ModuleType(f"custom_components.{DOMAIN}"))
    result = ae.installed_aquarea_metadata()
    assert result["integration_loaded"] is False
    assert result["integration_domain"] is None
    assert result["integration_version"] is None
