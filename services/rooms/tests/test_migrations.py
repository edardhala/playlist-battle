from pathlib import Path

import pytest

import config
import db


def test_migrate_twice_applies_nothing_the_second_time(make_database):
    conn = db.connect(make_database(), ())
    assert db.migrate(conn, "migrations") == sorted(path.name for path in Path("migrations").glob("*.sql"))
    assert db.migrate(conn, "migrations") == []
    conn.close()


def test_failed_migration_is_rolled_back(make_database, tmp_path):
    (tmp_path / "001_bad.sql").write_text("CREATE TABLE ok_table (id INT)\nGO\nSELECT * FROM missing_table")
    conn = db.connect(make_database(), ())
    with pytest.raises(Exception):
        db.migrate(conn, tmp_path)
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS n FROM schema_migrations")
    assert cur.fetchone()["n"] == 0
    cur.execute("SELECT OBJECT_ID('ok_table') AS id")
    assert cur.fetchone()["id"] is None
    conn.close()


def test_split_batches_on_go_lines():
    assert db.split_batches("A\nGO\nB\n  go  \n") == ["A\n", "\nB\n"]


def test_parse_url_decodes_password():
    assert db.parse_url("mssql://user:p%40ss@host:1444/name") == {
        "server": "host", "port": 1444, "user": "user", "password": "p@ss", "database": "name",
    }


def test_connect_gives_up_after_retries(monkeypatch):
    monkeypatch.setattr(db.time, "sleep", lambda s: None)
    with pytest.raises(db.pymssql.OperationalError):
        db.connect("mssql://nobody:wrong@127.0.0.1:1/none", (0,))


def test_config_requires_database_url():
    with pytest.raises(SystemExit):
        config.load_config({})


def test_config_defaults():
    loaded = config.load_config({"DATABASE_URL": "mssql://u:p@h/d"})
    assert loaded["PORT"] == 8000
    assert loaded["VERSION"] == "dev"
