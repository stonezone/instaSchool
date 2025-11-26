# InstaSchool TODO / Architecture & Bug Fixes

This file tracks open technical tasks for InstaSchool. It combines:
- Internal review items (GPT-5.1 review while hosting on Streamlit)
- Validated items from the Claude code review report

Statuses are for tracking only (no code has been changed yet).

Status legend: `TODO` = not started, `PLANNED` = design agreed, `DONE` = implemented.

---

## 1. Internal Review (GPT-5.1)

### 1.1 Parent mode – Reports & Certificates use wrong identifiers
- **Status:** TODO  
- **Priority:** High  
- **Files:** `main.py`, `services/report_service.py`, `services/certificate_service.py`, `services/user_service.py`  
- **Problem:**  
  - `user_service.list_users()` returns dicts like `{"username": ..., "has_pin": ..., "total_xp": ...}`.  
  - In Parent mode, `children = user_service.list_users()` is passed directly into `st.selectbox` for reports/certificates.  
  - `ReportService.generate_child_report` expects a **user ID**, while `CertificateService` helpers expect actual progress stats or a structured user object.  
  - Currently the code passes the whole dict (or just the username string in some paths), so reports/certificates are not reliably tied to a specific child.
- **Planned fix:**  
  - Normalize Parent mode to use **user IDs** from `DatabaseService` for both reports and certificates.  
  - Ensure `selectbox` shows friendly labels but stores the ID.  
  - Update `generate_child_report` and certificate calls to use IDs and pull consistent stats from DB.

### 1.2 Analytics dashboard uses legacy JSON instead of DB
- **Status:** TODO  
- **Priority:** High  
- **Files:** `services/analytics_service.py`, `services/database_service.py`  
- **Problem:**  
  - `AnalyticsService` still reads student profiles from JSON files under `users/` and progress from `curricula/...progress_*.json`.  
  - The rest of the app (Student mode, FamilyService, UserService) has migrated to SQLite (`instaschool.db`).  
  - New users and progress written only to the DB will not appear in analytics, so the dashboard is incomplete/incorrect.
- **Planned fix:**  
  - Refactor `AnalyticsService` to use `DatabaseService` for users, progress, and curriculum metadata.  
  - Preserve compatibility with any legacy JSON progress only as a fallback/migration path.  
  - Verify Parent dashboard and Analytics tab show the same underlying data.

### 1.3 AI provider config mismatch (config.yaml vs AIProviderService)
- **Status:** TODO  
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
- **Status:** TODO  
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
- **Status:** TODO  
- **Priority:** Medium  
- **Files:** `src/model_detector.py`, `main.py`, `services/provider_service.py`  
- **Problem:**  
  - `get_available_models()` always talks to the OpenAI API (using `OPENAI_API_KEY`) and populates the “Advanced AI Model Settings” sidebar.  
  - When another provider (e.g. Kimi/Ollama) is active, the sidebar can still list OpenAI models that do not exist on that provider.  
  - UI allows selecting a model string that the active provider cannot handle, leading to potential API errors at generation time.
- **Planned fix:**  
  - Decide how to reconcile provider choice and model detection: either:  
    - Only show OpenAI models when OpenAI is the active provider, **or**  
    - Integrate provider-aware model lists (per provider) and validate selections before calling the client.  
  - Add a lightweight validation step before generation that checks “selected model is valid for current provider” and surfaces a clear error if not.

### 1.6 Parent “Curricula Overview” metadata
- **Status:** TODO  
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
- **Status:** PLANNED (design decision needed, not urgent)  
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
- **Status:** TODO  
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
- **Status:** TODO  
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
- **Status:** TODO  
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
- **Status:** TODO  
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
- **Status:** TODO  
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

1. Fix Parent Reports/Certificates child identification (1.1).  
2. Migrate AnalyticsService to SQLite (1.2).  
3. Address `hash()`-based widget keys and add `requests` to requirements (1.4, 2.2).  
4. Clean up provider/model configuration and model validation (1.3, 1.5).  
5. Gradually tackle logging, state init consolidation, and UX polish items (2.4, 2.6, 2.10).

