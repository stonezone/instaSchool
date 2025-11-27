"""
Analytics Service for Teacher Dashboard
Generates insights from student progress data using SQLite database.

Migrated from JSON file-based storage to DatabaseService for consistency
with the rest of the application.
"""

import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from services.database_service import DatabaseService


@dataclass
class StudentStats:
    """Statistics for a single student"""
    user_id: str
    username: str
    total_xp: int = 0
    level: int = 0
    curricula_started: int = 0
    curricula_completed: int = 0
    total_sections_completed: int = 0
    quiz_attempts: int = 0
    quiz_correct: int = 0
    last_active: Optional[str] = None


@dataclass
class CurriculumStats:
    """Statistics for a single curriculum"""
    curriculum_id: str
    title: str = "Unknown"
    total_students: int = 0
    completion_rate: float = 0.0
    avg_progress: float = 0.0
    total_sections: int = 0
    section_completion: Dict[int, int] = field(default_factory=dict)
    struggle_sections: List[int] = field(default_factory=list)


@dataclass
class AnalyticsSummary:
    """Overall analytics summary"""
    total_students: int = 0
    total_curricula: int = 0
    active_students_7d: int = 0
    avg_completion_rate: float = 0.0
    total_xp_awarded: int = 0
    top_students: List[StudentStats] = field(default_factory=list)
    curriculum_stats: List[CurriculumStats] = field(default_factory=list)


class AnalyticsService:
    """Service for generating teacher analytics from student progress data.

    Uses DatabaseService for data access, with optional JSON fallback for
    legacy data that hasn't been migrated.
    """

    def __init__(self, db_path: str = "instaschool.db", curricula_dir: str = "curricula"):
        """Initialize analytics service.

        Args:
            db_path: Path to SQLite database
            curricula_dir: Path to curricula directory (for curriculum JSON files)
        """
        self.db = DatabaseService(db_path)
        self.curricula_dir = Path(curricula_dir)

    def get_all_students(self) -> List[Dict[str, Any]]:
        """Get all registered students from database."""
        return self.db.list_users()

    def get_curriculum_info(self, curriculum_id: str) -> Optional[Dict[str, Any]]:
        """Load curriculum metadata from JSON file.

        Note: Curriculum content is still stored as JSON files, only progress
        and user data is in the database.
        """
        # Try to find the curriculum file by ID pattern
        for f in self.curricula_dir.glob(f"*_{curriculum_id}.json"):
            try:
                with open(f, 'r') as file:
                    data = json.load(file)
                    if 'meta' in data or 'units' in data:
                        return data
            except (json.JSONDecodeError, IOError):
                continue

        # Try direct match
        curriculum_file = self.curricula_dir / f"{curriculum_id}.json"
        if curriculum_file.exists():
            try:
                with open(curriculum_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass

        return None

    def calculate_student_stats(self, user_data: Dict[str, Any]) -> StudentStats:
        """Calculate statistics for a single student using database data."""
        user_id = user_data.get('id', 'unknown')
        username = user_data.get('username', 'Unknown')

        stats = StudentStats(
            user_id=user_id,
            username=username,
            total_xp=user_data.get('total_xp', 0),
            level=user_data.get('level', 0)
        )

        # Get all progress records for this user from database
        progress_list = self.db.get_user_all_progress(user_id)

        latest_activity = None
        for progress in progress_list:
            stats.curricula_started += 1

            # Get completed sections
            completed_sections = progress.get('completed_sections', [])
            if isinstance(completed_sections, str):
                try:
                    completed_sections = json.loads(completed_sections)
                except json.JSONDecodeError:
                    completed_sections = []

            stats.total_sections_completed += len(completed_sections)

            # Parse stats JSON if needed
            progress_stats = progress.get('stats', {})
            if isinstance(progress_stats, str):
                try:
                    progress_stats = json.loads(progress_stats)
                except json.JSONDecodeError:
                    progress_stats = {}

            # Track max XP and level based on XP column
            progress_xp = progress.get('xp', 0) or 0
            stats.total_xp = max(stats.total_xp, progress_xp)
            stats.level = max(stats.level, progress_xp // 100)

            # Check if curriculum is completed
            if progress_stats.get('curricula_completed', 0) > 0:
                stats.curricula_completed += 1

            # Track last activity
            last_updated = progress.get('updated_at')
            if last_updated:
                if not latest_activity or str(last_updated) > str(latest_activity):
                    latest_activity = last_updated

        stats.last_active = str(latest_activity) if latest_activity else None
        return stats

    def calculate_curriculum_stats(self, curriculum_id: str) -> CurriculumStats:
        """Calculate statistics for a single curriculum."""
        stats = CurriculumStats(curriculum_id=curriculum_id)

        # Get curriculum info from JSON
        curriculum = self.get_curriculum_info(curriculum_id)
        if curriculum:
            meta = curriculum.get('meta', {})
            stats.title = meta.get('subject', curriculum.get('title', 'Unknown Curriculum'))
            units = curriculum.get('units', [])
            stats.total_sections = len(units)

        # Get all progress records for this curriculum from database
        progress_records = self.db.fetch_all("""
            SELECT * FROM progress WHERE curriculum_id = ?
        """, (curriculum_id,))

        stats.total_students = len(progress_records)

        if not progress_records:
            return stats

        # Calculate completion rates and section statistics
        total_completion = 0
        section_counts = {}

        for progress in progress_records:
            # Parse completed sections
            completed = progress.get('completed_sections', [])
            if isinstance(completed, str):
                try:
                    completed = json.loads(completed)
                except json.JSONDecodeError:
                    completed = []

            total = stats.total_sections or 1
            completion_pct = len(completed) / total if total > 0 else 0
            total_completion += completion_pct

            # Track which sections are completed
            for section_idx in completed:
                section_counts[section_idx] = section_counts.get(section_idx, 0) + 1

        stats.completion_rate = (total_completion / len(progress_records)) * 100
        stats.avg_progress = total_completion / len(progress_records)
        stats.section_completion = section_counts

        # Identify struggle sections (low completion compared to average)
        if stats.total_sections > 1 and section_counts:
            avg_completion = sum(section_counts.values()) / len(section_counts)
            for i in range(stats.total_sections):
                section_completions = section_counts.get(i, 0)
                if section_completions < avg_completion * 0.5:
                    stats.struggle_sections.append(i)

        return stats

    def get_analytics_summary(self) -> AnalyticsSummary:
        """Generate complete analytics summary from database."""
        summary = AnalyticsSummary()

        # Get all students from database
        students = self.get_all_students()
        summary.total_students = len(students)

        # Calculate student stats
        student_stats = []
        total_xp = 0
        now = datetime.now()
        seven_days_ago = now - timedelta(days=7)

        for student in students:
            stats = self.calculate_student_stats(student)
            student_stats.append(stats)
            total_xp += stats.total_xp

            # Check if active in last 7 days
            if stats.last_active:
                try:
                    last_active_str = str(stats.last_active).replace('Z', '+00:00')
                    # Handle both ISO format and simple date strings
                    if 'T' in last_active_str or ' ' in last_active_str:
                        last_active = datetime.fromisoformat(last_active_str.split('+')[0])
                    else:
                        last_active = datetime.strptime(last_active_str[:10], '%Y-%m-%d')

                    if last_active >= seven_days_ago:
                        summary.active_students_7d += 1
                except (ValueError, TypeError):
                    pass

        summary.total_xp_awarded = total_xp

        # Top 5 students by XP
        summary.top_students = sorted(student_stats, key=lambda s: s.total_xp, reverse=True)[:5]

        # Get unique curriculum IDs from progress table
        curriculum_records = self.db.fetch_all("""
            SELECT DISTINCT curriculum_id FROM progress
        """)
        curriculum_ids = {r['curriculum_id'] for r in curriculum_records if r.get('curriculum_id')}

        summary.total_curricula = len(curriculum_ids)

        # Calculate stats for each curriculum
        total_completion = 0
        for cid in curriculum_ids:
            cstats = self.calculate_curriculum_stats(cid)
            summary.curriculum_stats.append(cstats)
            if cstats.total_students > 0:
                total_completion += cstats.completion_rate

        if summary.curriculum_stats:
            summary.avg_completion_rate = total_completion / len(summary.curriculum_stats)

        return summary

    def get_curriculum_details(self, curriculum_id: str) -> Dict[str, Any]:
        """Get detailed analytics for a specific curriculum."""
        stats = self.calculate_curriculum_stats(curriculum_id)
        curriculum = self.get_curriculum_info(curriculum_id)

        # Build section-by-section breakdown
        sections = []
        if curriculum:
            units = curriculum.get('units', [])
            for i, unit in enumerate(units):
                section_data = {
                    'index': i,
                    'title': unit.get('title', f'Section {i+1}'),
                    'completions': stats.section_completion.get(i, 0),
                    'completion_rate': (
                        stats.section_completion.get(i, 0) / stats.total_students * 100
                    ) if stats.total_students > 0 else 0,
                    'is_struggle_point': i in stats.struggle_sections
                }
                sections.append(section_data)

        return {
            'curriculum_id': curriculum_id,
            'title': stats.title,
            'total_students': stats.total_students,
            'completion_rate': stats.completion_rate,
            'total_sections': stats.total_sections,
            'sections': sections,
            'struggle_sections': stats.struggle_sections
        }
