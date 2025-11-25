"""
User Service - File-based user management with PIN authentication

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
from typing import Dict, Optional, Tuple


class UserService:
    """File-based user management with simple PIN authentication."""

    def __init__(self, users_dir: str = "users") -> None:
        self.users_dir = Path(users_dir)
        self.users_dir.mkdir(exist_ok=True)

    def _hash_pin(self, username: str, pin: str) -> str:
        """Hash PIN with username as salt for storage."""
        combined = f"{username.lower()}:{pin}"
        return hashlib.sha256(combined.encode()).hexdigest()

    def _generate_user_id(self, username: str) -> str:
        """Generate a unique user ID from username."""
        return hashlib.md5(username.lower().encode()).hexdigest()[:8]

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
        user_id = self._generate_user_id(username)
        user_file = self.users_dir / f"{user_id}.json"

        if user_file.exists():
            with open(user_file, "r", encoding="utf-8") as f:
                user_data = json.load(f)

            # Check if user has a PIN set
            if user_data.get("pin_hash"):
                if pin is None:
                    return None, "pin_required"

                # Verify PIN
                pin_hash = self._hash_pin(username, pin)
                if pin_hash != user_data["pin_hash"]:
                    return None, "invalid_pin"

            # Update last login
            user_data["last_login"] = datetime.now().isoformat()
            self._save_user(user_data)
            return user_data, "success"

        # New user - PIN is optional but recommended
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
        user_id = self._generate_user_id(username)
        user_file = self.users_dir / f"{user_id}.json"

        if user_file.exists():
            return {}, "user_exists"

        user_data: Dict = {
            "id": user_id,
            "username": username,
            "created_at": datetime.now().isoformat(),
            "last_login": datetime.now().isoformat(),
            "badges": [],
            "total_xp": 0,
            "pin_hash": self._hash_pin(username, pin) if pin else None,
            "has_pin": bool(pin),
        }
        self._save_user(user_data)
        return user_data, "created"

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
        user_id = self._generate_user_id(username)
        user_file = self.users_dir / f"{user_id}.json"

        if not user_file.exists():
            return False, "user_not_found"

        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        # Verify old PIN if one exists
        if user_data.get("pin_hash") and old_pin:
            if self._hash_pin(username, old_pin) != user_data["pin_hash"]:
                return False, "invalid_pin"
        elif user_data.get("pin_hash") and not old_pin:
            return False, "old_pin_required"

        # Validate new PIN
        if not new_pin or len(new_pin) < 4 or len(new_pin) > 6:
            return False, "invalid_new_pin"
        if not new_pin.isdigit():
            return False, "pin_must_be_digits"

        # Set new PIN
        user_data["pin_hash"] = self._hash_pin(username, new_pin)
        user_data["has_pin"] = True
        self._save_user(user_data)
        return True, "pin_updated"

    def remove_pin(self, username: str, current_pin: str) -> Tuple[bool, str]:
        """Remove PIN from user account (revert to profile switching)."""
        user_id = self._generate_user_id(username)
        user_file = self.users_dir / f"{user_id}.json"

        if not user_file.exists():
            return False, "user_not_found"

        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        # Verify current PIN
        if user_data.get("pin_hash"):
            if self._hash_pin(username, current_pin) != user_data["pin_hash"]:
                return False, "invalid_pin"

        user_data["pin_hash"] = None
        user_data["has_pin"] = False
        self._save_user(user_data)
        return True, "pin_removed"

    def user_exists(self, username: str) -> bool:
        """Check if a user exists."""
        user_id = self._generate_user_id(username)
        return (self.users_dir / f"{user_id}.json").exists()

    def user_has_pin(self, username: str) -> bool:
        """Check if a user has a PIN set."""
        user_id = self._generate_user_id(username)
        user_file = self.users_dir / f"{user_id}.json"

        if not user_file.exists():
            return False

        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)
        return user_data.get("has_pin", False)

    def get_user(self, username: str) -> Optional[Dict]:
        """Get user data without authentication (for display purposes only)."""
        user_id = self._generate_user_id(username)
        user_file = self.users_dir / f"{user_id}.json"

        if not user_file.exists():
            return None

        with open(user_file, "r", encoding="utf-8") as f:
            user_data = json.load(f)

        # Don't expose PIN hash
        user_data.pop("pin_hash", None)
        return user_data

    def _save_user(self, user_data: Dict) -> None:
        """Persist user data to disk."""
        with open(self.users_dir / f"{user_data['id']}.json", "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=2)

    def list_users(self) -> list:
        """List all usernames (for profile switching UI)."""
        users = []
        for user_file in self.users_dir.glob("*.json"):
            try:
                with open(user_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    users.append({
                        "username": data.get("username"),
                        "has_pin": data.get("has_pin", False),
                        "total_xp": data.get("total_xp", 0),
                    })
            except (json.JSONDecodeError, IOError):
                continue
        return sorted(users, key=lambda x: x.get("username", "").lower())
