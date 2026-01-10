"""
Curriculum Service
Handles business logic for curriculum generation, separated from UI
"""

import uuid
import json
import copy
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.agent_framework import OrchestratorAgent
from src.image_generator import ImageGenerator

# Import Supabase service for persistent storage
try:
    from services.supabase_service import get_supabase_service
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    get_supabase_service = None


class CurriculumService:
    """Service class for curriculum generation business logic"""
    
    def __init__(self, client, config: Dict[str, Any]):
        """Initialize the service with OpenAI client and configuration
        
        Args:
            client: OpenAI client instance
            config: Configuration dictionary
        """
        self.client = client
        self.config = config or {}

        defaults = self.config.get("defaults") or {}
        text_model = defaults.get("text_model") or "gpt-4.1-nano"
        worker_model = defaults.get("worker_model") or text_model
        image_model = defaults.get("image_model") or "gpt-image-1-mini"

        # Initialize Supabase service for persistent storage
        self._supabase = None
        if SUPABASE_AVAILABLE and get_supabase_service:
            self._supabase = get_supabase_service()
        
        # Initialize orchestrator
        self.orchestrator = OrchestratorAgent(
            client, 
            model=text_model,
            worker_model=worker_model,
        )
        
        # Initialize image generator
        self.image_generator = ImageGenerator(
            client, 
            image_model,
        )
        
    def validate_generation_params(self, params: Dict[str, Any]) -> tuple[bool, Optional[str]]:
        """Validate curriculum generation parameters
        
        Args:
            params: Parameters for generation
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        if not params.get("subject_str"):
            return False, "Please select at least one subject"
            
        if not params.get("grade"):
            return False, "Please select a grade level"
            
        # Validate image model exists (use provider_service for dynamic list)
        image_model = params.get("image_model")
        if image_model:
            try:
                from services.provider_service import get_provider_service
                ps = get_provider_service(self.config)
                valid_image_models = ps.get_image_models("openai")
                if image_model not in valid_image_models:
                    return False, f"Invalid image model: {image_model}"
            except Exception:
                # Fallback to config if provider_service not available
                if image_model not in self.config["defaults"].get("image_models", []):
                    return False, f"Invalid image model: {image_model}"
            
        # Validate text model exists (use provider_service for dynamic list)
        text_model = params.get("text_model")
        if text_model:
            try:
                from services.provider_service import get_provider_service
                ps = get_provider_service(self.config)
                # Check all providers for the model
                all_models = []
                for provider in ps.get_available_providers():
                    all_models.extend(ps.get_text_models(provider))
                if text_model not in all_models:
                    return False, f"Invalid text model: {text_model}"
            except Exception:
                # Fallback to config if provider_service not available
                if text_model not in self.config["defaults"].get("text_models", []):
                    return False, f"Invalid text model: {text_model}"
            
        return True, None
        
    def create_curriculum_metadata(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create curriculum metadata structure
        
        Args:
            params: Generation parameters
            
        Returns:
            Metadata dictionary
        """
        return {
            "id": uuid.uuid4().hex,
            "subject": params["subject_str"],
            "grade": params["grade"], 
            "style": params["lesson_style"],
            "media_richness": params["media_richness"],
            "text_model": params["text_model"],
            "worker_model": params.get("worker_model", params["text_model"]),
            "image_model": params["image_model"],
            "language": params["language"],
            "generated": str(datetime.now().isoformat()),
            "extra": params.get("custom_prompt", ""),
            "include_quizzes": params.get("include_quizzes", True),
            "include_summary": params.get("include_summary", True),
            "include_resources": params.get("include_resources", True),
            "include_keypoints": params.get("include_keypoints", True)
        }
        
    def generate_curriculum(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a complete curriculum
        
        Args:
            params: Generation parameters
            
        Returns:
            Generated curriculum dictionary
        """
        # Validate parameters
        is_valid, error_msg = self.validate_generation_params(params)
        if not is_valid:
            raise ValueError(error_msg)
            
        # Create curriculum structure
        curriculum = {
            "meta": self.create_curriculum_metadata(params),
            "units": []
        }
        
        # Update config with current parameters
        # IMPORTANT: do not mutate cached config objects (get_curriculum_service is cached).
        current_config = copy.deepcopy(self.config)
        current_config["defaults"]["text_model"] = params["text_model"]
        current_config["defaults"]["worker_model"] = params.get("worker_model", params["text_model"])  # Use worker_model if provided
        current_config["defaults"]["image_model"] = params["image_model"]
        current_config["defaults"]["image_size"] = params.get("image_size", "1024x1024")
        current_config["defaults"]["include_quizzes"] = params.get("include_quizzes", True)
        current_config["defaults"]["include_summary"] = params.get("include_summary", True)
        current_config["defaults"]["include_resources"] = params.get("include_resources", True)
        current_config["defaults"]["include_keypoints"] = params.get("include_keypoints", True)
        current_config["defaults"]["media_richness"] = params["media_richness"]
        
        # Create orchestrator with current models
        orchestrator = OrchestratorAgent(
            self.client,
            model=params["text_model"],
            worker_model=params.get("worker_model", params["text_model"])
        )
        
        # Generate using orchestrator
        generated_curriculum = orchestrator.create_curriculum(
            params["subject_str"],
            params["grade"],
            params["lesson_style"],
            params["language"],
            params.get("custom_prompt", ""),
            current_config
        )

        return generated_curriculum

    # =========================================================================
    # Supabase Persistence Methods
    # =========================================================================

    def save_to_supabase(
        self,
        curriculum: Dict[str, Any],
        status: str = "complete"
    ) -> Optional[str]:
        """Save curriculum to Supabase for persistent storage.

        Args:
            curriculum: The curriculum to save.
            status: Status of the curriculum ('generating', 'partial', 'complete').

        Returns:
            The Supabase UUID if successful, None otherwise.
        """
        if not self._supabase or not self._supabase.is_available:
            return None

        curriculum_id = self._supabase.save_curriculum(curriculum, status=status)
        if curriculum_id and "meta" in curriculum:
            curriculum["meta"]["supabase_id"] = curriculum_id
        return curriculum_id

    def update_supabase_status(
        self,
        curriculum_id: str,
        status: str,
        curriculum: Optional[Dict[str, Any]] = None
    ) -> bool:
        """Update curriculum status in Supabase.

        Args:
            curriculum_id: The Supabase UUID.
            status: New status ('generating', 'partial', 'complete').
            curriculum: Optional updated curriculum content.

        Returns:
            True if successful.
        """
        if not self._supabase or not self._supabase.is_available:
            return False

        return self._supabase.update_curriculum_status(curriculum_id, status, curriculum)

    def load_from_supabase(self, curriculum_id: str) -> Optional[Dict[str, Any]]:
        """Load a curriculum from Supabase.

        Args:
            curriculum_id: The Supabase UUID.

        Returns:
            The curriculum dictionary or None.
        """
        if not self._supabase or not self._supabase.is_available:
            return None

        return self._supabase.get_curriculum(curriculum_id)

    def list_supabase_curricula(
        self,
        subject: Optional[str] = None,
        grade: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """List curricula from Supabase with optional filters.

        Args:
            subject: Filter by subject.
            grade: Filter by grade.
            status: Filter by status.
            limit: Maximum results.

        Returns:
            List of curriculum metadata (not full content).
        """
        if not self._supabase or not self._supabase.is_available:
            return []

        return self._supabase.list_curricula(
            subject=subject, grade=grade, status=status, limit=limit
        )

    def delete_from_supabase(self, curriculum_id: str) -> bool:
        """Delete a curriculum from Supabase.

        Args:
            curriculum_id: The Supabase UUID.

        Returns:
            True if successful.
        """
        if not self._supabase or not self._supabase.is_available:
            return False

        return self._supabase.delete_curriculum(curriculum_id)

    def duplicate_in_supabase(self, curriculum_id: str) -> Optional[str]:
        """Duplicate a curriculum in Supabase.

        Args:
            curriculum_id: The Supabase UUID to duplicate.

        Returns:
            The new curriculum UUID or None.
        """
        if not self._supabase or not self._supabase.is_available:
            return None

        return self._supabase.duplicate_curriculum(curriculum_id)

    @property
    def supabase_available(self) -> bool:
        """Check if Supabase is available."""
        return self._supabase is not None and self._supabase.is_available

    def get_supabase_stats(self) -> Dict[str, Any]:
        """Get Supabase storage statistics."""
        if not self._supabase or not self._supabase.is_available:
            return {"available": False}

        return self._supabase.get_stats()

    def estimate_costs(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Estimate costs for curriculum generation
        
        Args:
            params: Generation parameters
            
        Returns:
            Cost estimation dictionary
        """
        min_topics = self.config["defaults"]["min_topics"]
        max_topics = self.config["defaults"]["max_topics"]
        topic_count = (min_topics + max_topics) // 2
        media_richness = params.get("media_richness", 3)
        include_quizzes = params.get("include_quizzes", True)
        include_summary = params.get("include_summary", True)
        include_resources = params.get("include_resources", True)
        image_model = params.get("image_model", "gpt-image-1")
        text_model = params.get("text_model", "gpt-4o")
        
        # Base token estimates per topic
        tokens_per_topic = {
            "outline": 1000,
            "content": 4000,
            "image_prompt": 300,
            "chart": 1000 if media_richness >= 3 else 0,
            "quiz": 2000 if include_quizzes else 0,
            "summary": 1000 if include_summary else 0,
            "resources": 1000 if include_resources else 0,
        }
        
        # Image counts based on media richness
        image_count = 0
        if media_richness >= 2:
            image_count = 1
        if media_richness >= 5:
            image_count = 3
            
        # Calculate totals
        input_tokens = sum(tokens_per_topic.values()) * topic_count
        output_tokens = input_tokens * 1.5  # rough estimate
        total_tokens = input_tokens + output_tokens
        
        # Model costs per 1K tokens (approximate - adjust based on actual pricing)
        # Source: OpenAI pricing page, Kimi pricing page (as of late 2025)
        model_costs = {
            # GPT-4o family
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "chatgpt-4o-latest": {"input": 0.005, "output": 0.015},
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4o-nano": {"input": 0.0001, "output": 0.0004},
            # GPT-4.1 family
            "gpt-4.1": {"input": 0.01, "output": 0.03},
            "gpt-4.1-mini": {"input": 0.0015, "output": 0.002},
            "gpt-4.1-nano": {"input": 0.0005, "output": 0.0015},
            # GPT-5 family
            "gpt-5": {"input": 0.02, "output": 0.06},
            "gpt-5-mini": {"input": 0.003, "output": 0.012},
            "gpt-5-nano": {"input": 0.001, "output": 0.004},
            # Kimi models (approximate - generally cheaper)
            "kimi-k2-thinking": {"input": 0.001, "output": 0.003},
            "kimi-k2-turbo-preview": {"input": 0.0005, "output": 0.0015},
            "kimi-k2-thinking-turbo": {"input": 0.0008, "output": 0.0024},
            "kimi-latest": {"input": 0.0003, "output": 0.001},
            "moonshot-v1-auto": {"input": 0.0002, "output": 0.0008},
        }
        
        # Get costs or use defaults
        main_model_cost = model_costs.get(text_model, {"input": 0.01, "output": 0.03})
        worker_model_cost = model_costs.get(self.config["defaults"]["worker_model"], {"input": 0.0015, "output": 0.002})
        
        # Calculate text costs
        input_cost = (input_tokens / 1000) * main_model_cost["input"]
        output_cost = (output_tokens / 1000) * main_model_cost["output"]
        worker_input_cost = (input_tokens / 1000) * worker_model_cost["input"]
        worker_output_cost = (output_tokens / 1000) * worker_model_cost["output"]
        
        # Image costs (only gpt-image models supported)
        image_costs = {
            "gpt-image-1": 0.02,
            "gpt-image-1-mini": 0.01,
        }
        image_cost = image_count * topic_count * image_costs.get(image_model, 0.02)
        
        # Calculate totals
        text_cost = input_cost + output_cost + worker_input_cost + worker_output_cost
        total_cost = text_cost + image_cost
        
        return {
            "total_tokens": total_tokens,
            "topic_count": topic_count,
            "image_count": image_count * topic_count,
            "total_cost": total_cost,
            "text_cost": text_cost,
            "image_cost": image_cost,
            "tokens_breakdown": tokens_per_topic,
            "cost_breakdown": {
                "main_model": input_cost + output_cost,
                "worker_model": worker_input_cost + worker_output_cost,
                "images": image_cost
            }
        }


class CurriculumValidator:
    """Validates curriculum data structures"""
    
    @staticmethod
    def validate_curriculum(curriculum: Dict[str, Any]) -> tuple[bool, List[str]]:
        """Validate curriculum structure
        
        Args:
            curriculum: Curriculum dictionary to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        if not isinstance(curriculum, dict):
            errors.append("Curriculum must be a dictionary")
            return False, errors
            
        # Check required top-level keys
        if "meta" not in curriculum:
            errors.append("Missing 'meta' section")
        if "units" not in curriculum:
            errors.append("Missing 'units' section")
            
        # Validate metadata
        if "meta" in curriculum:
            meta = curriculum["meta"]
            required_meta_fields = ["subject", "grade", "style", "language"]
            for field in required_meta_fields:
                if field not in meta:
                    errors.append(f"Missing required meta field: {field}")
                    
        # Validate units
        if "units" in curriculum:
            units = curriculum["units"]
            if not isinstance(units, list):
                errors.append("Units must be a list")
            else:
                for i, unit in enumerate(units):
                    if not isinstance(unit, dict):
                        errors.append(f"Unit {i} must be a dictionary")
                        continue
                        
                    if "title" not in unit:
                        errors.append(f"Unit {i} missing title")
                    if "content" not in unit:
                        errors.append(f"Unit {i} missing content")
                        
        return len(errors) == 0, errors


class CurriculumExporter:
    """Handles curriculum export functionality"""
    
    @staticmethod
    def generate_markdown(curriculum: Dict[str, Any], include_images: bool = True) -> str:
        """Generate Markdown representation of curriculum.

        Note: This method is a thin compatibility wrapper. The canonical export
        implementation lives in `services/export_service.py`.
        """
        from services.export_service import get_exporter

        exporter = get_exporter()
        return exporter.generate_markdown(curriculum, include_images=include_images)
