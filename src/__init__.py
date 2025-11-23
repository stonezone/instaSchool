# InstaSchool Source Package
"""
Core modules for the InstaSchool curriculum generation application.
"""

# CRITICAL: Set matplotlib backend BEFORE any other imports
# This must be the first thing that happens to avoid backend conflicts
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for headless environments

# Export BaseAgent from core for convenience
from src.core.types import BaseAgent

__all__ = ['BaseAgent']
