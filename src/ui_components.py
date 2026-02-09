"""
UI Components and Styling Helpers for InstaSchool
Provides reusable UI components (StatusLogger, FamilyDashboard)
"""

import hashlib
import logging
import streamlit as st
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def _stable_hash(text: str) -> str:
    """Generate a stable, deterministic hash for widget keys.

    Unlike Python's built-in hash(), this is stable across processes
    and won't cause Streamlit widget key collisions.
    """
    return hashlib.md5(text.encode()).hexdigest()[:12]


class StatusLogger:
    """Real-time status logging for generation processes using st.status()"""

    def __init__(self, title: str = "Generating Curriculum", expanded: bool = True):
        """Initialize status logger with expandable container

        Args:
            title: Title for the status container
            expanded: Whether to expand by default
        """
        self.title = title
        self.expanded = expanded
        self.status = None
        self.logs: List[str] = []

    def __enter__(self):
        """Enter context manager - create status container"""
        self.status = st.status(self.title, expanded=self.expanded)
        self.status.__enter__()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context manager - complete status"""
        if exc_type is None:
            self.status.update(label=f"✅ {self.title} Complete", state="complete")
        else:
            self.status.update(label=f"❌ {self.title} Failed", state="error")
        self.status.__exit__(exc_type, exc_val, exc_tb)
        return False

    def log(self, message: str, icon: str = "📝") -> None:
        """Add a log entry to the status container

        Args:
            message: Log message to display
            icon: Emoji icon for the message
        """
        self.logs.append(f"{icon} {message}")
        if self.status:
            self.status.write(f"{icon} {message}")

    def update_label(self, label: str) -> None:
        """Update the status label/title

        Args:
            label: New label text
        """
        if self.status:
            self.status.update(label=label)

    def progress(self, step: str, icon: str = "🔄") -> None:
        """Log a progress step

        Args:
            step: Step description
            icon: Step icon
        """
        self.log(step, icon)

    def success(self, message: str) -> None:
        """Log a success message"""
        self.log(message, "✅")

    def warning(self, message: str) -> None:
        """Log a warning message"""
        self.log(message, "⚠️")

    def error(self, message: str) -> None:
        """Log an error message"""
        self.log(message, "❌")

    def info(self, message: str) -> None:
        """Log an info message"""
        self.log(message, "ℹ️")

    def agent_start(self, agent_name: str) -> None:
        """Log agent start"""
        self.log(f"Starting {agent_name}...", "🤖")

    def agent_complete(self, agent_name: str) -> None:
        """Log agent completion"""
        self.log(f"{agent_name} complete", "✓")


class FamilyDashboard:
    """Family dashboard UI components for parent view"""

    @staticmethod
    def render_child_card(child_data: Dict[str, Any]) -> None:
        """Render a single child's progress card

        Args:
            child_data: Dict with username, xp, streak, due_cards, etc.
        """
        username = child_data.get("username", "Unknown")
        xp = child_data.get("total_xp", 0)
        level = child_data.get("level", 0)
        streak = child_data.get("current_streak", 0)
        due_cards = child_data.get("due_cards", 0)
        last_active = child_data.get("last_active", "Never")
        curricula = child_data.get("total_curricula", 0)
        completed = child_data.get("completed_curricula", 0)

        # Card styling
        streak_emoji = "🔥" if streak > 0 else "❄️"
        due_color = "red" if due_cards > 10 else ("orange" if due_cards > 5 else "green")

        st.markdown(f"""
        <div style="
            background: var(--card-bg, #ffffff);
            border: 1px solid var(--border-color, #e2e8f0);
            border-radius: 12px;
            padding: 1.5rem;
            margin-bottom: 1rem;
        ">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem;">
                <h3 style="margin: 0; color: var(--neutral-900, #0f172a);">👤 {username}</h3>
                <span style="
                    background: linear-gradient(135deg, #6366f1, #8b5cf6);
                    color: white;
                    padding: 0.25rem 0.75rem;
                    border-radius: 20px;
                    font-size: 0.85rem;
                ">Level {level}</span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 1rem;">
                <div>
                    <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Streak</div>
                    <div style="font-size: 1.25rem; font-weight: 600;">{streak_emoji} {streak} days</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">XP</div>
                    <div style="font-size: 1.25rem; font-weight: 600;">⭐ {xp:,}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Due Cards</div>
                    <div style="font-size: 1.25rem; font-weight: 600; color: {due_color};">📚 {due_cards}</div>
                </div>
                <div>
                    <div style="font-size: 0.75rem; color: #64748b; text-transform: uppercase;">Last Active</div>
                    <div style="font-size: 1.25rem; font-weight: 600;">🕐 {last_active}</div>
                </div>
            </div>
            <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid var(--border-color, #e2e8f0);">
                <div style="font-size: 0.85rem; color: #64748b;">
                    📖 {curricula} curricula ({completed} completed)
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def render_family_totals(totals: Dict[str, Any]) -> None:
        """Render family-wide totals summary

        Args:
            totals: Dict with total_xp, total_curricula, active_today, etc.
        """
        col1, col2, col3, col4 = st.columns(4)

        with col1:
            st.metric(
                label="👨‍👩‍👧‍👦 Active Today",
                value=totals.get("active_today", 0)
            )

        with col2:
            st.metric(
                label="⭐ Family XP",
                value=f"{totals.get('total_xp', 0):,}"
            )

        with col3:
            st.metric(
                label="📚 Due Reviews",
                value=totals.get("total_due_cards", 0)
            )

        with col4:
            st.metric(
                label="📖 Total Curricula",
                value=totals.get("total_curricula", 0)
            )

    @staticmethod
    def render_dashboard(family_data: Dict[str, Any]) -> None:
        """Render complete family dashboard

        Args:
            family_data: Dict from FamilyService.get_family_summary()
        """
        st.markdown("## 📊 Family Learning Dashboard")

        children = family_data.get("children", [])
        totals = family_data.get("totals", {})

        if not children:
            st.info("No children profiles found. Create student profiles to see them here.")
            return

        # Family totals
        FamilyDashboard.render_family_totals(totals)

        st.markdown("---")
        st.markdown("### 👧👦 Children")

        # Render children in columns (2 per row)
        for i in range(0, len(children), 2):
            cols = st.columns(2)
            for j, col in enumerate(cols):
                if i + j < len(children):
                    with col:
                        FamilyDashboard.render_child_card(children[i + j])

    @staticmethod
    def render_add_child_form(form_key: str = "add_child_form", show_header: bool = True) -> Optional[Dict[str, Any]]:
        """Render form to add a new child

        Args:
            form_key: Unique key for the form to avoid duplicates
            show_header: Whether to show the "Add Child" header

        Returns:
            Dict with new child data if form submitted, None otherwise
        """
        if show_header:
            st.markdown("### ➕ Add Child")

        with st.form(form_key):
            username = st.text_input(
                "Child's Name",
                placeholder="Enter name...",
                help="This will be the child's profile name"
            )

            use_pin = st.checkbox(
                "🔐 Set PIN (optional)",
                help="Add a 4-6 digit PIN for privacy"
            )

            pin = None
            if use_pin:
                pin = st.text_input(
                    "PIN (4-6 digits)",
                    type="password",
                    max_chars=6
                )

            submitted = st.form_submit_button("Add Child", width="stretch")

            if submitted:
                if not username:
                    st.error("Please enter a name")
                    return None

                if use_pin and pin:
                    if len(pin) < 4:
                        st.error("PIN must be at least 4 digits")
                        return None
                    if not pin.isdigit():
                        st.error("PIN must be numbers only")
                        return None

                return {
                    "username": username,
                    "pin": pin if use_pin else None
                }

        return None
