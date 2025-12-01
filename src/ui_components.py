"""
UI Components and Styling Helpers for InstaSchool
Provides reusable UI components and modern styling utilities
"""

import hashlib
import logging
import streamlit as st
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


def _stable_hash(text: str) -> str:
    """Generate a stable, deterministic hash for widget keys.

    Unlike Python's built-in hash(), this is stable across processes
    and won't cause Streamlit widget key collisions.
    """
    return hashlib.md5(text.encode()).hexdigest()[:12]

class ModernUI:
    """Modern UI component system for InstaSchool"""
    
    @staticmethod
    def load_css():
        """Load the modern design system CSS"""
        css_path = Path(__file__).parent.parent / "static" / "css" / "design_system.css"
        
        if css_path.exists():
            with open(css_path, 'r') as f:
                css_content = f.read()
            
            st.markdown(f"""
                <style>
                {css_content}
                </style>
            """, unsafe_allow_html=True)
        else:
            # Fallback to inline CSS if file doesn't exist
            logger.warning(
                f"Design system CSS not found at {css_path}. "
                "Using minimal fallback styles. Check deployment packaging."
            )
            st.markdown("""
                <style>
                .modern-card {
                    background: white;
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                    padding: 24px;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
                    margin-bottom: 16px;
                }
                </style>
            """, unsafe_allow_html=True)

    @staticmethod
    def card(title: str = "", content: str = "", subtitle: str = "",
             icon: str = "", status: str = "", key: str = None) -> None:
        """
        Render a modern card component - FIXED VERSION
        Uses single complete HTML block to avoid Streamlit rendering issues.

        Args:
            title: Card title
            content: Card content (markdown supported)
            subtitle: Optional subtitle
            icon: Optional icon (emoji or text)
            status: Status badge (success, warning, error, info)
            key: Unique key for the component
        """
        card_id = key or f"card_{_stable_hash(title + content)}"

        # Build header if title exists
        header_html = ""
        if title or icon:
            status_badge = f'<span class="status-badge {status}">{status}</span>' if status else ""
            header_html = f"""
                <div class="modern-card-header">
                    {f'<span style="font-size: 1.5em;">{icon}</span>' if icon else ""}
                    <div>
                        <h3 class="modern-card-title">{title}</h3>
                        {f'<p class="modern-card-subtitle">{subtitle}</p>' if subtitle else ""}
                    </div>
                    {status_badge}
                </div>
            """

        # Convert markdown content to HTML for embedding
        content_html = ""
        if content:
            # Simple markdown to HTML conversion for common patterns
            import re
            html = content
            # Bold: **text** -> <strong>text</strong>
            html = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', html)
            # Italic: *text* -> <em>text</em>
            html = re.sub(r'\*(.+?)\*', r'<em>\1</em>', html)
            # Line breaks
            html = html.replace('\n\n', '</p><p>').replace('\n', '<br>')
            # Wrap numbered lists
            html = re.sub(r'^(\d+)\. (.+)$', r'<li>\2</li>', html, flags=re.MULTILINE)
            if '<li>' in html:
                html = f'<ol>{html}</ol>'
            content_html = f'<p>{html}</p>'

        # SINGLE complete HTML block - no split calls!
        st.markdown(f"""
            <div class="modern-card" id="{card_id}">
                {header_html}
                <div class="modern-card-content">
                    {content_html}
                </div>
            </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def stats_card(value: str, label: str, icon: str = "", 
                   trend: str = "", key: str = None) -> None:
        """
        Render a statistics card with modern styling
        
        Args:
            value: The main statistic value
            label: Description of the statistic
            icon: Optional icon
            trend: Optional trend indicator
            key: Unique key for the component
        """
        card_id = key or f"stats_{_stable_hash(value + label)}"
        
        st.markdown(f"""
            <div class="stats-card" id="{card_id}">
                {f'<div style="font-size: 2em; margin-bottom: 8px;">{icon}</div>' if icon else ""}
                <div class="stats-value">{value}</div>
                <div class="stats-label">{label}</div>
                {f'<div style="font-size: 0.875rem; margin-top: 8px; opacity: 0.8;">{trend}</div>' if trend else ""}
            </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def progress_steps(steps: List[Dict[str, Any]], current_step: int = 0) -> None:
        """
        Render a modern progress steps component using native Streamlit

        Args:
            steps: List of step dictionaries with 'title' and optional 'icon'
            current_step: Index of the current active step (0-based)
        """
        # Use native Streamlit columns for reliable rendering
        cols = st.columns(len(steps))

        for i, (col, step) in enumerate(zip(cols, steps)):
            with col:
                # Determine status and styling
                if i < current_step:
                    status_icon = "✅"
                    color = "#2D5A3D"  # forest green
                elif i == current_step:
                    status_icon = step.get('icon', '🔄')
                    color = "#B8860B"  # scholar gold
                else:
                    status_icon = step.get('icon', '⏳')
                    color = "#9A9589"  # warm gray

                # Render step with markdown
                st.markdown(f"""
                    <div style="text-align: center; padding: 8px;">
                        <div style="font-size: 1.5em; margin-bottom: 4px;">{status_icon}</div>
                        <div style="font-size: 0.75em; color: {color}; font-weight: {'600' if i <= current_step else '400'};">
                            {step['title']}
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    @staticmethod
    def section_header(title: str, icon: str = "", section_type: str = "generate") -> None:
        """
        Render a modern section header
        
        Args:
            title: Section title
            icon: Optional icon
            section_type: Type of section (generate, edit, export, templates)
        """
        st.markdown(f"""
            <div class="section-header">
                <div class="section-icon {section_type}">
                    {icon or "📝"}
                </div>
                <h2 style="margin: 0; font-size: 1.5rem; font-weight: 600;">{title}</h2>
            </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def dashboard_grid(items: List[str], columns: int = 3) -> None:
        """
        Create a responsive dashboard grid layout
        
        Args:
            items: List of HTML content for grid items
            columns: Number of columns (default: 3)
        """
        grid_items = ''.join(items)
        
        st.markdown(f"""
            <div class="dashboard-grid" style="grid-template-columns: repeat({columns}, 1fr);">
                {grid_items}
            </div>
        """, unsafe_allow_html=True)

    @staticmethod
    def quick_action_button(title: str, description: str, icon: str = "", 
                           action_key: str = "", disabled: bool = False) -> bool:
        """
        Render a quick action button card
        
        Args:
            title: Button title
            description: Button description
            icon: Optional icon
            action_key: Unique key for the button
            disabled: Whether the button is disabled
        
        Returns:
            bool: True if button was clicked
        """
        button_id = action_key or f"action_{_stable_hash(title)}"
        disabled_style = "opacity: 0.5; pointer-events: none;" if disabled else ""
        
        # Create the card content
        card_content = f"""
            <div class="modern-card" style="cursor: pointer; {disabled_style}" onclick="document.getElementById('{button_id}_btn').click();">
                <div class="modern-card-header">
                    {f'<span style="font-size: 2em;">{icon}</span>' if icon else ""}
                    <div>
                        <h3 class="modern-card-title">{title}</h3>
                        <p class="modern-card-subtitle">{description}</p>
                    </div>
                </div>
            </div>
        """
        
        # Render the card
        st.markdown(card_content, unsafe_allow_html=True)
        
        # Hidden button for functionality
        return st.button(f"__{title}__", key=f"{button_id}_btn", 
                        disabled=disabled, help=description)

    @staticmethod
    def form_section(title: str, content_func, expanded: bool = True) -> None:
        """
        Create a modern form section with optional collapsing
        
        Args:
            title: Section title
            content_func: Function that renders the form content
            expanded: Whether the section starts expanded
        """
        with st.expander(title, expanded=expanded):
            st.markdown('<div class="form-section">', unsafe_allow_html=True)
            content_func()
            st.markdown('</div>', unsafe_allow_html=True)


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


class ThemeManager:
    """Manage theme switching and dark/light mode - Warm Scholar Style"""

    # Light theme CSS - Warm Scholar Parchment Style
    LIGHT_THEME_CSS = """
    <style id="theme-light">
        :root, .stApp {
            --accent-primary: #2D5A3D !important;
            --accent-primary-dark: #1E3D29 !important;
            --accent-secondary: #B8860B !important;
            --glass-bg: rgba(255, 254, 245, 0.75) !important;
            --glass-bg-strong: rgba(255, 254, 245, 0.92) !important;
            --glass-border: rgba(184, 134, 11, 0.15) !important;
            --text-primary: #3D3A33 !important;
            --text-secondary: #524F47 !important;
            --text-tertiary: #6B6558 !important;
            --separator: rgba(107, 101, 88, 0.12) !important;
            --surface-primary: #FFFEF5 !important;
            --bg-gradient: #F5F0E1 !important;
        }
        .stApp {
            background: #F5F0E1 !important;
            background-image:
                radial-gradient(ellipse at 0% 0%, rgba(184, 134, 11, 0.06) 0%, transparent 50%),
                radial-gradient(ellipse at 100% 100%, rgba(45, 90, 61, 0.04) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 50%, rgba(194, 120, 92, 0.03) 0%, transparent 50%) !important;
            background-attachment: fixed !important;
            color: #3D3A33 !important;
        }
        .stApp [data-testid="stSidebar"] {
            background: rgba(255, 254, 245, 0.92) !important;
            backdrop-filter: blur(24px) saturate(120%) !important;
            -webkit-backdrop-filter: blur(24px) saturate(120%) !important;
            border-right: 1px solid rgba(184, 134, 11, 0.15) !important;
        }
        .stApp [data-testid="stSidebar"] > div {
            background: transparent !important;
        }
        .stApp .stMarkdown, .stApp p, .stApp span, .stApp label {
            color: #524F47 !important;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
            color: #3D3A33 !important;
        }
        .stApp .stTextInput > div > div > input,
        .stApp .stTextArea > div > div > textarea,
        .stApp .stSelectbox > div > div {
            background: #FFFEF5 !important;
            border: 1.5px solid rgba(107, 101, 88, 0.12) !important;
            border-radius: 10px !important;
            color: #3D3A33 !important;
        }
        .stApp .stButton > button {
            background: linear-gradient(135deg, #2D5A3D 0%, #1E3D29 100%) !important;
            color: #FFFEF5 !important;
            border: none !important;
            border-radius: 14px !important;
            box-shadow: 0 4px 16px rgba(61, 58, 51, 0.09), 0 4px 12px rgba(45, 90, 61, 0.25) !important;
        }
        .stApp .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 32px rgba(61, 58, 51, 0.12), 0 8px 24px rgba(45, 90, 61, 0.35) !important;
        }
        .stApp .stTabs [data-baseweb="tab-list"] {
            background: rgba(255, 254, 245, 0.88) !important;
            backdrop-filter: blur(20px) !important;
            border-radius: 20px !important;
            padding: 4px !important;
            border: 1px solid rgba(184, 134, 11, 0.15) !important;
        }
        .stApp .stTabs [data-baseweb="tab"] {
            background: transparent !important;
            border-radius: 14px !important;
            color: #524F47 !important;
        }
        .stApp .stTabs [aria-selected="true"] {
            background: #FFFEF5 !important;
            color: #2D5A3D !important;
            box-shadow: 0 2px 8px rgba(61, 58, 51, 0.08) !important;
        }
        .stApp .stTabs [data-baseweb="tab-highlight"],
        .stApp .stTabs [data-baseweb="tab-border"] {
            display: none !important;
        }
        .stApp .streamlit-expanderHeader {
            background: rgba(255, 254, 245, 0.88) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(107, 101, 88, 0.12) !important;
            border-left: 3px solid #B8860B !important;
            border-radius: 14px !important;
            color: #3D3A33 !important;
        }
        .stApp [data-testid="stMetric"] {
            background: rgba(255, 254, 245, 0.88) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(184, 134, 11, 0.15) !important;
            border-radius: 20px !important;
            padding: 20px 24px !important;
        }
        .stApp [data-testid="stForm"] {
            background: rgba(255, 254, 245, 0.88) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(184, 134, 11, 0.15) !important;
            border-radius: 20px !important;
            padding: 24px !important;
        }
    </style>
    """

    # Dark theme CSS - Warm Scholar Evening Study
    DARK_THEME_CSS = """
    <style id="theme-dark">
        :root, .stApp {
            --accent-primary: #4A8B5C !important;
            --accent-primary-dark: #2D5A3D !important;
            --accent-secondary: #D4A84B !important;
            --glass-bg: rgba(38, 35, 30, 0.82) !important;
            --glass-bg-strong: rgba(38, 35, 30, 0.92) !important;
            --glass-border: rgba(212, 168, 75, 0.18) !important;
            --text-primary: #F5F0E1 !important;
            --text-secondary: #D4CFC0 !important;
            --text-tertiary: #9A9589 !important;
            --separator: rgba(154, 149, 137, 0.25) !important;
            --surface-primary: #2A2622 !important;
            --bg-gradient: #1E1B18 !important;
        }
        .stApp {
            background: #1E1B18 !important;
            background-image:
                radial-gradient(ellipse at 0% 0%, rgba(212, 168, 75, 0.08) 0%, transparent 50%),
                radial-gradient(ellipse at 100% 100%, rgba(74, 139, 92, 0.06) 0%, transparent 50%),
                radial-gradient(ellipse at 50% 50%, rgba(194, 120, 92, 0.04) 0%, transparent 50%) !important;
            background-attachment: fixed !important;
            color: #F5F0E1 !important;
        }
        .stApp [data-testid="stSidebar"] {
            background: rgba(38, 35, 30, 0.92) !important;
            backdrop-filter: blur(24px) saturate(120%) !important;
            -webkit-backdrop-filter: blur(24px) saturate(120%) !important;
            border-right: 1px solid rgba(212, 168, 75, 0.18) !important;
        }
        .stApp [data-testid="stSidebar"] > div {
            background: transparent !important;
        }
        .stApp .stMarkdown, .stApp p, .stApp span, .stApp label {
            color: #D4CFC0 !important;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
            color: #F5F0E1 !important;
        }
        .stApp .stTextInput > div > div > input,
        .stApp .stTextArea > div > div > textarea,
        .stApp .stSelectbox > div > div {
            background: rgba(42, 38, 34, 0.85) !important;
            backdrop-filter: blur(8px) !important;
            border: 1.5px solid rgba(154, 149, 137, 0.25) !important;
            border-radius: 10px !important;
            color: #F5F0E1 !important;
        }
        .stApp .stButton > button {
            background: linear-gradient(135deg, #4A8B5C 0%, #2D5A3D 100%) !important;
            color: #F5F0E1 !important;
            border: none !important;
            border-radius: 14px !important;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25), 0 4px 12px rgba(74, 139, 92, 0.28) !important;
        }
        .stApp .stButton > button:hover {
            transform: translateY(-2px) !important;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.35), 0 8px 24px rgba(74, 139, 92, 0.38) !important;
        }
        .stApp .stTabs [data-baseweb="tab-list"] {
            background: rgba(38, 35, 30, 0.82) !important;
            backdrop-filter: blur(20px) !important;
            border-radius: 20px !important;
            padding: 4px !important;
            border: 1px solid rgba(212, 168, 75, 0.18) !important;
        }
        .stApp .stTabs [data-baseweb="tab"] {
            background: transparent !important;
            border-radius: 14px !important;
            color: #D4CFC0 !important;
        }
        .stApp .stTabs [aria-selected="true"] {
            background: rgba(255, 254, 245, 0.08) !important;
            color: #D4A84B !important;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.2) !important;
        }
        .stApp .stTabs [data-baseweb="tab-highlight"],
        .stApp .stTabs [data-baseweb="tab-border"] {
            display: none !important;
        }
        .stApp .streamlit-expanderHeader {
            background: rgba(38, 35, 30, 0.82) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(154, 149, 137, 0.25) !important;
            border-left: 3px solid #D4A84B !important;
            border-radius: 14px !important;
            color: #F5F0E1 !important;
        }
        .stApp [data-testid="stMetric"] {
            background: rgba(38, 35, 30, 0.82) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(212, 168, 75, 0.18) !important;
            border-radius: 20px !important;
            padding: 20px 24px !important;
        }
        .stApp [data-testid="stForm"] {
            background: rgba(38, 35, 30, 0.82) !important;
            backdrop-filter: blur(20px) !important;
            border: 1px solid rgba(212, 168, 75, 0.18) !important;
            border-radius: 20px !important;
            padding: 24px !important;
        }
        /* Dark mode specific fixes */
        .stApp .stAlert {
            background: rgba(38, 35, 30, 0.82) !important;
            border: 1px solid rgba(154, 149, 137, 0.25) !important;
        }
        .stApp .streamlit-expanderContent {
            background: rgba(42, 38, 34, 0.65) !important;
            border-color: rgba(154, 149, 137, 0.25) !important;
            border-left: 3px solid rgba(212, 168, 75, 0.5) !important;
        }
    </style>
    """

    @staticmethod
    def apply_theme(theme: str = "light") -> None:
        """Apply theme CSS directly for immediate effect"""
        if theme == "dark":
            st.markdown(ThemeManager.DARK_THEME_CSS, unsafe_allow_html=True)
        else:
            st.markdown(ThemeManager.LIGHT_THEME_CSS, unsafe_allow_html=True)

    @staticmethod
    def get_theme_toggle() -> str:
        """Get theme toggle component"""
        if "theme" not in st.session_state:
            st.session_state.theme = "light"

        # Theme toggle with selectbox for cleaner UI
        theme_choice = st.selectbox(
            "🎨 Theme",
            ["Light", "Dark"],
            index=0 if st.session_state.theme == "light" else 1,
            key="theme_selector"
        )

        # Update theme and rerun if changed
        new_theme = "light" if theme_choice == "Light" else "dark"
        if new_theme != st.session_state.theme:
            st.session_state.theme = new_theme
            st.rerun()

        # Apply theme CSS
        ThemeManager.apply_theme(new_theme)

        return new_theme

class LayoutHelpers:
    """Helper functions for common layout patterns"""
    
    @staticmethod
    def two_column_layout(left_content_func, right_content_func, 
                         ratio: List[int] = [2, 1]) -> None:
        """Create a two-column layout with custom ratios"""
        col1, col2 = st.columns(ratio)
        
        with col1:
            left_content_func()
        
        with col2:
            right_content_func()
    
    @staticmethod
    def three_column_layout(left_func, center_func, right_func) -> None:
        """Create a three-column layout"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            left_func()
        
        with col2:
            center_func()
        
        with col3:
            right_func()
    
    @staticmethod
    def responsive_columns(content_funcs: List, min_width: int = 300) -> None:
        """Create responsive columns based on content"""
        num_cols = min(len(content_funcs), 3)  # Max 3 columns
        cols = st.columns(num_cols)

        for i, func in enumerate(content_funcs):
            with cols[i % num_cols]:
                func()


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

            submitted = st.form_submit_button("Add Child", use_container_width=True)

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