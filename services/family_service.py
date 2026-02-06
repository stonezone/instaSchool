"""
Family Service - Family dashboard data aggregation

Provides methods to get family-wide learning statistics,
child progress summaries, and report generation data.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from pathlib import Path

from services.database_service import DatabaseService
from services.user_service import UserService


class FamilyService:
    """Aggregates family-wide learning data for parent dashboard"""

    def __init__(self, db_path: str = "instaschool.db"):
        """Initialize family service

        Args:
            db_path: Path to SQLite database
        """
        self.db = DatabaseService(db_path)
        self.user_service = UserService(db_path=db_path)

    def get_all_children(self) -> List[Dict[str, Any]]:
        """Get list of all children with basic info

        Returns:
            List of child dicts with id, username, total_xp, has_pin
        """
        return self.user_service.list_users()

    @staticmethod
    def _load_curriculum_units_from_metadata(
        curriculum_meta: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """Load curriculum units from a DB metadata record.

        Compatibility mode:
        - Prefer exact `file_path` recorded in DB.
        - Fallback to legacy glob/id naming patterns if file_path is missing.
        """
        # Preferred path: DB-backed file path
        file_path = curriculum_meta.get("file_path")
        if isinstance(file_path, str) and file_path.strip():
            candidate = Path(file_path)
            if candidate.exists():
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    units = data.get("units", [])
                    return units if isinstance(units, list) else []
                except Exception:
                    pass

        curriculum_id = curriculum_meta.get("id")
        if not curriculum_id:
            return []

        curricula_dir = Path("curricula")

        # Compatibility fallback #1: canonical save pattern
        for candidate in curricula_dir.glob(f"curriculum_{curriculum_id}_*.json"):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                units = data.get("units", [])
                if isinstance(units, list):
                    return units
            except Exception:
                continue

        # Compatibility fallback #2: older patterns
        for candidate in curricula_dir.glob(f"*_{curriculum_id}.json"):
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                units = data.get("units", [])
                if isinstance(units, list):
                    return units
            except Exception:
                continue

        # Compatibility fallback #3: direct id filename
        candidate = curricula_dir / f"{curriculum_id}.json"
        if candidate.exists():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    data = json.load(f)
                units = data.get("units", [])
                return units if isinstance(units, list) else []
            except Exception:
                pass

        return []

    def get_child_summary(self, user_id_or_username: str) -> Dict[str, Any]:
        """Get comprehensive summary for a single child

        Args:
            user_id_or_username: Child's user ID or username (both accepted)

        Returns:
            Dict with progress stats, streaks, due cards, etc.
        """
        # Get user info - try by ID first, then by username
        user = self.db.get_user(user_id_or_username)
        if not user:
            # Try by username if ID lookup failed
            user = self.db.get_user_by_username(user_id_or_username)
        if not user:
            return {}

        # Use the actual user ID from the looked up record
        user_id = user.get("id", user_id_or_username)

        # Get all progress records
        progress_list = self.db.get_user_all_progress(user_id)

        # Calculate aggregate stats
        total_curricula = len(progress_list)
        completed_curricula = 0
        total_sections_completed = 0
        total_xp = user.get("total_xp", 0)

        # Current streak from most recent progress
        current_streak = 0
        last_active = None

        for progress in progress_list:
            stats = progress.get("stats", {})
            completed_sections = progress.get("completed_sections", [])

            total_sections_completed += len(completed_sections)

            # Check completion
            if stats.get("curricula_completed", 0) > 0:
                completed_curricula += 1

            # Track streak (use highest)
            prog_streak = stats.get("current_streak", 0)
            if prog_streak > current_streak:
                current_streak = prog_streak

            # Track last active
            updated = progress.get("updated_at")
            if updated:
                if isinstance(updated, str):
                    try:
                        updated = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    except:
                        updated = None
                if updated and (last_active is None or updated > last_active):
                    last_active = updated

        # Get due review cards count
        due_cards = self._get_due_cards_count(user_id)

        # Format last active
        if last_active:
            today = datetime.now().date()
            if last_active.date() == today:
                last_active_str = "Today"
            elif last_active.date() == today - timedelta(days=1):
                last_active_str = "Yesterday"
            else:
                last_active_str = last_active.strftime("%b %d")
        else:
            last_active_str = "Never"

        return {
            "user_id": user_id,
            "username": user.get("username", "Unknown"),
            "total_xp": total_xp,
            "level": total_xp // 100,
            "current_streak": current_streak,
            "total_curricula": total_curricula,
            "completed_curricula": completed_curricula,
            "total_sections_completed": total_sections_completed,
            "due_cards": due_cards,
            "last_active": last_active_str,
            "progress_list": progress_list,
        }

    def get_family_summary(self) -> Dict[str, Any]:
        """Get summary of all children for family dashboard

        Returns:
            Dict with children list and family totals
        """
        children = self.get_all_children()
        children_summaries = []

        family_totals = {
            "total_xp": 0,
            "total_curricula": 0,
            "total_sections": 0,
            "total_due_cards": 0,
            "active_today": 0,
        }

        for child in children:
            # Get user ID from username
            user = self.db.get_user_by_username(child.get("username", ""))
            if not user:
                continue

            summary = self.get_child_summary(user["id"])
            children_summaries.append(summary)

            # Aggregate family totals
            family_totals["total_xp"] += summary.get("total_xp", 0)
            family_totals["total_curricula"] += summary.get("total_curricula", 0)
            family_totals["total_sections"] += summary.get("total_sections_completed", 0)
            family_totals["total_due_cards"] += summary.get("due_cards", 0)
            if summary.get("last_active") == "Today":
                family_totals["active_today"] += 1

        return {
            "children": children_summaries,
            "totals": family_totals,
            "generated_at": datetime.now().isoformat(),
        }

    def _get_due_cards_count(self, user_id: str) -> int:
        """Get count of due review cards for a user

        Args:
            user_id: User ID

        Returns:
            Number of due cards
        """
        now = datetime.now().isoformat()
        result = self.db.fetch_one(
            """
            SELECT COUNT(*) as count FROM review_items
            WHERE user_id = ? AND (next_review IS NULL OR next_review <= ?)
        """,
            (user_id, now),
        )

        return result.get("count", 0) if result else 0

    def get_child_curricula_progress(self, user_id_or_username: str) -> List[Dict[str, Any]]:
        """Get detailed progress for each curriculum a child is working on

        Args:
            user_id_or_username: Child's user ID or username (both accepted)

        Returns:
            List of curriculum progress dicts with completion percentage
        """
        # Resolve username to user ID if needed
        user = self.db.get_user(user_id_or_username)
        if not user:
            user = self.db.get_user_by_username(user_id_or_username)
        if not user:
            return []
        user_id = user.get("id", user_id_or_username)

        progress_list = self.db.get_user_all_progress(user_id)
        detailed = []

        for progress in progress_list:
            curriculum_id = progress.get("curriculum_id")

            total_sections = 0
            curriculum_meta = (
                self.db.get_curriculum_meta(curriculum_id) if curriculum_id else None
            ) or {}
            if curriculum_id and not curriculum_meta.get("id"):
                curriculum_meta["id"] = curriculum_id
            units = self._load_curriculum_units_from_metadata(curriculum_meta)
            if units:
                # Each unit has ~6 sections in Student mode.
                total_sections = len(units) * 6

            current = progress.get("current_section", 0)
            completed = len(progress.get("completed_sections", []))

            if total_sections > 0:
                pct = min(100, int((current / total_sections) * 100))
            else:
                pct = 0

            detailed.append(
                {
                    "curriculum_id": curriculum_id,
                    "title": progress.get("curriculum_title", "Unknown"),
                    "subject": progress.get("subject", ""),
                    "grade": progress.get("grade", ""),
                    "current_section": current,
                    "completed_sections": completed,
                    "total_sections": total_sections,
                    "progress_percent": pct,
                    "xp": progress.get("xp", 0),
                    "updated_at": progress.get("updated_at"),
                }
            )

        return detailed

    def generate_weekly_report(self, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Generate weekly progress report

        Args:
            user_id: Optional - if None, generates family-wide report

        Returns:
            Report data dict
        """
        one_week_ago = (datetime.now() - timedelta(days=7)).isoformat()

        if user_id:
            # Single child report
            summary = self.get_child_summary(user_id)
            curricula = self.get_child_curricula_progress(user_id)

            return {
                "type": "individual",
                "user": summary.get("username"),
                "period": "Last 7 days",
                "summary": summary,
                "curricula": curricula,
                "generated_at": datetime.now().isoformat(),
            }
        else:
            # Family report
            family = self.get_family_summary()

            return {
                "type": "family",
                "period": "Last 7 days",
                "children": family["children"],
                "totals": family["totals"],
                "generated_at": datetime.now().isoformat(),
            }


# Singleton instance
_family_service_instance = None


def get_family_service(db_path: str = "instaschool.db") -> FamilyService:
    """Get or create the family service singleton

    Args:
        db_path: Path to database

    Returns:
        FamilyService instance
    """
    global _family_service_instance
    if _family_service_instance is None:
        _family_service_instance = FamilyService(db_path)
    return _family_service_instance
