# InstaSchool Multi-Page Streamlit App Refactoring Analysis

## Executive Summary

The current `main.py` (3,660+ lines) contains three distinct user modes that should be separated into individual pages:
1. **Student Mode** (lines 874-979) - Already has dedicated module at `src/student_mode/student_ui.py`
2. **Parent Mode** (lines 984-1199) - Family dashboard and reports
3. **Teacher/Create Mode** (lines 1202-3650+) - Curriculum generation and management

**Current Architecture**: Single monolithic file with mode selector. 
**Recommended Architecture**: Multi-page Streamlit app with shared configuration and state management.

---

## File Structure Analysis

### Main.py Components (by line ranges)

#### 1. Imports & Setup (lines 0-149)
- **Purpose**: Initialize logging, state management, services
- **Status**: Shared - Should stay in main.py
- **Key components**:
  - Verbose logger initialization
  - Agent framework imports
  - Service imports (CurriculumService, BatchManager, TemplateManager)
  - UI components (ModernUI, ThemeManager)
  - Page config setup

#### 2. Utility Functions & Helpers (lines 160-809)
- **Purpose**: Password check, quickstart guide, config loading, cleanup
- **Shared Functions** (stay in main.py):
  - `check_password()` - lines 160-215
  - `show_quickstart_guide()` - lines 219-343
  - `load_config()` - lines 560-637
  - `detect_mobile_from_query_params()` - lines 295-343
  - Cleanup functions (lines 409-756)
  
#### 3. Student Mode (lines 874-979)
- **Current Implementation**: Mode selector + import from `src/student_mode/student_ui.py`
- **Location**: Already delegated to separate module
- **Status**: READY - Minimal changes needed
- **Call**: `render_student_mode(config, client)`

#### 4. Parent Mode (lines 984-1199)
- **Lines**: ~215 lines of direct code
- **Components**:
  - Family Overview tab (lines 1001-1049)
  - Reports & Certificates tab (lines 1051-1120)
  - Curricula tab (lines 1122-1170)
  - Settings tab (lines 1172-1198)
- **Dependencies**:
  - `FamilyDashboard` from `src/ui_components`
  - `family_service`, `report_service`, `certificate_service`, `user_service`
  - `ThemeManager`
- **Status**: READY FOR EXTRACTION

#### 5. Teacher/Create Mode (lines 1202-3650+)
- **Sidebar Configuration** (lines 1203-1499):
  - Basic settings (subject, grade, style, language)
  - AI Provider selection
  - AI Model settings
  - Content settings
  - Tips & Help
  - Preferences & theme

- **Main Content - 6 Tabs** (lines 1503-3650+):
  - Tab 1: Generate (lines 1505-1645)
  - Tab 2: View & Edit (lines 1650+)
  - Tab 3: Export (lines 2000+)
  - Tab 4: Templates (lines 3096-3230)
  - Tab 5: Batch Processing (lines 3257-3530)
  - Tab 6: Analytics (lines 3534-3661+)

- **Sidebar Length**: ~300 lines
- **Content Length**: ~2,400+ lines
- **Status**: READY FOR EXTRACTION

---

## Recommended Multi-Page Structure

### Directory Layout
```
instaSchool/
├── main.py                          # Entry point (reduced)
├── pages/
│   ├── 1_Student.py               # Student learning interface
│   ├── 2_Create.py                # Teacher curriculum creation
│   └── 3_Parent.py                # Parent dashboard
├── src/
│   ├── shared_config.py           # NEW: Shared initialization
│   ├── shared_sidebar.py          # NEW: Teacher sidebar config
│   ├── student_mode/
│   │   ├── student_ui.py          # EXISTING: Already modular
│   │   ├── progress_manager.py
│   │   └── review_queue.py
│   └── ... (existing modules)
└── services/                       # EXISTING: Already modular
```

---

## Function Mapping by Page

### pages/1_Student.py
**Current Location**: main.py lines 874-979 (imports from `src/student_mode/student_ui.py`)

**Functions to include**:
```
- Mode selector display (simplified for student)
- Student login/profile management (lines 875-961)
- render_student_mode() (imported from src/student_mode/student_ui.py)
```

**Dependencies**:
- `UserService` from services.user_service
- `StateManager` from src.state_manager
- `render_student_mode()` from src.student_mode.student_ui
- `config` (loaded)
- `client` (initialized)

**Status**: Nearly ready - just needs to be moved to pages/1_Student.py

---

### pages/2_Create.py
**Current Location**: main.py lines 1202-3650+ (Teacher mode)

**Sections to include**:

1. **Sidebar Configuration** (lines 1203-1499):
   ```python
   # Basic Settings Section
   st.sidebar.expander("📚 **Basic Settings**")
   - Subject selection (multiselect)
   - Grade level (selectbox)
   - Teaching style (selectbox)
   - Language (selectbox)
   
   # AI Provider Section
   st.sidebar.expander("🔌 **AI Provider**")
   - Provider selection
   - Cross-provider mode toggle
   
   # AI Model Settings
   st.sidebar.expander("🤖 **AI Model Settings**")
   - Main model selection
   - Worker model selection
   - Cost estimation
   - Image model selection
   
   # Content Settings
   st.sidebar.expander("📝 **Content Settings**")
   - Media richness slider
   - Component toggles (quizzes, summary, resources)
   - Days input
   
   # Tips & Help
   st.sidebar.expander("💡 **Tips & Help**")
   - UI help text
   
   # Theme & Preferences
   - Theme toggle
   - Mobile layout toggle
   ```

2. **Main Content Tabs** (lines 1503-3650+):
   - Tab 1: Generate New Curriculum
   - Tab 2: View & Edit
   - Tab 3: Export
   - Tab 4: Templates
   - Tab 5: Batch Processing
   - Tab 6: Analytics

**Dependencies**:
- All services (CurriculumService, BatchManager, TemplateManager, AnalyticsService)
- UI components (ModernUI, ThemeManager, LayoutHelpers, StatusLogger)
- ImageGenerator
- Config (with defaults and prompts)
- Client (initialized)
- StateManager for session management
- Provider service for AI provider management

**Key Session State Variables**:
- `st.session_state.curriculum` - current curriculum
- `st.session_state.template_manager` - template manager
- `st.session_state.batch_manager` - batch manager
- `st.session_state.analytics_service` - analytics
- `st.session_state.provider_service` - AI provider
- `st.session_state.is_mobile` - mobile layout toggle
- `st.session_state.theme` - selected theme
- Selected settings: subject, grade, style, language, model choices

**Status**: Large but straightforward extraction

---

### pages/3_Parent.py
**Current Location**: main.py lines 984-1199 (Parent mode)

**Tabs to include** (lines 993-1198):
1. **Family Overview** (lines 1001-1049)
   - Family dashboard display
   - Add child form
   - Empty state onboarding

2. **Reports & Certificates** (lines 1051-1120)
   - PDF report generation
   - Certificate generation
   - Child selection

3. **Curricula** (lines 1122-1170)
   - View created curricula
   - Display curriculum metadata

4. **Settings** (lines 1172-1198)
   - Theme toggle
   - Add child management
   - Family configuration

**Dependencies**:
- `FamilyDashboard` from src.ui_components
- `family_service` from services.family_service
- `report_service` from services.report_service
- `certificate_service` from services.certificate_service
- `UserService` from services.user_service
- `ThemeManager` from src.ui_components
- `config`

**Session State Variables**:
- Optional parent-level preferences
- Report generation state

**Status**: Clean extraction - well-contained code

---

## Shared Code to Extract

### 1. src/shared_config.py (NEW)
**Purpose**: Centralized configuration and initialization

**Contents**:
```python
"""Shared configuration and initialization for all pages."""

def initialize_app():
    """Initialize app config, services, and state."""
    # Load configuration
    # Initialize all cached services
    # Set up state manager
    # Return: (config, client, services_dict)

def setup_page_config():
    """Configure Streamlit page settings."""
    # set_page_config()
    # Load CSS
    # Initialize theme

def get_initialized_services():
    """Get or initialize all services."""
    # OpenAI client
    # CurriculumService
    # BatchManager
    # TemplateManager
    # UserService
    # AnalyticsService
    # Return services dict
```

### 2. src/shared_sidebar.py (NEW)
**Purpose**: Teacher mode sidebar configuration (for pages/2_Create.py)

**Contents**:
```python
"""Sidebar configuration for Create/Teacher mode."""

def render_basic_settings_sidebar(config):
    """Subject, grade, style, language selection."""
    # Returns: (subject_str, grade, lesson_style, language)

def render_ai_provider_sidebar(provider_service, available_providers):
    """AI provider selection and cross-provider config."""
    # Returns: (current_provider, cross_provider_enabled, orch_prov, worker_prov)

def render_ai_model_sidebar(provider_service, current_provider, config):
    """Model selection for orchestrator and workers."""
    # Returns: (text_model, worker_model, image_model, image_size)

def render_content_settings_sidebar(config):
    """Media richness, component toggles."""
    # Returns: (media_richness, include_quizzes, include_summary, include_resources, include_keypoints, num_days)

def render_preferences_sidebar():
    """Theme and mobile layout."""
    # Returns: (theme, mobile_mode)

def render_sidebar_complete(config, provider_service):
    """Render entire sidebar with all sections."""
    # Calls all the above functions
    # Returns: all settings in a dict
```

---

## Main.py Refactoring

### Reduced main.py (New Entry Point)
**Purpose**: Mode selector and page router

**Contents** (approximately 100-150 lines):
```python
import streamlit as st
from src.shared_config import initialize_app, setup_page_config
from src.state_manager import StateManager

# Set up page
setup_page_config()

# Initialize app
config, client, services = initialize_app()

# Store in session state
StateManager.initialize_state()
StateManager.set_state('config', config)
StateManager.set_state('client', client)
StateManager.set_state('provider_service', services['provider_service'])
StateManager.set_state('curriculum_service', services['curriculum_service'])
StateManager.set_state('batch_manager', services['batch_manager'])
StateManager.set_state('template_manager', services['template_manager'])
StateManager.set_state('analytics_service', services['analytics_service'])

# Mode selector (simplified)
st.sidebar.markdown("## 🎓 InstaSchool")
st.sidebar.markdown("---")

mode_options = {
    "parent": "👨‍👩‍👧 Parent Dashboard",
    "teacher": "👨‍🏫 Create & Manage",
    "student": "🎒 Student Learning"
}

app_mode = st.sidebar.selectbox(
    "Mode",
    options=list(mode_options.keys()),
    format_func=lambda x: mode_options[x],
    key="app_mode",
    help="Select your role"
)

StateManager.update_state('current_mode', app_mode)

# Pages are auto-loaded by Streamlit based on selection
# This is handled by the pages/ directory structure
```

**Note**: Streamlit Multi-Page apps automatically route based on `pages/` directory. The mode selector can navigate directly via st.switch_page() or use sidebar selectbox that coordinates with page loading.

---

## Session State Variables to Preserve

### Global/Shared
- `config` - Application configuration
- `client` - OpenAI/API client
- `provider_service` - AI provider service
- `current_provider` - Selected provider (openai/kimi)
- `current_user` - Logged-in student (if any)
- `current_mode` - Selected mode (parent/teacher/student)
- `is_mobile` - Mobile layout toggle
- `theme` - Selected theme
- `user_service` - Student/user management service

### Teacher Mode Specific
- `curriculum` - Current curriculum being edited
- `template_manager` - Template manager instance
- `batch_manager` - Batch processing manager
- `analytics_service` - Analytics service
- `selected_template_id` - Currently selected template
- `active_tab` - Active tab in teacher mode
- `image_size` - Selected image size
- Various subject/grade/model selections

### Student Mode Specific
- `login_needs_pin` - Login state
- `login_username` - Current username
- Student progress tracking (handled by student_ui.py)

### Parent Mode Specific
- Parent-specific preferences (if any)

---

## Migration Path

### Phase 1: Extract Student Mode (Already 80% done)
- [x] Student mode already has dedicated module at `src/student_mode/student_ui.py`
- Create `pages/1_Student.py` that:
  - Imports and wraps `render_student_mode()`
  - Includes login/profile management UI (currently in main.py lines 875-961)
  - Minimal changes needed

### Phase 2: Extract Parent Mode
- Create `pages/3_Parent.py` with:
  - All parent mode tabs (currently lines 984-1199)
  - Import necessary services and UI components
  - Session state management for parent mode

### Phase 3: Extract Create/Teacher Mode
- Create `src/shared_sidebar.py` with modular sidebar functions
- Create `pages/2_Create.py` with:
  - All 6 tabs for teacher mode (currently lines 1503-3650+)
  - Sidebar rendered via `shared_sidebar.py`
  - All session state management

### Phase 4: Create Shared Modules
- Create `src/shared_config.py` with:
  - App initialization
  - Service setup
  - Config loading
- Refactor `main.py` to minimal entry point

### Phase 5: Testing & Validation
- Test mode switching
- Test session state persistence
- Test all tabs and functionality
- Verify sidebar behavior across pages

---

## Key Considerations

### 1. Session State Persistence
- Streamlit automatically persists `st.session_state` across pages
- StateManager wraps this and should work seamlessly
- Sidebar selections should save to session state immediately

### 2. Module Imports
- All services should be initialized once and cached
- Use `@st.cache_resource` decorators
- StateManager handles cross-page state sharing

### 3. Authentication
- Student login currently in main.py (lines 875-961)
- Should be part of `pages/1_Student.py`
- UserService handles student profiles

### 4. Configuration Loading
- `config.yaml` loaded once and cached
- Should be accessible from all pages via StateManager
- Model and provider defaults come from config

### 5. Mobile Layout
- Toggle is sidebar-wide (applies to all pages)
- Should be set in session state for all pages to access
- ModernUI components check this flag

### 6. Image Generation
- Only available in teacher/create mode
- ImageGenerator initialized in create page
- Uses OpenAI API specifically

---

## File Size Comparison

### Current Structure
- `main.py`: 3,660+ lines

### Proposed Structure
- `main.py`: ~120 lines (entry point only)
- `pages/1_Student.py`: ~150 lines
- `pages/2_Create.py`: ~2,400 lines
- `pages/3_Parent.py`: ~250 lines
- `src/shared_config.py`: ~150 lines (NEW)
- `src/shared_sidebar.py`: ~300 lines (NEW)

**Total**: ~3,370 lines (similar total but much better organized)

---

## Implementation Checklist

### Pre-Migration Setup
- [ ] Create `pages/` directory
- [ ] Create `src/shared_config.py`
- [ ] Create `src/shared_sidebar.py`
- [ ] Update `main.py` to serve as entry point

### Phase 1: Student Page
- [ ] Create `pages/1_Student.py`
- [ ] Move student login code from main.py
- [ ] Import `render_student_mode()` from existing module
- [ ] Test with `streamlit run main.py`

### Phase 2: Parent Page
- [ ] Create `pages/3_Parent.py`
- [ ] Extract parent mode code (lines 984-1199)
- [ ] Import necessary services and components
- [ ] Test all 4 parent tabs

### Phase 3: Create Page
- [ ] Extract sidebar config to `src/shared_sidebar.py`
- [ ] Create `pages/2_Create.py`
- [ ] Move all 6 tabs to new page
- [ ] Update sidebar rendering to use `shared_sidebar.py`
- [ ] Test all 6 tabs and functionality

### Phase 4: Shared Modules
- [ ] Consolidate initialization in `src/shared_config.py`
- [ ] Verify StateManager works across pages
- [ ] Test session state persistence

### Phase 5: Validation
- [ ] Mode switching works correctly
- [ ] All sidebar selections persist
- [ ] No functionality broken
- [ ] All imports resolve correctly
- [ ] Performance acceptable (caching working)

---

## Code Examples

### Example: pages/1_Student.py
```python
import streamlit as st
from src.state_manager import StateManager
from services.user_service import UserService
from src.student_mode.student_ui import render_student_mode

st.set_page_config(page_title="Student Learning", page_icon=":books:", layout="wide")

# Initialize
config = StateManager.get_state('config')
client = StateManager.get_state('client')

st.sidebar.markdown("### 👤 Student Login")

user_service = StateManager.get_state("user_service")
if not user_service:
    user_service = UserService()
    StateManager.set_state("user_service", user_service)

current_user = StateManager.get_state("current_user")

# Login UI (from main.py lines 875-961)
if not current_user:
    # ... login form code ...
    pass
else:
    st.sidebar.success(f"✓ Logged in as **{current_user['username']}**")
    if st.sidebar.button("Logout", use_container_width=True):
        StateManager.set_state("current_user", None)
        st.rerun()

    # Render student learning interface
    render_student_mode(config, client)
```

### Example: src/shared_sidebar.py
```python
import streamlit as st
from services.session_service import InputValidator

def render_basic_settings_sidebar(config):
    """Render subject, grade, style, language selections."""
    with st.sidebar.expander("📚 **Basic Settings**", expanded=True):
        selected_subjects = st.multiselect(
            "Subject", 
            config["defaults"]["subjects"],
            default=[config["defaults"]["subject"]],
            key="sidebar_subjects"
        )
        # ... rest of code ...
        return subject_str, grade, lesson_style, language

def render_sidebar_complete(config, provider_service):
    """Render all sidebar sections."""
    st.sidebar.markdown("## ⚙️ Curriculum Settings")
    st.sidebar.markdown("---")
    
    subject_str, grade, style, language = render_basic_settings_sidebar(config)
    provider, cross_enabled = render_ai_provider_sidebar(provider_service)
    text_model, worker_model, image_model = render_ai_model_sidebar(...)
    media_richness, quizzes, summary = render_content_settings_sidebar(config)
    theme, mobile = render_preferences_sidebar()
    
    return {
        'subject': subject_str,
        'grade': grade,
        'style': style,
        'language': language,
        'provider': provider,
        'text_model': text_model,
        'worker_model': worker_model,
        'image_model': image_model,
        'media_richness': media_richness,
        'include_quizzes': quizzes,
        'include_summary': summary,
        'include_resources': include_resources,
        'theme': theme,
        'mobile': mobile
    }
```

---

## Testing Strategy

### Unit Tests to Verify
1. Session state persistence across page navigation
2. Service initialization and caching
3. Config loading and defaults
4. All sidebar sections render without errors
5. Mode selection works correctly

### Integration Tests to Verify
1. Navigate between all three pages
2. Create curriculum in Create page
3. View progress in Student page
4. Check reports in Parent page
5. Switch modes and verify state preserved

### Manual Testing Checklist
- [ ] Load app and see mode selector
- [ ] Switch to Student, login, see learning interface
- [ ] Switch to Create, configure settings, generate curriculum
- [ ] Switch to Parent, see dashboard
- [ ] Return to Student, see same session still logged in
- [ ] Check sidebar settings persist when switching pages
- [ ] Verify all 6 Create tabs work
- [ ] Verify all 4 Parent tabs work

---

## Potential Issues & Solutions

### Issue 1: Session State Not Persisting
**Cause**: StateManager not properly synced with st.session_state
**Solution**: Ensure all pages use StateManager.get_state() and set_state() consistently

### Issue 2: Imports Breaking on Page Switch
**Cause**: Circular imports or missing module initialization
**Solution**: Move all imports to page files, ensure shared modules are self-contained

### Issue 3: Service Caching Issues
**Cause**: `@st.cache_resource` not working across pages
**Solution**: Store cached services in StateManager instead of relying solely on decorator

### Issue 4: Large File Doesn't Load
**Cause**: pages/2_Create.py becomes too large (2,400 lines)
**Solution**: Break Create page into sub-components:
- `src/create_mode/generate_tab.py`
- `src/create_mode/edit_tab.py`
- `src/create_mode/export_tab.py`
- etc.

### Issue 5: Performance Degradation
**Cause**: Each page reload causes re-initialization
**Solution**: Leverage StateManager caching and @st.cache_resource properly

---

## Summary

The refactoring is highly feasible with minimal architectural changes needed. The code is already well-organized with dedicated services and UI components. The main work is:

1. **Extract existing code** into page files (mostly copy-paste)
2. **Create shared utility modules** for sidebar and config
3. **Establish shared state** via StateManager
4. **Test** mode switching and state persistence

**Estimated effort**: 4-6 hours for a complete refactoring with testing.

**Benefits**:
- Better code organization
- Easier to maintain and test individual pages
- Faster navigation between modes
- Clearer separation of concerns
- Foundation for future feature additions
