# InstaSchool TODO – Architecture, Bugs, and UX Improvements

This file tracks the next wave of fixes and improvements identified in a deep code review (running on Streamlit + multi‑provider OpenAI).

Use the status tags consistently:
- `TODO` = not started
- `PLANNED` = design agreed, not implemented
- `IN PROGRESS` = currently being worked on
- `DONE` = implemented and verified

**Last reviewed:** 2025‑11‑27 (pass 2) 

---

## 1. Unify Student Progress Storage (JSON ↔ SQLite)

**Status:** IN PROGRESS (core wiring implemented in `StudentProgress` and DB; continue tightening analytics & docs)  
**Priority:** 🔴 Critical  
**Areas:** `src/student_mode/*`, `services/database_service.py`, `services/analytics_service.py`, `services/family_service.py`

### 1.1 Decide the single source of truth
- [ ] Choose whether long‑term progress lives primarily in:
  - Option A: SQLite (`progress` table via `DatabaseService`), with JSON only as a cache/migration layer, **or**
  - Option B: JSON files via `StudentProgress`, with DB only for aggregated analytics.
- [ ] Document the decision at the top of `src/student_mode/progress_manager.py` and in `services/database_service.py`.

### 1.2 Wire StudentProgress to DatabaseService (recommended path)
- [ ] Add a thin adapter in `StudentProgress` that can call `DatabaseService.save_progress(...)` and `DatabaseService.get_progress(...)`:
  - Map `StudentProgress.data` → DB columns: `current_section`, `completed_sections`, `xp`, `badges`, `stats`.
  - Keep per‑user JSON as a local cache / offline‑friendly backup.
- [ ] On every `save_progress()`:
  - [ ] Write to JSON as today.
  - [ ] Also call `DatabaseService.save_progress(user_id, curriculum_id, data)` when `user_id` is available.
  - [ ] Ensure `save_progress` failures to DB are logged but do not crash Student Mode (use `ErrorHandler` or `log_exception`).
- [ ] On `StudentProgress._load_progress()`:
  - [ ] If DB has a record, hydrate `self.data` from DB fields first.
  - [ ] If only JSON exists (legacy), load JSON and then opportunistically upsert into DB once.

### 1.3 Make analytics/family dashboards rely on the same data
- [ ] Update `services/analytics_service.py`:
  - [ ] Ensure `get_user_all_progress(user_id)` in `DatabaseService` is the canonical path for student progress.
  - [ ] Remove or clearly mark any JSON‑based analytics code as “legacy migration only”.
- [ ] Update `services/family_service.py`:
  - [ ] Confirm `get_child_progress_summary` and detailed views use `get_user_all_progress(...)`.
  - [ ] After wiring StudentProgress → DB, verify that Parent dashboard shows correct curricula count, sections completed, XP, and streaks for an actively used student.

### 1.4 Resolve `xp` / `level` field confusion
- [ ] In `DatabaseService.save_progress(...)`:
  - [ ] Decide whether `xp` and `level` live in top‑level columns, inside `stats`, or both.
  - [ ] Make this consistent with `StudentProgress` (currently uses `data["xp"]` and `data["level"]`).
- [ ] In `AnalyticsService.calculate_student_stats(...)`:
  - [ ] Stop reading `stats.get("xp")` / `stats.get("level")` if you decide to use top‑level columns.
  - [ ] Or, if you keep them in `stats`, ensure `DatabaseService.save_progress` writes those into `stats` JSON reliably.

---

## 2. Fix SRS / Review Queue Functionality

**Status:** IN PROGRESS (quiz‑based SRS card creation and review queue are live; consider expanding triggers and AI‑generated cards)  
**Priority:** 🔴 Critical (user‑visible feature)  
**Areas:** `services/srs_service.py`, `src/student_mode/review_queue.py`, `src/student_mode/student_ui.py`, `services/database_service.py`

### 2.1 Wire flashcard creation into app flows
- [ ] Identify when to create SRS cards:
  - Good candidates:
    - When a unit is completed.
    - When a quiz is completed with a high score.
    - When grading returns detailed feedback.
- [ ] Implement a “card creation” helper (e.g. `create_cards_for_unit(...)`) that:
  - [ ] Extracts 3–5 key facts or Q&A pairs from the unit (initially simple heuristics; later, AI).
  - [ ] Calls `SRSService.create_card(user_id, curriculum_id, front, back)` for each key fact.
- [ ] Ensure `create_card` is only called when `user_id` is known (Student Mode with a logged‑in user).

### 2.2 Implement or defer AI‑based card creation
- [ ] For now, either:
  - Minimal: Keep `SRSService.create_cards_from_content(...)` as a **non‑UI** helper and hide any “auto‑generate cards” buttons, **or**
  - Implement: Use the existing OpenAI client to generate a small set of flashcards from lesson text and call `create_card` for each.
- [ ] If keeping it stubbed:
  - [ ] Add clear comments and a TODO in `services/srs_service.py` and remove any UI implying AI flashcard generation is live.

### 2.3 Ensure Review Queue shows real cards
- [ ] Verify `DatabaseService.create_review_item(...)`, `get_due_reviews(...)`, and `update_review_item(...)` are called from `SRSService` and the review queue UI.
- [ ] In `src/student_mode/review_queue.py`:
  - [ ] Confirm `render_review_queue(user_id, db)` uses `SRSService.get_due_cards(...)` (or similar) to drive what’s displayed.
  - [ ] Add a clear empty state message when there are no due cards **and** some cards exist overall (e.g., “You’re all caught up today” vs. “You have no cards yet”).

### 2.4 Align Review Queue controls with progress
- [ ] When a card is rated (SM‑2 quality 0–5):
  - [ ] Update next review time via `SRSService.review_card(...)` (or similar) and persist to DB.
  - [ ] Optionally award a small amount of XP via `StudentProgress` and/or DB `progress`.
- [ ] After each review:
  - [ ] Update `student_view` / counts in sidebar (`srs.get_due_count(user_id)`) and re‑render the page using `st.rerun()`.

---

## 3. Correct Grading Fallback Behavior

**Status:** IN PROGRESS (GradingAgent now distinguishes graded vs. fallback; confirm all XP paths respect `graded`)  
**Priority:** 🟠 High (subtle but impactful on learning)  
**Areas:** `src/grading_agent.py`, `src/student_mode/student_ui.py`, any XP logic tied to grading

### 3.1 Make failures “not graded” instead of “correct”
- [ ] In `GradingAgent.grade_answer(...)`:
  - [ ] Change the exception handler to return a `GradingResult` with:
    - `is_correct=False`
    - A clear `feedback` message indicating the system failed to grade (e.g., “I had trouble grading this answer. Please try again or ask your tutor.”).
  - [ ] Consider adding a `graded: bool` flag to `GradingResult` to distinguish true grading vs. fallback.

### 3.2 Avoid awarding XP for ungraded answers
- [ ] In Student Mode wherever grading results are consumed:
  - [ ] Only award XP or mark questions as “mastered” when `graded=True` and `is_correct=True`.
  - [ ] For fallback “not graded” cases, show feedback but do **not** change mastery / XP.

### 3.3 Surface grading errors in logs/UI
- [ ] Route grading exceptions through `log_exception` / `ErrorHandler`:
  - [ ] Ensure the full stack trace is logged for debugging.
  - [ ] Show a concise user message via `st.warning` or `st.error` so the student isn’t silently misled.

---

## 4. Model Detection & Provider Configuration Clean‑up

**Status:** IN PROGRESS (model detector now intentionally filters to cheap/mini models; review provider defaults and docstrings next)  
**Priority:** 🟡 Medium  
**Areas:** `src/model_detector.py`, `services/provider_service.py`, `config.yaml`

### 4.1 Align model_detector behavior with documentation
- [ ] Update the docstring in `src/model_detector.py` to accurately describe behavior:
  - [ ] Emphasize that only cheaper models (`gpt‑4o‑mini`, `gpt‑4.1‑mini/nano`, etc.) are intentionally selected.
  - [ ] Note that `gpt‑3` / `gpt‑3.5` are explicitly excluded.
  - [ ] Clarify that O1/O3 models are **not** currently selected unless explicitly configured.

### 4.2 Ensure provider default models are valid
- [ ] Validate that all defaults in `AIProviderService.PROVIDERS` still exist in the current OpenAI, Kimi, DeepSeek, and Ollama endpoints:
  - [ ] `openai.models["main"/"worker"/"image"]`
  - [ ] `kimi` model names (e.g., `kimi-k2-thinking`, `kimi-k2-turbo-preview`)
  - [ ] `deepseek` model names.
- [ ] If any are deprecated, either:
  - [ ] Update to current recommended equivalents, or
  - [ ] Add a validation layer that gracefully falls back and surfaces a warning in the UI.

### 4.3 Timeouts and retries
- [ ] Consider configuring per‑provider `timeout` / `max_retries` in `AIProviderService.get_client(...)` using OpenAI’s `timeout` options:
  - [ ] Shorter timeouts for interactive UI flows.
  - [ ] More generous timeouts for batch jobs.

---

## 5. Error Handling & Logging Consistency

**Status:** IN PROGRESS (image download now uses a bounded timeout; further exception tightening still needed)  
**Priority:** 🟡 Medium  
**Areas:** `src/error_handler.py`, `src/agent_framework.py`, `src/audio_agent.py`, `src/image_generator.py`, `src/verbose_logger.py`, `main.py`

### 5.1 Reduce broad `except Exception` where critical
- [ ] Audit all `except Exception as e:` occurrences, especially in:
  - `src/agent_framework.py` (orchestrator pipeline)
  - `src/grading_agent.py`
  - `src/audio_agent.py`
  - `src/image_generator.py`
  - `src/student_mode/*`
- [ ] For each:
  - [ ] Use more specific exceptions where practical (`APIError`, `RateLimitError`, `sqlite3.Error`, `JSONDecodeError`, etc.).
  - [ ] Log via `log_exception` / `ErrorHandler` instead of just `print`.

### 5.2 Standardize on VerboseLogger for debug logging
- [ ] Replace ad‑hoc `print(...)`/`sys.stderr.write(...)` in core flows with:
  - [ ] `VerboseLogger` where fine‑grained API logging is needed.
  - [ ] Fall back to `sys.stderr` only in very early bootstrap code (e.g., before logger is available).

### 5.3 Error boundaries
- [ ] Revisit `ErrorHandler.with_error_boundary`:
  - [ ] Avoid guessing return types purely from function name (`generate`/`create`).
  - [ ] Option: have each wrapped function specify an explicit `fallback` value or strategy.

---

## 6. Streamlit UI & UX Improvements

**Status:** TODO  
**Priority:** 🟡 Medium  
**Areas:** `main.py`, `src/ui_components.py`, `src/student_mode/*`

### 6.1 Clarify or hide unfinished features
- [ ] In Student Mode:
  - [ ] If SRS is not fully wired, either:
    - Hide the Review Queue entry point, **or**
    - Label it clearly as “Beta / Coming Soon” with a brief explanation.
- [ ] In any UI that references AI flashcard generation:
  - [ ] Ensure it is either implemented or explicitly disabled with a tooltip explaining why.

### 6.2 Simplify Teacher Mode layout
- [ ] In `main.py` Teacher/“Create & Manage” mode:
  - [ ] Group advanced controls (provider selection, model overrides, cost estimator, image size) into `st.expander` blocks.
  - [ ] Keep the main path (“Topic → Grade → Sections → Generate”) visually prominent and above the fold.

### 6.3 Harden HTML/Markdown rendering
- [ ] In `src/ui_components.py` (`ModernUI.card` and related):
  - [ ] Replace ad‑hoc regex markdown parsing with either:
    - Streamlit’s `st.markdown` for inner content, or
    - The `markdown` library (`markdown.markdown(...)`) with sanitization.
  - [ ] Ensure any user/AI‑supplied strings are HTML‑escaped before embedding when using `unsafe_allow_html=True`.

### 6.4 Mobile layout polish
- [ ] Review all places where `st.session_state["is_mobile"]` is checked:
  - [ ] Confirm the “Mobile Layout” toggle and query‑param detection (`detect_mobile_from_query_params`) behave consistently.
  - [ ] Adjust card sizes, font sizes, and column counts to reduce vertical scrolling on phones.

---

## 7. Codebase Structure & Maintainability

**Status:** TODO  
**Priority:** 🟢 Nice‑to‑have  
**Areas:** `main.py`, `src/*`, `services/*`

### 7.1 Decompose `main.py`
- [ ] Extract mode‑specific entrypoints into separate modules or functions:
  - [ ] `render_teacher_mode(...)`
  - [ ] `render_parent_mode(...)`
  - [ ] `render_student_mode(...)` (already exists, imported from `src/student_mode/student_ui.py`)
- [ ] Keep `main.py` primarily responsible for:
  - [ ] Bootstrapping config, providers, and services.
  - [ ] Handling password protection and quickstart.
  - [ ] Routing to the appropriate mode function.

### 7.2 Clean up unused imports and dead code
- [ ] Remove unused imports in `main.py` (e.g. `requests`, `markdown`) if the logic has moved to other modules.
- [ ] Grep for obviously dead functions / stubs that are no longer referenced; either:
  - [ ] Delete them, or
  - [ ] Move them to a clearly labeled “experimental/legacy” module.

---

## 8. Validation & Manual QA Checklist

**Status:** TODO  
**Priority:** 🟡 Medium  

- [ ] After unifying progress storage:
  - [ ] Create a student, generate a 2‑unit curriculum, complete several sections.
  - [ ] Verify:
    - Student sidebar shows correct XP, level, streak, badges.
    - Parent dashboard shows matching curricula/sections/X P/streak.
    - Analytics dashboard lists the student with the same totals.
- [ ] After fixing SRS:
  - [ ] Complete a unit and confirm that flashcards exist in DB and appear in Review Queue.
  - [ ] Rate several cards and confirm due counts and next review dates update correctly.
- [ ] After grading changes:
  - [ ] Simulate an OpenAI/API failure (e.g., invalid key) and ensure:
    - Grading result is clearly “not graded”.
    - No XP or mastery is awarded.
    - A clear, user‑friendly error message is shown.
- [ ] Run the recommended tests from `task_completion_checklist` memory (where available) and note any environment‑specific failures.

  - Verify Parent dashboard and Analytics tab show the same underlying data.

### 1.3 AI provider config mismatch (config.yaml vs AIProviderService)
- **Status:** DONE (v1.5.4)  
- **Priority:** Medium  
- **Files:** `services/provider_service.py`, `config.yaml`  
- **Problem:**  
  - `AIProviderService` expects overrides under `config["providers"]` and uses `config["defaults"]["provider"]` as the default provider.  
- **Current config:**  
  - `config.yaml` defines an `ai_providers:` block with its own structure (`default`, `providers: { openai, kimi, ollama, ... }`).  
  - That block is **not read** by `AIProviderService`, so changes there do not affect runtime behavior.  
- **Planned fix:**  
  - Decide on a single source of truth: either adapt `AIProviderService` to read the `ai_providers` structure, or move that configuration into `config["providers"]` / `config["defaults"]["provider"]`.  
  - Remove or clearly mark any unused config keys to avoid confusion.

### 1.4 Missing `requests` dependency
- **Status:** DONE (v1.5.4)  
- **Priority:** High (for clean deploys)  
- **Files:** `requirements.txt`, `src/image_generator.py`, `main.py`  
- **Problem:**  
  - `ImageGenerator.create_image` uses `requests.get(...)` to download image URLs from the OpenAI image API.  
  - `main.py` also imports `requests`.  
  - `requirements.txt` only includes `httpx`, not `requests`, so fresh environments can fail with `ModuleNotFoundError: No module named 'requests'`.
- **Planned fix:**  
  - Add `requests` to `requirements.txt`.  
  - Optionally standardize on one HTTP client (either `requests` or `httpx`) long-term.

### 1.5 Model detection vs provider selection
- **Status:** DONE (v1.5.3)
- **Priority:** Medium
- **Files:** `src/model_detector.py`, `main.py`, `services/provider_service.py`
- **Problem:**
  - `get_available_models()` always talks to the OpenAI API (using `OPENAI_API_KEY`) and populates the "Advanced AI Model Settings" sidebar.
  - When another provider (e.g. Kimi/Ollama) is active, the sidebar can still list OpenAI models that do not exist on that provider.
  - UI allows selecting a model string that the active provider cannot handle, leading to potential API errors at generation time.
- **Resolution (v1.5.3):**
  - Added per-provider model lists to `AIProviderService.PROVIDERS` (`text_models`, `image_models`).
  - Added helper methods: `get_text_models()`, `get_image_models()`, `supports_images()`, `get_cost_tier()`.
  - Updated "Advanced AI Model Settings" sidebar to show models from the **selected provider**, not always OpenAI.
  - Added cost tier display (FREE / Low Cost / Paid) per provider.
  - Image section now clearly states OpenAI is required for image generation.

### 1.6 Parent "Curricula Overview" metadata
- **Status:** DONE (v1.5.4)  
- **Priority:** Low  
- **Files:** `main.py` (Parent tab 3)  
- **Problem:**  
  - Parent “Curricula” tab reads saved curriculum JSON and uses `data.get('title')` and `data.get('subject')`.  
  - Generated curricula actually store metadata under `data["meta"]["subject"]`, `["meta"]["grade"]`, etc.  
  - Parent view therefore often shows `Unknown`/filename instead of real subject/grade.
- **Planned fix:**  
  - Update Parent Curricula tab to read from `curriculum["meta"]` fields when present.  
  - Keep a fallback to top-level keys for older files if needed.

---

## 2. Claude Code Review – Validated Items

Below are Claude’s findings, re-checked against the current repo. Items are kept if they are valid and actionable in this codebase.

### 2.1 StateManager threading lock (anti-pattern vs Streamlit model)
- **Status:** DONE (v1.5.4)  
- **Priority:** Medium  
- **File:** `src/state_manager.py`  
- **Observation:**  
  - `StateManager` uses a class-level `threading.Lock()` to guard `st.session_state` updates.  
  - Streamlit runs each session in its own process or thread; per-session isolation is already guaranteed, and updating `st.session_state` from background threads is generally discouraged.  
- **Risk:**  
  - The lock is global across sessions but Python’s GIL + Streamlit’s execution model means hard deadlocks are unlikely.  
  - The bigger concern is conceptual: background threads touching `st.session_state` at all can cause subtle issues.  
- **Planned action:**  
  - Document that `StateManager` is only to be used from the main Streamlit thread.  
  - Consider removing the lock entirely or replacing threaded patterns that touch `st.session_state` with queue/event patterns that update state in the main thread.  
  - This is a design clean-up rather than a known crash bug.

### 2.2 Widget key collisions via `hash(...)` in UI components
- **Status:** DONE (v1.5.4)  
- **Priority:** High (potential for flaky behavior)  
- **File:** `src/ui_components.py`  
- **Confirmed code:**  
  - `ModernUI.card` uses `card_id = key or f"card_{hash(title + content)}"`.  
  - `ModernUI.stats_card` uses `card_id = key or f"stats_{hash(value + label)}"`.  
  - `ModernUI.quick_action_button` uses `button_id = action_key or f"action_{hash(title)}"`.  
- **Issue:**  
  - Python’s built-in `hash()` is not stable across processes and can collide; Streamlit expects widget keys to be globally unique and stable across reruns.  
  - While collisions are unlikely, they are very hard to debug when they happen.  
- **Planned fix:**  
  - Replace `hash(...)` in IDs with either:  
    - Deterministic hashes via `hashlib.md5(...).hexdigest()[:12]`, **or**  
    - Explicit keys passed in from call sites, with a simple fallback like `uuid.uuid4().hex[:8]` where true uniqueness is needed.  
  - Audit all custom components for similar `hash(...)` usage.

### 2.3 atexit cleanup for temp files
- **Status:** DONE (v1.5.4)  
- **Priority:** Medium  
- **File:** `main.py` (`cleanup_on_exit`, `atexit.register`)  
- **Observation:**  
  - App registers `cleanup_on_exit` with `atexit.register(cleanup_on_exit)`.  
  - In Streamlit server environments (especially hosted), process teardown timing is not under app control; `atexit` may not always run, or may run long after a session is gone.  
- **Planned fix:**  
  - Treat `atexit` cleanup as best-effort only.  
  - Add per-session cleanup hooks (e.g., tracking temp files in `SessionManager` and pruning when a new curriculum replaces an old one or when a user logs out).  
  - Optionally, add a periodic “temp file GC” on startup that clears old temp files from known temp directories.

### 2.4 Broad `except Exception` patterns with minimal logging
- **Status:** DONE (v1.5.4)  
- **Priority:** Medium  
- **Files:** `main.py`, several `services/*.py` modules  
- **Observation:**  
  - Many `try/except Exception as e:` blocks only call `st.error(...)` or `print(...)`, sometimes without full tracebacks.  
  - Given the complexity of external calls (OpenAI, file I/O, DB), richer logging would significantly improve debuggability.  
- **Planned fix:**  
  - Standardize on `verbose_logger` or Python `logging` for error logging.  
  - At key boundaries (curriculum generation, export, batch processing, student mode), include `traceback.format_exc()` in logs while keeping user-facing messages friendly.  
  - Narrow some `except Exception` blocks to specific exceptions where feasible (e.g. `openai.APIError`, `sqlite3.Error`).

### 2.5 Progress bar / status UI updates
- **Status:** PLANNED  
- **Priority:** Low–Medium  
- **File:** `main.py` (Generate tab, batch tab)  
- **Observation:**  
  - The code uses `progress_container = st.empty()` plus repeated `with progress_container.container():` updates. This works but can cause small flicker/re-renders.  
  - Claude’s suggestion is to maintain a consistent `st.empty()` placeholder for progress + a separate placeholder for status text.  
- **Planned fix:**  
  - When refactoring the generation UI for other reasons, also simplify progress rendering to a small number of stable placeholders.  
  - This is purely UX polish; not a functional bug.

### 2.6 Duplicate/fragmented state initialization
- **Status:** DONE (v1.5.4)  
- **Priority:** Medium  
- **Files:** `main.py`, `src/state_manager.py`  
- **Observation:**  
  - There is a mix of direct `if "key" not in st.session_state` checks in `main.py` and defaults inside `StateManager.initialize_state()`.  
  - This makes it harder to reason about the complete initial state of a session.  
- **Planned fix:**  
  - Consolidate initial state into a single function (probably `StateManager.initialize_state`) that sets all required keys.  
  - In `main.py`, call this once near the top and remove duplicated per-key initialization where possible.

### 2.7 Input sanitization coverage
- **Status:** PLANNED  
- **Priority:** Medium  
- **Files:** `services/session_service.py` (`InputValidator`), `main.py`  
- **Observation:**  
  - `InputValidator` currently sanitizes the custom guidelines prompt and validates subjects/grades.  
  - Other inputs (style, language, some template parameters) come from controlled lists but could still be normalized and/or validated centrally.  
- **Planned fix:**  
  - Ensure **all** free-text user inputs that flow into prompts or file paths go through `InputValidator`.  
  - Keep this lightweight (no need to over-sanitize fields that are from fixed selectboxes).

### 2.8 Cost estimation duplication
- **Status:** TODO  
- **Priority:** Low–Medium  
- **Files:** `main.py`, `services/curriculum_service.py`  
- **Observation:**  
  - There are two cost-estimation flows:  
    - `CurriculumService.estimate_costs` (primary)  
    - A fallback calculation block in `main.py` when the service isn’t available.  
  - These do similar things but are implemented separately, which can drift over time.  
- **Planned fix:**  
  - Wrap all cost estimation behind a single helper (`get_cost_estimate(params, curriculum_service)`), with a small, well-documented fallback.  
  - Keep the numeric assumptions for the fallback in one place.

### 2.9 Hard-coded UI strings & magic numbers
- **Status:** PLANNED  
- **Priority:** Low  
- **Files:** Many (`main.py`, `src/ui_components.py`, services)  
- **Observation:**  
  - UI strings and “magic numbers” (like certain token estimates, XP thresholds) are inlined throughout.  
- **Planned fix:**  
  - Over time, introduce a small `constants.py` / `strings.py` module for frequently reused labels, messages, and numeric tuning parameters.  
  - Treat this as an ongoing cleanup, not a single big change.

### 2.10 Loading states and feedback for long-running actions
- **Status:** PARTIALLY DONE / PLANNED  
- **Priority:** Medium  
- **Files:** `main.py`, `utils/regeneration_fix.py`  
- **Observation:**  
  - The main generation flow already uses spinners and `StatusLogger`.  
  - Some per-unit regeneration actions (content, images, charts, quizzes) are wrapped by callbacks via `RegenerationHandler`, but visual feedback could be more immediate/consistent.  
- **Planned fix:**  
  - Ensure every user-visible long-running action has:  
    - A spinner or status line, and  
    - A success/warning toast when done.  
  - This is largely a UX improvement; the callback structure is already in place.

### 2.11 CSS fallback warning
- **Status:** DONE (v1.5.4)  
- **Priority:** Low  
- **File:** `src/ui_components.py` (`ModernUI.load_css`)  
- **Observation:**  
  - If `static/css/design_system.css` is missing, the code silently falls back to minimal inline CSS.  
- **Planned fix:**  
-  - Add a log line (via `logging` or `verbose_logger`) to signal that the design-system CSS file wasn’t found, to make mis-packaged deployments easier to diagnose.

---

## 3. Claude Issues Considered but *Not* Adopted as Direct Tasks

These were in Claude’s report but are either already handled, too generic, or not clearly beneficial enough to track as explicit TODOs.

### 3.1 “Session state mutation without callbacks” as a blanket issue
- In the current code, state updates are mostly tied directly to button presses and controlled paths; there is no specific, reproducible bug around stale headers like Claude’s generic example.  
- We will still **prefer callbacks** for new work, but we’re not treating this as a concrete bug item.

### 3.2 “Deprecated Streamlit APIs”
- A search for `st.experimental` in the repo returns no matches; the app already uses `st.rerun()` and newer APIs.  
- We’ll keep an eye on Streamlit release notes, but there is no actionable deprecation problem today.

---

## 4. Next Steps / Suggested Implementation Order

**Completed in v1.5.4:**
- ✅ 1.1: Parent Reports/Certificates child identification
- ✅ 1.2: Migrate AnalyticsService to SQLite
- ✅ 1.3: Provider config mismatch
- ✅ 1.4: Add `requests` to requirements.txt
- ✅ 1.5: Model validation (v1.5.3)
- ✅ 1.6: Parent Curricula metadata
- ✅ 2.1: Remove StateManager threading lock
- ✅ 2.2: Widget key collisions (`hash()` → `hashlib.md5`)
- ✅ 2.3: Per-session temp file cleanup (startup GC added)
- ✅ 2.4: Exception logging improvements
- ✅ 2.6: State initialization consolidation
- ✅ 2.11: CSS fallback warning

**Remaining (planned for future):**
- 2.5: Progress bar/status UI updates (UX polish)
- 2.7: Input sanitization coverage
- 2.8: Cost estimation duplication
- 2.9: Hard-coded UI strings & magic numbers
- 2.10: Loading states and feedback
