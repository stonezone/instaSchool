"""
Library Mode - Browse and Manage Saved Curricula
InstaSchool multi-page app
"""
import re
import json
import time
import streamlit as st
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from dotenv import load_dotenv

load_dotenv()

from src.shared_init import setup_page, load_config, get_provider_service
from src.state_manager import StateManager
from src.ui_components import ModernUI

# Import Supabase service
try:
    from services.supabase_service import get_supabase_service, SupabaseService
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    get_supabase_service = None

# Import export service
try:
    from services.export_service import get_exporter
    EXPORT_AVAILABLE = True
except ImportError:
    EXPORT_AVAILABLE = False
    get_exporter = None

# Page setup
setup_page(title="InstaSchool - Library", icon="📚")
config = load_config()
StateManager.initialize_state()


def sanitize_filename(name: str) -> str:
    """Sanitize filename: replace spaces with hyphens, remove unsafe chars."""
    name = name.replace(" ", "-")
    name = re.sub(r"[<>:\"/\\|?*]", "", name)
    name = re.sub(r"-+", "-", name)
    return name.strip("-")


def format_date(date_str: str) -> str:
    """Format ISO date string for display."""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime("%b %d, %Y %H:%M")
    except Exception:
        return date_str


def get_status_badge(status: str) -> str:
    """Get a colored badge for curriculum status."""
    colors = {
        "complete": "🟢",
        "generating": "🟡",
        "partial": "🟠",
        "failed": "🔴"
    }
    return f"{colors.get(status, '⚪')} {status.capitalize()}"


def get_curriculum_stats(curriculum_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate quality stats for a curriculum."""
    units = curriculum_data.get("units", [])

    total_images = 0
    total_quizzes = 0
    total_questions = 0
    total_words = 0

    image_fields = ["selected_image_b64", "image_base64", "image", "image_data"]

    for unit in units:
        if not isinstance(unit, dict):
            continue

        # Count images
        for field in image_fields:
            if unit.get(field):
                total_images += 1
                break

        # Count chart as image
        if unit.get("chart"):
            total_images += 1

        # Count quizzes and questions
        quiz = unit.get("quiz")
        if quiz:
            total_quizzes += 1
            if isinstance(quiz, dict):
                questions = quiz.get("questions", quiz.get("quiz", []))
            elif isinstance(quiz, list):
                questions = quiz
            else:
                questions = []
            total_questions += len(questions) if isinstance(questions, list) else 0

        # Count words in content
        content = unit.get("content", "")
        if content:
            total_words += len(content.split())

    return {
        "units": len(units),
        "images": total_images,
        "quizzes": total_quizzes,
        "questions": total_questions,
        "words": total_words,
        "est_time_min": max(5, total_words // 200)  # ~200 words per minute reading
    }


def render_curriculum_card(
    curriculum: Dict[str, Any],
    idx: int,
    source: str = "cloud",
    local_curricula: List[Dict] = None,
    supabase = None
) -> Optional[tuple]:
    """Render a single curriculum card with stats and export options.

    Args:
        curriculum: Curriculum data dict
        idx: Index for unique keys
        source: 'cloud' for Supabase, 'local' for filesystem
        local_curricula: List of local curricula for data lookup
        supabase: Supabase service instance
    """
    # Get full curriculum data for stats
    curriculum_data = None
    if source == "local" and curriculum.get("_data"):
        curriculum_data = curriculum["_data"]

    with st.container():
        # Header row
        col1, col2 = st.columns([3, 1])

        with col1:
            source_badge = "☁️" if source == "cloud" else "💾"
            st.markdown(f"### {source_badge} {curriculum.get('title', 'Untitled')}")
            st.caption(
                f"**Subject:** {curriculum.get('subject', 'N/A')} | "
                f"**Grade:** {curriculum.get('grade', 'N/A')} | "
                f"**Style:** {curriculum.get('style', 'Standard')}"
            )

            # Stats row with quality indicators
            units = curriculum.get('unit_count', 0)
            status = get_status_badge(curriculum.get('status', 'unknown'))

            if curriculum_data:
                stats = get_curriculum_stats(curriculum_data)
                st.caption(
                    f"📚 **{stats['units']}** units | "
                    f"🖼️ **{stats['images']}** images | "
                    f"📝 **{stats['questions']}** quiz questions | "
                    f"⏱️ ~{stats['est_time_min']} min"
                )
                # Show model info if available
                meta = curriculum_data.get("meta", {})
                model = meta.get("text_model") or meta.get("model")
                if model:
                    st.caption(f"🤖 Generated with **{model}**")
            else:
                st.caption(f"📚 **{units}** units | {status}")

        with col2:
            # Primary actions
            if st.button("📖 Load", key=f"load_{source}_{idx}", help="Open in Student view"):
                return ("load", curriculum.get("id"), source)
            if st.button("👀 Preview", key=f"preview_{source}_{idx}", help="Quick preview"):
                return ("preview", curriculum.get("id"), source)

        # Expandable section for more actions
        with st.expander("📦 More Actions", expanded=False):
            act_col1, act_col2, act_col3 = st.columns(3)

            with act_col1:
                if source == "local":
                    if st.button("☁️ Sync to Cloud", key=f"sync_{source}_{idx}", use_container_width=True):
                        return ("sync", curriculum.get("id"), source)
                else:
                    if st.button("📋 Duplicate", key=f"dup_{source}_{idx}", use_container_width=True):
                        return ("duplicate", curriculum.get("id"), source)

            with act_col2:
                if st.button("📤 Export", key=f"export_{source}_{idx}", use_container_width=True):
                    return ("export", curriculum.get("id"), source)

            with act_col3:
                if st.button("🗑️ Delete", key=f"del_{source}_{idx}", use_container_width=True):
                    return ("delete", curriculum.get("id"), source)

        st.divider()
    return None


def render_export_panel(curriculum_data: Dict[str, Any], curriculum_id: str, source: str):
    """Render export options for a curriculum."""
    st.markdown("---")
    st.markdown("#### 📤 Export Curriculum")
    st.caption("Export with all media included, exactly as presented to students.")

    if not EXPORT_AVAILABLE or get_exporter is None:
        st.error("Export service not available. Check dependencies.")
        if st.button("Close Export", key=f"close_export_{curriculum_id}"):
            StateManager.set_state("lib_export_id", None)
            st.rerun()
        return

    exporter = get_exporter()

    # Quality selection
    quality = st.selectbox(
        "Image Quality",
        options=["medium", "high", "low"],
        index=0,
        key=f"quality_{curriculum_id}",
        help="High: 800px (printing) | Medium: 600px (sharing) | Low: 400px (mobile)"
    )

    # Safe filename from curriculum title
    meta = curriculum_data.get("meta", {})
    title = meta.get("subject", "curriculum")
    grade = meta.get("grade", "")
    safe_name = sanitize_filename(f"{title}_{grade}".strip("_"))

    exp_col1, exp_col2, exp_col3 = st.columns(3)

    # HTML Export (primary - includes all media)
    html_key = f"export_html_{curriculum_id}"
    with exp_col1:
        if st.button("📄 Prepare HTML", key=f"prep_html_{curriculum_id}", use_container_width=True):
            with st.spinner("Generating HTML with all media..."):
                try:
                    html_content = exporter.generate_html(curriculum_data, quality=quality)
                    st.session_state[html_key] = html_content
                except Exception as e:
                    st.error(f"Export failed: {e}")

        if html_key in st.session_state:
            st.download_button(
                "⬇️ Download HTML",
                data=st.session_state[html_key],
                file_name=f"{safe_name}.html",
                mime="text/html",
                key=f"dl_html_{curriculum_id}",
                use_container_width=True,
            )
            st.success("✅ Ready!")

    # PDF Export
    pdf_key = f"export_pdf_{curriculum_id}"
    with exp_col2:
        if st.button("📕 Prepare PDF", key=f"prep_pdf_{curriculum_id}", use_container_width=True):
            with st.spinner("Generating PDF..."):
                try:
                    pdf_content = exporter.generate_pdf(curriculum_data, quality=quality)
                    st.session_state[pdf_key] = pdf_content
                except Exception as e:
                    st.error(f"PDF export failed: {e}")

        if pdf_key in st.session_state:
            st.download_button(
                "⬇️ Download PDF",
                data=st.session_state[pdf_key],
                file_name=f"{safe_name}.pdf",
                mime="application/pdf",
                key=f"dl_pdf_{curriculum_id}",
                use_container_width=True,
            )
            st.success("✅ Ready!")

    # JSON Export (raw data)
    with exp_col3:
        json_str = json.dumps(curriculum_data, indent=2, ensure_ascii=False)
        st.download_button(
            "📋 Download JSON",
            data=json_str,
            file_name=f"{safe_name}.json",
            mime="application/json",
            key=f"dl_json_{curriculum_id}",
            use_container_width=True,
        )
        st.caption("Raw curriculum data")

    st.markdown("")
    if st.button("Close Export Panel", key=f"close_export_{curriculum_id}"):
        StateManager.set_state("lib_export_id", None)
        st.rerun()


def render_preview_panel(curriculum_data: Dict[str, Any], key_prefix: str):
    """Render an enhanced preview panel for a curriculum."""
    st.markdown("---")
    st.markdown("#### 📖 Curriculum Preview")

    # Show quality stats
    stats = get_curriculum_stats(curriculum_data)
    stat_col1, stat_col2, stat_col3, stat_col4 = st.columns(4)
    with stat_col1:
        st.metric("📚 Units", stats["units"])
    with stat_col2:
        st.metric("🖼️ Images", stats["images"])
    with stat_col3:
        st.metric("📝 Questions", stats["questions"])
    with stat_col4:
        st.metric("⏱️ Est. Time", f"{stats['est_time_min']} min")

    st.markdown("---")

    units = curriculum_data.get("units", [])
    if not units:
        st.info("No units in this curriculum.")
        if st.button("Close Preview", key=f"close_preview_{key_prefix}"):
            StateManager.set_state("lib_preview_id", None)
            st.rerun()
        return

    # Image fields to check
    image_fields = ["selected_image_b64", "image_base64", "image", "image_data"]

    for i, unit in enumerate(units):
        if not isinstance(unit, dict):
            continue
        unit_title = unit.get('title', f'Unit {i+1}')

        # Build unit summary
        has_image = any(unit.get(f) for f in image_fields) or unit.get("chart")
        quiz = unit.get("quiz")
        quiz_count = 0
        if quiz:
            if isinstance(quiz, dict):
                questions = quiz.get("questions", quiz.get("quiz", []))
            elif isinstance(quiz, list):
                questions = quiz
            else:
                questions = []
            quiz_count = len(questions) if isinstance(questions, list) else 0

        badge = f"{'🖼️' if has_image else ''} {'📝' if quiz_count else ''}"

        with st.expander(f"📚 Unit {i+1}: {unit_title} {badge}", expanded=(i == 0)):
            # Introduction
            intro = unit.get('introduction', '')
            if intro:
                st.markdown("**Introduction:**")
                st.markdown(intro[:1000] + ('...' if len(intro) > 1000 else ''))

            # Content (show more in preview)
            content = unit.get('content', '')
            if content:
                st.markdown("**Content:**")
                # Show up to 3000 chars in preview
                st.markdown(content[:3000] + ('...' if len(content) > 3000 else ''))

            # Image preview
            for field in image_fields:
                img_b64 = unit.get(field)
                if img_b64:
                    st.markdown("**Illustration:**")
                    # Handle data URI prefix
                    if not img_b64.startswith("data:"):
                        img_b64 = f"data:image/jpeg;base64,{img_b64}"
                    st.image(img_b64, width=400)
                    break

            # Chart preview
            chart = unit.get("chart")
            if chart:
                st.markdown("**Chart:**")
                if isinstance(chart, dict) and chart.get("b64"):
                    chart_b64 = chart["b64"]
                    if not chart_b64.startswith("data:"):
                        chart_b64 = f"data:image/jpeg;base64,{chart_b64}"
                    st.image(chart_b64, width=400)
                elif isinstance(chart, str):
                    if not chart.startswith("data:"):
                        chart = f"data:image/jpeg;base64,{chart}"
                    st.image(chart, width=400)

            # Quiz preview
            if quiz_count > 0:
                st.markdown(f"**Quiz:** {quiz_count} questions")
                # Show first 2 questions as preview
                if isinstance(quiz, dict):
                    questions = quiz.get("questions", quiz.get("quiz", []))
                elif isinstance(quiz, list):
                    questions = quiz
                else:
                    questions = []

                for q_idx, question in enumerate(questions[:2]):
                    if isinstance(question, dict):
                        st.caption(f"Q{q_idx+1}: {question.get('question', '')[:100]}...")

            # Summary
            summary = unit.get('summary', '')
            if summary:
                st.markdown("**Summary:**")
                st.markdown(summary[:500] + ('...' if len(summary) > 500 else ''))

    st.markdown("")
    if st.button("Close Preview", key=f"close_preview_{key_prefix}"):
        StateManager.set_state("lib_preview_id", None)
        st.rerun()


def load_curriculum_to_session(supabase: SupabaseService, curriculum_id: str) -> bool:
    """Load a curriculum from Supabase into session state."""
    curriculum = supabase.get_curriculum(curriculum_id)
    if curriculum:
        StateManager.set_state("generated_curriculum", curriculum)
        StateManager.set_state("current_curriculum_id", curriculum_id)
        return True
    return False


def get_local_curricula() -> List[Dict[str, Any]]:
    """Scan curricula/ directory for local JSON files."""
    curricula_dir = Path("curricula")
    local_curricula = []

    if not curricula_dir.exists():
        return local_curricula

    for json_file in sorted(curricula_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True):
        try:
            with open(json_file) as f:
                data = json.load(f)

            # Extract metadata - check 'meta' block first (new format), then top-level
            meta = data.get('meta', {})
            subject = meta.get('subject', data.get('subject', 'Unknown'))
            grade = meta.get('grade', data.get('grade', ''))
            style = meta.get('style', data.get('style', 'Standard'))
            title = f"{subject} - Grade {grade}" if grade else subject
            units = data.get('units', [])

            # Get file modification time
            mtime = datetime.fromtimestamp(json_file.stat().st_mtime)
            created_at = mtime.isoformat()

            local_curricula.append({
                "id": json_file.name,  # Use filename as ID
                "title": title,
                "subject": subject,
                "grade": grade,
                "style": style,
                "unit_count": len(units),
                "status": "complete",
                "created_at": created_at,
                "_filepath": str(json_file),
                "_data": data  # Keep full data for preview/load/export
            })
        except Exception:
            pass  # Skip malformed files

    return local_curricula


def _validate_path_within_directory(base_dir: Path, filepath: Path) -> bool:
    """Validate that filepath stays within base_dir (prevent path traversal)."""
    try:
        base_resolved = base_dir.resolve()
        file_resolved = filepath.resolve()
        # Check if the resolved path starts with the base directory
        return str(file_resolved).startswith(str(base_resolved) + "/") or file_resolved == base_resolved
    except (OSError, ValueError):
        return False


def load_local_curriculum(filename: str) -> bool:
    """Load a local curriculum JSON file into session state."""
    base_dir = Path("curricula")
    filepath = base_dir / filename

    # Security: Validate path stays within curricula directory
    if not _validate_path_within_directory(base_dir, filepath):
        return False

    if not filepath.exists():
        return False

    try:
        with open(filepath) as f:
            data = json.load(f)
        StateManager.set_state("generated_curriculum", data)
        StateManager.set_state("current_curriculum_file", filename)
        StateManager.set_state("preferred_curriculum_file", filename)
        return True
    except Exception:
        return False


def main():
    # Handle navigation to Student view (set by "Open Student View" button)
    if StateManager.get_state("lib_navigate_to_student"):
        StateManager.set_state("lib_navigate_to_student", None)
        st.switch_page("pages/1_Student.py")
        return

    st.title("📚 Curriculum Library")
    st.markdown("Browse, manage, and export your saved curricula.")

    # Check Supabase availability
    supabase = None
    supabase_available = False
    if SUPABASE_AVAILABLE and get_supabase_service is not None:
        try:
            supabase = get_supabase_service()
            supabase_available = supabase.is_available
        except Exception:
            pass

    # Get local curricula (always available)
    local_curricula = get_local_curricula()

    # Show stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("💾 Local", len(local_curricula))
    with col2:
        if supabase_available:
            stats = supabase.get_stats()
            st.metric("☁️ Cloud", stats.get("total_curricula", 0))
        else:
            st.metric("☁️ Cloud", "N/A")
    with col3:
        total = len(local_curricula)
        if supabase_available:
            total += stats.get("total_curricula", 0)
        st.metric("📊 Total", total)
    with col4:
        if supabase_available:
            st.success("Cloud: Connected")
        else:
            st.warning("Cloud: Offline")

    # Bulk sync option (only show if there are local curricula and Supabase is connected)
    if local_curricula and supabase_available:
        with st.expander("☁️ Sync Local Curricula to Cloud", expanded=False):
            st.markdown("""
            **Upload all local curricula to Supabase cloud storage.**

            This allows your curricula to be accessible on Streamlit Cloud
            and other deployments where local files aren't available.
            """)

            # Show count of already synced vs not synced
            local_not_synced = [c for c in local_curricula if not c.get("_data", {}).get("meta", {}).get("supabase_id")]
            st.caption(f"📊 {len(local_not_synced)} of {len(local_curricula)} local curricula not yet synced to cloud")

            if st.button("☁️ Sync All to Cloud", type="primary", key="bulk_sync_btn"):
                synced = 0
                failed = 0
                progress_bar = st.progress(0)
                status_text = st.empty()

                for i, curriculum in enumerate(local_curricula):
                    try:
                        if curriculum.get("_data"):
                            status_text.text(f"Syncing: {curriculum.get('title', 'Unknown')}...")
                            new_id = supabase.save_curriculum(curriculum["_data"], status="complete")
                            if new_id:
                                synced += 1
                            else:
                                failed += 1
                    except Exception as e:
                        failed += 1
                        print(f"Sync error: {e}")

                    progress_bar.progress((i + 1) / len(local_curricula))

                status_text.empty()
                progress_bar.empty()

                if synced > 0:
                    st.success(f"✅ Synced {synced} curricula to cloud!")
                if failed > 0:
                    st.warning(f"⚠️ {failed} curricula failed to sync (may be too large)")

                if synced > 0:
                    st.rerun()

    st.divider()

    # Search and filter
    search_col1, search_col2 = st.columns([2, 1])
    with search_col1:
        search_query = st.text_input(
            "🔍 Search",
            placeholder="Filter by title, subject...",
            key="lib_search"
        )
    with search_col2:
        sort_option = st.selectbox(
            "Sort by",
            ["Newest First", "Oldest First", "Most Units", "Fewest Units"],
            key="lib_sort"
        )

    # Source filter tabs
    source_tab1, source_tab2, source_tab3 = st.tabs(["📁 All", "💾 Local Only", "☁️ Cloud Only"])

    # Handle pending actions first
    pending_action = StateManager.get_state("lib_pending_action")
    if pending_action:
        action, curriculum_id, source = pending_action
        StateManager.set_state("lib_pending_action", None)

        if action == "load":
            if source == "local":
                if load_local_curriculum(curriculum_id):
                    st.success("✅ Curriculum loaded!")
                    if st.button("🎓 Open Student View", type="primary"):
                        StateManager.set_state("lib_navigate_to_student", True)
                        st.rerun()
                else:
                    st.error("Failed to load curriculum.")
            else:
                if supabase and load_curriculum_to_session(supabase, curriculum_id):
                    st.success("✅ Curriculum loaded!")
                    if st.button("🎓 Open Student View", type="primary"):
                        StateManager.set_state("lib_navigate_to_student", True)
                        st.rerun()
                else:
                    st.error("Failed to load curriculum.")

        elif action == "preview":
            StateManager.set_state("lib_preview_id", (curriculum_id, source))
            StateManager.set_state("lib_export_id", None)

        elif action == "export":
            StateManager.set_state("lib_export_id", (curriculum_id, source))
            StateManager.set_state("lib_preview_id", None)

        elif action == "sync":
            # Upload local file to Supabase
            if supabase_available:
                local_match = next((c for c in local_curricula if c["id"] == curriculum_id), None)
                if local_match and "_data" in local_match:
                    try:
                        new_id = supabase.save_curriculum(local_match["_data"], status="complete")
                        if new_id:
                            st.success("✅ Curriculum synced to cloud!")
                            st.rerun()
                        else:
                            st.error("Failed to sync curriculum.")
                    except Exception as e:
                        st.error(f"Sync error: {e}")
            else:
                st.error("Cloud storage not available.")

        elif action == "duplicate":
            if source == "cloud" and supabase:
                new_id = supabase.duplicate_curriculum(curriculum_id)
                if new_id:
                    st.success("✅ Curriculum duplicated!")
                    st.rerun()
                else:
                    st.error("Failed to duplicate curriculum.")

        elif action == "delete":
            StateManager.set_state("lib_confirm_delete", (curriculum_id, source))

    # Handle delete confirmation
    confirm_delete = StateManager.get_state("lib_confirm_delete")
    if confirm_delete:
        curriculum_id, source = confirm_delete
        st.warning("⚠️ Are you sure you want to delete this curriculum? This cannot be undone.")
        del_col1, del_col2 = st.columns(2)
        with del_col1:
            if st.button("Yes, Delete", type="primary"):
                success = False
                if source == "local":
                    base_dir = Path("curricula")
                    filepath = base_dir / curriculum_id
                    # Security: Validate path stays within curricula directory
                    if _validate_path_within_directory(base_dir, filepath) and filepath.exists():
                        filepath.unlink()
                        success = True
                elif source == "cloud" and supabase:
                    success = supabase.delete_curriculum(curriculum_id)

                if success:
                    st.success("✅ Curriculum deleted.")
                    StateManager.set_state("lib_confirm_delete", None)
                    st.rerun()
                else:
                    st.error("Failed to delete curriculum.")
        with del_col2:
            if st.button("Cancel"):
                StateManager.set_state("lib_confirm_delete", None)
                st.rerun()

    # Handle export panel
    export_data = StateManager.get_state("lib_export_id")
    if export_data:
        curriculum_id, source = export_data
        curriculum_data = None
        if source == "local":
            local_match = next((c for c in local_curricula if c["id"] == curriculum_id), None)
            if local_match and "_data" in local_match:
                curriculum_data = local_match["_data"]
        elif source == "cloud" and supabase:
            curriculum_data = supabase.get_curriculum(curriculum_id)

        if curriculum_data:
            render_export_panel(curriculum_data, curriculum_id, source)
        else:
            st.error("Could not load curriculum for export.")
            if st.button("Close"):
                StateManager.set_state("lib_export_id", None)
                st.rerun()

    # Handle preview
    preview_data = StateManager.get_state("lib_preview_id")
    if preview_data:
        curriculum_id, source = preview_data
        if source == "local":
            local_match = next((c for c in local_curricula if c["id"] == curriculum_id), None)
            if local_match and "_data" in local_match:
                render_preview_panel(local_match["_data"], f"local_{curriculum_id}")
        elif source == "cloud" and supabase:
            cloud_data = supabase.get_curriculum(curriculum_id)
            if cloud_data:
                render_preview_panel(cloud_data, f"cloud_{curriculum_id}")

    # Get cloud curricula if available
    cloud_curricula = []
    if supabase_available:
        try:
            cloud_curricula = supabase.list_curricula(limit=50)
        except Exception:
            pass

    # Helper function to filter and sort curricula
    def filter_and_sort(curricula_list: List[tuple]) -> List[tuple]:
        # Filter by search query
        if search_query:
            q = search_query.lower()
            curricula_list = [
                (c, s) for c, s in curricula_list
                if q in c.get("title", "").lower()
                or q in c.get("subject", "").lower()
                or q in c.get("grade", "").lower()
            ]

        # Sort
        if sort_option == "Newest First":
            curricula_list.sort(key=lambda x: x[0].get("created_at", ""), reverse=True)
        elif sort_option == "Oldest First":
            curricula_list.sort(key=lambda x: x[0].get("created_at", ""))
        elif sort_option == "Most Units":
            curricula_list.sort(key=lambda x: x[0].get("unit_count", 0), reverse=True)
        elif sort_option == "Fewest Units":
            curricula_list.sort(key=lambda x: x[0].get("unit_count", 0))

        return curricula_list

    # Tab 1: All curricula
    with source_tab1:
        all_curricula = []
        for c in local_curricula:
            all_curricula.append((c, "local"))
        for c in cloud_curricula:
            all_curricula.append((c, "cloud"))

        all_curricula = filter_and_sort(all_curricula)

        if not all_curricula:
            st.info("📭 No curricula found.")
            st.markdown("""
            **To populate your library:**
            1. Go to the **Create** page to generate new curricula
            2. Or if running locally, use "Sync All to Cloud" above to upload existing files
            """)
        else:
            st.subheader(f"Showing {len(all_curricula)} curricula")
            for idx, (curriculum, source) in enumerate(all_curricula):
                action = render_curriculum_card(
                    curriculum, idx, source,
                    local_curricula=local_curricula,
                    supabase=supabase
                )
                if action:
                    StateManager.set_state("lib_pending_action", action)
                    st.rerun()

    # Tab 2: Local only
    with source_tab2:
        local_filtered = filter_and_sort([(c, "local") for c in local_curricula])

        if not local_filtered:
            st.info("📭 No local curricula found.")
        else:
            st.subheader(f"Showing {len(local_filtered)} local curricula")
            for idx, (curriculum, source) in enumerate(local_filtered):
                action = render_curriculum_card(
                    curriculum, idx + 1000, source,
                    local_curricula=local_curricula,
                    supabase=supabase
                )
                if action:
                    StateManager.set_state("lib_pending_action", action)
                    st.rerun()

    # Tab 3: Cloud only
    with source_tab3:
        if not supabase_available:
            st.warning("☁️ Cloud storage not connected. Set SUPABASE_URL and SUPABASE_KEY in environment.")
        else:
            cloud_filtered = filter_and_sort([(c, "cloud") for c in cloud_curricula])

            if not cloud_filtered:
                st.info("📭 No cloud curricula found.")
                st.markdown("""
                **Cloud storage is connected but empty.**

                Curricula created on this deployment will automatically save to the cloud.
                If you have local curricula, run locally and use "Sync All to Cloud" to upload them.
                """)
            else:
                st.subheader(f"Showing {len(cloud_filtered)} cloud curricula")
                for idx, (curriculum, source) in enumerate(cloud_filtered):
                    action = render_curriculum_card(
                        curriculum, idx + 2000, source,
                        local_curricula=local_curricula,
                        supabase=supabase
                    )
                    if action:
                        StateManager.set_state("lib_pending_action", action)
                        st.rerun()

    # Refresh button
    st.divider()
    if st.button("🔄 Refresh", help="Reload the curriculum list"):
        st.rerun()


if __name__ == "__main__":
    main()
