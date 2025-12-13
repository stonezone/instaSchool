"""
State Manager for InstaSchool Application
Provides centralized state management for Streamlit session state.

IMPORTANT: This class should only be used from the main Streamlit thread.
Streamlit's session state is already isolated per-session, so no locking is needed.
Do NOT call these methods from background threads.
"""
import streamlit as st
import copy
from typing import Any, Dict, Optional, Callable
from contextlib import contextmanager


class StateManager:
    """Manages application state with centralized access patterns.

    Note: Streamlit runs each session in isolation, so thread locking is not
    needed for session_state access. This class provides a clean API for
    state management without the overhead of locks.
    """

    # Default values for all session state keys
    # Services (provider_service, curriculum_service, etc.) are initialized
    # separately in main.py because they require runtime configuration.
    DEFAULTS = {
        # Generation state
        'generating': False,
        'curriculum': None,
        'curriculum_id': None,
        'generation_params': {},
        'progress': 0.0,
        'generation_future': None,
        'generation_cancel_event': None,
        'generation_started_at': None,
        'generation_progress_state': None,
        'generation_progress_lock': None,
        'generation_last_error': None,
        'generation_last_filename': None,
        'generation_executor': None,

        # Quiz state
        'quiz_answers': {},
        'quiz_feedback': {},

        # Edit state
        'edit_mode': False,
        'edit_history': {},
        'current_topic_index': 0,

        # UI state
        'is_mobile': False,
        'theme': 'light',
        'image_size': '1024x1024',

        # Session state
        'api_key_validated': False,
        'api_error': None,
        'current_user': None,
        'current_mode': 'student',

        # Login state
        'login_needs_pin': False,
        'login_username': '',

        # Temp file tracking
        'last_tmp_files': set(),
        '_startup_cleanup_done': False,

        # Batch processing
        'batch_polling': False,
        'active_batch_id': None,

        # Service placeholders (initialized to None, set properly in main.py)
        'curriculum_service': None,
        'provider_service': None,
        'session_manager': None,
        'template_manager': None,
        'batch_manager': None,
        'user_service': None,
        'analytics_service': None,
        'available_models': None,
    }

    @classmethod
    def initialize_state(cls):
        """Initialize all required session state variables.

        This sets default values for all known state keys. Services like
        provider_service and curriculum_service are set to None here and
        initialized properly in main.py once config is loaded.

        Call this once near the top of main.py before using any state.
        """
        for key, value in cls.DEFAULTS.items():
            if key not in st.session_state:
                try:
                    st.session_state[key] = copy.deepcopy(value)
                except Exception:
                    # Fallback: if deepcopy fails, use the value as-is.
                    st.session_state[key] = value

    @classmethod
    def update_state(cls, key: str, value: Any, callback: Optional[Callable] = None):
        """Update state with optional callback"""
        st.session_state[key] = value
        if callback:
            callback()

    @classmethod
    def batch_update(cls, updates: Dict[str, Any]):
        """Update multiple state values"""
        for key, value in updates.items():
            st.session_state[key] = value

    @classmethod
    @contextmanager
    def atomic_update(cls):
        """Context manager for grouped state updates.

        Note: In Streamlit's single-threaded model, this doesn't provide
        true atomicity, but it groups updates for code clarity.
        """
        yield st.session_state

    @classmethod
    def clear_generation_state(cls):
        """Clear all generation-related state"""
        st.session_state.edit_history = {}
        st.session_state.quiz_answers = {}
        st.session_state.quiz_feedback = {}
        st.session_state.edit_mode = False
        st.session_state.current_topic_index = 0

    @classmethod
    def update_quiz_answer(cls, question_key: str, answer: Any, is_correct: bool):
        """Update quiz answer and feedback"""
        st.session_state.quiz_answers[question_key] = answer
        st.session_state.quiz_feedback[question_key] = is_correct

    @classmethod
    def update_curriculum_unit(cls, unit_index: int, field: str, value: Any):
        """Update a specific field in a curriculum unit"""
        if st.session_state.curriculum and "units" in st.session_state.curriculum:
            if 0 <= unit_index < len(st.session_state.curriculum["units"]):
                st.session_state.curriculum["units"][unit_index][field] = value

    @classmethod
    def get_state(cls, key: str, default: Any = None) -> Any:
        """Safely get state value with default"""
        return st.session_state.get(key, default)

    @classmethod
    def has_state(cls, key: str) -> bool:
        """Check if state key exists"""
        return key in st.session_state

    @classmethod
    def set_state(cls, key: str, value: Any):
        """Safely set state value (alias for update_state for consistency)"""
        cls.update_state(key, value)
