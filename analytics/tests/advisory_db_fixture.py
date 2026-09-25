"""Disposable-only PostgreSQL fixture: no external DSN input or fallback."""
from contextlib import closing
from dataclasses import dataclass
import os
import secrets
import subprocess
import time
from types import SimpleNamespace
from uuid import uuid4

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import make_dsn
import pytest

from earthship_energy.migrations import (
    apply_migrations, discover_migrations, get_applied_migrations, plan_migrations,
)


@dataclass(frozen=True)
class FixtureEndpoint:
    host: str
    port: int
    dbname: str
    user: str
    password: str

    @property
    def dsn(self):
        return make_dsn(
            host=self.host, port=self.port, dbname=self.dbname,
            user=self.user, password=self.password,
        )

    def connect(self, *, connect_timeout=3):
        if os.environ.get("PGSERVICE") or os.environ.get("PGSERVICEFILE"):
            raise RuntimeError("unsafe disposable database environment")
        return psycopg2.connect(
            host=self.host, hostaddr=self.host, port=self.port,
            dbname=self.dbname, user=self.user, password=self.password,
            connect_timeout=connect_timeout, sslmode="disable",
        )


def docker(args, env=None):
    result = subprocess.run(
        ["docker", *args], env=env, capture_output=True, text=True, timeout=30,
    )
    if result.returncode:
        raise RuntimeError("disposable advisory database command failed")
    return result.stdout.strip()


@pytest.fixture(scope="module")
def advisory_db():
    name = "advisory-test-" + uuid4().hex
    owner_password = secrets.token_hex(24)
    writer_password = secrets.token_hex(24)
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("PG")}
    env.update(POSTGRES_PASSWORD=owner_password, POSTGRES_DB="advisory_test")
    created = False
    try:
        docker(["image", "inspect", "postgres:16"])
        docker(["create", "--pull=never", "--name", name,
                "--publish", "127.0.0.1::5432", "--env", "POSTGRES_PASSWORD",
                "--env", "POSTGRES_DB", "postgres:16"], env=env)
        created = True
        docker(["start", name])
        binding = docker(["port", name, "5432/tcp"])
        assert binding.startswith("127.0.0.1:") and "\n" not in binding
        port = int(binding.rsplit(":", 1)[1])
        owner = FixtureEndpoint(
            host="127.0.0.1", port=port, dbname="advisory_test",
            user="postgres", password=owner_password,
        )
        deadline = time.monotonic() + 30
        while True:
            try:
                connection = owner.connect(connect_timeout=1)
                break
            except psycopg2.Error:
                if time.monotonic() >= deadline:
                    raise RuntimeError("disposable advisory database not ready") from None
                time.sleep(0.1)
        with closing(connection), connection:
            pending = plan_migrations(discover_migrations(),
                                      get_applied_migrations(connection))
            assert [m.version for m in pending] == [1, 2, 3, 4, 5, 6]
            assert apply_migrations(connection, pending) == [1, 2, 3, 4, 5, 6]
            with connection.cursor() as cursor:
                cursor.execute("""INSERT INTO energy_analytics.system_epochs
                    (epoch_id, current_analytics) VALUES ('test_bank', true)""")
                cursor.execute(sql.SQL("CREATE ROLE advisory_writer LOGIN PASSWORD {}")
                               .format(sql.Literal(writer_password)))
                cursor.execute("GRANT USAGE ON SCHEMA energy_analytics TO advisory_writer")
                cursor.execute("""GRANT INSERT, SELECT ON
                    energy_analytics.advisory_decisions,
                    energy_analytics.advisory_results TO advisory_writer""")
                cursor.execute(sql.SQL("CREATE ROLE advisory_assessor LOGIN PASSWORD {}")
                               .format(sql.Literal(writer_password)))
                cursor.execute("GRANT USAGE ON SCHEMA energy_analytics TO advisory_assessor")
                cursor.execute("GRANT SELECT ON energy_analytics.advisory_decisions TO advisory_assessor")
                cursor.execute("GRANT SELECT ON energy_analytics.advisory_results TO advisory_assessor")
                cursor.execute("GRANT INSERT, SELECT ON energy_analytics.advisory_trough_outcomes TO advisory_assessor")
                cursor.execute("GRANT INSERT, SELECT ON energy_analytics.advisory_trough_selection TO advisory_assessor")
        writer = FixtureEndpoint(
            host="127.0.0.1", port=port, dbname="advisory_test",
            user="advisory_writer", password=writer_password,
        )
        assessor = FixtureEndpoint(host=owner.host, port=owner.port, dbname=owner.dbname,
                                   user="advisory_assessor", password=writer_password)
        yield SimpleNamespace(
            host=owner.host, port=owner.port, dbname=owner.dbname,
            owner_user=owner.user, owner_password=owner.password,
            writer_user=writer.user, writer_password=writer.password,
            owner=owner.dsn, writer=writer.dsn,
            connect_owner=owner.connect, connect_writer=writer.connect,
            assessor=assessor.dsn, connect_assessor=assessor.connect,
        )
    finally:
        if created:
            docker(["rm", "--force", "--volumes", name])
