from pathlib import Path

from flask import Flask, abort, jsonify, request

import db
import service
import web
from config import load_config
from rooms_client import RoomsClient, RoomsUnavailable
from service import BattleError

MIGRATIONS = Path(__file__).parent / "migrations"

ROOMS_DOWN = "Rooms are not available right now. Try again in a moment."


def create_app(env=None):
    config = load_config(env)
    web.setup_logging()
    conn = db.connect(config["DATABASE_URL"], config["DB_RETRY_DELAYS"])
    try:
        db.migrate(conn, MIGRATIONS)
    finally:
        conn.close()

    app = Flask(__name__)
    app.config.update(config)
    web.setup(app)
    rooms = RoomsClient(config["ROOMS_URL"], config["ROOMS_TIMEOUT_S"])

    @app.errorhandler(BattleError)
    def battle_error(err):
        return jsonify(error=str(err)), 400

    @app.errorhandler(RoomsUnavailable)
    def rooms_unavailable(err):
        return jsonify(error=ROOMS_DOWN), 503

    def member_room_id(code, me, host=False):
        room = rooms.get_room(code)
        if room is None:
            abort(404, "We couldn't find a room with that code.")
        member = next((m for m in room["members"] if m["name"] == me), None)
        if member is None:
            abort(403, "Join this room to add songs and vote.")
        if host and not member["is_host"]:
            abort(403, "Only the host can play the next song.")
        return room["id"]

    @app.get("/rooms/<code>/playlist")
    def playlist(code):
        room_id, rooms_available = rooms.room_id_for_reading(code)
        if room_id is None:
            abort(404, "We couldn't find a room with that code.")
        conn = db.get_db()
        me = request.args.get("me")
        my_votes = service.songs_voted_by(conn, room_id, me) if me else set()
        songs = [
            {**song_json(song), "votes": song["votes"], "voted_by_me": song["id"] in my_votes}
            for song in service.ranked_songs(conn, room_id)
        ]
        played = [
            {**song_json(song), "played_at": song["played_at"].isoformat() + "Z"}
            for song in service.played_songs(conn, room_id)
        ]
        return jsonify(songs=songs, played=played, rooms_available=rooms_available)

    @app.post("/rooms/<code>/songs")
    def add(code):
        data = web.body()
        me = data.get("me")
        room_id = member_room_id(code, me)
        song_id = service.add_song(db.get_db(), room_id, data.get("title"), data.get("artist"), me)
        return jsonify(id=song_id), 201

    @app.post("/rooms/<code>/songs/<int:song_id>/vote")
    def vote(code, song_id):
        me = web.body().get("me")
        service.vote(db.get_db(), member_room_id(code, me), song_id, me)
        return "", 204

    @app.delete("/rooms/<code>/songs/<int:song_id>/vote")
    def unvote(code, song_id):
        me = request.args.get("me")
        service.remove_vote(db.get_db(), member_room_id(code, me), song_id, me)
        return "", 204

    @app.post("/rooms/<code>/play")
    def play(code):
        room_id = member_room_id(code, web.body().get("me"), host=True)
        return jsonify(id=service.play_next(db.get_db(), room_id))

    return app


def song_json(song):
    return {
        "id": song["id"],
        "title": song["title"],
        "artist": song["artist"],
        "added_by": song["added_by"],
        "added_at": song["added_at"].isoformat() + "Z",
    }


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=app.config["PORT"])
