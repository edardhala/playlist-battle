import hashlib

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for

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
    room = find_room(code)
    members = service.list_members(conn, room["id"])
    songs = battle_service.ranked_songs(conn, room["id"])
    me = request.args.get("me")
    my_votes = battle_service.songs_voted_by(conn, me) if me else set()
    played = battle_service.played_songs(conn, room["id"])
    return render_template(
        "room.html",
        room=room,
        members=members,
        songs=songs,
        me=me,
        my_votes=my_votes,
        played=played,
        i_am_host=bool(me) and service.is_host(conn, room["id"], me),
        error=request.args.get("error"),
        version=room_version(room),
    )


@bp.get("/rooms/<code>/version")
def version(code):
    return jsonify(version=room_version(find_room(code)))


def find_room(code):
    room = service.get_room(get_db(), code)
    if room is None:
        abort(404)
    return room


def room_version(room):
    conn = get_db()
    members = [m["id"] for m in service.list_members(conn, room["id"])]
    songs = [(s["id"], s["votes"]) for s in battle_service.list_songs(conn, room["id"])]
    played = [p["id"] for p in battle_service.played_songs(conn, room["id"])]
    return hashlib.sha1(repr((members, songs, played)).encode()).hexdigest()[:12]
