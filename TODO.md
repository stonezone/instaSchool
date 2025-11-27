# InstaSchool TODO – Outstanding Issues

**Last reviewed:** 2025-11-26 (consolidated from code review + time-aware validation)
**Version:** 1.5.7

Status tags:
- `TODO` = not started
- `PLANNED` = design agreed, not implemented
- `IN PROGRESS` = currently being worked on
- `DONE` = implemented and verified

---

## 1. CRITICAL: Dependency Updates (Time-Aware Validation)

**Status:** TODO
**Priority:** 🔴 Critical
**File:** `requirements.txt`

### 1.1 Update Python package versions
Current requirements.txt has outdated minimum versions that should be updated:

- [ ] **Streamlit**: Update `streamlit>=1.24.0` → `streamlit>=1.51.0`
  - Current: 1.51.0 (Oct 29, 2025)
  - New features: Custom components v2, frameless UI, bidirectional data flow, custom themes

- [ ] **OpenAI SDK**: Update `openai>=1.0.0` → `openai>=2.8.1`
  - Current: 2.8.1 (Nov 17, 2025)
  - Required for: GPT-5.1 support, Realtime API, improved async clients
  - **Note:** Python 3.9+ now required (was 3.7+)

### 1.2 Update Python version requirement
- [ ] Update CLAUDE.md and documentation to require Python 3.9+ (OpenAI SDK 2.x requirement)

---

## 2. Student Progress Storage (JSON ↔ SQLite)

**Status:** IN PROGRESS
**Priority:** 🔴 Critical
**Areas:** `src/student_mode/*`, `services/database_service.py`, `services/analytics_service.py`

### 2.1 Decide single source of truth
- [ ] Choose whether progress lives in SQLite (with JSON as cache) or JSON (with DB for analytics)
- [ ] Document decision in `src/student_mode/progress_manager.py`

### 2.2 Wire StudentProgress to DatabaseService
- [ ] Add adapter in `StudentProgress` to call `DatabaseService.save_progress()` / `get_progress()`
- [ ] On `save_progress()`: Write to JSON + DB (with error handling)
- [ ] On `_load_progress()`: Hydrate from DB first, fallback to JSON

### 2.3 Align analytics/family dashboards
- [ ] Update `services/analytics_service.py` to use `get_user_all_progress(user_id)` as canonical path
- [ ] Update `services/family_service.py` to use same data source
- [ ] Verify Parent dashboard shows correct XP, sections, streaks

### 2.4 Resolve xp/level field confusion
- [ ] Decide if `xp`/`level` live in top-level columns or inside `stats` JSON
- [ ] Make consistent between `StudentProgress` and `DatabaseService`

---

## 3. SRS / Review Queue Functionality

**Status:** IN PROGRESS
**Priority:** 🔴 Critical
**Areas:** `services/srs_service.py`, `src/student_mode/review_queue.py`

### 3.1 Wire flashcard creation into app flows
- [ ] Create cards when: unit completed, quiz completed with high score, grading returns feedback
- [ ] Implement `create_cards_for_unit(...)` helper
- [ ] Only create cards when `user_id` is known

### 3.2 AI-based card creation
- [ ] Either implement AI card generation or clearly stub/hide it
- [ ] Remove any UI implying AI flashcard generation if not implemented

### 3.3 Review Queue shows real cards
- [ ] Verify `DatabaseService` methods are called from `SRSService`
- [ ] Confirm `render_review_queue()` uses `SRSService.get_due_cards()`
- [ ] Add empty state messages ("All caught up" vs "No cards yet")

### 3.4 Review Queue controls
- [ ] On card rating: Update next review time, optionally award XP
- [ ] After review: Update sidebar counts, rerender with `st.rerun()`

---

## 4. Grading Fallback Behavior

**Status:** IN PROGRESS
**Priority:** 🟠 High
**Areas:** `src/grading_agent.py`, `src/student_mode/student_ui.py`

### 4.1 Make failures "not graded" instead of "correct"
- [ ] Return `GradingResult` with `is_correct=False` and clear feedback on failure
- [ ] Add `graded: bool` flag to distinguish true grading vs fallback

### 4.2 Avoid awarding XP for ungraded answers
- [ ] Only award XP when `graded=True` and `is_correct=True`
- [ ] For fallback cases, show feedback but don't change mastery/XP

### 4.3 Surface grading errors
- [ ] Route exceptions through `log_exception` / `ErrorHandler`
- [ ] Show user-friendly `st.warning` or `st.error`

---

## 5. Model Detection & Provider Configuration

**Status:** IN PROGRESS
**Priority:** 🟡 Medium
**Areas:** `src/model_detector.py`, `services/provider_service.py`

### 5.1 Update model_detector docstrings
- [ ] Document that only cheaper models are selected (gpt-4o-mini, gpt-4.1-mini/nano)
- [ ] Note O1/O3 models not selected unless explicitly configured

### 5.2 Validate provider defaults (UPDATED for v1.5.7)
- [ ] Validate `openai` models: gpt-4.1-mini, gpt-4.1-nano, gpt-image-1
- [ ] Validate `kimi` models: kimi-k2-thinking, kimi-k2-turbo-preview
- [ ] ~~DeepSeek and Ollama~~ - REMOVED in v1.5.7

### 5.3 Per-provider timeouts and retries
- [ ] Configure shorter timeouts for interactive UI
- [ ] More generous timeouts for batch jobs

---

## 6. Error Handling & Logging

**Status:** IN PROGRESS
**Priority:** 🟡 Medium
**Areas:** `src/error_handler.py`, `src/agent_framework.py`, `src/image_generator.py`

### 6.1 Reduce broad `except Exception`
- [ ] Audit all `except Exception` in core files
- [ ] Use specific exceptions: `APIError`, `RateLimitError`, `sqlite3.Error`, `JSONDecodeError`
- [ ] Log via `log_exception` / `ErrorHandler`

### 6.2 Standardize on VerboseLogger
- [ ] Replace ad-hoc `print()` with `VerboseLogger`
- [ ] Use `sys.stderr` only in early bootstrap

### 6.3 Error boundaries
- [ ] Avoid guessing return types from function names
- [ ] Have wrapped functions specify explicit `fallback` values

---

## 7. Streamlit UI & UX Improvements

**Status:** TODO
**Priority:** 🟡 Medium
**Areas:** `main.py`, `src/ui_components.py`, `src/student_mode/*`

### 7.1 Clarify or hide unfinished features
- [ ] If SRS not fully wired, hide Review Queue or label as "Beta"
- [ ] Disable AI flashcard generation buttons if not implemented

### 7.2 Simplify Teacher Mode layout
- [ ] Group advanced controls into `st.expander` blocks
- [ ] Keep main path (Topic → Grade → Sections → Generate) above the fold

### 7.3 Harden HTML/Markdown rendering
- [ ] Replace regex markdown parsing with `st.markdown` or `markdown` library
- [ ] HTML-escape user/AI strings when using `unsafe_allow_html=True`

### 7.4 Mobile layout polish
- [ ] Review `st.session_state["is_mobile"]` checks
- [ ] Adjust card sizes, font sizes, column counts for phones

### 7.5 Progress bar/status UI updates
- [ ] Simplify progress rendering to stable placeholders
- [ ] Reduce flicker/re-renders

### 7.6 Loading states for long-running actions
- [ ] Ensure every long-running action has spinner/status
- [ ] Add success/warning toast when done

---

## 8. Code Quality & Maintainability

**Status:** TODO
**Priority:** 🟢 Nice-to-have
**Areas:** `main.py`, `src/*`, `services/*`

### 8.1 Decompose main.py
- [ ] Extract `render_teacher_mode()`, `render_parent_mode()` to separate modules
- [ ] Keep `main.py` for bootstrapping, config, routing only

### 8.2 Clean up unused imports and dead code
- [ ] Remove unused imports
- [ ] Delete or move dead functions to "experimental/legacy" module

### 8.3 Input sanitization coverage
- [ ] Ensure all free-text inputs go through `InputValidator`

### 8.4 Cost estimation duplication
- [ ] Wrap all cost estimation behind single helper
- [ ] Remove duplicate calculation in `main.py`

### 8.5 Hard-coded UI strings & magic numbers
- [ ] Create `constants.py` / `strings.py` for reused values
- [ ] Ongoing cleanup, not single big change

---

## 9. Validation & QA Checklist

**Status:** TODO
**Priority:** 🟡 Medium

### After unifying progress storage:
- [ ] Create student, generate 2-unit curriculum, complete sections
- [ ] Verify: Student sidebar shows correct XP/level/streak/badges
- [ ] Verify: Parent dashboard shows matching data
- [ ] Verify: Analytics dashboard lists student with same totals

### After fixing SRS:
- [ ] Complete unit, confirm flashcards exist in DB
- [ ] Confirm cards appear in Review Queue
- [ ] Rate cards, confirm due counts update

### After grading changes:
- [ ] Simulate API failure (invalid key)
- [ ] Verify: Grading result is "not graded"
- [ ] Verify: No XP/mastery awarded
- [ ] Verify: User-friendly error message shown

---

## Completed Items (v1.5.3 - v1.5.7)

### v1.5.7 (2025-11-26)
- ✅ Sidebar width increased to 360px
- ✅ Removed DeepSeek and Ollama providers (only OpenAI + Kimi)
- ✅ Fixed Kimi model validation (added to config.yaml text_models)
- ✅ Updated Kimi config with correct temperature (1.0)

### v1.5.6 (2025-11-26)
- ✅ Standardized model lists (OpenAI + Kimi only)
- ✅ Removed DALL-E, only gpt-image-1 and gpt-image-1-mini

### v1.5.5 (2025-11-26)
- ✅ Added Kimi provider with thinking models

### v1.5.4 (2025-11-26)
- ✅ Parent Reports/Certificates child identification
- ✅ Migrated AnalyticsService to SQLite
- ✅ Provider config mismatch fixed
- ✅ Added `requests` to requirements.txt
- ✅ Parent Curricula metadata
- ✅ Removed StateManager threading lock
- ✅ Fixed widget key collisions (hash → hashlib.md5)
- ✅ Per-session temp file cleanup
- ✅ Exception logging improvements
- ✅ State initialization consolidation
- ✅ CSS fallback warning

### v1.5.3 (2025-11-26)
- ✅ Model detection/provider selection alignment
- ✅ Per-provider model lists in AIProviderService
