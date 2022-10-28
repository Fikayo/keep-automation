import json
import yaml
from os import path
from typing import List

import gkeepapi
import keyring

from authmaker import get_credentials
from globals import TOKEN_PATH

KEEP_NOTES_STATE = path.join(path.dirname(__file__), './keep_state.json')


def log(str):
    print(str)


class Keeper(object):
    def __init__(self, use_keyring=True):
        self._keep = gkeepapi.Keep()
        self._token = None
        self._state = None
        self._use_keyring = use_keyring

    @property
    def keep(self) -> gkeepapi.Keep:
        return self._keep

    def login(self, email, password):
        if not self.restore_session(email): 
            # If no keyring, ask user for credentials as none could be found
            if not self._use_keyring:
                print("Please provide your google credentials keyring is not available")
                email, password = get_credentials()
            
            log("creating new keep session")        
            self._keep.login(email, password, self._state)
            token = self._keep.getMasterToken()
            self.store_token(email, token)

    def restore_session(self, email):
        token = self.get_token(email)
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

    def store_token(self, email, token):
        if self._use_keyring:
            keyring.set_password('google-keep-token', email, token)
        else:
            var = dict()
            var[email] = token
            with open(TOKEN_PATH, 'w') as file:
                yaml.safe_dump(var, file)

    def get_token(self, email):
        if self._use_keyring:
            return keyring.get_password('google-keep-token', email)
        else:
            if path.exists(TOKEN_PATH):
                with open(TOKEN_PATH, 'r') as file:
                    var = yaml.safe_load(file)

            if var is None:
                return None
            return var[email]

