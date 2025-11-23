# Student Mode UI/UX Design Specification
## InstaSchool Interactive Learning Experience

**Version**: 1.0  
**Date**: 2025-11-23  
**Status**: Design Complete - Ready for Implementation

---

## 1. Executive Summary

This document specifies the complete UI/UX design for InstaSchool's Student Mode - an engaging, gamified learning experience where students progress through curriculum units, earn experience points (XP), complete quizzes, and receive help from an AI tutor.

### Design Philosophy
- **Student-First**: All UI elements designed for learners, not teachers
- **Progressive Disclosure**: One section at a time to maintain focus
- **Immediate Feedback**: Instant responses to actions with visual rewards
- **Gamification**: XP system creates motivation and tracks progress
- **Accessibility**: Clear, age-appropriate interface for all grade levels

---

## 2. Mode Switching Architecture

### 2.1 Sidebar Mode Selector

**Location**: Top of sidebar, above all other controls  
**Component**: Radio button group with clear visual distinction

```python
# Streamlit Implementation
st.sidebar.markdown("## 🎓 InstaSchool")
st.sidebar.markdown("---")

mode = st.sidebar.radio(
    "Select Mode",
    ["👨‍🏫 Teacher (Create & Edit)", "🎒 Student (Learn & Practice)"],
    key="app_mode",
    help="Switch between creating curricula and learning from them"
)

# Store in state
StateManager.update_state('current_mode', 
    'teacher' if 'Teacher' in mode else 'student'
)
```

### 2.2 Mode-Specific UI Behavior

| UI Element | Teacher Mode | Student Mode |
|------------|-------------|--------------|
| Sidebar Settings | ✅ Visible | ❌ Hidden |
| Generate Tab | ✅ Visible | ❌ Hidden |
| Edit Controls | ✅ Visible | ❌ Hidden |
| Export Tab | ✅ Visible | ❌ Hidden |
| Templates Tab | ✅ Visible | ❌ Hidden |
| Student Dashboard | ❌ Hidden | ✅ Visible |
| Progress Tracking | ❌ Hidden | ✅ Visible |
| XP System | ❌ Hidden | ✅ Visible |
| Tutor Chat | ❌ Hidden | ✅ Visible (optional) |

---

## 3. Student Mode Interface Structure

### 3.1 Layout Hierarchy

```
┌─────────────────────────────────────────────────────────┐
│ SIDEBAR                                                 │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 🎓 InstaSchool                                     │ │
│ │ Mode: 🎒 Student                                   │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ XP Progress                                        │ │
│ │ ⭐ Level 3                                         │ │
│ │ 245/300 XP                                         │ │
│ │ [=========>    ] 82%                               │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ Select Curriculum                                  │ │
│ │ [Dropdown Menu]                                    │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ Course Progress                                    │ │
│ │ Unit 1: ✅ Complete                                │ │
│ │ Unit 2: ✅ Complete                                │ │
│ │ Unit 3: 📖 Current                                 │ │
│ │ Unit 4: 🔒 Locked                                  │ │
│ └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ MAIN CONTENT AREA                                       │
│ ┌────────────────────────────────────────────────────┐ │
│ │ [Subject] Curriculum - Grade [X]                   │ │
│ │ Overall Progress: [==========>   ] 67% Complete    │ │
│ ├────────────────────────────────────────────────────┤ │
│ │                                                    │ │
│ │ CURRENT SECTION CARD                               │ │
│ │ (One at a time - changes based on progress)        │ │
│ │                                                    │ │
│ │ Options:                                           │ │
│ │ - Introduction & Title                             │ │
│ │ - Illustration                                     │ │
│ │ - Main Content                                     │ │
│ │ - Chart (if available)                             │ │
│ │ - Quiz                                             │ │
│ │ - Summary                                          │ │
│ │                                                    │ │
│ ├────────────────────────────────────────────────────┤ │
│ │ NAVIGATION                                         │ │
│ │ [← Previous]     [Mark Complete]      [Next →]    │ │
│ └────────────────────────────────────────────────────┘ │
│                                                         │
│ ┌────────────────────────────────────────────────────┐ │
│ │ 🤖 Tutor Assistant (Collapsible)                   │ │
│ │ [Chat interface here]                              │ │
│ └────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Detailed Component Specifications

### 4.1 XP Progress Display (Sidebar)

**Purpose**: Show student's current level, XP, and progress to next level

**Visual Design**:
```
┌──────────────────────────────────┐
│ ⭐ Level 3                       │
│ 245/300 XP to Level 4            │
│ ┌──────────────────────────────┐ │
│ │████████████████░░░░░░░░░░░░░░│ │
│ └──────────────────────────────┘ │
│ 82% Complete                     │
└──────────────────────────────────┘
```

**Component Implementation**:
```python
def render_xp_progress():
    """Render XP progress widget in sidebar"""
    progress_data = StateManager.get_state('student_progress', {})
    total_xp = progress_data.get('total_xp', 0)
    
    # Calculate level and progress
    xp_per_level = config['student_mode']['xp_per_level']
    current_level = total_xp // xp_per_level
    xp_in_level = total_xp % xp_per_level
    progress_pct = xp_in_level / xp_per_level
    
    # Render with ModernUI
    st.sidebar.markdown("### 🎯 Your Progress")
    
    ModernUI.stats_card(
        value=f"Level {current_level}",
        label=f"{xp_in_level}/{xp_per_level} XP",
        icon="⭐",
        key="student_xp"
    )
    
    st.sidebar.progress(progress_pct, text=f"{int(progress_pct*100)}% to Level {current_level + 1}")
```

**State Variables**:
- `student_progress.total_xp`: Total XP earned
- `student_progress.current_level`: Calculated from total_xp

---

### 4.2 Curriculum Selector (Sidebar)

**Purpose**: Allow student to select which curriculum to study

**Design**:
```python
def render_curriculum_selector():
    """Render curriculum selection dropdown"""
    # Get available curricula
    curricula_files = list(Path("curricula").glob("*.json"))
    
    if not curricula_files:
        st.sidebar.warning("No curricula available. Ask your teacher to create one!")
        return None
    
    # Load metadata for each curriculum
    curriculum_options = []
    for file in curricula_files:
        try:
            with open(file, 'r') as f:
                data = json.load(f)
                meta = data.get('meta', {})
                label = f"{meta.get('subject', 'Unknown')} - Grade {meta.get('grade', '?')}"
                curriculum_options.append((label, file.name, data))
        except:
            continue
    
    if not curriculum_options:
        st.sidebar.error("No valid curricula found")
        return None
    
    # Selection dropdown
    selected_idx = st.sidebar.selectbox(
        "📚 Choose Your Lesson",
        range(len(curriculum_options)),
        format_func=lambda i: curriculum_options[i][0],
        key="student_curriculum_selector"
    )
    
    selected_curriculum = curriculum_options[selected_idx][2]
    selected_filename = curriculum_options[selected_idx][1]
    
    # Load or initialize progress for this curriculum
    load_student_progress(selected_filename)
    
    return selected_curriculum
```

---

### 4.3 Unit Progress Overview (Sidebar)

**Purpose**: Show completion status of all units at a glance

**Visual Design**:
```
Course Progress
───────────────
✅ Unit 1: Introduction to Cells
✅ Unit 2: Cell Structure
📖 Unit 3: Cell Functions (Current)
🔒 Unit 4: Cell Division (Locked)
🔒 Unit 5: Advanced Topics (Locked)
```

**Implementation**:
```python
def render_unit_progress_sidebar(curriculum):
    """Show unit completion status in sidebar"""
    st.sidebar.markdown("### 📊 Course Progress")
    
    progress_data = StateManager.get_state('student_progress', {})
    completed_units = progress_data.get('completed_units', [])
    current_section = progress_data.get('current_section_index', 0)
    
    units = curriculum.get('units', [])
    
    # Calculate which unit we're currently in
    sections_per_unit = 6  # intro, image, content, chart, quiz, summary
    current_unit_idx = current_section // sections_per_unit
    
    for idx, unit in enumerate(units):
        title = unit.get('title', f'Unit {idx+1}')
        
        if idx < current_unit_idx:
            # Completed
            icon = "✅"
            status = "Complete"
            color = "#10b981"
        elif idx == current_unit_idx:
            # Current
            icon = "📖"
            status = "In Progress"
            color = "#3b82f6"
        else:
            # Locked
            icon = "🔒"
            status = "Locked"
            color = "#9ca3af"
        
        st.sidebar.markdown(
            f'<div style="color: {color};">{icon} <b>Unit {idx+1}:</b> {title[:30]}...</div>',
            unsafe_allow_html=True
        )
```

---

### 4.4 Section Card Display (Main Content)

**Purpose**: Display one learning section at a time with clear visual hierarchy

**Section Types**:
1. **Introduction** - Unit title, description
2. **Illustration** - Educational image
3. **Main Content** - Lesson text with markdown
4. **Chart** - Data visualization (if available)
5. **Quiz** - Interactive assessment
6. **Summary** - Key takeaways

**Card Structure**:
```python
def render_current_section(curriculum):
    """Render the current section based on progress"""
    progress_data = StateManager.get_state('student_progress', {})
    section_idx = progress_data.get('current_section_index', 0)
    
    units = curriculum.get('units', [])
    sections_per_unit = 6
    
    unit_idx = section_idx // sections_per_unit
    section_type_idx = section_idx % sections_per_unit
    
    if unit_idx >= len(units):
        render_course_complete()
        return
    
    current_unit = units[unit_idx]
    
    # Map section types
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
        render_introduction_section(current_unit, unit_idx)
    elif section_type == 'illustration':
        render_illustration_section(current_unit)
    elif section_type == 'content':
        render_content_section(current_unit)
    elif section_type == 'chart':
        render_chart_section(current_unit)
    elif section_type == 'quiz':
        render_quiz_section(current_unit, unit_idx)
    elif section_type == 'summary':
        render_summary_section(current_unit)
```

---

### 4.5 Section Examples

#### 4.5.1 Introduction Section

```python
def render_introduction_section(unit, unit_idx):
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
    
    # Navigation
    render_section_navigation(can_go_back=False)
```

#### 4.5.2 Illustration Section

```python
def render_illustration_section(unit):
    """Render educational illustration"""
    image_b64 = unit.get('selected_image_b64')
    
    if image_b64:
        ModernUI.card(
            title="📸 Visual Learning",
            content="",
            icon="🎨"
        )
        
        st.image(
            f"data:image/png;base64,{image_b64}",
            caption=unit.get('title', 'Illustration'),
            use_container_width=True
        )
        
        st.info("💡 Study this illustration carefully. It will help you understand the concepts better!")
    else:
        st.info("No illustration available for this section. Moving on...")
        # Auto-advance
        advance_section()
    
    render_section_navigation()
```

#### 4.5.3 Content Section

```python
def render_content_section(unit):
    """Render main lesson content"""
    content = unit.get('content', 'No content available.')
    
    ModernUI.card(
        title="📖 Lesson Content",
        content="",
        icon="📚"
    )
    
    # Render markdown content
    st.markdown(content, unsafe_allow_html=False)
    
    # Optional: Read-aloud button if TTS is enabled
    if config.get('tts', {}).get('enabled', False):
        if st.button("🔊 Read Aloud", key="tts_content"):
            generate_and_play_audio(content)
    
    render_section_navigation()
```

#### 4.5.4 Quiz Section

```python
def render_quiz_section(unit, unit_idx):
    """Render interactive quiz"""
    quiz_data = unit.get('quiz', [])
    
    if not quiz_data:
        st.info("No quiz for this unit. Moving on...")
        advance_section()
        return
    
    ModernUI.card(
        title="✏️ Check Your Understanding",
        content="Answer the questions below to test what you've learned!",
        icon="🎯",
        status="warning"
    )
    
    # Track quiz state
    if 'current_quiz_answers' not in st.session_state:
        st.session_state.current_quiz_answers = {}
    
    all_answered = True
    correct_count = 0
    
    for q_idx, question in enumerate(quiz_data):
        q_key = f"unit_{unit_idx}_q_{q_idx}"
        
        st.markdown(f"#### Question {q_idx + 1}")
        st.markdown(f"**{question.get('question')}**")
        
        q_type = question.get('type')
        options = question.get('options', [])
        correct_answer = question.get('answer')
        
        # Render question based on type
        if q_type == "MCQ":
            user_answer = st.radio(
                f"Select your answer:",
                options,
                key=f"{q_key}_answer",
                label_visibility="collapsed"
            )
            
            if st.button(f"Check Answer", key=f"{q_key}_check"):
                is_correct = (user_answer == correct_answer)
                st.session_state.current_quiz_answers[q_key] = {
                    'answer': user_answer,
                    'correct': is_correct
                }
                
                if is_correct:
                    st.success("✅ Correct! Well done!")
                else:
                    st.error(f"❌ Not quite. The correct answer is: **{correct_answer}**")
        
        elif q_type == "TF":
            user_answer = st.radio(
                "Select your answer:",
                ["True", "False"],
                key=f"{q_key}_answer",
                label_visibility="collapsed"
            )
            
            if st.button("Check Answer", key=f"{q_key}_check"):
                is_correct = (user_answer == correct_answer)
                st.session_state.current_quiz_answers[q_key] = {
                    'answer': user_answer,
                    'correct': is_correct
                }
                
                if is_correct:
                    st.success("✅ Correct!")
                else:
                    st.error(f"❌ Incorrect. The answer is: **{correct_answer}**")
        
        # Check if answered
        if q_key not in st.session_state.current_quiz_answers:
            all_answered = False
        else:
            if st.session_state.current_quiz_answers[q_key]['correct']:
                correct_count += 1
        
        st.markdown("---")
    
    # Show quiz summary and award XP
    if all_answered:
        score_pct = (correct_count / len(quiz_data)) * 100
        
        st.markdown(f"### 📊 Quiz Results")
        st.markdown(f"You got **{correct_count}/{len(quiz_data)}** correct ({score_pct:.0f}%)")
        
        # Award XP
        xp_earned = config['student_mode']['xp_per_quiz']
        if score_pct == 100:
            xp_earned += config['student_mode']['xp_perfect_bonus']
            st.balloons()  # Celebration!
            st.success(f"🎉 Perfect score! You earned {xp_earned} XP (including {config['student_mode']['xp_perfect_bonus']} bonus points)!")
        else:
            st.info(f"Good effort! You earned {xp_earned} XP")
        
        # Add XP to student progress
        add_xp(xp_earned)
        
        # Clear quiz state
        st.session_state.current_quiz_answers = {}
        
        # Continue button
        if st.button("Continue to Next Section →", type="primary"):
            advance_section()
            st.rerun()
```

---

### 4.6 Navigation System

**Purpose**: Allow students to move between sections with clear feedback

```python
def render_section_navigation(can_go_back=True):
    """Render navigation buttons for sections"""
    progress_data = StateManager.get_state('student_progress', {})
    current_idx = progress_data.get('current_section_index', 0)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if can_go_back and current_idx > 0:
            if st.button("← Previous", key="nav_prev"):
                StateManager.update_state(
                    'student_progress',
                    {**progress_data, 'current_section_index': current_idx - 1}
                )
                st.rerun()
    
    with col2:
        if st.button("✅ Mark Complete & Continue", type="primary", key="nav_complete"):
            # Award XP for section completion
            xp_earned = config['student_mode']['xp_per_section']
            add_xp(xp_earned)
            
            st.success(f"+{xp_earned} XP!")
            time.sleep(0.5)
            
            # Advance to next section
            advance_section()
            st.rerun()
    
    with col3:
        # Next button (without marking complete)
        if st.button("Skip →", key="nav_skip", help="Skip without earning XP"):
            advance_section()
            st.rerun()

def advance_section():
    """Move to the next section"""
    progress_data = StateManager.get_state('student_progress', {})
    current_idx = progress_data.get('current_section_index', 0)
    
    StateManager.update_state(
        'student_progress',
        {**progress_data, 'current_section_index': current_idx + 1}
    )
```

---

### 4.7 XP System Logic

**Purpose**: Track and reward student progress

```python
def add_xp(amount):
    """Add XP to student's total and update level"""
    progress_data = StateManager.get_state('student_progress', {})
    current_xp = progress_data.get('total_xp', 0)
    new_xp = current_xp + amount
    
    # Check for level up
    xp_per_level = config['student_mode']['xp_per_level']
    old_level = current_xp // xp_per_level
    new_level = new_xp // xp_per_level
    
    if new_level > old_level:
        st.balloons()
        st.success(f"🎉 LEVEL UP! You're now Level {new_level}!")
    
    # Update progress
    progress_data['total_xp'] = new_xp
    StateManager.update_state('student_progress', progress_data)
    
    # Save to file
    save_student_progress()

def calculate_xp_breakdown():
    """Calculate XP sources for display"""
    progress_data = StateManager.get_state('student_progress', {})
    
    sections_completed = progress_data.get('sections_completed', 0)
    quizzes_completed = progress_data.get('quizzes_completed', 0)
    perfect_quizzes = progress_data.get('perfect_quizzes', 0)
    
    xp_from_sections = sections_completed * config['student_mode']['xp_per_section']
    xp_from_quizzes = quizzes_completed * config['student_mode']['xp_per_quiz']
    xp_from_bonuses = perfect_quizzes * config['student_mode']['xp_perfect_bonus']
    
    return {
        'sections': xp_from_sections,
        'quizzes': xp_from_quizzes,
        'bonuses': xp_from_bonuses,
        'total': xp_from_sections + xp_from_quizzes + xp_from_bonuses
    }
```

---

### 4.8 Progress Persistence

**Purpose**: Save and load student progress per curriculum

```python
def save_student_progress():
    """Save progress to JSON file"""
    progress_data = StateManager.get_state('student_progress', {})
    curriculum_file = progress_data.get('curriculum_file')
    
    if not curriculum_file:
        return
    
    # Create progress filename
    progress_file = Path("curricula") / f"progress_{curriculum_file}"
    
    try:
        with open(progress_file, 'w') as f:
            json.dump(progress_data, f, indent=2)
    except Exception as e:
        st.error(f"Error saving progress: {e}")

def load_student_progress(curriculum_file):
    """Load progress from JSON file"""
    progress_file = Path("curricula") / f"progress_{curriculum_file}"
    
    if progress_file.exists():
        try:
            with open(progress_file, 'r') as f:
                progress_data = json.load(f)
            StateManager.update_state('student_progress', progress_data)
            return progress_data
        except Exception as e:
            st.error(f"Error loading progress: {e}")
    
    # Initialize new progress
    initial_progress = {
        'curriculum_file': curriculum_file,
        'current_section_index': 0,
        'total_xp': 0,
        'sections_completed': 0,
        'quizzes_completed': 0,
        'perfect_quizzes': 0,
        'quiz_scores': {},
        'completed_sections': []
    }
    
    StateManager.update_state('student_progress', initial_progress)
    save_student_progress()
    
    return initial_progress
```

---

### 4.9 AI Tutor Assistant (Optional)

**Purpose**: Provide contextual help and answer questions

```python
def render_tutor_assistant(curriculum, current_unit):
    """Render collapsible AI tutor chat interface"""
    if not config.get('student_mode', {}).get('tutor_enabled', True):
        return
    
    with st.expander("🤖 Ask Your AI Tutor", expanded=False):
        st.markdown("""
        Stuck on something? Ask me for help! I can:
        - Explain concepts in simpler terms
        - Provide examples
        - Answer your questions about the lesson
        """)
        
        # Initialize chat history
        if 'tutor_history' not in st.session_state:
            st.session_state.tutor_history = []
        
        # Display chat history
        for msg in st.session_state.tutor_history[-5:]:  # Last 5 messages
            role = msg['role']
            content = msg['content']
            
            if role == 'user':
                st.markdown(f"**You:** {content}")
            else:
                st.markdown(f"**Tutor:** {content}")
        
        # Input area
        user_question = st.text_input(
            "Ask a question:",
            key="tutor_input",
            placeholder="What would you like to know?"
        )
        
        if st.button("Ask", key="tutor_ask") and user_question:
            # Add to history
            st.session_state.tutor_history.append({
                'role': 'user',
                'content': user_question
            })
            
            # Get AI response
            tutor_response = get_tutor_response(
                user_question,
                current_unit,
                curriculum.get('meta', {})
            )
            
            st.session_state.tutor_history.append({
                'role': 'assistant',
                'content': tutor_response
            })
            
            st.rerun()

def get_tutor_response(question, unit, metadata):
    """Generate AI tutor response"""
    context = f"""
    You are a friendly, encouraging tutor helping a {metadata.get('grade', 'student')} 
    grade student learn about {metadata.get('subject', 'this topic')}.
    
    Current topic: {unit.get('title', 'Unknown')}
    
    Student's question: {question}
    
    Provide a clear, age-appropriate answer that:
    - Uses simple language
    - Encourages the student
    - Relates to real-world examples
    - Keeps the response concise (2-3 paragraphs max)
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
    except Exception as e:
        return "I'm sorry, I'm having trouble right now. Please try asking your teacher!"
```

---

## 5. State Management Schema

### 5.1 Required State Variables

```python
# Student Mode State Structure
student_progress = {
    # Identification
    'curriculum_file': str,          # Filename of current curriculum
    'student_id': str,               # Optional student identifier
    
    # Progress Tracking
    'current_section_index': int,    # Current position (0-based)
    'completed_sections': List[int], # List of completed section indices
    
    # XP System
    'total_xp': int,                 # Total XP earned
    'sections_completed': int,       # Count of sections finished
    'quizzes_completed': int,        # Count of quizzes finished
    'perfect_quizzes': int,          # Count of 100% quiz scores
    
    # Quiz Results
    'quiz_scores': {                 # Dict of quiz results
        'unit_0_quiz': {
            'score': float,          # Percentage (0-100)
            'correct': int,          # Correct answers
            'total': int,            # Total questions
            'timestamp': str         # ISO format datetime
        }
    },
    
    # Timestamps
    'started_at': str,               # ISO format
    'last_updated': str,             # ISO format
    'completed_at': str              # ISO format (when course finished)
}
```

### 5.2 State Update Functions

```python
def update_section_completion(section_idx):
    """Mark a section as completed"""
    progress = StateManager.get_state('student_progress', {})
    
    if section_idx not in progress.get('completed_sections', []):
        progress.setdefault('completed_sections', []).append(section_idx)
        progress['sections_completed'] = progress.get('sections_completed', 0) + 1
        progress['last_updated'] = datetime.now().isoformat()
        
        StateManager.update_state('student_progress', progress)
        save_student_progress()

def update_quiz_completion(unit_idx, score_pct, correct, total):
    """Record quiz completion"""
    progress = StateManager.get_state('student_progress', {})
    
    quiz_key = f"unit_{unit_idx}_quiz"
    progress.setdefault('quiz_scores', {})[quiz_key] = {
        'score': score_pct,
        'correct': correct,
        'total': total,
        'timestamp': datetime.now().isoformat()
    }
    
    progress['quizzes_completed'] = progress.get('quizzes_completed', 0) + 1
    
    if score_pct == 100:
        progress['perfect_quizzes'] = progress.get('perfect_quizzes', 0) + 1
    
    progress['last_updated'] = datetime.now().isoformat()
    
    StateManager.update_state('student_progress', progress)
    save_student_progress()
```

---

## 6. User Flow Diagram

```
START: Student Mode Entry
    ↓
┌───────────────────────────────────┐
│ Select Mode: Student              │
└───────────────────────────────────┘
    ↓
┌───────────────────────────────────┐
│ Select Curriculum from Dropdown   │
└───────────────────────────────────┘
    ↓
┌───────────────────────────────────┐
│ Load/Initialize Progress          │
└───────────────────────────────────┘
    ↓
    ├─── Has Previous Progress?
    │    ├─ YES → Resume from saved position
    │    └─ NO  → Start from beginning
    ↓
┌───────────────────────────────────┐
│ Display Current Section           │
│ (Introduction, Content, etc.)     │
└───────────────────────────────────┘
    ↓
┌───────────────────────────────────┐
│ Student Reads/Views Content       │
└───────────────────────────────────┘
    ↓
    ├─── Section Type?
    │    ├─ Quiz → Complete Quiz → Award XP
    │    ├─ Content → Read → Award XP
    │    └─ Image → View → Award XP
    ↓
┌───────────────────────────────────┐
│ Mark Complete & Continue          │
│ OR Skip to Next                   │
└───────────────────────────────────┘
    ↓
    ├─── More Sections?
    │    ├─ YES → Loop to next section
    │    └─ NO  → Course Complete!
    ↓
┌───────────────────────────────────┐
│ Show Completion Certificate       │
│ Final XP Total                    │
│ Achievement Badges                │
└───────────────────────────────────┘
    ↓
END
```

---

## 7. Celebration & Feedback Moments

### 7.1 Achievement Triggers

| Event | Celebration | Message |
|-------|-------------|---------|
| Level Up | `st.balloons()` | "🎉 LEVEL UP! You're now Level X!" |
| Perfect Quiz | `st.balloons()` | "🎉 Perfect Score! +XX XP Bonus!" |
| Unit Complete | `st.success()` | "✅ Unit Complete! Great job!" |
| Course Complete | `st.balloons()` + Special UI | "🏆 Congratulations! Course Complete!" |
| First Quiz | `st.info()` | "💪 First quiz complete! You're on your way!" |

### 7.2 Encouragement Messages

```python
def get_encouragement_message(score_pct):
    """Get encouraging message based on quiz score"""
    if score_pct == 100:
        return random.choice([
            "🌟 Perfect! You're a star!",
            "🎯 Bullseye! Amazing work!",
            "💯 Outstanding! You nailed it!"
        ])
    elif score_pct >= 80:
        return random.choice([
            "👍 Great job! You really know this!",
            "🎉 Excellent work! Keep it up!",
            "⭐ Super! You're doing amazing!"
        ])
    elif score_pct >= 60:
        return random.choice([
            "👏 Good effort! You're learning!",
            "💪 Nice try! Keep practicing!",
            "🌱 You're growing! Keep going!"
        ])
    else:
        return random.choice([
            "💪 Don't give up! Review the lesson and try again!",
            "🌟 Learning takes time! You've got this!",
            "📚 Take your time to understand. Ask the tutor for help!"
        ])
```

---

## 8. Responsive Design Considerations

### 8.1 Mobile Adaptations

- **Sidebar**: Collapsible on mobile, toggle button at top
- **Navigation Buttons**: Stack vertically on small screens
- **XP Progress**: Condensed display on mobile
- **Quiz Options**: Full-width radio buttons
- **Images**: Always full-width with appropriate sizing

### 8.2 Accessibility

- **Font Sizes**: Minimum 16px for body text
- **Color Contrast**: WCAG AA compliance
- **Keyboard Navigation**: All interactive elements keyboard-accessible
- **Screen Readers**: Proper ARIA labels on all components
- **Focus Indicators**: Clear visual focus states

---

## 9. Implementation Checklist

### Phase 1: Core Structure
- [ ] Mode selector in sidebar
- [ ] Student mode state initialization
- [ ] Curriculum selector
- [ ] Progress tracking system
- [ ] Section navigation logic

### Phase 2: XP System
- [ ] XP calculation functions
- [ ] Level up detection
- [ ] XP display in sidebar
- [ ] Progress bar animation
- [ ] Achievement celebrations

### Phase 3: Content Display
- [ ] Introduction card
- [ ] Illustration display
- [ ] Content rendering
- [ ] Chart display
- [ ] Summary display

### Phase 4: Quiz System
- [ ] MCQ rendering
- [ ] True/False questions
- [ ] Fill-in-blank questions
- [ ] Answer checking
- [ ] Score calculation
- [ ] XP rewards

### Phase 5: Progress Persistence
- [ ] Save progress to JSON
- [ ] Load progress on startup
- [ ] Resume from saved position
- [ ] Progress file management

### Phase 6: Polish
- [ ] Tutor chatbot integration
- [ ] Celebration animations
- [ ] Mobile responsiveness
- [ ] Error handling
- [ ] User testing

---

## 10. Technical Implementation Notes

### 10.1 File Structure

```
src/
├── student_mode/
│   ├── __init__.py
│   ├── student_ui.py          # Main student UI components
│   ├── xp_system.py            # XP calculation & tracking
│   ├── quiz_handler.py         # Quiz rendering & scoring
│   ├── progress_manager.py     # Save/load progress
│   └── tutor.py                # AI tutor chatbot
```

### 10.2 Integration Points

1. **main.py**: Add mode selector and conditional rendering
2. **StateManager**: Extend with student progress methods
3. **config.yaml**: Student mode settings already present
4. **ModernUI**: Reuse existing card components

### 10.3 Performance Considerations

- Lazy load curriculum data
- Cache tutor responses
- Debounce progress saves (every 30s or on action)
- Optimize image loading

---

## 11. Future Enhancements

### 11.1 Short-term (v1.1)
- Streaks (daily learning streaks)
- Achievement badges
- Progress reports for teachers
- Multi-student support

### 11.2 Long-term (v2.0)
- Adaptive learning paths
- Social features (leaderboards)
- Custom avatar system
- Certificate generation

---

## 12. Appendix: Sample Screenshots

### A. XP Progress Widget
```
┌──────────────────────────────────┐
│ 🎯 Your Progress                 │
│                                  │
│ ⭐ Level 3                       │
│ 245/300 XP                       │
│                                  │
│ [████████████████░░░░░░░░░░░░░░] │
│ 82% to Level 4                   │
└──────────────────────────────────┘
```

### B. Quiz Interface
```
┌──────────────────────────────────┐
│ ✏️ Check Your Understanding      │
│                                  │
│ Question 1                       │
│ What is photosynthesis?          │
│                                  │
│ ○ Animal breathing               │
│ ● Plants making food             │
│ ○ Water cycle                    │
│ ○ Cell division                  │
│                                  │
│ [Check Answer]                   │
│                                  │
│ ✅ Correct! Well done!           │
│ +10 XP                           │
└──────────────────────────────────┘
```

### C. Completion Celebration
```
┌──────────────────────────────────┐
│ 🏆 Course Complete!              │
│                                  │
│ Congratulations! You finished:   │
│ Biology - Grade 3                │
│                                  │
│ 📊 Your Stats:                   │
│ • Total XP: 520                  │
│ • Final Level: 5                 │
│ • Quizzes: 8/8 (100%)            │
│ • Perfect Scores: 5              │
│                                  │
│ [View Certificate] [Start New]   │
└──────────────────────────────────┘
```

---

## END OF SPECIFICATION

**Status**: ✅ Design Complete  
**Next Steps**: Begin implementation with Phase 1  
**Estimated Development Time**: 2-3 days for full implementation  
**Priority**: High - Key differentiator for student engagement
