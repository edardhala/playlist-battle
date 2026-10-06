from flask import Flask, jsonify, render_template

import db
from config import load_config
from rooms import service as rooms_service
from rooms.routes import bp as rooms_bp


def create_app(env=None):
    config = load_config(env)
    config["DATA_DIR"].mkdir(parents=True, exist_ok=True)
    db.init_db(config["DATABASE"], rooms_service.SCHEMA)

    app = Flask(__name__)
    app.config.update(config)
    app.teardown_appcontext(db.close_db)
    app.register_blueprint(rooms_bp)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=app.config["PORT"])
