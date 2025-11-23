"""
Template Management Service
Handles creation, storage, and application of curriculum templates
"""

import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, asdict


@dataclass
class TemplateMetadata:
    """Metadata for curriculum templates"""
    id: str
    name: str
    description: str
    subjects: List[str]
    grades: List[str]
    style: str
    language: str
    author: str
    created_at: str
    updated_at: str
    usage_count: int = 0
    tags: List[str] = None
    is_public: bool = True
    
    def __post_init__(self):
        if self.tags is None:
            self.tags = []


@dataclass
class TemplateStructure:
    """Structure definition for curriculum templates"""
    topic_count: int
    media_richness: int
    include_quizzes: bool
    include_summary: bool
    include_resources: bool
    include_keypoints: bool
    topic_templates: List[Dict[str, Any]] = None
    custom_prompts: Dict[str, str] = None
    
    def __post_init__(self):
        if self.topic_templates is None:
            self.topic_templates = []
        if self.custom_prompts is None:
            self.custom_prompts = {}


class TemplateManager:
    """Manages curriculum templates"""
    
    def __init__(self, templates_dir: str = "templates"):
        """Initialize template manager
        
        Args:
            templates_dir: Directory to store templates
        """
        self.templates_dir = Path(templates_dir)
        self.templates_dir.mkdir(exist_ok=True)
        
        # Create subdirectories
        (self.templates_dir / "user").mkdir(exist_ok=True)
        (self.templates_dir / "system").mkdir(exist_ok=True)
        (self.templates_dir / "shared").mkdir(exist_ok=True)
        
        # Initialize built-in templates
        self._initialize_builtin_templates()
    
    def _initialize_builtin_templates(self):
        """Create built-in templates if they don't exist"""
        builtin_templates = [
            {
                "metadata": TemplateMetadata(
                    id="elementary_science",
                    name="Elementary Science Explorer",
                    description="Interactive science curriculum for elementary students with hands-on activities",
                    subjects=["Science"],
                    grades=["K", "1", "2", "3", "4", "5"],
                    style="Hands-on",
                    language="English",
                    author="InstaSchool",
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat(),
                    tags=["science", "elementary", "interactive", "hands-on"]
                ),
                "structure": TemplateStructure(
                    topic_count=4,
                    media_richness=4,
                    include_quizzes=True,
                    include_summary=True,
                    include_resources=True,
                    include_keypoints=True,
                    topic_templates=[
                        {"title_pattern": "Introduction to {concept}", "focus": "foundational understanding"},
                        {"title_pattern": "Exploring {concept}", "focus": "hands-on discovery"},
                        {"title_pattern": "{concept} in Action", "focus": "real-world applications"},
                        {"title_pattern": "Mastering {concept}", "focus": "synthesis and review"}
                    ],
                    custom_prompts={
                        "content": "Create engaging, age-appropriate content with simple experiments and observations that students can do safely. Include plenty of 'What would happen if...' questions."
                    }
                )
            },
            {
                "metadata": TemplateMetadata(
                    id="high_school_inquiry",
                    name="High School Inquiry-Based Learning",
                    description="Research-focused curriculum for high school students emphasizing critical thinking",
                    subjects=["Science", "Social Studies", "History"],
                    grades=["9", "10", "11", "12"],
                    style="Inquiry-based",
                    language="English",
                    author="InstaSchool",
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat(),
                    tags=["high-school", "inquiry", "research", "critical-thinking"]
                ),
                "structure": TemplateStructure(
                    topic_count=5,
                    media_richness=3,
                    include_quizzes=True,
                    include_summary=True,
                    include_resources=True,
                    include_keypoints=True,
                    topic_templates=[
                        {"title_pattern": "Essential Questions about {concept}", "focus": "driving questions"},
                        {"title_pattern": "Investigating {concept}", "focus": "research methods"},
                        {"title_pattern": "Evidence and Analysis: {concept}", "focus": "data interpretation"},
                        {"title_pattern": "Perspectives on {concept}", "focus": "multiple viewpoints"},
                        {"title_pattern": "Synthesis: Understanding {concept}", "focus": "drawing conclusions"}
                    ],
                    custom_prompts={
                        "content": "Frame content as investigative questions. Encourage students to think like researchers and consider multiple perspectives. Include primary sources when possible."
                    }
                )
            },
            {
                "metadata": TemplateMetadata(
                    id="math_problem_solving",
                    name="Mathematical Problem Solving",
                    description="Step-by-step mathematics curriculum emphasizing problem-solving strategies",
                    subjects=["Mathematics"],
                    grades=["3", "4", "5", "6", "7", "8"],
                    style="Project-based",
                    language="English",
                    author="InstaSchool",
                    created_at=datetime.now().isoformat(),
                    updated_at=datetime.now().isoformat(),
                    tags=["mathematics", "problem-solving", "step-by-step"]
                ),
                "structure": TemplateStructure(
                    topic_count=4,
                    media_richness=3,
                    include_quizzes=True,
                    include_summary=True,
                    include_resources=True,
                    include_keypoints=True,
                    topic_templates=[
                        {"title_pattern": "Understanding {concept}", "focus": "conceptual foundation"},
                        {"title_pattern": "Strategies for {concept}", "focus": "problem-solving methods"},
                        {"title_pattern": "Practice with {concept}", "focus": "guided practice"},
                        {"title_pattern": "Real-World {concept}", "focus": "applications"}
                    ],
                    custom_prompts={
                        "content": "Present multiple solution strategies. Include visual representations and real-world problems. Emphasize the thinking process, not just the answer."
                    }
                )
            }
        ]
        
        # Save built-in templates
        for template_data in builtin_templates:
            template_file = self.templates_dir / "system" / f"{template_data['metadata'].id}.json"
            if not template_file.exists():
                self._save_template_file(template_file, template_data)
    
    def _save_template_file(self, file_path: Path, template_data: Dict[str, Any]):
        """Save template data to file
        
        Args:
            file_path: Path to save template
            template_data: Template data to save
        """
        # Convert dataclasses to dictionaries
        save_data = {
            "metadata": asdict(template_data["metadata"]),
            "structure": asdict(template_data["structure"])
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, indent=2)
    
    def _load_template_file(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Load template data from file with validation
        
        Args:
            file_path: Path to template file
            
        Returns:
            Template data or None if failed
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate structure
            if not self._validate_template_data(data):
                print(f"Invalid template data in {file_path}")
                return None
            
            # Convert back to dataclasses with validation
            try:
                metadata = TemplateMetadata(**data["metadata"])
                structure = TemplateStructure(**data["structure"])
                
                return {"metadata": metadata, "structure": structure}
                
            except (TypeError, ValueError) as e:
                print(f"Template dataclass creation failed for {file_path}: {e}")
                return None
                
        except json.JSONDecodeError as e:
            print(f"JSON decode error in template {file_path}: {e}")
            return None
        except Exception as e:
            print(f"Error loading template {file_path}: {e}")
            return None
    
    def _validate_template_data(self, data: Dict[str, Any]) -> bool:
        """Validate template data structure
        
        Args:
            data: Template data to validate
            
        Returns:
            True if valid, False otherwise
        """
        # Check required top-level keys
        required_keys = ["metadata", "structure"]
        if not all(key in data for key in required_keys):
            return False
            
        # Validate metadata
        metadata = data.get("metadata", {})
        required_meta_keys = ["id", "name", "description", "subjects", "grades"]
        if not all(key in metadata for key in required_meta_keys):
            return False
            
        # Validate structure
        structure = data.get("structure", {})
        required_struct_keys = ["topic_count", "media_richness"]
        if not all(key in structure for key in required_struct_keys):
            return False
            
        # Validate data types
        try:
            if not isinstance(metadata.get("subjects"), list):
                return False
            if not isinstance(metadata.get("grades"), list):
                return False
            if not isinstance(structure.get("topic_count"), int):
                return False
            if not isinstance(structure.get("media_richness"), int):
                return False
        except (TypeError, ValueError):
            return False
            
        return True
    
    def create_template(self, 
                       name: str,
                       description: str,
                       curriculum: Dict[str, Any],
                       author: str = "User",
                       tags: List[str] = None,
                       is_public: bool = False) -> str:
        """Create a new template from an existing curriculum
        
        Args:
            name: Template name
            description: Template description
            curriculum: Source curriculum
            author: Template author
            tags: Optional tags
            is_public: Whether template is public
            
        Returns:
            Template ID
        """
        if tags is None:
            tags = []
        
        # Extract metadata from curriculum
        meta = curriculum.get("meta", {})
        units = curriculum.get("units", [])
        
        # Create template ID
        template_id = f"user_{uuid.uuid4().hex[:8]}"
        
        # Create metadata
        metadata = TemplateMetadata(
            id=template_id,
            name=name,
            description=description,
            subjects=[meta.get("subject", "")],
            grades=[meta.get("grade", "")],
            style=meta.get("style", "Standard"),
            language=meta.get("language", "English"),
            author=author,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat(),
            tags=tags,
            is_public=is_public
        )
        
        # Extract structure from curriculum
        structure = TemplateStructure(
            topic_count=len(units),
            media_richness=meta.get("media_richness", 3),
            include_quizzes=meta.get("include_quizzes", True),
            include_summary=meta.get("include_summary", True),
            include_resources=meta.get("include_resources", True),
            include_keypoints=meta.get("include_keypoints", True),
            topic_templates=[
                {"title": unit.get("title", ""), "focus": "general"}
                for unit in units
            ]
        )
        
        # Save template
        template_data = {"metadata": metadata, "structure": structure}
        save_dir = "shared" if is_public else "user"
        template_file = self.templates_dir / save_dir / f"{template_id}.json"
        self._save_template_file(template_file, template_data)
        
        return template_id
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a template by ID
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template data or None if not found
        """
        # Search in all directories
        for subdir in ["user", "system", "shared"]:
            template_file = self.templates_dir / subdir / f"{template_id}.json"
            if template_file.exists():
                return self._load_template_file(template_file)
        
        return None
    
    def list_templates(self, 
                      subject_filter: Optional[str] = None,
                      grade_filter: Optional[str] = None,
                      include_user: bool = True,
                      include_system: bool = True,
                      include_shared: bool = True) -> List[TemplateMetadata]:
        """List available templates
        
        Args:
            subject_filter: Filter by subject
            grade_filter: Filter by grade
            include_user: Include user templates
            include_system: Include system templates
            include_shared: Include shared templates
            
        Returns:
            List of template metadata
        """
        templates = []
        
        # Determine which directories to search
        search_dirs = []
        if include_user:
            search_dirs.append("user")
        if include_system:
            search_dirs.append("system")
        if include_shared:
            search_dirs.append("shared")
        
        # Load templates from directories
        for subdir in search_dirs:
            template_dir = self.templates_dir / subdir
            if template_dir.exists():
                for template_file in template_dir.glob("*.json"):
                    template_data = self._load_template_file(template_file)
                    if template_data:
                        metadata = template_data["metadata"]
                        
                        # Apply filters
                        if subject_filter and subject_filter not in metadata.subjects:
                            continue
                        if grade_filter and grade_filter not in metadata.grades:
                            continue
                        
                        templates.append(metadata)
        
        # Sort by usage count and creation date
        templates.sort(key=lambda t: (t.usage_count, t.created_at), reverse=True)
        return templates
    
    def apply_template(self, 
                      template_id: str,
                      subject: str,
                      grade: str,
                      custom_params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Apply a template to generate curriculum parameters
        
        Args:
            template_id: Template to apply
            subject: Target subject
            grade: Target grade
            custom_params: Optional parameter overrides
            
        Returns:
            Generation parameters based on template
        """
        template_data = self.get_template(template_id)
        if not template_data:
            raise ValueError(f"Template {template_id} not found")
        
        metadata = template_data["metadata"]
        structure = template_data["structure"]
        
        if custom_params is None:
            custom_params = {}
        
        # Increment usage count
        metadata.usage_count += 1
        metadata.updated_at = datetime.now().isoformat()
        
        # Save updated metadata (find and update the file)
        for subdir in ["user", "system", "shared"]:
            template_file = self.templates_dir / subdir / f"{template_id}.json"
            if template_file.exists():
                self._save_template_file(template_file, template_data)
                break
        
        # Build generation parameters
        params = {
            "subject_str": subject,
            "grade": grade,
            "lesson_style": custom_params.get("style", metadata.style),
            "language": custom_params.get("language", metadata.language),
            "media_richness": custom_params.get("media_richness", structure.media_richness),
            "include_quizzes": custom_params.get("include_quizzes", structure.include_quizzes),
            "include_summary": custom_params.get("include_summary", structure.include_summary),
            "include_resources": custom_params.get("include_resources", structure.include_resources),
            "include_keypoints": custom_params.get("include_keypoints", structure.include_keypoints),
            "custom_prompt": custom_params.get("custom_prompt", ""),
            "template_id": template_id,
            "template_name": metadata.name,
            "expected_topics": structure.topic_count,
            "topic_templates": structure.topic_templates,
            "custom_prompts": structure.custom_prompts
        }
        
        return params
    
    def delete_template(self, template_id: str, user_only: bool = True) -> bool:
        """Delete a template
        
        Args:
            template_id: Template to delete
            user_only: Only allow deletion of user templates
            
        Returns:
            True if deleted successfully
        """
        # Determine which directories to search
        search_dirs = ["user"] if user_only else ["user", "shared"]
        
        for subdir in search_dirs:
            template_file = self.templates_dir / subdir / f"{template_id}.json"
            if template_file.exists():
                try:
                    template_file.unlink()
                    return True
                except Exception as e:
                    print(f"Error deleting template {template_id}: {e}")
                    return False
        
        return False
    
    def update_template(self, 
                       template_id: str,
                       updates: Dict[str, Any],
                       user_only: bool = True) -> bool:
        """Update template metadata
        
        Args:
            template_id: Template to update
            updates: Dictionary of updates to apply
            user_only: Only allow updates to user templates
            
        Returns:
            True if updated successfully
        """
        # Load template
        template_data = self.get_template(template_id)
        if not template_data:
            return False
        
        # Find template file
        search_dirs = ["user"] if user_only else ["user", "shared"]
        template_file = None
        
        for subdir in search_dirs:
            candidate_file = self.templates_dir / subdir / f"{template_id}.json"
            if candidate_file.exists():
                template_file = candidate_file
                break
        
        if not template_file:
            return False
        
        # Apply updates to metadata
        metadata = template_data["metadata"]
        for key, value in updates.items():
            if hasattr(metadata, key):
                setattr(metadata, key, value)
        
        metadata.updated_at = datetime.now().isoformat()
        
        # Save updated template
        try:
            self._save_template_file(template_file, template_data)
            return True
        except Exception as e:
            print(f"Error updating template {template_id}: {e}")
            return False
    
    def search_templates(self, query: str) -> List[TemplateMetadata]:
        """Search templates by name, description, or tags
        
        Args:
            query: Search query
            
        Returns:
            List of matching template metadata
        """
        query_lower = query.lower()
        all_templates = self.list_templates()
        matching_templates = []
        
        for template in all_templates:
            # Search in name, description, and tags
            searchable_text = f"{template.name} {template.description} {' '.join(template.tags)}".lower()
            
            if query_lower in searchable_text:
                matching_templates.append(template)
        
        return matching_templates
    
    def get_template_stats(self) -> Dict[str, Any]:
        """Get template usage statistics
        
        Returns:
            Statistics about templates
        """
        all_templates = self.list_templates()
        
        stats = {
            "total_templates": len(all_templates),
            "user_templates": len([t for t in all_templates if t.id.startswith("user_")]),
            "system_templates": len([t for t in all_templates if not t.id.startswith("user_") and not t.is_public]),
            "shared_templates": len([t for t in all_templates if t.is_public]),
            "total_usage": sum(t.usage_count for t in all_templates),
            "popular_templates": sorted(all_templates, key=lambda t: t.usage_count, reverse=True)[:5],
            "recent_templates": sorted(all_templates, key=lambda t: t.created_at, reverse=True)[:5],
            "subjects": list(set(subject for t in all_templates for subject in t.subjects)),
            "grades": list(set(grade for t in all_templates for grade in t.grades))
        }
        
        return stats