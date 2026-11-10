import os

import db

DEFAULT_PORT = 8000


def load_config(env=None):
    env = os.environ if env is None else env
    if not env.get("DATABASE_URL"):
        raise SystemExit("DATABASE_URL is not set")
    return {
        "PORT": int(env.get("PORT", DEFAULT_PORT)),
        "DATABASE_URL": env["DATABASE_URL"],
        "CORS_ORIGIN": env.get("CORS_ORIGIN", "http://localhost:8080"),
        "VERSION": env.get("GIT_SHA", "dev"),
        "DB_RETRY_DELAYS": db.RETRY_DELAYS,
    }
