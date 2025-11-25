"""
Analytics Service for Teacher Dashboard
Scans student progress files and generates insights for teachers.
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field


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
    """Service for generating teacher analytics from student progress data"""

    def __init__(self, curricula_dir: str = "curricula", users_dir: str = "users"):
        self.curricula_dir = Path(curricula_dir)
        self.users_dir = Path(users_dir)
        self.users_progress_dir = self.curricula_dir / "users"

    def get_all_students(self) -> List[Dict[str, Any]]:
        """Get all registered students"""
        students = []
        if self.users_dir.exists():
            for user_file in self.users_dir.glob("*.json"):
                try:
                    with open(user_file, 'r') as f:
                        students.append(json.load(f))
                except (json.JSONDecodeError, IOError):
                    continue
        return students

    def get_student_progress_files(self, user_id: str) -> List[Path]:
        """Get all progress files for a specific user"""
        user_progress_dir = self.users_progress_dir / user_id
        if user_progress_dir.exists():
            return list(user_progress_dir.glob("progress_*.json"))
        return []

    def get_all_progress_files(self) -> List[Path]:
        """Get all progress files (both legacy and per-user)"""
        files = []

        # Legacy global progress files
        for f in self.curricula_dir.glob("progress_*.json"):
            files.append(f)

        # Per-user progress files
        if self.users_progress_dir.exists():
            for user_dir in self.users_progress_dir.iterdir():
                if user_dir.is_dir():
                    for f in user_dir.glob("progress_*.json"):
                        files.append(f)

        return files

    def load_progress_file(self, path: Path) -> Optional[Dict[str, Any]]:
        """Load a progress file"""
        try:
            with open(path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def get_curriculum_info(self, curriculum_id: str) -> Optional[Dict[str, Any]]:
        """Load curriculum metadata"""
        # Try to find the curriculum file
        for f in self.curricula_dir.glob(f"*_{curriculum_id}.json"):
            try:
                with open(f, 'r') as file:
                    data = json.load(file)
                    if 'meta' in data:
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
        """Calculate statistics for a single student"""
        user_id = user_data.get('id', 'unknown')
        username = user_data.get('username', 'Unknown')

        stats = StudentStats(
            user_id=user_id,
            username=username,
            total_xp=user_data.get('total_xp', 0),
            level=user_data.get('level', 0)
        )

        # Get progress files for this user
        progress_files = self.get_student_progress_files(user_id)

        latest_activity = None
        for pf in progress_files:
            progress = self.load_progress_file(pf)
            if not progress:
                continue

            stats.curricula_started += 1
            completed_sections = progress.get('completed_sections', [])
            stats.total_sections_completed += len(completed_sections)

            # Track XP from progress files
            stats.total_xp = max(stats.total_xp, progress.get('xp', 0))
            stats.level = max(stats.level, progress.get('level', 0))

            # Check if curriculum is completed (all sections done)
            total_sections = progress.get('total_sections', 0)
            if total_sections > 0 and len(completed_sections) >= total_sections:
                stats.curricula_completed += 1

            # Track last activity
            last_updated = progress.get('last_updated')
            if last_updated:
                if not latest_activity or last_updated > latest_activity:
                    latest_activity = last_updated

        stats.last_active = latest_activity
        return stats

    def calculate_curriculum_stats(self, curriculum_id: str) -> CurriculumStats:
        """Calculate statistics for a single curriculum"""
        stats = CurriculumStats(curriculum_id=curriculum_id)

        # Get curriculum info
        curriculum = self.get_curriculum_info(curriculum_id)
        if curriculum:
            meta = curriculum.get('meta', {})
            stats.title = meta.get('subject', 'Unknown Curriculum')
            units = curriculum.get('units', [])
            stats.total_sections = len(units)

        # Find all progress files for this curriculum
        progress_data = []

        # Check legacy progress
        legacy_file = self.curricula_dir / f"progress_{curriculum_id}.json"
        if legacy_file.exists():
            progress = self.load_progress_file(legacy_file)
            if progress:
                progress_data.append(progress)

        # Check per-user progress
        if self.users_progress_dir.exists():
            for user_dir in self.users_progress_dir.iterdir():
                if user_dir.is_dir():
                    user_progress_file = user_dir / f"progress_{curriculum_id}.json"
                    if user_progress_file.exists():
                        progress = self.load_progress_file(user_progress_file)
                        if progress:
                            progress_data.append(progress)

        stats.total_students = len(progress_data)

        if not progress_data:
            return stats

        # Calculate completion rates and section statistics
        total_completion = 0
        section_counts = {}

        for progress in progress_data:
            completed = progress.get('completed_sections', [])
            total = progress.get('total_sections', stats.total_sections) or 1

            completion_pct = len(completed) / total if total > 0 else 0
            total_completion += completion_pct

            # Track which sections are completed
            for section_idx in completed:
                section_counts[section_idx] = section_counts.get(section_idx, 0) + 1

        stats.completion_rate = (total_completion / len(progress_data)) * 100
        stats.avg_progress = total_completion / len(progress_data)
        stats.section_completion = section_counts

        # Identify struggle sections (low completion compared to previous sections)
        if stats.total_sections > 1 and section_counts:
            avg_completion = sum(section_counts.values()) / len(section_counts) if section_counts else 0
            for i in range(stats.total_sections):
                section_completions = section_counts.get(i, 0)
                if section_completions < avg_completion * 0.5:  # Less than 50% of average
                    stats.struggle_sections.append(i)

        return stats

    def get_analytics_summary(self) -> AnalyticsSummary:
        """Generate complete analytics summary"""
        summary = AnalyticsSummary()

        # Get all students
        students = self.get_all_students()
        summary.total_students = len(students)

        # Calculate student stats
        student_stats = []
        total_xp = 0
        now = datetime.now()

        for student in students:
            stats = self.calculate_student_stats(student)
            student_stats.append(stats)
            total_xp += stats.total_xp

            # Check if active in last 7 days
            if stats.last_active:
                try:
                    last_active = datetime.fromisoformat(stats.last_active.replace('Z', '+00:00'))
                    if (now - last_active.replace(tzinfo=None)).days <= 7:
                        summary.active_students_7d += 1
                except (ValueError, TypeError):
                    pass

        summary.total_xp_awarded = total_xp

        # Top 5 students by XP
        summary.top_students = sorted(student_stats, key=lambda s: s.total_xp, reverse=True)[:5]

        # Get unique curriculum IDs from progress files
        curriculum_ids = set()
        for pf in self.get_all_progress_files():
            # Extract curriculum ID from filename (progress_{id}.json)
            name = pf.stem
            if name.startswith('progress_'):
                curriculum_ids.add(name[9:])

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
        """Get detailed analytics for a specific curriculum"""
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
                    'completion_rate': (stats.section_completion.get(i, 0) / stats.total_students * 100) if stats.total_students > 0 else 0,
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
