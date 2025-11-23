"""
Test suite for AudioAgent TTS functionality
"""

import os
import pytest
from pathlib import Path
from unittest.mock import Mock, MagicMock, patch
from src.audio_agent import AudioAgent


@pytest.fixture
def mock_client():
    """Create a mock OpenAI client"""
    client = Mock()

    # Mock the audio.speech.create method
    mock_response = Mock()
    mock_response.stream_to_file = Mock()

    client.audio.speech.create = Mock(return_value=mock_response)

    return client


@pytest.fixture
def test_config():
    """Create test configuration"""
    return {
        "tts": {
            "enabled": True,
            "default_voice": "alloy",
            "available_voices": ["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
            "model": "tts-1",
            "max_chars": 4096
        }
    }


@pytest.fixture
def audio_agent(mock_client, test_config):
    """Create an AudioAgent instance"""
    return AudioAgent(mock_client, test_config)


class TestAudioAgent:
    """Test cases for AudioAgent"""

    def test_initialization(self, audio_agent, test_config):
        """Test AudioAgent initializes correctly"""
        assert audio_agent.enabled == True
        assert audio_agent.default_voice == "alloy"
        assert audio_agent.tts_model == "tts-1"
        assert audio_agent.max_chars == 4096
        assert audio_agent.audio_dir.exists()

    def test_chunk_content_short(self, audio_agent):
        """Test content chunking for short content"""
        content = "This is a short piece of content."
        chunks = audio_agent._chunk_content(content)

        assert len(chunks) == 1
        assert chunks[0] == content

    def test_chunk_content_long(self, audio_agent):
        """Test content chunking for long content"""
        # Create content that exceeds max_chars
        long_content = "A" * 5000
        chunks = audio_agent._chunk_content(long_content)

        assert len(chunks) > 1
        for chunk in chunks:
            assert len(chunk) <= audio_agent.max_chars

    def test_generate_cache_key(self, audio_agent):
        """Test cache key generation"""
        content = "Test content"
        voice = "alloy"

        key1 = audio_agent._generate_cache_key(content, voice)
        key2 = audio_agent._generate_cache_key(content, voice)
        key3 = audio_agent._generate_cache_key("Different content", voice)

        # Same content should produce same key
        assert key1 == key2
        # Different content should produce different key
        assert key1 != key3
        # Key should be 16 characters
        assert len(key1) == 16

    def test_generate_audio_disabled(self, mock_client, test_config):
        """Test audio generation when TTS is disabled"""
        test_config["tts"]["enabled"] = False
        agent = AudioAgent(mock_client, test_config)

        result = agent.generate_audio("Test content")
        assert result is None

    def test_generate_audio_no_content(self, audio_agent):
        """Test audio generation with no content"""
        result = audio_agent.generate_audio("")
        assert result is None

    def test_generate_audio_invalid_voice(self, audio_agent):
        """Test audio generation with invalid voice falls back to default"""
        with patch.object(audio_agent, '_generate_audio_chunk') as mock_generate:
            mock_generate.return_value = {"path": "test.mp3", "voice": "alloy"}

            result = audio_agent.generate_audio("Test content", voice="invalid_voice")

            # Should use default voice
            mock_generate.assert_called_once()
            call_args = mock_generate.call_args
            assert call_args[0][1] == "alloy"  # Second argument is voice

    @patch('builtins.open', create=True)
    def test_get_audio_for_unit(self, mock_open, audio_agent):
        """Test getting audio for a curriculum unit"""
        unit = {
            "title": "Test Unit",
            "content": "This is test content for the unit."
        }

        with patch.object(audio_agent, 'generate_audio') as mock_generate:
            mock_generate.return_value = {
                "path": "test_audio.mp3",
                "voice": "alloy",
                "created_at": "2025-01-01T00:00:00"
            }

            result = audio_agent.get_audio_for_unit(unit, voice="nova")

            assert result is not None
            assert result["path"] == "test_audio.mp3"
            assert result["voice"] == "alloy"
            mock_generate.assert_called_once_with(
                unit["content"],
                voice="nova",
                unit_title="Test Unit"
            )

    def test_get_audio_for_unit_no_content(self, audio_agent):
        """Test getting audio for unit with no content"""
        unit = {
            "title": "Empty Unit",
            "content": ""
        }

        result = audio_agent.get_audio_for_unit(unit)
        assert result is None

    def test_cleanup_old_audio(self, audio_agent, tmp_path):
        """Test cleanup of old audio files"""
        # Override audio_dir to use temp directory
        audio_agent.audio_dir = tmp_path

        # Create some test files
        old_file = tmp_path / "old_audio.mp3"
        old_file.touch()

        # Set modification time to 31 days ago
        import time
        old_time = time.time() - (31 * 24 * 60 * 60)
        os.utime(old_file, (old_time, old_time))

        # Create a recent file
        new_file = tmp_path / "new_audio.mp3"
        new_file.touch()

        # Run cleanup
        deleted_count = audio_agent.cleanup_old_audio()

        # Old file should be deleted, new file should remain
        assert deleted_count == 1
        assert not old_file.exists()
        assert new_file.exists()


class TestAudioIntegration:
    """Integration tests for audio functionality"""

    def test_full_audio_generation_workflow(self, mock_client, test_config):
        """Test complete workflow from unit to audio"""
        agent = AudioAgent(mock_client, test_config)

        # Create a sample unit
        unit = {
            "title": "Introduction to Science",
            "content": "Science is the study of the natural world through observation and experimentation."
        }

        # Mock the audio generation
        with patch.object(agent, '_generate_audio_chunk') as mock_chunk:
            mock_chunk.return_value = {
                "path": "/path/to/audio.mp3",
                "voice": "alloy",
                "text_length": 89,
                "chunk_index": 0,
                "created_at": "2025-01-01T00:00:00"
            }

            result = agent.get_audio_for_unit(unit, voice="alloy")

            assert result is not None
            assert "path" in result
            assert result["voice"] == "alloy"

    def test_multi_chunk_audio_generation(self, mock_client, test_config):
        """Test audio generation for long content (multi-chunk)"""
        agent = AudioAgent(mock_client, test_config)

        # Create very long content
        long_content = "A" * 5000

        with patch.object(agent, '_generate_audio_chunk') as mock_chunk:
            mock_chunk.return_value = {
                "path": "/path/to/audio_chunk.mp3",
                "voice": "alloy",
                "text_length": 4096,
                "chunk_index": 0,
                "created_at": "2025-01-01T00:00:00"
            }

            result = agent.generate_audio(long_content)

            # Should generate multiple chunks
            assert mock_chunk.call_count > 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
