from copy import deepcopy
from datetime import date, datetime, timezone

import pytest

from earthship_energy.ac_store import encode_ac_snapshot
from earthship_energy.ac_ui import build_ac_ui_payload
from earthship_energy.ui_payload import encode_energy_ui_payload, validate_energy_ui_payload
from test_ac_store import observation
from test_qualified_ui import build


def v4():
    payload = deepcopy(build())
    payload['schema'] = 'earthship-energy-ui/v4'
    payload['acLoad'] = {
        'policy': 'qualified_inverter_ac_output_v1',
        'cutover': '2026-08-21T00:00:00Z',
        'topologyFrom': '2026-08-21T00:00:00Z',
        'topologyUntil': None,
        'status': 'observed',
        'latest': {'date': '2026-08-23', 'windowStart': '2026-08-23T06:00:00Z',
                   'windowEnd': '2026-08-24T06:00:00Z', 'observedKwh': 12.5,
                   'coverage': .95, 'revision': {'id': 7, 'sha256': 'b'*64,
                   'computedAt': '2026-08-24T12:00:00Z'}},
    }
    return payload


def test_matching_reader_contract_keeps_v3_balance_unqualified():
    result = validate_energy_ui_payload(v4(), now=datetime(2026, 8, 24, 18,
                                        tzinfo=timezone.utc))
    assert result['acLoad']['latest']['observedKwh'] == 12.5
    assert result['energy']['latest']['loadKwh'] is None
    assert result['accounting']['loadStatus'] == 'ac_load_evidence_unqualified'
    assert len(encode_energy_ui_payload(result)) < 16384


def test_unavailable_and_partial_ac_are_explicit():
    payload = v4()
    payload['acLoad'].update(status='unavailable', latest=None)
    validate_energy_ui_payload(payload)
    payload = v4()
    payload['acLoad']['latest']['coverage'] = .75
    payload['acLoad']['status'] = 'partial'
    validate_energy_ui_payload(payload)


@pytest.mark.parametrize('mutate', [
    lambda p: p['acLoad'].update(extra=True),
    lambda p: p['acLoad'].update(policy='legacy'),
    lambda p: p['acLoad'].update(status='partial'),
    lambda p: p['acLoad']['latest'].update(coverage=0),
    lambda p: p['acLoad']['latest'].update(coverage=True),
    lambda p: p['acLoad']['latest'].update(observedKwh=-1),
    lambda p: p['acLoad']['latest'].update(windowStart='2026-08-23T07:00:00Z'),
    lambda p: p['acLoad']['latest'].update(windowEnd='2026-08-24T05:00:00Z'),
    lambda p: p['acLoad']['latest'].update(date='2026-08-22'),
    lambda p: p['acLoad']['latest']['revision'].update(sha256='x'),
    lambda p: p['acLoad']['latest']['revision'].update(computedAt='2026-08-23T12:00:00Z'),
    lambda p: p['acLoad'].update(topologyUntil='2026-08-24T05:59:59Z'),
    lambda p: p['energy']['latest'].update(loadKwh=12.5),
])
def test_bad_ac_contract_fails_closed(mutate):
    payload = v4()
    mutate(payload)
    with pytest.raises(ValueError):
        validate_energy_ui_payload(payload)


def selected_row(snapshot, policy):
    day, _, _, _, digest = encode_ac_snapshot(snapshot, policy)
    return {'snapshot_id': 7, 'local_date': day,
            'policy': 'qualified_inverter_ac_output_v1',
            'cutover': policy.cutover, 'topology_from': policy.topology_from,
            'computed_at': datetime(2026, 8, 24, 12, tzinfo=timezone.utc),
            'payload_sha256': digest, 'payload': snapshot}


def test_projection_uses_selected_ac_revision_separate_from_power_day():
    snapshot, policy = observation(day=date(2026, 8, 23))
    projected = build_ac_ui_payload(build(), policy=policy,
                                    ac_rows=[selected_row(snapshot, policy)])
    assert projected['schema'] == 'earthship-energy-ui/v4'
    assert projected['acLoad']['latest']['observedKwh'] == 12.5
    assert projected['energy']['latest']['loadKwh'] is None
    assert projected['accounting']['loadStatus'] == 'ac_load_evidence_unqualified'
    assert len(encode_energy_ui_payload(projected)) < 16384


def test_projection_does_not_fallback_after_zero_coverage_revision():
    snapshot, policy = observation(day=date(2026, 8, 23))
    snapshot.update(observed_ac_load_kwh=None, ac_coverage=0,
                    common_pv_dc_kwh=None, common_ac_load_kwh=None,
                    common_coverage=0, balance_reason='no_common_qualified_intervals')
    projected = build_ac_ui_payload(build(), policy=policy,
                                    ac_rows=[selected_row(snapshot, policy)])
    assert projected['acLoad']['status'] == 'unavailable'
    assert projected['acLoad']['latest'] is None


def test_projection_rejects_fabricated_digest():
    snapshot, policy = observation(day=date(2026, 8, 23))
    row = selected_row(snapshot, policy)
    row['payload_sha256'] = '0'*64
    with pytest.raises(ValueError, match='identity'):
        build_ac_ui_payload(build(), policy=policy, ac_rows=[row])
