"""
Review Queue UI Component

Renders the spaced repetition review interface for students to practice flashcards.
"""

import streamlit as st
from datetime import datetime

from services.database_service import DatabaseService
from services.srs_service import SRSService
from src.state_manager import StateManager
from src.constants import XP_FLASHCARD_REVIEW
from .progress_manager import StudentProgress

# Import logger
try:
    from src.verbose_logger import get_logger
    _logger = get_logger()
except ImportError:
    _logger = None


def render_review_queue(user_id: str, db: DatabaseService) -> None:
    """
    Render the spaced repetition review queue interface.
    
    Displays due flashcards, handles user reviews, and tracks progress.
    
    Args:
        user_id: The ID of the current student user
        db: DatabaseService instance for database operations
    """
    srs_service = SRSService(db)
    
    # Initialize session state variables using StateManager class methods
    if not StateManager.has_state("current_card"):
        StateManager.set_state("current_card", None)
    if not StateManager.has_state("show_answer"):
        StateManager.set_state("show_answer", False)
    if not StateManager.has_state("cards_reviewed_today"):
        StateManager.set_state("cards_reviewed_today", 0)
    
    try:
        # Get due card count and user stats
        due_count = srs_service.get_due_count(user_id)
        stats = srs_service.get_user_stats(user_id)
        
        # Header Section
        _render_header(due_count, stats)
        
        # Load current card if not already loaded
        if StateManager.get_state("current_card") is None and due_count > 0:
            cards = srs_service.get_due_cards(user_id, limit=1)
            if cards:
                StateManager.set_state("current_card", cards[0])
        
        # Main review interface
        if StateManager.get_state("current_card") is not None:
            _render_flashcard(srs_service, user_id)
        else:
            _render_empty_state(srs_service, user_id)
            
    except Exception as e:
        st.error(f"Error loading review queue: {str(e)}")
        st.info("Please try refreshing the page or contact support if the issue persists.")


def _render_header(due_count: int, stats: dict) -> None:
    """
    Render the header section with title, due count badge, and stats.
    
    Args:
        due_count: Number of cards currently due for review
        stats: Dictionary containing user statistics
    """
    col1, col2 = st.columns([3, 1])
    
    with col1:
        st.markdown("# 📚 Review Queue")
    
    with col2:
        if due_count > 0:
            st.markdown(
                f"""
                <div style='background-color: #ff6b6b; color: white; padding: 10px; 
                     border-radius: 10px; text-align: center; font-weight: bold;'>
                    {due_count} Due
                </div>
                """,
                unsafe_allow_html=True
            )
    
    # Stats summary
    if stats:
        st.markdown("---")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("🔥 Streak", f"{stats.get('current_streak', 0)} days")
        
        with col2:
            st.metric("✅ Reviewed Today", stats.get('cards_reviewed_today', 0))
        
        with col3:
            st.metric("📈 Total Reviews", stats.get('total_reviews', 0))
        
        with col4:
            accuracy = stats.get('accuracy_rate', 0)
            st.metric("🎯 Accuracy", f"{accuracy:.0%}" if accuracy else "N/A")
        
        st.markdown("---")


def _render_flashcard(srs_service: SRSService, user_id: str) -> None:
    """
    Render the current flashcard with show/hide answer functionality.
    
    Args:
        srs_service: SRSService instance for review operations
        user_id: The ID of the current student user
    """
    card = StateManager.get_state("current_card")
    
    # Card container with styling
    with st.container():
        st.markdown(
            """
            <style>
            .flashcard-container {
                border: 3px solid #4CAF50;
                border-radius: 15px;
                padding: 30px;
                background-color: #f9f9f9;
                margin: 20px 0;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }
            .card-front {
                font-size: 24px;
                font-weight: bold;
                color: #333;
                text-align: center;
                margin-bottom: 20px;
            }
            .card-back {
                font-size: 20px;
                color: #555;
                text-align: center;
                padding: 20px;
                background-color: #e8f5e9;
                border-radius: 10px;
                margin-top: 20px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
        
        st.markdown('<div class="flashcard-container">', unsafe_allow_html=True)
        
        # Card front (question)
        st.markdown(
            f'<div class="card-front">❓ {card.get("front", "")}</div>',
            unsafe_allow_html=True
        )
        
        # Show Answer button or answer content
        if not StateManager.get_state("show_answer"):
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                if st.button("🔍 Show Answer", type="primary", width="stretch"):
                    StateManager.set_state("show_answer", True)
                    st.rerun()
        else:
            # Display answer
            st.markdown(
                f'<div class="card-back">✅ {card.get("back", "")}</div>',
                unsafe_allow_html=True
            )
            
            st.markdown("### How well did you know this?")
            
            # Quality rating buttons
            _render_quality_buttons(card, srs_service, user_id)
        
        st.markdown('</div>', unsafe_allow_html=True)


def _render_quality_buttons(
    card: dict, 
    srs_service: SRSService, 
    user_id: str
) -> None:
    """
    Render the quality rating buttons after answer is shown.
    
    Args:
        card: The current flashcard dictionary
        srs_service: SRSService instance for review operations
        user_id: The ID of the current student user
    """
    col1, col2, col3, col4 = st.columns(4)
    
    button_configs = [
        ("Again ❌", 0, "#ff6b6b", col1),
        ("Hard 😓", 2, "#ffa726", col2),
        ("Good 👍", 4, "#66bb6a", col3),
        ("Easy 🚀", 5, "#42a5f5", col4)
    ]
    
    for label, quality, color, column in button_configs:
        with column:
            # Create styled button using markdown and button
            st.markdown(
                f"""
                <style>
                .stButton > button {{
                    background-color: {color};
                    color: white;
                    font-weight: bold;
                    border: none;
                    border-radius: 10px;
                    padding: 10px;
                }}
                .stButton > button:hover {{
                    opacity: 0.8;
                }}
                </style>
                """,
                unsafe_allow_html=True
            )
            
            if st.button(label, key=f"quality_{quality}", width="stretch"):
                _process_review(card, quality, srs_service, user_id)


def _process_review(
    card: dict, 
    quality: int, 
    srs_service: SRSService, 
    user_id: str
) -> None:
    """
    Process a card review and update state.
    
    Args:
        card: The flashcard being reviewed
        quality: Quality rating (0-5)
        srs_service: SRSService instance for review operations
        user_id: The ID of the current student user
    """
    try:
        card_id = card.get("id")
        if card_id:
            # Submit review to SRS service
            srs_service.review_card(card_id, quality)
            
            # Award XP for successful reviews (quality > 0)
            xp_msg = ""
            if quality > 0:
                try:
                    curriculum_id = card.get("curriculum_id")
                    if curriculum_id:
                        progress = StudentProgress(curriculum_id, user_id=user_id)
                        progress.add_xp(XP_FLASHCARD_REVIEW)
                        xp_msg = f" (+{XP_FLASHCARD_REVIEW} XP)"
                except Exception as xp_err:
                    if _logger:
                        _logger.log_event("WARNING", f"Error awarding XP: {xp_err}")

            # Update session state
            cards_reviewed = StateManager.get_state("cards_reviewed_today", 0) + 1
            StateManager.set_state("cards_reviewed_today", cards_reviewed)
            StateManager.set_state("current_card", None)
            StateManager.set_state("show_answer", False)
            
            # Show feedback toast
            feedback_messages = {
                0: "💪 Keep practicing! You'll get it!",
                2: f"📚 Getting there! Review it again soon.{xp_msg}",
                4: f"✨ Great job! You're learning!{xp_msg}",
                5: f"🌟 Excellent! You've mastered this!{xp_msg}"
            }
            
            st.toast(feedback_messages.get(quality, f"Review recorded!{xp_msg}"), icon="✅")
            st.rerun()
        else:
            st.error("Card ID not found. Unable to process review.")
            
    except Exception as e:
        st.error(f"Error processing review: {str(e)}")


def _render_empty_state(srs_service: SRSService, user_id: str) -> None:
    """
    Render empty state when no cards are due for review.
    
    Args:
        srs_service: SRSService instance for review operations
        user_id: The ID of the current student user
    """
    st.markdown(
        """
        <div style='text-align: center; padding: 60px 20px; background-color: #f0f8ff; 
             border-radius: 15px; margin: 20px 0;'>
            <h2 style='color: #4CAF50;'>🎉 All Caught Up!</h2>
            <p style='font-size: 18px; color: #666;'>
                Great work! You have no cards due for review right now.
            </p>
        </div>
        """,
        unsafe_allow_html=True
    )
    
    # Try to get next review time
    try:
        stats = srs_service.get_user_stats(user_id)
        next_review = stats.get("next_review_time")
        
        if next_review:
            if isinstance(next_review, str):
                next_review = datetime.fromisoformat(next_review)
            
            st.info(f"⏰ Your next review is scheduled for: {next_review.strftime('%B %d, %Y at %I:%M %p')}")
        else:
            st.info("✨ Add more flashcards to your deck to continue learning!")
            
    except Exception as e:
        # Silently fail on next review time lookup
        st.info("✨ Check back later for more reviews, or add new flashcards to your deck!")


# Utility function for custom button styling
def _apply_button_style(color: str) -> None:
    """
    Apply custom styling to Streamlit buttons.
    
    Args:
        color: Hex color code for button background
    """
    st.markdown(
        f"""
        <style>
        .stButton > button {{
            background-color: {color};
            color: white;
            font-weight: bold;
            border: none;
            border-radius: 10px;
            padding: 10px 20px;
            transition: all 0.3s ease;
        }}
        .stButton > button:hover {{
            opacity: 0.8;
            transform: scale(1.05);
        }}
        </style>
        """,
        unsafe_allow_html=True
    )
