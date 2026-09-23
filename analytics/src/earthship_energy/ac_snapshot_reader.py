"""Bounded, read-only latest AC revisions; no legacy or older-revision fallback."""
from contextlib import closing
from datetime import date, datetime

from .ac_policy import AcEvidencePolicy, POLICY
from .ac_store import encode_ac_snapshot
from .power_evidence import utc

MAX_DAYS = 366


def read_ac_snapshots(settings, *, policy, start_date, end_date, as_of):
    if type(policy) is not AcEvidencePolicy:
        raise ValueError('qualified AC policy required')
    if type(start_date) is not date or type(end_date) is not date:
        raise ValueError('site-local date bounds required')
    days = (end_date-start_date).days
    if not 1 <= days <= MAX_DAYS:
        raise ValueError('AC revision window must be 1 to 366 days')
    as_of = utc(as_of)
    if as_of < utc(policy.cutover):
        return []
    import psycopg2
    query = '''SELECT snapshot_id, local_date, payload_sha256,
                      CASE WHEN octet_length(payload::text)<=65536 THEN payload ELSE NULL END,
                      computed_at
               FROM (SELECT DISTINCT ON (local_date)
                            snapshot_id, local_date, payload_sha256, payload, computed_at
                     FROM energy_analytics.daily_ac_snapshots
                     WHERE policy=%s AND cutover_at=%s AND topology_from=%s
                       AND local_date >= %s AND local_date < %s AND computed_at <= %s
                     ORDER BY local_date, snapshot_id DESC) AS latest
               ORDER BY local_date LIMIT %s'''
    with closing(psycopg2.connect(
        **settings.connect_kwargs, connect_timeout=5,
        options='-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=1000',
    )) as connection:
        connection.set_session(readonly=True, autocommit=True)
        with connection.cursor() as cursor:
            cursor.execute(query, (POLICY, policy.cutover, policy.topology_from,
                                   start_date, end_date, as_of, days+1))
            rows = cursor.fetchall()
    if len(rows) > days:
        raise ValueError('AC revision row budget exceeded')
    result, previous = [], None
    for snapshot_id, local_day, stored_digest, payload, computed_at in rows:
        if (type(snapshot_id) is not int or snapshot_id <= 0 or type(local_day) is not date
                or not start_date <= local_day < end_date
                or previous is not None and local_day <= previous
                or type(payload) is not dict or utc(computed_at) > as_of):
            raise ValueError('invalid selected AC revision')
        # A later operator topology end can narrow eligibility without
        # invalidating a completed day stored while the period was open-ended.
        policy.day_window(local_day, as_of=as_of)
        try:
            stored_until = (None if payload['topology_until'] is None else
                            datetime.fromisoformat(payload['topology_until']))
            original_policy = AcEvidencePolicy(policy.cutover, policy.topology_from,
                                               stored_until)
            decoded_day, _, window_end, _, digest = encode_ac_snapshot(payload, original_policy)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError('invalid selected AC payload') from exc
        if (decoded_day != local_day or digest != stored_digest
                or window_end > min(as_of, utc(computed_at))):
            raise ValueError('AC revision identity or completion mismatch')
        result.append({'snapshot_id': snapshot_id, 'local_date': local_day,
                       'policy': POLICY, 'cutover': utc(policy.cutover),
                       'topology_from': utc(policy.topology_from),
                       'computed_at': utc(computed_at), 'payload_sha256': digest,
                       'payload': payload})
        previous = local_day
    return result
