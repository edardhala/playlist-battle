from datetime import datetime, timezone

import pymssql

MAX_TEXT_LENGTH = 80

SONG_COLUMNS = "s.id, s.room_id, s.title, s.artist, s.added_by, s.added_at"


class BattleError(Exception):
    pass


def utc_now():
    return datetime.now(timezone.utc).replace(tzinfo=None)


def check_text(value, field):
    value = (value or "").strip()
    if not value:
        raise BattleError(f"Please enter the {field.lower()}.")
    if len(value) > MAX_TEXT_LENGTH:
        raise BattleError(f"{field} must be at most {MAX_TEXT_LENGTH} characters.")
    return value


def add_song(conn, room_id, title, artist, added_by):
    title = check_text(title, "Title")
    artist = check_text(artist, "Artist")
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM songs WHERE room_id = %s AND title = %s AND artist = %s"
        " AND id NOT IN (SELECT song_id FROM played)",
        (room_id, title, artist),
    )
    if cur.fetchone() is not None:
        raise BattleError("That song is already in the playlist.")
    cur.execute(
        "INSERT INTO songs (room_id, title, artist, added_by, added_at)"
        " OUTPUT INSERTED.id VALUES (%s, %s, %s, %s, %s)",
        (room_id, title, artist, added_by, utc_now()),
    )
    song_id = cur.fetchone()["id"]
    conn.commit()
    return song_id


def list_songs(conn, room_id):
    cur = conn.cursor()
    cur.execute(
        f"SELECT {SONG_COLUMNS}, COUNT(v.id) AS votes FROM songs s"
        " LEFT JOIN votes v ON v.song_id = s.id"
        " WHERE s.room_id = %s AND s.id NOT IN (SELECT song_id FROM played)"
        f" GROUP BY {SONG_COLUMNS} ORDER BY s.id DESC",
        (room_id,),
    )
    return cur.fetchall()


def vote(conn, room_id, song_id, voter):
    cur = conn.cursor()
    cur.execute("SELECT id FROM songs WHERE id = %s AND room_id = %s", (song_id, room_id))
    if cur.fetchone() is None:
        raise BattleError("That song doesn't exist.")
    try:
        cur.execute("INSERT INTO votes (song_id, voter) VALUES (%s, %s)", (song_id, voter))
    except pymssql.IntegrityError:
        conn.rollback()
        raise BattleError("You already voted for this song.")
    conn.commit()


def remove_vote(conn, room_id, song_id, voter):
    conn.cursor().execute(
        "DELETE v FROM votes v JOIN songs s ON s.id = v.song_id"
        " WHERE s.room_id = %s AND v.song_id = %s AND v.voter = %s",
        (room_id, song_id, voter),
    )
    conn.commit()


def songs_voted_by(conn, room_id, voter):
    cur = conn.cursor()
    cur.execute(
        "SELECT v.song_id FROM votes v JOIN songs s ON s.id = v.song_id"
        " WHERE s.room_id = %s AND v.voter = %s",
        (room_id, voter),
    )
    return {row["song_id"] for row in cur.fetchall()}


def hot_score(votes, added_at, now):
    age_hours = (now - added_at).total_seconds() / 3600
    return (votes + 1) / (age_hours + 2) ** 1.5


def ranked_songs(conn, room_id, now=None):
    now = now or utc_now()
    songs = list_songs(conn, room_id)
    return sorted(songs, key=lambda song: hot_score(song["votes"], song["added_at"], now), reverse=True)


def play_next(conn, room_id, now=None):
    songs = ranked_songs(conn, room_id, now)
    if not songs:
        raise BattleError("There are no songs left to play.")
    winner = songs[0]
    conn.cursor().execute(
        "INSERT INTO played (song_id, played_at) VALUES (%s, %s)", (winner["id"], utc_now())
    )
    conn.commit()
    return winner["id"]


def played_songs(conn, room_id):
    cur = conn.cursor()
    cur.execute(
        f"SELECT {SONG_COLUMNS}, p.played_at FROM played p"
        " JOIN songs s ON s.id = p.song_id"
        " WHERE s.room_id = %s ORDER BY p.id DESC",
        (room_id,),
    )
    return cur.fetchall()
