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
# LLM PARAMETERS
# =============================================================================

# Temperature settings for different use cases
LLM_TEMPERATURE_DEFAULT = 0.7     # Default temperature for balanced output
LLM_TEMPERATURE_CREATIVE = 0.8    # Higher temperature for creative content
LLM_TEMPERATURE_PRECISE = 0.3     # Lower temperature for precise, factual content


# =============================================================================
# MODEL DEFAULTS
# =============================================================================

DEFAULT_MAIN_MODEL = "gpt-4.1"         # Primary model for orchestration
DEFAULT_WORKER_MODEL = "gpt-4.1-mini"  # Worker model for agent tasks
DEFAULT_IMAGE_MODEL = "gpt-image-1"    # Default image generation model


# =============================================================================
# PROGRESS TRACKING
# =============================================================================

# Progress milestones (0.0 to 1.0 scale)
PROGRESS_PLANNING_OUTLINE = 0.3    # After planning/outline phase
PROGRESS_CONTENT_ALLOCATION = 0.6  # After content allocation
PROGRESS_FINAL = 0.9               # Before final completion


# =============================================================================
# CONTENT LIMITS
# =============================================================================

# Text truncation limits for API calls
LESSON_SUMMARY_MAX_CHARS = 1500   # Max chars for lesson summaries in prompts
UNIT_CONTENT_MAX_CHARS = 2000     # Max chars for unit content in prompts
SESSION_DATA_MAX_CHARS = 2000     # Max chars for session data storage
MAX_CONTENT_LENGTH = 2000         # General maximum content length

# Quiz limits
MAX_QUIZ_QUESTIONS = 10           # Maximum quiz questions per assessment
MIN_QUIZ_QUESTIONS = 3            # Minimum quiz questions per assessment

# Conversation/history limits
TUTOR_MAX_HISTORY = 5             # Max conversation turns to remember


# =============================================================================
# CACHING
# =============================================================================

AUDIO_CACHE_EXPIRY_DAYS = 30     # Days before audio cache expires


# =============================================================================
# API & NETWORK
# =============================================================================

# Timeouts (seconds)
API_TIMEOUT_SECONDS = 60         # General API call timeout
IMAGE_FETCH_TIMEOUT = 15         # Timeout for fetching generated images
THREAD_JOIN_TIMEOUT = 5.0        # Default thread join timeout
THREAD_SHUTDOWN_TIMEOUT = 10.0   # Timeout for thread pool shutdown

# Retry settings
MAX_RETRIES = 3                  # Maximum number of retry attempts
DEFAULT_MAX_RETRIES = 3
RETRY_DELAY_BASE = 1.0           # Base delay for exponential backoff (seconds)
DEFAULT_MAX_RETRY_DELAY = 60.0   # Max delay between retries (seconds)


# =============================================================================
# IMAGE GENERATION
# =============================================================================

IMAGE_PROMPT_MAX_LENGTH = {
    "gpt-image-1": 32000,
    "gpt-image-1-mini": 32000,
    "default": 1000,
}

# Image size settings
IMAGE_SIZE_DEFAULT = "1024x1024"
IMAGE_SIZE_SMALL = "512x512"

# Image quality settings
IMAGE_QUALITY_HD = "hd"
IMAGE_QUALITY_STANDARD = "standard"

# Media richness thresholds
MEDIA_RICHNESS_IMAGE_THRESHOLD = 2   # Minimum richness for images
MEDIA_RICHNESS_HIGH = 5              # Threshold for high richness
IMAGE_COUNT_HIGH_RICHNESS = 3        # Number of images for high richness
IMAGE_COUNT_LOW_RICHNESS = 1         # Number of images for low richness


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


# =============================================================================
# PDF & EXPORT SETTINGS
# =============================================================================

PDF_DPI = 150              # DPI for PDF rendering
PDF_PAGE_WIDTH = 210       # Page width in mm (A4)
PDF_PAGE_HEIGHT = 297      # Page height in mm (A4)
