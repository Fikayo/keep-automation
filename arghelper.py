import sys, getopt

class ArgsHelper(object):
    def __init__(self, args):
        self._args = args

    def get(self, key):
        if key not in self._args:
            return None
        return self._args[key]


def print_help():
    print('keepmation.py -n <note_id> -r -p')
    print("-n --note-id=            specifies a specific note ID from keep to be dumped locally.")
    print("-r --reset               resets the note after it's been dumped locally. Only works if -n is specified.")
    print("-p --preserve-history    appends a timestamp to the notes dump file to preserve the history of the notes.")
    print("--no-key                 opts for not using 'keyring' to store google password (useful if keyring is incompatible with system). You must provide your google credentials during first run.")


def parse_args(sysargs):
    try:
        opts, _ = getopt.getopt(sysargs,"hn:rp",["help", "note-id=", "reset", "preserve-history", "no-key"])
    except getopt.GetoptError:
        print_help()
        sys.exit(2)

    argsObj = dict()
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            print_help()
            sys.exit()
        elif opt in ("-n", "--note-id"):
            argsObj["note_id"] = arg
        elif opt in ("-r", "--reset"):
            argsObj["reset_note"] = True
        elif opt in ("-p", "--preserve-history"):
            argsObj["preserve_history"] = True
        elif opt in ("--no-key"):
            argsObj["no_key"] = True

    return ArgsHelper(argsObj)


def parse_auth_args(sysargs):
    try:
        opts, _ = getopt.getopt(sysargs,"",["no-key"])
    except getopt.GetoptError:
        print("authmaker [no-key]")
        sys.exit(2)

    argsObj = dict()
    for opt, _ in opts:
        if opt in ("-h", "--help"):
            print("authmaker [no-key]")
            sys.exit()
        elif opt in ("--no-key"):
            argsObj["no_key"] = True

    return ArgsHelper(argsObj)