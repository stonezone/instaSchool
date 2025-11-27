"""
Audio Agent for Text-to-Speech Generation
Handles audio narration for curriculum content using OpenAI's TTS API
"""

import hashlib
from pathlib import Path
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from src.core.types import BaseAgent


class AudioAgent(BaseAgent):
    """Agent responsible for generating audio narration using OpenAI TTS API"""

    def __init__(self, client, config: Dict[str, Any]):
        """Initialize AudioAgent with OpenAI client and configuration

        Args:
            client: OpenAI client instance
            config: Configuration dictionary containing TTS settings
        """
        # AudioAgent doesn't use text models, so we don't pass a model to BaseAgent
        super().__init__(client, model="tts-1")

        # Extract TTS configuration
        self.tts_config = config.get("tts", {})
        self.enabled = self.tts_config.get("enabled", True)
        self.default_voice = self.tts_config.get("default_voice", "alloy")
        self.available_voices = self.tts_config.get("available_voices",
            ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])
        self.tts_model = self.tts_config.get("model", "tts-1")
        self.max_chars = self.tts_config.get("max_chars", 4096)

        # Setup audio cache directory
        self.audio_dir = Path("audio")
        self.audio_dir.mkdir(exist_ok=True)

        # Cache expiration (30 days)
        self.cache_expiry_days = 30

        # Initialize logger if available
        try:
            from src.verbose_logger import get_logger
            self.logger = get_logger()
        except ImportError:
            self.logger = None

    def _log(self, message: str, level: str = "info"):
        """Log message using logger if available, otherwise silent in production."""
        if self.logger:
            if level == "warning":
                self.logger.log_warning(message)
            elif level == "error":
                self.logger.log_error(message)
            elif level == "debug":
                self.logger.log_debug(message)
            else:
                self.logger.log_info(message)

    def generate_audio(
        self,
        content: str,
        voice: Optional[str] = None,
        unit_title: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Generate audio narration for content

        Args:
            content: Text content to convert to speech
            voice: Voice to use (defaults to config default_voice)
            unit_title: Optional title for logging/debugging

        Returns:
            Dictionary with audio file path and metadata, or None on error
        """
        if not self.enabled:
            self._log("TTS is disabled in configuration", "debug")
            return None

        if not content:
            self._log("No content provided for audio generation", "warning")
            return None

        # Use default voice if none specified
        if not voice:
            voice = self.default_voice

        # Validate voice
        if voice not in self.available_voices:
            self._log(f"Invalid voice '{voice}', using default '{self.default_voice}'", "warning")
            voice = self.default_voice

        # Check cache first
        cached_audio = self._get_cached_audio(content, voice)
        if cached_audio:
            self._log(f"Using cached audio for: {unit_title or 'content'}", "debug")
            return cached_audio

        # Truncate or chunk content if needed
        chunks = self._chunk_content(content)

        if len(chunks) > 1:
            self._log(f"Content exceeds {self.max_chars} chars, generating {len(chunks)} audio chunks")

        # Generate audio for each chunk
        audio_files = []
        for i, chunk in enumerate(chunks):
            chunk_audio = self._generate_audio_chunk(chunk, voice, unit_title, chunk_index=i)
            if chunk_audio:
                audio_files.append(chunk_audio)
            else:
                self._log(f"Failed to generate audio for chunk {i+1}/{len(chunks)}", "error")
                return None

        # If single chunk, return directly
        if len(audio_files) == 1:
            return audio_files[0]

        # For multiple chunks, return list with metadata
        return {
            "type": "multi_chunk",
            "chunks": audio_files,
            "voice": voice,
            "total_chunks": len(audio_files)
        }

    def _chunk_content(self, content: str) -> List[str]:
        """Split content into chunks that fit within max_chars limit

        Args:
            content: Text content to chunk

        Returns:
            List of content chunks
        """
        if len(content) <= self.max_chars:
            return [content]

        chunks = []
        current_chunk = ""

        # Split by paragraphs first
        paragraphs = content.split('\n\n')

        for para in paragraphs:
            # If single paragraph exceeds limit, split by sentences
            if len(para) > self.max_chars:
                sentences = para.split('. ')
                for sentence in sentences:
                    if len(current_chunk) + len(sentence) + 2 <= self.max_chars:
                        current_chunk += sentence + '. '
                    else:
                        if current_chunk:
                            chunks.append(current_chunk.strip())
                        current_chunk = sentence + '. '
            else:
                # Add paragraph to current chunk if it fits
                if len(current_chunk) + len(para) + 2 <= self.max_chars:
                    current_chunk += para + '\n\n'
                else:
                    if current_chunk:
                        chunks.append(current_chunk.strip())
                    current_chunk = para + '\n\n'

        # Add remaining content
        if current_chunk:
            chunks.append(current_chunk.strip())

        return chunks

    def _generate_audio_chunk(
        self,
        text: str,
        voice: str,
        unit_title: Optional[str] = None,
        chunk_index: int = 0
    ) -> Optional[Dict[str, Any]]:
        """Generate audio for a single chunk of text

        Args:
            text: Text to convert to speech
            voice: Voice to use
            unit_title: Optional title for logging
            chunk_index: Index of chunk (for multi-chunk content)

        Returns:
            Dictionary with audio file path and metadata, or None on error
        """
        try:
            # Log the request
            if self.logger:
                self.logger.log_api_request(
                    model=self.tts_model,
                    endpoint="audio.speech",
                    params={
                        "voice": voice,
                        "text_length": len(text),
                        "chunk_index": chunk_index
                    }
                )

            # Call OpenAI TTS API
            response = self.client.audio.speech.create(
                model=self.tts_model,
                voice=voice,
                input=text
            )

            # Generate cache filename based on content hash and voice
            cache_key = self._generate_cache_key(text, voice)
            audio_filename = f"{cache_key}_{chunk_index if chunk_index > 0 else ''}.mp3".replace("__", "_")
            audio_path = self.audio_dir / audio_filename

            # Save audio to file
            response.stream_to_file(str(audio_path))

            # Log success
            if self.logger:
                self.logger.log_api_response(
                    model=self.tts_model,
                    response={"status": "success", "file": str(audio_path)}
                )

            self._log(f"Generated audio: {audio_filename}")

            return {
                "path": str(audio_path),
                "voice": voice,
                "text_length": len(text),
                "chunk_index": chunk_index,
                "created_at": datetime.now().isoformat()
            }

        except Exception as e:
            error_msg = f"Audio generation error: {e}"
            self._log(error_msg, "error")

            if self.logger:
                self.logger.log_error(
                    error=e,
                    model=self.tts_model,
                    context=f"TTS generation for '{unit_title or 'content'}'"
                )

            # Check for quota errors
            if "insufficient_quota" in str(e).lower() or "quota" in str(e).lower():
                try:
                    import streamlit as st
                    st.error("⚠️ OpenAI API quota exceeded. Please check your billing details.")
                except ImportError:
                    pass

            return None

    def _generate_cache_key(self, content: str, voice: str) -> str:
        """Generate cache key from content and voice

        Args:
            content: Text content
            voice: Voice name

        Returns:
            Hash string for cache key
        """
        # Create hash from content and voice
        content_hash = hashlib.md5(f"{content}_{voice}".encode()).hexdigest()
        return content_hash[:16]  # Use first 16 chars

    def _get_cached_audio(self, content: str, voice: str) -> Optional[Dict[str, Any]]:
        """Check if audio is already cached

        Args:
            content: Text content
            voice: Voice name

        Returns:
            Cached audio info or None
        """
        cache_key = self._generate_cache_key(content, voice)

        # Check for any files matching this cache key
        matching_files = list(self.audio_dir.glob(f"{cache_key}*.mp3"))

        if not matching_files:
            return None

        # Check if cached file is expired
        audio_path = matching_files[0]
        file_age = datetime.now() - datetime.fromtimestamp(audio_path.stat().st_mtime)

        if file_age > timedelta(days=self.cache_expiry_days):
            self._log(f"Cached audio expired (age: {file_age.days} days), regenerating", "debug")
            audio_path.unlink()  # Delete expired file
            return None

        return {
            "path": str(audio_path),
            "voice": voice,
            "cached": True,
            "created_at": datetime.fromtimestamp(audio_path.stat().st_mtime).isoformat()
        }

    def cleanup_old_audio(self) -> int:
        """Remove audio files older than cache_expiry_days

        Returns:
            Number of files deleted
        """
        deleted_count = 0
        cutoff_date = datetime.now() - timedelta(days=self.cache_expiry_days)

        for audio_file in self.audio_dir.glob("*.mp3"):
            file_age = datetime.fromtimestamp(audio_file.stat().st_mtime)
            if file_age < cutoff_date:
                try:
                    audio_file.unlink()
                    deleted_count += 1
                except Exception as e:
                    self._log(f"Error deleting {audio_file}: {e}", "warning")

        if deleted_count > 0:
            self._log(f"Cleaned up {deleted_count} old audio files")

        return deleted_count

    def get_audio_for_unit(self, unit: Dict[str, Any], voice: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Generate audio narration for a curriculum unit

        Args:
            unit: Unit dictionary with 'title' and 'content' keys
            voice: Optional voice override

        Returns:
            Audio info dictionary or None
        """
        title = unit.get("title", "Untitled")
        content = unit.get("content", "")

        if not content:
            self._log(f"No content to narrate for unit: {title}", "warning")
            return None

        return self.generate_audio(content, voice=voice, unit_title=title)
