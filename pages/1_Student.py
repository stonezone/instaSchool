"""
Student Mode - Learning Interface
InstaSchool multi-page app
"""
import os
import sys

# CRITICAL: Clear stale module references before imports
# This fixes KeyError crashes on Streamlit Cloud hot reloads (Python 3.13)
# Note: Preserve 'src.core' to avoid KeyError on nested imports
_modules_to_clear = [k for k in list(sys.modules.keys())
                     if k.startswith(('src.', 'services.', 'utils.'))
                     and not k.startswith('src.core')  # Preserve core module hierarchy
                     and k in sys.modules]
for _mod in _modules_to_clear:
    try:
        del sys.modules[_mod]
    except KeyError:
        pass

import streamlit as st
import yaml
from pathlib import Path

# Import shared initialization
from src.shared_init import (
    setup_page,
    init_session_state,
    load_config,
    get_openai_client,
    get_user_service,
)
from src.state_manager import StateManager
from services.user_service import UserService

# Page config
setup_page(title="InstaSchool - Student", icon="🎓")

# Load config
config = load_config()

# Get OpenAI client
api_key = os.getenv("OPENAI_API_KEY")
org_id = os.getenv("OPENAI_ORG_ID")
client = get_openai_client() if api_key else None

# Initialize state
StateManager.initialize_state()

# Get or create user service
if not StateManager.get_state("user_service"):
    StateManager.set_state("user_service", UserService())

# Student Login UI
st.sidebar.markdown("### 👤 Student Login")

user_service: UserService = StateManager.get_state("user_service")
current_user = StateManager.get_state("current_user")

# Login state
needs_pin = StateManager.get_state('login_needs_pin')
saved_username = StateManager.get_state('login_username')

if not current_user:
    if needs_pin:
        # User exists and has PIN - show PIN entry
        st.sidebar.info(f"Welcome back, **{saved_username}**!")
        pin = st.sidebar.text_input("Enter PIN", type="password", max_chars=6, key="student_pin")

        col1, col2 = st.sidebar.columns(2)
        with col1:
            if st.button("Login", use_container_width=True):
                if pin:
                    user, msg = user_service.authenticate(saved_username, pin)
                    if msg == "success":
                        StateManager.set_state("current_user", user)
                        StateManager.set_state('login_needs_pin', False)
                        st.rerun()
                    else:
                        st.sidebar.error("Incorrect PIN. Try again.")
                else:
                    st.sidebar.warning("Please enter your PIN.")
        with col2:
            if st.button("Cancel", use_container_width=True):
                StateManager.set_state('login_needs_pin', False)
                StateManager.set_state('login_username', '')
                st.rerun()
    else:
        # Show username input
        username = st.sidebar.text_input("Your name", key="student_username")

        # Check if user exists and show appropriate action
        user_exists = user_service.user_exists(username.strip()) if username.strip() else False

        if user_exists:
            has_pin = user_service.user_has_pin(username.strip())
            if has_pin:
                if st.sidebar.button("Continue →", use_container_width=True):
                    StateManager.set_state('login_needs_pin', True)
                    StateManager.set_state('login_username', username.strip())
                    st.rerun()
            else:
                if st.sidebar.button("Login", use_container_width=True):
                    user, msg = user_service.authenticate(username.strip())
                    if msg == "success":
                        StateManager.set_state("current_user", user)
                        st.rerun()
        else:
            # New user - show create account options
            if username.strip():
                st.sidebar.caption("New student? Create your profile:")
                pin_input = st.sidebar.text_input(
                    "Optional PIN (4-6 digits)",
                    type="password",
                    max_chars=6,
                    key="new_user_pin",
                    help="Set a PIN to protect your progress"
                )

                if st.sidebar.button("Create Profile", use_container_width=True):
                    # Validate PIN if provided
                    if pin_input and (len(pin_input) < 4 or not pin_input.isdigit()):
                        st.sidebar.error("PIN must be 4-6 digits")
                    else:
                        user, msg = user_service.create_user(
                            username.strip(),
                            pin_input if pin_input else None
                        )
                        if msg == "created":
                            StateManager.set_state("current_user", user)
                            st.sidebar.success("Profile created!")
                            st.rerun()
                        else:
                            st.sidebar.error(f"Could not create profile: {msg}")

    # Show existing profiles for quick switching
    users = user_service.list_users()
    if users:
        with st.sidebar.expander("📋 Switch Profile", expanded=False):
            for u in users[:5]:  # Limit to 5 profiles
                label = f"{'🔒' if u['has_pin'] else '👤'} {u['username']}"
                if st.button(label, key=f"switch_{u['username']}", use_container_width=True):
                    if u['has_pin']:
                        StateManager.set_state('login_needs_pin', True)
                        StateManager.set_state('login_username', u['username'])
                    else:
                        user, _ = user_service.authenticate(u['username'])
                        StateManager.set_state("current_user", user)
                    st.rerun()

if not current_user:
    st.info("👈 Enter your name in the sidebar to start learning.")
    st.stop()

# Logged in - show user info and logout
st.sidebar.success(f"✓ Logged in as **{current_user['username']}**")
if current_user.get('has_pin'):
    st.sidebar.caption("🔒 PIN protected")
if st.sidebar.button("Logout", use_container_width=True):
    StateManager.set_state("current_user", None)
    StateManager.set_state('login_needs_pin', False)
    StateManager.set_state('login_username', '')
    st.rerun()

# Render the student learning interface
from src.student_mode.student_ui import render_student_mode
render_student_mode(config, client)
