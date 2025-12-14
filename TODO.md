# InstaSchool Audit TODO (2025-12-12)

This TODO is based on a repo review + Context7 docs checks (Streamlit multithreading + OpenAI Python SDK).

Note: `.gitignore` ignores most `*.md` files, but `README.md` and this `TODO.md` are intentionally kept for GitHub installs.

## Executive Summary (highest-impact findings)

- ✅ Fixed: Streamlit API calls from background threads could trigger `streamlit.errors.NoSessionContext`.
- ✅ Fixed: Cross-session state leakage risk due to mutable objects in `StateManager.DEFAULTS`.
- ✅ Fixed: Progress tracking corruption (`completed_sections` duplicates).
- ✅ Fixed: Cached config object mutation (shallow copies causing cross-rerun bleed).
- ✅ Fixed: Temp file cleanup was ineffective (cleanup ran on a brand-new `SessionManager` instance).
- ✅ Fixed: `CurriculumService.validate_generation_params()` provider service signature mismatch.
- ✅ Fixed: Cost estimator correctness issues (token totals + legacy model keys).
- ✅ Fixed: Curriculum schema mismatches (quiz/resources) could crash Student mode and break flashcards.

Note: A full automated test suite was intentionally NOT added (per request).

Priority legend:
- **P0** = correctness/security/reliability bug (fix first)
- **P1** = important maintainability + correctness
- **P2** = cleanup, DX, performance, UX improvements

---

## Findings → Fix Plan

### P0 — Reliability / Correctness

#### [x] P0.1 Eliminate Streamlit calls from background threads (NoSessionContext risk)

**Why this matters**
- Context7 Streamlit docs: Streamlit commands (including `st.session_state`) expect a script thread `ScriptRunContext`. Calls from non-script threads can raise `streamlit.errors.NoSessionContext`.

**Evidence in code**
- Parallel worker threads: `src/agent_framework.py` uses `ThreadPoolExecutor` inside `_process_topic()`.
- Streamlit usage inside non-UI code:
  - `src/core/types.py:179-219` imports `streamlit` inside exception handlers.
  - `src/image_generator.py:313-323` imports `streamlit` on image failures.
  - `src/agent_framework.py` → `ChartAgent.create_chart()` calls `st.warning(...)` (can run in worker thread when invoked from `run_chart()`).

**Plan**
1. Remove all `import streamlit as st` usage from non-UI modules (`src/core/types.py`, `src/image_generator.py`, chart generation helpers).
2. Replace Streamlit UI notifications with:
   - raising a typed exception (e.g., `UserFacingError`) OR
   - returning a structured result `{ok: bool, user_message: str, debug: ...}`.
3. In UI-layer only (`pages/*.py`, `src/student_mode/student_ui.py`), translate these errors into `st.warning/st.error`.
4. Add a guardrail helper (UI-only) like `notify_user(level, message)` to centralize messaging.

**Done when**
- Generating a curriculum with `media_richness >= 3` produces no `NoSessionContext` errors and completes or fails gracefully with user-visible messages.

---

#### [x] P0.2 Fix `StateManager.DEFAULTS` mutable object sharing across sessions

**Evidence in code**
- `src/state_manager.py:25-74` stores mutable defaults directly (`{}`, `set()`).

**Impact**
- Cross-session data leakage and “haunted state” bugs (multiple user sessions in same server process share object references).

**Plan**
1. Replace mutable default values with factories OR deep-copy on initialization:
   - e.g., store `DEFAULT_FACTORIES = {"quiz_answers": dict, "last_tmp_files": set, ...}`
   - or `st.session_state[key] = copy.deepcopy(value)` for known-safe types.
2. Add a small regression test (even a minimal `pytest` file) that asserts two initializations don’t share object identity for dict/set defaults.

**Done when**
- State initialization creates distinct dict/set objects per session and per rerun.

---

#### [x] P0.3 Fix progress corruption: duplicates in `completed_sections`

**Evidence in code**
- `src/student_mode/progress_manager.py:178-183` appends “previous section” during `advance_section()`.
- `src/student_mode/student_ui.py:391-400` also calls `complete_section(section_idx)` before `advance_section()`.
- Result: every “Complete & Continue” duplicates the section index in `completed_sections`.

**Plan**
1. Decide the single source of truth for completion writes:
   - Option A (recommended): `complete_section()` mutates `completed_sections`; `advance_section()` ONLY increments `current_section`.
2. Add a migration/dedup pass during `_load_progress()`:
   - `completed_sections = sorted(set(completed_sections))` (preserve ints only; filter non-ints defensively).
3. Add tests for the Student UI sequence:
   - call `complete_section(0)` then `advance_section()` → `completed_sections == [0]`, not `[0,0]`.
4. Validate DB records:
   - ensure `DatabaseService.save_progress()` stores deduped `completed_sections`.

**Done when**
- `completed_sections` remains unique, and `total_sections_completed` remains correct.

---

#### [x] P0.4 Stop mutating cached config objects (cross-rerun bleed)

**Evidence in code**
- `src/shared_init.py:26-34` caches `load_config()` (returns a mutable dict).
- `pages/2_Create.py:189-197` uses `run_config = config.copy()` (shallow) then mutates `run_config["defaults"]`, which mutates `config["defaults"]` too.
- `services/curriculum_service.py` previously used `self.config.copy()` then mutated `current_config["defaults"]` (mutating the cached service config).

**Impact**
- Settings can silently persist across reruns/users for up to TTL=300s.

**Plan**
1. Make `load_config()` return a deep copy (or an immutable mapping) so callers can’t mutate the cached object.
2. Update pages to treat config as immutable:
   - `run_config = copy.deepcopy(config)` before modifications.
3. Add a small test: mutate returned config, call `load_config()` again, ensure defaults unchanged.

**Done when**
- Toggling settings in Create mode doesn’t change defaults for other sessions/reruns.

---

#### [x] P0.5 Make “Cancel Generation” actually work (or remove it)

**Evidence in code**
- Previously, `pages/2_Create.py` showed a cancel button while generation ran synchronously in the same script run (cancel could not take effect).

**Plan (choose one)**
- Option A (simplest): Remove cancel UI; rely on Streamlit reruns to interrupt work (document limitations).
- Option B (recommended): Run generation in a background worker:
  1. Start generation in a thread/future stored in session state.
  2. Poll status with a fragment/timer and update UI (progress + allow cancel).
  3. Use a `threading.Event` cancellation token and check it between topic units (already supported by `OrchestratorAgent.create_curriculum(..., cancellation_event=...)`).

**Done when**
- User can cancel between units and the app returns partial curriculum with `meta.cancelled = True`.

---

#### [x] P0.6 Align curriculum schema (quiz/resources/charts) across generator + Student mode + exports

**Evidence in code**
- Generator produced `unit["quiz"]` as a list, but Student UI expects a dict like `{"questions": [...]}` and uses `q["correct"]` for scoring and flashcards.
- Generator produced `unit["resources"]` as a Markdown string, but Student summary UI treated it like a dict and called `.items()` (crash when non-empty).
- Export code expected `curriculum["metadata"]` and treated `unit["chart"]` / `unit["selected_image_b64"]` as already-HTML-safe strings.

**Fix implemented**
1. `QuizAgent.generate_quiz()` now returns `{"questions": [...]}` (and normalizes legacy `quiz` outputs) and `config.yaml` quiz prompt was updated to match.
2. Student UI now coerces legacy quiz formats (`list` or `{"quiz":[...]}`) into the expected `{"questions":[...]}` shape.
3. Student summary now renders `resources` safely for `str | list | dict`.
4. `services/export_service.py` now supports both `meta` and `metadata`, prefixes raw base64 as data URLs, and renders chart dicts via `b64` or Plotly config.
5. `ChartAgent.create_chart()` now attaches a `b64` fallback image even when `plotly_config` is present.

**Done when**
- Student mode quiz/summary render without exceptions for new and legacy curricula, and flashcard creation works.

---

### P1 — Correctness / Maintainability

#### [x] P1.1 Fix temp file cleanup (current atexit cleanup is ineffective)

**Evidence in code**
- Previously, `main.py` registered cleanup on a new `SessionManager()` instance, which had an empty `temp_files` set.

**Plan**
1. Ensure the cleanup function references the same `SessionManager` instance that tracks temp files:
   - store session manager in `StateManager` or `st.cache_resource` and register cleanup against that instance, OR
   - maintain a module-level global registry of temp files.
2. Add “startup cleanup” that deletes any orphaned temp files from previous runs.

**Done when**
- Loading/saving curricula with images/charts does not accumulate temp files indefinitely.

---

#### [x] P1.2 Fix `CurriculumService.validate_generation_params()` provider service call

**Evidence in code**
- `services/curriculum_service.py:58-85` calls `get_provider_service()` with no args, but `services/provider_service.get_provider_service(config)` requires a `config`.

**Plan**
1. Remove the ambiguous duplicate API:
   - Prefer `src/shared_init.get_provider_service()` (cached) OR
   - Change `services/provider_service.get_provider_service` to accept `config: Optional[dict] = None` and load config internally.
2. Update `CurriculumService.validate_generation_params()` to use the chosen provider service method.
3. Add a unit test that calls `validate_generation_params()` with a valid config and confirms it doesn’t crash.

**Done when**
- `CurriculumService` can be used without a runtime exception.

---

#### [x] P1.3 Fix cost estimator correctness issues

**Evidence in code**
- `src/cost_estimator.py`:
  - Total token counting loop uses mismatched keys (`content` vs `content_per_unit`, etc.).
  - `calculate_savings()` annotated as returning `float` but returns a dict.
  - References to `MODEL_COSTS["dall-e-3"]` / `["dall-e-2"]` exist but those keys are not defined (potential KeyError).

**Plan**
1. Normalize token estimate keys (prefer `src/constants.py:COST_ESTIMATE_TOKENS` as the canonical source).
2. Fix `calculate_savings()` return type annotation + callers.
3. Remove or fully support DALL·E-related branches (consistent keys + costs).
4. Add tests for a few model combos ensuring:
   - no KeyError,
   - totals are consistent and non-negative,
   - output schema is stable.

**Done when**
- Create page cost estimate is plausible and stable for all selectable models.

---

#### [x] P1.4 Avoid class-level global mutation in `AIProviderService`

**Evidence in code**
- `services/provider_service.py` mutates `AIProviderService.PROVIDERS` inside `__init__` when applying config overrides.

**Impact**
- Global state leaks across sessions and tests; config changes can persist unexpectedly.

**Plan**
1. Deep copy provider definitions into `self.providers` per instance.
2. Update all methods to use `self.providers`.
3. Add a test ensuring one instance’s override doesn’t affect another instance.

**Done when**
- Provider config is instance-scoped and deterministic.

---

### P2 — Improvements / Cleanup / DX

#### [x] P2.1 Consolidate exporter implementations and schema

**Evidence in code**
- Duplicate exporter functionality:
  - `services/export_service.py` historically expected `curriculum["metadata"]` (stale) and treated images/charts as already-HTML-safe strings.
  - `services/curriculum_service.py` contains a different `CurriculumExporter` (markdown only, uses `meta`).
  - Current runtime schema uses `curriculum["meta"]`, `unit["selected_image_b64"]` raw base64, and `unit["chart"]` as dict (plotly or matplotlib).

**Status**
- `services/export_service.py` is the canonical exporter and now supports the current curriculum schema (`meta`, `selected_image_b64`, chart dicts, flexible `resources`).
- `services/curriculum_service.py:CurriculumExporter.generate_markdown()` is now a thin compatibility wrapper that delegates to `services/export_service.get_exporter().generate_markdown(...)`.
- Create → Library now exposes export actions (JSON/Markdown/HTML/PDF) via the canonical exporter.

**Follow-ups (optional)**
1. Delete the legacy exporter implementation entirely (keep only the compatibility shim), if desired.
2. Add a small golden-file export fixture test (deferred per “no test suite” request).

---

#### [x] P2.2 Align dependency management + docs

**Evidence**
- README previously referenced a non-existent `release/` directory and outdated PDF tooling (`wkhtmltopdf`), and lacked a simple repo sanity check.

**Status**
- README now reflects current structure + export flow (PDF via `fpdf2`), and includes `./scripts/check.sh` for a fast sanity check.
- `.env_example` exists for GitHub installs, and CI runs `python -m compileall -q .` on Python 3.11.

**Follow-ups (optional)**
1. Pin `requirements.txt` versions or adopt a lockfile workflow (uv/poetry/pip-tools) for reproducible installs.

---

#### [x] P2.3 Add basic automated checks (tests + lint) ✅ COMPLETED

**Implementation (2025-12-14):**

Added pytest test suite with 51 regression tests covering:
- `test_state_manager.py` - State default isolation (P0.2)
- `test_progress_manager.py` - Progress dedup + advance logic (P0.3)
- `test_cost_estimator.py` - Cost estimator outputs (P1.3)
- `test_provider_service.py` - Provider service config isolation (P1.4)

Added ruff linter with minimal config in `pyproject.toml`:
- Checks for pycodestyle errors (E), Pyflakes (F), isort (I), pyupgrade (UP)
- Permissive ignores for existing codebase patterns

Updated CI workflow (`.github/workflows/ci.yml`):
- **sanity**: `python -m compileall -q .`
- **lint**: `ruff check . --output-format=github`
- **test**: `python -m pytest tests/ -v --tb=short`

**Files Added/Modified:**
- `tests/__init__.py`
- `tests/conftest.py`
- `tests/test_state_manager.py`
- `tests/test_progress_manager.py`
- `tests/test_cost_estimator.py`
- `tests/test_provider_service.py`
- `pyproject.toml` (pytest + ruff config)
- `requirements.txt` (added pytest, ruff)
- `.github/workflows/ci.yml` (lint + test jobs)

---

## Suggested Implementation Order

1. P0.1 (thread safety) → prevents crashes
2. P0.2 + P0.4 (state/config isolation) → prevents cross-session bleed
3. P0.3 (progress dedup) → prevents data corruption
4. P1.1 / P1.2 / P1.3 / P1.4
5. P2 cleanups + tests/CI

---

## Post-fix Validation Checklist

- Generate curricula at media richness 0 / 2 / 5 without `NoSessionContext` errors.
- Verify `completed_sections` remains unique after multiple "Complete & Continue" clicks.
- Verify Create mode settings do not persist unexpectedly across reruns.
- Verify temp files don't accumulate over multiple loads/exports.
- Verify cost estimator returns stable dict schema and sensible totals.

---

## Export Review Findings (2025-12-13)

### Files Reviewed

| File | Size |
|------|------|
| `exports/Language Arts_Mathematics_History_1_1765692049.html` | 11.5 MB |
| `exports/Language Arts_Mathematics_History_1_1765692049.pdf` | 11.0 MB |

### Critical Finding: Massively Oversized Export Files

The exports are **10-20x larger than necessary** due to unoptimized embedded images.

| Metric | Current | Target |
|--------|---------|--------|
| Embedded images | 8 | 8 |
| Average image size | ~2.5 MB (base64) | ~50-100 KB |
| Total export size | ~11 MB | ~1 MB |
| Image resolution | 1024x1024 | 600px max width |

**Root Cause Chain:**
1. `src/image_generator.py:40` - Images generated at 1024x1024 resolution
2. `src/image_generator.py:219-227` - Downloaded and base64 encoded without compression
3. `services/export_service.py:415-418` (HTML) - Raw base64 embedded directly
4. `services/export_service.py:202-207` (PDF) - Same issue

---

### P0-E: Image Optimization for Exports (CRITICAL) ✅ COMPLETED

**Goal:** Reduce export file sizes by 90%+ (11MB → <1.5MB)

**Implementation (2025-12-15):**

Added `_optimize_image()` helper to `services/export_service.py:132-186`:
- Decodes base64 → PIL Image
- Resizes to max 600px width (maintains aspect ratio)
- Converts to JPEG with 85% quality
- Returns optimized base64

Applied in:
- `generate_html()` - lines 477, 486, 494
- `generate_pdf()` - lines 265, 279

**Results:**
- HTML: 11MB → 604KB (**95% reduction**)
- PDF: 11MB → 465KB (**96% reduction**)

**Files Modified:**
- `services/export_service.py`

---

### P1-E: Export Quality Options ✅ COMPLETED

**Goal:** Let users choose export quality based on use case

| Quality | Max Width | JPEG Quality | Use Case |
|---------|-----------|--------------|----------|
| High | 800px | 90% | Printing, archival |
| Medium | 600px | 85% | General sharing (default) |
| Low | 400px | 75% | Email, mobile viewing |

**Implementation (2025-12-15):**

Added `QUALITY_PRESETS` dict to `CurriculumExporter` (line 129-134).
Updated `generate_html()` and `generate_pdf()` to accept `quality` parameter.
Added quality dropdown to Export UI in `pages/2_Create.py` (lines 628-635).

**Results:**
| Quality | HTML Size | PDF Size |
|---------|-----------|----------|
| High | 1.2 MB | 900 KB |
| Medium | 604 KB | 465 KB |
| Low | 254 KB | 203 KB |

**Files Modified:**
- `services/export_service.py`
- `pages/2_Create.py`

---

### P2-E: Filename Sanitization ✅ COMPLETED

**Before:** `Language Arts_Mathematics_History_1_1765692049.html`
**After:** `Language-Arts_Mathematics_History_1_1765692049.html`

**Implementation (2025-12-15):**
Added `sanitize_filename()` helper in `pages/2_Create.py` (lines 20-28).
Applied to all download buttons (Markdown, HTML, PDF).

---

### P2-E: Print-Friendly HTML ✅ COMPLETED

**Implementation (2025-12-15):**
Added `@media print` CSS block in `services/export_service.py` (lines 474-504).

Features:
- Page break handling (avoid mid-unit breaks)
- Print-friendly black text colors
- Preserved quiz backgrounds
- Images won't break across pages

---

### P3-E: Export Metadata ✅ COMPLETED

**Implementation (2025-12-15):**
Added metadata footer to both HTML and PDF exports.

Includes:
- Generator version (InstaSchool v1.0.0)
- Export timestamp
- AI model used

**Files Modified:**
- `services/export_service.py` (VERSION constant + footer sections)

---

### Export Implementation Order

1. **P0-E** - Image optimization (blocking - exports currently unusable)
2. **P1-E** - Quality options (quick win after P0-E)
3. **P2-E** - Filename + Print CSS (polish)
4. **P3-E** - Metadata (nice to have)

---

### Export Testing Checklist

- [x] HTML export < 2MB for typical curriculum (604KB achieved)
- [x] PDF export < 2MB for typical curriculum (465KB achieved)
- [x] Images render correctly at reduced size
- [x] PDF images properly embedded (not corrupted)
- [x] HTML prints cleanly (print CSS added)
- [x] Filenames have no spaces (sanitize_filename helper)
- [x] Quality options produce expected file sizes (High/Medium/Low tested)
