from datetime import datetime, timedelta

import pytest

import service
from service import BattleError

NOW = datetime(2026, 11, 1, 12, 0, 0)


def set_added_at(conn, song_id, when):
    conn.cursor().execute("UPDATE songs SET added_at = %s WHERE id = %s", (when, song_id))
    conn.commit()


def test_check_text_strips_and_validates():
    assert service.check_text("  Yellow ", "Title") == "Yellow"
    with pytest.raises(BattleError, match="Please enter the title."):
        service.check_text(" ", "Title")
    with pytest.raises(BattleError, match="at most 80"):
        service.check_text("x" * 81, "Artist")


def test_add_and_list_songs(conn):
    song_id = service.add_song(conn, 1, "Yellow", "Coldplay", "Ana")
    songs = service.list_songs(conn, 1)
    assert [(s["id"], s["title"], s["votes"]) for s in songs] == [(song_id, "Yellow", 0)]
    assert service.list_songs(conn, 2) == []


def test_duplicate_song_is_blocked_ignoring_case(conn):
    service.add_song(conn, 1, "Yellow", "Coldplay", "Ana")
    with pytest.raises(BattleError, match="already in the playlist"):
        service.add_song(conn, 1, "yellow", "COLDPLAY", "Ben")
    service.add_song(conn, 2, "Yellow", "Coldplay", "Ben")


def test_song_can_be_added_again_after_it_was_played(conn):
    service.add_song(conn, 1, "Yellow", "Coldplay", "Ana")
    service.play_next(conn, 1)
    service.add_song(conn, 1, "Yellow", "Coldplay", "Ana")


def test_vote_once_per_person(conn):
    song_id = service.add_song(conn, 1, "Yellow", "Coldplay", "Ana")
    service.vote(conn, 1, song_id, "Ben")
    with pytest.raises(BattleError, match="already voted"):
        service.vote(conn, 1, song_id, "Ben")
    service.vote(conn, 1, song_id, "Ana")
    assert service.list_songs(conn, 1)[0]["votes"] == 2


def test_vote_for_song_in_other_room_is_rejected(conn):
    song_id = service.add_song(conn, 2, "Yellow", "Coldplay", "Ana")
    with pytest.raises(BattleError, match="doesn't exist"):
        service.vote(conn, 1, song_id, "Ben")


def test_remove_vote_and_songs_voted_by(conn):
    song_id = service.add_song(conn, 1, "Yellow", "Coldplay", "Ana")
    service.vote(conn, 1, song_id, "Ben")
    assert service.songs_voted_by(conn, 1, "Ben") == {song_id}
    assert service.songs_voted_by(conn, 2, "Ben") == set()
    service.remove_vote(conn, 2, song_id, "Ben")
    assert service.songs_voted_by(conn, 1, "Ben") == {song_id}
    service.remove_vote(conn, 1, song_id, "Ben")
    assert service.songs_voted_by(conn, 1, "Ben") == set()


def test_hot_score_prefers_votes_and_new_songs():
    assert service.hot_score(5, NOW, NOW) > service.hot_score(1, NOW, NOW)
    assert service.hot_score(1, NOW, NOW) > service.hot_score(1, NOW - timedelta(hours=5), NOW)
    assert service.hot_score(0, NOW, NOW) == pytest.approx(1 / 2**1.5)


def test_ranked_songs_new_song_can_beat_old_popular_one(conn):
    old = service.add_song(conn, 1, "Old", "A", "Ana")
    new = service.add_song(conn, 1, "New", "B", "Ana")
    set_added_at(conn, old, NOW - timedelta(hours=24))
    set_added_at(conn, new, NOW)
    for voter in ["Ana", "Ben", "Cy"]:
        service.vote(conn, 1, old, voter)
    assert [s["id"] for s in service.ranked_songs(conn, 1, NOW)] == [new, old]


def test_play_next_moves_winner_to_played(conn):
    first = service.add_song(conn, 1, "Yellow", "Coldplay", "Ana")
    second = service.add_song(conn, 1, "Fix You", "Coldplay", "Ana")
    service.vote(conn, 1, first, "Ben")
    assert service.play_next(conn, 1) == first
    assert [s["id"] for s in service.list_songs(conn, 1)] == [second]
    assert [s["id"] for s in service.played_songs(conn, 1)] == [first]


def test_play_next_with_empty_playlist(conn):
    with pytest.raises(BattleError, match="no songs left"):
        service.play_next(conn, 1)
