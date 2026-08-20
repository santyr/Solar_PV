from datetime import timezone

import pytest

from earthship_energy.imports import ImportError, prepare_lynk_import


CSV = b"""module_id,sampled_at,soc_pct,voltage_v,current_a,temperature_c,cell_spread_mv,charge_kwh,discharge_kwh,faults
module-1,2026-08-20T12:00:00Z,90,52.1,1.2,24.0,8,10,9,
module-2,2026-08-20T12:00:00Z,89,52.0,1.1,24.5,9,10,9,WARN
"""


def test_prepares_typed_checksum_pinned_lynk_import():
    batch = prepare_lynk_import(CSV, "lynk-export.csv", existing_hashes=set())
    assert batch.status == "ready"
    assert len(batch.sha256) == 64
    assert len(batch.rows) == 2
    assert batch.rows[0].sampled_at.tzinfo is timezone.utc
    assert batch.rows[1].faults == ("WARN",)


def test_byte_identical_import_is_idempotent():
    first = prepare_lynk_import(CSV, "lynk-export.csv", existing_hashes=set())
    second = prepare_lynk_import(CSV, "renamed.csv", existing_hashes={first.sha256})
    assert second.status == "duplicate"
    assert second.rows == ()


def test_duplicate_sample_key_or_missing_columns_is_rejected():
    duplicate = CSV + CSV.splitlines(keepends=True)[1]
    with pytest.raises(ImportError, match="duplicate sample"):
        prepare_lynk_import(duplicate, "bad.csv", set())
    with pytest.raises(ImportError, match="columns"):
        prepare_lynk_import(b"module_id,sampled_at\na,2026-01-01T00:00:00Z\n", "bad.csv", set())
