# InstaSchool TODO – Outstanding Issues

**Last reviewed:** 2025-11-27 (verified against actual codebase)
**Version:** 1.6.0

Status tags:
- `TODO` = not started
- `IN PROGRESS` = currently being worked on
- `DONE` = implemented and verified in code

---

## ✅ COMPLETED - Core Features (v1.6.0)

### 1. Dependency Updates
- [x] Streamlit 1.51.0, OpenAI SDK 2.8.1
- [x] Python 3.9+ requirement documented

### 2. Student Progress Storage (JSON ↔ SQLite)
- [x] `StudentProgress` writes to DB via `self.db.save_progress()` (progress_manager.py:143)
- [x] Analytics/family dashboards use `DatabaseService`

### 3. SRS / Review Queue
- [x] `_create_flashcards_from_quiz()` auto-creates cards on quiz completion (student_ui.py:896-922)
- [x] Review Queue uses `SRSService.get_due_cards()`

### 4. Grading Fallback
- [x] `GradingResult.graded: bool` field exists (grading_agent.py:19)
- [x] On exception: `graded=False`, `is_correct=False` (grading_agent.py:147-153)

### 5. Provider Configuration
- [x] Only OpenAI + Kimi providers (v1.5.7)
- [x] Model lists standardized (v1.5.6)

---

## 🟡 REMAINING - Medium Priority Polish

### 6. Error Handling & Logging

**Status:** TODO
**Priority:** 🟡 Medium

- [ ] Audit `except Exception` blocks in core files
- [ ] Use specific exceptions: `APIError`, `RateLimitError`, `sqlite3.Error`
- [ ] Standardize on `VerboseLogger` over ad-hoc `print()`

### 7. UI/UX Improvements

**Status:** TODO
**Priority:** 🟡 Medium

- [ ] Group Teacher Mode advanced controls into `st.expander` blocks
- [ ] Mobile layout polish (card sizes, font sizes)
- [ ] Progress bar flicker reduction

### 8. Code Quality

**Status:** TODO
**Priority:** 🟢 Nice-to-have

- [ ] Decompose main.py into `render_teacher_mode()`, `render_parent_mode()`
- [ ] Clean up unused imports
- [ ] Create `constants.py` for magic numbers

---

## 🧪 QA Checklist (Manual Testing)

### Student Mode Flow
- [ ] Create student profile
- [ ] Generate 2-unit curriculum
- [ ] Complete sections, verify XP/level/badges update
- [ ] Complete quiz with high score, verify flashcards created
- [ ] Check Review Queue shows cards

### Parent Mode Flow
- [ ] Verify Parent dashboard shows correct child progress
- [ ] Verify Analytics tab matches Student sidebar data

### Grading Fallback
- [ ] Test with invalid API key
- [ ] Verify "not graded" message appears
- [ ] Verify no XP awarded on grading failure

### Provider Switching
- [ ] Switch from OpenAI to Kimi
- [ ] Verify text generation works
- [ ] Verify images still use OpenAI

---

## Completed Items Log

### v1.6.0 (2025-11-27)
- ✅ Unified student progress (JSON + SQLite)
- ✅ SRS auto-creates flashcards from quizzes
- ✅ Grading fallback with `graded: bool` flag
- ✅ Streamlit 1.51.0, OpenAI SDK 2.8.1
- ✅ Python 3.9+ requirement

### v1.5.7 (2025-11-26)
- ✅ Sidebar width 360px
- ✅ Removed DeepSeek/Ollama (only OpenAI + Kimi)
- ✅ Kimi model validation fixed

### v1.5.6 (2025-11-26)
- ✅ Model lists standardized
- ✅ Removed DALL-E (gpt-image-1 only)

### v1.5.4 (2025-11-26)
- ✅ AnalyticsService migrated to SQLite
- ✅ Widget key collisions fixed
- ✅ State initialization consolidated
