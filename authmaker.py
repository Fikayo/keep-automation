
import sys
import gkeepapi
import yaml
import keyring
from getpass import getpass
from arghelper import parse_auth_args
from globals import AUTH_PATH, TOKEN_PATH

AUTH_SERVICE = 'keepmation_authmaker'

def save_config(conf, path) -> None:
    with open(path, 'w') as file:
        yaml.safe_dump(conf, file)
    

def get_credentials():
    print("Enter Google Credentials. Password will be hidden")
    email = input("email: ")
    password = getpass("password: ")
    return email, password


if __name__ == "__main__":
    args = parse_auth_args(sys.argv[1:])
    no_key = args.get("no_key")
    if no_key:
        print("Running authmaker without a keyring.")

    email, password = get_credentials()

    # Save email
    auth = dict()
    auth["email"] = email
    save_config(auth, AUTH_PATH)

    # Save password/token.
    if no_key:
        keep = gkeepapi.Keep()
        keep.login(email, password)
        token = keep.getMasterToken()

        var = dict()
        var[email] = token
        with open(TOKEN_PATH, 'w') as file:
            yaml.safe_dump(var, file)
    else:
        keyring.set_password(AUTH_SERVICE, email, password)
