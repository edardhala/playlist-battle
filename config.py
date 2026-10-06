import os
from pathlib import Path

DEFAULT_PORT = 8000
DB_FILENAME = "playlist_battle.db"


def load_config(env=None):
    env = os.environ if env is None else env
    data_dir = Path(env.get("DATA_DIR", "data"))
    return {
        "PORT": int(env.get("PORT", DEFAULT_PORT)),
        "DATA_DIR": data_dir,
        "DATABASE": data_dir / DB_FILENAME,
    }
