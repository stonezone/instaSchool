"""Student Mode UI - Interactive learning interface"""

import streamlit as st
import json
from pathlib import Path
from typing import Dict, Any, Optional
from .progress_manager import StudentProgress


def render_student_mode(config: Dict[str, Any], client: Any):
    """
    Main student mode interface
    
    Args:
        config: Application configuration
        client: OpenAI client instance
    """
    
    # Sidebar - Student Progress
    st.sidebar.markdown("### 🎯 Your Progress")
    
    # Get available curricula
    curricula_path = Path("curricula")
    curriculum_files = [f for f in curricula_path.glob("*.json") 
                       if not f.name.startswith('progress_')]
    
    if not curriculum_files:
        st.info("📚 No curricula available yet!")
        st.markdown("Switch to **Teacher Mode** to create your first curriculum.")
        return
    
    # Load curriculum options
    curriculum_options = []
    for file in curriculum_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                meta = data.get('meta', {})
                curriculum_options.append({
                    'file': file,
                    'data': data,
                    'title': f"{meta.get('subject', 'Unknown')} - Grade {meta.get('grade', '?')}",
                    'id': file.stem
                })
        except (json.JSONDecodeError, IOError):
            continue
    
    if not curriculum_options:
        st.error("No valid curricula found.")
        return
    
    # Curriculum selector in sidebar
    st.sidebar.markdown("**📚 Choose Your Lesson**")
    selected_idx = st.sidebar.selectbox(
        "Select curriculum",
        range(len(curriculum_options)),
        format_func=lambda i: curriculum_options[i]['title'],
        label_visibility="collapsed",
        key="student_curriculum_selector"
    )
    
    selected_curriculum = curriculum_options[selected_idx]
    curriculum = selected_curriculum['data']
    curriculum_id = selected_curriculum['id']
    
    # Initialize progress tracker
    progress = StudentProgress(curriculum_id)
    
    # Display progress in sidebar
    current_level = progress.get_level()
    current_xp = progress.get_xp()
    xp_in_level = current_xp % 100
    xp_to_next = 100 - xp_in_level
    
    st.sidebar.markdown(f"⭐ **Level {current_level}**")
    st.sidebar.markdown(f"🎯 {current_xp} XP ({xp_in_level}/100 to Level {current_level + 1})")
    st.sidebar.progress(xp_in_level / 100.0)
    st.sidebar.markdown("---")
    
    # Main area - Header
    meta = curriculum.get('meta', {})
    st.markdown(f"# 🎓 {meta.get('subject', 'Curriculum')}")
    st.markdown(f"*Grade {meta.get('grade', '?')} • {meta.get('style', 'Standard')} Style*")
    st.markdown("---")
    
    # Get current section
    section_idx = progress.get_current_section()
    units = curriculum.get('units', [])
    
    if not units:
        st.warning("This curriculum has no units yet.")
        return
    
    # Calculate total sections (6 per unit: intro, image, content, chart, quiz, summary)
    total_sections = len(units) * 6
    
    # Check if course is complete
    if section_idx >= total_sections:
        st.success("🏆 **Congratulations! Course Complete!**")
        st.balloons()
        st.markdown(f"### Final Stats")
        st.markdown(f"- **Level Reached**: {current_level}")
        st.markdown(f"- **Total XP**: {current_xp}")
        st.markdown(f"- **Units Completed**: {len(units)}")
        
        if st.button("🔄 Start Over"):
            progress.reset_progress()
            st.rerun()
        return
    
    # Determine current unit and section type
    unit_idx = section_idx // 6
    section_type_idx = section_idx % 6
    section_types = ['intro', 'image', 'content', 'chart', 'quiz', 'summary']
    current_section_type = section_types[section_type_idx]
    
    if unit_idx >= len(units):
        st.error("Invalid unit index. Resetting progress.")
        progress.reset_progress()
        st.rerun()
        return
    
    unit = units[unit_idx]
    
    # Display current progress
    progress_percent = (section_idx / total_sections) * 100
    st.progress(progress_percent / 100.0, text=f"Progress: {progress_percent:.1f}%")
    
    # Unit header
    st.markdown(f"## 📖 Unit {unit_idx + 1}: {unit.get('title', 'Untitled')}")
    st.markdown(f"*Section {section_type_idx + 1} of 6: {current_section_type.title()}*")
    st.markdown("---")
    
    # Display content based on section type
    _render_section_content(unit, current_section_type)
    
    st.markdown("---")
    
    # Navigation buttons
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col1:
        if section_idx > 0:
            if st.button("⬅️ Previous", use_container_width=True):
                progress.previous_section()
                st.rerun()
    
    with col2:
        if st.button("✅ Complete & Continue", type="primary", use_container_width=True):
            # Award XP
            leveled_up = progress.add_xp(10)
            progress.advance_section()
            
            if leveled_up:
                st.success(f"🎉 Level Up! You're now Level {progress.get_level()}!")
                st.balloons()
            else:
                st.success("+10 XP!")
            
            st.rerun()
    
    with col3:
        if st.button("Skip ⏭️", use_container_width=True):
            progress.advance_section()
            st.rerun()


def _render_section_content(unit: Dict[str, Any], section_type: str):
    """
    Render content for a specific section type
    
    Args:
        unit: Unit data dictionary
        section_type: Type of section (intro, image, content, chart, quiz, summary)
    """
    
    if section_type == 'intro':
        st.markdown("### 🚀 Welcome to this Unit!")
        st.info(f"**Topic**: {unit.get('title', 'Untitled')}")
        st.markdown("Get ready to learn something amazing!")
        
        # Show topic preview
        topic_content = unit.get('content', '')
        if topic_content:
            # Extract first paragraph as preview
            preview = topic_content.split('\n\n')[0][:200]
            st.markdown(f"**Preview**: {preview}...")
    
    elif section_type == 'image':
        st.markdown("### 🖼️ Visual Learning")
        img_b64 = unit.get('selected_image_b64')
        if img_b64:
            st.image(f"data:image/png;base64,{img_b64}", use_container_width=True)
            caption = unit.get('selected_image_prompt', '')
            if caption:
                st.caption(caption)
        else:
            st.info("No image available for this section.")
    
    elif section_type == 'content':
        st.markdown("### 📚 Lesson Content")
        content = unit.get('content', '')
        if content:
            st.markdown(content)
        else:
            st.warning("No content available for this section.")
    
    elif section_type == 'chart':
        st.markdown("### 📊 Data & Visualization")
        chart = unit.get('chart', {})
        chart_b64 = chart.get('b64')
        
        if chart_b64:
            st.image(f"data:image/png;base64,{chart_b64}", use_container_width=True)
            chart_desc = chart.get('description', '')
            if chart_desc:
                st.markdown(chart_desc)
        else:
            st.info("No chart available for this section.")
    
    elif section_type == 'quiz':
        st.markdown("### 🎯 Knowledge Check")
        quiz_data = unit.get('quiz', {})
        
        if quiz_data and isinstance(quiz_data, dict):
            questions = quiz_data.get('questions', [])
            
            if questions:
                st.markdown("**Quiz questions will be interactive in Phase 3!**")
                st.markdown("For now, here's what you'll be tested on:")
                
                for i, q in enumerate(questions, 1):
                    with st.expander(f"Question {i}"):
                        st.markdown(f"**{q.get('question', '')}**")
                        options = q.get('options', [])
                        for opt in options:
                            st.markdown(f"- {opt}")
                        st.caption(f"Correct answer: {q.get('correct', 'Not specified')}")
            else:
                st.info("No quiz questions available.")
        else:
            st.info("No quiz available for this section.")
    
    elif section_type == 'summary':
        st.markdown("### 📝 Summary & Key Takeaways")
        summary = unit.get('summary', '')
        
        if summary:
            st.markdown(summary)
            
            # Add resources if available
            resources = unit.get('resources', {})
            if resources:
                st.markdown("---")
                st.markdown("#### 🔗 Additional Resources")
                
                for resource_type, resource_list in resources.items():
                    if resource_list:
                        st.markdown(f"**{resource_type.title()}**")
                        for resource in resource_list:
                            if isinstance(resource, dict):
                                st.markdown(f"- [{resource.get('title', 'Resource')}]({resource.get('url', '#')})")
                            else:
                                st.markdown(f"- {resource}")
        else:
            st.info("No summary available for this section.")
    
    else:
        st.warning(f"Unknown section type: {section_type}")
