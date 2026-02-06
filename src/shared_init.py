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

matplotlib.use("Agg")

import streamlit as st
import yaml
import copy
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def _apply_streamlit_secrets_to_env() -> None:
    """Populate common env vars from Streamlit secrets when present.

    Streamlit Cloud exposes secrets via `st.secrets`, not necessarily as process
    environment variables. This keeps the rest of the codebase (which uses
    `os.getenv`) working in both local `.env` and Cloud secrets setups.
    """
    try:
        secrets = getattr(st, "secrets", None)
        if not secrets:
            return

        def _maybe_set_env(env_key: str, value: Optional[str]) -> None:
            if not env_key or not value:
                return
            if os.getenv(env_key):
                return
            os.environ[env_key] = str(value).strip()

        # Common top-level secrets
        for env_key in [
            "OPENAI_API_KEY",
            "OPENAI_ORG_ID",
            "KIMI_API_KEY",
            "MOONSHOT_API_KEY",
            "DEEPSEEK_API_KEY",
            "APP_PASSWORD",
        ]:
            try:
                _maybe_set_env(env_key, secrets.get(env_key))
            except Exception:
                pass

        # Optional structured secrets
        try:
            openai_section = secrets.get("openai") or {}
            if isinstance(openai_section, dict):
                _maybe_set_env("OPENAI_API_KEY", openai_section.get("api_key"))
                _maybe_set_env("OPENAI_ORG_ID", openai_section.get("org_id"))
        except Exception:
            pass

        try:
            kimi_section = secrets.get("kimi") or secrets.get("moonshot") or {}
            if isinstance(kimi_section, dict):
                _maybe_set_env("KIMI_API_KEY", kimi_section.get("api_key"))
                _maybe_set_env("MOONSHOT_API_KEY", kimi_section.get("api_key"))
        except Exception:
            pass

        try:
            deepseek_section = secrets.get("deepseek") or {}
            if isinstance(deepseek_section, dict):
                _maybe_set_env("DEEPSEEK_API_KEY", deepseek_section.get("api_key"))
        except Exception:
            pass
    except Exception:
        return


_apply_streamlit_secrets_to_env()


@st.cache_data(ttl=300)
def load_config(path: str = "config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file with caching"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
            # Treat config as immutable: callers should not mutate cached objects.
            return copy.deepcopy(cfg)
    except Exception as e:
        st.error(f"Failed to load config: {e}")
        return {}


@st.cache_resource
def _build_openai_client(api_key: str, org_id: Optional[str]):
    """Build and cache OpenAI client for a specific credential tuple."""
    from openai import OpenAI

    return OpenAI(api_key=api_key, organization=org_id)


def get_openai_client():
    """Get OpenAI client.

    Do not cache the missing-key state; once a key is provided during the same
    process, client initialization should recover without a manual cache clear.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    org_id = os.getenv("OPENAI_ORG_ID")
    api_key = str(api_key).strip() if api_key is not None else ""
    org_id = str(org_id).strip() if org_id is not None else None
    if not api_key:
        return None
    return _build_openai_client(api_key, org_id)


@st.cache_resource
def _build_provider_service(config: Dict[str, Any]):
    """Build and cache provider service per effective config."""
    from services.provider_service import AIProviderService

    return AIProviderService(config)


def get_provider_service():
    """Get AI Provider Service."""
    config = load_config()
    return _build_provider_service(config)


@st.cache_resource
def _build_curriculum_service(client, config: Dict[str, Any]):
    """Build and cache curriculum service for a specific client/config pair."""
    from services.curriculum_service import CurriculumService

    return CurriculumService(client, config)


def get_curriculum_service():
    """Get Curriculum Service."""
    config = load_config()
    client = get_openai_client()
    if client is None:
        return None
    return _build_curriculum_service(client, config)


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
        "authenticated": False,
        "current_user": None,
        "app_mode": "student",
        "curriculum": None,
        "theme": "light",
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

    if st.session_state.get("authenticated", False):
        return True

    # Show login form
    st.markdown("## 🔐 Login Required")
    password = st.text_input("Password", type="password", key="login_password")

    if st.button("Login"):
        if password == app_password:
            st.session_state["authenticated"] = True
            st.rerun()
        else:
            st.error("Invalid password")

    return False


def setup_page(title: str = "InstaSchool", icon: str = ":material/school:", layout: str = "wide"):
    """Common page setup with logo, navigation, and session state."""
    st.set_page_config(
        page_title=title, page_icon=icon, layout=layout, initial_sidebar_state="auto"
    )

    # Ensure process-wide temp file cleanup
    try:
        from services.session_service import init_tempfile_cleanup
        init_tempfile_cleanup(max_age_hours=24)
    except Exception:
        pass

    # Logo (appears in sidebar header automatically)
    logo_path = Path("static/logo_wide.svg")
    icon_path = Path("static/logo.svg")
    if logo_path.exists() and icon_path.exists():
        st.logo(str(logo_path), icon_image=str(icon_path), size="large")

    # Initialize session state
    init_session_state()

    # Sidebar navigation with Material icons
    with st.sidebar:
        st.page_link("main.py", label="Home", icon=":material/home:")
        st.page_link("pages/1_Student.py", label="Student", icon=":material/school:")
        st.page_link("pages/2_Create.py", label="Create", icon=":material/auto_awesome:")
        st.page_link("pages/3_Parent.py", label="Family", icon=":material/family_restroom:")
        st.page_link("pages/4_Library.py", label="Library", icon=":material/library_books:")


def get_version_display() -> str:
    """Get version string for display"""
    try:
        from version import get_version_display as gvd

        return gvd()
    except:
        return "v1.7.0"
