"""Read bounded numeric series from OpenHAB's per-Item JDBC tables."""

from __future__ import annotations

from datetime import date, datetime
from math import isfinite
import re
from zoneinfo import ZoneInfo

from .series import Point


ITEM_TABLE = re.compile(r"^item\d{4,}$")


def normalize_window_series(
    carry_in: tuple[datetime, object] | None,
    rows: list[tuple[datetime, object]],
    window_start: datetime,
    window_end: datetime,
) -> list[Point]:
    if window_end <= window_start:
        raise ValueError("window_end must be after window_start")
    values: dict[datetime, float] = {}
    if carry_in is not None and carry_in[0] < window_start:
        values[window_start] = float(carry_in[1])
    for at, raw_value in rows:
        if window_start <= at <= window_end:
            value = float(raw_value)
            if not isfinite(value):
                raise ValueError("series values must be finite")
            values[at] = value
    ordered = sorted(values.items())
    if ordered and ordered[-1][0] < window_end:
        ordered.append((window_end, ordered[-1][1]))
    return ordered


def fetch_numeric_series(
    connection,
    table_name: str,
    window_start: datetime,
    window_end: datetime,
) -> list[Point]:
    if not ITEM_TABLE.fullmatch(table_name):
        raise ValueError("invalid OpenHAB Item table name")
    with connection.cursor() as cursor:
        cursor.execute(
            f"""SELECT time, value FROM public.{table_name}
                WHERE time < %s ORDER BY time DESC LIMIT 1""",
            (window_start,),
        )
        carry_in = cursor.fetchone()
        cursor.execute(
            f"""SELECT time, value FROM public.{table_name}
                WHERE time >= %s AND time <= %s ORDER BY time""",
            (window_start, window_end),
        )
        rows = cursor.fetchall()
    return normalize_window_series(carry_in, rows, window_start, window_end)


def normalize_window_text_series(
    carry_in: tuple[datetime, object] | None,
    rows: list[tuple[datetime, object]],
    window_start: datetime,
    window_end: datetime,
) -> list[tuple[datetime, str]]:
    if window_end <= window_start:
        raise ValueError("window_end must be after window_start")
    values: dict[datetime, str] = {}
    if carry_in is not None and carry_in[0] < window_start:
        values[window_start] = str(carry_in[1])
    for at, raw_value in rows:
        if window_start <= at <= window_end:
            values[at] = str(raw_value)
    ordered = sorted(values.items())
    if ordered and ordered[-1][0] < window_end:
        ordered.append((window_end, ordered[-1][1]))
    return ordered


def fetch_text_series(
    connection,
    table_name: str,
    window_start: datetime,
    window_end: datetime,
) -> list[tuple[datetime, str]]:
    if not ITEM_TABLE.fullmatch(table_name):
        raise ValueError("invalid OpenHAB Item table name")
    with connection.cursor() as cursor:
        cursor.execute(
            f"""SELECT time, value FROM public.{table_name}
                WHERE time < %s ORDER BY time DESC LIMIT 1""",
            (window_start,),
        )
        carry_in = cursor.fetchone()
        cursor.execute(
            f"""SELECT time, value FROM public.{table_name}
                WHERE time >= %s AND time <= %s ORDER BY time""",
            (window_start, window_end),
        )
        rows = cursor.fetchall()
    return normalize_window_text_series(carry_in, rows, window_start, window_end)


def state_duration_seconds(
    points: list[tuple[datetime, str]], target_state: str
) -> float:
    duration = 0.0
    for left, right in zip(points, points[1:]):
        if left[1].strip().upper() == target_state.strip().upper():
            duration += max(0.0, (right[0] - left[0]).total_seconds())
    return duration


def datetime_state_for_local_date(
    points: list[tuple[datetime, str]],
    local_date: date,
    timezone_name: str,
) -> datetime | None:
    zone = ZoneInfo(timezone_name)
    matches = []
    for _, raw in points:
        try:
            value = datetime.fromisoformat(raw)
        except ValueError:
            continue
        if value.tzinfo is None or value.utcoffset() is None:
            continue
        if value.astimezone(zone).date() == local_date:
            matches.append(value)
    return matches[-1] if matches else None
