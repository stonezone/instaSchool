"""
InstaSchool Version Management

IMPORTANT: Bump VERSION with each git commit/revision.
Format: MAJOR.MINOR.PATCH
- MAJOR: Breaking changes or major feature releases
- MINOR: New features, enhancements
- PATCH: Bug fixes, small improvements
"""

VERSION = "0.8.1"
VERSION_NAME = "Analytics & Fixes"

# Changelog for reference
CHANGELOG = {
    "0.8.1": {
        "date": "2025-11-25",
        "name": "Analytics & Fixes",
        "changes": [
            "Teacher Analytics Dashboard with student leaderboard and curriculum insights",
            "Fixed PDF/HTML export image key mismatch (selected_image_b64)",
            "Robust cost estimator with dynamic model matching (gpt-4-turbo, gpt-3.5, etc.)",
            "Quiz state management via StateManager (atomic updates)",
            "Improved tutor context transitions between units",
        ]
    },
    "0.8.0": {
        "date": "2025-11-25",
        "name": "Classroom OS Foundation",
        "changes": [
            "Multi-user student profiles with per-user progress tracking",
            "Fixed PDF export using fpdf2 (no OS dependencies)",
            "State management enforcement via StateManager",
            "Dynamic cost estimation for new models",
            "gpt-5-nano temperature parameter fix",
        ]
    }
}


def get_version() -> str:
    """Get current version string"""
    return VERSION


def get_version_display() -> str:
    """Get formatted version for display"""
    return f"v{VERSION} - {VERSION_NAME}"


def get_full_version_info() -> dict:
    """Get complete version information"""
    return {
        "version": VERSION,
        "name": VERSION_NAME,
        "changelog": CHANGELOG.get(VERSION, {})
    }
