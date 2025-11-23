# Audio Narration Quick Start Guide

## For Teachers

### Generating Audio for Your Curriculum

1. **Generate or Load a Curriculum**
   - Use Teacher Mode to create a curriculum
   - Or load an existing curriculum

2. **Navigate to View & Edit Tab**
   - Click the "✏️ View & Edit" tab
   - Expand any curriculum unit

3. **Generate Audio**
   - Scroll to the "🔊 Audio Narration" section
   - Select your preferred voice from dropdown:
     - **alloy**: Neutral, balanced (default)
     - **echo**: Male, clear voice
     - **fable**: British accent
     - **onyx**: Deep, authoritative
     - **nova**: Female, energetic
     - **shimmer**: Soft, friendly
   - Click "▶️ Generate Audio"
   - Wait 3-10 seconds for generation

4. **Listen and Review**
   - Audio player appears with controls
   - Click play to preview
   - Adjust voice if needed and regenerate

5. **Save Curriculum**
   - Audio is automatically saved with curriculum
   - Cached for 30 days for quick access

## For Students

### Listening to Lessons

1. **Load Curriculum in Student Mode**
   - Click "Student Mode" toggle
   - Select or load a curriculum

2. **Navigate to Content**
   - Go to any unit
   - Navigate to the "Content" section

3. **Listen to Lesson**
   - Audio player appears automatically if audio exists
   - Click play button to start listening
   - Can read along or just listen

4. **Controls**
   - Play/Pause button
   - Progress bar for seeking
   - Volume control
   - Standard browser audio controls

## Voice Comparison

| Voice | Description | Best For |
|-------|-------------|----------|
| alloy | Neutral, balanced | General use, all ages |
| echo | Male, clear | Older students, technical content |
| fable | British accent | Literature, engaging narratives |
| onyx | Deep, authoritative | Science, history, formal content |
| nova | Female, energetic | Younger students, fun subjects |
| shimmer | Soft, friendly | Early grades, soothing content |

## Tips & Best Practices

### For Teachers

**Voice Selection**
- Test different voices for your content
- Younger grades: Try nova or shimmer
- Older grades: Try echo or onyx
- Storytelling: Try fable

**Content Optimization**
- Clear, well-structured content generates better audio
- Break long paragraphs for better pacing
- Use punctuation to create natural pauses

**Cost Management**
- Audio is cached for 30 days
- Regenerate only when content changes
- Typical cost: $0.03 per lesson (~2000 chars)

### For Students

**Learning Strategies**
- Listen once without reading
- Listen again while reading along
- Take notes during playback
- Replay sections for better understanding

**Accessibility**
- Use headphones in quiet environments
- Adjust volume for comfort
- Pause frequently to process information

## Troubleshooting

### Audio Won't Generate

**Problem**: Button doesn't work or shows error

**Solutions**:
1. Check internet connection
2. Verify OpenAI API key is configured
3. Check API quota/billing
4. Try again in a few seconds

### Audio File Not Found

**Problem**: "Audio file not found" message

**Solutions**:
1. Click "Regenerate Audio"
2. Check if audio/ directory exists
3. Verify file permissions

### No Audio Player in Student Mode

**Problem**: Audio player doesn't appear

**Causes**:
- Audio not generated yet (Teacher Mode step needed)
- Unit doesn't have content
- Audio file was deleted from cache

**Solution**:
Generate audio in Teacher Mode first

### Audio Quality Issues

**Problem**: Audio sounds choppy or unclear

**Solutions**:
1. Try a different voice
2. Check browser audio settings
3. Ensure stable internet connection
4. Clear browser cache

## Advanced Features

### Multi-Chunk Content

**What It Is**: Long lessons split into multiple audio files

**When It Happens**: Content exceeds 4096 characters

**How It Works**:
- System automatically splits content
- Generates separate audio for each chunk
- Warning message shows chunk count

**Current Limitation**: Manual playback of each chunk
- Future versions will support auto-sequential playback

### Cache Management

**How Caching Works**:
- Audio files stored in `audio/` directory
- Based on content + voice combination
- Expires after 30 days

**Benefits**:
- Instant playback after first generation
- Reduced API costs
- Works offline once generated

**Manual Cleanup** (if needed):
```bash
# Remove all cached audio
rm -rf audio/

# Remove audio older than 30 days (automatic)
# Runs automatically during normal use
```

## API Usage & Costs

### Pricing (OpenAI TTS)
- **tts-1 model**: $15.00 per 1M characters
- **Per character**: $0.000015
- **Per 1000 chars**: ~$0.015

### Typical Costs
| Content Type | Avg Characters | Cost per Audio |
|--------------|----------------|----------------|
| Short lesson | 1,000 | $0.015 |
| Medium lesson | 2,000 | $0.030 |
| Long lesson | 4,000 | $0.060 |
| Full curriculum (5 units) | 10,000 | $0.150 |

### Cost Optimization
1. **Use caching**: Regenerate only when needed
2. **Batch generate**: Do all units at once
3. **Review before generating**: Ensure content is final
4. **Smart voice selection**: Pick right voice first time

## FAQ

**Q: Can I change the voice after generating?**
A: Yes, just select a new voice and click "Regenerate Audio"

**Q: Does audio work offline?**
A: Yes, once generated. Files are cached locally.

**Q: How long does generation take?**
A: Typically 3-10 seconds per unit

**Q: Can students download audio files?**
A: Not currently. Future feature.

**Q: What happens to audio when I edit content?**
A: Audio becomes outdated. Regenerate to match new content.

**Q: Is audio stored in exported files?**
A: Not currently. Audio is local cache only.

**Q: Can I batch-generate for entire curriculum?**
A: Not yet. Generate unit-by-unit currently.

**Q: Which voice is best for young children?**
A: Try "nova" or "shimmer" - friendly, energetic tones

**Q: Can I use custom voices?**
A: No, limited to 6 OpenAI TTS voices

**Q: Does audio support multiple languages?**
A: Yes, OpenAI TTS supports many languages automatically

## Getting Help

### Check Documentation
- `/Users/zackjordan/code/instaSchool/AUDIO_TTS_IMPLEMENTATION.md` - Full technical details
- `/Users/zackjordan/code/instaSchool/CLAUDE.md` - General project documentation

### Common Issues
1. Check verbose logs: `streamlit run main.py -- --verbose`
2. Verify config.yaml has `tts.enabled: true`
3. Ensure `audio/` directory exists and is writable
4. Check OpenAI API key is valid

### For Developers
- Test suite: `python -m pytest tests/test_audio_agent.py -v`
- AudioAgent source: `src/audio_agent.py`
- UI integration: `main.py` (search for "Audio Narration")
