"""Student Mode UI - Interactive learning interface"""

import os
import streamlit as st
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from .progress_manager import StudentProgress
from src.tutor_agent import TutorAgent


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

    # Initialize tutor if enabled
    tutor_enabled = config.get('student_mode', {}).get('tutor_enabled', True)

    # Initialize session state for tutor
    if 'tutor_agent' not in st.session_state:
        if tutor_enabled:
            tutor_model = config.get('student_mode', {}).get('tutor_model', 'gpt-4.1-nano')
            st.session_state.tutor_agent = TutorAgent(client, model=tutor_model)
        else:
            st.session_state.tutor_agent = None

    if 'tutor_messages' not in st.session_state:
        st.session_state.tutor_messages = []

    if 'last_curriculum_id' not in st.session_state:
        st.session_state.last_curriculum_id = None

    if 'last_unit_idx' not in st.session_state:
        st.session_state.last_unit_idx = None

    # Clear chat history if curriculum changed
    if st.session_state.last_curriculum_id != curriculum_id:
        st.session_state.tutor_messages = []
        st.session_state.last_curriculum_id = curriculum_id
        if st.session_state.tutor_agent:
            st.session_state.tutor_agent.clear_conversation()

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

    # Update tutor context if unit changed
    if tutor_enabled and st.session_state.tutor_agent:
        if st.session_state.last_unit_idx != unit_idx:
            st.session_state.last_unit_idx = unit_idx
            st.session_state.tutor_messages = []  # Clear chat on unit change
            st.session_state.tutor_agent.clear_conversation()

            # Set the new context
            unit_content = unit.get('content', '')
            unit_title = unit.get('title', 'Untitled')
            subject = meta.get('subject', 'Unknown')
            grade = meta.get('grade', 'Unknown')
            st.session_state.tutor_agent.set_lesson_context(
                unit_content=unit_content,
                unit_title=unit_title,
                subject=subject,
                grade=grade
            )

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

    # Add Tutor Chat Interface
    if tutor_enabled and st.session_state.tutor_agent:
        st.markdown("---")
        st.markdown("## 🤓 Ask Your Tutor")

        # Only show chat interface for content sections
        if current_section_type in ['content', 'quiz', 'summary']:
            _render_tutor_chat(config, unit)


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
        
        # Display audio player if available
        audio_data = unit.get('audio')
        if audio_data:
            audio_path = audio_data.get('path')
            if audio_path and os.path.exists(audio_path):
                st.markdown("#### 🔊 Listen to this lesson")
                with open(audio_path, 'rb') as audio_file:
                    audio_bytes = audio_file.read()
                    st.audio(audio_bytes, format='audio/mp3')
                st.markdown("---")
        
        content = unit.get('content', '')
        if content:
            st.markdown(content)
        else:
            st.warning("No content available for this section.")
    
    elif section_type == 'chart':
        st.markdown("### 📊 Data & Visualization")
        chart = unit.get('chart', {})
        
        if chart and isinstance(chart, dict):
            # Check if this is a Plotly chart or matplotlib chart
            chart_type = chart.get('chart_type', 'matplotlib')
            
            if chart_type == 'plotly' and chart.get('plotly_config'):
                # Display interactive Plotly chart
                try:
                    import plotly.graph_objects as go
                    fig = go.Figure(chart['plotly_config'])
                    st.plotly_chart(fig, use_container_width=True)
                except ImportError:
                    # Fallback to matplotlib if plotly not available
                    chart_b64 = chart.get('b64')
                    if chart_b64:
                        st.image(f"data:image/png;base64,{chart_b64}", use_container_width=True)
                    else:
                        st.warning("Plotly is not installed and no fallback image available.")
                except Exception as e:
                    st.error(f"Error displaying chart: {e}")
                    # Fallback to matplotlib if available
                    chart_b64 = chart.get('b64')
                    if chart_b64:
                        st.image(f"data:image/png;base64,{chart_b64}", use_container_width=True)
            else:
                # Display matplotlib chart (legacy or fallback)
                chart_b64 = chart.get('b64')
                if chart_b64:
                    st.image(f"data:image/png;base64,{chart_b64}", use_container_width=True)
                else:
                    st.info("No chart available for this section.")
            
            # Display chart description if available
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


def _render_tutor_chat(config: Dict[str, Any], unit: Dict[str, Any]):
    """
    Render the tutor chat interface

    Args:
        config: Application configuration
        unit: Current unit data
    """
    # Create chat container
    chat_container = st.container()

    # Show example questions if no messages
    if not st.session_state.tutor_messages:
        with chat_container:
            st.markdown("### 💭 Try asking me about:")
            example_questions = st.session_state.tutor_agent.get_example_questions()

            cols = st.columns(len(example_questions))
            for idx, question in enumerate(example_questions):
                with cols[idx]:
                    if st.button(question, key=f"example_{idx}", use_container_width=True):
                        # Process the example question
                        st.session_state.tutor_messages.append({
                            "role": "user",
                            "content": question
                        })

                        with st.spinner("🤔 Thinking..."):
                            tutor_config = config.get('student_mode', {})
                            temperature = tutor_config.get('tutor_temperature', 0.7)
                            response = st.session_state.tutor_agent.get_response(
                                question,
                                temperature=temperature
                            )

                            st.session_state.tutor_messages.append({
                                "role": "assistant",
                                "content": response
                            })
                        st.rerun()

    # Display chat messages
    with chat_container:
        for message in st.session_state.tutor_messages:
            if message["role"] == "user":
                with st.chat_message("user", avatar="🧑‍🎓"):
                    st.markdown(message["content"])
            else:
                with st.chat_message("assistant", avatar="🤓"):
                    st.markdown(message["content"])

    # Chat input at the bottom
    col1, col2 = st.columns([10, 1])

    with col1:
        user_input = st.chat_input(
            "Ask the tutor a question about this lesson...",
            key="tutor_chat_input"
        )

    with col2:
        if st.button("🗑️", help="Clear chat history"):
            st.session_state.tutor_messages = []
            if st.session_state.tutor_agent:
                st.session_state.tutor_agent.clear_conversation()
            st.rerun()

    # Process user input
    if user_input:
        # Add user message to history
        st.session_state.tutor_messages.append({
            "role": "user",
            "content": user_input
        })

        # Get tutor response
        with st.spinner("🤔 Let me think about that..."):
            tutor_config = config.get('student_mode', {})
            temperature = tutor_config.get('tutor_temperature', 0.7)

            response = st.session_state.tutor_agent.get_response(
                user_input,
                temperature=temperature
            )

            # Add assistant response to history
            st.session_state.tutor_messages.append({
                "role": "assistant",
                "content": response
            })

        st.rerun()
