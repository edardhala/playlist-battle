import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    return create_app({"DATA_DIR": str(tmp_path)}).test_client()


def test_create_room_then_friend_joins(client):
    response = client.post("/rooms", data={"room_name": "Road trip", "your_name": "Ana"})
    assert response.status_code == 302
    code = response.headers["Location"].split("/")[-1].split("?")[0]

    client.post("/rooms/join", data={"code": code, "your_name": "Ben"})
    page = client.get(f"/rooms/{code}").get_data(as_text=True)
    assert "Road trip" in page and "Ana" in page and "Ben" in page


def test_error_is_shown_on_home_page(client):
    response = client.post("/rooms/join", data={"code": "ZZZZZZ", "your_name": "Ben"})
    assert response.status_code == 400
    assert "find a room with that code" in response.get_data(as_text=True)


def test_unknown_room_is_404(client):
    assert client.get("/rooms/ZZZZZZ").status_code == 404


def test_share_link_fills_in_the_code(client):
    response = client.post("/rooms", data={"room_name": "Road trip", "your_name": "Ana"})
    code = response.headers["Location"].split("/")[-1].split("?")[0]
    room_page = client.get(f"/rooms/{code}").get_data(as_text=True)
    assert f"/?code={code}" in room_page

    home_page = client.get(f"/?code={code}").get_data(as_text=True)
    assert f'value="{code}"' in home_page


def test_version_changes_when_the_room_changes(client):
    response = client.post("/rooms", data={"room_name": "Road trip", "your_name": "Ana"})
    code = response.headers["Location"].split("/")[-1].split("?")[0]

    def version():
        return client.get(f"/rooms/{code}/version").get_json()["version"]

    start = version()
    assert version() == start

    client.post("/rooms/join", data={"code": code, "your_name": "Ben"})
    after_join = version()
    assert after_join != start

    client.post(f"/rooms/{code}/songs", data={"title": "Yellow", "artist": "Coldplay", "me": "Ana"})
    after_song = version()
    assert after_song != after_join

    client.post(f"/rooms/{code}/songs/1/vote", data={"me": "Ben"})
    assert version() != after_song


def test_room_page_has_live_updates(client):
    response = client.post("/rooms", data={"room_name": "Road trip", "your_name": "Ana"})
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "data-version-url" in page and "live.js" in page


def test_version_of_unknown_room_is_404(client):
    assert client.get("/rooms/ZZZZZZ/version").status_code == 404
