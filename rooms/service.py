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

CODE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
MAX_NAME_LENGTH = 30


class RoomError(Exception):
    pass


def make_code():
    return "".join(random.choice(CODE_LETTERS) for _ in range(6))


def check_name(name):
    name = name.strip()
    if not name:
        raise RoomError("Please enter a name.")
    if len(name) > MAX_NAME_LENGTH:
        raise RoomError(f"Name must be at most {MAX_NAME_LENGTH} characters.")
    return name


def create_room(conn, room_name, host_name):
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
    name = check_name(name)
    room = get_room(conn, code)
    if room is None:
        raise RoomError("We couldn't find a room with that code.")
    try:
        conn.execute(
            "INSERT INTO members (room_id, name) VALUES (?, ?)", (room["id"], name)
        )
    except sqlite3.IntegrityError:
        raise RoomError("Someone in this room already has that name. Try another one.")
    conn.commit()
    return room["code"]


def get_room(conn, code):
    code = code.strip().upper()
    return conn.execute("SELECT * FROM rooms WHERE code = ?", (code,)).fetchone()


def list_members(conn, room_id):
    return conn.execute(
        "SELECT * FROM members WHERE room_id = ? ORDER BY is_host DESC, id",
        (room_id,),
    ).fetchall()
