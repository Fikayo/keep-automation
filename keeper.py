import json
from datetime import datetime
from os import path
from typing import List

import gkeepapi
import keyring


KEEP_NOTES_STATE = path.join(path.dirname(__file__), './keep_state.json')


def log(str):
    print(str)


class Keeper(object):
    def __init__(self):
        self._keep = gkeepapi.Keep()
        self._token = None
        self._state = None

    @property
    def keep(self) -> gkeepapi.Keep:
        return self._keep

    def login(self, email, password):
        if not self.restore_session(email): 
            log("creating new keep session")        
            self._keep.login(email, password, self._state)
            token = self._keep.getMasterToken()
            keyring.set_password('google-keep-token', email, token)

    def restore_session(self, email):
        token = keyring.get_password('google-keep-token', email)
        if token is None:
            return False

        log("restoring keep session")
        try:
            self._keep.resume(email, token, self._state)
            return True
        except Exception as e:
            log(f"failed to restore session: {e}")
            return False

    def load_state(self):
        if not path.exists(KEEP_NOTES_STATE):
            return

        with open(KEEP_NOTES_STATE, 'r') as fh:
            self._state = json.load(fh)
        self._keep.restore(self._state)

    def store_state(self):
        self._state = self._keep.dump()
        with open(KEEP_NOTES_STATE, 'w') as fh:
            json.dump(self._state, fh)

    def filter(self, func: callable) -> List[gkeepapi._node.TopLevelNode]:
        notes = []
        for n in self._keep.find(func=func):
            notes.append(n)
        return notes

    def find_note(self, id) -> gkeepapi._node.TopLevelNode:
        return self._keep.get(id)

