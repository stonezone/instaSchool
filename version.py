"""
InstaSchool Version Management

IMPORTANT: Bump VERSION with each git commit/revision.
Format: MAJOR.MINOR.PATCH
- MAJOR: Breaking changes or major feature releases
- MINOR: New features, enhancements
- PATCH: Bug fixes, small improvements
"""

VERSION = "0.9.2"
VERSION_NAME = "Spaced Repetition"

# Changelog for reference
CHANGELOG = {
    "0.9.2": {
        "date": "2025-11-25",
        "name": "Spaced Repetition",
        "changes": [
            "SM-2 spaced repetition algorithm for flashcard scheduling",
            "SRS service with create/review/due cards functionality",
            "Review Queue UI in student mode with quality buttons",
            "Sidebar integration showing due card count",
            "View switching between Learn and Review modes",
            "Foundation for Phase 1 learning science features",
        ]
    },
    "0.9.1": {
        "date": "2025-11-25",
        "name": "SQLite Database",
        "changes": [
            "SQLite database service for local-first data storage",
            "Automatic JSON-to-SQLite migration for existing users",
            "Database tables: users, curricula, progress, review_items",
            "Thread-safe database operations with context managers",
            "User service refactored to use DatabaseService",
            "Database backup/export functionality",
            "Ready for Phase 1: Spaced Repetition System (SRS)",
        ]
    },
    "0.9.0": {
        "date": "2025-11-25",
        "name": "Multi-Provider AI",
        "changes": [
            "Multi-AI provider support: OpenAI, Kimi K2 (free!), Ollama (local)",
            "Provider switcher in sidebar - switch AI backends on the fly",
            "Kimi K2 integration with OpenAI-compatible API",
            "Provider service abstraction for clean architecture",
            "Revised ROADMAP for homeschool family focus",
            "Local-first design philosophy",
            "SQLite database schema ready (migration pending)",
        ]
    },
    "0.8.3": {
        "date": "2025-11-25",
        "name": "Production Refinement",
        "changes": [
            "StateManager enforcement in student_ui.py (no direct st.session_state)",
            "PIN-based authentication for student profiles (optional security)",
            "Profile switching with PIN lock indicators",
            "Mobile layout toggle in preferences",
            "Standardized logging in audio_agent (verbose_logger)",
            "Code quality improvements throughout",
        ]
    },
    "0.8.2": {
        "date": "2025-11-25",
        "name": "Gamification & AI Grading",
        "changes": [
            "AI Grading Agent for short-answer questions with constructive feedback",
            "Gamification 2.0: 15 badges system (Perfect Score, Streak, Curious Mind, etc.)",
            "Trophy Case in student sidebar with earned badges display",
            "Streak tracking for consecutive study days",
            "Badge notifications via toast when new badges earned",
            "Course completion screen with badge showcase",
        ]
    },
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
