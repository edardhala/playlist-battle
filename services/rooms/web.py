import logging
import sys
import time

from flask import g, jsonify, request
from werkzeug.exceptions import HTTPException

import db

log = logging.getLogger("requests")

HEALTH_RETRY_DELAYS = (1, 2)


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        stream=sys.stdout,
    )


def setup(app):
    app.teardown_appcontext(db.close_db)

    @app.before_request
    def start_timer():
        g.started = time.perf_counter()

    @app.after_request
    def log_and_allow_ui(response):
        duration_ms = (time.perf_counter() - g.get("started", time.perf_counter())) * 1000
        log.info("%s %s %s %.1fms", request.method, request.path, response.status_code, duration_ms)
        origin = request.headers.get("Origin")
        if origin and origin == app.config["CORS_ORIGIN"]:
            response.headers["Access-Control-Allow-Origin"] = origin
            response.headers["Access-Control-Allow-Methods"] = "GET, POST, DELETE, OPTIONS"
            response.headers["Access-Control-Allow-Headers"] = "Content-Type"
            response.headers["Vary"] = "Origin"
        return response

    @app.errorhandler(HTTPException)
    def http_error(err):
        return jsonify(error=err.description), err.code

    @app.get("/health")
    def health():
        version = app.config["VERSION"]
        try:
            conn = db.connect(app.config["DATABASE_URL"], HEALTH_RETRY_DELAYS)
            try:
                db.check(conn)
            finally:
                conn.close()
        except Exception as err:
            log.warning("health check failed: %s", err)
            return jsonify(status="error", db="error", version=version), 503
        return jsonify(status="ok", db="ok", version=version)


def body():
    return request.get_json(silent=True) or {}
