"""
Library Mode - Browse and Manage Saved Curricula
InstaSchool multi-page app
"""
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


def render_curriculum_card(curriculum: Dict[str, Any], idx: int, source: str = "cloud") -> Optional[tuple]:
    """Render a single curriculum card and return action if any.

    Args:
        curriculum: Curriculum data dict
        idx: Index for unique keys
        source: 'cloud' for Supabase, 'local' for filesystem
    """
    with st.container():
        col1, col2 = st.columns([3, 1])

        with col1:
            source_badge = "☁️" if source == "cloud" else "💾"
            st.markdown(f"### {source_badge} {curriculum.get('title', 'Untitled')}")
            st.caption(
                f"**Subject:** {curriculum.get('subject', 'N/A')} | "
                f"**Grade:** {curriculum.get('grade', 'N/A')} | "
                f"**Style:** {curriculum.get('style', 'Standard')}"
            )
            st.caption(
                f"**Units:** {curriculum.get('unit_count', 0)} | "
                f"**Status:** {get_status_badge(curriculum.get('status', 'unknown'))} | "
                f"**Source:** {'Cloud' if source == 'cloud' else 'Local'}"
            )

        with col2:
            # Action buttons
            if st.button("📖 Load", key=f"load_{source}_{idx}", help="Load this curriculum"):
                return ("load", curriculum.get("id"), source)
            if st.button("👀 Preview", key=f"preview_{source}_{idx}", help="Quick preview"):
                return ("preview", curriculum.get("id"), source)
            if source == "local":
                if st.button("☁️ Sync", key=f"sync_{source}_{idx}", help="Upload to cloud"):
                    return ("sync", curriculum.get("id"), source)
            else:
                if st.button("📋 Duplicate", key=f"dup_{source}_{idx}", help="Create a copy"):
                    return ("duplicate", curriculum.get("id"), source)
            if st.button("🗑️ Delete", key=f"del_{source}_{idx}", help="Delete this curriculum"):
                return ("delete", curriculum.get("id"), source)

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
                "_data": data  # Keep full data for preview/load
            })
        except Exception:
            pass  # Skip malformed files

    return local_curricula


def load_local_curriculum(filename: str) -> bool:
    """Load a local curriculum JSON file into session state."""
    filepath = Path("curricula") / filename
    if not filepath.exists():
        return False

    try:
        with open(filepath) as f:
            data = json.load(f)
        StateManager.set_state("generated_curriculum", data)
        StateManager.set_state("current_curriculum_file", filename)
        return True
    except Exception:
        return False


def render_preview_panel(curriculum_data: Dict[str, Any], key_prefix: str):
    """Render a quick preview panel for a curriculum."""
    st.markdown("---")
    st.markdown("#### 📖 Quick Preview")

    units = curriculum_data.get("units", [])
    if not units:
        st.info("No units in this curriculum.")
        return

    for i, unit in enumerate(units[:5]):  # Show first 5 units max
        unit_title = unit.get('title', f'Unit {i+1}')
        with st.expander(f"📚 {unit_title}", expanded=(i == 0)):
            content = unit.get('content', '')
            if content:
                # Truncate long content
                st.markdown(content[:2000] + ('...' if len(content) > 2000 else ''))
            if unit.get('image_base64'):
                st.image(f"data:image/png;base64,{unit['image_base64']}", width=300)
            if unit.get('quiz', {}).get('questions'):
                st.caption(f"📝 Quiz: {len(unit['quiz']['questions'])} questions")

    if len(units) > 5:
        st.caption(f"...and {len(units) - 5} more units")

    if st.button("Close Preview", key=f"close_preview_{key_prefix}"):
        StateManager.set_state("lib_preview_id", None)
        st.rerun()


def main():
    st.title("📚 Curriculum Library")
    st.markdown("Browse, manage, and load your saved curricula.")

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

    st.divider()

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
                    st.success("✅ Curriculum loaded! Go to the Create page to view it.")
                else:
                    st.error("Failed to load curriculum.")
            else:
                if supabase and load_curriculum_to_session(supabase, curriculum_id):
                    st.success("✅ Curriculum loaded! Go to the Create page to view it.")
                else:
                    st.error("Failed to load curriculum.")

        elif action == "preview":
            StateManager.set_state("lib_preview_id", (curriculum_id, source))

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
                    filepath = Path("curricula") / curriculum_id
                    if filepath.exists():
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

    # Tab 1: All curricula
    with source_tab1:
        all_curricula = []

        # Add local curricula
        for c in local_curricula:
            all_curricula.append((c, "local"))

        # Add cloud curricula
        for c in cloud_curricula:
            all_curricula.append((c, "cloud"))

        if not all_curricula:
            st.info("📭 No curricula found. Generate some on the Create page!")
        else:
            st.subheader(f"Showing {len(all_curricula)} curricula")
            for idx, (curriculum, source) in enumerate(all_curricula):
                action = render_curriculum_card(curriculum, idx, source)
                if action:
                    StateManager.set_state("lib_pending_action", action)
                    st.rerun()

    # Tab 2: Local only
    with source_tab2:
        if not local_curricula:
            st.info("📭 No local curricula found.")
        else:
            st.subheader(f"Showing {len(local_curricula)} local curricula")
            for idx, curriculum in enumerate(local_curricula):
                action = render_curriculum_card(curriculum, idx + 1000, "local")
                if action:
                    StateManager.set_state("lib_pending_action", action)
                    st.rerun()

    # Tab 3: Cloud only
    with source_tab3:
        if not supabase_available:
            st.warning("☁️ Cloud storage not connected. Set SUPABASE_URL and SUPABASE_KEY in environment.")
        elif not cloud_curricula:
            st.info("📭 No cloud curricula found.")
        else:
            st.subheader(f"Showing {len(cloud_curricula)} cloud curricula")
            for idx, curriculum in enumerate(cloud_curricula):
                action = render_curriculum_card(curriculum, idx + 2000, "cloud")
                if action:
                    StateManager.set_state("lib_pending_action", action)
                    st.rerun()

    # Refresh button
    st.divider()
    if st.button("🔄 Refresh", help="Reload the curriculum list"):
        st.rerun()


if __name__ == "__main__":
    main()
