"""Large legacy learning stays private and lossless, without live payload growth."""
from copy import deepcopy
import json

import pytest

from test_runtime import build


def large_archive(runtime, *, count=12000):
    historical = {"profiles": {"climate.public_zone": {
        "samples": count,
        "observations": [{"at": 1_790_000_000 + index * 900,
                          "indoor_c": 21.15, "outdoor_c": 14.2,
                          "action": "off", "sample_index": index}
                         for index in range(count)],
        "evidence_note": "Public fixture historical evidence",
    }}, "expected_mode": {"climate.public_zone": "off"}}
    runtime.panasonic_archive = {"read_only": True,
        "backup_options": deepcopy(runtime.entry.options),
        "backup_store": {"smart_climate": deepcopy(historical)}}
    runtime.panasonic.learning_archive = deepcopy(historical)
    return historical


def test_large_archive_does_not_expand_or_disclose_live_learning_payload():
    runtime, hass = build()
    historical = large_archive(runtime)
    before = deepcopy(runtime.panasonic_archive)

    live = runtime.panasonic.learning_overview()
    complete_live = runtime.learning_overview()

    assert live["read_only"] is True and live["archive_available"] is True
    assert "archived" not in live and "observations" not in json.dumps(complete_live)
    assert "Public fixture historical evidence" not in json.dumps(complete_live)
    assert len(json.dumps(live).encode()) < 1024
    assert runtime.panasonic_archive == before
    assert runtime.panasonic.learning_archive == historical
    assert not hass.services.calls


def test_archive_snapshot_retains_every_sample_and_is_independent_of_live_summary():
    runtime, hass = build()
    historical = large_archive(runtime)
    archived = runtime._snapshot()["panasonic_archive"]

    assert archived == runtime.panasonic_archive
    assert archived["backup_store"]["smart_climate"] == historical
    archived["backup_store"]["smart_climate"]["profiles"]["climate.public_zone"]["observations"].clear()
    assert len(runtime.panasonic.learning_archive["profiles"]["climate.public_zone"]["observations"]) == 12000
    assert len(runtime.panasonic_archive["backup_store"]["smart_climate"]["profiles"]["climate.public_zone"]["observations"]) == 12000
    assert not hass.services.calls


def test_private_analysis_export_contains_full_archive_without_commands():
    runtime, hass = build()
    historical = large_archive(runtime)
    before = deepcopy(runtime.panasonic_archive)
    report = runtime.analysis.build(hours=168, include_names=True)

    exported = report["components"]["runtime_and_models"]["panasonic_archive"]
    assert exported["backup_store"]["smart_climate"] == historical
    assert runtime.panasonic_archive == before
    assert not report["coverage"]["section_errors"]
    assert not hass.services.calls


def test_private_analysis_archive_does_not_silently_drop_old_samples_at_generic_list_limit():
    runtime, hass = build()
    historical = large_archive(runtime, count=50001)
    report = runtime.analysis.build(hours=168, include_names=True)
    exported = report["components"]["runtime_and_models"]["panasonic_archive"]["backup_store"]["smart_climate"]

    assert exported["profiles"]["climate.public_zone"]["observations"] == historical["profiles"]["climate.public_zone"]["observations"]
    assert len(runtime.panasonic.learning_archive["profiles"]["climate.public_zone"]["observations"]) == 50001
    assert not hass.services.calls


@pytest.mark.parametrize("include_names", [False, True])
def test_archive_preserves_deep_and_long_evidence_while_filtering_credentials(include_names):
    runtime, hass = build()
    large_archive(runtime, count=2)
    evidence = {"value": "Public evidence " + "x" * 9000,
                "api_key": "public-fixture-credential",
                "diagnostic": "public evidence https://public.example/status password=public-fixture"}
    for _ in range(30):
        evidence = {"nested_evidence": evidence}
    runtime.panasonic_archive["backup_store"]["deep_evidence"] = evidence
    before = deepcopy(runtime.panasonic_archive)

    report = runtime.analysis.build(hours=168, include_names=include_names)
    exported = report["components"]["runtime_and_models"]["panasonic_archive"]["backup_store"]["deep_evidence"]
    for _ in range(30):
        assert isinstance(exported, dict)
        exported = exported["nested_evidence"]
    assert exported["value"] == "Public evidence " + "x" * 9000
    assert exported["api_key"] == "[REDACTED]"
    assert exported["diagnostic"] == "public evidence [URL REDACTED] password=[REDACTED]"
    assert "public-fixture-credential" not in json.dumps(report)
    assert runtime.panasonic_archive == before
    assert not hass.services.calls


def test_default_private_export_keeps_archive_samples_but_hides_source_names():
    runtime, hass = build()
    historical = large_archive(runtime, count=500)
    report = runtime.analysis.build(hours=168)

    exported = report["components"]["runtime_and_models"]["panasonic_archive"]["backup_store"]["smart_climate"]
    assert "climate.public_zone" not in json.dumps(report)
    profile = next(iter(exported["profiles"].values()))
    assert profile["observations"] == historical["profiles"]["climate.public_zone"]["observations"]
    assert list(exported["profiles"])[0].startswith("climate.source_")
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_reset_passive_learning_keeps_private_archive_and_does_not_write_actuators():
    runtime, hass = build()
    historical = large_archive(runtime, count=500)
    before = deepcopy(runtime.panasonic_archive)

    await runtime.reset_learning()

    assert runtime.panasonic_archive == before
    assert runtime.panasonic.learning_archive == historical
    assert runtime.store.data["panasonic_archive"] == before
    assert not hass.services.calls
