import gkeepapi
import keyring
import json
import yaml
import csv
from os import path
from datetime import datetime

KEEP_NOTES_STATE = path.join(path.dirname(__file__), './keep_state.json')

def log(str):
    print(str)

class Keeper(object):
    def __init__(self):
        self._keep = gkeepapi.Keep()
        self._token = None
        self._state = None

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
        self._keep.resume(email, token, self._state)
        return True

    def load_state(self):
        with open(KEEP_NOTES_STATE, 'r') as fh:
            self._state = json.load(fh)
        self._keep.restore(self._state)

    def store_state(self):
        self._state = self._keep.dump()
        with open(KEEP_NOTES_STATE, 'w') as fh:
            json.dump(self._state, fh)

    def filter(self, func: callable):
        self._keep.find(func=func)


def filterNote(note):
    _1minute = 60
    _1hour = _1minute * 60
    _1day = _1hour * 24

    # example created time "2022-10-02T00:19:50.742000Z"
    format = "%Y-%m-%dT%H%M%S"
    created = datetime.strptime(note.timestamps.created, format)
    now = datetime.now()

    diff = now - created
    return diff.total_seconds() > _1hour


def main():
    with open(path.join(path.dirname(__file__), './vars.yml'), 'r') as file:
        vars = yaml.safe_load(file)

    k = Keeper()
    k.login(vars['email'], vars['password'])
    log("Keepmation login succesful - loading keep state")
    k.load_state()

    # Filter notes created in the past 1 hour
    # k.filter(filterNote)
    notesGenerator = k._keep.find(labels=[k._keep.findLabel('Church')])


    # Store notes in file for notion
    notes = list()
    notesJson = list()
    n: gkeepapi._node.TopLevelNode
    for n in notesGenerator:
        notes.append(n)
        noteObj = n.save()
        noteObj["text"] = n.text
        notesJson.append(noteObj)

    # Write to json
    with open(vars['keep_notes_json'], 'w') as file:
        json.dump(notesJson, file)

    # Write to csv
    with open(vars['keep_notes_csv'], 'w',  newline='') as file:
        # See https://realpython.com/python-csv/#writing-csv-files-with-csv for details
        csv_writer = csv.writer(file, delimiter=',', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        csv_writer.writerow(["id", "title", "created", "labels", "text"])
        
        n: gkeepapi._node.TopLevelNode
        for n in notes:
            labels = list()
            l: gkeepapi._node.Label
            for l in n.labels.all():
                labels.append(l.name)
            csv_writer.writerow([n.id, n.title, n.timestamps.created, ", ".join(labels), repr(n.text)])

    log("Keepmation completed - caching keep state")
    k.store_state()

    print(f"Keep Notes stored in {vars['keep_notes_csv']}")


if __name__ == "__main__":
    main()