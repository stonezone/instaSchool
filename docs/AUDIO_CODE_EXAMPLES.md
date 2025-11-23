# Audio Agent Code Examples

## Basic Usage

### Initialize AudioAgent

```python
from src.audio_agent import AudioAgent
import yaml

# Load config
with open('config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize with OpenAI client
from openai import OpenAI
client = OpenAI(api_key="your-api-key")

# Create AudioAgent
audio_agent = AudioAgent(client, config)
```

### Generate Audio for Text

```python
# Simple text-to-speech
content = "This is a sample lesson about science."
audio_info = audio_agent.generate_audio(
    content=content,
    voice="alloy",
    unit_title="Science Intro"
)

# Result contains file path
if audio_info:
    print(f"Audio saved to: {audio_info['path']}")
    print(f"Voice used: {audio_info['voice']}")
    print(f"Created at: {audio_info['created_at']}")
```

### Generate Audio for Curriculum Unit

```python
# For a curriculum unit dictionary
unit = {
    "title": "Introduction to Photosynthesis",
    "content": "Photosynthesis is the process by which plants..."
}

# Generate with custom voice
audio_info = audio_agent.get_audio_for_unit(
    unit=unit,
    voice="nova"  # Energetic female voice
)

if audio_info:
    print("Audio generated successfully!")
else:
    print("Audio generation failed")
```

### Handle Long Content (Multi-Chunk)

```python
# Long content automatically chunks
long_content = "A" * 5000  # Exceeds 4096 limit

audio_result = audio_agent.generate_audio(
    content=long_content,
    voice="echo"
)

# Check for multi-chunk result
if audio_result.get("type") == "multi_chunk":
    print(f"Generated {audio_result['total_chunks']} chunks")
    for i, chunk_info in enumerate(audio_result["chunks"]):
        print(f"Chunk {i+1}: {chunk_info['path']}")
else:
    print(f"Single audio file: {audio_result['path']}")
```

## Advanced Usage

### Custom Voice Selection by Content Type

```python
def select_voice_by_grade(grade, subject):
    """Select appropriate voice based on grade and subject"""

    # Young students - friendly voices
    if grade in ["Preschool", "Kindergarten", "1", "2"]:
        return "shimmer"  # Soft and friendly

    # Elementary - energetic
    elif grade in ["3", "4", "5"]:
        return "nova"  # Female, energetic

    # Middle school - clear
    elif grade in ["6", "7", "8"]:
        return "echo"  # Male, clear

    # High school/University - authoritative
    else:
        return "onyx"  # Deep, authoritative

# Use it
voice = select_voice_by_grade("5", "Science")
audio_agent.generate_audio(content, voice=voice)
```

### Cache Management

```python
# Check for cached audio
from src.audio_agent import AudioAgent

agent = AudioAgent(client, config)

# Get cached audio if exists
cached = agent._get_cached_audio(
    content="Sample content",
    voice="alloy"
)

if cached:
    print(f"Cache hit! Using: {cached['path']}")
else:
    print("Cache miss, generating new audio")

# Manual cleanup
deleted_count = agent.cleanup_old_audio()
print(f"Cleaned up {deleted_count} old audio files")
```

### Batch Generation for Entire Curriculum

```python
def generate_audio_for_curriculum(curriculum, voice="alloy"):
    """Generate audio for all units in a curriculum"""

    agent = AudioAgent(client, config)
    results = []

    for i, unit in enumerate(curriculum.get("units", [])):
        print(f"Generating audio for unit {i+1}...")

        audio_info = agent.get_audio_for_unit(unit, voice=voice)

        if audio_info:
            # Store audio info in unit
            unit["audio"] = audio_info
            results.append({
                "unit_index": i,
                "success": True,
                "path": audio_info["path"]
            })
        else:
            results.append({
                "unit_index": i,
                "success": False,
                "error": "Generation failed"
            })

    return results

# Use it
curriculum = {...}  # Your curriculum data
results = generate_audio_for_curriculum(curriculum, voice="nova")

# Check results
success_count = sum(1 for r in results if r["success"])
print(f"Successfully generated {success_count}/{len(results)} audio files")
```

## Streamlit Integration Examples

### Teacher Mode - Audio Generation Button

```python
import streamlit as st

# In your View & Edit tab
if st.button("Generate Audio"):
    # Initialize agent if needed
    if "audio_agent" not in st.session_state:
        st.session_state.audio_agent = AudioAgent(client, config)

    # Generate with selected voice
    voice = st.selectbox("Voice", ["alloy", "echo", "fable", "onyx", "nova", "shimmer"])

    with st.spinner("Generating audio..."):
        audio_info = st.session_state.audio_agent.get_audio_for_unit(
            unit=current_unit,
            voice=voice
        )

        if audio_info:
            # Store in unit
            current_unit["audio"] = audio_info
            st.success("Audio generated!")

            # Display player
            with open(audio_info["path"], "rb") as f:
                audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")
        else:
            st.error("Failed to generate audio")
```

### Student Mode - Auto Audio Player

```python
import streamlit as st
import os

# In content display section
def display_content_with_audio(unit):
    """Display lesson content with audio player"""

    # Check for audio
    audio_data = unit.get("audio")

    if audio_data:
        audio_path = audio_data.get("path")

        if audio_path and os.path.exists(audio_path):
            st.markdown("#### 🔊 Listen to this lesson")

            # Display audio player
            with open(audio_path, "rb") as f:
                audio_bytes = f.read()
                st.audio(audio_bytes, format="audio/mp3")

            st.markdown("---")

    # Display text content
    st.markdown(unit.get("content", "No content available"))

# Use it
display_content_with_audio(current_unit)
```

### Voice Preview Widget

```python
import streamlit as st

def voice_selector_with_preview():
    """Voice selector with audio preview samples"""

    voices = {
        "alloy": "Neutral, balanced - good for all content",
        "echo": "Male, clear - technical and formal",
        "fable": "British accent - storytelling",
        "onyx": "Deep, authoritative - science & history",
        "nova": "Female, energetic - younger students",
        "shimmer": "Soft, friendly - early grades"
    }

    selected_voice = st.selectbox(
        "Select Voice",
        options=list(voices.keys()),
        format_func=lambda x: f"{x.title()} - {voices[x]}"
    )

    # Show description
    st.caption(voices[selected_voice])

    # Optional: Preview sample
    if st.button("Preview Voice"):
        sample_text = "Hello! This is a sample of what this voice sounds like."
        # Generate short sample
        # ... (implementation)

    return selected_voice
```

## Error Handling Patterns

### Comprehensive Error Handling

```python
def safe_audio_generation(unit, voice="alloy"):
    """Generate audio with comprehensive error handling"""

    try:
        # Check if content exists
        content = unit.get("content", "")
        if not content:
            return {
                "success": False,
                "error": "No content to generate audio from"
            }

        # Check content length
        if len(content) > 100000:  # Very long
            return {
                "success": False,
                "error": "Content too long for audio generation"
            }

        # Initialize agent
        agent = AudioAgent(client, config)

        # Generate audio
        audio_info = agent.get_audio_for_unit(unit, voice=voice)

        if audio_info:
            return {
                "success": True,
                "audio_info": audio_info
            }
        else:
            return {
                "success": False,
                "error": "Audio generation returned None"
            }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": type(e).__name__
        }

# Use it
result = safe_audio_generation(unit, voice="nova")

if result["success"]:
    print(f"Success! Audio: {result['audio_info']['path']}")
else:
    print(f"Error: {result['error']}")
```

### Quota Error Detection

```python
def handle_api_errors(unit, voice):
    """Handle API errors with specific messages"""

    try:
        agent = AudioAgent(client, config)
        return agent.get_audio_for_unit(unit, voice=voice)

    except Exception as e:
        error_msg = str(e).lower()

        if "quota" in error_msg or "insufficient_quota" in error_msg:
            st.error("⚠️ OpenAI API quota exceeded. Check your billing.")
            return None

        elif "rate_limit" in error_msg:
            st.warning("⏳ Rate limit reached. Please wait a moment.")
            return None

        elif "invalid_api_key" in error_msg:
            st.error("🔑 Invalid API key. Check your .env file.")
            return None

        else:
            st.error(f"❌ Error: {str(e)}")
            return None
```

## Testing Examples

### Unit Test for Audio Generation

```python
import pytest
from unittest.mock import Mock, patch
from src.audio_agent import AudioAgent

def test_audio_generation():
    """Test basic audio generation"""

    # Mock client
    mock_client = Mock()
    mock_response = Mock()
    mock_response.stream_to_file = Mock()
    mock_client.audio.speech.create = Mock(return_value=mock_response)

    # Create agent
    config = {"tts": {"enabled": True, "default_voice": "alloy",
                      "model": "tts-1", "max_chars": 4096,
                      "available_voices": ["alloy", "echo"]}}
    agent = AudioAgent(mock_client, config)

    # Generate audio
    content = "Test content"
    result = agent.generate_audio(content, voice="alloy")

    # Verify
    assert result is not None
    assert "path" in result
    assert result["voice"] == "alloy"
    mock_client.audio.speech.create.assert_called_once()
```

### Integration Test

```python
def test_full_workflow():
    """Test complete workflow from unit to audio"""

    # Create test unit
    unit = {
        "title": "Test Lesson",
        "content": "This is test content for audio generation."
    }

    # Initialize agent
    agent = AudioAgent(client, config)

    # Generate audio
    audio_info = agent.get_audio_for_unit(unit, voice="nova")

    # Verify audio file exists
    assert audio_info is not None
    assert os.path.exists(audio_info["path"])

    # Verify file is mp3
    assert audio_info["path"].endswith(".mp3")

    # Clean up
    os.remove(audio_info["path"])
```

## Utility Functions

### Get Audio Duration

```python
from mutagen.mp3 import MP3

def get_audio_duration(audio_path):
    """Get duration of audio file in seconds"""
    try:
        audio = MP3(audio_path)
        return audio.info.length
    except:
        return None

# Use it
duration = get_audio_duration(audio_info["path"])
print(f"Audio duration: {duration:.1f} seconds")
```

### Format Audio Metadata

```python
from datetime import datetime

def format_audio_metadata(audio_info):
    """Format audio metadata for display"""

    metadata = {
        "Voice": audio_info.get("voice", "Unknown").title(),
        "Duration": f"{audio_info.get('text_length', 0)} characters",
        "Created": audio_info.get("created_at", "Unknown"),
        "Cached": "✓" if audio_info.get("cached", False) else "✗"
    }

    return metadata

# Use it
metadata = format_audio_metadata(audio_info)
for key, value in metadata.items():
    st.text(f"{key}: {value}")
```

### Batch Voice Comparison

```python
def generate_voice_samples(sample_text, voices=None):
    """Generate same text with different voices for comparison"""

    if voices is None:
        voices = ["alloy", "echo", "fable", "onyx", "nova", "shimmer"]

    agent = AudioAgent(client, config)
    results = {}

    for voice in voices:
        audio_info = agent.generate_audio(
            content=sample_text,
            voice=voice,
            unit_title=f"Sample_{voice}"
        )

        if audio_info:
            results[voice] = audio_info["path"]

    return results

# Use it
sample = "Welcome to our lesson on photosynthesis."
samples = generate_voice_samples(sample)

# Display in Streamlit
for voice, path in samples.items():
    st.markdown(f"### {voice.title()}")
    with open(path, "rb") as f:
        st.audio(f.read(), format="audio/mp3")
```

## Configuration Examples

### Custom TTS Config

```yaml
# config.yaml
tts:
  enabled: true
  default_voice: "nova"  # Change default
  available_voices:
    - "alloy"
    - "echo"
    - "nova"
    - "shimmer"
  model: "tts-1"  # or "tts-1-hd" for higher quality
  max_chars: 4096

  # Optional custom settings
  cache_expiry_days: 30
  audio_format: "mp3"
  audio_quality: "standard"  # or "hd"
```

### Environment Variables

```bash
# .env
OPENAI_API_KEY=your-api-key-here
TTS_ENABLED=true
TTS_DEFAULT_VOICE=alloy
TTS_CACHE_DAYS=30
```

### Load from Environment

```python
import os
from dotenv import load_dotenv

load_dotenv()

# Override config with env vars
if os.getenv("TTS_ENABLED"):
    config["tts"]["enabled"] = os.getenv("TTS_ENABLED").lower() == "true"

if os.getenv("TTS_DEFAULT_VOICE"):
    config["tts"]["default_voice"] = os.getenv("TTS_DEFAULT_VOICE")

if os.getenv("TTS_CACHE_DAYS"):
    config["tts"]["cache_expiry_days"] = int(os.getenv("TTS_CACHE_DAYS"))
```

## Performance Optimization

### Parallel Generation

```python
from concurrent.futures import ThreadPoolExecutor

def parallel_audio_generation(units, voice="alloy", max_workers=3):
    """Generate audio for multiple units in parallel"""

    agent = AudioAgent(client, config)

    def generate_for_unit(unit):
        return agent.get_audio_for_unit(unit, voice=voice)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(generate_for_unit, units))

    return results

# Use it (be careful with API rate limits)
units = curriculum["units"]
results = parallel_audio_generation(units[:3], voice="alloy", max_workers=2)
```

### Cache Warming

```python
def warm_audio_cache(curriculum, voice="alloy"):
    """Pre-generate all audio to warm cache"""

    agent = AudioAgent(client, config)

    print("Warming audio cache...")
    for i, unit in enumerate(curriculum["units"], 1):
        print(f"Unit {i}/{len(curriculum['units'])}...")

        # Check if already cached
        cached = agent._get_cached_audio(
            unit.get("content", ""),
            voice
        )

        if cached:
            print(f"  ✓ Already cached")
            unit["audio"] = cached
        else:
            # Generate
            audio_info = agent.get_audio_for_unit(unit, voice=voice)
            if audio_info:
                print(f"  ✓ Generated")
                unit["audio"] = audio_info
            else:
                print(f"  ✗ Failed")

    print("Cache warming complete!")
```

## Summary

This document provides practical code examples for:
- Basic audio generation
- Advanced voice selection
- Streamlit UI integration
- Error handling
- Testing
- Performance optimization
- Cache management

For full implementation details, see:
- `/Users/zackjordan/code/instaSchool/src/audio_agent.py`
- `/Users/zackjordan/code/instaSchool/AUDIO_TTS_IMPLEMENTATION.md`
