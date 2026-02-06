"""
Regression tests for DB-backed curriculum file resolution in family/analytics services.
"""

import json
import uuid
from pathlib import Path

from services.analytics_service import AnalyticsService
from services.database_service import DatabaseService
from services.family_service import FamilyService


def _seed_db_with_curriculum(db: DatabaseService, curriculum_path: Path, curriculum_id: str):
    username = f"alice_{uuid.uuid4().hex[:8]}"
    user = db.create_user(username)
    assert user is not None
    registered = db.register_curriculum(
        curriculum_id=curriculum_id,
        title="Math",
        subject="Math",
        grade="5",
        file_path=str(curriculum_path),
        created_by=user["id"],
    )
    assert registered is True
    saved = db.save_progress(
        user["id"],
        curriculum_id,
        {"current_section": 3, "completed_sections": [0], "xp": 10, "badges": [], "stats": {}},
    )
    assert saved is True
    return user["id"], curriculum_id


def test_family_service_prefers_db_file_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    curricula_dir = tmp_path / "curricula"
    curricula_dir.mkdir()

    curriculum_id = f"cid_{uuid.uuid4().hex[:8]}"
    # Canonical save filename format does NOT match "<id>.json".
    curriculum_file = curricula_dir / f"curriculum_{curriculum_id}_20260206_000000.json"
    curriculum_file.write_text(
        json.dumps({"meta": {"subject": "Math"}, "units": [{}, {}]}),
        encoding="utf-8",
    )

    db = DatabaseService(db_path="test.db")
    user_id, _ = _seed_db_with_curriculum(db, curriculum_file, curriculum_id)

    fs = FamilyService(db_path="test.db")
    rows = fs.get_child_curricula_progress(user_id)
    assert len(rows) == 1
    assert rows[0]["total_sections"] == 12
    assert rows[0]["progress_percent"] == 25


def test_analytics_service_prefers_db_file_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    curricula_dir = tmp_path / "curricula"
    curricula_dir.mkdir()

    curriculum_id = f"cid_{uuid.uuid4().hex[:8]}"
    curriculum_file = curricula_dir / f"curriculum_{curriculum_id}_20260206_000000.json"
    curriculum_file.write_text(
        json.dumps({"meta": {"subject": "Math"}, "units": [{}, {}]}),
        encoding="utf-8",
    )

    db = DatabaseService(db_path="test.db")
    _, curriculum_id = _seed_db_with_curriculum(db, curriculum_file, curriculum_id)

    analytics = AnalyticsService(db_path="test.db", curricula_dir="curricula")
    stats = analytics.calculate_curriculum_stats(curriculum_id)

    assert stats.total_sections == 2
    assert stats.title == "Math"
    assert stats.total_students == 1
    assert stats.completion_rate == 50.0
