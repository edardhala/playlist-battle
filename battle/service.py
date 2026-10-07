import sqlite3
from datetime import datetime, timezone

SCHEMA = """
CREATE TABLE IF NOT EXISTS songs (
    id        INTEGER PRIMARY KEY,
    room_id   INTEGER NOT NULL,
    title     TEXT NOT NULL,
    artist    TEXT NOT NULL,
    added_by  TEXT NOT NULL,
    added_at  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS votes (
    id       INTEGER PRIMARY KEY,
    song_id  INTEGER NOT NULL REFERENCES songs(id),
    voter    TEXT NOT NULL,
    UNIQUE (song_id, voter)
);
"""

MAX_TEXT_LENGTH = 80


class BattleError(Exception):
    pass


def check_text(value, field):
    value = value.strip()
    if not value:
        raise BattleError(f"Please enter the {field.lower()}.")
    if len(value) > MAX_TEXT_LENGTH:
        raise BattleError(f"{field} must be at most {MAX_TEXT_LENGTH} characters.")
    return value


def add_song(conn, room_id, title, artist, added_by):
    title = check_text(title, "Title")
    artist = check_text(artist, "Artist")
    added_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    cur = conn.execute(
        "INSERT INTO songs (room_id, title, artist, added_by, added_at)"
        " VALUES (?, ?, ?, ?, ?)",
        (room_id, title, artist, added_by, added_at),
    )
    conn.commit()
    return cur.lastrowid


def list_songs(conn, room_id):
    return conn.execute(
        "SELECT songs.*, COUNT(votes.id) AS votes FROM songs"
        " LEFT JOIN votes ON votes.song_id = songs.id"
        " WHERE songs.room_id = ? GROUP BY songs.id ORDER BY songs.id DESC",
        (room_id,),
    ).fetchall()


def vote(conn, song_id, voter):
    song = conn.execute("SELECT id FROM songs WHERE id = ?", (song_id,)).fetchone()
    if song is None:
        raise BattleError("That song doesn't exist.")
    try:
        conn.execute("INSERT INTO votes (song_id, voter) VALUES (?, ?)", (song_id, voter))
    except sqlite3.IntegrityError:
        raise BattleError("You already voted for this song.")
    conn.commit()


def remove_vote(conn, song_id, voter):
    conn.execute("DELETE FROM votes WHERE song_id = ? AND voter = ?", (song_id, voter))
    conn.commit()


def hot_score(votes, added_at, now):
    age_hours = (now - datetime.fromisoformat(added_at)).total_seconds() / 3600
    return (votes + 1) / (age_hours + 2) ** 1.5


def ranked_songs(conn, room_id, now=None):
    now = now or datetime.now(timezone.utc)
    songs = list_songs(conn, room_id)
    return sorted(songs, key=lambda song: hot_score(song["votes"], song["added_at"], now), reverse=True)
