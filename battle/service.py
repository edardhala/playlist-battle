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
        "SELECT * FROM songs WHERE room_id = ? ORDER BY id DESC", (room_id,)
    ).fetchall()
