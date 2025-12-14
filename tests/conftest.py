"""
Pytest configuration and shared fixtures for InstaSchool tests.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path for imports
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def sample_config():
    """Minimal config for testing services."""
    return {
        "defaults": {
            "provider": "openai",
            "main_model": "gpt-5-nano",
            "worker_model": "gpt-5-nano",
        },
        "providers": {},
    }


@pytest.fixture
def sample_curriculum():
    """Sample curriculum structure for testing."""
    return {
        "meta": {
            "title": "Test Curriculum",
            "subject": "Science",
            "grade": "5",
            "created_at": "2025-01-01T00:00:00",
        },
        "units": [
            {
                "title": "Unit 1",
                "content": "Test content",
                "quiz": {"questions": []},
                "resources": [],
            },
            {
                "title": "Unit 2",
                "content": "More content",
                "quiz": {"questions": []},
                "resources": [],
            },
        ],
    }
