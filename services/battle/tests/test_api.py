import logging

import pytest

import config
import db
import web


def add(client, title="Yellow", artist="Coldplay", me="Ana", code="ROOM01"):
    return client.post(f"/rooms/{code}/songs", json={"title": title, "artist": artist, "me": me})


def playlist(client, me="Ana", code="ROOM01"):
    return client.get(f"/rooms/{code}/playlist?me={me}")


def test_add_vote_and_see_playlist(client):
    song_id = add(client).get_json()["id"]
    assert client.post(f"/rooms/ROOM01/songs/{song_id}/vote", json={"me": "Ben"}).status_code == 204
    data = playlist(client, me="Ben").get_json()
    assert data["rooms_available"] is True
    assert data["songs"][0]["title"] == "Yellow"
    assert data["songs"][0]["votes"] == 1
    assert data["songs"][0]["voted_by_me"] is True
    assert data["songs"][0]["added_at"].endswith("Z")
    assert playlist(client, me="Ana").get_json()["songs"][0]["voted_by_me"] is False


def test_bad_song_is_400(client):
    response = add(client, title="")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Please enter the title."}


def test_voting_twice_is_400(client):
    song_id = add(client).get_json()["id"]
    client.post(f"/rooms/ROOM01/songs/{song_id}/vote", json={"me": "Ana"})
    response = client.post(f"/rooms/ROOM01/songs/{song_id}/vote", json={"me": "Ana"})
    assert response.get_json() == {"error": "You already voted for this song."}


def test_unvote(client):
    song_id = add(client).get_json()["id"]
    client.post(f"/rooms/ROOM01/songs/{song_id}/vote", json={"me": "Ana"})
    assert client.delete(f"/rooms/ROOM01/songs/{song_id}/vote?me=Ana").status_code == 204
    assert playlist(client).get_json()["songs"][0]["votes"] == 0


def test_non_member_cannot_add_songs(client):
    response = add(client, me="Mallory")
    assert response.status_code == 403
    assert response.get_json() == {"error": "Join this room to add songs and vote."}


def test_only_host_can_play(client):
    add(client)
    response = client.post("/rooms/ROOM01/play", json={"me": "Ben"})
    assert response.status_code == 403
    assert response.get_json() == {"error": "Only the host can play the next song."}


def test_host_plays_winner(client):
    song_id = add(client).get_json()["id"]
    assert client.post("/rooms/ROOM01/play", json={"me": "Ana"}).get_json() == {"id": song_id}
    data = playlist(client).get_json()
    assert data["songs"] == []
    assert data["played"][0]["id"] == song_id
    assert data["played"][0]["played_at"].endswith("Z")


def test_unknown_room_is_404(client):
    assert playlist(client, code="ZZZZZZ").status_code == 404
    assert add(client, code="ZZZZZZ").status_code == 404


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "db": "ok", "version": "test-sha"}


def test_health_ignores_rooms_service(client, rooms_stub):
    rooms_stub.status = 500
    assert client.get("/health").status_code == 200


def test_health_503_when_database_is_down(client, monkeypatch):
    monkeypatch.setattr(web, "HEALTH_RETRY_DELAYS", ())
    client.application.config["DATABASE_URL"] = "mssql://nobody:wrong@127.0.0.1:1/none"
    assert client.get("/health").status_code == 503


def test_every_request_is_logged(client, caplog):
    with caplog.at_level(logging.INFO, logger="requests"):
        client.get("/health")
    assert any(r.getMessage().startswith("GET /health 200 ") for r in caplog.records)


def test_config_defaults():
    loaded = config.load_config({"DATABASE_URL": "mssql://u:p@h/d"})
    assert loaded["ROOMS_URL"] == "http://rooms:8000"
    assert loaded["ROOMS_TIMEOUT_S"] == 2
    with pytest.raises(SystemExit):
        config.load_config({})


def test_migrations_are_applied_once(make_database):
    conn = db.connect(make_database(), ())
    assert db.migrate(conn, "migrations") == ["001_create_songs_votes_played.sql"]
    assert db.migrate(conn, "migrations") == []
    conn.close()
