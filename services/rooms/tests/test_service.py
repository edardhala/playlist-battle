import pytest

import service
from service import RoomError


def test_make_code_uses_allowed_letters():
    code = service.make_code()
    assert len(code) == 6
    assert set(code) <= set(service.CODE_LETTERS)


def test_check_name_strips_spaces():
    assert service.check_name("  Ana  ") == "Ana"


@pytest.mark.parametrize("name", ["", "   ", None])
def test_check_name_rejects_empty(name):
    with pytest.raises(RoomError, match="Please enter a name."):
        service.check_name(name)


def test_check_name_rejects_long_names():
    with pytest.raises(RoomError, match="at most 30"):
        service.check_name("x" * 31)


def test_create_room_makes_host(conn):
    code = service.create_room(conn, "Road trip", "Ana")
    room = service.get_room(conn, code)
    assert room["name"] == "Road trip"
    assert service.list_members(conn, room["id"]) == [{"name": "Ana", "is_host": True}]


def test_join_room_adds_guest_after_host(conn):
    code = service.create_room(conn, "Road trip", "Ana")
    assert service.join_room(conn, code.lower(), "Ben") == code
    room = service.get_room(conn, code)
    assert service.list_members(conn, room["id"]) == [
        {"name": "Ana", "is_host": True},
        {"name": "Ben", "is_host": False},
    ]


def test_join_unknown_room(conn):
    with pytest.raises(RoomError, match="couldn't find"):
        service.join_room(conn, "ZZZZZZ", "Ben")


def test_join_with_taken_name(conn):
    code = service.create_room(conn, "Road trip", "Ana")
    with pytest.raises(RoomError, match="already has that name"):
        service.join_room(conn, code, "Ana")


def test_get_room_ignores_case_and_spaces(conn):
    code = service.create_room(conn, "Road trip", "Ana")
    assert service.get_room(conn, f" {code.lower()} ")["code"] == code
