import os
import subprocess
import time

import pytest
import requests

ROOMS_URL = os.environ.get("ROOMS_URL", "http://localhost:8001")
BATTLE_URL = os.environ.get("BATTLE_URL", "http://localhost:8002")


def wait_healthy(url, seconds=60):
    deadline = time.time() + seconds
    while time.time() < deadline:
        try:
            if requests.get(f"{url}/health", timeout=2).status_code == 200:
                return
        except requests.RequestException:
            pass
        time.sleep(1)
    pytest.fail(f"{url} did not become healthy")


def compose(*args):
    subprocess.run(["docker", "compose", *args], check=True)


@pytest.fixture(scope="module", autouse=True)
def stack():
    wait_healthy(ROOMS_URL)
    wait_healthy(BATTLE_URL)


def test_song_added_through_battle_is_checked_against_rooms():
    room = requests.post(f"{ROOMS_URL}/rooms", json={"room_name": "E2E", "your_name": "Ana"}, timeout=5).json()
    code = room["code"]
    requests.post(f"{ROOMS_URL}/rooms/{code}/members", json={"your_name": "Ben"}, timeout=5).raise_for_status()

    added = requests.post(f"{BATTLE_URL}/rooms/{code}/songs", json={"title": "Yellow", "artist": "Coldplay", "me": "Ben"}, timeout=5)
    assert added.status_code == 201
    stranger = requests.post(f"{BATTLE_URL}/rooms/{code}/songs", json={"title": "Fix You", "artist": "Coldplay", "me": "Eve"}, timeout=5)
    assert stranger.status_code == 403
    not_host = requests.post(f"{BATTLE_URL}/rooms/{code}/play", json={"me": "Ben"}, timeout=5)
    assert not_host.status_code == 403
    played = requests.post(f"{BATTLE_URL}/rooms/{code}/play", json={"me": "Ana"}, timeout=5)
    assert played.json() == added.json()


def test_battle_degrades_when_rooms_is_stopped():
    code = requests.post(f"{ROOMS_URL}/rooms", json={"room_name": "Outage", "your_name": "Ana"}, timeout=5).json()["code"]
    requests.post(f"{BATTLE_URL}/rooms/{code}/songs", json={"title": "Yellow", "artist": "Coldplay", "me": "Ana"}, timeout=5)
    requests.get(f"{BATTLE_URL}/rooms/{code}/playlist", timeout=5).raise_for_status()

    compose("stop", "rooms")
    try:
        started = time.time()
        write = requests.post(f"{BATTLE_URL}/rooms/{code}/songs", json={"title": "Fix You", "artist": "Coldplay", "me": "Ana"}, timeout=10)
        assert write.status_code == 503
        assert time.time() - started < 5
        read = requests.get(f"{BATTLE_URL}/rooms/{code}/playlist", timeout=10)
        assert read.status_code == 200
        assert read.json()["rooms_available"] is False
        assert requests.get(f"{BATTLE_URL}/health", timeout=5).status_code == 200
    finally:
        compose("start", "rooms")
        wait_healthy(ROOMS_URL)
