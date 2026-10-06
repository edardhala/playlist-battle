import pytest

from db import connect, init_db
from rooms import service
from rooms.service import RoomError


@pytest.fixture
def conn():
    conn = connect(":memory:")
    conn.executescript(service.SCHEMA)
    yield conn
    conn.close()


def test_make_code():
    code = service.make_code()
    assert len(code) == 6
    assert all(letter in service.CODE_LETTERS for letter in code)


def test_check_name_trims_spaces():
    assert service.check_name("  Ana ") == "Ana"


@pytest.mark.parametrize("bad", ["", "   ", "x" * 31])
def test_check_name_rejects_bad_names(bad):
    with pytest.raises(RoomError):
        service.check_name(bad)


def test_create_room_adds_host(conn):
    code = service.create_room(conn, "Road trip", "Ana")
    room = service.get_room(conn, code)
    assert room["name"] == "Road trip"
    members = service.list_members(conn, room["id"])
    assert [(m["name"], m["is_host"]) for m in members] == [("Ana", 1)]


def test_join_room(conn):
    code = service.create_room(conn, "Road trip", "Ana")
    service.join_room(conn, code.lower(), "Ben")
    room = service.get_room(conn, code)
    names = [m["name"] for m in service.list_members(conn, room["id"])]
    assert names == ["Ana", "Ben"]


def test_join_unknown_room(conn):
    with pytest.raises(RoomError, match="couldn.t find"):
        service.join_room(conn, "ZZZZZZ", "Ben")


def test_join_with_taken_name(conn):
    code = service.create_room(conn, "Road trip", "Ana")
    with pytest.raises(RoomError, match="already has that name"):
        service.join_room(conn, code, "Ana")


def test_init_db_can_run_twice(tmp_path):
    path = tmp_path / "test.db"
    init_db(path, service.SCHEMA)
    init_db(path, service.SCHEMA)
    conn = connect(path)
    assert service.get_room(conn, "ABCDEF") is None
    conn.close()
