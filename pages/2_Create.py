"""
Create Mode - Curriculum Generation Interface
InstaSchool multi-page app
"""
import os
import sys
import json
import time
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# Imports
from src.shared_init import (
    setup_page,
    load_config,
    get_provider_service,
    get_curriculum_service,
)
from src.state_manager import StateManager
from src.ui_components import ModernUI, ThemeManager
from src.agent_framework import OrchestratorAgent
from services.session_service import InputValidator
from src.cost_estimator import estimate_curriculum_cost

# Page config
setup_page(title="InstaSchool - Create", icon="✨")
config = load_config()
StateManager.initialize_state()

# Services (lazy-init into StateManager to avoid None defaults)
provider_service = StateManager.get_state("provider_service")
if provider_service is None:
    provider_service = get_provider_service()
    StateManager.set_state("provider_service", provider_service)

curriculum_service = StateManager.get_state("curriculum_service")
if curriculum_service is None:
    curriculum_service = get_curriculum_service()
    StateManager.set_state("curriculum_service", curriculum_service)

# --- SIDEBAR: Configuration ---
st.sidebar.markdown("## ⚙️ Settings")

# 1. Basic Config
with st.sidebar.expander("📚 **Curriculum Basics**", expanded=True):
    # Subject
    selected_subjects = st.multiselect(
        "Subject",
        config["defaults"]["subjects"],
        default=[config["defaults"]["subject"]],
        key="sb_subject"
    )
    # Validation logic
    valid_subjects = [s for s in selected_subjects if InputValidator.validate_subject(s)]
    if not valid_subjects:
        valid_subjects = [config["defaults"]["subject"]]
    subject_str = ", ".join(valid_subjects)

    # Grade
    grade = st.selectbox("Grade", config["defaults"]["grades"], index=2, key="sb_grade")

    # Style & Language
    col_a, col_b = st.columns(2)
    with col_a:
        style = st.selectbox("Style", config["defaults"]["styles"], index=0, key="sb_style")
    with col_b:
        language = st.selectbox("Language", config["defaults"]["languages"], index=0, key="sb_lang")

# 2. AI Provider
with st.sidebar.expander("🔌 **AI Model**", expanded=False):
    providers = provider_service.get_available_providers()
    current_prov = StateManager.get_state("current_provider", "openai")

    sel_prov = st.selectbox("Provider", providers,
                           index=providers.index(current_prov) if current_prov in providers else 0,
                           key="sb_provider")

    if sel_prov != current_prov:
        StateManager.set_state("current_provider", sel_prov)
        # Reset client on change
        StateManager.set_state("client", provider_service.get_client(sel_prov))
        st.rerun()

    # Model Select
    models = provider_service.get_text_models(sel_prov)
    main_model = st.selectbox("Orchestrator", models, index=0, key="sb_model_main")
    worker_model = st.selectbox("Worker", models, index=0, key="sb_model_worker")

    # Image Model (images always use OpenAI backend)
    available_image_models = provider_service.get_image_models("openai")
    default_image_model = config["defaults"].get("image_model", "gpt-image-1")

    if available_image_models:
        if default_image_model not in available_image_models:
            default_image_model = available_image_models[0]

        image_model = st.selectbox(
            "Image Model (OpenAI)",
            options=available_image_models,
            index=available_image_models.index(default_image_model),
            help="Images always use OpenAI; gpt-image-1 is recommended.",
            key="sb_image_model",
        )
    else:
        st.warning("⚠️ OpenAI API key required for image generation")
        image_model = default_image_model

# 3. Content Depth
with st.sidebar.expander("📝 **Content Depth**", expanded=False):
    media_richness = st.slider("Media Richness", 0, 5, 2, help="0=Text Only, 5=Full Images/Charts")

    st.caption("Components")
    c1, c2 = st.columns(2)
    with c1:
        inc_quiz = st.checkbox("Quizzes", True)
        inc_res = st.checkbox("Resources", True)
    with c2:
        inc_sum = st.checkbox("Summaries", True)
        inc_keys = st.checkbox("Key Points", True)

# --- MAIN PAGE ---
st.markdown("# ✨ Create Curriculum")

# Tabs for workflow
tab_gen, tab_view = st.tabs(["🚀 Generate", "📂 Library"])

# === TAB 1: GENERATE ===
with tab_gen:
    is_generating = StateManager.get_state("generating", False)

    # Cost Estimation
    est_cost_data = estimate_curriculum_cost(
        orchestrator_model=main_model,
        worker_model=worker_model,
        num_units=len(valid_subjects) * 3,  # Approx topics
        include_quizzes=inc_quiz,
        include_summary=inc_sum,
        include_resources=inc_res,
    )
    est_cost = (
        est_cost_data.get("total", 0.0)
        if isinstance(est_cost_data, dict)
        else float(est_cost_data or 0.0)
    )

    if est_cost > 0.5:
        st.warning(f"💰 Estimated cost: ${est_cost:.2f}")
    else:
        st.caption(f"💰 Est. cost: ${est_cost:.2f}")

    # Extra Guidelines
    extra_instructions = st.text_area(
        "🎯 specific focus or learning goals?",
        placeholder="e.g., Focus on real-world examples involving space travel...",
        help="These instructions will guide the Orchestrator."
    )

    if is_generating:
        st.info("⚙️ Curriculum generation is currently in progress.")
        if st.button("❌ Cancel Generation", type="secondary", use_container_width=True):
            StateManager.update_state("generating", False)
            st.info("Generation cancellation requested. The process will stop at the next safe point.")

    # Generation Button (only when not already generating)
    if (not is_generating) and st.button("🚀 Start Generation", type="primary", use_container_width=True):
        if not valid_subjects:
            st.error("Please select at least one subject.")
            st.stop()

        # Update Config
        run_config = config.copy()
        run_config["defaults"].update({
            "media_richness": media_richness,
            "image_model": image_model,
            "include_quizzes": inc_quiz,
            "include_summary": inc_sum,
            "include_resources": inc_res,
            "include_keypoints": inc_keys
        })

        # Initialize Agent
        client = StateManager.get_state("client")
        if not client:
            client = provider_service.get_client(sel_prov)
            StateManager.set_state("client", client)

        orchestrator = OrchestratorAgent(client, main_model, worker_model)

        # Progress UI
        progress_bar = st.progress(0, text="Initializing agents...")
        status_area = st.empty()

        start_time = time.time()
        StateManager.update_state("generating", True)

        try:
            # Generate!
            with st.spinner("🤖 Orchestrating your curriculum... (This allows parallel processing)"):
                final_curriculum = orchestrator.create_curriculum(
                    subject=subject_str,
                    grade=grade,
                    style=style,
                    language=language,
                    extra=extra_instructions,
                    config=run_config,
                )

            # Save
            if final_curriculum and final_curriculum.get("units"):
                filename = f"{subject_str.replace(', ', '_')}_{grade}_{int(time.time())}.json"
                save_path = Path("curricula") / filename
                save_path.parent.mkdir(exist_ok=True)

                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(final_curriculum, f, indent=2, ensure_ascii=False)

                duration = time.time() - start_time
                progress_bar.progress(100, text=f"Done in {duration:.1f}s!")
                st.success(f"✅ Curriculum saved to {filename}")
                st.balloons()

                # Session State Update
                st.session_state['last_generated'] = filename

                # Option to switch view
                if st.button("👀 View Now"):
                    st.switch_page("pages/1_Student.py")
            else:
                st.error("Generation returned empty results. Please check API keys.")

        except Exception as e:
            st.error(f"Generation failed: {str(e)}")
            st.exception(e)
        finally:
            StateManager.update_state("generating", False)

# === TAB 2: LIBRARY ===
with tab_view:
    curricula_dir = Path("curricula")
    if curricula_dir.exists():
        files = sorted(list(curricula_dir.glob("*.json")), key=lambda x: x.stat().st_mtime, reverse=True)

        for f in files:
            with st.expander(f"📄 {f.name} ({time.ctime(f.stat().st_mtime)})"):
                try:
                    data = json.loads(f.read_text(encoding='utf-8'))
                    st.json(data.get('meta', {}), expanded=False)
                    if st.button("Delete", key=f"del_{f.name}"):
                        f.unlink()
                        st.rerun()
                except:
                    st.error("Invalid JSON")
    else:
        st.info("No curricula found.")
