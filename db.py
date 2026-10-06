"""SQLite helpers shared by both domains. Each domain owns its own tables."""
import sqlite3

from flask import current_app, g


def connect(path):
    conn = sqlite3.connect(path)
    # Lets us write row["name"] instead of row[1].
    conn.row_factory = sqlite3.Row
    return conn


def init_db(path, schema):
    """Create the tables if they don't exist yet. Safe to run on every start."""
    conn = connect(path)
    conn.executescript(schema)
    conn.close()


def get_db():
    """Open one connection per request and reuse it."""
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()
