import json

import pytest

from earthship_energy.config import ConfigError, load_source_config


def write_config(tmp_path, payload):
    path = tmp_path / "sources.json"
    path.write_text(json.dumps(payload))
    return path


def minimal_source(name="battery.soc", item="BMS_SOC", required=True):
    return {
        "canonical_name": name,
        "item_name": item,
        "device": "test",
        "protocol": "test",
        "raw_unit": "percent",
        "canonical_unit": "percent",
        "scale": 1.0,
        "sign": "unsigned",
        "stale_policy": "status_must_equal_OK",
        "kind": "device_reported",
        "confidence": 1.0,
        "required": required,
    }


def test_loads_strict_source_config(tmp_path):
    path = write_config(
        tmp_path,
        {
            "version": 1,
            "timezone": "America/Denver",
            "sources": [minimal_source()],
            "planned_sources": [],
            "denied_name_patterns": ["^Battery_"],
        },
    )
    config = load_source_config(path)
    assert config.timezone == "America/Denver"
    assert config.sources[0].canonical_name == "battery.soc"
    assert config.sources[0].required is True


def test_duplicate_canonical_names_are_rejected(tmp_path):
    source = minimal_source()
    path = write_config(
        tmp_path,
        {"version": 1, "timezone": "UTC", "sources": [source, source]},
    )
    with pytest.raises(ConfigError, match="duplicate canonical_name"):
        load_source_config(path)


def test_missing_required_fields_and_bad_regex_are_rejected(tmp_path):
    source = minimal_source()
    del source["protocol"]
    path = write_config(
        tmp_path,
        {
            "version": 1,
            "timezone": "UTC",
            "sources": [source],
            "denied_name_patterns": ["["],
        },
    )
    with pytest.raises(ConfigError):
        load_source_config(path)


def test_unknown_top_level_fields_are_rejected(tmp_path):
    path = write_config(
        tmp_path,
        {
            "version": 1,
            "timezone": "UTC",
            "sources": [minimal_source()],
            "secret": "must not be accepted",
        },
    )
    with pytest.raises(ConfigError, match="unknown top-level"):
        load_source_config(path)
