# InstaSchool Product Roadmap

> **Vision**: An affordable, easy-to-use AI curriculum generator for homeschool families, designed to run locally and adapt to each child's learning pace.

**Current Version**: v0.8.3
**Target Version**: v1.5
**Target Audience**: Homeschool parents with 1-5 children

---

## Design Principles

1. **Local-First**: Runs on your computer, your data stays with you
2. **Affordable**: Free/cheap AI options (Kimi K2), no subscription required
3. **Simple**: One-click setup, no server configuration
4. **Family-Scale**: Optimized for 1-5 students, not enterprise deployments
5. **Learning Science**: Evidence-based features that actually improve retention

---

## Architecture Overview

```
InstaSchool (Homeschool Edition)
├── UI: Streamlit (simple, Python-native, adequate for family use)
├── Database: SQLite (local, zero-config, portable)
├── AI Providers:
│   ├── OpenAI (quality, paid)
│   ├── Kimi K2 (quality, FREE tier available)
│   └── Ollama (optional, fully offline)
└── Distribution: pip install + CLI, or Docker one-liner
```

**Why Streamlit stays**: For 1-5 concurrent users on a single machine, Streamlit is perfectly adequate. It's fast to develop, easy to maintain, and doesn't require frontend expertise.

**Why SQLite**: No database server to configure. Portable - copy one file to backup. Perfect for family-scale data.

---

## Phase 0: Foundation (Now)
**Version**: v0.9.0 | **Effort**: 1-2 weeks

### 0.1 Multi-Provider AI Support

Add Kimi K2 alongside OpenAI for significant cost savings.

**Provider Comparison**:

| Provider | Quality | Cost | Best For |
|----------|---------|------|----------|
| OpenAI GPT-4.1 | Excellent | $15-30/1M tokens | Final content |
| OpenAI GPT-4.1-nano | Good | ~$0.10/1M tokens | Development/testing |
| **Kimi K2** | **Excellent** | **FREE tier** | Everything (default) |
| Ollama (local) | Varies | Free | Offline use |

**Implementation**:

```python
# config.yaml additions
ai_providers:
  default: "kimi"  # Switch easily

  openai:
    api_key_env: "OPENAI_API_KEY"
    base_url: "https://api.openai.com/v1"
    models:
      main: "gpt-4.1"
      worker: "gpt-4.1-mini"
      cheap: "gpt-4.1-nano"

  kimi:
    api_key_env: "MOONSHOT_API_KEY"
    base_url: "https://api.moonshot.ai/v1"
    models:
      main: "kimi-k2-0905-preview"
      worker: "kimi-k2-0905-preview"
      cheap: "kimi-k2-0905-preview"
    temperature: 0.6  # Recommended for Kimi

  ollama:
    base_url: "http://localhost:11434/v1"
    models:
      main: "llama3.1:8b"
      worker: "llama3.1:8b"
```

**Provider Switcher UI**:
- Dropdown in sidebar: "AI Provider: [OpenAI | Kimi K2 | Ollama]"
- Show current cost estimate based on provider
- Auto-detect which providers have valid API keys

**Kimi K2 Benefits**:
- OpenAI-compatible API (drop-in replacement)
- 1 trillion parameter MoE model
- 128K-256K context window
- Strong reasoning and tool calling
- Free tier available

### 0.2 SQLite Database Migration

Move from JSON files to SQLite for reliability.

**What Changes**:
- `curricula/*.json` → `instaschool.db` (curricula table)
- `curricula/users/*.json` → `instaschool.db` (users, progress tables)
- Automatic migration on first run

**Benefits**:
- No file corruption under concurrent writes
- Single file backup
- Query capabilities for analytics
- Still zero-config (SQLite is built into Python)

**Schema**:
```sql
-- Users (family members)
CREATE TABLE users (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    pin_hash TEXT,
    created_at TIMESTAMP,
    preferences JSON
);

-- Curricula
CREATE TABLE curricula (
    id TEXT PRIMARY KEY,
    title TEXT,
    subject TEXT,
    grade TEXT,
    content JSON,  -- Full curriculum data
    created_at TIMESTAMP,
    created_by TEXT
);

-- Progress per user per curriculum
CREATE TABLE progress (
    user_id TEXT,
    curriculum_id TEXT,
    current_section INTEGER,
    completed_sections JSON,
    xp INTEGER,
    badges JSON,
    stats JSON,
    updated_at TIMESTAMP,
    PRIMARY KEY (user_id, curriculum_id)
);

-- Review items for SRS (Phase 1)
CREATE TABLE review_items (
    id TEXT PRIMARY KEY,
    user_id TEXT,
    curriculum_id TEXT,
    card_front TEXT,
    card_back TEXT,
    easiness_factor REAL DEFAULT 2.5,
    interval INTEGER DEFAULT 1,
    repetitions INTEGER DEFAULT 0,
    next_review TIMESTAMP,
    created_at TIMESTAMP
);
```

### 0.3 Simple Distribution

Make it easy for non-technical parents to run.

**Option A: pip install (recommended)**
```bash
pip install instaschool
instaschool  # Opens browser automatically
```

**Option B: Docker one-liner**
```bash
docker run -p 8501:8501 -v ~/instaschool:/data instaschool/app
```

**Option C: Download & run (Windows/Mac)**
- Pre-built executable (PyInstaller)
- Download, double-click, done
- ~200MB standalone bundle

**Environment Setup**:
```bash
# Add to ~/.zshrc or ~/.bashrc
export MOONSHOT_API_KEY="your-key-here"  # Free at platform.moonshot.ai
export OPENAI_API_KEY="your-key-here"    # Optional
```

---

## Phase 1: Learning Science Core
**Version**: v1.0.0 | **Effort**: 3-4 weeks

These features are proven to improve learning outcomes. All work locally, no cloud required.

### 1.1 Spaced Repetition System (SRS)

**Why**: Without review, 70% of learned material is forgotten within weeks. SRS schedules optimal review times.

**How It Works**:
1. After each lesson, key concepts become flashcards
2. Cards appear in "Review Queue" based on SM-2 algorithm
3. Easy cards shown less often, hard cards more often
4. 5-10 minutes daily review = dramatic retention improvement

**UI**:
```
📚 Review Queue (7 cards due)
┌─────────────────────────────────┐
│  What is photosynthesis?        │
│                                 │
│  [Show Answer]                  │
└─────────────────────────────────┘

After reveal:
┌─────────────────────────────────┐
│  Photosynthesis is the process  │
│  plants use to convert sunlight │
│  into food (glucose).           │
│                                 │
│  How well did you remember?     │
│  [Again] [Hard] [Good] [Easy]   │
└─────────────────────────────────┘
```

**Parent Dashboard**:
- "Sarah reviewed 12 cards today"
- "Tommy has 5 overdue cards"
- Weekly retention trends

### 1.2 Mastery Gates

**Why**: Children shouldn't advance to new topics without understanding prerequisites.

**How It Works**:
1. Each unit has a quiz (already exists)
2. Need 80% to unlock next unit
3. Failed? Review highlighted weak areas, then retry
4. Parent can override if needed (homeschool flexibility)

**UI Changes**:
- Lock icon on unmastered units
- "Master this unit" button instead of just "Continue"
- Clear feedback: "You scored 65%. Review these topics, then try again."

### 1.3 Adaptive Difficulty

**Why**: Too easy = boredom. Too hard = frustration. Keep kids in the "zone of proximal development."

**How It Works**:
- Track success rate over last 10 questions
- If >85% correct → increase difficulty
- If <65% correct → decrease difficulty
- Target: ~75% success rate (optimal challenge)

**Difficulty Levers**:
- Vocabulary complexity
- Amount of scaffolding/hints
- Question type complexity
- Time pressure (optional)

### 1.4 Enhanced Question Types

Beyond multiple choice:

| Type | Example | Best For |
|------|---------|----------|
| Fill-in-blank | "Plants use ___ to make food" | Vocabulary |
| Matching | Connect terms to definitions | Relationships |
| Ordering | Put these events in sequence | Processes |
| True/False + Why | "True. Because..." | Deeper thinking |
| Draw/Label | Label parts of a cell | Visual learners |

**Implementation**: AI generates varied questions automatically from content.

---

## Phase 2: Parent & Family Features
**Version**: v1.2.0 | **Effort**: 2-3 weeks

Features specifically for homeschool family dynamics.

### 2.1 Multi-Child Dashboard

**Parent View**:
```
📊 Family Learning Dashboard

Sarah (Grade 5)          Tommy (Grade 3)
├─ Math: 72% complete    ├─ Science: 45% complete
├─ 🔥 8-day streak       ├─ 🔥 3-day streak
├─ Due: 4 review cards   ├─ Due: 12 review cards
└─ Last active: Today    └─ Last active: Yesterday

[+ Add Child]  [View Detailed Analytics]
```

**Quick Actions**:
- "Assign same curriculum to all children"
- "Compare progress across siblings"
- "Set daily learning goals"

### 2.2 Flexible Scheduling

**Why**: Homeschool schedules vary wildly. Support that flexibility.

**Features**:
- Set "school days" (e.g., Mon-Thu only)
- Define daily time blocks
- Vacation mode (pause streaks, extend review intervals)
- Co-op day integration (mark as "learning elsewhere")

### 2.3 Progress Reports

**Weekly Email Digest** (optional):
```
InstaSchool Weekly Report - Jordan Family

This Week:
✅ Sarah completed 3 units in Biology
✅ Tommy earned "Curious Mind" badge
⚠️ Sarah has 15 overdue review cards

Recommended Focus:
- Sarah: Schedule 15min review session
- Tommy: Ready to start "Forces & Motion"

[View Full Dashboard]
```

**Printable Reports**:
- PDF progress reports for portfolio/records
- State compliance documentation (varies by state)
- Skill checklist exports

### 2.4 Curriculum Customization

**Parent Controls**:
- Adjust content depth (brief/standard/deep)
- Add custom notes to any unit
- Skip units that don't apply
- Add supplemental resources
- Flag content for review before showing to child

---

## Phase 3: Engagement & Motivation
**Version**: v1.4.0 | **Effort**: 2-3 weeks

Keep kids engaged without expensive gamification infrastructure.

### 3.1 Daily Challenges

Simple, local-only challenges:
- "Answer 5 review cards" (+25 XP)
- "Complete 1 unit" (+50 XP)
- "Ask the tutor a question" (+10 XP)

No servers, no leaderboards - just personal goals.

### 3.2 Achievement System (Enhanced)

Expand current badge system:

**Learning Badges**:
- 🎯 First Perfect Score
- 📚 Bookworm (5 curricula started)
- 🏆 Master (curriculum 100% complete)
- 🔥 On Fire (7-day streak)
- 🌟 Superstar (30-day streak)

**Fun Badges**:
- 🦉 Night Owl (study after 8pm)
- 🌅 Early Bird (study before 8am)
- 🎨 Creative (completed art curriculum)
- 🔬 Scientist (completed science curriculum)

**Family Badges**:
- 👨‍👩‍👧‍👦 Family Study (all kids studied same day)
- 🤝 Helper (child helped sibling with topic)

### 3.3 Simple Certificates

Generate printable certificates:
- Curriculum completion certificates
- Monthly progress certificates
- Custom certificates (parent can edit text)

No blockchain, no verification servers - just nice PDFs the family can print and display.

---

## Phase 4: Advanced Features (Future)
**Version**: v1.5+ | **Effort**: As needed

Features to consider based on user feedback:

### 4.1 Offline Mode (Ollama Integration)

**Why**: Some families have unreliable internet or prefer complete privacy.

**How**:
- Integrate Ollama for local LLM inference
- Pre-download curricula for offline use
- Sync when connection available

**Models**:
- Llama 3.1 8B (runs on 8GB RAM)
- Mistral 7B (faster, slightly smaller)
- Phi-3 Mini (runs on modest hardware)

### 4.2 Co-op & Group Features

For homeschool co-ops:
- Share curricula with other families
- Group progress tracking
- Simple discussion threads (local network only)

**NOT building**: Cloud-based social features, leaderboards across internet, etc.

### 4.3 Voice & Accessibility

- Text-to-speech for all content (already have TTS)
- Voice input for answers
- Dyslexia-friendly fonts
- High contrast mode
- Screen reader support

### 4.4 State Compliance Tools

- Standards mapping (Common Core, state standards)
- Attendance tracking
- Portfolio generation for state reviews
- Learning hours calculator

---

## What We're NOT Building

To keep scope manageable:

| Feature | Why Not |
|---------|---------|
| Cloud hosting | Complexity, cost, privacy concerns |
| User accounts/auth server | Keep it local-first |
| Marketplace | Not enough scale to justify |
| LMS integration | Homeschool families don't use LMS |
| Mobile app | Streamlit works on mobile browsers |
| Real-time collaboration | Complexity for minimal benefit |
| Enterprise features | Wrong audience |
| Subscription billing | Keep it free/one-time |

---

## Technical Checklist

### Before Phase 1:
- [ ] Add Kimi K2 provider configuration
- [ ] Test Kimi K2 with existing agents
- [ ] Implement provider switcher UI
- [ ] Migrate JSON → SQLite
- [ ] Add database backup/export
- [ ] Create pip package structure
- [ ] Write installation docs

### Code Quality:
- [ ] Replace remaining print() statements
- [ ] Add basic test coverage (50%+)
- [ ] Error handling for API failures
- [ ] Graceful degradation when AI unavailable
- [ ] Logging for troubleshooting

### Documentation:
- [ ] README update for homeschool focus
- [ ] Installation guide (3 methods)
- [ ] API key setup guide
- [ ] Troubleshooting FAQ
- [ ] Video walkthrough

---

## Success Metrics

For a homeschool tool, success looks different:

### Usage (per family):
- Setup completed in <10 minutes
- At least 2 curricula created per month
- Daily usage by at least one child
- 70%+ review card completion

### Learning:
- Children report content is "right difficulty"
- Parents report less prep time
- Quiz scores improve over time
- Knowledge retained at 30-day check

### Satisfaction:
- Would recommend to other homeschool families
- Continued use after 3 months
- Feature requests (engaged users)

---

## Kimi K2 Quick Start

```python
# Test Kimi K2 connection
from openai import OpenAI
import os

client = OpenAI(
    api_key=os.environ["MOONSHOT_API_KEY"],
    base_url="https://api.moonshot.ai/v1"
)

response = client.chat.completions.create(
    model="kimi-k2-0905-preview",
    messages=[{"role": "user", "content": "Hello!"}],
    temperature=0.6
)
print(response.choices[0].message.content)
```

**Get API Key**: https://platform.moonshot.ai (free tier available)

---

*Last Updated: 2025-11-25*
*Version: Roadmap v2.0 (Homeschool Edition)*

**Sources for Kimi K2 information**:
- [Kimi K2 GitHub](https://github.com/MoonshotAI/Kimi-K2)
- [Moonshot AI Platform](https://platform.moonshot.ai/)
- [Kimi K2 Official Page](https://moonshotai.github.io/Kimi-K2/)
