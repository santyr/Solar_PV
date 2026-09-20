"""Bounded latest-revision reads; no legacy or older-quality fallback."""
from contextlib import closing
from datetime import date, datetime

from .power_evidence import utc
from .power_store import POLICY, encode_snapshot

MAX_DAYS = 366


def read_power_snapshots(settings, *, epoch_id, cutover, start_date, end_date, as_of):
    """Return selected qualified revisions for a half-open local-date range.

    Missing dates remain absent. Callers must disclose missing coverage, never
    fill it with legacy rows. Longer histories require explicit bounded pages.
    Selection precedes payload validation or quality interpretation: a malformed
    latest revision fails the read rather than resurrecting an earlier result.
    """
    if type(start_date) is not date or type(end_date) is not date:
        raise ValueError('local date bounds required')
    days = (end_date-start_date).days
    if not 1 <= days <= MAX_DAYS:
        raise ValueError('power snapshot window must be 1 to 366 days')
    if not isinstance(epoch_id, str) or not epoch_id or len(epoch_id) > 128:
        raise ValueError('invalid bank epoch')
    cutover, as_of = utc(cutover), utc(as_of)
    if as_of < cutover:
        return []
    import psycopg2
    query = '''SELECT snapshot_id, local_date, payload_sha256,
                      CASE WHEN octet_length(payload::text)<=65536 THEN payload ELSE NULL END,
                      computed_at
               FROM (SELECT DISTINCT ON (local_date)
                            snapshot_id, local_date, payload_sha256, payload, computed_at
                     FROM energy_analytics.daily_power_snapshots
                     WHERE epoch_id=%s AND policy=%s AND cutover_at=%s
                       AND local_date >= %s AND local_date < %s AND computed_at <= %s
                     ORDER BY local_date, snapshot_id DESC) AS latest
               ORDER BY local_date LIMIT %s'''
    with closing(psycopg2.connect(
        **settings.connect_kwargs, connect_timeout=5,
        options='-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=1000',
    )) as connection:
        connection.set_session(readonly=True, autocommit=True)
        with connection.cursor() as cursor:
            cursor.execute(query, (epoch_id, POLICY, cutover, start_date, end_date, as_of, days+1))
            rows = cursor.fetchall()
    if len(rows) > days:
        raise ValueError('power snapshot row budget exceeded')
    result = []
    previous = None
    for snapshot_id, local_day, stored_digest, payload, computed_at in rows:
        if (type(snapshot_id) is not int or snapshot_id <= 0 or type(local_day) is not date
                or not start_date <= local_day < end_date
                or (previous is not None and local_day <= previous)
                or not isinstance(payload, dict) or utc(computed_at) > as_of):
            raise ValueError('invalid selected power snapshot')
        decoded_day, decoded_cutover, _, digest = encode_snapshot(payload)
        if (decoded_day != local_day or decoded_cutover != cutover or digest != stored_digest
                or utc(datetime.fromisoformat(payload['window_end'])) > min(as_of,utc(computed_at))):
            raise ValueError('power snapshot identity or completed-window mismatch')
        result.append({'snapshot_id': snapshot_id, 'local_date': local_day,
                       'epoch_id': epoch_id, 'policy': POLICY, 'cutover': cutover,
                       'computed_at': utc(computed_at), 'payload_sha256': digest, 'payload': payload})
        previous = local_day
    return result
