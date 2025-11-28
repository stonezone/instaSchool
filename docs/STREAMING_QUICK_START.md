# Streaming Quick Start Guide

## TL;DR

InstaSchool now supports real-time streaming for content generation. Content appears as it's generated instead of waiting for the complete response.

## 30-Second Usage

```python
from src.agent_framework import ContentAgent

# Create agent (same as before)
agent = ContentAgent(client, model="gpt-4.1-mini", config=config)

# NEW: Enable streaming
for chunk in agent.generate_content(..., stream=True):
    print(chunk, end='', flush=True)  # Real-time output

# OLD: Still works (backward compatible)
content = agent.generate_content(...)  # Complete response
```

## What Changed?

### ContentAgent.generate_content()
- **New parameter**: `stream: bool = False`
- **When False** (default): Returns complete string (old behavior)
- **When True**: Returns generator that yields chunks (new behavior)

### BaseAgent
- **New method**: `_call_model_streaming(messages, ...)`
- Available to all agents that inherit from BaseAgent
- Yields content chunks from OpenAI streaming API

## Testing

```bash
python test_streaming.py
```

Expected: 3/3 tests pass ✓

## Examples

### Stream to Console
```python
stream = agent.generate_content(
    topic="Python Basics",
    subject="Programming",
    grade="High School",
    style="practical",
    extra="",
    language="English",
    include_keypoints=True,
    stream=True
)

for chunk in stream:
    print(chunk, end='', flush=True)
```

### Accumulate and Display
```python
full_content = ""
for chunk in stream:
    full_content += chunk
    # Update UI, log, process, etc.

print(f"Total: {len(full_content)} chars")
```

### Non-Streaming (Original)
```python
content = agent.generate_content(
    topic="Python Basics",
    subject="Programming",
    grade="High School",
    style="practical",
    extra="",
    language="English",
    include_keypoints=True
    # stream defaults to False
)
print(content)  # Complete response
```

## Key Points

1. **Backward Compatible**: All existing code works unchanged
2. **Opt-In**: Set `stream=True` to enable
3. **Cache-Aware**: Checks cache first, streams if not cached
4. **Error Handling**: Errors yielded as `[Error: ...]` chunks
5. **Logging**: All streaming calls logged for debugging

## What's Next?

- UI integration in main.py (not yet implemented)
- Progress indicators in Streamlit (future)
- Streaming for other agents (outline, summary, etc.)

## Full Documentation

See `/Users/zackjordan/code/instaSchool/docs/STREAMING.md` for:
- Complete API reference
- Error handling details
- Performance characteristics
- Architecture overview
- Migration guide
