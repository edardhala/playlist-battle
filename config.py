"""App settings, read from environment variables so nothing is hard-coded."""
import os
from pathlib import Path

DEFAULT_PORT = 8000  # not 5000: macOS uses 5000 for AirPlay
DB_FILENAME = "playlist_battle.db"


def load_config(env=None):
    """Build the config dict from env vars (or a dict passed in by tests)."""
    env = os.environ if env is None else env
    data_dir = Path(env.get("DATA_DIR", "data"))
    return {
        "PORT": int(env.get("PORT", DEFAULT_PORT)),
        "DATA_DIR": data_dir,
        "DATABASE": data_dir / DB_FILENAME,
    }
