from pathlib import Path

from flask import Flask, abort, jsonify

import db
import service
import web
from config import load_config
from service import RoomError

MIGRATIONS = Path(__file__).parent / "migrations"


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

    @app.errorhandler(RoomError)
    def room_error(err):
        return jsonify(error=str(err)), 400

    @app.post("/rooms")
    def create():
        data = web.body()
        code = service.create_room(db.get_db(), data.get("room_name"), data.get("your_name"))
        return jsonify(room_json(code)), 201

    @app.post("/rooms/<code>/members")
    def join(code):
        code = service.join_room(db.get_db(), code, web.body().get("your_name"))
        return jsonify(room_json(code)), 201

    @app.get("/rooms/<code>")
    def show(code):
        return jsonify(room_json(code))

    def room_json(code):
        conn = db.get_db()
        room = service.get_room(conn, code)
        if room is None:
            abort(404, "We couldn't find a room with that code.")
        return {
            "id": room["id"],
            "code": room["code"],
            "name": room["name"],
            "members": service.list_members(conn, room["id"]),
        }

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=app.config["PORT"])
