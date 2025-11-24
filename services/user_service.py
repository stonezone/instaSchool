import json
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Dict


class UserService:
    """Simple file-based user management service."""

    def __init__(self, users_dir: str = "users") -> None:
        self.users_dir = Path(users_dir)
        self.users_dir.mkdir(exist_ok=True)

    def authenticate(self, username: str) -> Dict:
        """Authenticate a user, creating a new record if needed."""
        user_id = hashlib.md5(username.lower().encode()).hexdigest()[:8]
        user_file = self.users_dir / f"{user_id}.json"

        if user_file.exists():
            with open(user_file, "r", encoding="utf-8") as f:
                return json.load(f)

        # Create new user
        user_data: Dict = {
            "id": user_id,
            "username": username,
            "created_at": datetime.now().isoformat(),
            "badges": [],
            "total_xp": 0,
        }
        self._save_user(user_data)
        return user_data

    def _save_user(self, user_data: Dict) -> None:
        """Persist user data to disk."""
        with open(self.users_dir / f"{user_data['id']}.json", "w", encoding="utf-8") as f:
            json.dump(user_data, f, indent=2)

