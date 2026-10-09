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
    me = request.args.get("me")
    my_votes = battle_service.songs_voted_by(conn, me) if me else set()
    return render_template(
        "room.html",
        room=room,
        members=members,
        songs=songs,
        me=me,
        my_votes=my_votes,
        error=request.args.get("error"),
    )
