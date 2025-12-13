# Mobile UI Fix Plan (iPhone / small screens)

This doc captures (1) what was broken on iPhone, (2) what’s already been fixed, and (3) the remaining plan to make mobile feel as intentional as desktop.

## Status (already addressed)

- **Sidebar “phantom gutter”**: sidebar width is now only forced on tablet/desktop; on mobile we no longer set a fixed width (only `max-width`) so Streamlit can correctly collapse/overlay it.
- **Icon-name text leaks** (`keyboard_double_arrow_right`, `keyboard_arrow_down`): icon font CSS now targets both Material Icons + Material Symbols with the correct font families.
- **Landing hero typography**: hero title now uses a responsive class (`.hero-title` with `clamp()` sizing).
- **API “Matrix feed” readability**: increased contrast and font sizing so logs aren’t muddy on dark backgrounds.

---

## Goals (definition of “mobile works as well as desktop”)

1. **No horizontal clipping / no phantom gutter**: main content uses full viewport width when sidebar is collapsed.
2. **Navigation is clear on mobile**: users can switch modes without relying on the sidebar.
3. **Readable typography**: hero title, labels, and body text are legible and never overlap.
4. **Touch-friendly controls**: buttons/inputs are at least ~44px tall and full width where appropriate.
5. **No icon-name text leaks**: Material icons render as icons (not their textual glyph names).
6. **Consistent layout across pages**: `Home`, `Student`, `Create`, `Parent` all look intentional.

---

## Current likely root causes (what caused the iPhone screenshot)

### A) Sidebar width is forced even when collapsed
`static/css/design_system.css` previously forced a fixed sidebar width unconditionally:
- `.stApp [data-testid="stSidebar"] { width: 360px !important; min-width: 360px !important; }`
- Mobile media queries also used to force widths, which prevented Streamlit’s “collapsed” state from reducing width to `0`.

On mobile, Streamlit’s sidebar is supposed to behave like an overlay/drawer. If CSS forces width while collapsed, Streamlit will still reserve layout space → the blank gutter seen on iPhone.

### B) Global `span` typography rule overrides icon fonts in places
The stylesheet applies font-family to almost all spans:
- `.stApp span:not(.material-icons):not(.material-symbols-*) { font-family: ... }`

Some Streamlit toolbar icons may use different classes (e.g., `material-icons-round`, `material-icons-outlined`, etc.). If those classes aren’t excluded, the icon span renders as text (`keyboard_double_arrow_right`).

### C) Mobile column stacking CSS is too broad
This rule is very aggressive:
- `.stApp [data-testid="stHorizontalBlock"] { flex-direction: column !important; }`

It may unintentionally affect Streamlit internal layout blocks beyond your content (toolbar rows, header rows, etc.), causing unpredictable layout shifts on iOS.

### D) Landing hero title uses inline font-size
In `main.py`, the title is rendered with an inline `font-size: 44px;` which does not respond to mobile media queries.

---

## Implementation plan

### Phase 0 — Reproduce + inspect (30–60 min)

1. **Reproduce locally**:
   - Run: `streamlit run main.py`
   - Use Chrome devtools device emulation (iPhone 14/15 Pro, iPhone SE) and Safari Responsive Design Mode if available.
2. **Inspect the sidebar DOM** to find a reliable “collapsed vs expanded” selector:
   - Check whether `section[data-testid="stSidebar"]` has `aria-expanded="false|true"` or another attribute/class.
3. **Inspect the toolbar icon DOM** where `keyboard_double_arrow_right` is leaking:
   - Identify actual classes used on the icon span (e.g., `material-icons-round`).
4. Capture “before” screenshots for:
   - Home, Create, Student, Parent.

Acceptance: we have a confirmed selector for “collapsed sidebar” + confirmed icon class names.

---

### Phase 1 — Fix the sidebar gutter (high priority)

Files: `static/css/design_system.css`

1. **Make sidebar width conditional on expanded state**:
   - If DOM supports it, implement:
     - `[data-testid="stSidebar"][aria-expanded="false"] { width: 0 !important; min-width: 0 !important; }`
     - `[data-testid="stSidebar"][aria-expanded="true"] { width: var(--sidebar-width) !important; }`
   - Apply the same logic to `stSidebarContent` and the immediate child wrapper.
2. **Define sidebar width via CSS variables** so mobile/tablet/desktop use a single source of truth:
   - `--sidebar-width-desktop: 360px;`
   - `--sidebar-width-tablet: 320px;`
   - `--sidebar-width-mobile: min(92vw, 420px);`
3. Ensure the “collapsed” rule wins on mobile (override ordering).

Acceptance:
- On iPhone emulation with sidebar collapsed: **no left gutter**.
- Opening the sidebar: sidebar behaves as a drawer overlay and does not permanently reduce main content width.

---

### Phase 2 — Fix icons rendering as text (high priority)

Files: `static/css/design_system.css`

1. **Remove or narrow the global span typography rule**:
   - Prefer targeting markdown/content containers instead of all spans:
     - `:is([data-testid="stMarkdownContainer"], [data-testid="stText"]) span { ... }`
   - Avoid touching spans used by Streamlit’s chrome/toolbar.
2. **Expand icon exclusions** to include the full Material icon class set Streamlit uses:
   - `.material-icons`, `.material-icons-round`, `.material-icons-outlined`, `.material-icons-two-tone`, `.material-icons-sharp`
   - Keep existing `material-symbols-*` exclusions.
3. Verify on iPhone: sidebar chevron icon is an icon again, not a word.

Acceptance:
- No occurrences of icon-name text (`keyboard_*`, `expand_*`, etc.) in the UI chrome.

---

### Phase 3 — Replace “global column stacking” with targeted mobile layout

Files: `static/css/design_system.css`, `main.py`, `src/shared_init.py`, `pages/*.py`

Goal: stop using broad `[data-testid="stHorizontalBlock"] { flex-direction: column }`.

Two viable approaches (pick one):

**Option A (preferred): mobile-aware layout in Python**
1. Add a reliable “mobile mode” flag:
   - Implement a small JS snippet via `st.components.v1.html` to detect viewport width and set `?mobile=1` query param when `<768px`.
   - In `src/shared_init.setup_page()`, read `st.query_params.get("mobile")` and store `is_mobile` in session state.
2. In each page:
   - If `is_mobile`:
     - Use single-column layout (no `st.columns(3)` on Home; stacked CTAs).
     - Move critical sidebar settings into main content (Create page) via expanders.
     - Use fewer columns for dashboards; prefer stacked cards.
   - If not mobile: keep current desktop layout.

**Option B: CSS-only layout**
1. Remove the global `stHorizontalBlock` rule.
2. Add page-specific layout wrappers via Streamlit structure (limited) and more precise selectors (fragile).

Acceptance:
- Home page cards stack cleanly on iPhone without affecting Streamlit toolbar layout.
- Create page settings are usable without fighting the sidebar drawer.

---

### Phase 4 — Landing page hero typography + safe-area polish

Files: `main.py`, `static/css/design_system.css`

1. Replace inline hero title sizing with a class:
   - `<div class="hero-title">🎓 InstaSchool</div>`
2. Add responsive rules:
   - desktop: ~44px
   - mobile: ~28–34px
3. Add iOS safe-area padding to the main container:
   - `padding-left/right: max(existing, env(safe-area-inset-left/right))`
   - same for top/bottom if needed.

Acceptance:
- Title is never clipped or oversized on iPhone Safari.
- Content doesn’t collide with notch/bottom browser UI.

---

### Phase 5 — Mobile UX improvements (quality pass)

Files: `static/css/design_system.css`, `pages/2_Create.py`, `src/student_mode/student_ui.py`, `pages/3_Parent.py`

1. Ensure all primary CTAs are full-width on mobile.
2. Reduce visual density:
   - Slightly smaller paddings/margins
   - Fewer heavy shadows on mobile
3. Make the generation status area “sticky” on mobile (optional):
   - Keep progress + cancel accessible without scrolling.

Acceptance:
- All key flows are comfortable on iPhone: Login, Start Generation, Cancel, Open Student, Complete section, Export.

---

## Validation checklist (after implementation)

1. Test pages: Home, Student, Create, Parent.
2. Test devices: iPhone SE (small), iPhone 15 Pro (notch), Android mid-size (optional).
3. Test sidebar states:
   - collapsed: no gutter
   - expanded: overlay drawer
4. Confirm icons render as icons (no `keyboard_*` words).
5. No new Streamlit warnings in logs.

---

## Suggested implementation order (fastest impact)

1. Phase 1 (sidebar gutter) + Phase 2 (icons)
2. Phase 4 (hero typography)
3. Phase 3 (replace global stacking; introduce mobile layout mode)
4. Phase 5 polish

---

# PDF Export (failure + fix)

## Symptom (reported)
- Clicking “Prepare PDF” / “Download PDF” failed, with errors like:
  - `PDF generation failed: 'bytearray' object has no attribute 'encode'`
  - Or `FPDFException: Not enough horizontal space to render a single character` (after the first error was removed).

## Root causes
1. **`fpdf2` output type**: `FPDF.output()` returns a `bytearray` in `fpdf2` (v2.x), not a `str`. Calling `.encode('latin-1')` on it crashes.
2. **`multi_cell` cursor behavior**: `fpdf2` defaults `multi_cell(..., new_x=XPos.RIGHT)`, so repeated `multi_cell()` calls can leave the cursor at the right margin and the next call fails with “not enough horizontal space…”.
3. **Unicode text in core fonts**: bullets (`•`), curly quotes, long URLs, and model-generated punctuation can break core-font PDFs unless sanitized/wrapped.

## Fix implemented (now)
- `services/export_service.py`
  - Return `bytes(pdf.output())` (no deprecated `dest=...`, no `.encode()`).
  - Normalize text to PDF-safe latin-1 (with common punctuation replacements).
  - Insert spaces into very long “runs” (URLs) so `multi_cell` can wrap.
  - Use `multi_cell(..., new_x="LMARGIN", new_y="NEXT")` for repeated blocks.
  - Replace bullet glyphs with `-` in PDF output.
- `services/certificate_service.py`
  - Same `bytes(pdf.output())` fix + latin-1 sanitization (and removed emoji glyphs that core fonts can’t render reliably).

## Follow-ups (optional hardening)
1. Add an embedded TTF font to support full Unicode (names, emoji, non-Latin languages).
2. Standardize other PDF generators (e.g., `services/report_service.py`) to use Helvetica + the same sanitization helper.
