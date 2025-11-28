# InstaSchool Multi-Page Refactoring - Quick Summary

## Current State
```
main.py (3,660+ lines)
├── Imports & Setup (lines 0-149)
├── Utilities (lines 160-809)
├── Student Mode (lines 874-979)
├── Parent Mode (lines 984-1199)
└── Teacher/Create Mode (lines 1202-3650+)
    ├── Sidebar Config (lines 1203-1499)
    └── 6 Main Tabs (lines 1503-3650+)
```

## Target Structure
```
main.py (120 lines - entry point only)
├── Mode selector
├── State initialization
└── Router

pages/
├── 1_Student.py (150 lines)
│   └── Login + render_student_mode()
├── 2_Create.py (2,400 lines)
│   ├── Sidebar via shared_sidebar.py
│   └── 6 tabs for curriculum creation
└── 3_Parent.py (250 lines)
    └── 4 tabs for family dashboard

src/
├── shared_config.py (NEW - 150 lines)
│   └── App initialization & services
├── shared_sidebar.py (NEW - 300 lines)
│   └── Sidebar builder for Create mode
└── student_mode/ (EXISTING)
    └── Modular student learning interface
```

## Three Distinct User Modes

### 1. Student Mode (pages/1_Student.py)
**Current Users**: Students learning from curricula
**Current Code**: Lines 874-979 in main.py
**Status**: 80% done - student_ui.py already exists
**Work Needed**: Move login UI (875-961) + import render_student_mode()

**Key Functions**:
- Student login/profile management
- PIN authentication
- Profile switching
- Logout

**Dependencies**:
- UserService
- render_student_mode() from src/student_mode/student_ui.py

---

### 2. Create Mode (pages/2_Create.py)
**Current Users**: Teachers creating curricula
**Current Code**: Lines 1202-3650+ in main.py
**Status**: Largest refactor, but straightforward extraction

**Sidebar Sections** (moved to shared_sidebar.py):
1. Basic Settings (subject, grade, style, language)
2. AI Provider (OpenAI, Kimi K2, cross-provider)
3. AI Models (main orchestrator, worker, image models)
4. Content Settings (media richness, component toggles)
5. Preferences (theme, mobile layout)

**Main Content Tabs**:
1. Generate - Create new curriculum from settings
2. View & Edit - Modify existing curriculum
3. Export - Download as HTML/PDF/Markdown
4. Templates - Save/load curriculum templates
5. Batch - Process multiple curricula
6. Analytics - View student engagement metrics

**Dependencies**:
- All services (Curriculum, Batch, Template, Analytics)
- ImageGenerator
- Provider service for AI management
- Modern UI components

---

### 3. Parent Mode (pages/3_Parent.py)
**Current Users**: Parents monitoring children's learning
**Current Code**: Lines 984-1199 in main.py
**Status**: Clean extraction - well-contained code

**Tabs**:
1. Family Overview - Dashboard showing children's progress
2. Reports & Certificates - Generate PDF reports and certificates
3. Curricula - View available learning materials
4. Settings - Family preferences and add children

**Dependencies**:
- FamilyDashboard from src/ui_components
- family_service, report_service, certificate_service
- UserService
- ThemeManager

---

## Key Shared Code

### src/shared_config.py (NEW)
Centralizes app initialization for all pages:

```python
initialize_app()           # Load config, services, state
setup_page_config()       # Streamlit page config
get_initialized_services() # Return all services
```

### src/shared_sidebar.py (NEW)
Builds Create mode sidebar with modular functions:

```python
render_basic_settings_sidebar()
render_ai_provider_sidebar()
render_ai_model_sidebar()
render_content_settings_sidebar()
render_preferences_sidebar()
render_sidebar_complete()  # All-in-one
```

### main.py (Refactored)
Becomes a lightweight entry point:

```
1. Initialize app via shared_config
2. Show mode selector
3. Let Streamlit route to pages/
```

---

## Session State Management

### Shared Across All Pages
- `config` - App configuration
- `client` - API client
- `provider_service` - AI provider
- `current_user` - Logged-in student
- `current_mode` - Selected mode
- `theme`, `is_mobile` - Preferences

### Create Mode Only
- `curriculum` - Current curriculum
- `template_manager` - Templates
- `batch_manager` - Batch jobs
- `analytics_service` - Analytics
- Model/subject/grade selections

### Student Mode Only
- `login_needs_pin`, `login_username` - Auth state
- Student progress data

---

## Migration Path (5 Phases)

**Phase 1: Student Page** (30 mins)
- Move login code from main.py to pages/1_Student.py
- Import existing render_student_mode()

**Phase 2: Parent Page** (45 mins)
- Extract parent mode code to pages/3_Parent.py
- Keep all imports and logic as-is

**Phase 3: Create Page** (2 hours)
- Extract teacher mode to pages/2_Create.py
- Move sidebar to src/shared_sidebar.py

**Phase 4: Shared Modules** (1 hour)
- Create src/shared_config.py
- Create src/shared_sidebar.py
- Consolidate initialization

**Phase 5: Testing** (1 hour)
- Test mode switching
- Verify state persistence
- Check all functionality

**Total Time**: 4-5 hours

---

## Line Count Comparison

| Component | Lines |
|-----------|-------|
| main.py (current) | 3,660+ |
| pages/1_Student.py | 150 |
| pages/2_Create.py | 2,400 |
| pages/3_Parent.py | 250 |
| src/shared_config.py | 150 |
| src/shared_sidebar.py | 300 |
| **Total** | **3,250** |

Similar total but much better organized.

---

## Why This Refactoring Matters

### Problems with Current Structure
- 3,660+ line single file is hard to navigate
- Mixing three unrelated user modes in one file
- Sidebar configuration is embedded in mode code
- Hard to test individual pages
- Onboarding difficulty for new developers

### Benefits of Multi-Page Structure
- Clear separation of user roles
- Each page <= 2,400 lines (manageable)
- Sidebar logic extracted and reusable
- Easier to test individual pages
- Cleaner code organization
- Faster development for feature additions
- Students/Parents/Teachers each have dedicated interface

---

## Implementation Details

### What Stays in main.py
- Logging setup
- Mode selector
- State initialization
- Entry point logic

### What Moves to pages/
- Student login & learning interface
- Teacher sidebar & curriculum tools
- Parent dashboard & reports

### What Moves to src/
- Shared config initialization
- Sidebar builder functions
- Reusable UI utilities (already exists)

### What Stays in services/
- All business logic (no changes needed)
- Database access
- API interactions

---

## Detailed Function Mapping

### pages/1_Student.py Sources
```
main.py lines 874-979
└── Student mode selector + login UI
└── import render_student_mode from src/student_mode/student_ui.py
```

### pages/2_Create.py Sources
```
main.py lines 1203-1499
└── Sidebar configuration
main.py lines 1503-3650+
└── 6 main tabs for curriculum creation
```

### pages/3_Parent.py Sources
```
main.py lines 993-1198
└── 4 parent dashboard tabs
```

### src/shared_sidebar.py Sources
```
main.py lines 1203-1499
└── Extracted sidebar sections
```

### src/shared_config.py Sources
```
main.py lines 0-149 (imports & setup)
main.py lines 125-144 (cached service wrappers)
main.py lines 345-407 (initialization)
main.py lines 559-637 (config loading)
```

---

## Testing Checklist

- [ ] App loads without errors
- [ ] Mode selector visible in sidebar
- [ ] Can navigate to each page
- [ ] Student page: Login works
- [ ] Student page: Logout works
- [ ] Create page: All sidebar sections appear
- [ ] Create page: All 6 tabs appear
- [ ] Create page: Can generate curriculum
- [ ] Parent page: All 4 tabs appear
- [ ] Parent page: Can generate reports
- [ ] Session state persists between pages
- [ ] Settings saved when switching pages
- [ ] Mobile layout toggle works
- [ ] Theme toggle works
- [ ] No broken imports

---

## Reference: Code Locations

### Student Mode Code
- **Login UI**: main.py lines 875-961
- **Profile switching**: main.py lines 948-961
- **Learning interface**: src/student_mode/student_ui.py

### Parent Mode Code
- **Family Overview**: main.py lines 1001-1049
- **Reports & Certificates**: main.py lines 1051-1120
- **Curricula**: main.py lines 1122-1170
- **Settings**: main.py lines 1172-1198

### Create Mode - Sidebar Code
- **Basic Settings**: main.py lines 1207-1231
- **AI Provider**: main.py lines 1234-1341
- **AI Models**: main.py lines 1344-1432
- **Content Settings**: main.py lines 1457-1469
- **Tips & Preferences**: main.py lines 1474-1499

### Create Mode - Tab Code
- **Tab 1 (Generate)**: main.py lines 1505-1645
- **Tab 2 (View & Edit)**: main.py lines 1650+
- **Tab 3 (Export)**: main.py lines 2000+
- **Tab 4 (Templates)**: main.py lines 3096-3230
- **Tab 5 (Batch)**: main.py lines 3257-3530
- **Tab 6 (Analytics)**: main.py lines 3534-3661+

---

## Next Steps

1. Read full analysis: `MULTIPAGE_ANALYSIS.md`
2. Create `pages/` directory
3. Start with Phase 1 (Student page - easiest)
4. Move through phases in order
5. Run `streamlit run main.py` after each phase
6. Test thoroughly before moving to next phase
