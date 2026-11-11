import os
import uuid

import pymssql
import pytest

import db
from app import create_app

ADMIN_URL = os.environ.get("TEST_DATABASE_URL", "mssql://sa:Local_Dev_Only_1@localhost:1433/master")
TABLES = "members rooms".split()


def admin_execute(sql):
    conn = pymssql.connect(**db.parse_url(ADMIN_URL), autocommit=True)
    try:
        conn.cursor().execute(sql)
    finally:
        conn.close()


def database_url(name):
    return ADMIN_URL.rsplit("/", 1)[0] + "/" + name


@pytest.fixture(scope="session")
def make_database():
    names = []

    def make():
        name = f"rooms_test_{uuid.uuid4().hex[:8]}"
        admin_execute(f"CREATE DATABASE {name}")
        names.append(name)
        return database_url(name)

    yield make
    for name in names:
        admin_execute(f"ALTER DATABASE {name} SET SINGLE_USER WITH ROLLBACK IMMEDIATE; DROP DATABASE {name}")


@pytest.fixture(scope="session")
def test_url(make_database):
    url = make_database()
    conn = db.connect(url, ())
    db.migrate(conn, "migrations")
    conn.close()
    return url


@pytest.fixture
def conn(test_url):
    conn = db.connect(test_url, ())
    yield conn
    conn.rollback()
    cur = conn.cursor()
    for table in TABLES:
        cur.execute(f"DELETE FROM {table}")
    conn.commit()
    conn.close()


@pytest.fixture
def env(test_url):
    return {"DATABASE_URL": test_url, "GIT_SHA": "test-sha"}


@pytest.fixture
def client(env, conn):
    return create_app(env).test_client()
