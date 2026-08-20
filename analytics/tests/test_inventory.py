import json

import pytest

from earthship_energy.config import SourceConfig
from earthship_energy.inventory import (
    SourceResolutionError,
    item_table_name,
    resolve_sources,
)

from test_config import minimal_source


def config_for(*sources):
    return SourceConfig.from_payload(
        {"version": 1, "timezone": "UTC", "sources": list(sources)}
    )


def test_item_table_name_is_zero_padded_and_rejects_invalid_ids():
    assert item_table_name(2) == "item0002"
    assert item_table_name(550) == "item0550"
    assert item_table_name(12345) == "item12345"
    with pytest.raises(ValueError):
        item_table_name(0)


def test_resolves_item_names_to_existing_tables():
    source = minimal_source()
    source["freshness_item"] = "BMS_Comms_Status"
    config = config_for(source)
    result = resolve_sources(
        config,
        [(550, "BMS_SOC"), (551, "BMS_Comms_Status")],
        {"item0550", "item0551"},
    )
    assert result[0].table_name == "item0550"
    assert result[0].freshness_table_name == "item0551"
    assert result[0].status == "ok"


def test_missing_required_freshness_companion_fails_closed():
    source = minimal_source()
    source["freshness_item"] = "BMS_Comms_Status"
    config = config_for(source)
    with pytest.raises(SourceResolutionError, match="freshness Item missing"):
        resolve_sources(config, [(550, "BMS_SOC")], {"item0550"})


def test_missing_required_source_fails_closed():
    config = config_for(minimal_source())
    with pytest.raises(SourceResolutionError, match="required source"):
        resolve_sources(config, [], set())


def test_missing_optional_source_is_reported_not_fatal():
    config = config_for(minimal_source(required=False))
    result = resolve_sources(config, [], set())
    assert result[0].status == "missing_optional"
    assert result[0].table_name is None


def test_missing_raw_table_fails_for_required_source():
    config = config_for(minimal_source())
    with pytest.raises(SourceResolutionError, match="raw table"):
        resolve_sources(config, [(550, "BMS_SOC")], set())


def test_resolution_summary_contains_no_connection_secrets():
    config = config_for(minimal_source())
    result = resolve_sources(config, [(550, "BMS_SOC")], {"item0550"})
    rendered = json.dumps([row.as_dict() for row in result])
    assert "password" not in rendered.lower()
    assert "dsn" not in rendered.lower()
