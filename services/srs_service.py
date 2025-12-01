"""
Spaced Repetition System (SRS) Service
Implements the SM-2 algorithm for intelligent flashcard review scheduling.
"""

import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

# Conditional logger import
try:
    from src.verbose_logger import get_logger
    _logger = get_logger()

    def log_info(msg: str) -> None:
        if _logger is None:
            print(msg)
        elif hasattr(_logger, "log_info"):
            _logger.log_info(msg)
        else:
            # Fallback to underlying logger if exposed
            getattr(_logger, "logger", _logger).info(msg)

    def log_error(msg: str) -> None:
        if _logger is None:
            print(f"ERROR: {msg}")
        elif hasattr(_logger, "log_error"):
            _logger.log_error(msg)
        else:
            getattr(_logger, "logger", _logger).error(msg)

except ImportError:

    def log_info(msg: str) -> None:
        print(msg)

    def log_error(msg: str) -> None:
        print(f"ERROR: {msg}")


class SRSService:
    """Manages spaced repetition flashcards using the SM-2 algorithm.
    
    The SM-2 (SuperMemo 2) algorithm schedules review intervals based on
    user performance, optimizing long-term retention.
    
    Quality ratings (0-5):
        0 - Complete blackout, no recall
        1 - Incorrect response, correct answer remembered
        2 - Incorrect response, correct answer seemed easy to recall
        3 - Correct response, but required significant difficulty to recall
        4 - Correct response, after some hesitation
        5 - Perfect response, immediate recall
    """
    
    def __init__(self, db):
        """Initialize SRS service with database connection.
        
        Args:
            db: DatabaseService instance for data persistence
        """
        self.db = db
        log_info("SRSService initialized with SM-2 algorithm")
        
    def create_card(
        self,
        user_id: str,
        curriculum_id: str,
        front: str,
        back: str
    ) -> Optional[str]:
        """Create a new flashcard for spaced repetition review.
        
        Args:
            user_id: ID of the user who owns the card
            curriculum_id: ID of the curriculum this card belongs to
            front: Front side of card (question/prompt)
            back: Back side of card (answer/explanation)
            
        Returns:
            Card ID if successful, None otherwise
        """
        try:
            card_id = uuid.uuid4().hex
            
            # Create review item with default SM-2 parameters
            item_id = self.db.create_review_item(
                user_id=user_id,
                curriculum_id=curriculum_id,
                card_front=front,
                card_back=back,
                item_id=card_id
            )
            
            if item_id:
                log_info(f"Created flashcard {item_id} for user {user_id}")
                return item_id
            else:
                log_error(f"Failed to create flashcard for user {user_id}")
                return None
                
        except Exception as e:
            log_error(f"Error creating flashcard: {e}")
            return None
            
    def create_cards_from_content(
        self,
        user_id: str,
        curriculum_id: str,
        content: str
    ) -> List[Dict[str, Any]]:
        """Generate flashcards from lesson content using AI.
        
        This is a stub for Phase 1.2 AI integration. Currently returns empty list.
        
        Args:
            user_id: ID of the user
            curriculum_id: ID of the curriculum
            content: Lesson content to extract flashcards from
            
        Returns:
            List of created flashcard dictionaries (empty in Phase 1.1)
        """
        log_info(f"create_cards_from_content stub called for user {user_id}")
        log_info("AI flashcard generation will be implemented in Phase 1.2")
        
        # Placeholder for Phase 1.2
        # Will use AI to extract key concepts and generate Q&A pairs
        return []
        
    def get_due_cards(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get flashcards that are due for review.
        
        Cards are considered due if their next_review timestamp is in the past.
        Results are ordered by next_review date (oldest first).
        
        Args:
            user_id: ID of the user
            limit: Maximum number of cards to return (default: 20)
            
        Returns:
            List of flashcard dictionaries due for review
        """
        try:
            due_cards = self.db.get_due_reviews(user_id=user_id, limit=limit)
            log_info(f"Retrieved {len(due_cards)} due cards for user {user_id}")
            return due_cards
            
        except Exception as e:
            log_error(f"Error getting due cards for user {user_id}: {e}")
            return []
            
    def get_due_count(self, user_id: str) -> int:
        """Get the count of cards due for review.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Number of cards currently due for review
        """
        try:
            # Get stats which includes due_today count
            stats = self.db.get_review_stats(user_id=user_id)
            due_count = stats.get('due_today', 0)
            
            log_info(f"User {user_id} has {due_count} cards due")
            return due_count
            
        except Exception as e:
            log_error(f"Error getting due count for user {user_id}: {e}")
            return 0
            
    def review_card(self, card_id: str, quality: int) -> bool:
        """Process a card review using the SM-2 algorithm.
        
        The SM-2 algorithm adjusts the review interval based on performance:
        - Quality < 3: Reset to day 1 (failed recall)
        - Quality >= 3: Increase interval based on easiness factor
        
        Algorithm details:
        1. If quality < 3:
           - repetitions = 0
           - interval = 1 day
           
        2. If quality >= 3:
           - repetitions increases
           - interval = 1 day (first rep), 6 days (second rep), 
                       or interval * EF (subsequent reps)
                       
        3. Easiness Factor update:
           - EF = EF + (0.1 - (5-quality) * (0.08 + (5-quality) * 0.02))
           - Minimum EF is 1.3
           
        4. Next review date = today + interval days
        
        Args:
            card_id: ID of the card being reviewed
            quality: Quality rating (0-5)
                    0 = complete blackout
                    1 = incorrect, but remembered when shown
                    2 = incorrect, seemed easy when shown
                    3 = correct with significant difficulty
                    4 = correct after hesitation
                    5 = perfect recall
            
        Returns:
            True if review processed successfully, False otherwise
        """
        # Validate quality rating
        if not 0 <= quality <= 5:
            log_error(f"Invalid quality rating {quality} for card {card_id}. Must be 0-5.")
            return False
            
        try:
            # Get current card data
            card = self.db.fetch_one(
                "SELECT * FROM review_items WHERE id = ?",
                (card_id,)
            )
            
            if not card:
                log_error(f"Card {card_id} not found")
                return False
                
            # Extract current SM-2 parameters
            ef = card['easiness_factor']  # Default: 2.5
            interval = card['interval']    # Default: 1
            reps = card['repetitions']     # Default: 0
            
            log_info(f"Reviewing card {card_id}: quality={quality}, "
                    f"EF={ef:.2f}, interval={interval}, reps={reps}")
            
            # SM-2 Algorithm Implementation
            
            # Step 1: Calculate new repetition count and interval
            if quality < 3:
                # Failed recall - reset progress
                reps = 0
                interval = 1
                log_info(f"Card {card_id} failed (quality < 3). Reset to day 1.")
            else:
                # Successful recall - advance progress
                reps += 1
                
                if reps == 1:
                    interval = 1
                elif reps == 2:
                    interval = 6
                else:
                    interval = round(interval * ef)
                    
                log_info(f"Card {card_id} passed. New interval: {interval} days")
            
            # Step 2: Update easiness factor
            # Formula: EF' = EF + (0.1 - (5-q) * (0.08 + (5-q) * 0.02))
            ef_delta = 0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)
            new_ef = max(1.3, ef + ef_delta)
            
            log_info(f"Card {card_id} EF updated: {ef:.2f} -> {new_ef:.2f}")
            
            # Step 3: Calculate next review date
            next_review = datetime.now() + timedelta(days=interval)
            
            # Step 4: Update card in database
            success = self.db.execute(
                """
                UPDATE review_items
                SET easiness_factor = ?, 
                    interval = ?, 
                    repetitions = ?, 
                    next_review = ?
                WHERE id = ?
                """,
                (new_ef, interval, reps, next_review.isoformat(), card_id)
            )
            
            if success:
                log_info(f"Card {card_id} review processed successfully. "
                        f"Next review: {next_review.strftime('%Y-%m-%d')}")
            else:
                log_error(f"Failed to update card {card_id} in database")
                
            return success
            
        except Exception as e:
            log_error(f"Error processing review for card {card_id}: {e}")
            return False
            
    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """Get comprehensive SRS statistics for a user.
        
        Args:
            user_id: ID of the user
            
        Returns:
            Dictionary containing:
                - total_cards: Total number of flashcards
                - due_today: Number of cards due for review
                - streak_days: Current review streak (stub - Phase 1.2)
                - retention_rate: Percentage of successful reviews (stub - Phase 1.2)
        """
        try:
            # Get base stats from database
            db_stats = self.db.get_review_stats(user_id=user_id)
            
            # Compile comprehensive stats
            stats = {
                'total_cards': db_stats.get('total_cards', 0),
                'due_today': db_stats.get('due_today', 0),
                'mastered': db_stats.get('mastered', 0),
                
                # Phase 1.2 features (stubs)
                'streak_days': 0,        # Will track consecutive review days
                'retention_rate': 0.0    # Will calculate from review history
            }
            
            log_info(f"Retrieved stats for user {user_id}: "
                    f"{stats['total_cards']} cards, {stats['due_today']} due")
            
            return stats
            
        except Exception as e:
            log_error(f"Error getting stats for user {user_id}: {e}")
            return {
                'total_cards': 0,
                'due_today': 0,
                'mastered': 0,
                'streak_days': 0,
                'retention_rate': 0.0
            }
            
    def get_card(self, card_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific flashcard by ID.
        
        Args:
            card_id: ID of the card to retrieve
            
        Returns:
            Card dictionary or None if not found
        """
        try:
            card = self.db.fetch_one(
                "SELECT * FROM review_items WHERE id = ?",
                (card_id,)
            )
            
            if card:
                log_info(f"Retrieved card {card_id}")
            else:
                log_info(f"Card {card_id} not found")
                
            return card
            
        except Exception as e:
            log_error(f"Error getting card {card_id}: {e}")
            return None
            
    def delete_card(self, card_id: str) -> bool:
        """Delete a flashcard.
        
        Args:
            card_id: ID of the card to delete
            
        Returns:
            True if successful, False otherwise
        """
        try:
            success = self.db.execute(
                "DELETE FROM review_items WHERE id = ?",
                (card_id,)
            )
            
            if success:
                log_info(f"Deleted card {card_id}")
            else:
                log_error(f"Failed to delete card {card_id}")
                
            return success
            
        except Exception as e:
            log_error(f"Error deleting card {card_id}: {e}")
            return False
            
    def get_user_cards(
        self,
        user_id: str,
        curriculum_id: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all cards for a user, optionally filtered by curriculum.
        
        Args:
            user_id: ID of the user
            curriculum_id: Optional curriculum ID to filter by
            limit: Optional maximum number of cards to return
            
        Returns:
            List of card dictionaries
        """
        try:
            if curriculum_id:
                sql = """
                    SELECT * FROM review_items 
                    WHERE user_id = ? AND curriculum_id = ?
                    ORDER BY created_at DESC
                """
                params = (user_id, curriculum_id)
            else:
                sql = """
                    SELECT * FROM review_items 
                    WHERE user_id = ?
                    ORDER BY created_at DESC
                """
                params = (user_id,)
                
            if limit:
                sql += f" LIMIT {limit}"
                
            cards = self.db.fetch_all(sql, params)
            
            log_info(f"Retrieved {len(cards)} cards for user {user_id}" +
                    (f" (curriculum: {curriculum_id})" if curriculum_id else ""))
            
            return cards
            
        except Exception as e:
            log_error(f"Error getting cards for user {user_id}: {e}")
            return []
