import re

import streamlit as st
from streamlit_authenticator.utilities.hasher import Hasher

from utils.auth import _load_config, require_admin, save_config

st.set_page_config(page_title="User Management", page_icon="👥", layout="wide")
current_username, _ = require_admin()
st.title("👥 User Management")
st.caption("Create accounts, update account details or passwords, and remove access.")

config = _load_config()
users = config["credentials"]["usernames"]
admin_count = sum(user.get("role", "staff") == "admin" for user in users.values())

st.subheader("Current users")
if users:
    st.dataframe(
        [
            {"Username": username, "Name": user.get("name", ""), "Email": user.get("email", ""), "Role": user.get("role", "staff")}
            for username, user in sorted(users.items())
        ],
        hide_index=True,
        use_container_width=True,
    )
else:
    st.info("There are no user accounts.")

create_tab, edit_tab, delete_tab = st.tabs(["Create user", "Edit user", "Delete user"])

with create_tab:
    with st.form("create_user"):
        new_username = st.text_input("Username")
        new_name = st.text_input("Full name")
        new_email = st.text_input("Email")
        new_role = st.selectbox("Role", ["staff", "admin"], key="new_role")
        new_password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm password", type="password")
        create_submitted = st.form_submit_button("Create user", type="primary")

    if create_submitted:
        username = new_username.strip()
        if not re.fullmatch(r"[A-Za-z0-9_.-]+", username):
            st.error("Use a username with letters, numbers, dots, underscores, or hyphens only.")
        elif username in users:
            st.error("That username already exists.")
        elif not new_name.strip() or not new_email.strip():
            st.error("Enter the user's name and email.")
        elif len(new_password) < 8:
            st.error("Use a password with at least 8 characters.")
        elif new_password != confirm_password:
            st.error("The passwords do not match.")
        else:
            users[username] = {
                "name": new_name.strip(),
                "email": new_email.strip(),
                "password": Hasher.hash(new_password),
                "role": new_role,
            }
            save_config(config)
            st.success(f"Created {username}.")
            st.rerun()

with edit_tab:
    if not users:
        st.info("Create a user before editing accounts.")
    else:
        selected_username = st.selectbox("Choose a user", sorted(users), key="edit_username")
        selected_user = users[selected_username]
        with st.form("edit_user"):
            edited_name = st.text_input("Full name", value=selected_user.get("name", ""))
            edited_email = st.text_input("Email", value=selected_user.get("email", ""))
            role_options = ["staff", "admin"]
            selected_role = selected_user.get("role", "staff")
            edited_role = st.selectbox("Role", role_options, index=role_options.index(selected_role) if selected_role in role_options else 0)
            edited_password = st.text_input("New password (leave blank to keep current)", type="password")
            confirm_edited_password = st.text_input("Confirm new password", type="password")
            edit_submitted = st.form_submit_button("Save changes", type="primary")

        if edit_submitted:
            if not edited_name.strip() or not edited_email.strip():
                st.error("Name and email are required.")
            elif edited_password and len(edited_password) < 8:
                st.error("Use a password with at least 8 characters.")
            elif edited_password != confirm_edited_password:
                st.error("The new passwords do not match.")
            elif selected_user.get("role") == "admin" and edited_role != "admin" and admin_count <= 1:
                st.error("You cannot demote the last admin account.")
            else:
                selected_user.update({"name": edited_name.strip(), "email": edited_email.strip(), "role": edited_role})
                if edited_password:
                    selected_user["password"] = Hasher.hash(edited_password)
                save_config(config)
                st.success(f"Updated {selected_username}.")
                st.rerun()

with delete_tab:
    deletable_users = [username for username in sorted(users) if username != current_username]
    if not deletable_users:
        st.info("There are no other accounts to delete.")
    else:
        delete_username = st.selectbox("Choose a user to delete", deletable_users, key="delete_username")
        st.warning(f"Deleting **{delete_username}** removes their login access immediately.")
        if st.button("Delete user", type="primary", key="confirm_delete"):
            target_user = users[delete_username]
            if target_user.get("role", "staff") == "admin" and admin_count <= 1:
                st.error("You cannot delete the last admin account.")
            else:
                del users[delete_username]
                save_config(config)
                st.success(f"Deleted {delete_username}.")
                st.rerun()
