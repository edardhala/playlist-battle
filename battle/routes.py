from flask import Blueprint, abort, redirect, request, url_for

from battle import service
from battle.service import BattleError
from db import get_db
from rooms import service as rooms_service

bp = Blueprint("battle", __name__)


def find_room_id(code):
    room = rooms_service.get_room(get_db(), code)
    if room is None:
        abort(404)
    return room["id"]


@bp.post("/rooms/<code>/songs")
def add(code):
    me = request.form["me"]
    try:
        service.add_song(get_db(), find_room_id(code), request.form["title"], request.form["artist"], me)
    except BattleError as err:
        return redirect(url_for("rooms.show", code=code, me=me, error=str(err)))
    return redirect(url_for("rooms.show", code=code, me=me))


@bp.post("/rooms/<code>/songs/<int:song_id>/vote")
def vote(code, song_id):
    me = request.form["me"]
    find_room_id(code)
    try:
        service.vote(get_db(), song_id, me)
    except BattleError as err:
        return redirect(url_for("rooms.show", code=code, me=me, error=str(err)))
    return redirect(url_for("rooms.show", code=code, me=me))
