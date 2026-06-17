"""MiLyfe Brain — Multi-User / Team Mode.

User profiles, RBAC, shared playbook library, approval chains.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Dict, List, Optional

import structlog

logger = structlog.get_logger()

# In-memory user store (SQLite-backed in production)
_users: Dict[str, Dict] = {}
_sessions: Dict[str, str] = {}  # token -> user_id

# Default roles
ROLES = {
    "admin": {"permissions": ["*"]},
    "user": {"permissions": ["playbook.create", "playbook.read", "chat", "view"]},
    "viewer": {"permissions": ["playbook.read", "view"]},
}


class MultiUserService:
    """Multi-user support with local auth (no cloud)."""

    async def create_user(
        self, username: str, password: str, role: str = "user"
    ) -> Dict:
        """Create a new user."""
        if username in _users:
            raise ValueError(f"User exists: {username}")
        if role not in ROLES:
            raise ValueError(f"Invalid role: {role}")

        user_id = str(uuid.uuid4())
        password_hash = hashlib.sha256(password.encode()).hexdigest()

        _users[username] = {
            "id": user_id,
            "username": username,
            "password_hash": password_hash,
            "role": role,
            "created_at": datetime.utcnow().isoformat(),
            "last_login": None,
        }

        return {"id": user_id, "username": username, "role": role}

    async def authenticate(self, username: str, password: str) -> Optional[str]:
        """Authenticate and return session token."""
        user = _users.get(username)
        if not user:
            return None

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user["password_hash"] != password_hash:
            return None

        token = str(uuid.uuid4())
        _sessions[token] = username
        user["last_login"] = datetime.utcnow().isoformat()

        return token

    async def get_user_from_token(self, token: str) -> Optional[Dict]:
        """Get user from session token."""
        username = _sessions.get(token)
        if not username:
            return None
        return _users.get(username)

    async def check_permission(self, token: str, permission: str) -> bool:
        """Check if user has a specific permission."""
        user = await self.get_user_from_token(token)
        if not user:
            return False

        role = user.get("role", "viewer")
        role_perms = ROLES.get(role, {}).get("permissions", [])

        return "*" in role_perms or permission in role_perms

    async def list_users(self) -> List[Dict]:
        """List all users (without passwords)."""
        return [
            {"id": u["id"], "username": u["username"], "role": u["role"], "last_login": u["last_login"]}
            for u in _users.values()
        ]

    async def delete_user(self, username: str):
        """Delete a user."""
        _users.pop(username, None)
        # Clean sessions
        to_remove = [t for t, u in _sessions.items() if u == username]
        for t in to_remove:
            del _sessions[t]

    async def logout(self, token: str):
        """Invalidate a session."""
        _sessions.pop(token, None)


# Singleton
multi_user_service = MultiUserService()
