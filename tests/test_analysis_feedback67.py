"""Persisted advice and revision reviews never grant device or model authority."""
from copy import deepcopy
import json
import pytest

from test_analysis_api import api
from test_consumer_history_api import context
from test_runtime import build
from custom_components.solar_pilot.feedback_store import (
    AnalysisFeedbackStore, FeedbackValidationError, MAX_KNOWN_EXPORTS, parse_feedback,
)
from custom_components.solar_pilot.analysis_review import feedback_template


def exported(runtime, hours=168):
    report = runtime.analysis.build(hours=hours)
    template = feedback_template(report)
    return report, template


async def register(runtime, report, template):
    await runtime.analysis_feedback.note_export(report['export_provenance'],
        requested_hours=report['requested_hours'], question_refs=[
            {'question_id': row['question_id'], 'revision': row['revision']}
            for row in template['question_answers']])


def state(runtime, hass):
    return deepcopy((runtime.entry.options, runtime.settings, runtime.sg_boost.snapshot(),
        runtime.learning_hub.policy, runtime.learning_hub.answers,
        runtime.unified_planner.base_load.adaptive_enabled, hass.services.calls))


@pytest.mark.asyncio
async def test_matched_seven_day_answer_hides_only_same_finding_and_keeps_all_authority():
    runtime, hass = build()
    report, template = exported(runtime)
    answer = next(row for row in template['question_answers'] if row['question_id'] == 'adaptation')
    answer.update(answer='Het profiel blijft adviserend; meer meetdagen beoordelen.', outcome='reviewed')
    template['question_answers'] = [answer]
    await register(runtime, report, template)
    before = state(runtime, hass)
    await runtime.analysis_feedback.import_content(json.dumps(template))
    data = runtime.learning_hub.refresh(force=True)
    assert 'adaptation' not in {row['id'] for row in data['questions']}
    assert any(row['id'] == 'adaptation' for row in data['reviewed_findings'])
    assert runtime.analysis_feedback.status()['association']['state'] == 'matched'
    assert runtime.analysis_feedback.status()['question_review'][0]['status'] == 'reviewed'
    assert state(runtime, hass) == before
    # Changed actual meter bindings make a new revision pending automatically.
    runtime.settings['pv_entity'] = 'sensor.new_pv'
    current = runtime.learning_hub.refresh(force=True)
    new = next(row for row in current['questions'] if row['id'] == 'adaptation')
    assert new['revision'] != answer['revision']
    assert runtime.analysis_feedback.question_review(answer['question_id'], answer['revision']) is None
    assert runtime.analysis_feedback.status()['question_review'][0]['status'] == 'ignored_stale'


@pytest.mark.asyncio
async def test_needs_more_data_keeps_finding_and_note_and_remove_reopens_review():
    runtime, hass = build()
    report, template = exported(runtime)
    await register(runtime, report, template)
    await runtime.analysis_feedback.import_content(json.dumps(template))
    data = runtime.learning_hub.refresh(force=True)
    finding = next(row for row in data['questions'] if row['id'] == 'adaptation')
    assert finding['analysis_outcome'] == 'needs_more_data' and finding['answer_note']
    assert 'choices' not in runtime.learning_hub.summary()['findings'][0]
    assert runtime.learning_hub.summary()['analysis_action'] == 'export_7d'
    template['question_answers'][0]['outcome'] = 'reviewed'
    await runtime.analysis_feedback.import_content(json.dumps(template))
    runtime.learning_hub.refresh(force=True)
    await runtime.analysis_feedback.remove()
    assert runtime.analysis_feedback.status()['report'] is None
    assert 'adaptation' in {row['id'] for row in runtime.learning_hub.refresh(force=True)['questions']}
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_cross_entry_unmatched_source_never_reviews_or_changes_model():
    first, _ = build()
    second, hass = build()
    second.entry.entry_id = 'another_entry'
    second.analysis_feedback = AnalysisFeedbackStore(second)
    report, template = exported(first)
    for row in template['question_answers']:
        row['outcome'] = 'reviewed'
    await register(first, report, template)
    before = state(second, hass)
    await second.analysis_feedback.import_content(json.dumps(template))
    current = second.learning_hub.refresh(force=True)
    assert current['questions']
    assert second.analysis_feedback.status()['association']['state'] == 'unverified'
    assert all(row['status'] == 'ignored_unverified' for row in second.analysis_feedback.status()['question_review'])
    assert state(second, hass) == before


@pytest.mark.asyncio
@pytest.mark.parametrize('hours,change', [(24, False), (168, True)])
async def test_known_export_wrong_period_or_unissued_revision_rejects_entire_report(hours, change):
    runtime, hass = build()
    report, template = exported(runtime, hours)
    await register(runtime, report, template)
    if change:
        template['question_answers'][0]['revision'] = 'f' * 16
    before = state(runtime, hass)
    with pytest.raises(FeedbackValidationError):
        await runtime.analysis_feedback.import_content(json.dumps(template))
    assert runtime.analysis_feedback.report is None
    assert state(runtime, hass) == before


@pytest.mark.asyncio
async def test_feedback_save_failure_retains_old_report_and_learning_state(monkeypatch):
    runtime, hass = build()
    report, template = exported(runtime)
    await register(runtime, report, template)
    await runtime.analysis_feedback.import_content(json.dumps(template))
    old = deepcopy(runtime.analysis_feedback.report)
    previous = state(runtime, hass)
    async def fail(_payload):
        raise OSError('disk full')
    monkeypatch.setattr(runtime.analysis_feedback.store, 'async_save', fail)
    template['summary'] = 'Nieuw advies mag niet gedeeltelijk worden opgeslagen.'
    template['question_answers'][0]['outcome'] = 'reviewed'
    with pytest.raises(OSError):
        await runtime.analysis_feedback.import_content(json.dumps(template))
    assert runtime.analysis_feedback.report == old and state(runtime, hass) == previous


@pytest.mark.asyncio
async def test_persistent_last_report_and_known_export_survive_restart():
    runtime, hass = build()
    report, template = exported(runtime)
    await register(runtime, report, template)
    await runtime.analysis_feedback.import_content(json.dumps(template))
    saved = deepcopy(runtime.analysis_feedback.store.data)
    replacement = AnalysisFeedbackStore(runtime)
    replacement.store.data = saved
    await replacement.start()
    assert replacement.status()['report'] == template
    assert replacement.status()['association']['state'] == 'matched'
    assert not hass.services.calls


@pytest.mark.asyncio
async def test_bounded_ledger_preserves_current_report_source():
    runtime, _ = build()
    report, template = exported(runtime)
    await register(runtime, report, template)
    await runtime.analysis_feedback.import_content(json.dumps(template))
    for index in range(MAX_KNOWN_EXPORTS + 3):
        provenance = {**report['export_provenance'], 'export_id': 'export_' + f'{index:032x}'}
        await runtime.analysis_feedback.note_export(provenance, requested_hours=168)
    assert len(runtime.analysis_feedback.known_exports) == MAX_KNOWN_EXPORTS
    assert runtime.analysis_feedback.status()['association']['state'] == 'matched'


@pytest.mark.asyncio
@pytest.mark.parametrize('action', ['status', 'import', 'remove'])
async def test_feedback_api_requires_admin_for_all_actions(api, action):
    runtime, hass, connection, results, errors = context(admin=False)
    before = state(runtime, hass)
    await api.websocket_analysis_feedback(hass, connection, {'id': 1, 'config_entry_id': 'test',
        'action': action, **({'content': '{}'} if action == 'import' else {})})
    assert errors == ['unauthorized'] and not results and state(runtime, hass) == before


@pytest.mark.asyncio
async def test_feedback_ws_lifecycle_and_forbidden_extra_actions(api):
    runtime, hass, connection, results, errors = context()
    report, template = exported(runtime)
    await register(runtime, report, template)
    before = state(runtime, hass)
    await api.websocket_analysis_feedback(hass, connection, {'id': 1, 'config_entry_id': 'test',
        'action': 'import', 'content': json.dumps(template)})
    assert not errors and results[-1]['report'] == template
    await api.websocket_analysis_feedback(hass, connection, {'id': 2, 'config_entry_id': 'test',
        'action': 'status', 'service': 'switch.turn_on'})
    assert errors == ['invalid_action'] and state(runtime, hass) == before
    await api.websocket_analysis_feedback(hass, connection, {'id': 3, 'config_entry_id': 'test', 'action': 'remove'})
    assert results[-1]['report'] is None and state(runtime, hass) == before


@pytest.mark.asyncio
@pytest.mark.parametrize('broken', ['publish', 'refresh'])
async def test_diagnostic_failure_after_persist_keeps_one_successful_response(api, monkeypatch, broken):
    runtime, hass, connection, results, errors = context()
    report, template = exported(runtime)
    await register(runtime, report, template)
    before = state(runtime, hass)
    def fail(*_args, **_kwargs):
        raise RuntimeError('presentation unavailable')
    if broken == 'publish':
        monkeypatch.setattr(runtime, 'publish', fail)
    else:
        monkeypatch.setattr(runtime.learning_hub, 'refresh', fail)
    await api.websocket_analysis_feedback(hass, connection, {'id': 1, 'config_entry_id': 'test',
        'action': 'import', 'content': json.dumps(template)})
    assert not errors and len(results) == 1 and results[0]['report'] == template
    assert runtime.analysis_feedback.store.data['report'] == template
    assert runtime.analysis_feedback.report == template
    assert state(runtime, hass) == before


def test_uploaded_execution_or_implemented_status_are_not_feedback_fields():
    runtime, _ = build()
    _, template = exported(runtime)
    template['recommendations'] = [{'category': 'logic_update', 'text': 'Voorgestelde wijziging.',
        'evidence': [], 'confidence': 'low', 'limitations': [], 'proposal_id': 'warmtepomp-activity-v2',
        'status': 'implemented'}]
    with pytest.raises(FeedbackValidationError):
        parse_feedback(json.dumps(template))
