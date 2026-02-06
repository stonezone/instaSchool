"""
InstaSchool - AI-Powered Curriculum Generator
Landing Page - Modern 2025 Design (Native Streamlit)
"""

import matplotlib
matplotlib.use('Agg')

import streamlit as st
from pathlib import Path

# Page config - MUST be first Streamlit call
st.set_page_config(
    page_title="InstaSchool - AI Curriculum Generator",
    page_icon=":material/school:",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from version import get_version_display

# =============================================================================
# LOGO (appears on every page via Streamlit's built-in logo system)
# =============================================================================
st.logo(
    "static/logo_wide.svg",
    icon_image="static/logo.svg",
    size="large",
)

# =============================================================================
# MINIMAL CSS - Only for hero gradient text (no native equivalent)
# =============================================================================
st.html("""
<style>
.hero-gradient {
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}
</style>
""")

# =============================================================================
# HERO SECTION
# =============================================================================
version = get_version_display()

st.space("large")

with st.container(horizontal_alignment="center"):
    st.caption(f":green-badge[Live] {version}")

    st.html("""
    <h1 style="font-size: clamp(40px, 6vw, 64px); font-weight: 800; line-height: 1.1;
               letter-spacing: -0.03em; text-align: center; margin: 0 0 16px;">
        Create <span class="hero-gradient">AI-powered</span><br>curricula in minutes
    </h1>
    """)

    st.markdown(
        "Generate complete, standards-aligned K-12 curricula with AI-powered lessons, "
        "interactive assessments, and personalized learning paths. Built for educators and families.",
        text_alignment="center",
    )

st.space("medium")

# CTA buttons
with st.container(horizontal=True, horizontal_alignment="center"):
    if st.button("Start creating", icon=":material/auto_awesome:", type="primary"):
        st.switch_page("pages/2_Create.py")
    if st.button("Explore learning", icon=":material/school:"):
        st.switch_page("pages/1_Student.py")

st.space("large")

# =============================================================================
# STATS ROW
# =============================================================================
curricula_dir = Path("curricula")
total_curricula = len(list(curricula_dir.glob("*.json"))) if curricula_dir.exists() else 0

try:
    from services.user_service import UserService
    user_count = len(UserService().list_users())
except Exception:
    user_count = 0

with st.container(horizontal=True):
    st.metric("Curricula created", f"{total_curricula}+", border=True)
    st.metric("Active learners", str(user_count), border=True)
    st.metric("Grade range", "K-12", border=True)
    st.metric("AI providers", "3", border=True)

st.space("large")

# =============================================================================
# FEATURES SECTION
# =============================================================================
st.subheader("Everything you need to educate smarter", anchor=False)
st.caption("Powered by the latest AI models to create engaging, personalized educational content.")

st.space("small")

row1 = st.columns(3)
with row1[0]:
    with st.container(border=True):
        st.markdown(":material/psychology: **AI curriculum generator**")
        st.caption("Generate complete curricula with lessons, quizzes, and activities aligned to educational standards.")

with row1[1]:
    with st.container(border=True):
        st.markdown(":material/palette: **AI illustrations**")
        st.caption("Create custom educational illustrations for every lesson using GPT-Image-1 technology.")

with row1[2]:
    with st.container(border=True):
        st.markdown(":material/school: **Adaptive learning**")
        st.caption("Personalized AI tutoring that adapts to each student's pace and learning style.")

row2 = st.columns(3)
with row2[0]:
    with st.container(border=True):
        st.markdown(":material/analytics: **Progress analytics**")
        st.caption("Track learning progress with detailed analytics, streaks, and achievement badges.")

with row2[1]:
    with st.container(border=True):
        st.markdown(":material/replay: **Spaced repetition**")
        st.caption("SM-2 algorithm for flashcard scheduling ensures long-term knowledge retention.")

with row2[2]:
    with st.container(border=True):
        st.markdown(":material/download: **Multi-format export**")
        st.caption("Export curricula to PDF, HTML, or Markdown for offline use and sharing.")

st.space("large")

# =============================================================================
# MODE CARDS - Choose your path
# =============================================================================
st.subheader("Choose your path", anchor=False)
st.caption("Whether you're a student, educator, or parent, InstaSchool has the right tools for you.")

st.space("small")

modes = st.columns(3)
with modes[0]:
    with st.container(border=True):
        st.markdown(":material/school: **Student portal**")
        st.write("Access lessons, take quizzes, and track your progress with AI-powered tutoring.")
        st.page_link("pages/1_Student.py", label="Start learning", icon=":material/arrow_forward:")

with modes[1]:
    with st.container(border=True):
        st.markdown(":material/auto_awesome: **Create curriculum**")
        st.write("Generate complete curricula with AI-powered lessons, assessments, and media.")
        st.page_link("pages/2_Create.py", label="Create now", icon=":material/arrow_forward:")

with modes[2]:
    with st.container(border=True):
        st.markdown(":material/family_restroom: **Family dashboard**")
        st.write("Monitor progress, manage profiles, and export learning materials.")
        st.page_link("pages/3_Parent.py", label="View dashboard", icon=":material/arrow_forward:")

st.space("large")

# =============================================================================
# FOOTER
# =============================================================================
st.caption(
    f"Built with [Streamlit](https://streamlit.io) and [OpenAI](https://openai.com) · {version}",
    text_alignment="center",
)

# =============================================================================
# CLEANUP
# =============================================================================
try:
    from services.session_service import init_tempfile_cleanup
    init_tempfile_cleanup(max_age_hours=24)
except Exception:
    pass
