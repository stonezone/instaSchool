"""
Database Management Service
Provides SQLite database management for InstaSchool with user profiles,
curricula metadata, and progress tracking.
"""

import os
import json
import sqlite3
import hashlib
import threading
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
from contextlib import contextmanager

try:
    import streamlit as st

    HAS_STREAMLIT = True
except ImportError:
    HAS_STREAMLIT = False


class DatabaseService:
    """Manages SQLite database operations for InstaSchool"""

    _local = threading.local()

    def __init__(self, db_path: str = "instaschool.db"):
        """Initialize database service and create tables

        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._ensure_database_exists()

    def _ensure_database_exists(self) -> None:
        """Create database and tables if they don't exist"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Users table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        id TEXT PRIMARY KEY,
                        username TEXT UNIQUE NOT NULL,
                        pin_hash TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        total_xp INTEGER DEFAULT 0,
                        preferences TEXT
                    )
                """)

                # Curricula metadata table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS curricula (
                        id TEXT PRIMARY KEY,
                        title TEXT,
                        subject TEXT,
                        grade TEXT,
                        style TEXT,
                        language TEXT,
                        file_path TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_by TEXT,
                        FOREIGN KEY (created_by) REFERENCES users(id)
                    )
                """)

                # Progress tracking table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS progress (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id TEXT NOT NULL,
                        curriculum_id TEXT NOT NULL,
                        current_section INTEGER DEFAULT 0,
                        completed_sections TEXT,
                        xp INTEGER DEFAULT 0,
                        badges TEXT,
                        stats TEXT,
                        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        UNIQUE(user_id, curriculum_id),
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (curriculum_id) REFERENCES curricula(id)
                    )
                """)

                # Review items for spaced repetition system
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS review_items (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        curriculum_id TEXT NOT NULL,
                        card_front TEXT NOT NULL,
                        card_back TEXT NOT NULL,
                        easiness_factor REAL DEFAULT 2.5,
                        interval INTEGER DEFAULT 1,
                        repetitions INTEGER DEFAULT 0,
                        next_review TIMESTAMP,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (user_id) REFERENCES users(id),
                        FOREIGN KEY (curriculum_id) REFERENCES curricula(id)
                    )
                """)

                # Create indexes for common queries
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_progress_user 
                    ON progress(user_id)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_progress_curriculum 
                    ON progress(curriculum_id)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_review_next 
                    ON review_items(user_id, next_review)
                """)

                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_curricula_creator 
                    ON curricula(created_by)
                """)

                conn.commit()
                print(f"Database initialized: {self.db_path}")

        except sqlite3.Error as e:
            print(f"Error initializing database: {e}")
            raise

    @contextmanager
    def get_connection(self):
        """Get thread-local database connection with connection reuse.

        Yields:
            sqlite3.Connection: Database connection
        """
        conn = getattr(self._local, "connection", None)
        conn_db_path = getattr(self._local, "db_path", None)

        # If this thread already has a connection for a different DB file,
        # close and replace it to avoid cross-database bleed.
        if conn is not None and conn_db_path != self.db_path:
            try:
                conn.close()
            except sqlite3.Error:
                pass
            finally:
                self._local.connection = None
                self._local.db_path = None
                conn = None

        if conn is None:
            try:
                conn = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=30.0,
                    isolation_level=None,  # Autocommit mode
                )
                conn.row_factory = sqlite3.Row
                # Enable WAL and busy timeout for better concurrency
                try:
                    conn.execute("PRAGMA journal_mode=WAL")
                    conn.execute("PRAGMA busy_timeout=30000")
                except sqlite3.Error:
                    # Pragmas may fail on some SQLite builds; ignore
                    pass
                self._local.connection = conn
                self._local.db_path = self.db_path
            except sqlite3.Error as e:
                print(f"Database connection error: {e}")
                raise

        try:
            yield conn
        except sqlite3.Error as e:
            print(f"Database connection error: {e}")
            try:
                conn.rollback()
            except sqlite3.Error:
                pass
            raise

    def close_connection(self) -> None:
        """Explicitly close the thread-local database connection."""
        conn = getattr(self._local, "connection", None)
        if conn is not None:
            try:
                conn.close()
            except sqlite3.Error as e:
                print(f"Error closing database connection: {e}")
            finally:
                self._local.connection = None
                self._local.db_path = None

    def execute(self, sql: str, params: tuple = ()) -> bool:
        """Execute SQL statement with error handling

        Args:
            sql: SQL statement to execute
            params: Parameters for SQL statement

        Returns:
            True if successful, False otherwise
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                conn.commit()
                return True
        except sqlite3.Error as e:
            # Log error without exposing sensitive parameter values
            print(f"Error executing SQL: {e}")
            print(f"SQL: {sql}")
            # Don't log params - may contain sensitive data (PIN hashes, etc.)
            return False

    def fetch_one(self, sql: str, params: tuple = ()) -> Optional[Dict[str, Any]]:
        """Fetch single row from database

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            Dictionary of row data or None
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                row = cursor.fetchone()
                return dict(row) if row else None
        except sqlite3.Error as e:
            print(f"Error fetching data: {e}")
            return None

    def fetch_all(self, sql: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Fetch all rows from database

        Args:
            sql: SQL query
            params: Query parameters

        Returns:
            List of dictionaries containing row data
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except sqlite3.Error as e:
            print(f"Error fetching data: {e}")
            return []

    # ========== User Management ==========

    def create_user(
        self, username: str, pin_hash: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Create a new user

        Args:
            username: Unique username
            pin_hash: Optional hashed PIN for authentication

        Returns:
            User dictionary if successful, None otherwise
        """
        try:
            import uuid

            user_id = uuid.uuid4().hex

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO users (id, username, pin_hash, preferences)
                    VALUES (?, ?, ?, ?)
                """,
                    (user_id, username, pin_hash, json.dumps({})),
                )
                conn.commit()

            print(f"Created user: {username} (ID: {user_id})")
            return self.get_user(user_id)

        except sqlite3.IntegrityError:
            print(f"Username already exists: {username}")
            return None
        except sqlite3.Error as e:
            print(f"Error creating user: {e}")
            return None

    def get_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get user by ID

        Args:
            user_id: User ID

        Returns:
            User dictionary or None
        """
        user = self.fetch_one("SELECT * FROM users WHERE id = ?", (user_id,))

        if user and user.get("preferences"):
            try:
                user["preferences"] = json.loads(user["preferences"])
            except (json.JSONDecodeError, TypeError):
                user["preferences"] = {}

        return user

    def get_user_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        """Get user by username

        Args:
            username: Username to search for

        Returns:
            User dictionary or None
        """
        user = self.fetch_one("SELECT * FROM users WHERE username = ?", (username,))

        if user and user.get("preferences"):
            try:
                user["preferences"] = json.loads(user["preferences"])
            except (json.JSONDecodeError, TypeError):
                user["preferences"] = {}

        return user

    # Allowed columns for dynamic updates (security: prevent SQL injection via column names)
    _ALLOWED_USER_COLUMNS = {"username", "pin_hash", "last_login", "total_xp", "preferences"}

    def update_user(self, user_id: str, **kwargs) -> bool:
        """Update user fields

        Args:
            user_id: User ID to update
            **kwargs: Fields to update (last_login, total_xp, preferences, etc.)

        Returns:
            True if successful, False otherwise
        """
        if not kwargs:
            return False

        # Security: Validate column names against whitelist
        invalid_cols = set(kwargs.keys()) - self._ALLOWED_USER_COLUMNS
        if invalid_cols:
            # Log attempt but don't expose column names in error
            print(f"Warning: Rejected invalid column names in update_user")
            return False

        # Handle JSON serialization for preferences
        if "preferences" in kwargs and isinstance(kwargs["preferences"], dict):
            kwargs["preferences"] = json.dumps(kwargs["preferences"])

        # Build UPDATE query dynamically (column names validated above)
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = tuple(kwargs.values()) + (user_id,)

        sql = f"UPDATE users SET {set_clause} WHERE id = ?"
        return self.execute(sql, values)

    def update_last_login(self, user_id: str) -> bool:
        """Update user's last login timestamp

        Args:
            user_id: User ID

        Returns:
            True if successful
        """
        return self.update_user(user_id, last_login=datetime.now().isoformat())

    def list_users(self) -> List[Dict[str, Any]]:
        """Get all users

        Returns:
            List of user dictionaries
        """
        users = self.fetch_all("SELECT * FROM users ORDER BY created_at DESC")

        # Parse JSON preferences
        for user in users:
            if user.get("preferences"):
                try:
                    user["preferences"] = json.loads(user["preferences"])
                except (json.JSONDecodeError, TypeError):
                    user["preferences"] = {}

        return users

    def delete_user(self, user_id: str) -> bool:
        """Delete user and all associated data

        Args:
            user_id: User ID to delete

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Delete in order due to foreign keys
                cursor.execute("DELETE FROM review_items WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM progress WHERE user_id = ?", (user_id,))
                cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))

                conn.commit()
                print(f"Deleted user: {user_id}")
                return True

        except sqlite3.Error as e:
            print(f"Error deleting user: {e}")
            return False

    def hash_pin(self, pin: str) -> str:
        """Hash a PIN for secure storage

        Args:
            pin: Plain text PIN

        Returns:
            Hashed PIN string
        """
        return hashlib.sha256(pin.encode()).hexdigest()

    def verify_pin(self, user_id: str, pin: str) -> bool:
        """Verify user PIN

        Args:
            user_id: User ID
            pin: Plain text PIN to verify

        Returns:
            True if PIN matches, False otherwise
        """
        user = self.get_user(user_id)
        if not user or not user.get("pin_hash"):
            return False

        return user["pin_hash"] == self.hash_pin(pin)

    # ========== Progress Management ==========

    def get_progress(self, user_id: str, curriculum_id: str) -> Optional[Dict[str, Any]]:
        """Get progress for a user on a curriculum

        Args:
            user_id: User ID
            curriculum_id: Curriculum ID

        Returns:
            Progress dictionary or None
        """
        progress = self.fetch_one(
            """
            SELECT * FROM progress 
            WHERE user_id = ? AND curriculum_id = ?
        """,
            (user_id, curriculum_id),
        )

        if progress:
            # Parse JSON fields
            for field in ["completed_sections", "badges", "stats"]:
                if progress.get(field):
                    try:
                        progress[field] = json.loads(progress[field])
                    except (json.JSONDecodeError, TypeError):
                        progress[field] = [] if field in ["completed_sections", "badges"] else {}

        return progress

    def save_progress(self, user_id: str, curriculum_id: str, data: Dict[str, Any]) -> bool:
        """Save or update progress for a user on a curriculum

        Args:
            user_id: User ID
            curriculum_id: Curriculum ID
            data: Progress data (current_section, completed_sections, xp, badges, stats)

        Returns:
            True if successful
        """
        try:
            # Serialize JSON fields
            json_fields = {}
            for field in ["completed_sections", "badges", "stats"]:
                if field in data:
                    if isinstance(data[field], (list, dict)):
                        json_fields[field] = json.dumps(data[field])
                    else:
                        json_fields[field] = data[field]

            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Check if progress exists
                cursor.execute(
                    """
                    SELECT id FROM progress 
                    WHERE user_id = ? AND curriculum_id = ?
                """,
                    (user_id, curriculum_id),
                )

                exists = cursor.fetchone()

                if exists:
                    # Update existing progress
                    set_parts = []
                    values = []

                    if "current_section" in data:
                        set_parts.append("current_section = ?")
                        values.append(data["current_section"])

                    if "xp" in data:
                        set_parts.append("xp = ?")
                        values.append(data["xp"])

                    for field in ["completed_sections", "badges", "stats"]:
                        if field in json_fields:
                            set_parts.append(f"{field} = ?")
                            values.append(json_fields[field])

                    set_parts.append("updated_at = ?")
                    values.append(datetime.now().isoformat())

                    values.extend([user_id, curriculum_id])

                    sql = f"UPDATE progress SET {', '.join(set_parts)} WHERE user_id = ? AND curriculum_id = ?"
                    cursor.execute(sql, tuple(values))

                else:
                    # Insert new progress
                    cursor.execute(
                        """
                        INSERT INTO progress (
                            user_id, curriculum_id, current_section, 
                            completed_sections, xp, badges, stats
                        ) VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                        (
                            user_id,
                            curriculum_id,
                            data.get("current_section", 0),
                            json_fields.get("completed_sections", "[]"),
                            data.get("xp", 0),
                            json_fields.get("badges", "[]"),
                            json_fields.get("stats", "{}"),
                        ),
                    )

                conn.commit()

                # Update user's total XP if provided
                if "xp" in data:
                    self._update_user_total_xp(user_id, conn)

                return True

        except sqlite3.Error as e:
            print(f"Error saving progress: {e}")
            return False

    def _update_user_total_xp(self, user_id: str, conn: sqlite3.Connection) -> None:
        """Update user's total XP from all curricula

        Args:
            user_id: User ID
            conn: Database connection
        """
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT SUM(xp) as total_xp FROM progress WHERE user_id = ?
        """,
            (user_id,),
        )

        row = cursor.fetchone()
        total_xp = row["total_xp"] if row and row["total_xp"] else 0

        cursor.execute(
            """
            UPDATE users SET total_xp = ? WHERE id = ?
        """,
            (total_xp, user_id),
        )

    def get_user_all_progress(self, user_id: str) -> List[Dict[str, Any]]:
        """Get all progress records for a user

        Args:
            user_id: User ID

        Returns:
            List of progress dictionaries with curriculum info
        """
        progress_list = self.fetch_all(
            """
            SELECT 
                p.*,
                c.title as curriculum_title,
                c.subject,
                c.grade
            FROM progress p
            JOIN curricula c ON p.curriculum_id = c.id
            WHERE p.user_id = ?
            ORDER BY p.updated_at DESC
        """,
            (user_id,),
        )

        # Parse JSON fields
        for progress in progress_list:
            for field in ["completed_sections", "badges", "stats"]:
                if progress.get(field):
                    try:
                        progress[field] = json.loads(progress[field])
                    except (json.JSONDecodeError, TypeError):
                        progress[field] = [] if field in ["completed_sections", "badges"] else {}

        return progress_list

    def delete_progress(self, user_id: str, curriculum_id: str) -> bool:
        """Delete progress for a user on a curriculum

        Args:
            user_id: User ID
            curriculum_id: Curriculum ID

        Returns:
            True if successful
        """
        return self.execute(
            """
            DELETE FROM progress 
            WHERE user_id = ? AND curriculum_id = ?
        """,
            (user_id, curriculum_id),
        )

    # ========== Curricula Management ==========

    def register_curriculum(
        self,
        curriculum_id: str,
        title: str,
        subject: str,
        grade: str,
        file_path: str,
        created_by: Optional[str] = None,
        style: Optional[str] = None,
        language: Optional[str] = "English",
    ) -> bool:
        """Register curriculum metadata in database

        Args:
            curriculum_id: Unique curriculum ID
            title: Curriculum title
            subject: Subject area
            grade: Grade level
            file_path: Path to full curriculum JSON file
            created_by: Optional user ID of creator
            style: Optional teaching style
            language: Language (default: English)

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT OR REPLACE INTO curricula 
                    (id, title, subject, grade, style, language, file_path, created_by)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (curriculum_id, title, subject, grade, style, language, file_path, created_by),
                )
                conn.commit()
                print(f"Registered curriculum: {title} (ID: {curriculum_id})")
                return True

        except sqlite3.Error as e:
            print(f"Error registering curriculum: {e}")
            return False

    def get_curriculum_meta(self, curriculum_id: str) -> Optional[Dict[str, Any]]:
        """Get curriculum metadata

        Args:
            curriculum_id: Curriculum ID

        Returns:
            Curriculum metadata dictionary or None
        """
        return self.fetch_one("SELECT * FROM curricula WHERE id = ?", (curriculum_id,))

    def list_curricula(
        self,
        created_by: Optional[str] = None,
        subject: Optional[str] = None,
        grade: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List all curricula with optional filters

        Args:
            created_by: Filter by creator user ID
            subject: Filter by subject
            grade: Filter by grade

        Returns:
            List of curriculum metadata dictionaries
        """
        conditions = []
        params = []

        if created_by:
            conditions.append("created_by = ?")
            params.append(created_by)

        if subject:
            conditions.append("subject = ?")
            params.append(subject)

        if grade:
            conditions.append("grade = ?")
            params.append(grade)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        sql = f"SELECT * FROM curricula WHERE {where_clause} ORDER BY created_at DESC"

        return self.fetch_all(sql, tuple(params))

    def delete_curriculum(self, curriculum_id: str) -> bool:
        """Delete curriculum metadata and associated progress

        Args:
            curriculum_id: Curriculum ID

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Delete in order due to foreign keys
                cursor.execute("DELETE FROM review_items WHERE curriculum_id = ?", (curriculum_id,))
                cursor.execute("DELETE FROM progress WHERE curriculum_id = ?", (curriculum_id,))
                cursor.execute("DELETE FROM curricula WHERE id = ?", (curriculum_id,))

                conn.commit()
                print(f"Deleted curriculum: {curriculum_id}")
                return True

        except sqlite3.Error as e:
            print(f"Error deleting curriculum: {e}")
            return False

    # Allowed columns for curriculum updates (security: prevent SQL injection via column names)
    _ALLOWED_CURRICULUM_COLUMNS = {
        "title",
        "subject",
        "grade",
        "style",
        "language",
        "file_path",
        "created_by",
    }

    def update_curriculum(self, curriculum_id: str, **kwargs) -> bool:
        """Update curriculum metadata fields

        Args:
            curriculum_id: Curriculum ID
            **kwargs: Fields to update

        Returns:
            True if successful
        """
        if not kwargs:
            return False

        # Security: Validate column names against whitelist
        invalid_cols = set(kwargs.keys()) - self._ALLOWED_CURRICULUM_COLUMNS
        if invalid_cols:
            # Log attempt but don't expose column names in error
            print(f"Warning: Rejected invalid column names in update_curriculum")
            return False

        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = tuple(kwargs.values()) + (curriculum_id,)

        sql = f"UPDATE curricula SET {set_clause} WHERE id = ?"
        return self.execute(sql, values)

    # ========== Review Items (SRS) ==========

    def create_review_item(
        self,
        user_id: str,
        curriculum_id: str,
        card_front: str,
        card_back: str,
        item_id: Optional[str] = None,
    ) -> Optional[str]:
        """Create a new review item (flashcard)

        Args:
            user_id: User ID
            curriculum_id: Curriculum ID
            card_front: Front of flashcard (question)
            card_back: Back of flashcard (answer)
            item_id: Optional custom ID

        Returns:
            Item ID if successful, None otherwise
        """
        try:
            import uuid

            if not item_id:
                item_id = uuid.uuid4().hex

            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    INSERT INTO review_items 
                    (id, user_id, curriculum_id, card_front, card_back, next_review)
                    VALUES (?, ?, ?, ?, ?, ?)
                """,
                    (
                        item_id,
                        user_id,
                        curriculum_id,
                        card_front,
                        card_back,
                        datetime.now().isoformat(),
                    ),
                )
                conn.commit()
                return item_id

        except sqlite3.Error as e:
            print(f"Error creating review item: {e}")
            return None

    def get_due_reviews(self, user_id: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Get review items due for this user

        Args:
            user_id: User ID
            limit: Maximum number of items to return

        Returns:
            List of review item dictionaries
        """
        return self.fetch_all(
            """
            SELECT * FROM review_items
            WHERE user_id = ? AND next_review <= ?
            ORDER BY next_review
            LIMIT ?
        """,
            (user_id, datetime.now().isoformat(), limit),
        )

    def update_review_item(self, item_id: str, quality: int) -> bool:
        """Update review item after review (SM-2 algorithm)

        Args:
            item_id: Review item ID
            quality: Quality rating (0-5)

        Returns:
            True if successful
        """
        try:
            # Get current item
            item = self.fetch_one("SELECT * FROM review_items WHERE id = ?", (item_id,))
            if not item:
                return False

            # SM-2 algorithm
            ef = item["easiness_factor"]
            interval = item["interval"]
            reps = item["repetitions"]

            if quality >= 3:
                if reps == 0:
                    interval = 1
                elif reps == 1:
                    interval = 6
                else:
                    interval = round(interval * ef)
                reps += 1
            else:
                reps = 0
                interval = 1

            ef = max(1.3, ef + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02)))

            # Calculate next review date
            from datetime import timedelta

            next_review = datetime.now() + timedelta(days=interval)

            # Update item
            return self.execute(
                """
                UPDATE review_items
                SET easiness_factor = ?, interval = ?, repetitions = ?, next_review = ?
                WHERE id = ?
            """,
                (ef, interval, reps, next_review.isoformat(), item_id),
            )

        except Exception as e:
            print(f"Error updating review item: {e}")
            return False

    def get_review_stats(self, user_id: str) -> Dict[str, Any]:
        """Get review statistics for a user

        Args:
            user_id: User ID

        Returns:
            Dictionary with review stats
        """
        stats = {"total_cards": 0, "due_today": 0, "mastered": 0}

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Total cards
                cursor.execute(
                    "SELECT COUNT(*) as count FROM review_items WHERE user_id = ?", (user_id,)
                )
                row = cursor.fetchone()
                stats["total_cards"] = row["count"] if row else 0

                # Due today
                cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM review_items 
                    WHERE user_id = ? AND next_review <= ?
                """,
                    (user_id, datetime.now().isoformat()),
                )
                row = cursor.fetchone()
                stats["due_today"] = row["count"] if row else 0

                # Mastered (EF > 2.5 and interval > 21 days)
                cursor.execute(
                    """
                    SELECT COUNT(*) as count FROM review_items 
                    WHERE user_id = ? AND easiness_factor > 2.5 AND interval > 21
                """,
                    (user_id,),
                )
                row = cursor.fetchone()
                stats["mastered"] = row["count"] if row else 0

        except sqlite3.Error as e:
            print(f"Error getting review stats: {e}")

        return stats

    # ========== Migration Helper ==========

    def migrate_from_json(self, curricula_dir: str = "curricula") -> Dict[str, int]:
        """One-time migration from JSON files to database

        Args:
            curricula_dir: Directory containing curriculum JSON files

        Returns:
            Dictionary with migration statistics
        """
        stats = {"curricula_migrated": 0, "curricula_failed": 0, "errors": []}

        try:
            curricula_path = Path(curricula_dir)
            if not curricula_path.exists():
                stats["errors"].append(f"Directory not found: {curricula_dir}")
                return stats

            # Migrate curriculum files
            for json_file in curricula_path.glob("curriculum_*.json"):
                try:
                    with open(json_file, "r", encoding="utf-8") as f:
                        curriculum = json.load(f)

                    meta = curriculum.get("meta", {})

                    # Register curriculum
                    success = self.register_curriculum(
                        curriculum_id=meta.get("id", json_file.stem),
                        title=meta.get("topic", "Untitled"),
                        subject=meta.get("subject", "Unknown"),
                        grade=meta.get("grade", "Unknown"),
                        file_path=str(json_file),
                        style=meta.get("style"),
                        language=meta.get("language", "English"),
                    )

                    if success:
                        stats["curricula_migrated"] += 1
                    else:
                        stats["curricula_failed"] += 1

                except Exception as e:
                    stats["curricula_failed"] += 1
                    stats["errors"].append(f"Error migrating {json_file.name}: {e}")

            print(f"Migration complete: {stats['curricula_migrated']} curricula migrated")
            if stats["curricula_failed"] > 0:
                print(f"Failed: {stats['curricula_failed']} curricula")

        except Exception as e:
            stats["errors"].append(f"Migration error: {e}")
            print(f"Migration error: {e}")

        return stats

    # ========== Database Utilities ==========

    def backup_database(self, backup_path: Optional[str] = None) -> Tuple[bool, str]:
        """Create a backup of the database

        Args:
            backup_path: Optional custom backup path

        Returns:
            Tuple of (success, message)
        """
        try:
            if not backup_path:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_path = f"instaschool_backup_{timestamp}.db"

            # Use SQLite's backup API
            with self.get_connection() as source:
                dest = sqlite3.connect(backup_path)
                source.backup(dest)
                dest.close()

            return True, f"Backup created: {backup_path}"

        except Exception as e:
            return False, f"Backup failed: {e}"

    def get_database_stats(self) -> Dict[str, Any]:
        """Get database statistics

        Returns:
            Dictionary with database statistics
        """
        stats = {
            "users": 0,
            "curricula": 0,
            "progress_records": 0,
            "review_items": 0,
            "db_size_mb": 0,
        }

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()

                # Count records in each table
                for table in ["users", "curricula", "progress", "review_items"]:
                    cursor.execute(f"SELECT COUNT(*) as count FROM {table}")
                    row = cursor.fetchone()
                    key = table if table != "progress" else "progress_records"
                    stats[key] = row["count"] if row else 0

            # Get database file size
            if os.path.exists(self.db_path):
                stats["db_size_mb"] = round(os.path.getsize(self.db_path) / (1024 * 1024), 2)

        except sqlite3.Error as e:
            print(f"Error getting database stats: {e}")

        return stats

    def vacuum_database(self) -> bool:
        """Optimize and compact database

        Returns:
            True if successful
        """
        try:
            with self.get_connection() as conn:
                conn.execute("VACUUM")
                conn.commit()
            print("Database vacuumed successfully")
            return True
        except sqlite3.Error as e:
            print(f"Error vacuuming database: {e}")
            return False


# ========== Cached Singleton Factory ==========
if HAS_STREAMLIT:

    @st.cache_resource
    def get_database_service():
        """Get cached DatabaseService singleton"""
        return DatabaseService()
else:
    # Fallback for non-Streamlit contexts
    _db_instance = None

    def get_database_service():
        """Get DatabaseService singleton (non-cached fallback)"""
        global _db_instance
        if _db_instance is None:
            _db_instance = DatabaseService()
        return _db_instance
