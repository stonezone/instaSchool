# Student Mode Quick Start Guide
## Get Up and Running in 30 Minutes

**For**: Developers ready to implement  
**Time**: ~30 minutes to first working prototype  
**Prerequisites**: InstaSchool project already set up

---

## 🚀 Speed Run: Working Student Mode in 30 Minutes

### Step 1: Create Files (2 minutes)

```bash
# From project root
cd /Users/zackjordan/code/instaSchool

# Create student_mode module
mkdir -p src/student_mode
touch src/student_mode/__init__.py
touch src/student_mode/student_ui.py
touch src/student_mode/progress_manager.py
```

### Step 2: Add Mode Selector to main.py (5 minutes)

**Location**: After `st.sidebar.markdown("## ⚙️ Curriculum Settings")` (around line 280)

```python
# Add this block BEFORE the existing sidebar settings
st.sidebar.markdown("## 🎓 InstaSchool")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio(
    "Select Mode",
    ["👨‍🏫 Teacher (Create & Edit)", "🎒 Student (Learn & Practice)"],
    key="app_mode"
)

current_mode = 'teacher' if 'Teacher' in app_mode else 'student'
StateManager.update_state('current_mode', current_mode)

st.sidebar.markdown("---")

# If student mode, show student interface and stop
if current_mode == 'student':
    from src.student_mode.student_ui import render_student_mode
    render_student_mode(config, client)
    st.stop()

# Otherwise continue with teacher mode below...
```

### Step 3: Create Basic Student UI (10 minutes)

**File**: `src/student_mode/student_ui.py`

Copy this minimal working version:

```python
"""Student Mode UI - Minimal Working Version"""
import streamlit as st
import json
from pathlib import Path
from src.state_manager import StateManager
from src.ui_components import ModernUI

def render_student_mode(config, client):
    """Main student mode interface"""
    
    # Sidebar
    st.sidebar.markdown("### 🎯 Your Progress")
    st.sidebar.markdown("⭐ Level 0")
    st.sidebar.markdown("0/100 XP")
    st.sidebar.progress(0.0)
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("**📚 Choose Your Lesson**")
    
    # Get curricula
    curricula_path = Path("curricula")
    curriculum_files = [f for f in curricula_path.glob("*.json") 
                       if not f.name.startswith('progress_')]
    
    if not curriculum_files:
        st.info("No curricula available. Switch to Teacher Mode to create one!")
        return
    
    # Load curriculum options
    options = []
    for file in curriculum_files:
        with open(file, 'r') as f:
            data = json.load(f)
            meta = data.get('meta', {})
            options.append((f"{meta.get('subject')} - Grade {meta.get('grade')}", data))
    
    # Select curriculum
    selected_idx = st.sidebar.selectbox(
        "curriculum",
        range(len(options)),
        format_func=lambda i: options[i][0],
        label_visibility="collapsed"
    )
    
    curriculum = options[selected_idx][1]
    
    # Main area
    meta = curriculum.get('meta', {})
    st.markdown(f"# {meta.get('subject')} - Grade {meta.get('grade')}")
    
    # Get current section
    if 'student_section' not in st.session_state:
        st.session_state.student_section = 0
    
    section_idx = st.session_state.student_section
    units = curriculum.get('units', [])
    
    if section_idx >= len(units) * 6:
        st.success("🏆 Course Complete!")
        return
    
    # Determine which unit and section
    unit_idx = section_idx // 6
    section_type = section_idx % 6
    
    if unit_idx >= len(units):
        st.success("🏆 Course Complete!")
        return
        
    unit = units[unit_idx]
    
    # Show section
    section_names = ['intro', 'image', 'content', 'chart', 'quiz', 'summary']
    current_section = section_names[section_type]
    
    st.markdown(f"### Unit {unit_idx + 1}: {unit.get('title')}")
    st.markdown(f"*Section: {current_section.title()}*")
    
    # Display content based on section type
    if current_section == 'intro':
        st.markdown("**Welcome to this unit!**")
    elif current_section == 'image':
        img = unit.get('selected_image_b64')
        if img:
            st.image(f"data:image/png;base64,{img}")
    elif current_section == 'content':
        st.markdown(unit.get('content', 'No content'))
    elif current_section == 'chart':
        chart = unit.get('chart', {})
        if chart.get('b64'):
            st.image(f"data:image/png;base64,{chart['b64']}")
    elif current_section == 'quiz':
        st.markdown("**Quiz section - to be implemented**")
    elif current_section == 'summary':
        st.markdown(unit.get('summary', 'No summary'))
    
    # Navigation
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if section_idx > 0:
            if st.button("← Previous"):
                st.session_state.student_section -= 1
                st.rerun()
    
    with col2:
        if st.button("✅ Complete", type="primary"):
            st.success("+10 XP!")
            st.session_state.student_section += 1
            st.rerun()
    
    with col3:
        if st.button("Skip →"):
            st.session_state.student_section += 1
            st.rerun()
```

### Step 4: Test It! (3 minutes)

```bash
streamlit run main.py
```

**What you should see**:
1. Mode selector at top of sidebar
2. Switch to "Student" mode
3. Curriculum selector appears
4. Basic section display with navigation
5. Clicking "Complete" advances to next section

---

## ✅ You Now Have Working Student Mode!

### What Works:
- ✅ Mode switching
- ✅ Curriculum selection
- ✅ Section navigation
- ✅ Basic content display

### What's Next:
Continue with **STUDENT_MODE_IMPLEMENTATION_GUIDE.md** for:
- XP system with level-ups
- Interactive quizzes
- Progress persistence
- AI tutor
- Celebrations & polish

---

## 🐛 Troubleshooting

### "Module not found" error
```bash
# Make sure you created __init__.py
touch src/student_mode/__init__.py
```

### Mode selector doesn't appear
- Check you added code BEFORE existing sidebar settings
- Ensure indentation is correct
- Verify StateManager is imported

### No curricula showing
```bash
# Create a test curriculum in Teacher Mode first
# Then switch back to Student Mode
```

### Navigation not working
- Verify `st.session_state.student_section` is being updated
- Check `st.rerun()` is being called
- Ensure session state persists between clicks

---

## 📊 Full Feature Comparison

| Feature | This Quick Start | Full Implementation |
|---------|-----------------|---------------------|
| Mode switching | ✅ | ✅ |
| Curriculum selection | ✅ | ✅ |
| Navigation | ✅ | ✅ |
| Content display | ✅ Basic | ✅ Enhanced |
| XP System | ❌ | ✅ |
| Level-ups | ❌ | ✅ |
| Quizzes | ❌ Placeholder | ✅ Interactive |
| Progress saving | ❌ | ✅ |
| AI Tutor | ❌ | ✅ |
| Celebrations | ❌ | ✅ |
| Mobile optimized | ⚠️ Partial | ✅ |

---

## 🎯 Where to Go From Here

### Option 1: Demo Now (Quick)
- Show stakeholders the basic working prototype
- Get feedback on navigation and flow
- Validate the approach

### Option 2: Continue Building (Recommended)
Follow the phases in **STUDENT_MODE_IMPLEMENTATION_GUIDE.md**:
- **Phase 2**: Add XP system (~2 hours)
- **Phase 3**: Enhance content display (~3 hours)
- **Phase 4**: Build quiz system (~4 hours)
- **Phase 5**: Polish & extras (~2 hours)

### Option 3: Iterate
- Test with real students
- Gather feedback
- Prioritize features based on impact

---

## 💡 Pro Tips

1. **Test with Real Curricula**: Use existing curricula from Teacher Mode
2. **Mobile First**: Test on mobile browser early
3. **Console Check**: Watch browser console for errors
4. **State Debugging**: Use `st.write(st.session_state)` to debug state
5. **Incremental**: Build one feature at a time, test thoroughly

---

## 📚 Reference Documents

- **STUDENT_MODE_SUMMARY.md** - Overview & rationale
- **STUDENT_MODE_DESIGN_SPEC.md** - Complete design specification
- **STUDENT_MODE_IMPLEMENTATION_GUIDE.md** - Full development guide
- **STUDENT_MODE_VISUAL_REFERENCE.md** - UI mockups & layouts

---

## 🎉 Congratulations!

You now have a working Student Mode in InstaSchool! Students can:
- Switch to student interface
- Select a curriculum
- Navigate through sections
- See content, images, charts

**Next**: Add the XP system to make it engaging and gamified! 🚀

---

**Quick Start Complete** ✅  
**Time Invested**: ~30 minutes  
**Lines of Code**: ~150  
**Features Working**: 4/10  
**Path Forward**: Clear & documented
