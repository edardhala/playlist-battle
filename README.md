# Playlist Battle

Friends join a shared room, submit songs, and vote. The playlist reorders
itself by a "hot" score that mixes votes with how recently a song was added.

Built as a single Flask process with SQLite (IE University, Individual Assignment 1).

## Features

- **Rooms:** start a room and get a 6-character code, or join one with a code or a share link.
- **Songs and votes:** add songs, vote once per song, and take a vote back. The same song can't be added twice while it's still in the battle.
- **Hot score ranking:** songs are ranked by `(votes + 1) / (age_hours + 2) ** 1.5`, so new songs get a chance against old popular ones.
- **Play the winner:** the host plays the top song. It shows as "Now playing" and earlier winners move to a "Played" list.
- **Listen links:** every song links to a YouTube search for it.
- **Live updates:** the room page checks for changes every 5 seconds and refreshes by itself when someone joins, adds a song or votes (not while you are typing).

## How to use it

1. Open http://localhost:8000, enter a room name and your name, and click **Start the battle**.
2. Send the share link on the room page to your friends. They only need to type their name.
3. Add songs and vote. The playlist reorders itself.
4. As the host, click **Play the winner** to play the top song.

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

## Project structure

```
app.py              starts the app, creates the tables and registers both domains
config.py           reads PORT and DATA_DIR from environment variables
db.py               SQLite connection helpers shared by both domains
rooms/service.py    Rooms domain rules: rooms and members tables
rooms/routes.py     Rooms pages: create, join, room page
battle/service.py   Battle domain rules: songs, votes, played tables and the hot score
battle/routes.py    Battle actions: add song, vote, remove vote, play the winner
templates/          HTML pages (Jinja)
static/             CSS, logo and live.js (live updates)
tests/              pytest tests
```

The two domains (Rooms and Battle) only share ids, never tables, so they could be split into separate services later (see ADR 2 and 3).

## Tests and coverage

```bash
pytest --cov=. --cov-report=term-missing
```

Test files are left out of the coverage number (see `.coveragerc`).

Latest result: **50 tests passed, 98% coverage** of the app code.

| File | Coverage |
|---|---|
| `rooms/service.py` | 100% |
| `battle/service.py` | 100% |
| `battle/routes.py` | 100% |
| `rooms/routes.py` | 96% |
| `app.py` | 92% |
| `config.py`, `db.py` | 100% |

The only lines not covered are the `python app.py` start-up lines and one error branch in `rooms/routes.py`.
