
import yaml
import keyring
from getpass import getpass
from globals import AUTH_PATH

AUTH_SERVICE = 'keepmation_authmaker'

def save_config(conf, path) -> None:
    with open(path, 'w') as file:
        yaml.safe_dump(conf, file)
    

if __name__ == "__main__":
    print("Enter Google Credentials. Password will be hidden")
    email = input("email: ")
    password = getpass("password: ")

    keyring.set_password(AUTH_SERVICE, email, password)

    auth = dict()
    auth["email"] = email
    save_config(auth, AUTH_PATH)
