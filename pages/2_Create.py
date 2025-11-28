"""
Create Mode - Curriculum Generation Interface
InstaSchool multi-page app

NOTE: This is a transitional page. Full Create mode functionality
is still in main.py. This page provides the core sidebar settings
and redirects to main.py for generation.
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

import streamlit as st
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Import shared initialization
from src.shared_init import (
    setup_page,
    init_session_state,
    load_config,
    get_openai_client,
    get_provider_service,
    get_curriculum_service,
)
from src.state_manager import StateManager
from src.ui_components import ModernUI, ThemeManager
from services.session_service import InputValidator
from services.provider_service import AIProviderService
from src.cost_estimator import estimate_curriculum_cost

# Page config
setup_page(title="InstaSchool - Create", icon="✨")

# Load config
config = load_config()

# Initialize state
StateManager.initialize_state()

# Get provider service
if not StateManager.get_state("provider_service"):
    StateManager.set_state("provider_service", get_provider_service())

provider_service = StateManager.get_state("provider_service")

# --- Sidebar Configuration ---
st.sidebar.markdown("## ⚙️ Curriculum Settings")
st.sidebar.markdown("---")

# Basic Settings Section
with st.sidebar.expander("📚 **Basic Settings**", expanded=True):
    # Subject selection
    selected_subjects = st.multiselect(
        "Subject",
        config["defaults"]["subjects"],
        default=[config["defaults"]["subject"]],
        key="sidebar_subjects"
    )
    if selected_subjects:
        valid_subjects = [s for s in selected_subjects if InputValidator.validate_subject(s)]
        if valid_subjects != selected_subjects:
            st.warning("Some subjects were invalid and removed.")
        subject_str = ", ".join(valid_subjects) if valid_subjects else config["defaults"]["subject"]
    else:
        subject_str = config["defaults"]["subject"]

    # Grade level selection
    grade = st.selectbox(
        "Grade Level",
        config["defaults"]["grades"],
        index=config["defaults"]["grades"].index(config["defaults"]["grade"])
        if config["defaults"]["grade"] in config["defaults"]["grades"] else 0,
        key="sidebar_grade"
    )

    if not InputValidator.validate_grade(grade):
        st.error("Invalid grade selection. Using default.")
        grade = config["defaults"]["grade"]

    # Teaching style selection
    lesson_style = st.selectbox(
        "Style",
        config["defaults"]["styles"],
        index=config["defaults"]["styles"].index(config["defaults"]["style"])
        if config["defaults"]["style"] in config["defaults"]["styles"] else 0,
        key="sidebar_style"
    )

    # Language selection
    language = st.selectbox(
        "Language",
        config["defaults"]["languages"],
        index=config["defaults"]["languages"].index(config["defaults"]["language"])
        if config["defaults"]["language"] in config["defaults"]["languages"] else 0,
        key="sidebar_language"
    )

# AI Provider Selection Section
with st.sidebar.expander("🔌 **AI Provider**", expanded=False):
    available_providers = provider_service.get_available_providers()

    provider_names = {
        "openai": "OpenAI (Paid)",
        "kimi": "Kimi K2 (Free)",
    }

    st.caption(f"Available: {', '.join(available_providers)}")

    current_provider = StateManager.get_state("current_provider", "openai")

    selected_provider = st.selectbox(
        "Select AI Provider",
        options=available_providers,
        format_func=lambda x: provider_names.get(x, x),
        index=available_providers.index(current_provider) if current_provider in available_providers else 0,
        help="Choose your AI provider. Kimi K2 is free! OpenAI costs money.",
        key="provider_selector"
    )

    if selected_provider != current_provider:
        StateManager.set_state("current_provider", selected_provider)
        new_client = provider_service.get_client(selected_provider)
        StateManager.set_state("client", new_client)
        st.rerun()

    if selected_provider == "kimi":
        st.success("✓ Using Kimi K2 (Free tier)")
    elif selected_provider == "openai":
        st.info("✓ Using OpenAI")

# AI Model Settings
with st.sidebar.expander("🤖 **AI Model Settings**", expanded=False):
    current_provider = StateManager.get_state("current_provider", "openai")
    available_text_models = provider_service.get_text_models(current_provider)

    provider_display = provider_names.get(current_provider, current_provider)
    st.caption(f"📍 Showing models for: **{provider_display}**")

    if not available_text_models:
        st.warning(f"No models defined for {provider_display}")
        available_text_models = ["default"]

    # Main model selection
    default_text_model = provider_service.get_model_for_task(current_provider, "main")
    if default_text_model not in available_text_models and available_text_models:
        default_text_model = available_text_models[0]

    text_model = st.selectbox(
        "Main AI Model (Orchestrator)",
        options=available_text_models,
        index=available_text_models.index(default_text_model) if default_text_model in available_text_models else 0,
        key="main_model_select"
    )

    # Worker model selection
    default_worker_model = provider_service.get_model_for_task(current_provider, "worker")
    if default_worker_model not in available_text_models and available_text_models:
        default_worker_model = available_text_models[0]

    worker_model = st.selectbox(
        "Worker AI Model (Content)",
        options=available_text_models,
        index=available_text_models.index(default_worker_model) if default_worker_model in available_text_models else 0,
        key="worker_model_select"
    )

# Content Settings Section
with st.sidebar.expander("📝 **Content Settings**", expanded=False):
    media_richness = st.slider(
        "Media Richness",
        min_value=0,
        max_value=5,
        value=config["defaults"]["media_richness"],
        help="0: Text only, 5: Rich media"
    )

    st.markdown("**Include Additional Components:**")
    include_quizzes = st.checkbox("Include Quizzes", value=config["defaults"]["include_quizzes"])
    include_summary = st.checkbox("Include Summary", value=config["defaults"]["include_summary"])
    include_resources = st.checkbox("Include Further Resources", value=config["defaults"]["include_resources"])
    include_keypoints = st.checkbox("Include Learning Points", value=config["defaults"]["include_keypoints"])

# Theme toggle
st.sidebar.markdown("---")
st.sidebar.markdown("**Preferences**")
ThemeManager.get_theme_toggle()

# --- Main Area ---
st.markdown("# ✨ Create Curriculum")

# Show current settings
col1, col2, col3 = st.columns(3)
with col1:
    total_curricula = len([f for f in os.listdir("curricula") if f.endswith('.json')]) if os.path.exists("curricula") else 0
    ModernUI.stats_card(str(total_curricula), "Total Curricula", "📚")

with col2:
    settings_summary = f"{subject_str} • {grade}"
    ModernUI.stats_card(settings_summary, "Current Settings", "⚙️")

with col3:
    ModernUI.stats_card(selected_provider.title(), "AI Provider", "🤖")

st.markdown("---")

# Transitional notice
st.info("""
**🚧 Multi-Page Transition**

The Create mode is being migrated to this page. For now, please use **main.py**
to access full curriculum generation functionality:

```bash
streamlit run main.py
```

This page provides:
- ✅ Sidebar configuration (working)
- ✅ Provider/model selection (working)
- 🔄 Generation (coming soon)
- 🔄 View & Edit (coming soon)
- 🔄 Export (coming soon)
""")

# Quick generation form
st.markdown("### 🚀 Quick Generate")
st.markdown("Configure settings in the sidebar, then generate your curriculum.")

custom_prompt = st.text_area(
    "Optional: Specific Guidelines or Focus",
    value=config["defaults"]["extra"],
    key="extra_guidelines",
    help="Add specific instructions for the AI"
)

if st.button("🚀 Generate Curriculum", type="primary", use_container_width=True):
    st.warning("Full generation is available in main.py. Run: `streamlit run main.py`")
    st.info(f"""
    **Your settings are saved:**
    - Subject: {subject_str}
    - Grade: {grade}
    - Style: {lesson_style}
    - Provider: {selected_provider}
    - Model: {text_model}
    """)

# Show existing curricula
st.markdown("---")
st.markdown("### 📚 Existing Curricula")

curricula_dir = Path("curricula")
if curricula_dir.exists():
    json_files = list(curricula_dir.glob("*.json"))
    if json_files:
        for json_file in sorted(json_files, key=lambda x: x.stat().st_mtime, reverse=True)[:5]:
            try:
                import json
                with open(json_file) as f:
                    data = json.load(f)
                meta = data.get('meta', {})
                subject = meta.get('subject', data.get('subject', 'Unknown'))
                grade_level = meta.get('grade', data.get('grade', ''))
                units = len(data.get('units', []))
                display_title = f"{subject} - Grade {grade_level}" if grade_level else subject

                with st.expander(f"📖 {display_title}"):
                    st.write(f"**Units:** {units}")
                    st.write(f"**File:** {json_file.name}")
            except Exception:
                pass
    else:
        st.info("No curricula created yet.")
else:
    st.info("No curricula created yet.")
