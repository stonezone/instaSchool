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
        Render a modern card component
        
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
        
        # Render the card container with header
        st.markdown(f"""
            <div class="modern-card" id="{card_id}">
                {header_html}
                <div class="modern-card-content">
        """, unsafe_allow_html=True)
        
        # Render the content as markdown (this allows proper markdown processing)
        if content:
            st.markdown(content)
        
        # Close the card container
        st.markdown("""
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
        Render a modern progress steps component
        
        Args:
            steps: List of step dictionaries with 'title' and optional 'icon'
            current_step: Index of the current active step (0-based)
        """
        steps_html = []
        
        for i, step in enumerate(steps):
            if i < current_step:
                status = "completed"
                icon = "✓"
            elif i == current_step:
                status = "active"
                icon = str(i + 1)
            else:
                status = "pending"
                icon = str(i + 1)
            
            step_icon = step.get('icon', icon)
            
            steps_html.append(f"""
                <div class="progress-step {status}">
                    <div class="progress-step-icon">{step_icon}</div>
                    <span>{step['title']}</span>
                </div>
            """)
        
        st.markdown(f"""
            <div class="modern-progress-container">
                <div class="progress-steps">
                    {''.join(steps_html)}
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

class ThemeManager:
    """Manage theme switching and dark/light mode"""
    
    @staticmethod
    def set_theme_attribute(theme: str = "light") -> None:
        """Set the theme data attribute for CSS styling"""
        st.markdown(f"""
            <script>
                document.documentElement.setAttribute('data-theme', '{theme}');
            </script>
        """, unsafe_allow_html=True)
    
    @staticmethod
    def get_theme_toggle() -> str:
        """Get theme toggle component"""
        if "theme" not in st.session_state:
            st.session_state.theme = "light"
        
        # Theme toggle
        theme = st.radio(
            "Theme", 
            ["Light", "Dark"], 
            index=0 if st.session_state.theme == "light" else 1, 
            horizontal=True,
            key="theme_toggle"
        )
        
        # Update theme
        new_theme = "light" if theme == "Light" else "dark"
        if new_theme != st.session_state.theme:
            st.session_state.theme = new_theme
            st.rerun()
        
        # Set theme attribute
        ThemeManager.set_theme_attribute(new_theme)
        
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