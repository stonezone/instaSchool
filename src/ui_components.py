"""
UI Components and Styling Helpers for InstaSchool
Provides reusable UI components and modern styling utilities
"""

import streamlit as st
from pathlib import Path
from typing import Dict, Any, Optional, List

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
        card_id = key or f"card_{hash(title + content)}"

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
        card_id = key or f"stats_{hash(value + label)}"
        
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
                    color = "#10b981"  # green
                elif i == current_step:
                    status_icon = step.get('icon', '🔄')
                    color = "#3b82f6"  # blue
                else:
                    status_icon = step.get('icon', '⏳')
                    color = "#94a3b8"  # gray

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
        button_id = action_key or f"action_{hash(title)}"
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
    """Manage theme switching and dark/light mode"""

    # Dark theme CSS variables
    DARK_THEME_CSS = """
    <style>
        :root, .stApp {
            --primary-50: #1e293b !important;
            --primary-100: #334155 !important;
            --neutral-50: #0f172a !important;
            --neutral-100: #1e293b !important;
            --neutral-200: #334155 !important;
            --neutral-300: #475569 !important;
            --neutral-800: #f1f5f9 !important;
            --neutral-900: #ffffff !important;
            --card-bg: #1e1e2e !important;
            --border-color: #313244 !important;
            --hover-shadow: 0 4px 12px rgba(0, 0, 0, 0.3) !important;
        }
        .stApp {
            background-color: #0f172a !important;
            color: #f1f5f9 !important;
        }
        .stApp [data-testid="stSidebar"] {
            background-color: #1e293b !important;
        }
        .stApp .stMarkdown, .stApp p, .stApp span, .stApp label {
            color: #f1f5f9 !important;
        }
        .stApp h1, .stApp h2, .stApp h3, .stApp h4 {
            color: #ffffff !important;
        }
        .stApp .stTextInput input, .stApp .stSelectbox select {
            background-color: #334155 !important;
            color: #f1f5f9 !important;
        }
    </style>
    """

    @staticmethod
    def apply_theme(theme: str = "light") -> None:
        """Apply theme CSS directly for immediate effect"""
        if theme == "dark":
            st.markdown(ThemeManager.DARK_THEME_CSS, unsafe_allow_html=True)
        # Light theme uses default CSS variables from design_system.css

    @staticmethod
    def get_theme_toggle() -> str:
        """Get theme toggle component"""
        if "theme" not in st.session_state:
            st.session_state.theme = "light"

        # Theme toggle with selectbox for cleaner UI
        col1, col2 = st.columns([1, 1])
        with col1:
            theme_choice = st.selectbox(
                "🎨 Theme",
                ["Light", "Dark"],
                index=0 if st.session_state.theme == "light" else 1,
                key="theme_selector",
                label_visibility="collapsed"
            )

        # Update theme
        new_theme = "light" if theme_choice == "Light" else "dark"
        if new_theme != st.session_state.theme:
            st.session_state.theme = new_theme

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