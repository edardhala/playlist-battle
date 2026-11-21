import shutil

import db


def test_joined_at_migration_keeps_existing_members(make_database, tmp_path):
    shutil.copy("migrations/001_create_rooms_and_members.sql", tmp_path)
    conn = db.connect(make_database(), ())
    db.migrate(conn, tmp_path)
    cur = conn.cursor()
    cur.execute("INSERT INTO rooms (code, name) VALUES ('ABC234', 'Old room')")
    cur.execute("INSERT INTO members (room_id, name, is_host) SELECT id, 'Ana', 1 FROM rooms")
    conn.commit()

    shutil.copy("migrations/002_add_members_joined_at.sql", tmp_path)
    assert db.migrate(conn, tmp_path) == ["002_add_members_joined_at.sql"]

    cur.execute("SELECT m.name, m.is_host, m.joined_at FROM members m")
    rows = cur.fetchall()
    assert len(rows) == 1
    assert rows[0]["name"] == "Ana" and rows[0]["is_host"]
    assert rows[0]["joined_at"] is not None
    conn.close()
