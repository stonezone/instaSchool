"""
Curriculum Customization Service

Provides parent controls for curriculum customization:
- Content depth adjustment (brief/standard/deep)
- Custom notes per unit
- Skip units that don't apply
- Supplemental resources
- Flag content for review before showing to child
"""

import json
from datetime import datetime
from typing import Dict, Any, List, Optional

from services.database_service import DatabaseService


class CurriculumCustomization:
    """Data class for curriculum customization settings"""

    def __init__(
        self,
        curriculum_id: str,
        content_depth: str = "standard",
        unit_notes: Optional[Dict[int, str]] = None,
        skipped_units: Optional[List[int]] = None,
        supplemental_resources: Optional[List[Dict[str, str]]] = None,
        flagged_units: Optional[List[int]] = None
    ):
        self.curriculum_id = curriculum_id
        self.content_depth = content_depth  # brief, standard, deep
        self.unit_notes = unit_notes or {}
        self.skipped_units = skipped_units or []
        self.supplemental_resources = supplemental_resources or []
        self.flagged_units = flagged_units or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage"""
        return {
            "curriculum_id": self.curriculum_id,
            "content_depth": self.content_depth,
            "unit_notes": self.unit_notes,
            "skipped_units": self.skipped_units,
            "supplemental_resources": self.supplemental_resources,
            "flagged_units": self.flagged_units
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CurriculumCustomization":
        """Create from dictionary"""
        return cls(
            curriculum_id=data.get("curriculum_id", ""),
            content_depth=data.get("content_depth", "standard"),
            unit_notes=data.get("unit_notes", {}),
            skipped_units=data.get("skipped_units", []),
            supplemental_resources=data.get("supplemental_resources", []),
            flagged_units=data.get("flagged_units", [])
        )


class CustomizationService:
    """Service for managing curriculum customizations"""

    CONTENT_DEPTHS = ["brief", "standard", "deep"]
    DEPTH_DESCRIPTIONS = {
        "brief": "Quick overview with key concepts only",
        "standard": "Balanced coverage of topics",
        "deep": "In-depth exploration with extra detail"
    }

    def __init__(self, db_path: str = "instaschool.db"):
        self.db = DatabaseService(db_path)
        self._ensure_table_exists()

    def _ensure_table_exists(self) -> None:
        """Create customizations table if it doesn't exist"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS curriculum_customizations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    curriculum_id TEXT NOT NULL UNIQUE,
                    content_depth TEXT DEFAULT 'standard',
                    unit_notes TEXT,
                    skipped_units TEXT,
                    supplemental_resources TEXT,
                    flagged_units TEXT,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def get_customization(self, curriculum_id: str) -> CurriculumCustomization:
        """Get customization settings for a curriculum

        Args:
            curriculum_id: Curriculum ID

        Returns:
            CurriculumCustomization object (default values if none exist)
        """
        result = self.db.fetch_one("""
            SELECT content_depth, unit_notes, skipped_units,
                   supplemental_resources, flagged_units
            FROM curriculum_customizations
            WHERE curriculum_id = ?
        """, (curriculum_id,))

        if not result:
            return CurriculumCustomization(curriculum_id=curriculum_id)

        return CurriculumCustomization(
            curriculum_id=curriculum_id,
            content_depth=result.get("content_depth", "standard"),
            unit_notes=json.loads(result.get("unit_notes") or "{}"),
            skipped_units=json.loads(result.get("skipped_units") or "[]"),
            supplemental_resources=json.loads(result.get("supplemental_resources") or "[]"),
            flagged_units=json.loads(result.get("flagged_units") or "[]")
        )

    def save_customization(self, customization: CurriculumCustomization) -> bool:
        """Save or update customization settings

        Args:
            customization: CurriculumCustomization object

        Returns:
            True if successful
        """
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO curriculum_customizations
                    (curriculum_id, content_depth, unit_notes, skipped_units,
                     supplemental_resources, flagged_units, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(curriculum_id) DO UPDATE SET
                        content_depth = excluded.content_depth,
                        unit_notes = excluded.unit_notes,
                        skipped_units = excluded.skipped_units,
                        supplemental_resources = excluded.supplemental_resources,
                        flagged_units = excluded.flagged_units,
                        updated_at = excluded.updated_at
                """, (
                    customization.curriculum_id,
                    customization.content_depth,
                    json.dumps(customization.unit_notes),
                    json.dumps(customization.skipped_units),
                    json.dumps(customization.supplemental_resources),
                    json.dumps(customization.flagged_units),
                    datetime.now().isoformat()
                ))
                conn.commit()
            return True
        except Exception:
            return False

    def set_content_depth(self, curriculum_id: str, depth: str) -> bool:
        """Set content depth for a curriculum

        Args:
            curriculum_id: Curriculum ID
            depth: One of 'brief', 'standard', 'deep'

        Returns:
            True if successful
        """
        if depth not in self.CONTENT_DEPTHS:
            return False

        customization = self.get_customization(curriculum_id)
        customization.content_depth = depth
        return self.save_customization(customization)

    def add_unit_note(self, curriculum_id: str, unit_index: int, note: str) -> bool:
        """Add a custom note to a unit

        Args:
            curriculum_id: Curriculum ID
            unit_index: Index of the unit (0-based)
            note: Note text

        Returns:
            True if successful
        """
        customization = self.get_customization(curriculum_id)
        customization.unit_notes[str(unit_index)] = note
        return self.save_customization(customization)

    def remove_unit_note(self, curriculum_id: str, unit_index: int) -> bool:
        """Remove a note from a unit"""
        customization = self.get_customization(curriculum_id)
        if str(unit_index) in customization.unit_notes:
            del customization.unit_notes[str(unit_index)]
            return self.save_customization(customization)
        return True

    def skip_unit(self, curriculum_id: str, unit_index: int) -> bool:
        """Mark a unit as skipped

        Args:
            curriculum_id: Curriculum ID
            unit_index: Index of the unit to skip

        Returns:
            True if successful
        """
        customization = self.get_customization(curriculum_id)
        if unit_index not in customization.skipped_units:
            customization.skipped_units.append(unit_index)
        return self.save_customization(customization)

    def unskip_unit(self, curriculum_id: str, unit_index: int) -> bool:
        """Remove skip status from a unit"""
        customization = self.get_customization(curriculum_id)
        if unit_index in customization.skipped_units:
            customization.skipped_units.remove(unit_index)
            return self.save_customization(customization)
        return True

    def flag_unit(self, curriculum_id: str, unit_index: int) -> bool:
        """Flag a unit for parent review before showing to child

        Args:
            curriculum_id: Curriculum ID
            unit_index: Index of the unit to flag

        Returns:
            True if successful
        """
        customization = self.get_customization(curriculum_id)
        if unit_index not in customization.flagged_units:
            customization.flagged_units.append(unit_index)
        return self.save_customization(customization)

    def unflag_unit(self, curriculum_id: str, unit_index: int) -> bool:
        """Remove flag from a unit"""
        customization = self.get_customization(curriculum_id)
        if unit_index in customization.flagged_units:
            customization.flagged_units.remove(unit_index)
            return self.save_customization(customization)
        return True

    def add_supplemental_resource(
        self,
        curriculum_id: str,
        title: str,
        url: str,
        description: str = ""
    ) -> bool:
        """Add a supplemental resource link

        Args:
            curriculum_id: Curriculum ID
            title: Resource title
            url: Resource URL
            description: Optional description

        Returns:
            True if successful
        """
        customization = self.get_customization(curriculum_id)
        resource = {
            "title": title,
            "url": url,
            "description": description,
            "added_at": datetime.now().isoformat()
        }
        customization.supplemental_resources.append(resource)
        return self.save_customization(customization)

    def remove_supplemental_resource(self, curriculum_id: str, index: int) -> bool:
        """Remove a supplemental resource by index"""
        customization = self.get_customization(curriculum_id)
        if 0 <= index < len(customization.supplemental_resources):
            customization.supplemental_resources.pop(index)
            return self.save_customization(customization)
        return False

    def is_unit_skipped(self, curriculum_id: str, unit_index: int) -> bool:
        """Check if a unit is skipped"""
        customization = self.get_customization(curriculum_id)
        return unit_index in customization.skipped_units

    def is_unit_flagged(self, curriculum_id: str, unit_index: int) -> bool:
        """Check if a unit is flagged for review"""
        customization = self.get_customization(curriculum_id)
        return unit_index in customization.flagged_units

    def get_unit_note(self, curriculum_id: str, unit_index: int) -> Optional[str]:
        """Get note for a specific unit"""
        customization = self.get_customization(curriculum_id)
        return customization.unit_notes.get(str(unit_index))


# Singleton instance
_customization_service_instance = None


def get_customization_service(db_path: str = "instaschool.db") -> CustomizationService:
    """Get or create the customization service singleton

    Args:
        db_path: Path to database

    Returns:
        CustomizationService instance
    """
    global _customization_service_instance
    if _customization_service_instance is None:
        _customization_service_instance = CustomizationService(db_path)
    return _customization_service_instance
