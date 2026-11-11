import os
import uuid

import pymssql
import pytest

import db
from app import create_app

ADMIN_URL = os.environ.get("TEST_DATABASE_URL", "mssql://sa:Local_Dev_Only_1@localhost:1433/master")
TABLES = "votes played songs".split()


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
        name = f"battle_test_{uuid.uuid4().hex[:8]}"
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
def client(env, conn):
    return create_app(env).test_client()


class RoomsStub:
    def __init__(self):
        self.rooms = {}
        self.delay_s = 0
        self.status = 200

    def add_room(self, room_id, code, members):
        self.rooms[code] = {
            "id": room_id,
            "code": code,
            "name": f"Room {code}",
            "members": [{"name": name, "is_host": index == 0} for index, name in enumerate(members)],
        }


@pytest.fixture(scope="session")
def rooms_server():
    import threading
    import time

    from flask import Flask, jsonify
    from werkzeug.serving import make_server

    stub = RoomsStub()
    app = Flask("rooms_stub")

    @app.get("/rooms/<code>")
    def show(code):
        time.sleep(stub.delay_s)
        if stub.status != 200:
            return jsonify(error="broken"), stub.status
        room = stub.rooms.get(code)
        if room is None:
            return jsonify(error="We couldn't find a room with that code."), 404
        return jsonify(room)

    server = make_server("127.0.0.1", 0, app, threaded=True)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    stub.url = f"http://127.0.0.1:{server.server_port}"
    yield stub
    server.shutdown()


@pytest.fixture
def rooms_stub(rooms_server):
    rooms_server.rooms.clear()
    rooms_server.delay_s = 0
    rooms_server.status = 200
    rooms_server.add_room(1, "ROOM01", ["Ana", "Ben"])
    return rooms_server


@pytest.fixture
def env(test_url, rooms_stub):
    return {
        "DATABASE_URL": test_url,
        "GIT_SHA": "test-sha",
        "ROOMS_URL": rooms_stub.url,
        "ROOMS_TIMEOUT_S": "0.5",
    }
