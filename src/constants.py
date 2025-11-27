"""
InstaSchool Constants

Centralized configuration values to avoid magic numbers scattered throughout the codebase.
Import from here instead of hardcoding values.
"""

# =============================================================================
# GAMIFICATION - XP & LEVELS
# =============================================================================

XP_PER_LEVEL = 100  # XP needed to advance one level

# XP Awards
XP_SECTION_COMPLETE = 10      # Completing a lesson section
XP_QUIZ_PERFECT = 50          # Getting 100% on a quiz
XP_FLASHCARD_REVIEW = 5       # Successfully reviewing a flashcard
XP_SHORT_ANSWER_MAX = 20      # Maximum XP for a short answer (scaled by score)

# Mastery
MASTERY_THRESHOLD = 0.8       # 80% quiz score required to advance


# =============================================================================
# CONTENT LIMITS
# =============================================================================

# Text truncation limits for API calls
LESSON_SUMMARY_MAX_CHARS = 1500   # Max chars for lesson summaries in prompts
UNIT_CONTENT_MAX_CHARS = 2000    # Max chars for unit content in prompts
SESSION_DATA_MAX_CHARS = 2000    # Max chars for session data storage

# Conversation/history limits
TUTOR_MAX_HISTORY = 5            # Max conversation turns to remember


# =============================================================================
# CACHING
# =============================================================================

AUDIO_CACHE_EXPIRY_DAYS = 30     # Days before audio cache expires


# =============================================================================
# API & NETWORK
# =============================================================================

# Timeouts (seconds)
IMAGE_FETCH_TIMEOUT = 15         # Timeout for fetching generated images
THREAD_JOIN_TIMEOUT = 5.0        # Default thread join timeout
THREAD_SHUTDOWN_TIMEOUT = 10.0   # Timeout for thread pool shutdown

# Retry settings
DEFAULT_MAX_RETRIES = 3
DEFAULT_MAX_RETRY_DELAY = 60.0   # Max delay between retries (seconds)


# =============================================================================
# IMAGE GENERATION
# =============================================================================

IMAGE_PROMPT_MAX_LENGTH = {
    "gpt-image-1": 32000,
    "gpt-image-1-mini": 32000,
    "default": 1000,
}


# =============================================================================
# UI SETTINGS
# =============================================================================

SIDEBAR_WIDTH_PX = 360           # Sidebar width in pixels
PIN_MAX_CHARS = 6                # Max characters for student PIN


# =============================================================================
# COST ESTIMATION (Token estimates per component)
# =============================================================================

COST_ESTIMATE_TOKENS = {
    "orchestrator": {"input": 2000, "output": 1000},
    "outline": {"input": 1500, "output": 800},
    "content_per_unit": {"input": 2000, "output": 3000},
}
