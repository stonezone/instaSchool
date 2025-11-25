"""Student Progress Manager - Track student progress through curricula"""

import json
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from datetime import datetime, timedelta


def load_badges_config() -> Dict:
    """Load badge definitions from badges.json"""
    badges_file = Path("badges.json")
    if badges_file.exists():
        try:
            with open(badges_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"badges": []}


class StudentProgress:
    """Manages student progress tracking and persistence"""
    
    def __init__(self, curriculum_id: str, user_id: Optional[str] = None):
        """
        Initialize progress tracker for a curriculum
        
        Args:
            curriculum_id: Unique identifier for the curriculum
            user_id: Optional user identifier for per-student progress
        """
        self.curriculum_id = curriculum_id
        self.user_id = user_id

        base_dir = Path("curricula")
        # If a user_id is provided, store progress under curricula/users/{user_id}
        if self.user_id:
            self.progress_dir = base_dir / "users" / self.user_id
        else:
            self.progress_dir = base_dir

        self.progress_dir.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.progress_dir / f"progress_{curriculum_id}.json"
        self.data = self._load_progress()
    
    def _load_progress(self) -> Dict:
        """Load progress from file or create new progress data"""
        # Prefer user-scoped progress file if it exists
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If file is corrupted, start fresh
                pass

        # Backwards compatibility: if using per-user storage but a legacy
        # global progress file exists, load it once as a starting point.
        if self.user_id:
            legacy_file = Path("curricula") / f"progress_{self.curriculum_id}.json"
            if legacy_file.exists():
                try:
                    with open(legacy_file, "r") as f:
                        data = json.load(f)
                        # Ensure minimal fields and attach user_id
                        data.setdefault("curriculum_id", self.curriculum_id)
                        data.setdefault("current_section", 0)
                        data.setdefault("completed_sections", [])
                        data.setdefault("xp", 0)
                        data.setdefault("level", 0)
                        data["user_id"] = self.user_id
                        data.setdefault("created_at", datetime.now().isoformat())
                        data["last_updated"] = datetime.now().isoformat()
                        return data
                except (json.JSONDecodeError, IOError):
                    pass
        
        # Default progress structure with badge stats
        return {
            "curriculum_id": self.curriculum_id,
            "user_id": self.user_id,
            "current_section": 0,
            "completed_sections": [],
            "xp": 0,
            "level": 0,
            "badges": [],  # List of earned badge IDs
            "stats": {
                "perfect_quizzes": 0,
                "tutor_questions": 0,
                "short_answers": 0,
                "curricula_completed": 0,
                "current_streak": 0,
                "best_streak": 0,
                "last_study_date": None,
                "total_sections_completed": 0
            },
            "last_updated": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat()
        }
    
    def save_progress(self):
        """Persist progress data to file"""
        self.data["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.progress_file, 'w') as f:
                json.dump(self.data, f, indent=2)
        except IOError as e:
            print(f"Error saving progress: {e}")
    
    def get_current_section(self) -> int:
        """Get current section index"""
        return self.data.get("current_section", 0)
    
    def set_current_section(self, section: int):
        """Update current section"""
        self.data["current_section"] = section
        self.save_progress()
    
    def advance_section(self):
        """Move to next section"""
        self.data["current_section"] += 1
        if self.data["current_section"] not in self.data["completed_sections"]:
            self.data["completed_sections"].append(self.data["current_section"] - 1)
        self.save_progress()
    
    def previous_section(self):
        """Move to previous section"""
        if self.data["current_section"] > 0:
            self.data["current_section"] -= 1
            self.save_progress()
    
    def get_xp(self) -> int:
        """Get current XP"""
        return self.data.get("xp", 0)
    
    def add_xp(self, amount: int):
        """Add XP and check for level up"""
        self.data["xp"] += amount
        # Simple level calculation: 100 XP per level
        new_level = self.data["xp"] // 100
        leveled_up = new_level > self.data.get("level", 0)
        self.data["level"] = new_level
        self.save_progress()
        return leveled_up
    
    def get_level(self) -> int:
        """Get current level"""
        return self.data.get("level", 0)
    
    def get_progress_percent(self, total_sections: int) -> float:
        """Calculate progress percentage"""
        if total_sections == 0:
            return 0.0
        return (self.data["current_section"] / total_sections) * 100
    
    def reset_progress(self):
        """Reset all progress for this curriculum"""
        self.data = {
            "curriculum_id": self.curriculum_id,
            "user_id": self.user_id,
            "current_section": 0,
            "completed_sections": [],
            "xp": 0,
            "level": 0,
            "badges": [],
            "stats": {
                "perfect_quizzes": 0,
                "tutor_questions": 0,
                "short_answers": 0,
                "curricula_completed": 0,
                "current_streak": 0,
                "best_streak": 0,
                "last_study_date": None,
                "total_sections_completed": 0
            },
            "last_updated": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat()
        }
        self.save_progress()

    # =========================================================================
    # BADGE SYSTEM
    # =========================================================================

    def _ensure_stats(self):
        """Ensure stats structure exists for backwards compatibility"""
        if "stats" not in self.data:
            self.data["stats"] = {
                "perfect_quizzes": 0,
                "tutor_questions": 0,
                "short_answers": 0,
                "curricula_completed": 0,
                "current_streak": 0,
                "best_streak": 0,
                "last_study_date": None,
                "total_sections_completed": len(self.data.get("completed_sections", []))
            }
        if "badges" not in self.data:
            self.data["badges"] = []

    def get_stats(self) -> Dict:
        """Get all stats"""
        self._ensure_stats()
        return self.data.get("stats", {})

    def increment_stat(self, stat_name: str, amount: int = 1) -> List[Dict]:
        """
        Increment a stat and check for new badges.
        Returns list of newly earned badges.
        """
        self._ensure_stats()
        if stat_name in self.data["stats"]:
            self.data["stats"][stat_name] += amount
        self.save_progress()
        return self.check_and_award_badges()

    def record_perfect_quiz(self) -> List[Dict]:
        """Record a perfect quiz score and check for badges"""
        return self.increment_stat("perfect_quizzes")

    def record_tutor_question(self) -> List[Dict]:
        """Record a tutor question asked"""
        return self.increment_stat("tutor_questions")

    def record_short_answer(self) -> List[Dict]:
        """Record a short answer submission"""
        return self.increment_stat("short_answers")

    def record_curriculum_completion(self) -> List[Dict]:
        """Record curriculum completion"""
        return self.increment_stat("curricula_completed")

    def update_streak(self) -> List[Dict]:
        """Update study streak based on last study date"""
        self._ensure_stats()
        today = datetime.now().date().isoformat()
        last_study = self.data["stats"].get("last_study_date")

        if last_study:
            last_date = datetime.fromisoformat(last_study).date()
            today_date = datetime.now().date()
            diff = (today_date - last_date).days

            if diff == 1:
                # Consecutive day - increment streak
                self.data["stats"]["current_streak"] += 1
            elif diff > 1:
                # Streak broken
                self.data["stats"]["current_streak"] = 1
            # diff == 0: Same day, no change
        else:
            # First study session
            self.data["stats"]["current_streak"] = 1

        # Update best streak
        if self.data["stats"]["current_streak"] > self.data["stats"].get("best_streak", 0):
            self.data["stats"]["best_streak"] = self.data["stats"]["current_streak"]

        self.data["stats"]["last_study_date"] = today
        self.save_progress()
        return self.check_and_award_badges()

    def get_badges(self) -> List[str]:
        """Get list of earned badge IDs"""
        self._ensure_stats()
        return self.data.get("badges", [])

    def get_badge_details(self) -> List[Dict]:
        """Get full details of earned badges"""
        badge_config = load_badges_config()
        all_badges = {b["id"]: b for b in badge_config.get("badges", [])}
        earned_ids = self.get_badges()
        return [all_badges[bid] for bid in earned_ids if bid in all_badges]

    def check_and_award_badges(self) -> List[Dict]:
        """
        Check all badge conditions and award any newly earned badges.
        Returns list of newly awarded badge dictionaries.
        """
        self._ensure_stats()
        badge_config = load_badges_config()
        all_badges = badge_config.get("badges", [])
        earned_badges = set(self.data.get("badges", []))
        newly_earned = []

        stats = self.data["stats"]

        for badge in all_badges:
            badge_id = badge["id"]
            if badge_id in earned_badges:
                continue  # Already earned

            condition = badge.get("condition", {})
            cond_type = condition.get("type")
            cond_value = condition.get("value", 0)

            earned = False

            if cond_type == "sections_completed":
                earned = stats.get("total_sections_completed", 0) >= cond_value
            elif cond_type == "perfect_quiz":
                earned = stats.get("perfect_quizzes", 0) >= cond_value
            elif cond_type == "curricula_completed":
                earned = stats.get("curricula_completed", 0) >= cond_value
            elif cond_type == "total_xp":
                earned = self.data.get("xp", 0) >= cond_value
            elif cond_type == "level":
                earned = self.data.get("level", 0) >= cond_value
            elif cond_type == "tutor_questions":
                earned = stats.get("tutor_questions", 0) >= cond_value
            elif cond_type == "short_answers":
                earned = stats.get("short_answers", 0) >= cond_value
            elif cond_type == "streak_days":
                earned = stats.get("current_streak", 0) >= cond_value

            if earned:
                self.data["badges"].append(badge_id)
                newly_earned.append(badge)
                # Award XP bonus
                xp_bonus = badge.get("xp_bonus", 0)
                if xp_bonus > 0:
                    self.data["xp"] += xp_bonus
                    self.data["level"] = self.data["xp"] // 100

        if newly_earned:
            self.save_progress()

        return newly_earned

    def complete_section(self, section_idx: int) -> Tuple[bool, List[Dict]]:
        """
        Mark a section as completed and update stats.
        Returns (leveled_up, new_badges)
        """
        self._ensure_stats()

        if section_idx not in self.data["completed_sections"]:
            self.data["completed_sections"].append(section_idx)
            self.data["stats"]["total_sections_completed"] = len(self.data["completed_sections"])

        # Update streak
        self.update_streak()

        self.save_progress()
        new_badges = self.check_and_award_badges()

        return False, new_badges
