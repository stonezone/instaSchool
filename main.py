"""
InstaSchool - AI-Powered Curriculum Generator
Landing page and navigation hub
"""

# NOTE: Module cleanup removed - causes KeyError crashes on Python 3.13/Streamlit Cloud
# The previous approach of clearing sys.modules broke nested imports

# CRITICAL: Set matplotlib backend BEFORE any other imports that might use it
import matplotlib
matplotlib.use('Agg')

import streamlit as st
from pathlib import Path

# Page config MUST be first Streamlit command
st.set_page_config(
    page_title="InstaSchool",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="auto"
)

# Load CSS
css_path = Path("static/css/design_system.css")
if css_path.exists():
    with open(css_path, 'r') as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Import after page config
from version import get_version_display

# Landing Page Content
st.markdown(
    f"""
    <div class="hero-glass animate-fade-in">
        <div class="gradient-text" style="font-family: var(--font-display); font-size: 44px; font-weight: 600; margin: 0;">
            🎓 InstaSchool
        </div>
        <div style="color: var(--text-tertiary); font-size: 13px; font-weight: 600; letter-spacing: 0.5px; margin-top: 6px;">
            {get_version_display()}
        </div>
        <div style="margin-top: 14px; font-size: 17px;">
            Choose your mode to get started:
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

col1, col2, col3 = st.columns(3)

with col1:
    with st.container(border=True):
        st.markdown("### 🎒 Student")
        st.markdown("Access your lessons, complete quizzes, and track your progress.")
        if st.button("Enter Classroom", width="stretch", key="btn_student"):
            st.switch_page("pages/1_Student.py")

with col2:
    with st.container(border=True):
        st.markdown("### 👨‍🏫 Teacher")
        st.markdown("Create new curricula, manage content, and view analytics.")
        if st.button("Create Curriculum", width="stretch", key="btn_teacher"):
            st.switch_page("pages/2_Create.py")

with col3:
    with st.container(border=True):
        st.markdown("### 👨‍👩‍👧 Parent")
        st.markdown("Monitor family progress, manage profiles, and print reports.")
        if st.button("Family Dashboard", width="stretch", key="btn_parent"):
            st.switch_page("pages/3_Parent.py")

# Quick stats
st.markdown("---")
st.markdown("### 📊 Quick Stats")

curricula_dir = Path("curricula")
total_curricula = len(list(curricula_dir.glob("*.json"))) if curricula_dir.exists() else 0

stat_col1, stat_col2, stat_col3 = st.columns(3)
with stat_col1:
    st.metric("Curricula Created", total_curricula)
    if st.button("📚 View Curricula", width="stretch", key="btn_view_curricula"):
        # Parent dashboard has a Curricula tab; send users there
        st.switch_page("pages/3_Parent.py")
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
from services.session_service import init_tempfile_cleanup
init_tempfile_cleanup(max_age_hours=24)
