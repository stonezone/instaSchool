"""
Library Mode - Browse and Manage Saved Curricula
InstaSchool multi-page app
"""
import streamlit as st
from datetime import datetime
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

# Page setup
setup_page(title="InstaSchool - Library", icon="📚")
config = load_config()
StateManager.initialize_state()


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


def render_curriculum_card(curriculum: Dict[str, Any], idx: int) -> Optional[str]:
    """Render a single curriculum card and return action if any."""
    with st.container():
        col1, col2 = st.columns([3, 1])

        with col1:
            st.markdown(f"### {curriculum.get('title', 'Untitled')}")
            st.caption(
                f"**Subject:** {curriculum.get('subject', 'N/A')} | "
                f"**Grade:** {curriculum.get('grade', 'N/A')} | "
                f"**Style:** {curriculum.get('style', 'Standard')}"
            )
            st.caption(
                f"**Units:** {curriculum.get('unit_count', 0)} | "
                f"**Status:** {get_status_badge(curriculum.get('status', 'unknown'))} | "
                f"**Created:** {format_date(curriculum.get('created_at', ''))}"
            )

        with col2:
            # Action buttons
            if st.button("📖 Load", key=f"load_{idx}", help="Load this curriculum"):
                return ("load", curriculum.get("id"))
            if st.button("📋 Duplicate", key=f"dup_{idx}", help="Create a copy"):
                return ("duplicate", curriculum.get("id"))
            if st.button("🗑️ Delete", key=f"del_{idx}", help="Delete this curriculum"):
                return ("delete", curriculum.get("id"))

        st.divider()
    return None


def load_curriculum_to_session(supabase: SupabaseService, curriculum_id: str) -> bool:
    """Load a curriculum from Supabase into session state."""
    curriculum = supabase.get_curriculum(curriculum_id)
    if curriculum:
        StateManager.set_state("generated_curriculum", curriculum)
        StateManager.set_state("current_curriculum_id", curriculum_id)
        return True
    return False


def main():
    st.title("📚 Curriculum Library")
    st.markdown("Browse, manage, and load your saved curricula.")

    # Check Supabase availability
    if not SUPABASE_AVAILABLE or get_supabase_service is None:
        st.error("Supabase is not configured. Please set SUPABASE_URL and SUPABASE_KEY environment variables.")
        st.info("To set up Supabase, visit [supabase.com](https://supabase.com) and create a free account.")
        return

    supabase = get_supabase_service()

    if not supabase.is_available:
        st.warning(
            "Supabase connection not available. Check your environment variables:\n"
            "- `SUPABASE_URL`: Your Supabase project URL\n"
            "- `SUPABASE_KEY`: Your Supabase anon key"
        )
        return

    # Show stats
    stats = supabase.get_stats()
    if stats.get("available"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Curricula", stats.get("total_curricula", 0))
        with col2:
            st.metric("Complete", stats.get("complete", 0))
        with col3:
            st.metric("In Progress", stats.get("generating", 0))

    st.divider()

    # Filters
    st.subheader("Filter Curricula")
    filter_col1, filter_col2, filter_col3 = st.columns(3)

    with filter_col1:
        subject_filter = st.selectbox(
            "Subject",
            ["All"] + config["defaults"]["subjects"],
            key="lib_subject_filter"
        )

    with filter_col2:
        grade_filter = st.selectbox(
            "Grade",
            ["All"] + config["defaults"]["grades"],
            key="lib_grade_filter"
        )

    with filter_col3:
        status_filter = st.selectbox(
            "Status",
            ["All", "complete", "generating", "partial"],
            key="lib_status_filter"
        )

    # Apply filters
    subject = None if subject_filter == "All" else subject_filter
    grade = None if grade_filter == "All" else grade_filter
    status = None if status_filter == "All" else status_filter

    # Fetch curricula
    curricula = supabase.list_curricula(
        subject=subject,
        grade=grade,
        status=status,
        limit=50
    )

    st.divider()

    # Handle pending actions from previous render
    pending_action = StateManager.get_state("lib_pending_action")
    if pending_action:
        action, curriculum_id = pending_action
        StateManager.set_state("lib_pending_action", None)

        if action == "load":
            if load_curriculum_to_session(supabase, curriculum_id):
                st.success("Curriculum loaded! Go to the Create page to view it.")
            else:
                st.error("Failed to load curriculum.")

        elif action == "duplicate":
            new_id = supabase.duplicate_curriculum(curriculum_id)
            if new_id:
                st.success("Curriculum duplicated!")
                st.rerun()
            else:
                st.error("Failed to duplicate curriculum.")

        elif action == "delete":
            # Show confirmation
            StateManager.set_state("lib_confirm_delete", curriculum_id)

    # Handle delete confirmation
    confirm_delete_id = StateManager.get_state("lib_confirm_delete")
    if confirm_delete_id:
        st.warning(f"Are you sure you want to delete this curriculum? This cannot be undone.")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Yes, Delete", type="primary"):
                if supabase.delete_curriculum(confirm_delete_id):
                    st.success("Curriculum deleted.")
                    StateManager.set_state("lib_confirm_delete", None)
                    st.rerun()
                else:
                    st.error("Failed to delete curriculum.")
        with col2:
            if st.button("Cancel"):
                StateManager.set_state("lib_confirm_delete", None)
                st.rerun()

    # Display curricula
    if not curricula:
        st.info("No curricula found. Generate some on the Create page!")
    else:
        st.subheader(f"Showing {len(curricula)} curricula")

        for idx, curriculum in enumerate(curricula):
            action = render_curriculum_card(curriculum, idx)
            if action:
                StateManager.set_state("lib_pending_action", action)
                st.rerun()

    # Refresh button
    st.divider()
    if st.button("🔄 Refresh", help="Reload the curriculum list"):
        st.rerun()


if __name__ == "__main__":
    main()
