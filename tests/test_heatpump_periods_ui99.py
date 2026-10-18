"""Session summaries preserve each original interval and recorded uncertainty."""
from copy import deepcopy
from datetime import datetime, timedelta

from test_heatpump_history_ui70 import history_fixture, render_history
from test_heatpump_history_scrub98 import run_scrub
from test_overview_details60 import Markup


def period_fixture(count=9):
    data = history_fixture()
    start = datetime.fromisoformat('2026-10-12T06:00:00+02:00')
    data['task_sessions'] = [dict(
        segment_start=(start + timedelta(minutes=index * 5, seconds=12)).isoformat(),
        segment_end=(start + timedelta(minutes=index * 5, seconds=37)).isoformat(),
        duration_s=25, task='heatpump_unknown' if index % 2 else 'tapwater_heating',
        tier='unknown' if index % 2 else 'derived',
        label='Taak onbekend' if index % 2 else 'Boiler opwarmen')
        for index in range(count)]
    return data


def text(node):
    return ' '.join(node.text().split())


def all_nodes(root, attribute):
    return [n for n in root.walk() if attribute in n.attributes]


def test_eight_periods_stay_visible_nine_get_summary_and_full_chronological_details():
    simple = Markup(render_history(period_fixture(8))['html']).root
    assert len(all_nodes(simple, 'data-session-task-period')) == 8
    assert not all_nodes(simple, 'data-session-task-summary')
    detailed = Markup(render_history(period_fixture(9))['html']).root
    assert len(all_nodes(detailed, 'data-session-task-summary')) == 1
    details = [n for n in detailed.walk() if n.tag == 'details' and
               n.attributes.get('data-history-key', '').startswith('session-tasks:')]
    assert len(details) == 1 and 'open' not in details[0].attributes
    assert 'Alle 9 taakperioden en meetpunten' in details[0].text()
    rows = all_nodes(details[0], 'data-session-task-period')
    assert len(rows) == 9
    assert rows[0].text().startswith('06:00:12 – 06:00:37')
    assert rows[-1].text().startswith('06:40:12 – 06:40:37')
    summary = text(all_nodes(detailed, 'data-session-task-summary')[0])
    assert 'Boiler opwarmen Afgeleid · 2 min 5 s' in summary
    assert 'Taak onbekend · 1 min 40 s' in summary
    assert '5 waarnemingen' in summary and '4 waarnemingen' in summary


def test_unknown_short_periods_include_seconds_and_point_has_no_fabricated_duration():
    data = period_fixture(2)
    data['task_sessions'][0].update(task='heatpump_unknown', tier='unknown', label='Taak onbekend')
    data['task_sessions'][1].update(segment_end=data['task_sessions'][1]['segment_start'], duration_s=0)
    root = Markup(render_history(data)['html']).root
    rows = all_nodes(root, 'data-session-task-period')
    assert text(rows[0]) == '06:00:12 – 06:00:37 · Taak onbekend · 25 s'
    assert text(rows[1]) == 'Meetpunt 06:05:12 · Taak onbekend · duur niet vastgesteld'
    assert all(row.text().count('Taak onbekend') == 1 for row in rows)
    assert all(not any('pill' in child.attributes.get('class', '') for child in row.walk()) for row in rows)
    assert '0 min' not in rows[1].text() and '0 s' not in rows[1].text()


def test_summary_counts_zero_points_without_inventing_duration_or_merging_tiers():
    data = period_fixture(10)
    for row in data['task_sessions']:
        row.update(task='heatpump_unknown', tier='unknown', label='Taak onbekend',
                   segment_end=row['segment_start'], duration_s=0)
    data['task_sessions'][0].update(task='tapwater_heating', tier='derived', label='Boiler opwarmen',
        segment_end='2026-10-12T06:00:37+02:00')
    data['task_sessions'][1].update(task='tapwater_heating', tier='confirmed', label='Boiler opwarmen',
        segment_end='2026-10-12T06:05:37+02:00')
    root = Markup(render_history(data)['html']).root
    summary = text(all_nodes(root, 'data-session-task-summary')[0])
    assert 'Boiler opwarmen Afgeleid · 25 s' in summary
    assert 'Boiler opwarmen Bevestigd · 25 s' in summary
    assert 'Taak onbekend · duur niet vastgesteld' in summary
    assert '8 waarnemingen · 8 meetpunten zonder vastgestelde duur' in summary


def test_clipping_uses_interval_times_and_leaves_all_source_data_untouched():
    data = period_fixture(9)
    data['sessions'][0].update(segment_start='2026-10-12T06:00:20+02:00',
                               segment_end='2026-10-12T06:40:20+02:00')
    # Deliberately inconsistent display duration must never inflate the summary.
    data['task_sessions'][0]['duration_s'] = 9999
    before = deepcopy(data)
    rendered = render_history(data)['html']
    assert data == before
    root = Markup(rendered).root
    rows = all_nodes(root, 'data-session-task-period')
    assert '06:00:20 – 06:00:37' in rows[0].text() and '17 s' in rows[0].text()
    assert '06:40:12 – 06:40:20' in rows[-1].text() and '8 s' in rows[-1].text()
    assert 'Getoond binnen deze sessie en dag.' in rows[0].text()
    summary = text(all_nodes(root, 'data-session-task-summary')[0])
    assert 'Boiler opwarmen Afgeleid · 1 min 40 s' in summary
    assert '9999' not in summary
    assert next(n for n in root.walk() if 'data-energy' in n.attributes).text() == '1,25 kWh'
    assert len([n for n in root.walk() if 'data-history-task' in n.attributes]) == 10  # 9 task + SG lane


def test_support_is_separate_and_not_added_to_primary_task_summary():
    data = period_fixture(9)
    data['support_sessions'] = [dict(data['sessions'][0], duration_s=3600)]
    root = Markup(render_history(data)['html']).root
    summary = text(all_nodes(root, 'data-session-task-summary')[0])
    assert 'Elektrische ondersteuning' not in summary and '1 u' not in summary
    support = all_nodes(root, 'data-session-support')
    assert len(support) == 1 and 'Elektrische ondersteuning Afgeleid · 1 u' in text(support[0])


def test_summary_key_survives_later_endpoint_and_period_updates():
    data = period_fixture(9)
    data['sessions'][0]['id'] = 7
    initial = Markup(render_history(data)['html']).root
    key = next(n.attributes['data-history-key'] for n in initial.walk() if
               n.attributes.get('data-history-key', '').startswith('session-tasks:'))
    data['sessions'][0].update(segment_end='2026-10-12T07:30:00+02:00', ongoing=True)
    data['task_sessions'].append(dict(data['task_sessions'][-1],
        segment_start='2026-10-12T07:01:00+02:00', segment_end='2026-10-12T07:02:00+02:00'))
    updated = Markup(render_history(data)['html']).root
    assert next(n.attributes['data-history-key'] for n in updated.walk() if
                n.attributes.get('data-history-key', '').startswith('session-tasks:')) == key


def test_point_only_parent_session_is_not_formatted_as_zero_length_cycle():
    data = period_fixture(0)
    data['sessions'][0].update(segment_start='2026-10-12T06:00:12+02:00',
        segment_end='2026-10-12T06:00:12+02:00', duration_s=0)
    root = Markup(render_history(data)['html']).root
    session = next(n for n in root.walk() if n.tag == 'article' and n.attributes.get('class') == 'session')
    assert 'Meetpunt 06:00:12' in session.text() and 'duur niet vastgesteld' in session.text()
    assert '→' not in session.text() and '0 s' not in session.text()


def test_fractional_second_duration_is_not_rounded_to_zero():
    assert run_scrub(history_fixture(), 'return d._periodDuration(.4);') == '0,4 s'
    assert run_scrub(history_fixture(), 'return d._periodDuration(.04);') == '< 0,1 s'
