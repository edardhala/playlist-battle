"""Entry point: `python app.py` starts the whole app as one process."""
from flask import Flask, jsonify, render_template

from config import load_config


def create_app(env=None):
    config = load_config(env)
    # Make sure the SQLite folder exists, so startup needs no manual setup.
    config["DATA_DIR"].mkdir(parents=True, exist_ok=True)

    app = Flask(__name__)
    app.config.update(config)

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/health")
    def health():
        return jsonify(status="ok")

    return app


if __name__ == "__main__":
    app = create_app()
    # 0.0.0.0 so the app is reachable from outside a container later.
    app.run(host="0.0.0.0", port=app.config["PORT"])
