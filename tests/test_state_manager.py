"""
Tests for StateManager - P0.2 regression tests for state isolation.

These tests verify that:
1. Mutable defaults (dict, set) are not shared across sessions
2. deepcopy is used for initialization
3. State updates don't affect the DEFAULTS class attribute
"""

import pytest
from unittest.mock import MagicMock, patch


class TestStateManagerDefaults:
    """Test that StateManager.DEFAULTS mutable objects are isolated."""

    def test_defaults_contains_mutable_types(self):
        """Verify DEFAULTS contains mutable types that need isolation."""
        from src.state_manager import StateManager

        # Check that we have mutable types in DEFAULTS
        mutable_keys = []
        for key, value in StateManager.DEFAULTS.items():
            if isinstance(value, (dict, list, set)):
                mutable_keys.append(key)

        # Should have some mutable defaults
        assert len(mutable_keys) > 0, "No mutable defaults found - test assumptions may be wrong"

        # Specifically check known mutable keys
        assert "quiz_answers" in StateManager.DEFAULTS
        assert "quiz_feedback" in StateManager.DEFAULTS
        assert "last_tmp_files" in StateManager.DEFAULTS
        assert isinstance(StateManager.DEFAULTS["quiz_answers"], dict)
        assert isinstance(StateManager.DEFAULTS["last_tmp_files"], set)

    @patch("src.state_manager.st")
    def test_initialize_state_deep_copies_dicts(self, mock_st):
        """Verify dict defaults are deep copied on initialization."""
        from src.state_manager import StateManager

        # Setup mock session_state as a dict
        mock_session_state = {}
        mock_st.session_state = mock_session_state

        # Initialize state
        StateManager.initialize_state()

        # Get the initialized quiz_answers
        initialized_quiz_answers = mock_session_state.get("quiz_answers")

        # Should be a different object, not the same reference
        assert initialized_quiz_answers is not StateManager.DEFAULTS["quiz_answers"], (
            "quiz_answers should be a copy, not the same object"
        )

        # Modifying initialized value should not affect DEFAULTS
        original_default = StateManager.DEFAULTS["quiz_answers"].copy()
        initialized_quiz_answers["test_key"] = "test_value"

        assert StateManager.DEFAULTS["quiz_answers"] == original_default, (
            "Modifying initialized state should not affect DEFAULTS"
        )

    @patch("src.state_manager.st")
    def test_initialize_state_deep_copies_sets(self, mock_st):
        """Verify set defaults are deep copied on initialization."""
        from src.state_manager import StateManager

        mock_session_state = {}
        mock_st.session_state = mock_session_state

        StateManager.initialize_state()

        initialized_tmp_files = mock_session_state.get("last_tmp_files")

        # Should be a different object
        assert initialized_tmp_files is not StateManager.DEFAULTS["last_tmp_files"], (
            "last_tmp_files should be a copy, not the same object"
        )

    @patch("src.state_manager.st")
    def test_multiple_initializations_independent(self, mock_st):
        """Verify multiple initializations create independent state."""
        from src.state_manager import StateManager

        # Simulate two different sessions
        session1_state = {}
        session2_state = {}

        # Initialize session 1
        mock_st.session_state = session1_state
        StateManager.initialize_state()

        # Initialize session 2
        mock_st.session_state = session2_state
        StateManager.initialize_state()

        # Modify session 1's quiz_answers
        session1_state["quiz_answers"]["session1_key"] = "session1_value"

        # Session 2 should not be affected
        assert "session1_key" not in session2_state.get("quiz_answers", {}), (
            "Session 2 should not see Session 1's modifications"
        )

    @patch("src.state_manager.st")
    def test_skip_existing_keys(self, mock_st):
        """Verify existing keys are not overwritten."""
        from src.state_manager import StateManager

        mock_session_state = {
            "quiz_answers": {"existing": "value"},
        }
        mock_st.session_state = mock_session_state

        StateManager.initialize_state()

        # Existing value should be preserved
        assert mock_session_state["quiz_answers"] == {"existing": "value"}


class TestStateManagerOperations:
    """Test StateManager state operations."""

    @patch("src.state_manager.st")
    def test_get_state_with_default(self, mock_st):
        """Test get_state returns default when key missing."""
        from src.state_manager import StateManager

        mock_st.session_state = {}

        result = StateManager.get_state("nonexistent_key", "default_value")
        assert result == "default_value"

    @patch("src.state_manager.st")
    def test_update_state(self, mock_st):
        """Test update_state modifies session state."""
        from src.state_manager import StateManager

        mock_session_state = {}
        mock_st.session_state = mock_session_state

        StateManager.update_state("test_key", "test_value")

        assert mock_session_state["test_key"] == "test_value"

    @patch("src.state_manager.st")
    def test_batch_update(self, mock_st):
        """Test batch_update modifies multiple keys."""
        from src.state_manager import StateManager

        mock_session_state = {}
        mock_st.session_state = mock_session_state

        StateManager.batch_update({
            "key1": "value1",
            "key2": "value2",
        })

        assert mock_session_state["key1"] == "value1"
        assert mock_session_state["key2"] == "value2"
