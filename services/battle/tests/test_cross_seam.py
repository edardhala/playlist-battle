import time

from rooms_client import RoomsClient, RoomsUnavailable

import pytest

CLOSED_PORT_URL = "http://127.0.0.1:9"


def test_client_reads_room_over_http(rooms_stub):
    room = RoomsClient(rooms_stub.url, 0.5).get_room(" room01 ")
    assert room["id"] == 1
    assert [m["name"] for m in room["members"]] == ["Ana", "Ben"]


def test_client_returns_none_for_unknown_room(rooms_stub):
    assert RoomsClient(rooms_stub.url, 0.5).get_room("ZZZZZZ") is None


def test_client_times_out_instead_of_hanging(rooms_stub):
    rooms_stub.delay_s = 2
    started = time.perf_counter()
    with pytest.raises(RoomsUnavailable):
        RoomsClient(rooms_stub.url, 0.3).get_room("ROOM01")
    assert time.perf_counter() - started < 1.5


def test_client_treats_server_errors_as_unavailable(rooms_stub):
    rooms_stub.status = 500
    with pytest.raises(RoomsUnavailable):
        RoomsClient(rooms_stub.url, 0.5).get_room("ROOM01")


def test_reads_fall_back_to_cached_room_id(rooms_stub):
    client = RoomsClient(rooms_stub.url, 0.5)
    assert client.room_id_for_reading("ROOM01") == (1, True)
    client.base_url = CLOSED_PORT_URL
    assert client.room_id_for_reading("room01") == (1, False)
    with pytest.raises(RoomsUnavailable):
        client.room_id_for_reading("OTHER1")


def test_adding_a_song_crosses_the_seam(client, rooms_stub):
    response = client.post("/rooms/ROOM01/songs", json={"title": "Yellow", "artist": "Coldplay", "me": "Ana"})
    assert response.status_code == 201
    rooms_stub.add_room(1, "ROOM01", ["Ana"])
    response = client.post("/rooms/ROOM01/songs", json={"title": "Fix You", "artist": "Coldplay", "me": "Ben"})
    assert response.status_code == 403


def test_rooms_down_writes_fail_with_503_and_reads_degrade(client, rooms_stub):
    client.post("/rooms/ROOM01/songs", json={"title": "Yellow", "artist": "Coldplay", "me": "Ana"})
    assert client.get("/rooms/ROOM01/playlist?me=Ana").get_json()["rooms_available"] is True

    rooms_stub.delay_s = 2
    started = time.perf_counter()
    write = client.post("/rooms/ROOM01/songs", json={"title": "Fix You", "artist": "Coldplay", "me": "Ana"})
    assert write.status_code == 503
    assert "Rooms are not available" in write.get_json()["error"]
    read = client.get("/rooms/ROOM01/playlist?me=Ana")
    assert time.perf_counter() - started < 3
    assert read.status_code == 200
    assert read.get_json()["rooms_available"] is False
    assert [s["title"] for s in read.get_json()["songs"]] == ["Yellow"]


def test_rooms_down_and_room_never_seen_is_503(client, rooms_stub):
    rooms_stub.status = 503
    response = client.get("/rooms/ROOM01/playlist")
    assert response.status_code == 503
