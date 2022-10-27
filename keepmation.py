from typing import List
import gkeepapi
import json
import yaml
import csv
import sys

from keeper import Keeper, log
from arghelper import parse_args
from os import path
from datetime import datetime
from globals import AUTH_PATH, CONFIG_PATH, SECRET_PATH, VARS_PATH
from authmaker import decrypt


LAST_RUN = datetime.now()
TIME_ZERO = datetime.strptime("2022-10-22", "%Y-%m-%d")


def fetch_cipher_key(path):
    with open(path, "rb") as file:
        return file.read()


def fetch_vars() -> dict():
    vars_path = VARS_PATH
    if not path.exists(vars_path):
        raise Exception(f"Cannot find vars file {vars_path}")

    with open(vars_path, 'r') as file:
        vars = yaml.safe_load(file)
    return vars

def fetch_auth() -> dict():
    auth_path = AUTH_PATH
    if not path.exists(auth_path):
        raise Exception(f"Cannot find auth file {auth_path}; run `python3 authmaker` to generate auth files")

    with open(auth_path, 'r') as file:
        vars = yaml.safe_load(file)
    return vars


def fetch_config() -> dict():
    conf = dict() 
    if path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, 'r') as file:
            conf = yaml.safe_load(file)

    if conf is None:
        return dict()
    return conf


def save_config(conf) -> None:
    with open(CONFIG_PATH, 'w') as file:
        yaml.safe_dump(conf, file)


def dump_notes(vars: dict(), notes: List[gkeepapi._node.TopLevelNode], timestamp=False) -> None:
    notesJson = list()
    for n in notes:
        obj = n.save()
        obj["text"] = n.text
        notesJson.append(obj)

    # Write to json
    jsonpath = vars['keep_notes_json']
    dump_json(jsonpath, notesJson)
    if timestamp:
        name, ext = path.splitext(path.basename(jsonpath))
        jsonpath = path.join(path.dirname(jsonpath), f"{name}-{datetime.now()}.{ext}")
        dump_json(jsonpath, notesJson)

    # Write to csv
    csvpath = vars['keep_notes_csv']
    dump_csv(csvpath, notes)
    if timestamp:
        name, ext = path.splitext(path.basename(csvpath))
        csvpath = path.join(path.dirname(csvpath), f"{name}-{datetime.now()}.{ext}")
        dump_csv(csvpath, notes)
    
    print(f"Keep Notes stored in:\n{jsonpath}\n{csvpath}")
    return jsonpath, csvpath


def dump_json(jsonpath, notesJson):
    with open(jsonpath, 'w') as file:
        json.dump(notesJson, file)

def dump_csv(csvpath, notes):
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


def filterNote(note: gkeepapi._node.TopLevelNode):
    _1hour = 60 * 60

    # example created time "2022-10-02T10:19:50.742000Z"
    created = note.timestamps.created
    elapsed = (created - LAST_RUN).total_seconds()
    if TIME_ZERO > created or note.archived or elapsed > _1hour:
        return False
        
    return True


def main(args):
    global LAST_RUN
    conf = fetch_config()

    LAST_RUN = datetime.now()
    if conf is not None and "last_run" in conf and conf["last_run"] != "":
        LAST_RUN = conf["last_run"]
    conf["last_run"] = LAST_RUN

    auth = fetch_auth()
    ci_key = fetch_cipher_key(SECRET_PATH)
    email = decrypt(ci_key, auth["email"])
    password = decrypt(ci_key, auth["password"])

    k = Keeper()
    k.login(email, password)
    k.load_state()
    log("Keepmation login succesful")

    # Filter notes for notion.
    vars = fetch_vars()
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
    save_config(conf)


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    main(args)

