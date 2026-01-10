"""
Supabase Service for InstaSchool
Provides persistent storage for curricula and generation logs.
"""

import os
import json
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List, Union
from functools import lru_cache

# Import supabase client
try:
    from supabase import create_client, Client
    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    Client = None


def get_supabase_client() -> Optional[Client]:
    """Get or create a Supabase client singleton.

    Returns:
        Supabase client or None if not configured.
    """
    if not SUPABASE_AVAILABLE:
        print("Warning: supabase package not installed. Run: pip install supabase")
        return None

    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        print("Warning: SUPABASE_URL and SUPABASE_KEY environment variables not set")
        return None

    try:
        return create_client(url, key)
    except Exception as e:
        print(f"Error creating Supabase client: {e}")
        return None


class SupabaseService:
    """Service for interacting with Supabase database."""

    def __init__(self):
        """Initialize the Supabase service."""
        self._client = None
        self._initialized = False

    @property
    def client(self) -> Optional[Client]:
        """Lazy-load the Supabase client."""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    @property
    def is_available(self) -> bool:
        """Check if Supabase is configured and available."""
        return self.client is not None

    # =========================================================================
    # Curriculum Operations
    # =========================================================================

    def _optimize_curriculum_for_storage(self, curriculum: Dict[str, Any]) -> Dict[str, Any]:
        """Optimize curriculum images for cloud storage.

        First tries to compress/resize images. If still too large, strips them.

        Args:
            curriculum: Original curriculum with potential images.

        Returns:
            Copy of curriculum with optimized or stripped images.
        """
        import copy

        # First, try to optimize images
        try:
            from services.image_optimization_service import optimize_curriculum_images
            optimized = optimize_curriculum_images(curriculum, preset="storage", in_place=False)

            # Check if optimized version is small enough (< 5MB)
            optimized_size = self._estimate_json_size(optimized)
            if optimized_size < 5_000_000:
                print(f"Curriculum optimized to {optimized_size / 1_000_000:.1f}MB")
                return optimized
            else:
                print(f"Optimized curriculum still {optimized_size / 1_000_000:.1f}MB, stripping images")
        except ImportError:
            print("Image optimization service not available, falling back to stripping")

        # Fallback: strip images entirely if optimization isn't enough
        return self._strip_images_from_curriculum(curriculum)

    def _strip_images_from_curriculum(self, curriculum: Dict[str, Any]) -> Dict[str, Any]:
        """Remove base64 images from curriculum to reduce payload size.

        Args:
            curriculum: Original curriculum with potential images.

        Returns:
            Copy of curriculum with images replaced by placeholders.
        """
        import copy
        stripped = copy.deepcopy(curriculum)

        units = stripped.get("units", [])
        images_stripped = 0

        # Image field names to check (different curriculum versions use different names)
        image_fields = [
            "image_base64",
            "selected_image_b64",
            "image",
            "image_data",
            "thumbnail_b64",
        ]

        for unit in units:
            if not isinstance(unit, dict):
                continue

            # Check all known image field names
            for field in image_fields:
                if unit.get(field) and isinstance(unit.get(field), str) and len(unit.get(field)) > 1000:
                    unit[field] = None
                    unit["_image_stripped"] = True
                    images_stripped += 1

            # Also check for any field containing 'b64' or 'base64' with large content
            for key, val in list(unit.items()):
                if isinstance(val, str) and len(val) > 10000:
                    if "b64" in key.lower() or "base64" in key.lower() or "image" in key.lower():
                        unit[key] = None
                        unit["_image_stripped"] = True
                        images_stripped += 1

        if images_stripped > 0:
            stripped["_images_stripped"] = images_stripped
            stripped["_storage_note"] = "Images stored locally only due to size limits"

        return stripped

    def _estimate_json_size(self, obj: Any) -> int:
        """Estimate JSON size in bytes without full serialization."""
        try:
            return len(json.dumps(obj))
        except Exception:
            return 0

    def save_curriculum(
        self,
        curriculum: Dict[str, Any],
        status: str = "complete",
        strip_images: bool = True
    ) -> Optional[str]:
        """Save a curriculum to Supabase.

        Args:
            curriculum: Full curriculum dictionary with meta and units.
            status: Status string ('generating', 'partial', 'complete').
            strip_images: If True (default), remove base64 images to reduce size.

        Returns:
            The curriculum UUID if successful, None otherwise.
        """
        if not self.is_available:
            return None

        try:
            meta = curriculum.get("meta", {})
            units = curriculum.get("units", [])

            # Generate title from subject/grade if not provided
            title = meta.get("title") or f"{meta.get('subject', 'Curriculum')} - Grade {meta.get('grade', 'N/A')}"

            # Optimize images if content is large (> 1MB)
            content_to_save = curriculum
            estimated_size = self._estimate_json_size(curriculum)

            if strip_images and estimated_size > 1_000_000:  # 1MB threshold
                print(f"Optimizing curriculum for storage ({estimated_size / 1_000_000:.1f}MB)")
                content_to_save = self._optimize_curriculum_for_storage(curriculum)
                new_size = self._estimate_json_size(content_to_save)
                print(f"Reduced to {new_size / 1_000_000:.1f}MB")

            record = {
                "title": title,
                "subject": meta.get("subject", "Unknown"),
                "grade": str(meta.get("grade", "N/A")),
                "style": meta.get("style", "Standard"),
                "language": meta.get("language", "English"),
                "content": content_to_save,
                "unit_count": len(units),
                "status": status,
            }

            # Check if this curriculum already has a Supabase ID
            existing_id = meta.get("supabase_id")

            if existing_id:
                # Update existing record
                result = self.client.table("curricula").update(record).eq("id", existing_id).execute()
            else:
                # Insert new record
                result = self.client.table("curricula").insert(record).execute()

            if result.data:
                return result.data[0].get("id")
            return None

        except Exception as e:
            print(f"Error saving curriculum to Supabase: {e}")
            return None

    def update_curriculum_status(
        self,
        curriculum_id: str,
        status: str,
        content: Optional[Dict[str, Any]] = None,
        strip_images: bool = True
    ) -> bool:
        """Update the status of a curriculum.

        Args:
            curriculum_id: The UUID of the curriculum.
            status: New status ('generating', 'partial', 'complete').
            content: Optional updated content.
            strip_images: If True (default), remove base64 images to reduce size.

        Returns:
            True if successful, False otherwise.
        """
        if not self.is_available:
            return False

        try:
            update_data = {
                "status": status,
                "updated_at": datetime.utcnow().isoformat()
            }
            if content:
                # Optimize images if content is large
                content_to_save = content
                estimated_size = self._estimate_json_size(content)

                if strip_images and estimated_size > 1_000_000:  # 1MB threshold
                    content_to_save = self._optimize_curriculum_for_storage(content)

                update_data["content"] = content_to_save
                update_data["unit_count"] = len(content.get("units", []))

            result = self.client.table("curricula").update(update_data).eq("id", curriculum_id).execute()
            return bool(result.data)

        except Exception as e:
            print(f"Error updating curriculum status: {e}")
            return False

    def get_curriculum(self, curriculum_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a curriculum by ID.

        Args:
            curriculum_id: The UUID of the curriculum.

        Returns:
            The curriculum dictionary or None if not found.
        """
        if not self.is_available:
            return None

        try:
            result = self.client.table("curricula").select("*").eq("id", curriculum_id).single().execute()
            if result.data:
                return result.data.get("content")
            return None

        except Exception as e:
            print(f"Error retrieving curriculum: {e}")
            return None

    def list_curricula(
        self,
        subject: Optional[str] = None,
        grade: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """List curricula with optional filters.

        Args:
            subject: Filter by subject.
            grade: Filter by grade level.
            status: Filter by status.
            limit: Maximum number of results.
            offset: Offset for pagination.

        Returns:
            List of curriculum metadata (not full content).
        """
        if not self.is_available:
            return []

        try:
            # Select only metadata columns, not the full content
            query = self.client.table("curricula").select(
                "id, title, subject, grade, style, language, unit_count, status, created_at, updated_at"
            )

            if subject:
                query = query.eq("subject", subject)
            if grade:
                query = query.eq("grade", str(grade))
            if status:
                query = query.eq("status", status)

            query = query.order("created_at", desc=True).range(offset, offset + limit - 1)
            result = query.execute()

            return result.data or []

        except Exception as e:
            print(f"Error listing curricula: {e}")
            return []

    def delete_curriculum(self, curriculum_id: str) -> bool:
        """Delete a curriculum and its associated logs.

        Args:
            curriculum_id: The UUID of the curriculum.

        Returns:
            True if successful, False otherwise.
        """
        if not self.is_available:
            return False

        try:
            # Logs are deleted via CASCADE, so just delete the curriculum
            result = self.client.table("curricula").delete().eq("id", curriculum_id).execute()
            return bool(result.data)

        except Exception as e:
            print(f"Error deleting curriculum: {e}")
            return False

    def duplicate_curriculum(self, curriculum_id: str) -> Optional[str]:
        """Create a copy of an existing curriculum.

        Args:
            curriculum_id: The UUID of the curriculum to copy.

        Returns:
            The new curriculum UUID if successful, None otherwise.
        """
        if not self.is_available:
            return None

        try:
            # Get the original curriculum
            original = self.get_curriculum(curriculum_id)
            if not original:
                return None

            # Modify the title
            if "meta" in original:
                original["meta"]["title"] = original["meta"].get("title", "Curriculum") + " (Copy)"
                # Remove the old ID so a new one is generated
                original["meta"].pop("supabase_id", None)

            # Save as new
            return self.save_curriculum(original)

        except Exception as e:
            print(f"Error duplicating curriculum: {e}")
            return None

    # =========================================================================
    # Generation Log Operations
    # =========================================================================

    def log_generation_start(
        self,
        curriculum_id: Optional[str],
        agent: str,
        model: str,
        prompt_preview: Optional[str] = None
    ) -> Optional[str]:
        """Log the start of a generation task.

        Args:
            curriculum_id: The UUID of the curriculum being generated.
            agent: Name of the agent (e.g., 'orchestrator', 'content').
            model: Model being used (e.g., 'gpt-4.1-nano').
            prompt_preview: First 500 chars of the prompt.

        Returns:
            The log entry UUID if successful, None otherwise.
        """
        if not self.is_available:
            return None

        try:
            record = {
                "curriculum_id": curriculum_id,
                "agent": agent,
                "model": model,
                "prompt_preview": (prompt_preview[:500] if prompt_preview else None),
                "status": "started",
            }

            result = self.client.table("generation_logs").insert(record).execute()
            if result.data:
                return result.data[0].get("id")
            return None

        except Exception as e:
            print(f"Error logging generation start: {e}")
            return None

    def log_generation_complete(
        self,
        log_id: str,
        status: str = "completed",
        tokens_used: Optional[int] = None,
        duration_ms: Optional[int] = None
    ) -> bool:
        """Update a generation log entry with completion info.

        Args:
            log_id: The UUID of the log entry.
            status: Final status ('completed', 'failed').
            tokens_used: Number of tokens used.
            duration_ms: Duration in milliseconds.

        Returns:
            True if successful, False otherwise.
        """
        if not self.is_available:
            return False

        try:
            update_data = {"status": status}
            if tokens_used is not None:
                update_data["tokens_used"] = tokens_used
            if duration_ms is not None:
                update_data["duration_ms"] = duration_ms

            result = self.client.table("generation_logs").update(update_data).eq("id", log_id).execute()
            return bool(result.data)

        except Exception as e:
            print(f"Error updating generation log: {e}")
            return False

    def get_generation_logs(
        self,
        curriculum_id: str,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Get generation logs for a curriculum.

        Args:
            curriculum_id: The UUID of the curriculum.
            limit: Maximum number of logs to return.

        Returns:
            List of log entries.
        """
        if not self.is_available:
            return []

        try:
            result = self.client.table("generation_logs").select("*").eq(
                "curriculum_id", curriculum_id
            ).order("created_at", desc=False).limit(limit).execute()

            return result.data or []

        except Exception as e:
            print(f"Error retrieving generation logs: {e}")
            return []

    # =========================================================================
    # Utility Methods
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about stored curricula.

        Returns:
            Dictionary with counts and other stats.
        """
        if not self.is_available:
            return {"available": False}

        try:
            # Count total curricula
            total = self.client.table("curricula").select("id", count="exact").execute()

            # Count by status
            complete = self.client.table("curricula").select("id", count="exact").eq("status", "complete").execute()
            generating = self.client.table("curricula").select("id", count="exact").eq("status", "generating").execute()

            return {
                "available": True,
                "total_curricula": total.count or 0,
                "complete": complete.count or 0,
                "generating": generating.count or 0,
            }

        except Exception as e:
            print(f"Error getting stats: {e}")
            return {"available": True, "error": str(e)}


# Global instance for easy access
_supabase_service: Optional[SupabaseService] = None


def get_supabase_service() -> SupabaseService:
    """Get the global SupabaseService instance."""
    global _supabase_service
    if _supabase_service is None:
        _supabase_service = SupabaseService()
    return _supabase_service


class GenerationLogger:
    """Tracks generation events for visibility and logging to Supabase.

    This class provides a progress callback compatible with the agent framework
    that logs generation activity to both an in-memory list (for UI display)
    and optionally to Supabase (for persistence).
    """

    def __init__(
        self,
        curriculum_id: Optional[str] = None,
        model: str = "gpt-4.1-nano",
        supabase_service: Optional[SupabaseService] = None
    ):
        """Initialize the generation logger.

        Args:
            curriculum_id: Optional Supabase curriculum UUID for logging.
            model: The primary model being used.
            supabase_service: Optional SupabaseService instance.
        """
        self.curriculum_id = curriculum_id
        self.model = model
        self._supabase = supabase_service
        self._events: List[Dict[str, Any]] = []
        self._log_ids: Dict[str, str] = {}  # Maps event keys to Supabase log IDs
        self._start_times: Dict[str, datetime] = {}

    @property
    def events(self) -> List[Dict[str, Any]]:
        """Get all logged events."""
        return self._events.copy()

    def _log_to_supabase(
        self,
        agent: str,
        model: str,
        status: str,
        prompt_preview: Optional[str] = None,
        event_key: Optional[str] = None
    ) -> Optional[str]:
        """Log an event to Supabase.

        Args:
            agent: Name of the agent.
            model: Model being used.
            status: Event status.
            prompt_preview: Optional prompt preview.
            event_key: Key for tracking start/complete pairs.

        Returns:
            Log ID if successful.
        """
        if not self._supabase or not self._supabase.is_available:
            return None

        if status == "started":
            log_id = self._supabase.log_generation_start(
                self.curriculum_id, agent, model, prompt_preview
            )
            if log_id and event_key:
                self._log_ids[event_key] = log_id
            return log_id
        elif status in ("completed", "failed") and event_key:
            log_id = self._log_ids.get(event_key)
            if log_id:
                # Calculate duration
                duration_ms = None
                if event_key in self._start_times:
                    duration = datetime.now() - self._start_times[event_key]
                    duration_ms = int(duration.total_seconds() * 1000)
                self._supabase.log_generation_complete(
                    log_id, status=status, duration_ms=duration_ms
                )
                return log_id
        return None

    def log_event(
        self,
        event_type: str,
        agent: str,
        status: str,
        details: Optional[Dict[str, Any]] = None,
        model: Optional[str] = None,
        prompt_preview: Optional[str] = None
    ) -> None:
        """Log a generation event.

        Args:
            event_type: Type of event (e.g., 'planning', 'outline', 'content').
            agent: Name of the agent handling the event.
            status: Status of the event ('started', 'completed', 'failed').
            details: Optional additional details.
            model: Model used (defaults to self.model).
            prompt_preview: Optional prompt preview for logging.
        """
        event_key = f"{event_type}_{agent}"
        timestamp = datetime.now()
        model = model or self.model

        if status == "started":
            self._start_times[event_key] = timestamp

        duration_ms = None
        if status in ("completed", "failed") and event_key in self._start_times:
            duration = timestamp - self._start_times[event_key]
            duration_ms = int(duration.total_seconds() * 1000)

        event = {
            "timestamp": timestamp.isoformat(),
            "event_type": event_type,
            "agent": agent,
            "model": model,
            "status": status,
            "duration_ms": duration_ms,
            "details": details or {}
        }

        self._events.append(event)

        # Log to Supabase if available
        self._log_to_supabase(agent, model, status, prompt_preview, event_key)

    def create_progress_callback(self) -> callable:
        """Create a progress callback function for the agent framework.

        Returns:
            A callback function that logs progress events.
        """
        def progress_callback(event: str, data: Dict[str, Any]) -> None:
            """Progress callback for agent framework."""
            # Map event names to agent names and types
            event_mapping = {
                "planning_start": ("planning", "orchestrator", "started"),
                "planning_done": ("planning", "orchestrator", "completed"),
                "outline_start": ("outline", "outline_agent", "started"),
                "outline_done": ("outline", "outline_agent", "completed"),
                "topic_start": ("topic", "content_agent", "started"),
                "topic_done": ("topic", "content_agent", "completed"),
                "refine_start": ("refinement", "orchestrator", "started"),
                "done": ("refinement", "orchestrator", "completed"),
                "cancelled": ("generation", "orchestrator", "cancelled"),
            }

            if event in event_mapping:
                event_type, agent, status = event_mapping[event]

                # Add topic details if available
                details = {}
                if "topic_title" in data:
                    details["topic"] = data["topic_title"]
                if "topic_index" in data:
                    details["index"] = data["topic_index"]
                if "total_topics" in data:
                    details["total"] = data["total_topics"]
                if "topics_completed" in data:
                    details["completed"] = data["topics_completed"]

                self.log_event(event_type, agent, status, details)

        return progress_callback

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of the generation process.

        Returns:
            Summary dictionary with counts and timings.
        """
        total_duration_ms = 0
        event_counts = {"started": 0, "completed": 0, "failed": 0, "cancelled": 0}
        agents_used = set()

        for event in self._events:
            status = event.get("status", "")
            if status in event_counts:
                event_counts[status] = event_counts.get(status, 0) + 1
            if event.get("duration_ms"):
                total_duration_ms += event["duration_ms"]
            agents_used.add(event.get("agent", "unknown"))

        return {
            "total_events": len(self._events),
            "total_duration_ms": total_duration_ms,
            "event_counts": event_counts,
            "agents_used": list(agents_used),
            "model": self.model
        }
