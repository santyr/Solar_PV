"""Bounded, read-only power history transport; no scheduler activation."""
from contextlib import closing
from datetime import timedelta
import re

from .power_evidence import BOUNDS, build_power_intervals, utc

MAX_ROWS = 60000
MAX_WINDOW = timedelta(hours=25)
LOOKBACK = timedelta(seconds=120)


class PowerHistoryLimitError(ValueError):
    """Do not use a truncated prefix as a complete accounting window."""


def read_power_history(settings, table_name, window_start, window_end, *, cutover, row_limit=MAX_ROWS):
    """Read one snapshot and build all three fields from identical source rows.

    Separate read-only connection: never borrows a materialization transaction.
    Row budget includes the 120s lookback; two older boundary rows are retained
    to expose an ambiguous duplicated latest carry. Oversized values become
    invalid barriers in SQL, never large transferred blobs or truncated JSON.
    """
    if not isinstance(table_name, str) or not re.fullmatch(r'item\d{4,}', table_name):
        raise ValueError('invalid power evidence table')
    start, end, floor = utc(window_start), utc(window_end), utc(cutover)
    if not timedelta(0) < end-start <= MAX_WINDOW:
        raise ValueError('power history window must be positive and at most 25 hours')
    if type(row_limit) is not int or not 1 <= row_limit <= MAX_ROWS:
        raise ValueError('invalid power history row limit')
    if floor >= end:
        return {field: [] for field in BOUNDS}
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
    lookback = max(start, floor)-LOOKBACK
    with closing(psycopg2.connect(
        **settings.connect_kwargs, connect_timeout=5,
        options='-c default_transaction_read_only=on -c statement_timeout=5000 -c lock_timeout=1000',
    )) as connection:
        connection.set_session(readonly=True, autocommit=True)
        with connection.cursor() as cursor:
            cursor.execute(query, (lookback, lookback, end, row_limit+1))
            rows = cursor.fetchall()
    if len(rows) > row_limit+2 or sum(bool(in_window) for _, _, in_window in rows) > row_limit:
        raise PowerHistoryLimitError('power evidence row budget exceeded')
    observations = [(at, raw) for at, raw, _ in rows]
    return {field: build_power_intervals(observations, field, start, end, cutover=floor)
            for field in BOUNDS}
