# Streaming Support in InstaSchool

## Overview

InstaSchool now supports real-time streaming content generation, providing better UX with immediate feedback as content is being generated. This feature is particularly useful for long-form content where users want to see progress rather than waiting for the complete response.

## Architecture

### Core Components

1. **BaseAgent._call_model_streaming()** (`src/core/types.py`)
   - Low-level streaming method available to all agents
   - Handles OpenAI streaming API with proper error handling
   - Yields content chunks as they arrive
   - Returns complete response after streaming completes
   - Supports logging and all typed exceptions

2. **ContentAgent.generate_content()** (`src/agent_framework.py`)
   - Enhanced with optional `stream: bool = False` parameter
   - Maintains backward compatibility (default is non-streaming)
   - Integrates with existing caching system
   - Yields cached content in chunks for consistent behavior

### Design Decisions

**Backward Compatibility**: The streaming feature is opt-in via a `stream` parameter. All existing code continues to work without changes.

**Caching Integration**: When streaming is enabled, the system still checks the cache first. If content is cached, it's yielded in simulated chunks to maintain consistent behavior with live streaming.

**Error Handling**: Uses the same typed OpenAI exceptions as non-streaming methods, ensuring consistent error reporting and handling across the application.

**Logging**: Streaming calls are logged with the endpoint marked as "chat.completions (streaming)" for easy identification in logs.

## Usage

### Basic Streaming Usage

```python
from openai import OpenAI
from src.agent_framework import ContentAgent
from config import load_config

# Initialize
client = OpenAI(api_key="your-api-key")
config = load_config()
agent = ContentAgent(client, model="gpt-4.1-mini", config=config)

# Stream content generation
content_stream = agent.generate_content(
    topic="The Solar System",
    subject="Astronomy",
    grade="7th Grade",
    style="engaging",
    extra="Include recent discoveries",
    language="English",
    include_keypoints=True,
    stream=True  # Enable streaming
)

# Process chunks as they arrive
for chunk in content_stream:
    print(chunk, end='', flush=True)  # Real-time display
    # Or: accumulate, process, display in UI, etc.
```

### Non-Streaming (Default) Usage

```python
# Same parameters, but stream=False (or omitted)
content = agent.generate_content(
    topic="The Solar System",
    subject="Astronomy",
    grade="7th Grade",
    style="engaging",
    extra="Include recent discoveries",
    language="English",
    include_keypoints=True
    # stream defaults to False - backward compatible
)

print(content)  # Complete content returned at once
```

### Streamlit Integration (Future)

```python
import streamlit as st

# Create a placeholder for streaming content
content_placeholder = st.empty()
full_content = ""

# Stream and update display in real-time
for chunk in content_stream:
    full_content += chunk
    content_placeholder.markdown(full_content)
```

## API Reference

### BaseAgent._call_model_streaming()

```python
def _call_model_streaming(
    self,
    messages: list,
    response_format=None,
    temperature: float = 0.7
) -> Generator[str, None, str]:
    """
    Call the model with streaming enabled for real-time output.

    Args:
        messages: List of message dictionaries for the API
        response_format: Optional response format specification
        temperature: Temperature parameter for generation

    Yields:
        str: Content chunks as they arrive from the API

    Returns:
        str: The complete response text after streaming completes,
             or None on error
    """
```

**Features**:
- Respects model temperature support (automatically excludes for o1, o3, o4, gpt-5-nano)
- Full error handling with typed exceptions
- Logging support for debugging
- Yields error messages on failures for graceful degradation

### ContentAgent.generate_content()

```python
def generate_content(
    self,
    topic: str,
    subject: str,
    grade: str,
    style: str,
    extra: str,
    language: str,
    include_keypoints: bool,
    stream: bool = False
) -> Union[str, Generator[str, None, str]]:
    """
    Generate lesson content with optional streaming support.

    Args:
        topic: The topic to generate content for
        subject: The subject area
        grade: The grade level
        style: The teaching style
        extra: Additional requirements/guidelines
        language: The language for content
        include_keypoints: Whether to include key takeaways
        stream: If True, yields content chunks as they arrive

    Returns:
        str: Complete content (when stream=False)
        Generator[str, None, str]: Content chunks (when stream=True)
    """
```

**Features**:
- Backward compatible (stream defaults to False)
- Integrates with SmartCache
- Yields cached content in chunks when streaming
- Consistent error handling whether streaming or not

## Error Handling

Streaming methods handle all OpenAI exceptions gracefully:

| Exception | Behavior | Retryable |
|-----------|----------|-----------|
| `RateLimitError` | Yields error message, logs | No (yields error) |
| `AuthenticationError` | Yields error, shows UI warning | No |
| `APIConnectionError` | Yields error message, logs | No (yields error) |
| `BadRequestError` | Yields error message, logs | No |
| `APIError` (quota) | Yields error, shows UI warning | No |
| `APIError` (other) | Yields error message, logs | No (yields error) |
| `Exception` (unexpected) | Yields error message, logs | No |

**Error Message Format**: `[Error: {error_type} - {error_message}]`

This makes it easy to detect errors in the stream and handle them appropriately in the UI.

## Performance Considerations

### Network Efficiency
- Streaming reduces perceived latency by showing content immediately
- Total API time is similar to non-streaming, but UX is better
- Small overhead from chunk processing (typically <5%)

### Memory Usage
- Streaming processes chunks incrementally
- Lower peak memory for very large responses
- Full response still accumulated for caching

### Caching
- Cache lookups happen before streaming starts
- Cached content is yielded in 50-character chunks
- Same cache behavior whether streaming or not

## Testing

Run the streaming tests:

```bash
# Test all streaming functionality
python test_streaming.py

# Expected output:
# - BaseAgent streaming test
# - ContentAgent streaming test
# - Backward compatibility test
# All tests should PASS
```

The test suite covers:
1. BaseAgent low-level streaming
2. ContentAgent streaming integration
3. Backward compatibility (non-streaming still works)

## Limitations

1. **Response Format**: Streaming may not support all response formats (e.g., JSON mode might not stream properly with some models)

2. **Retry Logic**: Current implementation doesn't retry streaming calls automatically. Errors are yielded as chunks instead.

3. **Progress Tracking**: Streaming doesn't provide token count or completion percentage during generation.

4. **Model Support**: All OpenAI models support streaming, but some third-party providers may not.

## Future Enhancements

1. **UI Integration**: Add Streamlit components that consume streaming generators
2. **Progress Indicators**: Implement token-based progress estimation
3. **Streaming for Other Agents**: Extend streaming to OutlineAgent, SummaryAgent, etc.
4. **Retry with Streaming**: Implement retry logic that works with streaming
5. **Multiple Streams**: Support concurrent streaming for multiple topics

## Migration Guide

### For Existing Code

No changes required! Streaming is opt-in:

```python
# Old code (still works)
content = agent.generate_content(topic, subject, grade, style, extra, language, keypoints)

# New streaming capability (when ready)
stream = agent.generate_content(topic, subject, grade, style, extra, language, keypoints, stream=True)
```

### For New Features

When adding streaming to new code:

1. Add `stream: bool = False` parameter to your method
2. Use `_call_model_streaming()` instead of `_call_model()` when stream=True
3. Ensure your method returns a generator when streaming
4. Test both streaming and non-streaming modes
5. Document the streaming behavior in docstrings

## Support

For issues or questions:
- Check logs in verbose mode: `streamlit run main.py -- --verbose`
- Review error messages in the stream output
- Ensure OpenAI API key is valid and has quota
- Test with `test_streaming.py` to isolate issues
