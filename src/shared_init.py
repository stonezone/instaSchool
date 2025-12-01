"""
Shared initialization for InstaSchool multi-page app.
Contains all common setup, config loading, and service initialization.
"""

import os
import sys

# NOTE: Module cache cleanup is handled at the page level (pages/*.py)
# Each page clears stale modules before importing shared_init
# This prevents shared_init from deleting itself during import

import matplotlib
matplotlib.use('Agg')

import streamlit as st
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


@st.cache_data(ttl=300)
def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file with caching"""
    try:
        with open(path, "r", encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        st.error(f"Failed to load config: {e}")
        return {}


@st.cache_resource
def get_openai_client():
    """Get cached OpenAI client"""
    from openai import OpenAI
    api_key = os.getenv("OPENAI_API_KEY")
    org_id = os.getenv("OPENAI_ORG_ID")
    if not api_key:
        return None
    return OpenAI(api_key=api_key, organization=org_id)


@st.cache_resource
def get_provider_service():
    """Get cached AI Provider Service"""
    from services.provider_service import AIProviderService
    config = load_config()
    return AIProviderService(config)


@st.cache_resource
def get_curriculum_service():
    """Get cached Curriculum Service"""
    from services.curriculum_service import CurriculumService
    config = load_config()
    client = get_openai_client()
    if client is None:
        return None
    return CurriculumService(client, config)


@st.cache_resource
def get_database_service():
    """Get cached Database Service"""
    from services.database_service import DatabaseService
    return DatabaseService()


@st.cache_resource
def get_user_service():
    """Get cached User Service"""
    from services.user_service import UserService
    return UserService()


def init_session_state():
    """Initialize all session state variables"""
    from src.state_manager import StateManager

    defaults = {
        'authenticated': False,
        'current_user': None,
        'app_mode': 'student',
        'curriculum': None,
        'theme': 'light',
    }

    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def check_authentication() -> bool:
    """Check if user is authenticated"""
    app_password = os.getenv("APP_PASSWORD")

    # No password set = always authenticated
    if not app_password:
        return True

    if st.session_state.get('authenticated', False):
        return True

    # Show login form
    st.markdown("## 🔐 Login Required")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login"):
        if password == app_password:
            st.session_state['authenticated'] = True
            st.rerun()
        else:
            st.error("Invalid password")

    return False


def setup_page(title: str = "InstaSchool", icon: str = "🎓", layout: str = "wide"):
    """Common page setup"""
    st.set_page_config(
        page_title=title,
        page_icon=icon,
        layout=layout,
        initial_sidebar_state="expanded"
    )

    # Load CSS
    css_path = Path("static/css/design_system.css")
    if css_path.exists():
        with open(css_path, 'r') as f:
            st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

    # Initialize session state
    init_session_state()


def get_version_display() -> str:
    """Get version string for display"""
    try:
        from version import get_version_display as gvd
        return gvd()
    except:
        return "v1.7.0"
