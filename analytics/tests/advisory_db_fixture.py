"""Disposable-only PostgreSQL fixture: no external DSN input or fallback."""
from contextlib import closing
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
        owner_dsn = make_dsn(host="127.0.0.1", port=port,
                             dbname="advisory_test", user="postgres",
                             password=owner_password)
        deadline = time.monotonic() + 30
        while True:
            try:
                connection = psycopg2.connect(owner_dsn, connect_timeout=1)
                break
            except psycopg2.Error:
                if time.monotonic() >= deadline:
                    raise RuntimeError("disposable advisory database not ready") from None
                time.sleep(0.1)
        with closing(connection), connection:
            pending = plan_migrations(discover_migrations(),
                                      get_applied_migrations(connection))
            assert [m.version for m in pending] == [1, 2]
            assert apply_migrations(connection, pending) == [1, 2]
            with connection.cursor() as cursor:
                cursor.execute("""INSERT INTO energy_analytics.system_epochs
                    (epoch_id, current_analytics) VALUES ('test_bank', true)""")
                cursor.execute(sql.SQL("CREATE ROLE advisory_writer LOGIN PASSWORD {}")
                               .format(sql.Literal(writer_password)))
                cursor.execute("GRANT USAGE ON SCHEMA energy_analytics TO advisory_writer")
                cursor.execute("""GRANT INSERT, SELECT ON
                    energy_analytics.advisory_decisions,
                    energy_analytics.advisory_results TO advisory_writer""")
        writer_dsn = make_dsn(host="127.0.0.1", port=port,
                              dbname="advisory_test", user="advisory_writer",
                              password=writer_password)
        yield SimpleNamespace(owner=owner_dsn, writer=writer_dsn)
    finally:
        if created:
            docker(["rm", "--force", name])
