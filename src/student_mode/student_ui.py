"""Student Mode UI - Interactive learning interface"""

import os
import streamlit as st
import json
from pathlib import Path
from typing import Dict, Any, Optional, List
from .progress_manager import StudentProgress
from .review_queue import render_review_queue
from src.tutor_agent import TutorAgent
from src.state_manager import StateManager
from src.grading_agent import GradingAgent, GradingResult
from src.shared_init import get_database_service
from src.constants import (
    XP_PER_LEVEL,
    XP_SECTION_COMPLETE,
    XP_QUIZ_PERFECT,
    XP_SHORT_ANSWER_MAX,
)
from services.srs_service import SRSService


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

    # If a preferred curriculum file was set (e.g., from Parent dashboard),
    # use it as the default selection.
    preferred_file = StateManager.get_state("preferred_curriculum_file", None)
    default_index = 0
    if preferred_file:
        for i, opt in enumerate(curriculum_options):
            if opt["file"].name == preferred_file or str(opt["file"]) == preferred_file:
                default_index = i
                break

    selected_idx = st.sidebar.selectbox(
        "Select curriculum",
        range(len(curriculum_options)),
        format_func=lambda i: curriculum_options[i]['title'],
        index=default_index,
        label_visibility="collapsed",
        key="student_curriculum_selector"
    )
    
    selected_curriculum = curriculum_options[selected_idx]
    curriculum = selected_curriculum['data']
    curriculum_id = selected_curriculum['id']
    
    # Determine current user (if any) for per-student progress
    current_user = StateManager.get_state("current_user", None)
    user_id: Optional[str] = None
    if isinstance(current_user, dict):
        user_id = current_user.get("id")
    
    # Initialize progress tracker
    progress = StudentProgress(curriculum_id, user_id=user_id)

    # Initialize tutor if enabled
    tutor_enabled = config.get('student_mode', {}).get('tutor_enabled', True)

    # Initialize session state for tutor using StateManager for thread-safety
    if not StateManager.has_state('tutor_agent'):
        if tutor_enabled:
            tutor_model = config.get('student_mode', {}).get('tutor_model', 'gpt-5-nano')
            StateManager.set_state('tutor_agent', TutorAgent(client, model=tutor_model))
        else:
            StateManager.set_state('tutor_agent', None)

    if not StateManager.has_state('tutor_messages'):
        StateManager.set_state('tutor_messages', [])

    if not StateManager.has_state('last_curriculum_id'):
        StateManager.set_state('last_curriculum_id', None)

    if not StateManager.has_state('last_unit_idx'):
        StateManager.set_state('last_unit_idx', None)

    # Clear chat history if curriculum changed
    if StateManager.get_state('last_curriculum_id') != curriculum_id:
        StateManager.set_state('tutor_messages', [])
        StateManager.set_state('last_curriculum_id', curriculum_id)
        tutor_agent = StateManager.get_state('tutor_agent')
        if tutor_agent:
            tutor_agent.clear_conversation()

    # Display progress in sidebar
    current_level = progress.get_level()
    current_xp = progress.get_xp()
    xp_in_level = current_xp % XP_PER_LEVEL
    xp_to_next = XP_PER_LEVEL - xp_in_level
    
    st.sidebar.markdown(f"⭐ **Level {current_level}**")
    st.sidebar.markdown(
        f"🎯 {current_xp} XP ({xp_in_level}/{XP_PER_LEVEL} to Level {current_level + 1})"
    )
    st.sidebar.progress(xp_in_level / float(XP_PER_LEVEL))

    # Streak display
    stats = progress.get_stats()
    current_streak = stats.get("current_streak", 0)
    if current_streak > 0:
        st.sidebar.markdown(f"🔥 **{current_streak} day streak!**")

    # Adaptive difficulty indicator
    difficulty_level = progress.get_difficulty_level()
    difficulty_label = progress.get_difficulty_label()
    difficulty_colors = {1: "🟢", 2: "🟡", 3: "🟠", 4: "🔴", 5: "⭐"}
    st.sidebar.markdown(f"{difficulty_colors.get(difficulty_level, '🟠')} **Difficulty:** {difficulty_label}")

    # Trophy Case (collapsible)
    with st.sidebar.expander("🏆 Trophy Case", expanded=False):
        earned_badges = progress.get_badge_details()
        if earned_badges:
            badge_cols = st.columns(3)
            for i, badge in enumerate(earned_badges):
                with badge_cols[i % 3]:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 5px;">
                        <span style="font-size: 1.5rem;">{badge['icon']}</span><br>
                        <span style="font-size: 0.65rem; color: #888;">{badge['name']}</span>
                    </div>
                    """, unsafe_allow_html=True)
        else:
            st.caption("Complete lessons to earn badges!")

        # Show next available badges
        from .progress_manager import load_badges_config
        all_badges = load_badges_config().get("badges", [])
        earned_ids = set(progress.get_badges())
        available = [b for b in all_badges if b["id"] not in earned_ids][:3]

        if available:
            st.markdown("**Next badges:**")
            for badge in available:
                st.caption(f"{badge['icon']} {badge['name']} - {badge['description']}")

    # Daily Challenges (collapsible)
    from services.challenge_service import get_challenge_service
    challenge_service = get_challenge_service()
    challenges = challenge_service.get_daily_challenges(user_id) if user_id else []
    summary = challenge_service.get_today_summary(user_id) if user_id else {}

    with st.sidebar.expander(f"🎯 Daily Challenges ({summary.get('completed', 0)}/{summary.get('total', 0)})", expanded=False):
        if challenges:
            for challenge in challenges:
                icon = challenge.get('icon', '🎯')
                name = challenge.get('name', 'Challenge')
                progress_val = challenge.get('progress', 0)
                target = challenge.get('target', 1)
                xp = challenge.get('xp_reward', 0)
                completed = challenge.get('completed', False)

                if completed:
                    st.markdown(f"~~{icon} **{name}**~~ ✅")
                    st.caption(f"+{xp} XP earned!")
                else:
                    progress_pct = min(100, int((progress_val / target) * 100))
                    st.markdown(f"{icon} **{name}**")
                    st.progress(progress_pct / 100)
                    st.caption(f"{progress_val}/{target} | +{xp} XP")
                st.markdown("")

            if summary.get('all_complete'):
                st.success("🎉 All challenges complete!")
        else:
            st.caption("Complete tasks to earn XP!")

    st.sidebar.markdown("---")

    # Review Queue section in sidebar
    db = get_database_service()
    srs = SRSService(db)
    due_count = srs.get_due_count(user_id) if user_id else 0
    
    if st.sidebar.button(f"📚 Review Cards ({due_count} due)", width="stretch"):
        StateManager.set_state('student_view', 'review')
        st.rerun()
    
    st.sidebar.markdown("---")

    # Check for new badges to display (from previous action)
    new_badges = StateManager.get_state('new_badges', [])
    if new_badges:
        for badge in new_badges:
            st.toast(f"🏆 New Badge: {badge['icon']} {badge['name']}!", icon="🎉")
        # Clear after displaying
        StateManager.set_state('new_badges', [])

    # View mode: 'learn' or 'review'
    current_view = StateManager.get_state('student_view', 'learn')
    
    if current_view == 'review':
        if user_id:
            db = get_database_service()
            render_review_queue(user_id, db)
            if st.button("← Back to Learning"):
                StateManager.set_state('student_view', 'learn')
                st.rerun()
        else:
            st.warning("Please create a student profile to use the review queue.")
            if st.button("← Back to Learning"):
                StateManager.set_state('student_view', 'learn')
                st.rerun()
        return  # Don't show curriculum content

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
        # Record curriculum completion for badges (only once)
        completion_key = f"curriculum_complete_{curriculum_id}"
        if not StateManager.get_state(completion_key, False):
            new_badges = progress.record_curriculum_completion()
            StateManager.set_state(completion_key, True)
            if new_badges:
                for badge in new_badges:
                    st.toast(f"🏆 New Badge: {badge['icon']} {badge['name']}!", icon="🎉")

        st.success("🏆 **Congratulations! Course Complete!**")
        st.balloons()

        # Show earned badges
        earned_badges = progress.get_badge_details()
        if earned_badges:
            st.markdown("### 🏆 Your Badges")
            badge_cols = st.columns(min(len(earned_badges), 5))
            for i, badge in enumerate(earned_badges):
                with badge_cols[i % 5]:
                    st.markdown(f"""
                    <div style="text-align: center; padding: 8px; background: #f0f2f6; border-radius: 8px; margin: 4px;">
                        <span style="font-size: 2rem;">{badge['icon']}</span><br>
                        <span style="font-size: 0.75rem; font-weight: bold;">{badge['name']}</span>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown(f"### 📊 Final Stats")
        st.markdown(f"- **Level Reached**: {current_level}")
        st.markdown(f"- **Total XP**: {current_xp}")
        st.markdown(f"- **Units Completed**: {len(units)}")
        st.markdown(f"- **Badges Earned**: {len(earned_badges)}")

        if st.button("🔄 Start Over"):
            progress.reset_progress()
            StateManager.set_state(completion_key, False)
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
    tutor_agent = StateManager.get_state('tutor_agent')
    if tutor_enabled and tutor_agent:
        if StateManager.get_state('last_unit_idx') != unit_idx:
            previous_unit_idx = StateManager.get_state('last_unit_idx')
            StateManager.set_state('last_unit_idx', unit_idx)
            StateManager.set_state('tutor_messages', [])  # Clear chat on unit change
            tutor_agent.clear_conversation()

            # Set the new context
            unit_content = unit.get('content', '')
            unit_title = unit.get('title', 'Untitled')
            subject = meta.get('subject', 'Unknown')
            grade = meta.get('grade', 'Unknown')
            tutor_agent.set_lesson_context(
                unit_content=unit_content,
                unit_title=unit_title,
                subject=subject,
                grade=grade
            )

            # Add a helpful transition message so tutor feels less "amnesiac"
            if previous_unit_idx is not None:
                transition_msg = f"📚 *You've moved to Unit {unit_idx + 1}: {unit_title}. Feel free to ask questions about this new topic!*"
                tutor_messages = StateManager.get_state('tutor_messages', [])
                tutor_messages.append({
                    "role": "assistant",
                    "content": transition_msg
                })
                StateManager.set_state('tutor_messages', tutor_messages)

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
    # Store section_idx in state for quiz scoring
    StateManager.set_state('current_section_idx', section_idx)

    # Check mastery gates for quiz sections
    section_in_unit = section_idx % 6
    can_advance = True
    gate_message = ""

    if section_in_unit == 4:  # Quiz section
        can_advance, gate_message = progress.can_advance_from_section(section_idx, len(units))

    col1, col2, col3 = st.columns([1, 2, 1])

    with col1:
        if section_idx > 0:
            if st.button("⬅️ Previous", width="stretch"):
                progress.previous_section()
                st.rerun()

    with col2:
        if can_advance:
            if st.button("✅ Complete & Continue", type="primary", width="stretch"):
                # Award XP for completing the section
                leveled_up = progress.add_xp(XP_SECTION_COMPLETE)

                # Mark section complete (updates streak and checks badges)
                _, new_badges = progress.complete_section(section_idx)

                # TRIGGER SRS CARD CREATION (On Quiz Completion)
                # Section 4 is Quiz. If we are completing it, we passed the gate.
                if section_type_idx == 4 and user_id:
                    _create_flashcards_from_quiz(unit, user_id, curriculum_id)

                progress.advance_section()

                if leveled_up:
                    st.success(f"🎉 Level Up! You're now Level {progress.get_level()}!")
                    st.balloons()
                else:
                    st.success(f"+{XP_SECTION_COMPLETE} XP!")

                # Store new badges for display
                if new_badges:
                    StateManager.set_state('new_badges', new_badges)

                st.rerun()
        else:
            # Show locked state with mastery requirement
            st.error(f"🔒 {gate_message}")
            if st.button("🔄 Try Again", type="primary", width="stretch"):
                # Reset quiz state to allow retry
                StateManager.set_state('quiz_submitted', False)
                StateManager.set_state('quiz_answers', {})
                st.rerun()

    with col3:
        if not can_advance:
            # Parent override - allow skip even if not mastered
            with st.expander("👨‍👩‍👧 Parent"):
                if st.button("Override & Skip", key="parent_override"):
                    progress.complete_section(section_idx)
                    progress.advance_section()
                    st.rerun()
        else:
            if st.button("Skip ⏭️", width="stretch"):
                progress.advance_section()
                st.rerun()

    # Add Tutor Chat Interface
    tutor_agent = StateManager.get_state('tutor_agent')
    if tutor_enabled and tutor_agent:
        st.markdown("---")
        st.markdown("## 🤓 Ask Your Tutor")

        # Only show chat interface for content sections
        if current_section_type in ['content', 'quiz', 'summary']:
            _render_tutor_chat(config, unit)


def _validate_quiz_state(quiz_data: Dict[str, Any]) -> bool:
    """Validate persisted quiz state against current quiz structure.

    This helps detect stale state when switching units or after errors.
    """
    quiz_answers = StateManager.get_state('quiz_answers', {})
    if not isinstance(quiz_answers, dict):
        return False

    questions = quiz_data.get('questions', [])
    mc_questions: List[Dict[str, Any]] = []
    if isinstance(questions, list):
        for q in questions:
            if not isinstance(q, dict):
                continue

            q_type = str(q.get("type", "")).strip().lower()
            if q_type in {"short_answer", "fill", "fill_in_blank", "fill-in-the-blank", "fill_in_the_blank"}:
                continue
            if q_type in {"tf", "true_false", "true/false", "truefalse"}:
                mc_questions.append(q)
                continue
            options = q.get("options")
            if q_type in {"multiple_choice", "mcq", "mc", "choice"}:
                if isinstance(options, list) and len(options) > 0:
                    mc_questions.append(q)
                continue
            if isinstance(options, list) and len(options) > 0:
                mc_questions.append(q)

    expected_mc_count = len(mc_questions)

    # Multiple choice answers are stored with integer keys
    mc_keys = [k for k in quiz_answers.keys() if isinstance(k, int)]
    if not mc_keys:
        return True  # No answers yet – always valid

    if len(mc_keys) > expected_mc_count:
        return False
    if any(k < 0 or k >= expected_mc_count for k in mc_keys):
        return False

    return True


def _coerce_quiz_data(raw_quiz: Any) -> Dict[str, Any]:
    """Normalize quiz into a dict with a 'questions' list (backward compatible)."""
    if isinstance(raw_quiz, dict):
        if isinstance(raw_quiz.get("questions"), list):
            return raw_quiz
        if isinstance(raw_quiz.get("quiz"), list):
            return {"questions": raw_quiz.get("quiz", [])}
        return raw_quiz
    if isinstance(raw_quiz, list):
        return {"questions": raw_quiz}
    return {}


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
            st.image(f"data:image/png;base64,{img_b64}", width="stretch")
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
                        st.image(f"data:image/png;base64,{chart_b64}", width="stretch")
                    else:
                        st.warning("Plotly is not installed and no fallback image available.")
                except Exception as e:
                    st.error(f"Error displaying chart: {e}")
                    # Fallback to matplotlib if available
                    chart_b64 = chart.get('b64')
                    if chart_b64:
                        st.image(f"data:image/png;base64,{chart_b64}", width="stretch")
            else:
                # Display matplotlib chart (legacy or fallback)
                chart_b64 = chart.get('b64')
                if chart_b64:
                    st.image(f"data:image/png;base64,{chart_b64}", width="stretch")
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
        quiz_data = _coerce_quiz_data(unit.get('quiz', {}))

        if quiz_data and isinstance(quiz_data, dict):
            questions = quiz_data.get('questions', [])

            # Validate existing quiz state to avoid stale answers when switching units
            if not _validate_quiz_state(quiz_data):
                StateManager.set_state('quiz_submitted', False)
                StateManager.set_state('quiz_answers', {})
                StateManager.set_state('grading_results', {})
                st.info("Quiz state reset due to unit change.")

            if questions:
                # Separate multiple choice and short answer questions
                def _is_short_answer(q: Dict[str, Any]) -> bool:
                    t = str(q.get("type", "")).strip().lower()
                    return t in {"short_answer", "fill", "fill_in_blank", "fill-in-the-blank", "fill_in_the_blank"}

                def _is_multiple_choice(q: Dict[str, Any]) -> bool:
                    t = str(q.get("type", "")).strip().lower()
                    if t in {"tf", "true_false", "true/false", "truefalse"}:
                        return True
                    options = q.get("options")
                    if t in {"multiple_choice", "mcq", "mc", "choice"}:
                        return isinstance(options, list) and len(options) > 0
                    return isinstance(options, list) and len(options) > 0 and not _is_short_answer(q)

                mc_questions = [q for q in questions if isinstance(q, dict) and _is_multiple_choice(q)]
                sa_questions = [q for q in questions if isinstance(q, dict) and _is_short_answer(q)]

                # Initialize session state for quiz answers using StateManager for thread-safety
                if StateManager.get_state('quiz_submitted') is None:
                    StateManager.set_state('quiz_submitted', False)
                if StateManager.get_state('quiz_answers') is None:
                    StateManager.set_state('quiz_answers', {})
                if StateManager.get_state('grading_results') is None:
                    StateManager.set_state('grading_results', {})

                # === MULTIPLE CHOICE SECTION ===
                if mc_questions:
                    st.markdown("#### 📝 Multiple Choice")
                    with st.form("quiz_form_mc"):
                        user_answers = {}

                        for i, q in enumerate(mc_questions):
                            st.markdown(f"**Question {i + 1}: {q.get('question', '')}**")
                            options = q.get('options', [])
                            if not isinstance(options, list):
                                options = []
                            q_type = str(q.get("type", "")).strip().lower()
                            if q_type in {"tf", "true_false", "true/false", "truefalse"} and not options:
                                options = ["True", "False"]

                            answer = st.radio(
                                f"Select your answer for question {i + 1}",
                                options,
                                key=f"mc_q_{i}",
                                label_visibility="collapsed"
                            )
                            user_answers[i] = answer
                            st.markdown("")

                        submitted = st.form_submit_button("Submit Multiple Choice", type="primary", width="stretch")

                        if submitted:
                            StateManager.set_state('quiz_submitted', True)
                            StateManager.set_state('quiz_answers', user_answers)

                    # Show MC results if submitted
                    if StateManager.get_state('quiz_submitted', False) and mc_questions:
                        correct_count = 0
                        quiz_answers = StateManager.get_state('quiz_answers', {})

                        # Initialize progress for adaptive difficulty and mastery tracking
                        current_user = StateManager.get_state("current_user", None)
                        user_id = current_user.get("id") if isinstance(current_user, dict) else None
                        curriculum_id = StateManager.get_state('last_curriculum_id')
                        progress = StudentProgress(curriculum_id, user_id=user_id)

                        for i, q in enumerate(mc_questions):
                            user_answer = quiz_answers.get(i)
                            correct_answer = q.get('correct') or q.get('answer') or ''

                            is_correct = user_answer == correct_answer
                            if is_correct:
                                correct_count += 1
                                st.success(f"✅ Question {i + 1}: Correct!")
                            else:
                                st.error(f"❌ Question {i + 1}: Incorrect. The correct answer was: {correct_answer}")
                            
                            # Track each question for adaptive difficulty
                            progress.record_question_result(is_correct)

                        total_mc = len(mc_questions)
                        
                        # Record quiz score for mastery tracking
                        score_pct = correct_count / total_mc if total_mc > 0 else 0

                        # Get unit_idx from section_idx
                        section_idx = StateManager.get_state('current_section_idx', 0)
                        unit_idx = section_idx // 6
                        
                        # Record quiz score for this unit
                        progress.record_quiz_score(unit_idx, score_pct, total_mc, correct_count)
                        
                        if correct_count == total_mc:
                            st.success(f"🌟 Perfect score! {correct_count}/{total_mc} correct!")
                            progress.add_xp(XP_QUIZ_PERFECT)
                            # Record perfect quiz for badge tracking
                            new_badges = progress.record_perfect_quiz()
                            st.info(f"🎁 Bonus: +{XP_QUIZ_PERFECT} XP for perfect score!")
                            # Show badge notifications
                            for badge in new_badges:
                                st.balloons()
                                st.success(f"🏆 **New Badge Earned!** {badge['icon']} {badge['name']} - {badge['description']}")
                        elif correct_count > 0:
                            st.info(f"📊 You got {correct_count}/{total_mc} correct!")
                            progress.add_xp(XP_SECTION_COMPLETE)
                            st.info(f"⭐ +{XP_SECTION_COMPLETE} XP for completing the quiz!")
                        else:
                            st.warning(f"Keep trying! You got {correct_count}/{total_mc} correct.")

                # === SHORT ANSWER SECTION (AI Graded) ===
                if sa_questions:
                    st.markdown("---")
                    st.markdown("#### ✍️ Short Answer (AI Graded)")
                    st.caption("Write your answers and get personalized AI feedback!")

                    for i, q in enumerate(sa_questions):
                        q_key = f"sa_{i}"
                        st.markdown(f"**Question {i + 1}: {q.get('question', '')}**")

                        # Text area for answer
                        answer = st.text_area(
                            f"Your answer for question {i + 1}",
                            key=q_key,
                            height=100,
                            label_visibility="collapsed",
                            placeholder="Type your answer here..."
                        )

                        # Voice input option
                        audio_val = st.audio_input(f"🎤 Or speak your answer", key=f"audio_{q_key}")

                        if audio_val:
                            with st.spinner("Transcribing your answer..."):
                                try:
                                    from openai import OpenAI

                                    api_key = os.getenv("OPENAI_API_KEY")
                                    if api_key:
                                        whisper_client = OpenAI(api_key=api_key)
                                        transcription = whisper_client.audio.transcriptions.create(
                                            model="whisper-1",
                                            file=audio_val
                                        )

                                        if transcription.text:
                                            st.success(f"✅ Heard: {transcription.text}")
                                            # Update the answer variable for grading
                                            answer = transcription.text

                                            # Store in session state so it persists
                                            if 'transcribed_answers' not in st.session_state:
                                                st.session_state.transcribed_answers = {}
                                            st.session_state.transcribed_answers[q_key] = transcription.text
                                    else:
                                        st.warning("⚠️ Voice input requires OpenAI API key in your .env file")

                                except Exception as e:
                                    st.error(f"Transcription failed: {str(e)}")

                        # Use transcribed answer if available
                        if hasattr(st.session_state, 'transcribed_answers') and q_key in st.session_state.transcribed_answers:
                            answer = st.session_state.transcribed_answers[q_key]

                        # Grade button for each short answer
                        if st.button(f"📊 Get AI Feedback", key=f"grade_{q_key}"):
                            if answer and answer.strip():
                                with st.spinner("🤖 AI is grading your answer..."):
                                    try:
                                        # Initialize grading agent
                                        grading_model = StateManager.get_state('config', {}).get('student_mode', {}).get('grading_model', 'gpt-5-nano')
                                        grader = GradingAgent(
                                            client=StateManager.get_state('client'),
                                            model=grading_model
                                        )

                                        # Get context
                                        selected_curriculum = StateManager.get_state('selected_curriculum', {})
                                        meta = selected_curriculum.get('data', {}).get('meta', {}) if selected_curriculum else {}
                                        unit_content = unit.get('content', '')
                                        unit_title = unit.get('title', 'Unknown')

                                        # Grade the answer
                                        result = grader.grade_answer(
                                            question=q.get('question', ''),
                                            student_answer=answer,
                                            unit_title=unit_title,
                                            lesson_content=unit_content,
                                            subject=meta.get('subject', 'General'),
                                            grade=meta.get('grade', 'K-12'),
                                            criteria=q.get('criteria')
                                        )

                                        # Store result
                                        grading_results = StateManager.get_state('grading_results', {})
                                        grading_results[q_key] = result
                                        StateManager.set_state('grading_results', grading_results)

                                        # Award XP based on score
                                        current_user = StateManager.get_state("current_user", None)
                                        user_id = current_user.get("id") if isinstance(current_user, dict) else None
                                        progress = StudentProgress(StateManager.get_state('last_curriculum_id'), user_id=user_id)

                                        xp_earned = int(result.score * XP_SHORT_ANSWER_MAX)
                                        if xp_earned > 0:
                                            progress.add_xp(xp_earned)

                                        # Record short answer for badge tracking
                                        new_badges = progress.record_short_answer()
                                        # Store badges for display after rerun
                                        if new_badges:
                                            StateManager.set_state('new_badges', new_badges)

                                        st.rerun()

                                    except Exception as e:
                                        st.error(f"Grading error: {e}")
                            else:
                                st.warning("Please write an answer first!")

                        # Display grading result if available
                        grading_results = StateManager.get_state('grading_results', {})
                        if q_key in grading_results:
                            result = grading_results[q_key]

                            # Score display with color coding
                            score_pct = int(result.score * 100)
                            if score_pct >= 80:
                                st.success(f"🌟 Score: {score_pct}%")
                            elif score_pct >= 60:
                                st.info(f"👍 Score: {score_pct}%")
                            else:
                                st.warning(f"📚 Score: {score_pct}%")

                            # Feedback
                            st.markdown(f"**Feedback:** {result.feedback}")

                            # Strengths and improvements in columns
                            col1, col2 = st.columns(2)
                            with col1:
                                if result.strengths:
                                    st.markdown("**✅ Strengths:**")
                                    for s in result.strengths:
                                        st.markdown(f"- {s}")
                            with col2:
                                if result.improvements:
                                    st.markdown("**💡 To improve:**")
                                    for imp in result.improvements:
                                        st.markdown(f"- {imp}")

                            # Model answer (expandable)
                            if result.model_answer:
                                with st.expander("📖 See example answer"):
                                    st.markdown(result.model_answer)

                            xp_earned = int(result.score * 20)
                            if xp_earned > 0:
                                st.caption(f"⭐ +{xp_earned} XP earned!")

                        st.markdown("---")

                # Reset button
                if StateManager.get_state('quiz_submitted', False) or StateManager.get_state('grading_results', {}):
                    if st.button("🔄 Try Again"):
                        StateManager.set_state('quiz_submitted', False)
                        StateManager.set_state('quiz_answers', {})
                        StateManager.set_state('grading_results', {})
                        # Clear transcribed answers when resetting quiz
                        if 'transcribed_answers' in st.session_state:
                            st.session_state.transcribed_answers = {}
                        st.rerun()
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
            resources = unit.get('resources', None)
            if resources:
                st.markdown("---")
                st.markdown("#### 🔗 Additional Resources")

                if isinstance(resources, str):
                    st.markdown(resources)
                elif isinstance(resources, list):
                    for resource in resources:
                        if isinstance(resource, dict):
                            title = resource.get("title", "Resource")
                            url = resource.get("url")
                            st.markdown(f"- [{title}]({url})" if url else f"- {title}")
                        else:
                            st.markdown(f"- {resource}")
                elif isinstance(resources, dict):
                    for resource_type, resource_list in resources.items():
                        if not resource_list:
                            continue
                        st.markdown(f"**{str(resource_type).title()}**")

                        if isinstance(resource_list, str):
                            st.markdown(resource_list)
                            continue
                        if isinstance(resource_list, list):
                            for resource in resource_list:
                                if isinstance(resource, dict):
                                    title = resource.get("title", "Resource")
                                    url = resource.get("url")
                                    st.markdown(f"- [{title}]({url})" if url else f"- {title}")
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

    # Get tutor state from StateManager
    tutor_messages = StateManager.get_state('tutor_messages', [])
    tutor_agent = StateManager.get_state('tutor_agent')

    # Show example questions if no messages
    if not tutor_messages:
        with chat_container:
            st.markdown("### 💭 Try asking me about:")
            example_questions = tutor_agent.get_example_questions() if tutor_agent else []

            if example_questions:
                cols = st.columns(len(example_questions))
                for idx, question in enumerate(example_questions):
                    with cols[idx]:
                        if st.button(question, key=f"example_{idx}", width="stretch"):
                            # Process the example question
                            tutor_messages = StateManager.get_state('tutor_messages', [])
                            tutor_messages.append({
                                "role": "user",
                                "content": question
                            })
                            StateManager.set_state('tutor_messages', tutor_messages)

                            with st.spinner("🤔 Thinking..."):
                                tutor_config = config.get('student_mode', {})
                                temperature = tutor_config.get('tutor_temperature', 0.7)
                                response = tutor_agent.get_response(
                                    question,
                                    temperature=temperature
                                )

                                tutor_messages = StateManager.get_state('tutor_messages', [])
                                tutor_messages.append({
                                    "role": "assistant",
                                    "content": response
                                })
                                StateManager.set_state('tutor_messages', tutor_messages)
                            st.rerun()

    # Display chat messages
    with chat_container:
        tutor_messages = StateManager.get_state('tutor_messages', [])
        for message in tutor_messages:
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
            StateManager.set_state('tutor_messages', [])
            tutor_agent = StateManager.get_state('tutor_agent')
            if tutor_agent:
                tutor_agent.clear_conversation()
            st.rerun()

    # Process user input
    if user_input:
        # Add user message to history
        tutor_messages = StateManager.get_state('tutor_messages', [])
        tutor_messages.append({
            "role": "user",
            "content": user_input
        })
        StateManager.set_state('tutor_messages', tutor_messages)

        # Track tutor question for badge system
        current_user = StateManager.get_state("current_user", None)
        user_id = current_user.get("id") if isinstance(current_user, dict) else None
        curriculum_id = StateManager.get_state('last_curriculum_id')
        if curriculum_id:
            progress = StudentProgress(curriculum_id, user_id=user_id)
            new_badges = progress.record_tutor_question()
            if new_badges:
                StateManager.set_state('new_badges', new_badges)

        # Get tutor response
        with st.spinner("🤔 Let me think about that..."):
            tutor_config = config.get('student_mode', {})
            temperature = tutor_config.get('tutor_temperature', 0.7)

            tutor_agent = StateManager.get_state('tutor_agent')
            response = tutor_agent.get_response(
                user_input,
                temperature=temperature
            )

            # Add assistant response to history
            tutor_messages = StateManager.get_state('tutor_messages', [])
            tutor_messages.append({
                "role": "assistant",
                "content": response
            })
            StateManager.set_state('tutor_messages', tutor_messages)

        st.rerun()


def _create_flashcards_from_quiz(unit: Dict[str, Any], user_id: str, curriculum_id: str):
    """Create flashcards from quiz questions"""
    try:
        db = get_database_service()
        srs = SRSService(db)
        quiz_data = _coerce_quiz_data(unit.get('quiz', {}))
        questions = quiz_data.get('questions', [])
        
        count = 0
        for q in questions:
            if not isinstance(q, dict):
                continue
            front = q.get('question')
            back = ""
            
            # Determine back of card based on question type
            q_type = str(q.get("type", "")).strip().lower()
            if q_type in {"short_answer", "fill", "fill_in_blank", "fill-in-the-blank", "fill_in_the_blank"}:
                back = q.get('sample_answer') or q.get("answer") or q.get("correct")
            else:
                # Default to multiple choice style
                back = q.get('correct') or q.get("answer")
                
            # Create card if valid
            if front and back:
                srs.create_card(user_id, curriculum_id, front, str(back))
                count += 1
        
        if count > 0:
            st.toast(f"📇 Created {count} flashcards for your review queue!", icon="🧠")
            
    except Exception as e:
        print(f"Error creating flashcards: {e}")
