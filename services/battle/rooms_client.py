import logging
from urllib.parse import quote

import requests

log = logging.getLogger(__name__)


class RoomsUnavailable(Exception):
    pass


class RoomsClient:
    def __init__(self, base_url, timeout_s):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.room_ids = {}

    def get_room(self, code):
        url = f"{self.base_url}/rooms/{quote(code.strip().upper())}"
        try:
            response = requests.get(url, timeout=self.timeout_s)
        except requests.RequestException as err:
            log.warning("rooms service unreachable: %s", err)
            raise RoomsUnavailable() from err
        if response.status_code == 404:
            return None
        if response.status_code != 200:
            log.warning("rooms service answered %s", response.status_code)
            raise RoomsUnavailable()
        room = response.json()
        self.room_ids[room["code"]] = room["id"]
        return room

    def room_id_for_reading(self, code):
        try:
            room = self.get_room(code)
        except RoomsUnavailable:
            cached = self.room_ids.get(code.strip().upper())
            if cached is None:
                raise
            return cached, False
        return (room["id"] if room else None), True
