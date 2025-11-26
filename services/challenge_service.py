"""
Daily Challenges Service

Simple, local-only daily challenges to keep kids engaged.
No servers, no leaderboards - just personal goals with XP rewards.
"""

import json
import random
from datetime import datetime, date
from typing import Dict, Any, List, Optional
from pathlib import Path

from services.database_service import DatabaseService


# Challenge definitions
DAILY_CHALLENGES = [
    {
        "id": "review_cards_5",
        "name": "Review Champion",
        "description": "Answer 5 review cards",
        "icon": "🃏",
        "xp_reward": 25,
        "target": 5,
        "type": "review_cards",
        "difficulty": "easy"
    },
    {
        "id": "review_cards_10",
        "name": "Memory Master",
        "description": "Answer 10 review cards",
        "icon": "🧠",
        "xp_reward": 50,
        "target": 10,
        "type": "review_cards",
        "difficulty": "medium"
    },
    {
        "id": "complete_unit",
        "name": "Unit Complete",
        "description": "Complete 1 lesson unit",
        "icon": "📖",
        "xp_reward": 50,
        "target": 1,
        "type": "units_completed",
        "difficulty": "medium"
    },
    {
        "id": "complete_units_2",
        "name": "Learning Marathon",
        "description": "Complete 2 lesson units",
        "icon": "🏃",
        "xp_reward": 100,
        "target": 2,
        "type": "units_completed",
        "difficulty": "hard"
    },
    {
        "id": "ask_tutor",
        "name": "Curious Mind",
        "description": "Ask the AI tutor a question",
        "icon": "❓",
        "xp_reward": 10,
        "target": 1,
        "type": "tutor_questions",
        "difficulty": "easy"
    },
    {
        "id": "ask_tutor_3",
        "name": "Question Quest",
        "description": "Ask the AI tutor 3 questions",
        "icon": "🤔",
        "xp_reward": 30,
        "target": 3,
        "type": "tutor_questions",
        "difficulty": "medium"
    },
    {
        "id": "perfect_quiz",
        "name": "Perfect Score",
        "description": "Get 100% on a quiz",
        "icon": "⭐",
        "xp_reward": 75,
        "target": 1,
        "type": "perfect_quizzes",
        "difficulty": "hard"
    },
    {
        "id": "earn_xp_50",
        "name": "XP Hunter",
        "description": "Earn 50 XP today",
        "icon": "💎",
        "xp_reward": 25,
        "target": 50,
        "type": "xp_earned",
        "difficulty": "easy"
    },
    {
        "id": "earn_xp_100",
        "name": "XP Champion",
        "description": "Earn 100 XP today",
        "icon": "🏆",
        "xp_reward": 50,
        "target": 100,
        "type": "xp_earned",
        "difficulty": "medium"
    },
    {
        "id": "study_session",
        "name": "Dedicated Learner",
        "description": "Complete a study session",
        "icon": "📚",
        "xp_reward": 15,
        "target": 1,
        "type": "study_sessions",
        "difficulty": "easy"
    }
]


class ChallengeService:
    """Service for managing daily challenges"""

    def __init__(self, db_path: str = "instaschool.db"):
        self.db = DatabaseService(db_path)
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        """Create challenges table if it doesn't exist"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_challenges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    challenge_date DATE NOT NULL,
                    challenge_ids TEXT NOT NULL,
                    progress TEXT,
                    completed_ids TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, challenge_date)
                )
            """)
            conn.commit()

    def get_daily_challenges(self, user_id: str, num_challenges: int = 3) -> List[Dict[str, Any]]:
        """Get today's daily challenges for a user

        Args:
            user_id: User ID
            num_challenges: Number of challenges to assign (default 3)

        Returns:
            List of challenge dicts with progress
        """
        today = date.today().isoformat()

        # Check if challenges already assigned for today
        result = self.db.fetch_one("""
            SELECT challenge_ids, progress, completed_ids
            FROM daily_challenges
            WHERE user_id = ? AND challenge_date = ?
        """, (user_id, today))

        if result:
            # Return existing challenges with progress
            challenge_ids = json.loads(result.get("challenge_ids", "[]"))
            progress = json.loads(result.get("progress", "{}"))
            completed_ids = json.loads(result.get("completed_ids", "[]"))

            challenges = []
            for cid in challenge_ids:
                challenge = self._get_challenge_by_id(cid)
                if challenge:
                    challenge["progress"] = progress.get(cid, 0)
                    challenge["completed"] = cid in completed_ids
                    challenges.append(challenge)
            return challenges

        # Generate new challenges for today
        return self._generate_daily_challenges(user_id, num_challenges)

    def _generate_daily_challenges(self, user_id: str, num_challenges: int) -> List[Dict[str, Any]]:
        """Generate new daily challenges for user"""
        today = date.today().isoformat()

        # Select challenges with variety (different difficulties)
        easy = [c for c in DAILY_CHALLENGES if c["difficulty"] == "easy"]
        medium = [c for c in DAILY_CHALLENGES if c["difficulty"] == "medium"]
        hard = [c for c in DAILY_CHALLENGES if c["difficulty"] == "hard"]

        selected = []

        # Always include at least 1 easy
        if easy:
            selected.append(random.choice(easy))

        # Add medium/hard based on total needed
        remaining = num_challenges - len(selected)
        pool = medium + hard

        if remaining > 0 and pool:
            random.shuffle(pool)
            for challenge in pool:
                if challenge["id"] not in [s["id"] for s in selected]:
                    selected.append(challenge)
                    if len(selected) >= num_challenges:
                        break

        # Fill remaining with any if needed
        if len(selected) < num_challenges:
            all_challenges = [c for c in DAILY_CHALLENGES if c["id"] not in [s["id"] for s in selected]]
            random.shuffle(all_challenges)
            selected.extend(all_challenges[:num_challenges - len(selected)])

        challenge_ids = [c["id"] for c in selected]

        # Save to database
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO daily_challenges (user_id, challenge_date, challenge_ids, progress, completed_ids)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, today, json.dumps(challenge_ids), "{}", "[]"))
            conn.commit()

        # Add progress info
        for challenge in selected:
            challenge["progress"] = 0
            challenge["completed"] = False

        return selected

    def _get_challenge_by_id(self, challenge_id: str) -> Optional[Dict[str, Any]]:
        """Get challenge definition by ID"""
        for challenge in DAILY_CHALLENGES:
            if challenge["id"] == challenge_id:
                return challenge.copy()
        return None

    def update_progress(
        self,
        user_id: str,
        challenge_type: str,
        increment: int = 1
    ) -> List[Dict[str, Any]]:
        """Update progress on challenges of a given type

        Args:
            user_id: User ID
            challenge_type: Type of action (review_cards, units_completed, etc.)
            increment: Amount to increment progress

        Returns:
            List of newly completed challenges (for notifications)
        """
        today = date.today().isoformat()

        result = self.db.fetch_one("""
            SELECT challenge_ids, progress, completed_ids
            FROM daily_challenges
            WHERE user_id = ? AND challenge_date = ?
        """, (user_id, today))

        if not result:
            # No challenges for today
            return []

        challenge_ids = json.loads(result.get("challenge_ids", "[]"))
        progress = json.loads(result.get("progress", "{}"))
        completed_ids = json.loads(result.get("completed_ids", "[]"))

        newly_completed = []

        for cid in challenge_ids:
            if cid in completed_ids:
                continue  # Already completed

            challenge = self._get_challenge_by_id(cid)
            if not challenge or challenge["type"] != challenge_type:
                continue

            # Update progress
            current = progress.get(cid, 0)
            new_progress = current + increment
            progress[cid] = new_progress

            # Check if completed
            if new_progress >= challenge["target"]:
                completed_ids.append(cid)
                challenge["just_completed"] = True
                newly_completed.append(challenge)

        # Save updates
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE daily_challenges
                SET progress = ?, completed_ids = ?
                WHERE user_id = ? AND challenge_date = ?
            """, (json.dumps(progress), json.dumps(completed_ids), user_id, today))
            conn.commit()

        return newly_completed

    def get_completion_stats(self, user_id: str) -> Dict[str, Any]:
        """Get challenge completion statistics for user

        Args:
            user_id: User ID

        Returns:
            Stats dict with total completed, streak, etc.
        """
        # Get all time stats
        results = self.db.fetch_all("""
            SELECT challenge_date, completed_ids
            FROM daily_challenges
            WHERE user_id = ?
            ORDER BY challenge_date DESC
        """, (user_id,))

        total_completed = 0
        total_days = len(results)
        perfect_days = 0  # Days where all challenges completed

        for row in results:
            challenge_ids_result = self.db.fetch_one("""
                SELECT challenge_ids FROM daily_challenges
                WHERE user_id = ? AND challenge_date = ?
            """, (user_id, row["challenge_date"]))

            if challenge_ids_result:
                all_ids = json.loads(challenge_ids_result.get("challenge_ids", "[]"))
                completed = json.loads(row.get("completed_ids", "[]"))
                total_completed += len(completed)
                if len(completed) == len(all_ids) and len(all_ids) > 0:
                    perfect_days += 1

        # Calculate streak of perfect days
        streak = 0
        for row in results:
            challenge_ids_result = self.db.fetch_one("""
                SELECT challenge_ids FROM daily_challenges
                WHERE user_id = ? AND challenge_date = ?
            """, (user_id, row["challenge_date"]))

            if challenge_ids_result:
                all_ids = json.loads(challenge_ids_result.get("challenge_ids", "[]"))
                completed = json.loads(row.get("completed_ids", "[]"))
                if len(completed) == len(all_ids) and len(all_ids) > 0:
                    streak += 1
                else:
                    break

        return {
            "total_completed": total_completed,
            "total_days": total_days,
            "perfect_days": perfect_days,
            "current_streak": streak
        }

    def get_today_summary(self, user_id: str) -> Dict[str, Any]:
        """Get today's challenge summary

        Args:
            user_id: User ID

        Returns:
            Summary with completion count and XP available
        """
        challenges = self.get_daily_challenges(user_id)
        completed = [c for c in challenges if c.get("completed")]
        remaining = [c for c in challenges if not c.get("completed")]

        xp_earned = sum(c.get("xp_reward", 0) for c in completed)
        xp_available = sum(c.get("xp_reward", 0) for c in remaining)

        return {
            "total": len(challenges),
            "completed": len(completed),
            "remaining": len(remaining),
            "xp_earned": xp_earned,
            "xp_available": xp_available,
            "all_complete": len(remaining) == 0 and len(challenges) > 0
        }


# Singleton instance
_challenge_service_instance = None


def get_challenge_service(db_path: str = "instaschool.db") -> ChallengeService:
    """Get or create the challenge service singleton

    Args:
        db_path: Path to database

    Returns:
        ChallengeService instance
    """
    global _challenge_service_instance
    if _challenge_service_instance is None:
        _challenge_service_instance = ChallengeService(db_path)
    return _challenge_service_instance
