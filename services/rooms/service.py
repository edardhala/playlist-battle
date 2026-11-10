import random

import pymssql

CODE_LETTERS = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
MAX_NAME_LENGTH = 30


class RoomError(Exception):
    pass


def make_code():
    return "".join(random.choice(CODE_LETTERS) for _ in range(6))


def check_name(name):
    name = (name or "").strip()
    if not name:
        raise RoomError("Please enter a name.")
    if len(name) > MAX_NAME_LENGTH:
        raise RoomError(f"Name must be at most {MAX_NAME_LENGTH} characters.")
    return name


def create_room(conn, room_name, host_name):
    room_name = check_name(room_name)
    host_name = check_name(host_name)
    code = make_code()
    cur = conn.cursor()
    cur.execute("INSERT INTO rooms (code, name) OUTPUT INSERTED.id VALUES (%s, %s)", (code, room_name))
    room_id = cur.fetchone()["id"]
    cur.execute(
        "INSERT INTO members (room_id, name, is_host) VALUES (%s, %s, 1)",
        (room_id, host_name),
    )
    conn.commit()
    return code


def join_room(conn, code, name):
    name = check_name(name)
    room = get_room(conn, code)
    if room is None:
        raise RoomError("We couldn't find a room with that code.")
    try:
        conn.cursor().execute(
            "INSERT INTO members (room_id, name) VALUES (%s, %s)", (room["id"], name)
        )
    except pymssql.IntegrityError:
        conn.rollback()
        raise RoomError("Someone in this room already has that name. Try another one.")
    conn.commit()
    return room["code"]


def get_room(conn, code):
    cur = conn.cursor()
    cur.execute("SELECT id, code, name FROM rooms WHERE code = %s", ((code or "").strip().upper(),))
    return cur.fetchone()


def list_members(conn, room_id):
    cur = conn.cursor()
    cur.execute(
        "SELECT name, is_host FROM members WHERE room_id = %s ORDER BY is_host DESC, id",
        (room_id,),
    )
    return [{"name": row["name"], "is_host": bool(row["is_host"])} for row in cur.fetchall()]

