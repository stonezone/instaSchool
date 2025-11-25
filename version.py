"""
InstaSchool Version Management

IMPORTANT: Bump VERSION with each git commit/revision.
Format: MAJOR.MINOR.PATCH
- MAJOR: Breaking changes or major feature releases
- MINOR: New features, enhancements
- PATCH: Bug fixes, small improvements
"""

VERSION = "0.8.0"
VERSION_NAME = "Classroom OS Foundation"

# Changelog for reference
CHANGELOG = {
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
