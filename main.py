"""
InstaSchool - AI-Powered Curriculum Generator
Landing page and navigation hub
"""
import os
import sys

# CRITICAL: Clear stale module references before imports
_modules_to_clear = [k for k in list(sys.modules.keys())
                     if k.startswith(('src.', 'services.', 'utils.'))
                     and k in sys.modules]
for _mod in _modules_to_clear:
    try:
        del sys.modules[_mod]
    except KeyError:
        pass

# CRITICAL: Set matplotlib backend BEFORE any other imports that might use it
import matplotlib
matplotlib.use('Agg')

import streamlit as st
import atexit
from pathlib import Path

# Page config MUST be first Streamlit command
st.set_page_config(
    page_title="InstaSchool",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load CSS
css_path = Path("static/css/design_system.css")
if css_path.exists():
    with open(css_path, 'r') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Import after page config
from src.ui_components import ModernUI
from version import get_version_display

# Landing Page Content
st.markdown("# 🎓 Welcome to InstaSchool")
st.markdown(f"*{get_version_display()}*")
st.markdown("### Choose your mode to get started:")

col1, col2, col3 = st.columns(3)

with col1:
    with st.container(border=True):
        st.markdown("### 🎒 Student")
        st.markdown("Access your lessons, complete quizzes, and track your progress.")
        if st.button("Enter Classroom", use_container_width=True, key="btn_student"):
            st.switch_page("pages/1_Student.py")

with col2:
    with st.container(border=True):
        st.markdown("### 👨‍🏫 Teacher")
        st.markdown("Create new curricula, manage content, and view analytics.")
        if st.button("Create Curriculum", use_container_width=True, key="btn_teacher"):
            st.switch_page("pages/2_Create.py")

with col3:
    with st.container(border=True):
        st.markdown("### 👨‍👩‍👧 Parent")
        st.markdown("Monitor family progress, manage profiles, and print reports.")
        if st.button("Family Dashboard", use_container_width=True, key="btn_parent"):
            st.switch_page("pages/3_Parent.py")

# Quick stats
st.markdown("---")
st.markdown("### 📊 Quick Stats")

curricula_dir = Path("curricula")
total_curricula = len(list(curricula_dir.glob("*.json"))) if curricula_dir.exists() else 0

stat_col1, stat_col2, stat_col3 = st.columns(3)
with stat_col1:
    st.metric("Curricula Created", total_curricula)
with stat_col2:
    from services.user_service import UserService
    user_count = len(UserService().list_users())
    st.metric("Student Profiles", user_count)
with stat_col3:
    st.metric("AI Providers", "OpenAI + Kimi")

# Footer
st.markdown("---")
st.caption("Built with ❤️ using Streamlit and OpenAI")

# Cleanup registration
from services.session_service import SessionManager
atexit.register(lambda: SessionManager().cleanup_temp_files())
