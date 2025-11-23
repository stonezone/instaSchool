# Student Mode Implementation Guide
## Step-by-Step Development Roadmap

**Version**: 1.0  
**Date**: 2025-11-23  
**For**: InstaSchool Student Learning Mode

---

## Quick Start Summary

### What We're Building
An interactive student learning interface where students:
- Select a curriculum to study
- Progress through units one section at a time
- Earn XP for completing sections and quizzes
- Level up based on XP earned
- Get help from an AI tutor (optional)

### Key Features
✅ Mode switching (Teacher ↔ Student)  
✅ XP and leveling system  
✅ Progress tracking per curriculum  
✅ Interactive quizzes with immediate feedback  
✅ Visual progress indicators  
✅ Celebration animations  
✅ AI tutor chatbot  

---

## Implementation Phases

### Phase 1: Foundation (Day 1 Morning)
**Goal**: Get basic student mode working with mode switching

#### 1.1 Create Student Mode Module Structure
```bash
mkdir -p src/student_mode
touch src/student_mode/__init__.py
touch src/student_mode/student_ui.py
touch src/student_mode/progress_manager.py
```

#### 1.2 Add Mode Selector to main.py

**Location**: After sidebar initialization, before settings

```python
# In main.py, after st.sidebar.markdown("## ⚙️ Curriculum Settings")

# Add mode selector at the top
st.sidebar.markdown("## 🎓 InstaSchool")
st.sidebar.markdown("---")

app_mode = st.sidebar.radio(
    "Select Mode",
    ["👨‍🏫 Teacher (Create & Edit)", "🎒 Student (Learn & Practice)"],
    key="app_mode",
    help="Switch between creating curricula and learning from them"
)

# Store mode in state
current_mode = 'teacher' if 'Teacher' in app_mode else 'student'
StateManager.update_state('current_mode', current_mode)

st.sidebar.markdown("---")

# Conditional rendering based on mode
if current_mode == 'student':
    # Hide teacher controls
    st.sidebar.empty()
    
    # Import student mode UI
    from src.student_mode.student_ui import render_student_mode
    
    # Render student interface in main area
    render_student_mode(config, client)
    
    # Stop processing rest of teacher UI
    st.stop()

# Continue with teacher mode UI below...
```

#### 1.3 Create Basic Student UI Structure

**File**: `src/student_mode/student_ui.py`

```python
"""
Student Mode UI Components
Main interface for student learning experience
"""

import streamlit as st
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional

from src.state_manager import StateManager
from src.ui_components import ModernUI

def render_student_mode(config: Dict, client):
    """Main entry point for student mode"""
    
    # Render sidebar components
    render_student_sidebar(config)
    
    # Get selected curriculum
    curriculum = StateManager.get_state('selected_curriculum')
    
    if curriculum is None:
        render_no_curriculum_message()
        return
    
    # Render main learning interface
    render_learning_interface(curriculum, config, client)

def render_student_sidebar(config: Dict):
    """Render student mode sidebar"""
    
    st.sidebar.markdown("### 🎯 Your Progress")
    
    # XP Progress widget
    render_xp_progress(config)
    
    st.sidebar.markdown("---")
    
    # Curriculum selector
    render_curriculum_selector()
    
    st.sidebar.markdown("---")
    
    # Unit progress overview
    curriculum = StateManager.get_state('selected_curriculum')
    if curriculum:
        render_unit_progress_sidebar(curriculum)

def render_no_curriculum_message():
    """Show message when no curriculum is selected"""
    ModernUI.card(
        title="📚 Welcome to Student Mode!",
        content="""
        **Ready to start learning?**
        
        Select a curriculum from the sidebar to begin your learning journey!
        
        If you don't see any curricula available, ask your teacher to create one in Teacher Mode.
        """,
        icon="🎓"
    )

def render_xp_progress(config: Dict):
    """Render XP and level progress"""
    progress_data = StateManager.get_state('student_progress', {})
    total_xp = progress_data.get('total_xp', 0)
    
    # Calculate level
    xp_per_level = config['student_mode']['xp_per_level']
    current_level = total_xp // xp_per_level
    xp_in_level = total_xp % xp_per_level
    progress_pct = xp_in_level / xp_per_level if xp_per_level > 0 else 0
    
    # Render stats card
    ModernUI.stats_card(
        value=f"Level {current_level}",
        label=f"{xp_in_level}/{xp_per_level} XP",
        icon="⭐",
        key="student_xp_widget"
    )
    
    # Progress bar
    st.sidebar.progress(
        progress_pct,
        text=f"{int(progress_pct*100)}% to Level {current_level + 1}"
    )

def render_curriculum_selector():
    """Render curriculum selection dropdown"""
    curricula_path = Path("curricula")
    
    if not curricula_path.exists():
        st.sidebar.warning("No curricula folder found")
        return
    
    # Get all curriculum files
    curriculum_files = list(curricula_path.glob("*.json"))
    
    # Filter out progress files
    curriculum_files = [f for f in curriculum_files if not f.name.startswith('progress_')]
    
    if not curriculum_files:
        st.sidebar.warning("No curricula available. Ask your teacher to create one!")
        return
    
    # Load metadata for selection
    curriculum_options = []
    for file in curriculum_files:
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                meta = data.get('meta', {})
                label = f"{meta.get('subject', 'Unknown')} - Grade {meta.get('grade', '?')}"
                curriculum_options.append((label, file.name, data))
        except Exception as e:
            continue
    
    if not curriculum_options:
        st.sidebar.error("No valid curricula found")
        return
    
    # Dropdown selection
    st.sidebar.markdown("**📚 Choose Your Lesson**")
    
    selected_idx = st.sidebar.selectbox(
        "Select curriculum",
        range(len(curriculum_options)),
        format_func=lambda i: curriculum_options[i][0],
        key="curriculum_selector",
        label_visibility="collapsed"
    )
    
    # Store selected curriculum
    selected_data = curriculum_options[selected_idx][2]
    selected_filename = curriculum_options[selected_idx][1]
    
    StateManager.update_state('selected_curriculum', selected_data)
    StateManager.update_state('selected_curriculum_file', selected_filename)
    
    # Load progress for this curriculum
    from src.student_mode.progress_manager import load_student_progress
    load_student_progress(selected_filename)

def render_unit_progress_sidebar(curriculum: Dict):
    """Show unit completion status"""
    st.sidebar.markdown("**📊 Course Progress**")
    
    progress_data = StateManager.get_state('student_progress', {})
    current_section = progress_data.get('current_section_index', 0)
    
    units = curriculum.get('units', [])
    sections_per_unit = 6  # intro, image, content, chart, quiz, summary
    
    current_unit_idx = current_section // sections_per_unit
    
    for idx, unit in enumerate(units):
        title = unit.get('title', f'Unit {idx+1}')
        
        if idx < current_unit_idx:
            icon = "✅"
            color = "#10b981"
        elif idx == current_unit_idx:
            icon = "📖"
            color = "#3b82f6"
        else:
            icon = "🔒"
            color = "#9ca3af"
        
        # Truncate long titles
        display_title = title[:25] + "..." if len(title) > 25 else title
        
        st.sidebar.markdown(
            f'<div style="color: {color}; font-size: 0.9em;">'
            f'{icon} Unit {idx+1}: {display_title}'
            f'</div>',
            unsafe_allow_html=True
        )

def render_learning_interface(curriculum: Dict, config: Dict, client):
    """Render main learning area with current section"""
    
    # Show curriculum header
    meta = curriculum.get('meta', {})
    st.markdown(f"# {meta.get('subject', 'Subject')} - Grade {meta.get('grade', '?')}")
    
    # Overall progress bar
    render_overall_progress(curriculum)
    
    st.markdown("---")
    
    # Render current section
    render_current_section(curriculum, config, client)

def render_overall_progress(curriculum: Dict):
    """Show overall course completion progress"""
    progress_data = StateManager.get_state('student_progress', {})
    current_section = progress_data.get('current_section_index', 0)
    
    units = curriculum.get('units', [])
    total_sections = len(units) * 6  # 6 sections per unit
    
    progress_pct = current_section / total_sections if total_sections > 0 else 0
    
    st.progress(progress_pct, text=f"Overall Progress: {int(progress_pct*100)}% Complete")

def render_current_section(curriculum: Dict, config: Dict, client):
    """Render the current learning section"""
    
    progress_data = StateManager.get_state('student_progress', {})
    section_idx = progress_data.get('current_section_index', 0)
    
    units = curriculum.get('units', [])
    sections_per_unit = 6
    
    unit_idx = section_idx // sections_per_unit
    section_type_idx = section_idx % sections_per_unit
    
    # Check if course complete
    if unit_idx >= len(units):
        render_course_complete(curriculum)
        return
    
    current_unit = units[unit_idx]
    
    # Section types
    section_types = [
        'introduction',
        'illustration',
        'content',
        'chart',
        'quiz',
        'summary'
    ]
    
    section_type = section_types[section_type_idx]
    
    # Render appropriate section
    if section_type == 'introduction':
        render_introduction(current_unit, unit_idx)
    elif section_type == 'illustration':
        render_illustration(current_unit)
    elif section_type == 'content':
        render_content(current_unit)
    elif section_type == 'chart':
        render_chart(current_unit)
    elif section_type == 'quiz':
        render_quiz(current_unit, unit_idx, config)
    elif section_type == 'summary':
        render_summary(current_unit)

# Section rendering functions (stubs for Phase 1)
def render_introduction(unit: Dict, unit_idx: int):
    """Render unit introduction"""
    ModernUI.card(
        title=f"Unit {unit_idx + 1}: {unit.get('title', 'Untitled')}",
        content="Introduction section - to be implemented",
        icon="🚀"
    )
    render_navigation()

def render_illustration(unit: Dict):
    """Render illustration section"""
    st.info("Illustration section - to be implemented")
    render_navigation()

def render_content(unit: Dict):
    """Render main content section"""
    st.info("Content section - to be implemented")
    render_navigation()

def render_chart(unit: Dict):
    """Render chart section"""
    st.info("Chart section - to be implemented")
    render_navigation()

def render_quiz(unit: Dict, unit_idx: int, config: Dict):
    """Render quiz section"""
    st.info("Quiz section - to be implemented")
    render_navigation()

def render_summary(unit: Dict):
    """Render summary section"""
    st.info("Summary section - to be implemented")
    render_navigation()

def render_course_complete(curriculum: Dict):
    """Show course completion message"""
    st.balloons()
    
    ModernUI.card(
        title="🏆 Congratulations!",
        content="""
        You've completed the entire course! Great work!
        
        Your achievements will be saved to your progress file.
        """,
        icon="🎉"
    )

def render_navigation():
    """Render section navigation buttons"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if st.button("← Previous", key="nav_prev"):
            # TODO: Implement
            pass
    
    with col2:
        if st.button("✅ Complete & Continue", type="primary", key="nav_complete"):
            advance_section()
            st.rerun()
    
    with col3:
        if st.button("Skip →", key="nav_skip"):
            advance_section()
            st.rerun()

def advance_section():
    """Move to next section"""
    progress_data = StateManager.get_state('student_progress', {})
    current_idx = progress_data.get('current_section_index', 0)
    
    progress_data['current_section_index'] = current_idx + 1
    StateManager.update_state('student_progress', progress_data)
    
    # Save progress
    from src.student_mode.progress_manager import save_student_progress
    save_student_progress()
```

#### 1.4 Create Progress Manager

**File**: `src/student_mode/progress_manager.py`

```python
"""
Student Progress Management
Handles saving and loading student progress data
"""

import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional

import streamlit as st
from src.state_manager import StateManager

def save_student_progress():
    """Save current progress to JSON file"""
    progress_data = StateManager.get_state('student_progress', {})
    curriculum_file = StateManager.get_state('selected_curriculum_file')
    
    if not curriculum_file:
        return
    
    # Create progress filename
    progress_file = Path("curricula") / f"progress_{curriculum_file}"
    
    # Update timestamp
    progress_data['last_updated'] = datetime.now().isoformat()
    
    try:
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
    except Exception as e:
        st.error(f"Error saving progress: {e}")

def load_student_progress(curriculum_file: str) -> Dict:
    """Load progress from JSON file or create new"""
    progress_file = Path("curricula") / f"progress_{curriculum_file}"
    
    if progress_file.exists():
        try:
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
            
            StateManager.update_state('student_progress', progress_data)
            return progress_data
            
        except Exception as e:
            st.error(f"Error loading progress: {e}")
    
    # Create new progress
    initial_progress = {
        'curriculum_file': curriculum_file,
        'current_section_index': 0,
        'total_xp': 0,
        'sections_completed': 0,
        'quizzes_completed': 0,
        'perfect_quizzes': 0,
        'quiz_scores': {},
        'completed_sections': [],
        'started_at': datetime.now().isoformat(),
        'last_updated': datetime.now().isoformat()
    }
    
    StateManager.update_state('student_progress', initial_progress)
    save_student_progress()
    
    return initial_progress

def reset_progress(curriculum_file: str):
    """Reset progress for a curriculum"""
    progress_file = Path("curricula") / f"progress_{curriculum_file}"
    
    if progress_file.exists():
        progress_file.unlink()
    
    # Reload fresh progress
    load_student_progress(curriculum_file)
```

**Testing Phase 1**:
```bash
streamlit run main.py
```

- Switch to Student Mode
- Verify curriculum selector appears
- Verify XP progress shows (Level 0, 0 XP)
- Verify unit list shows in sidebar
- Verify navigation buttons appear
- Click "Complete & Continue" - should advance

---

### Phase 2: XP System (Day 1 Afternoon)
**Goal**: Implement XP earning and level-up system

#### 2.1 Create XP System Module

**File**: `src/student_mode/xp_system.py`

```python
"""
XP and Leveling System
Handles XP calculations, awards, and level-ups
"""

import streamlit as st
import random
from src.state_manager import StateManager

def add_xp(amount: int, config: dict):
    """Add XP and check for level up"""
    progress_data = StateManager.get_state('student_progress', {})
    current_xp = progress_data.get('total_xp', 0)
    new_xp = current_xp + amount
    
    # Check for level up
    xp_per_level = config['student_mode']['xp_per_level']
    old_level = current_xp // xp_per_level
    new_level = new_xp // xp_per_level
    
    # Update XP
    progress_data['total_xp'] = new_xp
    StateManager.update_state('student_progress', progress_data)
    
    # Show XP gain
    st.success(f"✨ +{amount} XP earned!")
    
    # Check for level up
    if new_level > old_level:
        st.balloons()
        st.success(f"🎉 **LEVEL UP!** You're now Level {new_level}!")
    
    # Save progress
    from src.student_mode.progress_manager import save_student_progress
    save_student_progress()
    
    return new_level > old_level

def award_section_xp(config: dict):
    """Award XP for completing a section"""
    xp = config['student_mode']['xp_per_section']
    add_xp(xp, config)

def award_quiz_xp(score_pct: float, config: dict):
    """Award XP for completing a quiz"""
    xp = config['student_mode']['xp_per_quiz']
    
    # Add bonus for perfect score
    if score_pct == 100:
        bonus = config['student_mode']['xp_perfect_bonus']
        xp += bonus
        st.balloons()
        st.success(f"🌟 **PERFECT SCORE!** Bonus {bonus} XP!")
    
    leveled_up = add_xp(xp, config)
    
    return leveled_up

def get_xp_breakdown() -> dict:
    """Get breakdown of XP sources"""
    progress_data = StateManager.get_state('student_progress', {})
    
    sections = progress_data.get('sections_completed', 0)
    quizzes = progress_data.get('quizzes_completed', 0)
    perfect = progress_data.get('perfect_quizzes', 0)
    
    return {
        'sections': sections,
        'quizzes': quizzes,
        'perfect': perfect,
        'total_xp': progress_data.get('total_xp', 0)
    }

def get_encouragement(score_pct: float) -> str:
    """Get encouraging message based on score"""
    if score_pct == 100:
        messages = [
            "🌟 Perfect! You're a star!",
            "🎯 Bullseye! Amazing work!",
            "💯 Outstanding! You nailed it!"
        ]
    elif score_pct >= 80:
        messages = [
            "👍 Great job! You really know this!",
            "🎉 Excellent work! Keep it up!",
            "⭐ Super! You're doing amazing!"
        ]
    elif score_pct >= 60:
        messages = [
            "👏 Good effort! You're learning!",
            "💪 Nice try! Keep practicing!",
            "🌱 You're growing! Keep going!"
        ]
    else:
        messages = [
            "💪 Don't give up! Review and try again!",
            "🌟 Learning takes time! You've got this!",
            "📚 Take your time. Ask for help if needed!"
        ]
    
    return random.choice(messages)
```

#### 2.2 Update Navigation to Award XP

Update `student_ui.py`:

```python
def render_navigation(section_type: str = "generic"):
    """Render navigation with XP awards"""
    col1, col2, col3 = st.columns([1, 2, 1])
    
    progress_data = StateManager.get_state('student_progress', {})
    current_idx = progress_data.get('current_section_index', 0)
    
    with col1:
        if current_idx > 0:
            if st.button("← Previous", key="nav_prev"):
                progress_data['current_section_index'] = current_idx - 1
                StateManager.update_state('student_progress', progress_data)
                st.rerun()
    
    with col2:
        if st.button("✅ Complete & Continue", type="primary", key="nav_complete"):
            # Award XP based on section type
            from src.student_mode.xp_system import award_section_xp
            
            # Import config
            config = st.session_state.get('config', {})
            
            # Award XP (skip for quiz - handled separately)
            if section_type != 'quiz':
                award_section_xp(config)
            
            # Advance
            advance_section()
            st.rerun()
    
    with col3:
        if st.button("Skip →", key="nav_skip"):
            advance_section()
            st.rerun()
```

**Testing Phase 2**:
- Complete a section
- Verify XP is awarded
- Complete enough sections to level up
- Verify balloons appear on level up

---

### Phase 3: Content Sections (Day 2 Morning)
**Goal**: Implement all non-quiz sections with proper content display

#### 3.1 Implement Introduction Section

Update `student_ui.py`:

```python
def render_introduction(unit: Dict, unit_idx: int):
    """Render unit introduction"""
    ModernUI.card(
        title=f"Unit {unit_idx + 1}: {unit.get('title', 'Untitled')}",
        content=f"""
        **Welcome to this learning unit!**
        
        You're about to explore: **{unit.get('title')}**
        
        This lesson will help you understand important concepts through:
        - 📖 Clear explanations
        - 🎨 Visual illustrations
        - 📊 Data examples
        - ✅ Practice quizzes
        
        Take your time and enjoy learning!
        """,
        icon="🚀",
        status="info"
    )
    
    render_navigation(section_type="introduction")
```

#### 3.2 Implement Illustration Section

```python
def render_illustration(unit: Dict):
    """Render illustration"""
    image_b64 = unit.get('selected_image_b64')
    
    if image_b64:
        ModernUI.card(
            title="📸 Visual Learning",
            content="Study this illustration to help understand the concepts.",
            icon="🎨"
        )
        
        st.image(
            f"data:image/png;base64,{image_b64}",
            caption=unit.get('title', 'Illustration'),
            use_container_width=True
        )
        
        st.info("💡 Take a moment to observe the details in this image.")
    else:
        st.info("No illustration for this section.")
    
    render_navigation(section_type="illustration")
```

#### 3.3 Implement Content Section

```python
def render_content(unit: Dict):
    """Render main lesson content"""
    content = unit.get('content', 'No content available.')
    
    ModernUI.card(
        title="📖 Lesson Content",
        content="",
        icon="📚"
    )
    
    # Render markdown
    st.markdown(content, unsafe_allow_html=False)
    
    render_navigation(section_type="content")
```

#### 3.4 Implement Chart Section

```python
def render_chart(unit: Dict):
    """Render chart if available"""
    chart_dict = unit.get('chart', {})
    
    if chart_dict and chart_dict.get('b64'):
        suggestion = unit.get('chart_suggestion', {})
        title = suggestion.get('title', 'Chart') if suggestion else 'Chart'
        
        ModernUI.card(
            title=f"📊 {title}",
            content="Visual data to help you understand the concepts.",
            icon="📈"
        )
        
        st.image(
            f"data:image/png;base64,{chart_dict['b64']}",
            caption=title,
            width=400
        )
    else:
        st.info("No chart for this section.")
    
    render_navigation(section_type="chart")
```

#### 3.5 Implement Summary Section

```python
def render_summary(unit: Dict):
    """Render unit summary"""
    summary = unit.get('summary', 'No summary available.')
    
    ModernUI.card(
        title="📝 Summary",
        content=summary,
        icon="✅",
        status="success"
    )
    
    st.info("🎯 Review these key points to reinforce your learning!")
    
    render_navigation(section_type="summary")
```

**Testing Phase 3**:
- Navigate through all section types
- Verify content displays correctly
- Verify images and charts load
- Test with different curricula

---

### Phase 4: Quiz System (Day 2 Afternoon)
**Goal**: Full interactive quiz with XP rewards

#### 4.1 Create Quiz Handler Module

**File**: `src/student_mode/quiz_handler.py`

```python
"""
Quiz Rendering and Scoring
Handles interactive quizzes with immediate feedback
"""

import streamlit as st
from typing import Dict, List
from src.state_manager import StateManager
from src.ui_components import ModernUI

def render_quiz_section(unit: Dict, unit_idx: int, config: Dict):
    """Render interactive quiz"""
    quiz_data = unit.get('quiz', [])
    
    if not quiz_data:
        st.info("No quiz for this unit.")
        from src.student_mode.student_ui import render_navigation
        render_navigation(section_type="quiz")
        return
    
    ModernUI.card(
        title="✏️ Check Your Understanding",
        content="Answer all questions to test what you've learned!",
        icon="🎯",
        status="warning"
    )
    
    # Initialize quiz state
    if 'current_quiz_state' not in st.session_state:
        st.session_state.current_quiz_state = {}
    
    quiz_key = f"unit_{unit_idx}_quiz"
    all_answered = True
    correct_count = 0
    total_questions = len(quiz_data)
    
    # Render each question
    for q_idx, question in enumerate(quiz_data):
        q_key = f"{quiz_key}_q{q_idx}"
        
        st.markdown(f"### Question {q_idx + 1}")
        st.markdown(f"**{question.get('question', 'Question')}**")
        
        q_type = question.get('type')
        options = question.get('options', [])
        correct_answer = question.get('answer')
        
        # Render based on type
        if q_type == "MCQ":
            render_mcq_question(q_key, options, correct_answer)
        elif q_type == "TF":
            render_tf_question(q_key, correct_answer)
        elif q_type == "FILL":
            render_fill_question(q_key, correct_answer)
        
        # Check if answered
        if q_key not in st.session_state.current_quiz_state:
            all_answered = False
        else:
            if st.session_state.current_quiz_state[q_key]['correct']:
                correct_count += 1
        
        st.markdown("---")
    
    # Show results if all answered
    if all_answered:
        render_quiz_results(correct_count, total_questions, unit_idx, config)

def render_mcq_question(q_key: str, options: List[str], correct_answer: str):
    """Render multiple choice question"""
    user_answer = st.radio(
        "Select your answer:",
        options,
        key=f"{q_key}_input",
        label_visibility="collapsed"
    )
    
    if st.button("Check Answer", key=f"{q_key}_check"):
        is_correct = (user_answer == correct_answer)
        
        st.session_state.current_quiz_state[q_key] = {
            'answer': user_answer,
            'correct': is_correct
        }
        
        if is_correct:
            st.success("✅ Correct! Well done!")
        else:
            st.error(f"❌ Not quite. The correct answer is: **{correct_answer}**")
    
    # Show previous result if exists
    elif q_key in st.session_state.current_quiz_state:
        result = st.session_state.current_quiz_state[q_key]
        if result['correct']:
            st.success("✅ Correct!")
        else:
            st.error(f"❌ The correct answer is: **{correct_answer}**")

def render_tf_question(q_key: str, correct_answer: str):
    """Render True/False question"""
    user_answer = st.radio(
        "Select your answer:",
        ["True", "False"],
        key=f"{q_key}_input",
        label_visibility="collapsed"
    )
    
    if st.button("Check Answer", key=f"{q_key}_check"):
        is_correct = (user_answer == correct_answer)
        
        st.session_state.current_quiz_state[q_key] = {
            'answer': user_answer,
            'correct': is_correct
        }
        
        if is_correct:
            st.success("✅ Correct!")
        else:
            st.error(f"❌ The correct answer is: **{correct_answer}**")
    
    elif q_key in st.session_state.current_quiz_state:
        result = st.session_state.current_quiz_state[q_key]
        if result['correct']:
            st.success("✅ Correct!")
        else:
            st.error(f"❌ The correct answer is: **{correct_answer}**")

def render_fill_question(q_key: str, correct_answer: str):
    """Render fill-in-the-blank question"""
    user_answer = st.text_input(
        "Type your answer:",
        key=f"{q_key}_input",
        label_visibility="collapsed",
        placeholder="Type here..."
    )
    
    if st.button("Check Answer", key=f"{q_key}_check"):
        # Case-insensitive comparison
        is_correct = (user_answer.strip().lower() == correct_answer.strip().lower())
        
        st.session_state.current_quiz_state[q_key] = {
            'answer': user_answer,
            'correct': is_correct
        }
        
        if is_correct:
            st.success("✅ Correct!")
        else:
            st.error(f"❌ The correct answer is: **{correct_answer}**")
    
    elif q_key in st.session_state.current_quiz_state:
        result = st.session_state.current_quiz_state[q_key]
        if result['correct']:
            st.success("✅ Correct!")
        else:
            st.error(f"❌ The correct answer is: **{correct_answer}**")

def render_quiz_results(correct: int, total: int, unit_idx: int, config: Dict):
    """Show quiz results and award XP"""
    score_pct = (correct / total) * 100 if total > 0 else 0
    
    st.markdown("### 📊 Quiz Results")
    st.markdown(f"**Score: {correct}/{total} ({score_pct:.0f}%)**")
    
    # Get encouragement
    from src.student_mode.xp_system import get_encouragement, award_quiz_xp
    message = get_encouragement(score_pct)
    st.info(message)
    
    # Award XP button
    if st.button("Continue & Claim XP", type="primary", key="quiz_continue"):
        # Award XP
        award_quiz_xp(score_pct, config)
        
        # Update progress
        progress_data = StateManager.get_state('student_progress', {})
        progress_data['quizzes_completed'] = progress_data.get('quizzes_completed', 0) + 1
        
        if score_pct == 100:
            progress_data['perfect_quizzes'] = progress_data.get('perfect_quizzes', 0) + 1
        
        StateManager.update_state('student_progress', progress_data)
        
        # Save and advance
        from src.student_mode.progress_manager import save_student_progress
        from src.student_mode.student_ui import advance_section
        
        save_student_progress()
        
        # Clear quiz state
        st.session_state.current_quiz_state = {}
        
        advance_section()
        st.rerun()
```

#### 4.2 Update Quiz Import in student_ui.py

```python
# In render_current_section function
elif section_type == 'quiz':
    from src.student_mode.quiz_handler import render_quiz_section
    render_quiz_section(current_unit, unit_idx, config)
```

**Testing Phase 4**:
- Complete a quiz with all correct answers → verify perfect score bonus
- Complete a quiz with some wrong answers → verify partial XP
- Verify quiz state persists between reruns
- Test all question types (MCQ, TF, FILL)

---

### Phase 5: Polish & Optional Features (Day 3)

#### 5.1 Add Course Completion Screen

```python
def render_course_complete(curriculum: Dict):
    """Show completion celebration"""
    st.balloons()
    
    progress_data = StateManager.get_state('student_progress', {})
    meta = curriculum.get('meta', {})
    
    ModernUI.card(
        title="🏆 Course Complete!",
        content=f"""
        **Congratulations!** You've finished:
        
        **{meta.get('subject', 'Course')} - Grade {meta.get('grade', '?')}**
        
        ### 📊 Your Final Stats:
        - **Total XP**: {progress_data.get('total_xp', 0)}
        - **Final Level**: {progress_data.get('total_xp', 0) // 100}
        - **Quizzes Completed**: {progress_data.get('quizzes_completed', 0)}
        - **Perfect Scores**: {progress_data.get('perfect_quizzes', 0)}
        
        You're a learning superstar! 🌟
        """,
        icon="🎉",
        status="success"
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📜 View Progress Details", type="secondary"):
            show_progress_details()
    
    with col2:
        if st.button("🔄 Start New Course", type="primary"):
            # Reset selection
            StateManager.update_state('selected_curriculum', None)
            st.rerun()
```

#### 5.2 Add AI Tutor (Optional)

**File**: `src/student_mode/tutor.py`

```python
"""
AI Tutor Chatbot
Provides contextual help to students
"""

import streamlit as st
from typing import Dict, List

def render_tutor_widget(unit: Dict, meta: Dict, config: Dict, client):
    """Render AI tutor chat interface"""
    
    if not config.get('student_mode', {}).get('tutor_enabled', True):
        return
    
    with st.expander("🤖 Ask Your AI Tutor", expanded=False):
        st.markdown("""
        **Need help?** I'm here to assist!
        
        I can help you:
        - Understand difficult concepts
        - See examples
        - Review key points
        """)
        
        # Chat history
        if 'tutor_history' not in st.session_state:
            st.session_state.tutor_history = []
        
        # Display recent messages
        for msg in st.session_state.tutor_history[-5:]:
            if msg['role'] == 'user':
                st.markdown(f"**You:** {msg['content']}")
            else:
                st.markdown(f"**Tutor:** {msg['content']}")
        
        # Input
        question = st.text_input(
            "Ask a question:",
            key="tutor_input",
            placeholder="What would you like to know?"
        )
        
        if st.button("Ask", key="tutor_ask") and question:
            # Get response
            response = get_tutor_response(question, unit, meta, config, client)
            
            # Update history
            st.session_state.tutor_history.append({'role': 'user', 'content': question})
            st.session_state.tutor_history.append({'role': 'assistant', 'content': response})
            
            st.rerun()

def get_tutor_response(question: str, unit: Dict, meta: Dict, config: Dict, client):
    """Generate AI response"""
    context = f"""
    You are a friendly tutor helping a {meta.get('grade', '')} grade student 
    learn about {meta.get('subject', 'this topic')}.
    
    Current topic: {unit.get('title', 'Unknown')}
    
    Student's question: {question}
    
    Provide a clear, encouraging, age-appropriate answer in 2-3 short paragraphs.
    Use simple language and real-world examples.
    """
    
    try:
        response = client.chat.completions.create(
            model=config['defaults']['worker_model'],
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": question}
            ],
            max_tokens=300
        )
        
        return response.choices[0].message.content
    except:
        return "Sorry, I'm having trouble right now. Please ask your teacher for help!"
```

#### 5.3 Add Tutor to Content Sections

In `student_ui.py`, add after content rendering:

```python
def render_content(unit: Dict):
    """Render main content"""
    content = unit.get('content', 'No content available.')
    
    ModernUI.card(
        title="📖 Lesson Content",
        content="",
        icon="📚"
    )
    
    st.markdown(content, unsafe_allow_html=False)
    
    # Add tutor widget
    from src.student_mode.tutor import render_tutor_widget
    curriculum = StateManager.get_state('selected_curriculum', {})
    meta = curriculum.get('meta', {})
    config = st.session_state.get('config', {})
    client = st.session_state.get('client')
    
    if client:
        render_tutor_widget(unit, meta, config, client)
    
    render_navigation(section_type="content")
```

**Testing Phase 5**:
- Complete entire course → verify completion screen
- Test tutor chatbot with questions
- Verify tutor context is relevant to unit

---

## Final Integration Checklist

### Pre-Deployment
- [ ] Test with multiple curricula
- [ ] Test progress persistence across sessions
- [ ] Verify XP calculations are correct
- [ ] Test on mobile browser
- [ ] Check accessibility (keyboard navigation)
- [ ] Test with different grade levels

### Documentation
- [ ] Update README with Student Mode section
- [ ] Add student mode to CLAUDE.md
- [ ] Create user guide for students
- [ ] Document progress file format

### Performance
- [ ] Test with large curricula (10+ units)
- [ ] Optimize image loading
- [ ] Add loading states
- [ ] Handle API errors gracefully

---

## Troubleshooting Guide

### Issue: Progress not saving
**Solution**: Check file permissions in `curricula/` folder

### Issue: XP not updating in sidebar
**Solution**: Ensure `StateManager.update_state()` is being called

### Issue: Quiz state persists between units
**Solution**: Clear `current_quiz_state` in `advance_section()`

### Issue: Mode switch doesn't work
**Solution**: Check `st.stop()` is called after student mode rendering

---

## Success Metrics

### Phase 1 Success
- ✅ Mode switching works
- ✅ Curriculum selector populates
- ✅ Navigation advances sections

### Phase 2 Success
- ✅ XP awards on completion
- ✅ Level up triggers balloons
- ✅ Progress bar updates

### Phase 3 Success
- ✅ All content types display
- ✅ Images load correctly
- ✅ Charts render properly

### Phase 4 Success
- ✅ Quiz questions interactive
- ✅ Answer checking works
- ✅ XP awarded correctly
- ✅ Perfect score bonus works

### Phase 5 Success
- ✅ Course completion screen shows
- ✅ Tutor responds helpfully
- ✅ Mobile UI works well

---

## Next Steps After Implementation

1. **User Testing**: Have students test with real curricula
2. **Feedback Loop**: Collect student feedback on engagement
3. **Analytics**: Track completion rates, quiz scores
4. **Enhancements**: Add badges, streaks, certificates

---

**END OF IMPLEMENTATION GUIDE**

Good luck with implementation! 🚀
