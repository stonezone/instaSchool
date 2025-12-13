"""
Create Mode - Curriculum Generation Interface
InstaSchool multi-page app
"""
import os
import sys
import copy
import json
import html
import time
import threading
import concurrent.futures
import streamlit as st
from pathlib import Path
from dotenv import load_dotenv
from typing import Any, Dict

# NOTE: Module cleanup removed - causes KeyError crashes on Python 3.13/Streamlit Cloud
# The previous approach of clearing sys.modules broke nested imports

load_dotenv()

# Imports
from src.shared_init import (
    setup_page,
    load_config,
    get_provider_service,
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

# --- SIDEBAR: Configuration ---
st.sidebar.markdown("## ⚙️ Settings")

# 1. Basic Config
with st.sidebar.expander("Curriculum Basics", expanded=True):
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
with st.sidebar.expander("AI Model Settings", expanded=False):
    # Extra safety: ensure provider_service is initialized before use
    if provider_service is None:
        provider_service = get_provider_service()
        StateManager.set_state("provider_service", provider_service)

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
    default_main = config["defaults"].get("text_model", "gpt-5-nano")
    default_worker = config["defaults"].get("worker_model", "gpt-5-nano")
    
    # Find index of default model, fallback to 0 if not found
    main_idx = models.index(default_main) if default_main in models else 0
    worker_idx = models.index(default_worker) if default_worker in models else 0
    
    main_model = st.selectbox("Orchestrator", models, index=main_idx, key="sb_model_main")
    worker_model = st.selectbox("Worker", models, index=worker_idx, key="sb_model_worker")

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
with st.sidebar.expander("Content Options", expanded=False):
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
st.caption("Tip: Settings live in the sidebar. On mobile, tap the ☰ button to open it.")

# Tabs for workflow
tab_gen, tab_view = st.tabs(["🚀 Generate", "📂 Library"])

# === TAB 1: GENERATE ===
with tab_gen:
    def _is_lock(obj: Any) -> bool:
        return hasattr(obj, "acquire") and hasattr(obj, "release")

    def _get_or_create_generation_executor() -> concurrent.futures.ThreadPoolExecutor:
        executor = StateManager.get_state("generation_executor")
        if executor is None:
            executor = concurrent.futures.ThreadPoolExecutor(
                max_workers=1, thread_name_prefix="instaschool_generation"
            )
            StateManager.set_state("generation_executor", executor)
        return executor

    def _request_cancel_generation() -> None:
        cancel_event = StateManager.get_state("generation_cancel_event")
        if isinstance(cancel_event, threading.Event):
            cancel_event.set()

        progress_state = StateManager.get_state("generation_progress_state")
        progress_lock = StateManager.get_state("generation_progress_lock")
        if isinstance(progress_state, dict) and _is_lock(progress_lock):
            with progress_lock:
                progress_state["cancel_requested"] = True
                progress_state["message"] = "Cancellation requested — stopping at next safe point…"
                progress_state["updated_at"] = time.time()

    def _finalize_generation_job() -> bool:
        future = StateManager.get_state("generation_future")
        if future is None:
            return False
        if not getattr(future, "done", lambda: True)():
            return False

        params = StateManager.get_state("generation_params", {}) or {}
        subject_for_file = params.get("subject_str", subject_str)
        grade_for_file = params.get("grade", grade)

        try:
            final_curriculum = future.result()
            cancelled = bool(
                isinstance(final_curriculum, dict)
                and final_curriculum.get("meta", {}).get("cancelled")
            )

            if final_curriculum and isinstance(final_curriculum, dict) and final_curriculum.get("units"):
                suffix = "_partial" if cancelled else ""
                filename = f"{subject_for_file.replace(', ', '_')}_{grade_for_file}_{int(time.time())}{suffix}.json"
                save_path = Path("curricula") / filename
                save_path.parent.mkdir(exist_ok=True)

                with open(save_path, "w", encoding="utf-8") as f:
                    json.dump(final_curriculum, f, indent=2, ensure_ascii=False)

                StateManager.set_state("generation_last_filename", filename)
                StateManager.set_state("generation_last_error", None)
                st.session_state["last_generated"] = filename
                StateManager.set_state("preferred_curriculum_file", filename)
            else:
                StateManager.set_state(
                    "generation_last_error",
                    "Generation returned empty results. Please check API keys/settings.",
                )
        except Exception as e:
            StateManager.set_state("generation_last_error", str(e))
        finally:
            StateManager.set_state("generating", False)
            StateManager.set_state("generation_future", None)
            StateManager.set_state("generation_cancel_event", None)
            StateManager.set_state("generation_progress_state", None)
            StateManager.set_state("generation_progress_lock", None)
            StateManager.set_state("generation_started_at", None)
        return True

    def _run_generation_background(
        *,
        client: Any,
        main_model: str,
        worker_model: str,
        subject_str: str,
        grade: str,
        style: str,
        language: str,
        extra_instructions: str,
        run_config: Dict[str, Any],
        cancel_event: threading.Event,
        progress_state: Dict[str, Any],
        progress_lock: threading.Lock,
    ) -> Dict[str, Any]:
        orchestrator = OrchestratorAgent(client, main_model, worker_model)

        def _push_log(line: str) -> None:
            if not line:
                return
            logs = progress_state.get("log")
            if not isinstance(logs, list):
                logs = []
                progress_state["log"] = logs
            logs.append(line)
            if len(logs) > 200:
                del logs[:-200]

        # Safe, opt-in LLM trace hook (prompt/response excerpts) for the UI feed.
        try:
            from src.core.types import set_trace_hook
        except Exception:
            set_trace_hook = None  # type: ignore[assignment]

        def trace_hook(evt: Dict[str, Any]) -> None:
            with progress_lock:
                if not progress_state.get("trace_enabled"):
                    return

                ts = time.strftime("%H:%M:%S")
                agent = evt.get("agent", "Agent")
                model = evt.get("model", "?")
                kind = evt.get("type", "?")
                include_more = bool(progress_state.get("trace_include_content"))

                if kind == "llm.request":
                    msgs = evt.get("messages") or []
                    if not isinstance(msgs, list):
                        msgs = []
                    if not include_more:
                        msgs = msgs[-2:]
                    _push_log(f"[{ts}] → {agent} ({model})")
                    for m in msgs:
                        role = m.get("role")
                        content = m.get("content", "")
                        if role and content:
                            _push_log(f"[{ts}]   {role}: {content}")
                elif kind == "llm.response":
                    content = evt.get("content", "")
                    usage = evt.get("usage") or {}
                    tok = usage.get("total_tokens") if isinstance(usage, dict) else None
                    suffix = f" ({tok} tok)" if tok is not None else ""
                    if content:
                        _push_log(f"[{ts}] ← {agent} ({model}){suffix}: {content}")
                    else:
                        _push_log(f"[{ts}] ← {agent} ({model}){suffix}")
                elif kind == "llm.error":
                    err_t = evt.get("error_type", "Error")
                    msg = evt.get("message", "")
                    _push_log(f"[{ts}] ! {agent} ({model}) {err_t}: {msg}")
                else:
                    _push_log(f"[{ts}] {kind}: {evt}")

        if set_trace_hook is not None:
            set_trace_hook(trace_hook, max_chars=900)

        def progress_callback(event: str, data: Dict[str, Any]) -> None:
            with progress_lock:
                progress_state["event"] = event
                progress_state["data"] = data or {}
                progress_state["updated_at"] = time.time()

                total = data.get("total_topics")
                done = data.get("topics_completed")
                if isinstance(total, int) and total > 0 and isinstance(done, int):
                    progress_state["percent"] = int((done / total) * 90) + 5
                elif event in {"planning_start"}:
                    progress_state["percent"] = 0
                elif event in {"planning_done", "outline_start"}:
                    progress_state["percent"] = 3
                elif event in {"outline_done"}:
                    progress_state["percent"] = 5
                elif event in {"refine_start"}:
                    progress_state["percent"] = 95
                elif event in {"done"}:
                    progress_state["percent"] = 100

                # Human-friendly message
                if event == "planning_start":
                    progress_state["message"] = "Planning curriculum…"
                elif event == "outline_start":
                    progress_state["message"] = "Generating outline…"
                elif event == "outline_done":
                    progress_state["message"] = f"Outline ready — {data.get('total_topics', '?')} topics"
                elif event == "topic_start":
                    idx = data.get("topic_index", 0) + 1
                    total_topics = data.get("total_topics", "?")
                    title = data.get("topic_title", "")
                    progress_state["message"] = f"Building unit {idx}/{total_topics}: {title}"
                elif event == "topic_done":
                    done_topics = data.get("topics_completed", 0)
                    total_topics = data.get("total_topics", "?")
                    progress_state["message"] = f"Completed {done_topics}/{total_topics} units…"
                elif event == "refine_start":
                    progress_state["message"] = "Final refinement…"
                elif event == "cancelled":
                    progress_state["message"] = "Cancelled — wrapping up…"
                elif event == "done":
                    progress_state["message"] = "Done!"

                # Append to live feed log (for UI transparency)
                ts = time.strftime("%H:%M:%S")
                msg = progress_state.get("message")
                if isinstance(msg, str) and msg:
                    _push_log(f"[{ts}] {msg}")
                else:
                    _push_log(f"[{ts}] {event}: {data}")

        return orchestrator.create_curriculum(
            subject=subject_str,
            grade=grade,
            style=style,
            language=language,
            extra=extra_instructions,
            config=run_config,
            cancellation_event=cancel_event,
            progress_callback=progress_callback,
        )

    gen_future = StateManager.get_state("generation_future")
    is_generating = bool(gen_future is not None and not gen_future.done())
    if StateManager.get_state("generating", False) != is_generating:
        StateManager.set_state("generating", is_generating)

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

    # Show last generation outcome (if any)
    last_err = StateManager.get_state("generation_last_error")
    last_file = StateManager.get_state("generation_last_filename")
    if last_err:
        st.error(f"Generation failed: {last_err}")
    elif last_file:
        st.success(f"✅ Curriculum saved to {last_file}")
        if st.button("👀 View Now", use_container_width=True):
            st.switch_page("pages/1_Student.py")

    if is_generating:
        st.info("⚙️ Curriculum generation is currently in progress.")

        @st.fragment(run_every="1s")
        def _generation_status_fragment():
            if _finalize_generation_job():
                st.rerun()

            future = StateManager.get_state("generation_future")
            if future is None:
                return

            progress_state = StateManager.get_state("generation_progress_state") or {}
            progress_lock = StateManager.get_state("generation_progress_lock")

            snapshot: Dict[str, Any]
            if isinstance(progress_state, dict) and _is_lock(progress_lock):
                with progress_lock:
                    snapshot = dict(progress_state)
            else:
                snapshot = dict(progress_state) if isinstance(progress_state, dict) else {}

            percent = int(snapshot.get("percent", 0) or 0)
            msg = snapshot.get("message", "Working…")

            started_at = StateManager.get_state("generation_started_at")
            elapsed = (time.time() - started_at) if isinstance(started_at, (int, float)) else None
            if elapsed is not None:
                st.caption(f"⏱️ Elapsed: {elapsed:.0f}s")

            # Always show full status text (progress bar text can truncate on mobile)
            if msg:
                st.markdown(
                    f'<div class="status-line">{html.escape(str(msg))}</div>',
                    unsafe_allow_html=True,
                )

            st.progress(percent)

            # Live feed ("Matrix"-style) so users can see what's happening.
            show_feed = st.toggle(
                "Show live generation feed",
                value=True,
                key="show_generation_feed",
                help="Shows a running log of the generation phases (and unit titles).",
            )
            capture_trace = st.toggle(
                "Capture model prompts/responses",
                value=bool(snapshot.get("trace_enabled")),
                key="capture_api_trace",
                help="Adds sanitized prompt/response excerpts to the live feed.",
            )
            trace_more = st.toggle(
                "Verbose trace (more lines per request)",
                value=bool(snapshot.get("trace_include_content")),
                key="capture_api_trace_verbose",
                disabled=not capture_trace,
            )
            if isinstance(progress_state, dict) and _is_lock(progress_lock):
                with progress_lock:
                    progress_state["trace_enabled"] = bool(capture_trace)
                    progress_state["trace_include_content"] = bool(trace_more)
            if show_feed:
                logs = snapshot.get("log", [])
                if isinstance(logs, list) and logs:
                    tail = logs[-24:]
                    pre = html.escape("\n".join(str(x) for x in tail))
                    st.markdown(
                        f'<div class="matrix-terminal"><pre>{pre}</pre></div>',
                        unsafe_allow_html=True,
                    )
                else:
                    st.caption("Waiting for the first model response…")

            cancel_event = StateManager.get_state("generation_cancel_event")
            cancel_requested = bool(snapshot.get("cancel_requested"))
            if cancel_requested:
                st.warning("Cancellation requested. Waiting for a safe stop point…")
            elif isinstance(cancel_event, threading.Event):
                if st.button("❌ Cancel Generation", type="secondary", use_container_width=True):
                    _request_cancel_generation()

        _generation_status_fragment()

    # Generation Button (only when not already generating)
    if (not is_generating) and st.button("🚀 Start Generation", type="primary", use_container_width=True):
        if not valid_subjects:
            st.error("Please select at least one subject.")
            st.stop()

        # Update Config
        run_config = copy.deepcopy(config)
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

        # Reset last outcome state
        StateManager.set_state("generation_last_error", None)
        StateManager.set_state("generation_last_filename", None)

        # Prepare cancellation + progress tracking objects
        cancel_event = threading.Event()
        progress_state: Dict[str, Any] = {
            "percent": 0,
            "message": "Starting…",
            "event": None,
            "data": {},
            "log": [],
            "trace_enabled": False,
            "trace_include_content": False,
            "cancel_requested": False,
            "updated_at": time.time(),
        }
        progress_lock = threading.Lock()

        # Persist run params (used for filename + completion messaging)
        StateManager.set_state(
            "generation_params",
            {
                "subject_str": subject_str,
                "grade": grade,
                "style": style,
                "language": language,
                "extra": extra_instructions,
            },
        )

        executor = _get_or_create_generation_executor()
        future = executor.submit(
            _run_generation_background,
            client=client,
            main_model=main_model,
            worker_model=worker_model,
            subject_str=subject_str,
            grade=grade,
            style=style,
            language=language,
            extra_instructions=extra_instructions,
            run_config=run_config,
            cancel_event=cancel_event,
            progress_state=progress_state,
            progress_lock=progress_lock,
        )

        StateManager.set_state("generation_future", future)
        StateManager.set_state("generation_cancel_event", cancel_event)
        StateManager.set_state("generation_progress_state", progress_state)
        StateManager.set_state("generation_progress_lock", progress_lock)
        StateManager.set_state("generation_started_at", time.time())
        StateManager.set_state("generating", True)
        st.rerun()

# === TAB 2: LIBRARY ===
with tab_view:
    curricula_dir = Path("curricula")
    if curricula_dir.exists():
        files = sorted(list(curricula_dir.glob("*.json")), key=lambda x: x.stat().st_mtime, reverse=True)

        # Lightweight search by filename
        search = st.text_input("Search library", value="", placeholder="Type to filter by filename…")
        if search.strip():
            q = search.strip().lower()
            files = [f for f in files if q in f.name.lower()]

        # Exporter (optional; depends on fpdf2/markdown being installed)
        try:
            from services.export_service import get_exporter
            exporter = get_exporter()
        except Exception:
            exporter = None

        for f in files:
            with st.expander(f"📄 {f.name} ({time.ctime(f.stat().st_mtime)})"):
                try:
                    data = json.loads(f.read_text(encoding='utf-8'))
                    meta = data.get("meta", {}) if isinstance(data, dict) else {}
                    units = data.get("units", []) if isinstance(data, dict) else []
                    st.json(meta, expanded=False)
                    st.caption(f"Units: {len(units) if isinstance(units, list) else 0}")

                    # Actions
                    a1, a2, a3 = st.columns(3)
                    with a1:
                        if st.button("🎓 Open in Student", key=f"open_{f.name}", use_container_width=True):
                            StateManager.set_state("preferred_curriculum_file", f.name)
                            st.switch_page("pages/1_Student.py")

                    with a2:
                        json_str = json.dumps(data, indent=2, ensure_ascii=False)
                        st.download_button(
                            "⬇️ Download JSON",
                            data=json_str,
                            file_name=f.name,
                            mime="application/json",
                            key=f"dl_json_{f.name}",
                            use_container_width=True,
                        )

                    with a3:
                        confirm = st.checkbox("Confirm delete", key=f"confirm_del_{f.name}")
                        if st.button("🗑️ Delete", key=f"del_{f.name}", disabled=not confirm, use_container_width=True):
                            f.unlink()
                            st.rerun()

                    st.markdown("---")
                    st.markdown("### Export")

                    if exporter is None:
                        st.info("Export helpers unavailable (missing dependencies).")
                    else:
                        include_images = st.checkbox(
                            "Include image/chart placeholders in Markdown",
                            value=True,
                            key=f"md_img_{f.name}",
                        )

                        exp1, exp2, exp3 = st.columns(3)

                        # Markdown
                        md_state_key = f"export_md_{f.name}"
                        with exp1:
                            if st.button("Prepare Markdown", key=f"prep_md_{f.name}", use_container_width=True):
                                with st.spinner("Preparing Markdown…"):
                                    st.session_state[md_state_key] = exporter.generate_markdown(
                                        data, include_images=include_images
                                    )
                            if md_state_key in st.session_state:
                                st.download_button(
                                    "⬇️ Markdown",
                                    data=st.session_state[md_state_key],
                                    file_name=f"{f.stem}.md",
                                    mime="text/markdown",
                                    key=f"dl_md_{f.name}",
                                    use_container_width=True,
                                )

                        # HTML
                        html_state_key = f"export_html_{f.name}"
                        with exp2:
                            if st.button("Prepare HTML", key=f"prep_html_{f.name}", use_container_width=True):
                                with st.spinner("Preparing HTML…"):
                                    st.session_state[html_state_key] = exporter.generate_html(data)
                            if html_state_key in st.session_state:
                                st.download_button(
                                    "⬇️ HTML",
                                    data=st.session_state[html_state_key],
                                    file_name=f"{f.stem}.html",
                                    mime="text/html",
                                    key=f"dl_html_{f.name}",
                                    use_container_width=True,
                                )

                        # PDF
                        pdf_state_key = f"export_pdf_{f.name}"
                        with exp3:
                            if st.button("Prepare PDF", key=f"prep_pdf_{f.name}", use_container_width=True):
                                with st.spinner("Preparing PDF…"):
                                    st.session_state[pdf_state_key] = exporter.generate_pdf(data)
                            if pdf_state_key in st.session_state:
                                st.download_button(
                                    "⬇️ PDF",
                                    data=st.session_state[pdf_state_key],
                                    file_name=f"{f.stem}.pdf",
                                    mime="application/pdf",
                                    key=f"dl_pdf_{f.name}",
                                    use_container_width=True,
                                )

                except Exception:
                    st.error("Invalid JSON")
    else:
        st.info("No curricula found.")
