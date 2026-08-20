"""Resolve stable OpenHAB Item names to physical persistence tables."""

from __future__ import annotations

from dataclasses import dataclass

from .config import SourceConfig


class SourceResolutionError(RuntimeError):
    pass


def item_table_name(item_id: int) -> str:
    if not isinstance(item_id, int) or isinstance(item_id, bool) or item_id <= 0:
        raise ValueError("item_id must be a positive integer")
    return f"item{item_id:04d}"


@dataclass(frozen=True)
class ResolvedSource:
    canonical_name: str
    item_name: str
    item_id: int | None
    table_name: str | None
    required: bool
    status: str
    freshness_item: str | None = None
    freshness_table_name: str | None = None

    def as_dict(self) -> dict[str, object]:
        return {
            "canonical_name": self.canonical_name,
            "item_name": self.item_name,
            "item_id": self.item_id,
            "table_name": self.table_name,
            "required": self.required,
            "status": self.status,
            "freshness_item": self.freshness_item,
            "freshness_table_name": self.freshness_table_name,
        }


def resolve_sources(
    config: SourceConfig,
    item_rows: list[tuple[int, str]],
    existing_tables: set[str],
) -> list[ResolvedSource]:
    by_name: dict[str, list[int]] = {}
    for item_id, item_name in item_rows:
        by_name.setdefault(item_name, []).append(item_id)
    results = []
    for source in config.sources:
        ids = by_name.get(source.item_name, [])
        if len(ids) > 1:
            raise SourceResolutionError(f"ambiguous Item: {source.item_name}")
        if not ids:
            if source.required:
                raise SourceResolutionError(
                    f"required source Item missing: {source.item_name}"
                )
            results.append(
                ResolvedSource(
                    source.canonical_name,
                    source.item_name,
                    None,
                    None,
                    False,
                    "missing_optional",
                )
            )
            continue
        item_id = ids[0]
        table_name = item_table_name(item_id)
        if table_name not in existing_tables:
            if source.required:
                raise SourceResolutionError(
                    f"required source raw table missing: {table_name}"
                )
            status = "raw_table_missing_optional"
            table_name = None
        else:
            status = "ok"
        freshness_table_name = None
        if source.freshness_item is not None:
            freshness_ids = by_name.get(source.freshness_item, [])
            if len(freshness_ids) > 1:
                raise SourceResolutionError(
                    f"ambiguous freshness Item: {source.freshness_item}"
                )
            if not freshness_ids:
                if source.required:
                    raise SourceResolutionError(
                        f"required freshness Item missing: {source.freshness_item}"
                    )
            else:
                candidate = item_table_name(freshness_ids[0])
                if candidate not in existing_tables:
                    if source.required:
                        raise SourceResolutionError(
                            f"required freshness raw table missing: {candidate}"
                        )
                else:
                    freshness_table_name = candidate
        results.append(
            ResolvedSource(
                source.canonical_name,
                source.item_name,
                item_id,
                table_name,
                source.required,
                status,
                source.freshness_item,
                freshness_table_name,
            )
        )
    return results


def fetch_inventory(connection) -> tuple[list[tuple[int, str]], set[str]]:
    with connection.cursor() as cursor:
        cursor.execute("SELECT itemid, itemname FROM public.items ORDER BY itemid")
        item_rows = cursor.fetchall()
        cursor.execute(
            """SELECT table_name FROM information_schema.tables
               WHERE table_schema = 'public' AND table_name LIKE 'item%'"""
        )
        tables = {row[0] for row in cursor.fetchall()}
    return item_rows, tables
