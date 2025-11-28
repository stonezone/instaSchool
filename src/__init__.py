# InstaSchool Source Package
"""
Core modules for the InstaSchool curriculum generation application.
"""

# CRITICAL: Set matplotlib backend BEFORE any other imports
# This must be the first thing that happens to avoid backend conflicts
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for headless environments

# Lazy export to prevent module caching issues on Streamlit Cloud reloads
# Import BaseAgent directly when needed: from src.core.types import BaseAgent
__all__ = []

def get_base_agent():
    """Lazy loader for BaseAgent to avoid module import crashes"""
    from src.core.types import BaseAgent
    return BaseAgent
