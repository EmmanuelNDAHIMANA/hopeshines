"""
Login + role-based access control.

Users, hashed passwords and roles are stored in config/users.yaml.
Roles: "admin" (full access incl. dashboard + user management)
       "staff" (data entry only: single entry + bulk upload)

Run `python utils/manage_users.py` to add/update users and generate
password hashes - never store plain-text passwords in the yaml file.
"""

import os
import tempfile

import yaml
from yaml.loader import SafeLoader
import streamlit as st
import streamlit_authenticator as stauth

USERS_FILE = os.path.join(os.path.dirname(__file__), "..", "config", "users.yaml")


def _load_config():
    with open(USERS_FILE) as f:
        return yaml.load(f, Loader=SafeLoader)


def save_config(config):
    """Write the user configuration atomically so a failed save cannot truncate it."""
    directory = os.path.dirname(os.path.abspath(USERS_FILE))
    fd, temporary_path = tempfile.mkstemp(dir=directory, suffix=".yaml.tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            yaml.safe_dump(config, f, default_flow_style=False, sort_keys=False)
        os.replace(temporary_path, USERS_FILE)
    finally:
        if os.path.exists(temporary_path):
            os.remove(temporary_path)


def get_authenticator():
    config = _load_config()
    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )
    return authenticator, config


def _find_user(users, username):
    """Find a configured username, tolerating case normalization by auth cookies."""
    if not username:
        return None, None
    if username in users:
        return username, users[username]

    normalized_username = str(username).casefold()
    for configured_username, user in users.items():
        if str(configured_username).casefold() == normalized_username:
            return configured_username, user
    return None, None


def login_widget():
    """Render the login form. Returns (name, auth_status, username, role)."""
    authenticator, config = get_authenticator()
    authenticator.login(location="main")

    auth_status = st.session_state.get("authentication_status")
    name = st.session_state.get("name")
    username = st.session_state.get("username")
    role = None

    if auth_status:
        canonical_username, user = _find_user(config["credentials"]["usernames"], username)
        if user is None:
            st.session_state["authentication_status"] = False
            st.session_state.pop("role", None)
            auth_status = False
            st.error("Your account is no longer active. Please log in again.")
        else:
            username = canonical_username
            st.session_state["username"] = canonical_username
            role = user.get("role", "staff")
            st.session_state["role"] = role
    elif auth_status is False:
        st.error("Username or password is incorrect.")
    elif auth_status is None:
        st.info("Please enter your username and password.")

    return authenticator, name, auth_status, username, role


def require_login():
    """Call at the top of every page. Stops the page if not logged in."""
    username = st.session_state.get("username")
    if not st.session_state.get("authentication_status") or not username:
        st.warning("Please log in from the Home page first.")
        st.stop()

    # Read the current role on every page load so deleted or demoted accounts
    # cannot keep using privileges from an old Streamlit session.
    users = _load_config()["credentials"]["usernames"]
    canonical_username, user = _find_user(users, username)
    if user is None:
        st.session_state["authentication_status"] = False
        st.session_state.pop("role", None)
        st.error("Your account is no longer active. Please log in again.")
        st.stop()
    username = canonical_username
    st.session_state["username"] = canonical_username
    role = user.get("role", "staff")
    st.session_state["role"] = role
    return username, role


def require_admin():
    username, role = require_login()
    if role != "admin":
        st.error("This page is only available to admin users.")
        st.stop()
    return username, role
