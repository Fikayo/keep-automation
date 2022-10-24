from typing import List
import gkeepapi
import keyring
import json
import yaml
import csv
import pytz
import sys

from arghelper import parse_args
from dateutil import parser
from os import path
from datetime import datetime

utc=pytz.UTC

LAST_RUN = datetime.now()
TIME_ZERO = utc.localize(parser.parse("2022-10-22"))
KEEP_NOTES_STATE = path.join(path.dirname(__file__), './keep_state.json')
CONFIG = path.join(path.dirname(__file__), './config.yml')

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


def filterNote(note: gkeepapi._node.TopLevelNode):
    _1hour = 60 * 60

    # example created time "2022-10-02T10:19:50.742000Z"
    created = note.timestamps.created
    elapsed = (created - LAST_RUN).total_seconds()
    if TIME_ZERO < created or note.archived or elapsed > _1hour:
        return False
        
    return True


def fetch_vars() -> dict():
    vars_path = path.join(path.dirname(__file__), './vars.yml')
    if not path.exists(vars_path):
        raise Exception(f"Cannot find vars file {vars_path}")

    with open(vars_path, 'r') as file:
        vars = yaml.safe_load(file)
    return vars


def fetch_config() -> dict():
    conf = dict() 
    if path.exists(CONFIG):
        with open(CONFIG, 'r') as file:
            conf = yaml.safe_load(file)

    if conf is None:
        return dict()
    return conf


def store_config(conf) -> None:
    with open(CONFIG, 'w') as file:
        yaml.safe_dump(conf, file)


def dump_notes(vars: dict(), notes: List[gkeepapi._node.TopLevelNode], timestamp=False) -> None:
    notesJson = list()
    for n in notes:
        obj = n.save()
        obj["text"] = n.text
        notesJson.append(obj)

    # Write to json
    jsonpath = vars['keep_notes_json']
    if timestamp:
        jsonpath = path.join(path.dirname(jsonpath), f"{path.basename(jsonpath)}-{datetime.now()}.json")

    with open(jsonpath, 'w') as file:
        json.dump(notesJson, file)

    # Write to csv
    csvpath = vars['keep_notes_csv']
    if timestamp:
        csvpath = path.join(path.dirname(csvpath), f"{path.basename(csvpath)}-{datetime.now()}.csv")

    with open(csvpath, 'w',  newline='') as file:
        # See https://realpython.com/python-csv/#writing-csv-files-with-csv for details
        csv_writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(["id", "title", "labels", "text"])
        
        for n in notes:
            labels = list()
            l: gkeepapi._node.Label
            for l in n.labels.all():
                labels.append(l.name)
            csv_writer.writerow([n.id, n.title, ", ".join(labels), repr(n.text)])
    
    print(f"Keep Notes stored in:\n{jsonpath}\n{csvpath}")
    return jsonpath, csvpath


def main(args):
    global LAST_RUN
    conf = fetch_config()

    LAST_RUN = datetime.now()
    if conf is not None and "last_run" in conf and conf["last_run"] != "":
        LAST_RUN = conf["last_run"]
    conf["last_run"] = LAST_RUN

    vars = fetch_vars()
    email = vars["email"]
    password = vars["password"]

    k = Keeper()
    k.login(email, password)
    k.load_state()
    log("Keepmation login succesful")

    # Filter notes for notion.
    if not args.get("note_id"):
        notes = k.filter(filterNote)
        dump_notes(vars, notes, args.get("preserve_history"))
    else:
        note = k.find_note(args.get("note_id"))
        dump_notes(vars, [note], args.get("preserve_history"))

        # Reset and sync note
        if args.get("reset_note"):
            note.text = ''
            k.keep.sync()

    log("Keepmation completed - caching keep state")
    k.store_state()
    store_config(conf)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    main(args)

