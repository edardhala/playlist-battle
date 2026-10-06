import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    return create_app({"DATA_DIR": str(tmp_path)}).test_client()


def test_create_room_then_friend_joins(client):
    response = client.post("/rooms", data={"room_name": "Road trip", "your_name": "Ana"})
    assert response.status_code == 302
    code = response.headers["Location"].split("/")[-1]

    client.post("/rooms/join", data={"code": code, "your_name": "Ben"})
    page = client.get(f"/rooms/{code}").get_data(as_text=True)
    assert "Road trip" in page and "Ana" in page and "Ben" in page


def test_error_is_shown_on_home_page(client):
    response = client.post("/rooms/join", data={"code": "ZZZZZZ", "your_name": "Ben"})
    assert response.status_code == 400
    assert "No room with that code" in response.get_data(as_text=True)


def test_unknown_room_is_404(client):
    assert client.get("/rooms/ZZZZZZ").status_code == 404
