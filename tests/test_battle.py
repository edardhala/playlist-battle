import pytest

from battle import service
from battle.service import BattleError
from db import connect


@pytest.fixture
def conn():
    conn = connect(":memory:")
    conn.executescript(service.SCHEMA)
    yield conn
    conn.close()


def test_add_song(conn):
    song_id = service.add_song(conn, 1, " Bohemian Rhapsody ", "Queen", "Ana")
    songs = service.list_songs(conn, 1)
    assert len(songs) == 1
    assert songs[0]["id"] == song_id
    assert songs[0]["title"] == "Bohemian Rhapsody"
    assert songs[0]["added_by"] == "Ana"
    assert songs[0]["added_at"]


@pytest.mark.parametrize("title, artist", [("", "Queen"), ("Song", "  "), ("x" * 101, "Queen")])
def test_add_song_rejects_bad_text(conn, title, artist):
    with pytest.raises(BattleError):
        service.add_song(conn, 1, title, artist, "Ana")


def test_list_songs_newest_first_and_only_this_room(conn):
    service.add_song(conn, 1, "First", "A", "Ana")
    service.add_song(conn, 1, "Second", "B", "Ben")
    service.add_song(conn, 2, "Other room", "C", "Cleo")
    titles = [s["title"] for s in service.list_songs(conn, 1)]
    assert titles == ["Second", "First"]
