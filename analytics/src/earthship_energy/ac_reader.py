"""Bounded, read-only transport for separate inverter-output evidence."""
from contextlib import closing
from datetime import timedelta
import re

from .ac_evidence import build_ac_intervals
from .power_evidence import utc
from .power_reader import MAX_ROWS, MAX_WINDOW, PowerHistoryLimitError

LOOKBACK = timedelta(seconds=30)


def read_ac_history(settings, table_name, window_start, window_end, *, cutover,
                    topology_start, topology_end, row_limit=MAX_ROWS):
    """Return qualified inverter-output intervals, never inferred load totals."""
    if not isinstance(table_name, str) or not re.fullmatch(r'item\d{4,}', table_name):
        raise ValueError('invalid AC evidence table')
    start, end, floor = map(utc, (window_start, window_end, cutover))
    topo_start, topo_end = map(utc, (topology_start, topology_end))
    if not timedelta(0) < end-start <= MAX_WINDOW:
        raise ValueError('AC history window must be positive and at most 25 hours')
    if topo_end <= topo_start:
        raise ValueError('invalid inverter-only topology period')
    if type(row_limit) is not int or not 1 <= row_limit <= MAX_ROWS:
        raise ValueError('invalid AC history row limit')
    if max(start, floor, topo_start) >= min(end, topo_end):
        return []
    import psycopg2

    query = f"""
        WITH boundary AS (
            SELECT time, value FROM public.{table_name}
            WHERE time < %s ORDER BY time DESC LIMIT 2
        ), observations AS (
            SELECT time, value FROM public.{table_name}
            WHERE time >= %s AND time < %s ORDER BY time LIMIT %s
        )
        SELECT time,
               CASE WHEN octet_length(value::text) <= 4096
                    THEN value::text ELSE NULL END,
               in_window
        FROM (
            SELECT time, value, false AS in_window FROM boundary
            UNION ALL
            SELECT time, value, true AS in_window FROM observations
        ) AS evidence ORDER BY time
    """
    lookback = max(start, floor, topo_start) - LOOKBACK
    with closing(psycopg2.connect(
        **settings.connect_kwargs, connect_timeout=5,
        options='-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=1000',
    )) as connection:
        connection.set_session(readonly=True, autocommit=True)
        with connection.cursor() as cursor:
            cursor.execute(query, (lookback, lookback, end, row_limit+1))
            rows = cursor.fetchall()
    if len(rows) > row_limit+2 or sum(bool(in_window) for _, _, in_window in rows) > row_limit:
        raise PowerHistoryLimitError('AC evidence row budget exceeded')
    return build_ac_intervals([(at, raw) for at, raw, _ in rows], start, end,
                              cutover=floor, topology_start=topo_start, topology_end=topo_end)
