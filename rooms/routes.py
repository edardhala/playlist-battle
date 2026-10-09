from flask import Blueprint, abort, redirect, render_template, request, url_for

from battle import service as battle_service
from db import get_db
from rooms import service
from rooms.service import RoomError

bp = Blueprint("rooms", __name__)


@bp.post("/rooms")
def create():
    try:
        code = service.create_room(get_db(), request.form["room_name"], request.form["your_name"])
    except RoomError as err:
        return render_template("index.html", error=str(err)), 400
    return redirect(url_for("rooms.show", code=code, me=request.form["your_name"].strip()))


@bp.post("/rooms/join")
def join():
    try:
        code = service.join_room(get_db(), request.form["code"], request.form["your_name"])
    except RoomError as err:
        return render_template("index.html", error=str(err)), 400
    return redirect(url_for("rooms.show", code=code, me=request.form["your_name"].strip()))


@bp.get("/rooms/<code>")
def show(code):
    conn = get_db()
    room = service.get_room(conn, code)
    if room is None:
        abort(404)
    members = service.list_members(conn, room["id"])
    songs = battle_service.ranked_songs(conn, room["id"])
    return render_template(
        "room.html",
        room=room,
        members=members,
        songs=songs,
        me=request.args.get("me"),
        error=request.args.get("error"),
    )
