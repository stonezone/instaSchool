"""
State Manager for InstaSchool Application
Provides atomic state updates and proper resource management
"""
import streamlit as st
from typing import Any, Dict, Optional, Callable
import threading
from contextlib import contextmanager

class StateManager:
    """Manages application state with atomic updates and proper locking"""
    
    _lock = threading.Lock()
    
    @classmethod
    def initialize_state(cls):
        """Initialize all required session state variables"""
        defaults = {
            'generating': False,
            'curriculum': None,
            'generation_params': {},
            'quiz_answers': {},
            'quiz_feedback': {},
            'edit_mode': False,
            'edit_history': {},
            'progress': 0.0,
            'last_tmp_files': set(),
            'current_topic_index': 0,
            'api_key_validated': False,
            'curriculum_service': None,
            'image_size': '1024x1024'
        }
        
        for key, value in defaults.items():
            if key not in st.session_state:
                st.session_state[key] = value
    
    @classmethod
    def update_state(cls, key: str, value: Any, callback: Optional[Callable] = None):
        """Atomically update state with optional callback"""
        with cls._lock:
            st.session_state[key] = value
            if callback:
                callback()
    
    @classmethod
    def batch_update(cls, updates: Dict[str, Any]):
        """Update multiple state values atomically"""
        with cls._lock:
            for key, value in updates.items():
                st.session_state[key] = value
    
    @classmethod
    @contextmanager
    def atomic_update(cls):
        """Context manager for atomic state updates"""
        with cls._lock:
            yield st.session_state
    
    @classmethod
    def clear_generation_state(cls):
        """Clear all generation-related state"""
        with cls._lock:
            st.session_state.edit_history = {}
            st.session_state.quiz_answers = {}
            st.session_state.quiz_feedback = {}
            st.session_state.edit_mode = False
            st.session_state.current_topic_index = 0
    
    @classmethod
    def update_quiz_answer(cls, question_key: str, answer: Any, is_correct: bool):
        """Update quiz answer and feedback atomically"""
        with cls._lock:
            st.session_state.quiz_answers[question_key] = answer
            st.session_state.quiz_feedback[question_key] = is_correct
    
    @classmethod
    def update_curriculum_unit(cls, unit_index: int, field: str, value: Any):
        """Update a specific field in a curriculum unit"""
        with cls._lock:
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