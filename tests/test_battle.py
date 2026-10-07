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


@pytest.mark.parametrize("title, artist", [("", "Queen"), ("Song", "  "), ("x" * 81, "Queen")])
def test_add_song_rejects_bad_text(conn, title, artist):
    with pytest.raises(BattleError):
        service.add_song(conn, 1, title, artist, "Ana")


def test_list_songs_newest_first_and_only_this_room(conn):
    service.add_song(conn, 1, "First", "A", "Ana")
    service.add_song(conn, 1, "Second", "B", "Ben")
    service.add_song(conn, 2, "Other room", "C", "Cleo")
    titles = [s["title"] for s in service.list_songs(conn, 1)]
    assert titles == ["Second", "First"]


def test_new_song_has_no_votes(conn):
    service.add_song(conn, 1, "Song", "Artist", "Ana")
    assert service.list_songs(conn, 1)[0]["votes"] == 0


def test_vote_counts_each_person_once(conn):
    song_id = service.add_song(conn, 1, "Song", "Artist", "Ana")
    service.vote(conn, song_id, "Ana")
    service.vote(conn, song_id, "Ben")
    assert service.list_songs(conn, 1)[0]["votes"] == 2
    with pytest.raises(BattleError, match="already voted"):
        service.vote(conn, song_id, "Ben")


def test_vote_for_missing_song(conn):
    with pytest.raises(BattleError, match="doesn't exist"):
        service.vote(conn, 999, "Ana")


def test_remove_vote(conn):
    song_id = service.add_song(conn, 1, "Song", "Artist", "Ana")
    service.vote(conn, song_id, "Ana")
    service.remove_vote(conn, song_id, "Ana")
    assert service.list_songs(conn, 1)[0]["votes"] == 0
