"""
Tests for StudentProgress - P0.3 regression tests for progress tracking.

These tests verify that:
1. completed_sections is deduplicated (no duplicates)
2. advance_section and complete_section don't create duplicates
3. _normalize_completed_sections works correctly
"""

import pytest
from unittest.mock import MagicMock, patch


class TestNormalizeCompletedSections:
    """Test the _normalize_completed_sections helper."""

    def test_removes_duplicates(self):
        """Verify duplicates are removed."""
        from src.student_mode.progress_manager import _normalize_completed_sections

        result = _normalize_completed_sections([0, 1, 1, 2, 2, 2, 3])
        assert result == [0, 1, 2, 3]

    def test_preserves_order(self):
        """Verify order is preserved (first occurrence)."""
        from src.student_mode.progress_manager import _normalize_completed_sections

        result = _normalize_completed_sections([3, 1, 2, 1, 0, 3])
        assert result == [3, 1, 2, 0]

    def test_handles_non_int_values(self):
        """Verify non-int values are filtered out."""
        from src.student_mode.progress_manager import _normalize_completed_sections

        result = _normalize_completed_sections([0, "1", 2, None, 3, "invalid"])
        # "1" should convert to 1, None and "invalid" should be filtered
        assert result == [0, 1, 2, 3]

    def test_handles_empty_list(self):
        """Verify empty list returns empty list."""
        from src.student_mode.progress_manager import _normalize_completed_sections

        result = _normalize_completed_sections([])
        assert result == []

    def test_handles_non_list_input(self):
        """Verify non-list input returns empty list."""
        from src.student_mode.progress_manager import _normalize_completed_sections

        assert _normalize_completed_sections(None) == []
        assert _normalize_completed_sections("not a list") == []
        assert _normalize_completed_sections(123) == []


class TestStudentProgressAdvance:
    """Test StudentProgress advance and complete section logic."""

    @patch("src.student_mode.progress_manager.DatabaseService")
    @patch("src.student_mode.progress_manager.Path")
    def test_advance_section_no_duplicate(self, mock_path, mock_db):
        """Verify advance_section doesn't create duplicates."""
        from src.student_mode.progress_manager import StudentProgress

        # Setup mocks
        mock_path.return_value.exists.return_value = False
        mock_db.return_value = MagicMock()

        progress = StudentProgress("test_curriculum", "test_user")
        progress.data = {
            "curriculum_id": "test_curriculum",
            "user_id": "test_user",
            "current_section": 0,
            "completed_sections": [],
            "xp": 0,
            "level": 0,
            "badges": [],
            "stats": {"total_sections_completed": 0},
            "last_updated": "2025-01-01",
            "created_at": "2025-01-01",
        }
        progress.save_progress = MagicMock()

        # Advance from section 0 to 1
        progress.advance_section()

        assert progress.data["current_section"] == 1
        assert progress.data["completed_sections"] == [0]

        # Advance again (section 1 to 2)
        progress.advance_section()

        assert progress.data["current_section"] == 2
        assert progress.data["completed_sections"] == [0, 1]

    @patch("src.student_mode.progress_manager.DatabaseService")
    @patch("src.student_mode.progress_manager.Path")
    def test_complete_section_no_duplicate(self, mock_path, mock_db):
        """Verify complete_section doesn't create duplicates."""
        from src.student_mode.progress_manager import StudentProgress

        mock_path.return_value.exists.return_value = False
        mock_db.return_value = MagicMock()

        progress = StudentProgress("test_curriculum", "test_user")
        progress.data = {
            "curriculum_id": "test_curriculum",
            "user_id": "test_user",
            "current_section": 0,
            "completed_sections": [],
            "xp": 0,
            "level": 0,
            "badges": [],
            "stats": {"total_sections_completed": 0},
            "last_updated": "2025-01-01",
            "created_at": "2025-01-01",
        }
        progress.save_progress = MagicMock()

        # Complete section 0 multiple times
        progress.complete_section(0)
        progress.complete_section(0)
        progress.complete_section(0)

        # Should only have one entry
        assert progress.data["completed_sections"].count(0) == 1
        assert progress.data["stats"]["total_sections_completed"] == 1

    @patch("src.student_mode.progress_manager.DatabaseService")
    @patch("src.student_mode.progress_manager.Path")
    def test_complete_then_advance_no_duplicate(self, mock_path, mock_db):
        """Verify complete_section then advance_section doesn't create duplicates."""
        from src.student_mode.progress_manager import StudentProgress

        mock_path.return_value.exists.return_value = False
        mock_db.return_value = MagicMock()

        progress = StudentProgress("test_curriculum", "test_user")
        progress.data = {
            "curriculum_id": "test_curriculum",
            "user_id": "test_user",
            "current_section": 0,
            "completed_sections": [],
            "xp": 0,
            "level": 0,
            "badges": [],
            "stats": {"total_sections_completed": 0},
            "last_updated": "2025-01-01",
            "created_at": "2025-01-01",
        }
        progress.save_progress = MagicMock()

        # This is the actual UI flow: complete_section then advance_section
        progress.complete_section(0)
        progress.advance_section()

        # Should still only have section 0 once
        assert progress.data["completed_sections"].count(0) == 1
        assert progress.data["current_section"] == 1

    @patch("src.student_mode.progress_manager.DatabaseService")
    @patch("src.student_mode.progress_manager.Path")
    def test_save_progress_normalizes_completed(self, mock_path, mock_db):
        """Verify save_progress normalizes completed_sections."""
        from src.student_mode.progress_manager import StudentProgress

        mock_path.return_value.exists.return_value = False
        mock_db.return_value = MagicMock()

        progress = StudentProgress("test_curriculum", "test_user")
        progress.progress_file = MagicMock()
        progress.db = None  # Disable DB save for this test

        # Manually inject duplicates (simulating legacy data)
        progress.data = {
            "curriculum_id": "test_curriculum",
            "user_id": "test_user",
            "current_section": 3,
            "completed_sections": [0, 1, 1, 2, 2, 2],  # Duplicates!
            "xp": 0,
            "level": 0,
            "badges": [],
            "stats": {"total_sections_completed": 6},  # Wrong count
            "last_updated": "2025-01-01",
            "created_at": "2025-01-01",
        }

        # Mock the file write
        with patch("builtins.open", MagicMock()):
            progress.save_progress()

        # Should be normalized
        assert progress.data["completed_sections"] == [0, 1, 2]
        assert progress.data["stats"]["total_sections_completed"] == 3


class TestStudentProgressStats:
    """Test StudentProgress stats tracking."""

    @patch("src.student_mode.progress_manager.DatabaseService")
    @patch("src.student_mode.progress_manager.Path")
    def test_total_sections_completed_matches_list_length(self, mock_path, mock_db):
        """Verify total_sections_completed always matches list length."""
        from src.student_mode.progress_manager import StudentProgress

        mock_path.return_value.exists.return_value = False
        mock_db.return_value = MagicMock()

        progress = StudentProgress("test_curriculum", "test_user")
        progress.data = {
            "curriculum_id": "test_curriculum",
            "user_id": "test_user",
            "current_section": 0,
            "completed_sections": [],
            "xp": 0,
            "level": 0,
            "badges": [],
            "stats": {"total_sections_completed": 0},
            "last_updated": "2025-01-01",
            "created_at": "2025-01-01",
        }
        progress.save_progress = MagicMock()

        # Complete several sections
        for i in range(5):
            progress.complete_section(i)
            expected_count = len(progress.data["completed_sections"])
            actual_count = progress.data["stats"]["total_sections_completed"]
            assert expected_count == actual_count, (
                f"After completing section {i}: "
                f"list has {expected_count} but stats says {actual_count}"
            )
