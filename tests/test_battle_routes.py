import pytest

from app import create_app


@pytest.fixture
def client(tmp_path):
    return create_app({"DATA_DIR": str(tmp_path)}).test_client()


@pytest.fixture
def code(client):
    response = client.post("/rooms", data={"room_name": "Road trip", "your_name": "Ana"})
    return response.headers["Location"].split("/")[-1].split("?")[0]


def test_add_song_and_vote(client, code):
    client.post(f"/rooms/{code}/songs", data={"title": "Yellow", "artist": "Coldplay", "me": "Ana"})
    client.post(f"/rooms/{code}/songs/1/vote", data={"me": "Ana"})
    page = client.get(f"/rooms/{code}?me=Ana").get_data(as_text=True)
    assert "Yellow" in page and "Coldplay" in page
    assert "1 vote," in page


def test_bad_song_shows_error(client, code):
    response = client.post(f"/rooms/{code}/songs", data={"title": "", "artist": "Coldplay", "me": "Ana"})
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Please enter the title." in page


def test_voting_twice_shows_error(client, code):
    client.post(f"/rooms/{code}/songs", data={"title": "Yellow", "artist": "Coldplay", "me": "Ana"})
    client.post(f"/rooms/{code}/songs/1/vote", data={"me": "Ana"})
    response = client.post(f"/rooms/{code}/songs/1/vote", data={"me": "Ana"})
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "You already voted for this song." in page


def test_songs_in_unknown_room_is_404(client):
    response = client.post("/rooms/ZZZZZZ/songs", data={"title": "A", "artist": "B", "me": "Ana"})
    assert response.status_code == 404


def test_remove_vote_button(client, code):
    client.post(f"/rooms/{code}/songs", data={"title": "Yellow", "artist": "Coldplay", "me": "Ana"})
    client.post(f"/rooms/{code}/songs/1/vote", data={"me": "Ana"})
    assert "Remove vote" in client.get(f"/rooms/{code}?me=Ana").get_data(as_text=True)

    client.post(f"/rooms/{code}/songs/1/unvote", data={"me": "Ana"})
    page = client.get(f"/rooms/{code}?me=Ana").get_data(as_text=True)
    assert "0 votes," in page
    assert "Remove vote" not in page


def test_host_plays_the_winner(client, code):
    client.post(f"/rooms/{code}/songs", data={"title": "Yellow", "artist": "Coldplay", "me": "Ana"})
    page = client.get(f"/rooms/{code}?me=Ana").get_data(as_text=True)
    assert "Play the winner" in page
    assert "youtube.com/results?search_query=Yellow%20Coldplay" in page

    client.post(f"/rooms/{code}/play", data={"me": "Ana"})
    page = client.get(f"/rooms/{code}?me=Ana").get_data(as_text=True)
    assert "Now playing" in page and "Yellow" in page


def test_only_host_can_play(client, code):
    client.post("/rooms/join", data={"code": code, "your_name": "Ben"})
    client.post(f"/rooms/{code}/songs", data={"title": "Yellow", "artist": "Coldplay", "me": "Ben"})
    assert "Play the winner" not in client.get(f"/rooms/{code}?me=Ben").get_data(as_text=True)

    response = client.post(f"/rooms/{code}/play", data={"me": "Ben"})
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "Only the host can play the next song." in page
    assert "Now playing" not in page


def test_play_with_empty_playlist_shows_error(client, code):
    response = client.post(f"/rooms/{code}/play", data={"me": "Ana"})
    page = client.get(response.headers["Location"]).get_data(as_text=True)
    assert "There are no songs left to play." in page
