import logging
import re
import time
from pathlib import Path
from urllib.parse import unquote, urlparse

import pymssql
from flask import current_app, g

log = logging.getLogger(__name__)

RETRY_DELAYS = (1, 2, 4, 8, 15, 30)

CREATE_MIGRATIONS_TABLE = """
IF OBJECT_ID('schema_migrations') IS NULL
CREATE TABLE schema_migrations (
    version     NVARCHAR(255) NOT NULL PRIMARY KEY,
    applied_at  DATETIME2 NOT NULL DEFAULT SYSUTCDATETIME()
)
"""

LOCK = """
DECLARE @result INT;
EXEC @result = sp_getapplock @Resource = 'schema_migrations', @LockMode = 'Exclusive',
    @LockOwner = 'Session', @LockTimeout = 60000;
IF @result < 0 THROW 50000, 'Could not get the migrations lock.', 1;
"""

UNLOCK = "EXEC sp_releaseapplock @Resource = 'schema_migrations', @LockOwner = 'Session'"


def parse_url(url):
    parts = urlparse(url)
    return {
        "server": parts.hostname,
        "port": parts.port or 1433,
        "user": unquote(parts.username or ""),
        "password": unquote(parts.password or ""),
        "database": parts.path.lstrip("/"),
    }


def connect(url, retry_delays=RETRY_DELAYS):
    for delay in (*retry_delays, None):
        try:
            return pymssql.connect(**parse_url(url), as_dict=True, login_timeout=10, timeout=30)
        except pymssql.OperationalError as err:
            if delay is None:
                raise
            log.warning("database not reachable (%s), retrying in %ss", err, delay)
            time.sleep(delay)


def split_batches(sql):
    return [batch for batch in re.split(r"^\s*GO\s*$", sql, flags=re.MULTILINE | re.IGNORECASE) if batch.strip()]


def migrate(conn, folder):
    cur = conn.cursor()
    cur.execute(LOCK)
    try:
        cur.execute(CREATE_MIGRATIONS_TABLE)
        conn.commit()
        cur.execute("SELECT version FROM schema_migrations")
        applied = {row["version"] for row in cur.fetchall()}
        pending = [path for path in sorted(Path(folder).glob("*.sql")) if path.name not in applied]
        for path in pending:
            for batch in split_batches(path.read_text()):
                cur.execute(batch)
            cur.execute("INSERT INTO schema_migrations (version) VALUES (%s)", (path.name,))
            conn.commit()
            log.info("applied migration %s", path.name)
        if not pending:
            log.info("no pending migrations, %d already applied", len(applied))
        return [path.name for path in pending]
    except Exception:
        conn.rollback()
        raise
    finally:
        cur.execute(UNLOCK)
        conn.commit()


def check(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) AS applied FROM schema_migrations")
    cur.fetchone()
    cur.execute("UPDATE TOP (1) schema_migrations SET applied_at = applied_at")
    conn.rollback()


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE_URL"], current_app.config["DB_RETRY_DELAYS"])
    return g.db


def close_db(exc=None):
    conn = g.pop("db", None)
    if conn is not None:
        conn.close()
