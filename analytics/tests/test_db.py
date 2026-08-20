from earthship_energy.db import parse_openhab_jdbc_config


def test_parses_jdbc_config_without_exposing_secret_in_summary(tmp_path):
    path = tmp_path / "jdbc.config"
    path.write_text(
        'url="jdbc:postgresql://db.local:5433/openhab"\n'
        'user="analytics"\npassword="correct horse"\n'
    )
    settings = parse_openhab_jdbc_config(path)
    assert settings.connect_kwargs["host"] == "db.local"
    assert settings.connect_kwargs["port"] == 5433
    assert settings.connect_kwargs["password"] == "correct horse"
    assert settings.safe_summary() == {
        "host": "db.local",
        "port": 5433,
        "dbname": "openhab",
        "user": "analytics",
    }
    assert "correct horse" not in str(settings.safe_summary())
