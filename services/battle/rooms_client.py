import logging
import time
from urllib.parse import quote

import requests

log = logging.getLogger(__name__)


def elapsed_ms(started):
    return (time.perf_counter() - started) * 1000


class RoomsUnavailable(Exception):
    pass


class RoomsClient:
    def __init__(self, base_url, timeout_s):
        self.base_url = base_url.rstrip("/")
        self.timeout_s = timeout_s
        self.room_ids = {}

    def get_room(self, code):
        path = f"/rooms/{quote(code.strip().upper())}"
        started = time.perf_counter()
        try:
            response = requests.get(self.base_url + path, timeout=self.timeout_s)
        except requests.RequestException as err:
            log.warning("call rooms GET %s failed after %.1fms: %s", path, elapsed_ms(started), err)
            raise RoomsUnavailable() from err
        log.info("call rooms GET %s %s %.1fms", path, response.status_code, elapsed_ms(started))
        if response.status_code == 404:
            return None
        if response.status_code != 200:
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
