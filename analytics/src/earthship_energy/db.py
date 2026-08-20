"""Secret-safe PostgreSQL connection configuration."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


class DatabaseConfigError(ValueError):
    pass


@dataclass(frozen=True)
class JdbcSettings:
    host: str
    port: int
    dbname: str
    user: str
    password: str

    @property
    def connect_kwargs(self) -> dict[str, object]:
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
            "password": self.password,
        }

    def safe_summary(self) -> dict[str, object]:
        return {
            "host": self.host,
            "port": self.port,
            "dbname": self.dbname,
            "user": self.user,
        }


def parse_openhab_jdbc_config(path: str | Path) -> JdbcSettings:
    values = {}
    try:
        lines = Path(path).read_text().splitlines()
    except OSError as exc:
        raise DatabaseConfigError(f"cannot read JDBC config: {exc}") from exc
    for line in lines:
        if "=" not in line or line.lstrip().startswith("#"):
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"')
    missing = {"url", "user", "password"} - set(values)
    if missing:
        raise DatabaseConfigError(f"JDBC config missing keys: {sorted(missing)}")
    url = values["url"]
    if not url.startswith("jdbc:postgresql://"):
        raise DatabaseConfigError("only jdbc:postgresql URLs are supported")
    parsed = urlparse(url.removeprefix("jdbc:"))
    if not parsed.hostname or not parsed.path.strip("/"):
        raise DatabaseConfigError("invalid PostgreSQL JDBC URL")
    return JdbcSettings(
        host=parsed.hostname,
        port=parsed.port or 5432,
        dbname=parsed.path.strip("/"),
        user=values["user"],
        password=values["password"],
    )


def connect_read_only(settings: JdbcSettings):
    import psycopg2

    connection = psycopg2.connect(**settings.connect_kwargs)
    connection.set_session(readonly=True, autocommit=True)
    return connection
