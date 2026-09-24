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


def test_default_soc_source_selects_atomic_evidence_without_renaming_numeric_item():
    source = next(source for source in load_source_config().sources
                  if source.canonical_name == "battery.soc_pct")
    assert source.item_name == "BMS_SOC"
    assert source.freshness_item == "BMS_SOC_Evidence_JSON"
    assert source.stale_policy == "atomic_bms_evidence"


def test_astro_local_date_quality_uses_only_its_own_derived_schedule():
    sources = {source.canonical_name: source for source in load_source_config().sources}
    for name, item in (("solar.sunrise_at", "Sun_Rise_End"),
                       ("solar.sunset_at", "Sun_Set_Start")):
        source = sources[name]
        assert source.item_name == source.freshness_item == item
        assert source.stale_policy == "local_date_must_match"
        assert source.kind == "derived"
        assert source.raw_unit == "datetime"


def test_local_date_policy_rejects_other_sources_as_freshness_basis(tmp_path):
    source = minimal_source(name="solar.sunrise_at", item="Sun_Rise_End", required=False)
    source.update(stale_policy="local_date_must_match", kind="derived",
                  raw_unit="datetime", freshness_item="Other_Item")
    path = write_config(tmp_path, {"version": 1, "timezone": "America/Denver",
                                   "sources": [source]})
    with pytest.raises(ConfigError, match="its own derived datetime Item"):
        load_source_config(path)


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
