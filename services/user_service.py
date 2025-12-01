"""
User Service - Database-backed user management with PIN authentication

Migrated from JSON file storage to SQLite database via DatabaseService.
Maintains backward compatibility with existing username-salted PIN hashes.

NOTE: This is a simple PIN-based system for educational context.
For production use, consider a proper authentication system with:
- Secure password hashing (bcrypt/argon2)
- Database storage
- Session management
- Rate limiting
"""

import json
import hashlib
import secrets
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # For type checkers only; avoids import-time issues
    from services.database_service import DatabaseService


class UserService:
    """Database-backed user management with simple PIN authentication."""

    def __init__(self, users_dir: str = "users", db_path: str = "instaschool.db") -> None:
        from services.database_service import DatabaseService

        self.users_dir = Path(users_dir)
        self.users_dir.mkdir(exist_ok=True)  # Keep for backward compatibility
        self.db = DatabaseService(db_path)
        self._migrate_existing_users()

    def _hash_pin_legacy(self, username: str, pin: str) -> str:
        """Legacy PIN hash using simple SHA-256 with username salt."""
        combined = f"{username.lower()}:{pin}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _hash_pin(self, username: str, pin: str) -> str:
        """Hash PIN using PBKDF2 with a random salt.

        Returns a hex-encoded 'salt:hash' string.
        """
        combined = f"{username.lower()}:{pin}".encode()
        salt = secrets.token_bytes(32)
        key = hashlib.pbkdf2_hmac("sha256", combined, salt, 100_000)
        return f"{salt.hex()}:{key.hex()}"

    def _verify_and_maybe_upgrade_pin(self, user: Dict, pin: str) -> bool:
        """Verify PIN against stored hash and upgrade legacy hashes to PBKDF2."""
        stored_hash = user.get("pin_hash")
        if not stored_hash or pin is None:
            return False

        username = user.get("username", "")

        # New format: 'salt:hash'
        if ":" in stored_hash:
            try:
                salt_hex, key_hex = stored_hash.split(":", 1)
                salt = bytes.fromhex(salt_hex)
                stored_key = bytes.fromhex(key_hex)
            except (ValueError, TypeError):
                # Malformed hash: treat as failure
                return False

            combined = f"{username.lower()}:{pin}".encode()
            computed_key = hashlib.pbkdf2_hmac("sha256", combined, salt, 100_000)
            return secrets.compare_digest(computed_key, stored_key)

        # Legacy SHA-256 format
        if self._hash_pin_legacy(username, pin) == stored_hash:
            # Migrate to PBKDF2 format on successful verification
            try:
                new_hash = self._hash_pin(username, pin)
                self.db.update_user(user["id"], pin_hash=new_hash)
            except Exception:
                # Migration failure should not block a successful login
                pass
            return True

        return False

    def _generate_user_id(self, username: str) -> str:
        """Generate a unique user ID from username."""
        return hashlib.md5(username.lower().encode()).hexdigest()[:8]

    def _migrate_existing_users(self) -> None:
        """One-time migration: Move existing JSON user files to SQLite database."""
        try:
            # Check if any JSON files exist
            json_files = list(self.users_dir.glob("*.json"))
            if not json_files:
                return  # No files to migrate

            # Check if migration already done (users exist in DB)
            existing_users = self.db.list_users()
            if existing_users:
                return  # Migration already completed

            print(f"Migrating {len(json_files)} user(s) from JSON to database...")

            migrated = 0
            for user_file in json_files:
                try:
                    with open(user_file, "r", encoding="utf-8") as f:
                        user_data = json.load(f)

                    # Extract user info
                    username = user_data.get("username")
                    if not username:
                        continue

                    # Create user in database with existing PIN hash
                    # Note: DatabaseService create_user expects pin_hash parameter
                    result = self.db.create_user(
                        username=username,
                        pin_hash=user_data.get("pin_hash")  # Keep existing hash
                    )

                    if result:
                        user_id = result["id"]
                        
                        # Update additional fields
                        self.db.update_user(
                            user_id,
                            total_xp=user_data.get("total_xp", 0),
                            last_login=user_data.get("last_login"),
                            preferences=json.dumps({
                                "badges": user_data.get("badges", []),
                                "has_pin": user_data.get("has_pin", False),
                                "created_at": user_data.get("created_at")
                            })
                        )
                        
                        migrated += 1
                        print(f"  ✓ Migrated user: {username}")

                except Exception as e:
                    print(f"  ✗ Error migrating {user_file.name}: {e}")
                    continue

            print(f"Migration complete: {migrated}/{len(json_files)} users migrated")

        except Exception as e:
            print(f"Migration error: {e}")

    def authenticate(self, username: str, pin: Optional[str] = None) -> Tuple[Optional[Dict], str]:
        """
        Authenticate a user with username and PIN.

        Args:
            username: The username to authenticate
            pin: The user's PIN (4-6 digits)

        Returns:
            Tuple of (user_data, message)
            - If successful: (user_dict, "success")
            - If user exists but wrong PIN: (None, "invalid_pin")
            - If new user created: (user_dict, "created")
            - If PIN required for existing user: (None, "pin_required")
        """
        # Get user from database
        user = self.db.get_user_by_username(username)

        if user:
            # Check if user has a PIN set
            if user.get("pin_hash"):
                if pin is None:
                    return None, "pin_required"

                # Verify PIN (supports legacy + PBKDF2 formats, migrates on success)
                if not self._verify_and_maybe_upgrade_pin(user, pin):
                    return None, "invalid_pin"

            # Update last login
            self.db.update_last_login(user["id"])
            
            # Reload user to get updated timestamp
            user = self.db.get_user(user["id"])
            
            # Format response to match expected structure
            return self._format_user_response(user), "success"

        # New user - return not found
        return None, "user_not_found"

    def create_user(self, username: str, pin: Optional[str] = None) -> Tuple[Dict, str]:
        """
        Create a new user account.

        Args:
            username: The username for the new account
            pin: Optional PIN (4-6 digits) for account security

        Returns:
            Tuple of (user_data, message)
        """
        # Check if user already exists
        existing_user = self.db.get_user_by_username(username)
        if existing_user:
            return {}, "user_exists"

        # Create PIN hash if provided (secure PBKDF2 with per-user salt)
        pin_hash = self._hash_pin(username, pin) if pin else None

        # Create user in database
        user = self.db.create_user(username=username, pin_hash=pin_hash)
        
        if not user:
            return {}, "creation_failed"

        # Initialize preferences with backward-compatible structure
        self.db.update_user(
            user["id"],
            preferences=json.dumps({
                "badges": [],
                "has_pin": bool(pin),
                "created_at": user.get("created_at")
            })
        )

        # Reload user with preferences
        user = self.db.get_user(user["id"])
        
        return self._format_user_response(user), "created"

    def set_pin(self, username: str, old_pin: Optional[str], new_pin: str) -> Tuple[bool, str]:
        """
        Set or change a user's PIN.

        Args:
            username: The username
            old_pin: Current PIN (None if no PIN set)
            new_pin: New PIN to set (4-6 digits)

        Returns:
            Tuple of (success, message)
        """
        # Get user from database
        user = self.db.get_user_by_username(username)
        if not user:
            return False, "user_not_found"

        # Verify old PIN if one exists
        if user.get("pin_hash") and old_pin:
            if not self._verify_and_maybe_upgrade_pin(user, old_pin):
                return False, "invalid_pin"
        elif user.get("pin_hash") and not old_pin:
            return False, "old_pin_required"

        # Validate new PIN
        if not new_pin or len(new_pin) < 4 or len(new_pin) > 6:
            return False, "invalid_new_pin"
        if not new_pin.isdigit():
            return False, "pin_must_be_digits"

        # Set new PIN (secure hash)
        new_pin_hash = self._hash_pin(username, new_pin)
        
        # Update user in database
        success = self.db.update_user(user["id"], pin_hash=new_pin_hash)
        
        if success:
            # Update preferences to reflect PIN status
            prefs = user.get("preferences", {})
            if isinstance(prefs, str):
                prefs = json.loads(prefs)
            prefs["has_pin"] = True
            self.db.update_user(user["id"], preferences=json.dumps(prefs))
            
        return success, "pin_updated" if success else "update_failed"

    def remove_pin(self, username: str, current_pin: str) -> Tuple[bool, str]:
        """Remove PIN from user account (revert to profile switching)."""
        # Get user from database
        user = self.db.get_user_by_username(username)
        if not user:
            return False, "user_not_found"

        # Verify current PIN
        if user.get("pin_hash"):
            if not self._verify_and_maybe_upgrade_pin(user, current_pin):
                return False, "invalid_pin"

        # Remove PIN from database
        success = self.db.update_user(user["id"], pin_hash=None)
        
        if success:
            # Update preferences to reflect PIN removal
            prefs = user.get("preferences", {})
            if isinstance(prefs, str):
                prefs = json.loads(prefs)
            prefs["has_pin"] = False
            self.db.update_user(user["id"], preferences=json.dumps(prefs))
            
        return success, "pin_removed" if success else "update_failed"

    def user_exists(self, username: str) -> bool:
        """Check if a user exists."""
        user = self.db.get_user_by_username(username)
        return user is not None

    def user_has_pin(self, username: str) -> bool:
        """Check if a user has a PIN set."""
        user = self.db.get_user_by_username(username)
        if not user:
            return False
        return bool(user.get("pin_hash"))

    def get_user(self, username: str) -> Optional[Dict]:
        """Get user data without authentication (for display purposes only)."""
        user = self.db.get_user_by_username(username)
        if not user:
            return None

        # Format response and don't expose PIN hash
        response = self._format_user_response(user)
        response.pop("pin_hash", None)
        return response

    def _save_user(self, user_data: Dict) -> None:
        """DEPRECATED: Kept for backward compatibility during migration."""
        # This method is no longer used as we now use DatabaseService
        pass

    def list_users(self) -> list:
        """List all users with metadata (for profile switching UI).

        Returns:
            List of dicts with username, has_pin, total_xp keys.
        """
        db_users = self.db.list_users()

        users = []
        for user in db_users:
            # Extract preferences
            prefs = user.get("preferences", {})
            if isinstance(prefs, str):
                try:
                    prefs = json.loads(prefs)
                except json.JSONDecodeError:
                    prefs = {}

            users.append({
                "username": user.get("username"),
                "has_pin": bool(user.get("pin_hash")) or prefs.get("has_pin", False),
                "total_xp": user.get("total_xp", 0),
            })

        return sorted(users, key=lambda x: x.get("username", "").lower())

    def list_usernames(self) -> list:
        """List all usernames as simple strings.

        Use this for selectboxes where you need simple string options.

        Returns:
            List of username strings, sorted alphabetically.
        """
        db_users = self.db.list_users()
        usernames = [user.get("username") for user in db_users if user.get("username")]
        return sorted(usernames, key=str.lower)

    def _format_user_response(self, user: Dict) -> Dict:
        """Format database user record to match expected response structure."""
        # Parse preferences if it's a JSON string
        prefs = user.get("preferences", {})
        if isinstance(prefs, str):
            try:
                prefs = json.loads(prefs)
            except json.JSONDecodeError:
                prefs = {}
        
        # Build response with backward-compatible structure
        return {
            "id": user.get("id"),
            "username": user.get("username"),
            "created_at": prefs.get("created_at") or user.get("created_at"),
            "last_login": user.get("last_login"),
            "badges": prefs.get("badges", []),
            "total_xp": user.get("total_xp", 0),
            "pin_hash": user.get("pin_hash"),
            "has_pin": bool(user.get("pin_hash")) or prefs.get("has_pin", False),
        }
