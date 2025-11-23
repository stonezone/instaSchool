"""Student Progress Manager - Track student progress through curricula"""

import json
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime


class StudentProgress:
    """Manages student progress tracking and persistence"""
    
    def __init__(self, curriculum_id: str):
        """
        Initialize progress tracker for a curriculum
        
        Args:
            curriculum_id: Unique identifier for the curriculum
        """
        self.curriculum_id = curriculum_id
        self.progress_dir = Path("curricula")
        self.progress_dir.mkdir(exist_ok=True)
        self.progress_file = self.progress_dir / f"progress_{curriculum_id}.json"
        self.data = self._load_progress()
    
    def _load_progress(self) -> Dict:
        """Load progress from file or create new progress data"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                # If file is corrupted, start fresh
                pass
        
        # Default progress structure
        return {
            "curriculum_id": self.curriculum_id,
            "current_section": 0,
            "completed_sections": [],
            "xp": 0,
            "level": 0,
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
            "current_section": 0,
            "completed_sections": [],
            "xp": 0,
            "level": 0,
            "last_updated": datetime.now().isoformat(),
            "created_at": datetime.now().isoformat()
        }
        self.save_progress()
