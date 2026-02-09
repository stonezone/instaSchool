# InstaSchool UI Patterns & Design Guidelines

Modern, native Streamlit UI patterns for InstaSchool (2025+)

## Core Principles

1. **Native First** - Use Streamlit's built-in components before custom HTML/CSS
2. **Theme Aware** - All styling via `.streamlit/config.toml` with light/dark modes
3. **Material Icons** - Use `:material/icon_name:` format, avoid emojis (Python 3.13 bug)
4. **Sentence Casing** - "Family dashboard" not "Family Dashboard"
5. **Minimal CSS** - Keep `design_system.css` under 60 lines

## Theming Architecture

### Config Structure
All theming is handled in `.streamlit/config.toml`:

```toml
# Light mode colors
[theme.light]
primaryColor = "#6366f1"
backgroundColor = "#ffffff"
...

# Dark mode colors
[theme.dark]
primaryColor = "#818cf8"
backgroundColor = "#09090b"
...

# Shared settings (fonts, chart colors, etc.)
[theme]
font = "'Inter':https://fonts.googleapis.com/..."
chartCategoricalColors = ["#6366f1", "#22c55e", ...]
```

**CRITICAL**: `chartCategoricalColors` ONLY works in `[theme]` section, NOT in `[theme.light]` or `[theme.dark]`

### Theme Toggle
Users toggle via Settings menu (⚙️) → Theme. No custom toggle button needed.

## Essential UI Components

### Cards
Use `st.container(border=True)` for card-like sections:

```python
with st.container(border=True):
    st.markdown("**Card title**")
    st.caption("Card description here")
```

### Metrics/Stats
Use `st.metric(border=True)` for statistics:

```python
st.metric("Active learners", "1,234", border=True)
```

### Button Groups
Use `st.container(horizontal=True)` for horizontal layouts:

```python
with st.container(horizontal=True):
    if st.button("Save"):
        ...
    if st.button("Cancel"):
        ...
```

### Spacing
Use `st.space()` for vertical spacing:

```python
st.space(2)  # 2 lines of space
```

Avoid `st.markdown("---")` dividers unless semantically meaningful.

### Lightweight Info
Use `st.caption()` for subtle text instead of `st.info()`:

```python
st.caption("ℹ️ This is some helpful context")
```

### Navigation
Use `st.page_link()` for navigation with Material icons:

```python
st.page_link("pages/1_Student.py", label="Student", icon=":material/school:")
st.page_link("pages/2_Create.py", label="Create", icon=":material/auto_awesome:")
```

### Logo
Use `st.logo()` in `setup_page()` (appears on all pages):

```python
st.logo("static/logo_wide.svg", icon_image="static/logo.svg", size="large")
```

## Material Icons

### Icon Format
`:material/icon_name:`

### Common Icons
- `:material/home:` - Home
- `:material/school:` - Student
- `:material/auto_awesome:` - AI/Create
- `:material/family_restroom:` - Family
- `:material/library_books:` - Library
- `:material/person:` - User
- `:material/settings:` - Settings
- `:material/arrow_forward:` - Next/Forward
- `:material/psychology:` - AI/Brain

### Finding Icons
Browse at: https://fonts.google.com/icons

## Anti-Patterns ❌

### Never Use
1. **Massive inline CSS** with `unsafe_allow_html=True`
   ```python
   # ❌ BAD - Fights native rendering
   st.markdown("""<style>
       .stApp { background: #000 !important; }
       ... 700 more lines ...
   </style>""", unsafe_allow_html=True)
   ```

2. **Emojis in expanders** (Python 3.13 text corruption bug)
   ```python
   # ❌ BAD - Causes corrupted text
   st.expander("📚 Library")

   # ✅ GOOD - Use text only
   st.expander("Library")
   ```

3. **Custom theme toggle buttons** (native already exists)
   ```python
   # ❌ BAD - Unnecessary
   if st.button("🌙 Dark Mode"):
       # custom theme switching logic

   # ✅ GOOD - Use Settings menu
   # (No code needed - native Streamlit)
   ```

4. **Title Case everywhere**
   ```python
   # ❌ BAD - Too formal
   st.header("Family Dashboard")

   # ✅ GOOD - Sentence casing
   st.header("Family dashboard")
   ```

5. **Hiding Streamlit chrome** with CSS
   ```python
   # ❌ BAD - Breaks user expectations
   st.markdown("""<style>
       header { display: none !important; }
   </style>""", unsafe_allow_html=True)
   ```

## Code Examples

### Landing Page Hero
```python
st.logo("static/logo_wide.svg", icon_image="static/logo.svg", size="large")

# Minimal CSS only for gradient text (no native equivalent)
st.html("""<style>
.hero-gradient {
    background: linear-gradient(135deg, #6366f1 0%, #a855f7 50%, #ec4899 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
}
</style>""")

st.markdown('<h1 class="hero-gradient">InstaSchool</h1>', unsafe_allow_html=True)
st.markdown("Generate complete K-12 curricula with AI")

# Stats with native metrics
with st.container(horizontal=True):
    st.metric("Curricula created", "1,000+", border=True)
    st.metric("Active learners", "500", border=True)

# Feature cards
with st.container(border=True):
    st.markdown(":material/psychology: **AI curriculum generator**")
    st.caption("Generate complete curricula in minutes")

# Navigation
st.page_link("pages/1_Student.py", label="Start learning", icon=":material/arrow_forward:")
```

### Page Setup
```python
from src.shared_init import setup_page

setup_page(title="Student", icon=":material/school:", layout="wide")

# Logo and navigation automatically rendered in sidebar
```

### Empty States
```python
# ❌ BAD - Custom HTML
st.markdown("""<div class="empty-state">No items found</div>""", unsafe_allow_html=True)

# ✅ GOOD - Native container
with st.container(border=True):
    st.markdown(":material/library_books: **No curricula yet**")
    st.caption("Create your first curriculum to get started")
    if st.button("Create curriculum"):
        ...
```

## File Structure

- `.streamlit/config.toml` - ALL theming (light/dark modes, fonts, colors)
- `static/css/design_system.css` - Minimal CSS (<60 lines) for unavoidable custom styling
- `static/logo.svg` - Square icon (40x40)
- `static/logo_wide.svg` - Wide logo with text (180x40)
- `src/shared_init.py` - Shared page setup (logo, navigation, session state)

## Migration Notes

From previous custom CSS approach:
- Removed 1,350 lines of custom CSS/HTML
- Migrated to native `st.container()`, `st.metric()`, `st.page_link()`
- Consolidated 3 competing theme systems into config.toml
- Replaced emoji navigation with Material icons

## Testing

After UI changes:
1. Test locally: `streamlit run main.py`
2. Check both light and dark modes (Settings → Theme)
3. Verify on mobile viewport (responsive design)
4. Push to git
5. **Reboot Streamlit Cloud** to see changes

## Resources

- [Streamlit Theming Docs](https://docs.streamlit.io/develop/concepts/configuration/theming)
- [Material Icons](https://fonts.google.com/icons)
- [Streamlit Components](https://docs.streamlit.io/develop/api-reference)
