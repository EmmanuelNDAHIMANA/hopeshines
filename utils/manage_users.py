"""
Command-line helper to add/update users in config/users.yaml with a
properly bcrypt-hashed password. Run this from the project root:

    python utils/manage_users.py

Never hand-edit a plain-text password into users.yaml and leave it
there - always run this script so the password is stored hashed.
"""

import os
import yaml
from yaml.loader import SafeLoader
import getpass
from streamlit_authenticator.utilities.hasher import Hasher

USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "config", "users.yaml")


def load():
    with open(USERS_FILE) as f:
        return yaml.load(f, Loader=SafeLoader)


def save(config):
    with open(USERS_FILE, "w") as f:
        yaml.dump(config, f, default_flow_style=False)


def main():
    config = load()
    print("=== RH App - User Management ===")
    username = input("Username (no spaces): ").strip()
    name = input("Full name: ").strip()
    email = input("Email: ").strip()
    role = ""
    while role not in ("admin", "staff"):
        role = input("Role (admin/staff): ").strip().lower()
    password = getpass.getpass("Password: ")
    confirm = getpass.getpass("Confirm password: ")
    if password != confirm:
        print("Passwords do not match. Aborting.")
        return

    hashed = Hasher.hash(password)

    config["credentials"]["usernames"][username] = {
        "name": name,
        "email": email,
        "password": hashed,
        "role": role,
    }
    save(config)
    print(f"\nUser '{username}' ({role}) saved to {USERS_FILE}.")


if __name__ == "__main__":
    main()
