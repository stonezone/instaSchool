"""
InstaSchool Version Management

IMPORTANT: Bump VERSION with each git commit/revision.
Format: MAJOR.MINOR.PATCH
- MAJOR: Breaking changes or major feature releases
- MINOR: New features, enhancements
- PATCH: Bug fixes, small improvements
"""

VERSION = "1.0.2"
VERSION_NAME = "Curriculum Customization"

# Changelog for reference
CHANGELOG = {
    "1.0.2": {
        "date": "2025-11-26",
        "name": "Curriculum Customization",
        "changes": [
            "Parent Controls panel in View & Edit tab",
            "Content depth selector (brief/standard/deep)",
            "Supplemental resources management with add/remove",
            "Per-unit Skip functionality to hide units from students",
            "Per-unit Flag for Review before showing to students",
            "Custom parent notes per unit",
            "Visual indicators for skipped/flagged units",
            "CustomizationService with database persistence",
        ]
    },
    "1.0.1": {
        "date": "2025-11-26",
        "name": "Progress Reports",
        "changes": [
            "PDF Progress Report generation using fpdf2",
            "ReportService for generating child and family reports",
            "Beautiful PDF layout with progress bars and stat boxes",
            "Downloadable PDF reports from Family Dashboard",
            "Individual child reports with curriculum breakdown",
            "Family-wide reports with all children's progress",
            "Personalized recommendations in family reports",
        ]
    },
    "1.0.0": {
        "date": "2025-11-26",
        "name": "Family Dashboard",
        "changes": [
            "Multi-child Family Dashboard for parent overview",
            "FamilyService for aggregating family-wide learning data",
            "Child progress cards with streak, XP, due reviews",
            "Family totals summary (total XP, sections, active today)",
            "Child management: add new profiles from dashboard",
            "Weekly progress reports (preview with PDF coming soon)",
            "Individual and family-wide report generation",
            "New tab structure: 7 tabs including Family tab",
        ]
    },
    "0.9.5": {
        "date": "2025-11-26",
        "name": "UI/UX Foundation",
        "changes": [
            "Fixed font loading: Added Google Fonts import for Inter font",
            "Created .streamlit/config.toml for native theme support",
            "Fixed dark mode: Direct CSS injection for immediate effect",
            "Added system prefers-color-scheme fallback for dark mode",
            "Real-time generation logs with st.status() API",
            "StatusLogger component for expandable generation feedback",
            "Improved theme toggle UX with selectbox",
        ]
    },
    "0.9.4": {
        "date": "2025-11-26",
        "name": "Cross-Provider & Fixes",
        "changes": [
            "Cross-provider orchestration: Kimi for text + OpenAI for images",
            "Fixed PDF export: handle quiz as list not dict",
            "Fixed cost estimation: added Kimi (FREE) and image model costs",
            "Per-task provider configuration (orchestrator, worker, image)",
            "HTML and Markdown export fixes for quiz format",
        ]
    },
    "0.9.3": {
        "date": "2025-11-25",
        "name": "Mastery Gates",
        "changes": [
            "80% quiz score required to advance to next unit",
            "Quiz score tracking with attempts count",
            "Retry mechanism for failed quizzes",
            "Parent override option for flexibility",
            "Clear feedback on mastery requirements",
        ]
    },
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
