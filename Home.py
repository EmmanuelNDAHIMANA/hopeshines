import streamlit as st
from utils.auth import login_widget

st.set_page_config(page_title="RH Database App", page_icon="📋", layout="wide")

st.title("📋 RH Database App")

authenticator, name, auth_status, username, role = login_widget()

if auth_status:
    st.success(f"Welcome, {name}! (role: {role})")
    st.write(
        "Use the sidebar to navigate:\n\n"
        "- **Single Entry** — add one record at a time to any dataset\n"
        "- **Bulk Upload** — upload a CSV/Excel file to add many records at once\n"
        + ("- **Dashboard** — visual summary of all submitted data (admin only)\n- **User Management** — create, edit, and delete accounts (admin only)\n" if role == "admin" else "")
    )
    authenticator.logout(location="sidebar")
elif auth_status is False:
    st.stop()
else:
    st.stop()
