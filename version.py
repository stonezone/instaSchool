"""
InstaSchool Version Management

IMPORTANT: Bump VERSION with each git commit/revision.
Format: MAJOR.MINOR.PATCH
- MAJOR: Breaking changes or major feature releases
- MINOR: New features, enhancements
- PATCH: Bug fixes, small improvements
"""

VERSION = "1.6.2"
VERSION_NAME = "Error Handling & Logging"

# Changelog for reference
CHANGELOG = {
    "1.6.2": {
        "date": "2025-11-27",
        "name": "Error Handling & Logging",
        "changes": [
            "grading_agent.py: Use specific exceptions (APIError, RateLimitError, JSONDecodeError)",
            "progress_manager.py: Use sqlite3.Error for database operations",
            "All updated files now use VerboseLogger instead of print()",
            "Proper error logging with context for debugging",
        ]
    },
    "1.6.1": {
        "date": "2025-11-27",
        "name": "Review Queue XP Rewards",
        "changes": [
            "Review Queue now awards +5 XP for successful flashcard reviews",
            "XP feedback displayed in toast messages after each review",
            "TODO.md consolidated with verified code status",
        ]
    },
    "1.6.0": {
        "date": "2025-11-27",
        "name": "Student Progress & SRS Upgrade",
        "changes": [
            "Unified student progress between JSON files and SQLite database",
            "Student Mode progress now powers Parent and Teacher analytics dashboards",
            "SRS Review Queue now auto-creates flashcards from completed quizzes",
            "Grading agent now distinguishes graded vs fallback and never marks failed API calls as correct",
            "Model detector and provider defaults updated for modern GPT-4o/4.1/5 and gpt-image-1",
            "Updated Streamlit to 1.51.0 (custom components v2, themes)",
            "Updated OpenAI SDK to 2.8.1 (GPT-5.1 support)",
            "Python 3.9+ now required (OpenAI SDK 2.x requirement)",
        ]
    },
    "1.5.7": {
        "date": "2025-11-26",
        "name": "Sidebar & Provider Cleanup",
        "changes": [
            "Wider sidebar (360px) - all text now visible without cutoff",
            "Collapse button highlighted with hover effect",
            "REMOVED: DeepSeek and Ollama providers (only OpenAI + Kimi remain)",
            "Fixed: Kimi models now validated correctly (kimi-k2-thinking, kimi-k2-turbo-preview)",
            "Config.yaml text_models now includes Kimi models for validation",
        ]
    },
    "1.5.6": {
        "date": "2025-11-26",
        "name": "Model List Cleanup",
        "changes": [
            "OpenAI text: gpt-4o, chatgpt-4o-latest, gpt-4o-mini/nano, gpt-4.1/mini/nano, gpt-5/mini/nano",
            "Kimi text: kimi-k2-thinking (main), kimi-k2-turbo-preview (worker)",
            "Image models: ONLY gpt-image-1 and gpt-image-1-mini (removed DALL-E)",
            "Cross-provider routing: Any provider can use OpenAI for images",
            "Updated all defaults and help text to use gpt-image-1",
        ]
    },
    "1.5.5": {
        "date": "2025-11-26",
        "name": "Kimi Thinking Model",
        "changes": [
            "Kimi default main model: kimi-k2-thinking (smart reasoning)",
            "Kimi worker model: kimi-k2-turbo-preview (fast processing)",
            "Cross-provider: Kimi for text/reasoning, OpenAI for images",
            "Added MOONSHOT_API_KEY as fallback for KIMI_API_KEY",
            "Simplified Kimi text_models list (removed vision models)",
        ]
    },
    "1.5.4": {
        "date": "2025-11-26",
        "name": "Technical Debt Cleanup",
        "changes": [
            "Fixed Parent mode Reports/Certificates identifier handling",
            "Migrated AnalyticsService from JSON to SQLite database",
            "Fixed AI provider config mismatch (ai_providers block now read)",
            "Added missing 'requests' dependency to requirements.txt",
            "Fixed Parent Curricula metadata (reads from meta fields)",
            "Removed unnecessary threading lock from StateManager",
            "Fixed widget key collisions (hash() → hashlib.md5)",
            "Added startup temp file cleanup for orphaned files",
            "Enhanced exception logging with traceback support",
            "Consolidated state initialization in StateManager.DEFAULTS",
            "Added CSS fallback warning when design_system.css missing",
            "Version number now displayed at bottom of UI",
        ]
    },
    "1.5.3": {
        "date": "2025-11-26",
        "name": "Smart Provider Models",
        "changes": [
            "Model dropdown now shows SELECTED PROVIDER's models (not always OpenAI)",
            "REMOVED: GPT 3.x models (outdated)",
            "ADDED: gpt-4.1-mini, gpt-4.1-nano, gpt-5-mini models",
            "Provider cost tiers: FREE (Kimi), Low Cost (DeepSeek), Paid (OpenAI)",
            "Image section clearly states OpenAI required for images",
            "Fixed widget key conflicts in cross-provider mode",
            "Enhanced Liquid Glass UI throughout site",
        ]
    },
    "1.5.2": {
        "date": "2025-11-26",
        "name": "Multi-Provider + Quickstart",
        "changes": [
            "NEW: Quickstart guide for new users after login",
            "NEW: DeepSeek provider support (cheap reasoning models)",
            "Cost optimization: OpenAI limited to gpt-4o-mini + images only",
            "Kimi K2 recommended as default (FREE text generation)",
            "Three-button quickstart: Go, Skip Forever, Show Later",
            "Updated provider service with 4 providers: OpenAI, Kimi, DeepSeek, Ollama",
        ]
    },
    "1.5.1": {
        "date": "2025-11-26",
        "name": "Deployment Ready",
        "changes": [
            "NEW: Password protection for app security (APP_PASSWORD env var)",
            "Created .env_example template for easy deployment setup",
            "Environment variable documentation for all API keys",
            "Login page with glassmorphism styling",
            "Session-based authentication persistence",
            "Ready for cloud deployment (Streamlit Cloud, Railway, Render)",
        ]
    },
    "1.5.0": {
        "date": "2025-11-26",
        "name": "Liquid Glass UI",
        "changes": [
            "NEW: Apple-inspired Liquid Glass design system",
            "Glassmorphism effects with backdrop blur throughout UI",
            "Subtle mesh gradient backgrounds (blue/purple/teal)",
            "Modern pill-style tabs with glass effect",
            "Refined typography with Inter font family",
            "Smooth hover animations and transitions",
            "Better dark mode with deep space aesthetic",
            "Improved button styling with gradient and glow",
            "Glass-styled forms, inputs, and cards",
            "Enhanced sidebar with frosted glass effect",
            "Fixed theme toggle to properly switch light/dark",
        ]
    },
    "1.4.0": {
        "date": "2025-11-26",
        "name": "GUI Overhaul & Parent Mode",
        "changes": [
            "NEW: Dedicated Parent Mode with family-focused interface",
            "Role-based mode switcher: Parent / Create / Student",
            "Parent Dashboard with 4 tabs: Family Overview, Reports, Curricula, Settings",
            "Beautiful empty state onboarding for new users",
            "Streamlined teacher mode: reduced from 7 to 6 tabs",
            "Family features moved from teacher to parent mode",
            "Cleaner navigation and improved UX flow",
            "Better separation of concerns between parent oversight and content creation",
        ]
    },
    "1.3.0": {
        "date": "2025-11-26",
        "name": "Engagement & Motivation",
        "changes": [
            "Daily Challenges system with XP rewards",
            "10 different challenge types (review cards, units, quizzes, tutor questions)",
            "Challenge progress tracking with visual indicators",
            "Enhanced badge system with 30+ achievement badges",
            "Subject-specific badges (Scientist, Mathematician, etc.)",
            "Fun badges (Night Owl, Early Bird)",
            "Printable PDF Certificates (completion, progress, custom)",
            "Certificates tab in Family Dashboard",
            "Daily challenge sidebar in student mode",
        ]
    },
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
