"""
InstaSchool - AI-Powered Curriculum Generator
Modern landing page with light/dark mode
"""

import matplotlib
matplotlib.use('Agg')

import streamlit as st
from pathlib import Path

# Page config - MUST be first Streamlit call
st.set_page_config(
    page_title="InstaSchool",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from version import get_version_display
from src.ui_components import ModernUI, ThemeManager

# =============================================================================
# LOAD DESIGN SYSTEM & THEME
# =============================================================================
ModernUI.load_css()
theme = ThemeManager.init_theme()
ThemeManager.apply_theme(theme)

# =============================================================================
# LANDING PAGE STYLES
# =============================================================================
is_dark = theme == "dark"

st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* Landing page specific styles */
.stApp > header {{ display: none !important; }}
.stApp [data-testid="stSidebar"] {{ display: none !important; }}
#MainMenu, .stDeployButton, footer {{ display: none !important; }}

/* Fixed Header */
.fixed-header {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    z-index: 1000;
    background: {('rgba(10,10,15,0.85)' if is_dark else 'rgba(255,255,255,0.85)')};
    backdrop-filter: blur(20px);
    -webkit-backdrop-filter: blur(20px);
    border-bottom: 1px solid {('rgba(255,255,255,0.08)' if is_dark else '#e2e8f0')};
    padding: 0 40px;
    height: 64px;
    display: flex;
    align-items: center;
    justify-content: space-between;
}}

.header-logo {{
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 20px;
    font-weight: 700;
    color: {('#f1f5f9' if is_dark else '#0f172a')};
    text-decoration: none;
}}

.header-logo-icon {{
    font-size: 28px;
}}

.header-nav {{
    display: flex;
    align-items: center;
    gap: 8px;
}}

.nav-link {{
    padding: 8px 16px;
    border-radius: 8px;
    font-size: 14px;
    font-weight: 500;
    color: {('#94a3b8' if is_dark else '#475569')};
    text-decoration: none;
    transition: all 0.2s ease;
}}

.nav-link:hover {{
    color: {('#f1f5f9' if is_dark else '#0f172a')};
    background: {('rgba(255,255,255,0.05)' if is_dark else '#f8fafc')};
}}

.theme-btn {{
    width: 40px;
    height: 40px;
    border-radius: 10px;
    border: 1px solid {('rgba(255,255,255,0.08)' if is_dark else '#e2e8f0')};
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    cursor: pointer;
    font-size: 18px;
    margin-left: 16px;
}}

/* Main content offset */
.main-content {{
    padding-top: 100px;
    max-width: 1200px;
    margin: 0 auto;
    padding-left: 24px;
    padding-right: 24px;
}}

/* Hero Section */
.hero {{
    text-align: center;
    padding: 40px 20px 60px;
}}

.hero-badge {{
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: {('rgba(99,102,241,0.15)' if is_dark else 'rgba(99,102,241,0.08)')};
    border: 1px solid {('rgba(99,102,241,0.3)' if is_dark else 'rgba(99,102,241,0.2)')};
    color: #818cf8;
    padding: 8px 16px;
    border-radius: 100px;
    font-size: 13px;
    font-weight: 500;
    margin-bottom: 24px;
}}

.hero-badge-dot {{
    width: 6px;
    height: 6px;
    background: #22c55e;
    border-radius: 50%;
}}

.hero-title {{
    font-size: clamp(36px, 6vw, 56px);
    font-weight: 800;
    color: {('#f1f5f9' if is_dark else '#0f172a')};
    margin: 0 0 16px;
    line-height: 1.1;
    letter-spacing: -0.02em;
}}

.hero-title-accent {{
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #a855f7 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

.hero-subtitle {{
    font-size: 18px;
    color: {('#94a3b8' if is_dark else '#475569')};
    max-width: 560px;
    margin: 0 auto;
    line-height: 1.7;
}}

/* Mode Cards */
.cards-section {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    margin: 0 auto 60px;
    max-width: 960px;
}}

@media (max-width: 800px) {{
    .cards-section {{
        grid-template-columns: 1fr;
        max-width: 400px;
    }}
}}

.mode-card {{
    background: {('rgba(255,255,255,0.03)' if is_dark else '#ffffff')};
    border: 1px solid {('rgba(255,255,255,0.08)' if is_dark else '#e2e8f0')};
    border-radius: 16px;
    padding: 28px;
    transition: all 0.25s ease;
    cursor: pointer;
    text-decoration: none;
    display: block;
}}

.mode-card:hover {{
    border-color: {('rgba(255,255,255,0.15)' if is_dark else '#cbd5e1')};
    box-shadow: {('0 8px 30px rgba(0,0,0,0.3)' if is_dark else '0 4px 20px rgba(0,0,0,0.08)')};
    transform: translateY(-4px);
}}

.mode-card-icon {{
    width: 48px;
    height: 48px;
    background: {('rgba(99,102,241,0.15)' if is_dark else 'rgba(99,102,241,0.08)')};
    border-radius: 12px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 24px;
    margin-bottom: 16px;
}}

.mode-card-title {{
    font-size: 17px;
    font-weight: 600;
    color: {('#f1f5f9' if is_dark else '#0f172a')};
    margin: 0 0 8px;
}}

.mode-card-desc {{
    font-size: 14px;
    color: {('#94a3b8' if is_dark else '#475569')};
    line-height: 1.6;
    margin: 0;
}}

/* Stats */
.stats-section {{
    background: {('#111118' if is_dark else '#f8fafc')};
    border: 1px solid {('rgba(255,255,255,0.08)' if is_dark else '#e2e8f0')};
    border-radius: 20px;
    padding: 40px;
    margin: 0 auto 60px;
    max-width: 800px;
}}

.stats-grid {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
}}

@media (max-width: 600px) {{
    .stats-grid {{
        grid-template-columns: repeat(2, 1fr);
    }}
}}

.stat-item {{
    text-align: center;
}}

.stat-value {{
    font-size: 32px;
    font-weight: 800;
    color: #6366f1;
    margin-bottom: 4px;
}}

.stat-label {{
    font-size: 13px;
    color: {('#64748b' if is_dark else '#94a3b8')};
    font-weight: 500;
}}

/* Features */
.features-grid {{
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 20px;
    margin: 0 auto 60px;
    max-width: 800px;
}}

@media (max-width: 600px) {{
    .features-grid {{
        grid-template-columns: 1fr;
    }}
}}

.feature-card {{
    background: {('rgba(255,255,255,0.03)' if is_dark else '#ffffff')};
    border: 1px solid {('rgba(255,255,255,0.08)' if is_dark else '#e2e8f0')};
    border-radius: 16px;
    padding: 24px;
}}

.feature-title {{
    font-size: 15px;
    font-weight: 600;
    color: {('#f1f5f9' if is_dark else '#0f172a')};
    margin: 0 0 16px;
    display: flex;
    align-items: center;
    gap: 10px;
}}

.feature-list {{
    list-style: none;
    padding: 0;
    margin: 0;
}}

.feature-list li {{
    font-size: 14px;
    color: {('#94a3b8' if is_dark else '#475569')};
    padding: 8px 0;
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 1px solid {('rgba(255,255,255,0.05)' if is_dark else '#f1f5f9')};
}}

.feature-list li:last-child {{
    border-bottom: none;
}}

.check-icon {{
    color: #22c55e;
    font-size: 14px;
}}

/* Footer */
.site-footer {{
    text-align: center;
    padding: 32px 20px;
    border-top: 1px solid {('rgba(255,255,255,0.05)' if is_dark else '#e2e8f0')};
    color: {('#64748b' if is_dark else '#94a3b8')};
    font-size: 14px;
}}

/* Block container adjustments */
.stApp [data-testid="block-container"] {{
    padding-top: 0 !important;
    max-width: 100% !important;
}}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# FIXED HEADER
# =============================================================================
theme_icon = "☀️" if is_dark else "🌙"

st.markdown(f'''
<div class="fixed-header">
    <a href="/" class="header-logo">
        <span class="header-logo-icon">🎓</span>
        <span>InstaSchool</span>
    </a>
    <div class="header-nav">
        <a href="/Student" class="nav-link">Student</a>
        <a href="/Create" class="nav-link">Create</a>
        <a href="/Parent" class="nav-link">Parent</a>
        <a href="/Library" class="nav-link">Library</a>
    </div>
</div>
''', unsafe_allow_html=True)

# Theme toggle button (functional Streamlit button)
col_spacer, col_toggle = st.columns([12, 1])
with col_toggle:
    if st.button(theme_icon, key="theme_toggle", help="Toggle dark/light mode"):
        ThemeManager.toggle_theme()
        st.rerun()

# =============================================================================
# HERO SECTION
# =============================================================================
version = get_version_display()

st.markdown(f'''
<div class="main-content">
    <div class="hero">
        <div class="hero-badge">
            <span class="hero-badge-dot"></span>
            {version}
        </div>
        <h1 class="hero-title">
            <span class="hero-title-accent">AI-Powered</span> Curriculum Generator
        </h1>
        <p class="hero-subtitle">
            Create engaging, standards-aligned K-12 curricula in minutes.
            Personalized learning experiences powered by the latest AI.
        </p>
    </div>
</div>
''', unsafe_allow_html=True)

# =============================================================================
# MODE CARDS
# =============================================================================
st.markdown('''
<div class="main-content">
    <div class="cards-section">
        <a href="/Student" class="mode-card">
            <div class="mode-card-icon">🎓</div>
            <h3 class="mode-card-title">Student Portal</h3>
            <p class="mode-card-desc">Access lessons, take quizzes, and track your progress with adaptive AI tutoring.</p>
        </a>
        <a href="/Create" class="mode-card">
            <div class="mode-card-icon">✨</div>
            <h3 class="mode-card-title">Create Curriculum</h3>
            <p class="mode-card-desc">Generate complete curricula with AI-powered lessons, assessments, and media.</p>
        </a>
        <a href="/Parent" class="mode-card">
            <div class="mode-card-icon">👨‍👩‍👧</div>
            <h3 class="mode-card-title">Family Dashboard</h3>
            <p class="mode-card-desc">Monitor progress, manage profiles, and export learning materials.</p>
        </a>
    </div>
</div>
''', unsafe_allow_html=True)

# Navigation buttons (functional fallback for proper Streamlit routing)
st.markdown('<div class="main-content">', unsafe_allow_html=True)
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🎓 Student Portal", use_container_width=True, key="nav_student"):
        st.switch_page("pages/1_Student.py")
with col2:
    if st.button("✨ Create Curriculum", use_container_width=True, key="nav_create"):
        st.switch_page("pages/2_Create.py")
with col3:
    if st.button("👨‍👩‍👧 Family Dashboard", use_container_width=True, key="nav_parent"):
        st.switch_page("pages/3_Parent.py")
st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# STATS
# =============================================================================
curricula_dir = Path("curricula")
total_curricula = len(list(curricula_dir.glob("*.json"))) if curricula_dir.exists() else 0

try:
    from services.user_service import UserService
    user_count = len(UserService().list_users())
except:
    user_count = 0

st.markdown(f'''
<div class="main-content">
    <div class="stats-section">
        <div class="stats-grid">
            <div class="stat-item">
                <div class="stat-value">{total_curricula}</div>
                <div class="stat-label">Curricula</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{user_count}</div>
                <div class="stat-label">Students</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">3</div>
                <div class="stat-label">AI Providers</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">K-12</div>
                <div class="stat-label">Grades</div>
            </div>
        </div>
    </div>
</div>
''', unsafe_allow_html=True)

# =============================================================================
# FEATURES
# =============================================================================
st.markdown('''
<div class="main-content">
    <div class="features-grid">
        <div class="feature-card">
            <h4 class="feature-title">🧠 For Students</h4>
            <ul class="feature-list">
                <li><span class="check-icon">✓</span> Adaptive AI tutoring</li>
                <li><span class="check-icon">✓</span> Progress tracking</li>
                <li><span class="check-icon">✓</span> Interactive quizzes</li>
                <li><span class="check-icon">✓</span> Multimedia lessons</li>
            </ul>
        </div>
        <div class="feature-card">
            <h4 class="feature-title">⚡ For Educators</h4>
            <ul class="feature-list">
                <li><span class="check-icon">✓</span> Generate curricula in minutes</li>
                <li><span class="check-icon">✓</span> Standards-aligned content</li>
                <li><span class="check-icon">✓</span> AI-generated illustrations</li>
                <li><span class="check-icon">✓</span> Export to PDF/HTML</li>
            </ul>
        </div>
    </div>
</div>
''', unsafe_allow_html=True)

# =============================================================================
# FOOTER
# =============================================================================
st.markdown('''
<div class="site-footer">
    Built with Streamlit & OpenAI
</div>
''', unsafe_allow_html=True)

# Cleanup
try:
    from services.session_service import init_tempfile_cleanup
    init_tempfile_cleanup(max_age_hours=24)
except:
    pass
