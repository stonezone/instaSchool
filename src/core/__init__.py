"""
Core module for InstaSchool
Contains base types and shared definitions to prevent circular dependencies
"""

# Lazy export to prevent module caching issues on Streamlit Cloud (Python 3.13)
# During app reloads, sys.modules can get into inconsistent state causing KeyError
# Import directly when needed: from src.core.types import BaseAgent
__all__ = []

def get_base_agent():
    """Lazy loader for BaseAgent to avoid module import crashes on reload"""
    from .types import BaseAgent
    return BaseAgent
