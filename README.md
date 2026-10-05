# Playlist Battle

Friends join a shared room, submit songs, and vote. The playlist reorders
itself by a "hot" score that mixes votes with how recently a song was added.

Built as a single Flask process with SQLite (IE University, Individual Assignment 1).

## Setup

Requires Python 3.10+.

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
python app.py
```

Then open http://localhost:8000. Health check: http://localhost:8000/health

## Configuration

All settings come from environment variables, and every one has a default.

| Variable   | Default | Meaning                                   |
|------------|---------|-------------------------------------------|
| `PORT`     | `8000`  | Port the server listens on (on `0.0.0.0`) |
| `DATA_DIR` | `data`  | Folder for the SQLite file                |

The database file is always `$DATA_DIR/playlist_battle.db`. The folder is
created automatically on startup.

## Tests and coverage

```bash
pytest --cov=. --cov-report=term-missing
```
