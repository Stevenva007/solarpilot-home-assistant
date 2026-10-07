"""Historical command evidence survives replacement of the latest audit row."""
from copy import deepcopy

import pytest

from test_dhw_auto_recovery61 import failed, mismatch_reports


@pytest.mark.asyncio
async def test_separate_failure_and_reconciliation_events_keep_the_original_evidence(monkeypatch):
    runtime, hass, wall, mono = await failed(monkeypatch)
    original = deepcopy(runtime.dhw.failed_command)
    await mismatch_reports(runtime, hass, wall, mono)
    rows = [e for e in runtime.analysis.events if e['kind'].startswith('dhw_command_')]
    assert [e['kind'] for e in rows] == ['dhw_command_failure', 'dhw_command_reconciled']
    assert rows[0]['data']['requested_target_c'] == original['requested_target_c'] == 60
    assert rows[0]['data']['reported_target_c'] == original['reported_target_c'] == 50
    assert 'reviewed_at' not in rows[0]['data']
    assert rows[1]['data']['review_kind'] == 'automatic_observed_target'
    runtime.dhw.failed_command = {'schema': 1, 'reason': 'Latere afzonderlijke fout'}
    assert rows[0]['data']['requested_target_c'] == 60
    assert rows[1]['data']['reported_target_c'] == 50


@pytest.mark.asyncio
async def test_research_storage_failure_never_prevents_fault_capture_or_safe_reconciliation(monkeypatch):
    from custom_components.solar_pilot.analysis_export import AnalysisRecorder
    def broken_event(*args, **kwargs):
        raise OSError('Test opslag niet beschikbaar')
    monkeypatch.setattr(AnalysisRecorder, 'event', broken_event)
    # Ordinary note() also writes an advisory event; keep its existing logging
    # outside this explicit diagnostic-storage-failure scenario.
    from custom_components.solar_pilot.runtime import SolarRuntime
    monkeypatch.setattr(SolarRuntime, 'note', lambda *args: None)
    runtime, hass, wall, mono = await failed(monkeypatch)
    assert runtime.dhw.fault and runtime.dhw.automatic_recovery
    await mismatch_reports(runtime, hass, wall, mono)
    assert not runtime.dhw.fault and runtime.dhw.recovery_barrier
    assert runtime.dhw.failed_command['review_kind'] == 'automatic_observed_target'
