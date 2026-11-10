import logging

import web


def create(client, room_name="Road trip", your_name="Ana"):
    return client.post("/rooms", json={"room_name": room_name, "your_name": your_name})


def test_create_room(client):
    response = create(client)
    assert response.status_code == 201
    room = response.get_json()
    assert room["name"] == "Road trip"
    assert room["members"] == [{"name": "Ana", "is_host": True}]


def test_create_room_with_bad_name(client):
    response = create(client, your_name=" ")
    assert response.status_code == 400
    assert response.get_json() == {"error": "Please enter a name."}


def test_join_and_show_room(client):
    code = create(client).get_json()["code"]
    assert client.post(f"/rooms/{code}/members", json={"your_name": "Ben"}).status_code == 201
    room = client.get(f"/rooms/{code}").get_json()
    assert [m["name"] for m in room["members"]] == ["Ana", "Ben"]


def test_join_with_taken_name(client):
    code = create(client).get_json()["code"]
    response = client.post(f"/rooms/{code}/members", json={"your_name": "Ana"})
    assert response.status_code == 400


def test_unknown_room_is_404_json(client):
    response = client.get("/rooms/ZZZZZZ")
    assert response.status_code == 404
    assert "couldn't find" in response.get_json()["error"]


def test_health_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok", "db": "ok", "version": "test-sha"}


def test_health_503_when_database_is_down(client, monkeypatch):
    monkeypatch.setattr(web, "HEALTH_RETRY_DELAYS", ())
    client.application.config["DATABASE_URL"] = "mssql://nobody:wrong@127.0.0.1:1/none"
    response = client.get("/health")
    assert response.status_code == 503
    assert response.get_json()["db"] == "error"


def test_every_request_is_logged(client, caplog):
    with caplog.at_level(logging.INFO, logger="requests"):
        client.get("/rooms/ZZZZZZ")
    assert any(r.getMessage().startswith("GET /rooms/ZZZZZZ 404 ") and r.getMessage().endswith("ms") for r in caplog.records)


def test_cors_only_for_ui_origin(client):
    allowed = client.get("/health", headers={"Origin": "http://localhost:8080"})
    other = client.get("/health", headers={"Origin": "https://evil.example"})
    assert allowed.headers["Access-Control-Allow-Origin"] == "http://localhost:8080"
    assert "Access-Control-Allow-Origin" not in other.headers


def test_preflight_allows_json_posts(client):
    response = client.options("/rooms", headers={"Origin": "http://localhost:8080", "Access-Control-Request-Method": "POST"})
    assert response.status_code == 200
    assert "Content-Type" in response.headers["Access-Control-Allow-Headers"]
