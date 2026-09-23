from datetime import date, datetime, timezone
import json

import pytest

from earthship_energy import ac_policy
from earthship_energy.inventory import SourceResolutionError


def policy_file(tmp_path, **changes):
    payload = {
        'version': 1, 'policy': ac_policy.POLICY, 'item_name': ac_policy.ITEM,
        'cutover': '2026-09-23T20:55:00Z',
        'topology': {'basis': ac_policy.BASIS,
                     'effective_from': '2026-09-23T20:55:00Z',
                     'effective_until': '2026-10-23T20:55:00Z'},
    }
    payload.update(changes)
    path = tmp_path / 'ac-policy.json'
    path.write_text(json.dumps(payload))
    return path


def test_resolves_exact_new_item_not_existing_three_field_stream(tmp_path):
    policy = ac_policy.load_ac_policy(policy_file(tmp_path))
    assert policy.resolve_table([(653, ac_policy.ITEM), (648, 'Power_Evidence_JSON')],
                                {'item0653', 'item0648'}) == 'item0653'
    for items, tables in (([], set()), ([(653, ac_policy.ITEM)], set()),
                          ([(653, ac_policy.ITEM), (654, ac_policy.ITEM)],
                           {'item0653', 'item0654'})):
        with pytest.raises(SourceResolutionError):
            policy.resolve_table(items, tables)


def test_only_complete_finished_local_days_within_both_periods(tmp_path):
    policy = ac_policy.load_ac_policy(policy_file(tmp_path))
    as_of = datetime(2026, 9, 25, 7, tzinfo=timezone.utc)
    start, end = policy.day_window(date(2026, 9, 24), as_of=as_of)
    assert (start.isoformat(), end.isoformat()) == (
        '2026-09-24T06:00:00+00:00', '2026-09-25T06:00:00+00:00')
    for day, now in ((date(2026, 9, 23), as_of),
                     (date(2026, 9, 25), as_of),
                     (date(2026, 10, 23), datetime(2026, 10, 25, tzinfo=timezone.utc))):
        with pytest.raises(ValueError):
            policy.day_window(day, as_of=now)
    with pytest.raises(ValueError):
        policy.day_window(datetime(2026, 9, 24, tzinfo=timezone.utc), as_of=as_of)
    with pytest.raises(ValueError):
        policy.day_window(date(2026, 9, 24), as_of=as_of.replace(tzinfo=None))


def test_open_period_still_passes_finite_day_end_to_reader(tmp_path, monkeypatch):
    topology = {'basis': ac_policy.BASIS,
                'effective_from': '2026-09-23T20:55:00Z', 'effective_until': None}
    policy = ac_policy.load_ac_policy(policy_file(tmp_path, topology=topology))
    captured = {}
    def fake_reader(*args, **kwargs):
        captured.update(kwargs)
        return ['qualified interval']
    monkeypatch.setattr(ac_policy, 'read_ac_history', fake_reader)
    result = policy.read_day(object(), 'item0653', date(2026, 9, 24),
                             as_of=datetime(2026, 9, 25, 7, tzinfo=timezone.utc))
    assert result == ['qualified interval']
    assert captured['topology_end'] == datetime(2026, 9, 25, 6, tzinfo=timezone.utc)
    assert captured['cutover'] == captured['topology_start']


def test_dst_day_keeps_true_25_hour_bounds(tmp_path):
    topology = {'basis': ac_policy.BASIS,
                'effective_from': '2026-10-31T06:00:00Z',
                'effective_until': '2026-11-03T07:00:00Z'}
    policy = ac_policy.load_ac_policy(policy_file(
        tmp_path, cutover='2026-10-31T06:00:00Z', topology=topology))
    start, end = policy.day_window(date(2026, 11, 1),
                                   as_of=datetime(2026, 11, 3, tzinfo=timezone.utc))
    assert (end-start).total_seconds() == 25*3600


@pytest.mark.parametrize('changes', [
    {'version': True}, {'version': 2}, {'policy': 'legacy'},
    {'item_name': 'Power_Evidence_JSON'}, {'extra': 1},
    {'cutover': '2026-09-23T20:55:00'},
    {'topology': {'basis': 'household_load', 'effective_from': '2026-09-23T20:55:00Z',
                  'effective_until': None}},
    {'topology': {'basis': ac_policy.BASIS, 'effective_from': '2026-09-23T20:54:00Z',
                  'effective_until': None}},
    {'topology': {'basis': ac_policy.BASIS, 'effective_from': '2026-09-23T20:55:00Z',
                  'effective_until': '2026-09-23T20:55:00Z'}},
])
def test_invalid_policy_is_refused(tmp_path, changes):
    with pytest.raises(ValueError, match='valid AC evidence policy'):
        ac_policy.load_ac_policy(policy_file(tmp_path, **changes))


@pytest.mark.parametrize('raw', ['{"version":1,"version":1}', ' '*4097])
def test_duplicate_and_oversized_policy_refused(tmp_path, raw):
    path = tmp_path/'bad.json'
    path.write_text(raw)
    with pytest.raises(ValueError, match='valid AC evidence policy'):
        ac_policy.load_ac_policy(path)
