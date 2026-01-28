"""
InstaSchool - AI-Powered Curriculum Generator
Premium Landing Page - Modern 2025 Design
Inspired by Linear, Vercel, and Notion
"""

import matplotlib
matplotlib.use('Agg')

import streamlit as st
from pathlib import Path

# Page config - MUST be first Streamlit call
st.set_page_config(
    page_title="InstaSchool - AI Curriculum Generator",
    page_icon="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>%E2%9C%A8</text></svg>",
    layout="wide",
    initial_sidebar_state="collapsed"
)

from version import get_version_display
from src.ui_components import ModernUI, ThemeManager

# =============================================================================
# INITIALIZE THEME
# =============================================================================
ModernUI.load_css()
theme = ThemeManager.init_theme()
ThemeManager.apply_theme(theme)

is_dark = theme == "dark"

# =============================================================================
# CSS DESIGN SYSTEM - Premium 2025 Aesthetic
# =============================================================================
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

/* ============================================
   RESET & BASE
   ============================================ */
*, *::before, *::after {{
    box-sizing: border-box;
}}

.stApp {{
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif !important;
    background: {('#09090b' if is_dark else '#fafafa')} !important;
    overflow-x: hidden;
}}

/* Hide Streamlit chrome */
.stApp > header,
.stApp [data-testid="stSidebar"],
#MainMenu,
.stDeployButton,
footer,
.stApp [data-testid="stToolbar"] {{
    display: none !important;
}}

.stApp [data-testid="block-container"] {{
    padding: 0 !important;
    max-width: 100% !important;
}}

/* ============================================
   ANIMATED BACKGROUND
   ============================================ */
.bg-grid {{
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-image:
        linear-gradient({('rgba(255,255,255,0.02)' if is_dark else 'rgba(0,0,0,0.02)')} 1px, transparent 1px),
        linear-gradient(90deg, {('rgba(255,255,255,0.02)' if is_dark else 'rgba(0,0,0,0.02)')} 1px, transparent 1px);
    background-size: 64px 64px;
    pointer-events: none;
    z-index: 0;
}}

.gradient-orb {{
    position: fixed;
    border-radius: 50%;
    filter: blur(100px);
    opacity: {('0.15' if is_dark else '0.08')};
    pointer-events: none;
    z-index: 0;
}}

.orb-1 {{
    top: -200px;
    right: -100px;
    width: 600px;
    height: 600px;
    background: linear-gradient(135deg, #6366f1, #8b5cf6);
    animation: float-1 20s ease-in-out infinite;
}}

.orb-2 {{
    bottom: -150px;
    left: -150px;
    width: 500px;
    height: 500px;
    background: linear-gradient(135deg, #06b6d4, #3b82f6);
    animation: float-2 25s ease-in-out infinite;
}}

.orb-3 {{
    top: 40%;
    left: 50%;
    width: 400px;
    height: 400px;
    background: linear-gradient(135deg, #f472b6, #c084fc);
    animation: float-3 22s ease-in-out infinite;
}}

@keyframes float-1 {{
    0%, 100% {{ transform: translate(0, 0) scale(1); }}
    25% {{ transform: translate(-50px, 50px) scale(1.1); }}
    50% {{ transform: translate(-30px, 100px) scale(0.95); }}
    75% {{ transform: translate(30px, 50px) scale(1.05); }}
}}

@keyframes float-2 {{
    0%, 100% {{ transform: translate(0, 0) scale(1); }}
    33% {{ transform: translate(80px, -60px) scale(1.1); }}
    66% {{ transform: translate(40px, -30px) scale(0.9); }}
}}

@keyframes float-3 {{
    0%, 100% {{ transform: translate(-50%, 0) scale(1); }}
    50% {{ transform: translate(-50%, -100px) scale(1.15); }}
}}

/* ============================================
   FIXED HEADER - Glassmorphism
   ============================================ */
.site-header {{
    position: fixed !important;
    top: 0 !important;
    left: 0 !important;
    right: 0 !important;
    z-index: 999999 !important;
    height: 72px;
    display: flex !important;
    align-items: center;
    justify-content: space-between;
    padding: 0 48px;
    background: {('#09090b' if is_dark else '#ffffff')} !important;
    border-bottom: 1px solid {('rgba(255,255,255,0.08)' if is_dark else 'rgba(0,0,0,0.08)')};
    box-shadow: 0 1px 3px {('rgba(0,0,0,0.3)' if is_dark else 'rgba(0,0,0,0.05)')};
}}

.header-logo {{
    display: flex;
    align-items: center;
    gap: 12px;
    text-decoration: none;
}}

.logo-svg {{
    width: 40px;
    height: 40px;
    border-radius: 10px;
    box-shadow: 0 4px 12px rgba(99, 102, 241, 0.3);
    flex-shrink: 0;
}}

.logo-text {{
    font-size: 20px;
    font-weight: 700;
    color: {('#fafafa' if is_dark else '#09090b')};
    letter-spacing: -0.02em;
}}

.header-nav {{
    display: flex;
    align-items: center;
    gap: 4px;
}}

.nav-item {{
    padding: 10px 18px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 500;
    color: {('#a1a1aa' if is_dark else '#52525b')};
    text-decoration: none;
    transition: all 0.2s ease;
    cursor: pointer;
}}

.nav-item:hover {{
    color: {('#fafafa' if is_dark else '#09090b')};
    background: {('rgba(255,255,255,0.06)' if is_dark else 'rgba(0,0,0,0.04)')};
}}

.header-actions {{
    display: flex;
    align-items: center;
    gap: 12px;
}}

.theme-toggle {{
    width: 40px;
    height: 40px;
    border-radius: 10px;
    border: 1px solid {('rgba(255,255,255,0.08)' if is_dark else 'rgba(0,0,0,0.08)')};
    background: transparent;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 18px;
    cursor: pointer;
    transition: all 0.2s ease;
}}

.theme-toggle:hover {{
    background: {('rgba(255,255,255,0.06)' if is_dark else 'rgba(0,0,0,0.04)')};
    border-color: {('rgba(255,255,255,0.15)' if is_dark else 'rgba(0,0,0,0.12)')};
}}

.cta-btn {{
    padding: 10px 20px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
    color: white;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    text-decoration: none;
    transition: all 0.2s ease;
    box-shadow: 0 2px 8px rgba(99, 102, 241, 0.3);
}}

.cta-btn:hover {{
    transform: translateY(-1px);
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.4);
}}

/* ============================================
   MAIN CONTENT WRAPPER
   ============================================ */
.page-content {{
    position: relative;
    z-index: 1;
    padding-top: 72px;
}}

/* ============================================
   HERO SECTION
   ============================================ */
.hero {{
    min-height: calc(100vh - 72px);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 24px 120px;
    text-align: center;
    position: relative;
}}

.hero-badge {{
    display: inline-flex;
    align-items: center;
    gap: 10px;
    padding: 8px 16px 8px 10px;
    background: {('rgba(99,102,241,0.12)' if is_dark else 'rgba(99,102,241,0.08)')};
    border: 1px solid {('rgba(99,102,241,0.25)' if is_dark else 'rgba(99,102,241,0.15)')};
    border-radius: 100px;
    font-size: 13px;
    font-weight: 500;
    color: #818cf8;
    margin-bottom: 32px;
    animation: fadeInUp 0.6s ease;
}}

.badge-dot {{
    width: 8px;
    height: 8px;
    background: #22c55e;
    border-radius: 50%;
    animation: pulse-dot 2s ease-in-out infinite;
}}

@keyframes pulse-dot {{
    0%, 100% {{ opacity: 1; transform: scale(1); }}
    50% {{ opacity: 0.6; transform: scale(1.1); }}
}}

.hero-title {{
    font-size: clamp(48px, 8vw, 80px);
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -0.03em;
    margin: 0 0 24px;
    color: {('#fafafa' if is_dark else '#09090b')};
    animation: fadeInUp 0.6s ease 0.1s backwards;
}}

.hero-title-gradient {{
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

.hero-subtitle {{
    font-size: clamp(18px, 2.5vw, 22px);
    font-weight: 400;
    line-height: 1.6;
    color: {('#a1a1aa' if is_dark else '#52525b')};
    max-width: 640px;
    margin: 0 auto 48px;
    animation: fadeInUp 0.6s ease 0.2s backwards;
}}

.hero-cta-group {{
    display: flex;
    align-items: center;
    gap: 16px;
    flex-wrap: wrap;
    justify-content: center;
    animation: fadeInUp 0.6s ease 0.3s backwards;
}}

.btn-primary {{
    padding: 16px 32px;
    border-radius: 12px;
    font-size: 16px;
    font-weight: 600;
    color: white;
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%);
    text-decoration: none;
    transition: all 0.25s ease;
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.35);
    border: none;
    cursor: pointer;
}}

.btn-primary:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.45);
}}

.btn-secondary {{
    padding: 16px 32px;
    border-radius: 12px;
    font-size: 16px;
    font-weight: 600;
    color: {('#fafafa' if is_dark else '#09090b')};
    background: transparent;
    border: 1px solid {('rgba(255,255,255,0.12)' if is_dark else 'rgba(0,0,0,0.12)')};
    text-decoration: none;
    transition: all 0.25s ease;
    cursor: pointer;
}}

.btn-secondary:hover {{
    background: {('rgba(255,255,255,0.06)' if is_dark else 'rgba(0,0,0,0.04)')};
    border-color: {('rgba(255,255,255,0.2)' if is_dark else 'rgba(0,0,0,0.2)')};
}}

@keyframes fadeInUp {{
    from {{
        opacity: 0;
        transform: translateY(20px);
    }}
    to {{
        opacity: 1;
        transform: translateY(0);
    }}
}}

/* ============================================
   SOCIAL PROOF / STATS BAR
   ============================================ */
.stats-bar {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 48px;
    flex-wrap: wrap;
    margin-top: 80px;
    padding: 32px 40px;
    background: {('rgba(255,255,255,0.02)' if is_dark else 'rgba(0,0,0,0.02)')};
    border: 1px solid {('rgba(255,255,255,0.05)' if is_dark else 'rgba(0,0,0,0.05)')};
    border-radius: 20px;
    animation: fadeInUp 0.6s ease 0.4s backwards;
}}

.stat-item {{
    text-align: center;
}}

.stat-value {{
    font-size: 32px;
    font-weight: 800;
    color: {('#fafafa' if is_dark else '#09090b')};
    letter-spacing: -0.02em;
}}

.stat-value-accent {{
    background: linear-gradient(135deg, #6366f1, #a855f7);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

.stat-label {{
    font-size: 13px;
    font-weight: 500;
    color: {('#71717a' if is_dark else '#71717a')};
    margin-top: 4px;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}}

/* ============================================
   FEATURES SECTION
   ============================================ */
.features-section {{
    padding: 120px 24px;
    max-width: 1200px;
    margin: 0 auto;
}}

.section-label {{
    font-size: 13px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
    color: #6366f1;
    text-align: center;
    margin-bottom: 16px;
}}

.section-title {{
    font-size: clamp(32px, 5vw, 48px);
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: -0.02em;
    color: {('#fafafa' if is_dark else '#09090b')};
    text-align: center;
    margin: 0 0 16px;
}}

.section-subtitle {{
    font-size: 18px;
    color: {('#a1a1aa' if is_dark else '#52525b')};
    text-align: center;
    max-width: 600px;
    margin: 0 auto 64px;
    line-height: 1.6;
}}

.features-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
}}

@media (max-width: 900px) {{
    .features-grid {{
        grid-template-columns: repeat(2, 1fr);
    }}
}}

@media (max-width: 600px) {{
    .features-grid {{
        grid-template-columns: 1fr;
    }}
}}

.feature-card {{
    padding: 32px;
    background: {('rgba(255,255,255,0.02)' if is_dark else '#ffffff')};
    border: 1px solid {('rgba(255,255,255,0.06)' if is_dark else 'rgba(0,0,0,0.06)')};
    border-radius: 20px;
    transition: all 0.3s ease;
    cursor: pointer;
    position: relative;
    overflow: hidden;
}}

.feature-card::before {{
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 2px;
    background: linear-gradient(90deg, transparent, #6366f1, transparent);
    opacity: 0;
    transition: opacity 0.3s ease;
}}

.feature-card:hover {{
    border-color: {('rgba(255,255,255,0.12)' if is_dark else 'rgba(0,0,0,0.1)')};
    transform: translateY(-4px);
    box-shadow: {('0 20px 40px rgba(0,0,0,0.3)' if is_dark else '0 20px 40px rgba(0,0,0,0.08)')};
}}

.feature-card:hover::before {{
    opacity: 1;
}}

.feature-icon {{
    width: 56px;
    height: 56px;
    border-radius: 14px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 28px;
    margin-bottom: 20px;
    transition: transform 0.3s ease;
}}

.feature-card:hover .feature-icon {{
    transform: scale(1.1);
}}

.icon-purple {{ background: linear-gradient(135deg, rgba(99,102,241,0.15), rgba(139,92,246,0.15)); }}
.icon-cyan {{ background: linear-gradient(135deg, rgba(6,182,212,0.15), rgba(59,130,246,0.15)); }}
.icon-pink {{ background: linear-gradient(135deg, rgba(244,114,182,0.15), rgba(192,132,252,0.15)); }}
.icon-green {{ background: linear-gradient(135deg, rgba(34,197,94,0.15), rgba(16,185,129,0.15)); }}
.icon-orange {{ background: linear-gradient(135deg, rgba(251,146,60,0.15), rgba(249,115,22,0.15)); }}
.icon-blue {{ background: linear-gradient(135deg, rgba(59,130,246,0.15), rgba(99,102,241,0.15)); }}

.feature-title {{
    font-size: 18px;
    font-weight: 600;
    color: {('#fafafa' if is_dark else '#09090b')};
    margin: 0 0 10px;
}}

.feature-desc {{
    font-size: 14px;
    color: {('#a1a1aa' if is_dark else '#71717a')};
    line-height: 1.6;
    margin: 0;
}}

/* ============================================
   MODE CARDS SECTION
   ============================================ */
.modes-section {{
    padding: 80px 24px 120px;
    max-width: 1000px;
    margin: 0 auto;
}}

.modes-grid {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 24px;
}}

@media (max-width: 800px) {{
    .modes-grid {{
        grid-template-columns: 1fr;
        max-width: 400px;
        margin: 0 auto;
    }}
}}

.mode-card {{
    padding: 32px;
    background: {('rgba(255,255,255,0.02)' if is_dark else '#ffffff')};
    border: 1px solid {('rgba(255,255,255,0.06)' if is_dark else 'rgba(0,0,0,0.06)')};
    border-radius: 20px;
    text-decoration: none;
    transition: all 0.3s ease;
    display: block;
    position: relative;
    overflow: hidden;
}}

.mode-card:hover {{
    border-color: {('rgba(99,102,241,0.4)' if is_dark else 'rgba(99,102,241,0.3)')};
    transform: translateY(-6px);
    box-shadow: 0 24px 48px rgba(99, 102, 241, 0.15);
}}

.mode-icon {{
    width: 64px;
    height: 64px;
    border-radius: 16px;
    background: linear-gradient(135deg, rgba(99,102,241,0.1), rgba(139,92,246,0.1));
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 32px;
    margin-bottom: 20px;
    transition: all 0.3s ease;
}}

.mode-card:hover .mode-icon {{
    transform: scale(1.1) rotate(5deg);
    background: linear-gradient(135deg, rgba(99,102,241,0.2), rgba(139,92,246,0.2));
}}

.mode-title {{
    font-size: 20px;
    font-weight: 700;
    color: {('#fafafa' if is_dark else '#09090b')};
    margin: 0 0 10px;
}}

.mode-desc {{
    font-size: 14px;
    color: {('#a1a1aa' if is_dark else '#71717a')};
    line-height: 1.6;
    margin: 0 0 20px;
}}

.mode-link {{
    font-size: 14px;
    font-weight: 600;
    color: #6366f1;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    transition: gap 0.2s ease;
}}

.mode-card:hover .mode-link {{
    gap: 10px;
}}

/* ============================================
   FOOTER
   ============================================ */
.site-footer {{
    padding: 48px 24px;
    border-top: 1px solid {('rgba(255,255,255,0.05)' if is_dark else 'rgba(0,0,0,0.05)')};
    text-align: center;
}}

.footer-content {{
    max-width: 1200px;
    margin: 0 auto;
}}

.footer-text {{
    font-size: 14px;
    color: {('#71717a' if is_dark else '#71717a')};
}}

.footer-link {{
    color: #6366f1;
    text-decoration: none;
}}

.footer-link:hover {{
    text-decoration: underline;
}}

/* ============================================
   HIDE STREAMLIT BUTTONS STYLING
   ============================================ */
.stApp .stButton > button {{
    background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%) !important;
    color: white !important;
    border: none !important;
    border-radius: 12px !important;
    padding: 14px 28px !important;
    font-weight: 600 !important;
    font-size: 15px !important;
    transition: all 0.25s ease !important;
    box-shadow: 0 4px 16px rgba(99, 102, 241, 0.3) !important;
}}

.stApp .stButton > button:hover {{
    transform: translateY(-2px) !important;
    box-shadow: 0 8px 24px rgba(99, 102, 241, 0.4) !important;
}}

/* Hide action buttons container visually but keep functional */
.nav-buttons-container {{
    position: fixed;
    bottom: -100px;
    left: 0;
    opacity: 0;
    pointer-events: none;
}}

/* Theme toggle button positioning */
.theme-btn-wrapper {{
    position: fixed;
    top: 16px;
    right: 100px;
    z-index: 1001;
}}

.theme-btn-wrapper .stButton {{
    width: auto !important;
}}

.theme-btn-wrapper .stButton > button {{
    background: transparent !important;
    border: 1px solid {('rgba(255,255,255,0.1)' if is_dark else 'rgba(0,0,0,0.1)')} !important;
    box-shadow: none !important;
    width: 44px !important;
    height: 44px !important;
    padding: 0 !important;
    border-radius: 12px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    font-size: 20px !important;
}}

.theme-btn-wrapper .stButton > button:hover {{
    background: {('rgba(255,255,255,0.06)' if is_dark else 'rgba(0,0,0,0.04)')} !important;
    border-color: {('rgba(255,255,255,0.2)' if is_dark else 'rgba(0,0,0,0.15)')} !important;
    transform: none !important;
}}
</style>
""", unsafe_allow_html=True)

# =============================================================================
# BACKGROUND ELEMENTS
# =============================================================================
st.markdown('''
<div class="bg-grid"></div>
<div class="gradient-orb orb-1"></div>
<div class="gradient-orb orb-2"></div>
<div class="gradient-orb orb-3"></div>
''', unsafe_allow_html=True)

# =============================================================================
# FIXED HEADER
# =============================================================================
version = get_version_display()

st.markdown(f'''
<header class="site-header">
    <a href="/" class="header-logo">
        <svg class="logo-svg" width="40" height="40" viewBox="0 0 40 40" fill="none" xmlns="http://www.w3.org/2000/svg">
            <defs>
                <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" style="stop-color:#6366f1"/>
                    <stop offset="50%" style="stop-color:#8b5cf6"/>
                    <stop offset="100%" style="stop-color:#ec4899"/>
                </linearGradient>
            </defs>
            <rect width="40" height="40" rx="10" fill="url(#logoGrad)"/>
            <path d="M12 28L20 12L28 28" stroke="white" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" fill="none"/>
            <circle cx="20" cy="24" r="2" fill="white"/>
            <path d="M14 18L20 8L26 18" stroke="white" stroke-width="1.5" stroke-linecap="round" opacity="0.6"/>
            <circle cx="28" cy="12" r="1.5" fill="white" opacity="0.8"/>
            <circle cx="12" cy="14" r="1" fill="white" opacity="0.6"/>
            <circle cx="30" cy="22" r="1" fill="white" opacity="0.5"/>
        </svg>
        <span class="logo-text">InstaSchool</span>
    </a>
    <nav class="header-nav">
        <a href="/Student" class="nav-item">Learn</a>
        <a href="/Create" class="nav-item">Create</a>
        <a href="/Parent" class="nav-item">Family</a>
        <a href="/Library" class="nav-item">Library</a>
    </nav>
    <div class="header-actions">
        <a href="/Create" class="cta-btn">Get Started</a>
    </div>
</header>
''', unsafe_allow_html=True)

# Theme toggle button (functional)
st.markdown('<div class="theme-btn-wrapper">', unsafe_allow_html=True)
theme_icon = "sun" if is_dark else "moon"
if st.button("☀️" if is_dark else "🌙", key="theme_toggle", help="Toggle theme"):
    ThemeManager.toggle_theme()
    st.rerun()
st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# HERO SECTION
# =============================================================================
st.markdown(f'''
<div class="page-content">
    <section class="hero">
        <div class="hero-badge">
            <span class="badge-dot"></span>
            {version}
        </div>
        <h1 class="hero-title">
            Create <span class="hero-title-gradient">AI-Powered</span><br>
            Curricula in Minutes
        </h1>
        <p class="hero-subtitle">
            Generate complete, standards-aligned K-12 curricula with AI-powered lessons,
            interactive assessments, and personalized learning paths. Built for educators and families.
        </p>
        <div class="hero-cta-group">
            <a href="/Create" class="btn-primary">Start Creating</a>
            <a href="/Student" class="btn-secondary">Explore Learning</a>
        </div>
''', unsafe_allow_html=True)

# Get dynamic stats
curricula_dir = Path("curricula")
total_curricula = len(list(curricula_dir.glob("*.json"))) if curricula_dir.exists() else 0

try:
    from services.user_service import UserService
    user_count = len(UserService().list_users())
except:
    user_count = 0

st.markdown(f'''
        <div class="stats-bar">
            <div class="stat-item">
                <div class="stat-value stat-value-accent">{total_curricula}+</div>
                <div class="stat-label">Curricula Created</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{user_count}</div>
                <div class="stat-label">Active Learners</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">K-12</div>
                <div class="stat-label">Grade Range</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">3</div>
                <div class="stat-label">AI Providers</div>
            </div>
        </div>
    </section>
''', unsafe_allow_html=True)

# =============================================================================
# FEATURES SECTION
# =============================================================================
st.markdown('''
    <section class="features-section">
        <div class="section-label">Features</div>
        <h2 class="section-title">Everything you need<br>to educate smarter</h2>
        <p class="section-subtitle">
            Powered by the latest AI models to create engaging, personalized educational content at scale.
        </p>
        <div class="features-grid">
            <div class="feature-card">
                <div class="feature-icon icon-purple">&#x1F9E0;</div>
                <h3 class="feature-title">AI Curriculum Generator</h3>
                <p class="feature-desc">Generate complete curricula with lessons, quizzes, and activities aligned to educational standards.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon icon-cyan">&#x1F3A8;</div>
                <h3 class="feature-title">AI Illustrations</h3>
                <p class="feature-desc">Create custom educational illustrations for every lesson using GPT-Image-1 technology.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon icon-pink">&#x1F393;</div>
                <h3 class="feature-title">Adaptive Learning</h3>
                <p class="feature-desc">Personalized AI tutoring that adapts to each student's pace and learning style.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon icon-green">&#x1F4CA;</div>
                <h3 class="feature-title">Progress Analytics</h3>
                <p class="feature-desc">Track learning progress with detailed analytics, streaks, and achievement badges.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon icon-orange">&#x1F4DA;</div>
                <h3 class="feature-title">Spaced Repetition</h3>
                <p class="feature-desc">SM-2 algorithm for flashcard scheduling ensures long-term knowledge retention.</p>
            </div>
            <div class="feature-card">
                <div class="feature-icon icon-blue">&#x1F4E4;</div>
                <h3 class="feature-title">Multi-Format Export</h3>
                <p class="feature-desc">Export curricula to PDF, HTML, or Markdown for offline use and sharing.</p>
            </div>
        </div>
    </section>
''', unsafe_allow_html=True)

# =============================================================================
# MODE CARDS SECTION
# =============================================================================
st.markdown('''
    <section class="modes-section">
        <div class="section-label">Get Started</div>
        <h2 class="section-title">Choose your path</h2>
        <p class="section-subtitle">
            Whether you're a student, educator, or parent, InstaSchool has the right tools for you.
        </p>
        <div class="modes-grid">
            <a href="/Student" class="mode-card">
                <div class="mode-icon">&#x1F393;</div>
                <h3 class="mode-title">Student Portal</h3>
                <p class="mode-desc">Access lessons, take quizzes, and track your progress with AI-powered tutoring.</p>
                <span class="mode-link">Start Learning <span>&#8594;</span></span>
            </a>
            <a href="/Create" class="mode-card">
                <div class="mode-icon">&#x2728;</div>
                <h3 class="mode-title">Create Curriculum</h3>
                <p class="mode-desc">Generate complete curricula with AI-powered lessons, assessments, and media.</p>
                <span class="mode-link">Create Now <span>&#8594;</span></span>
            </a>
            <a href="/Parent" class="mode-card">
                <div class="mode-icon">&#x1F468;&#x200D;&#x1F469;&#x200D;&#x1F467;</div>
                <h3 class="mode-title">Family Dashboard</h3>
                <p class="mode-desc">Monitor progress, manage profiles, and export learning materials.</p>
                <span class="mode-link">View Dashboard <span>&#8594;</span></span>
            </a>
        </div>
    </section>
''', unsafe_allow_html=True)

# =============================================================================
# FUNCTIONAL NAVIGATION BUTTONS (Hidden but functional for proper Streamlit routing)
# =============================================================================
st.markdown('<div class="nav-buttons-container">', unsafe_allow_html=True)
col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("Student", key="nav_student"):
        st.switch_page("pages/1_Student.py")
with col2:
    if st.button("Create", key="nav_create"):
        st.switch_page("pages/2_Create.py")
with col3:
    if st.button("Parent", key="nav_parent"):
        st.switch_page("pages/3_Parent.py")
with col4:
    if st.button("Library", key="nav_library"):
        st.switch_page("pages/4_Library.py")
st.markdown('</div>', unsafe_allow_html=True)

# =============================================================================
# FOOTER
# =============================================================================
st.markdown(f'''
    <footer class="site-footer">
        <div class="footer-content">
            <p class="footer-text">
                Built with <a href="https://streamlit.io" class="footer-link" target="_blank">Streamlit</a>
                and <a href="https://openai.com" class="footer-link" target="_blank">OpenAI</a>
                &nbsp;&middot;&nbsp; {version}
            </p>
        </div>
    </footer>
</div>
''', unsafe_allow_html=True)

# =============================================================================
# CLEANUP
# =============================================================================
try:
    from services.session_service import init_tempfile_cleanup
    init_tempfile_cleanup(max_age_hours=24)
except:
    pass
