"""Rooms domain: create a room, join it with a code, list who is in it."""
import random
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS rooms (
    id    INTEGER PRIMARY KEY,
    code  TEXT NOT NULL UNIQUE,
    name  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS members (
    id       INTEGER PRIMARY KEY,
    room_id  INTEGER NOT NULL REFERENCES rooms(id),
    name     TEXT NOT NULL,
    is_host  INTEGER NOT NULL DEFAULT 0,
    UNIQUE (room_id, name)
);
"""

# No 0/O or 1/I, so codes are easy to read out loud.
CODE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
MAX_NAME_LENGTH = 40


class RoomError(Exception):
    """Raised when the user asks for something the rules don't allow."""


def make_code():
    return "".join(random.choice(CODE_LETTERS) for _ in range(6))


def check_name(name):
    name = name.strip()
    if not name:
        raise RoomError("Name can't be empty.")
    if len(name) > MAX_NAME_LENGTH:
        raise RoomError(f"Name must be at most {MAX_NAME_LENGTH} characters.")
    return name


def create_room(conn, room_name, host_name):
    """Create a room with its creator as host. Returns the room code."""
    room_name = check_name(room_name)
    host_name = check_name(host_name)
    code = make_code()
    cur = conn.execute("INSERT INTO rooms (code, name) VALUES (?, ?)", (code, room_name))
    conn.execute(
        "INSERT INTO members (room_id, name, is_host) VALUES (?, ?, 1)",
        (cur.lastrowid, host_name),
    )
    conn.commit()
    return code


def join_room(conn, code, name):
    """Add a person to an existing room. Returns the room code."""
    name = check_name(name)
    room = get_room(conn, code)
    if room is None:
        raise RoomError("No room with that code.")
    try:
        conn.execute(
            "INSERT INTO members (room_id, name) VALUES (?, ?)", (room["id"], name)
        )
    except sqlite3.IntegrityError:
        raise RoomError("That name is already taken in this room.")
    conn.commit()
    return room["code"]


def get_room(conn, code):
    code = code.strip().upper()
    return conn.execute("SELECT * FROM rooms WHERE code = ?", (code,)).fetchone()


def list_members(conn, room_id):
    """Host first, then everyone else in the order they joined."""
    return conn.execute(
        "SELECT * FROM members WHERE room_id = ? ORDER BY is_host DESC, id",
        (room_id,),
    ).fetchall()
