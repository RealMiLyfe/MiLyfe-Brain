"""
MiLyfe Brain - Multi-User Service

Provides basic multi-user support with authentication and
role-based permissions. Stub implementation for local-first use.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# In-memory user store (would be backed by DB in production)
_users: Dict[str, Dict[str, Any]] = {
    "admin": {
        "id": "admin",
        "username": "admin",
        "role": "admin",
        "created_at": datetime.utcnow().isoformat(),
        "password_hash": hashlib.sha256(b"admin").hexdigest(),
        "api_key": None,
    },
}

# Permission matrix
_ROLE_PERMISSIONS: Dict[str, List[str]] = {
    "admin": ["*"],  # All permissions
    "user": [
        "playbook.create", "playbook.read", "playbook.run",
        "chat.send", "chat.read",
        "memory.read", "memory.write",
        "settings.read",
    ],
    "viewer": [
        "playbook.read", "chat.read", "memory.read", "settings.read",
    ],
}


async def create_user(
    username: str,
    password: str,
    role: str = "user",
) -> Dict[str, Any]:
    """
    Create a new user account.

    Args:
        username: Unique username.
        password: User password.
        role: User role ('admin', 'user', 'viewer').

    Returns:
        Dict with user info (excluding password).
    """
    if username in _users:
        return {"error": f"User '{username}' already exists"}

    if role not in _ROLE_PERMISSIONS:
        return {"error": f"Invalid role: {role}"}

    password_hash = hashlib.sha256(password.encode()).hexdigest()
    api_key = secrets.token_urlsafe(32)

    user = {
        "id": username,
        "username": username,
        "role": role,
        "created_at": datetime.utcnow().isoformat(),
        "password_hash": password_hash,
        "api_key": api_key,
    }
    _users[username] = user

    logger.info("User created: %s (role=%s)", username, role)

    # Return without password hash
    return {
        "id": username,
        "username": username,
        "role": role,
        "api_key": api_key,
        "created_at": user["created_at"],
    }


async def authenticate(
    username: Optional[str] = None,
    password: Optional[str] = None,
    api_key: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Authenticate a user by username/password or API key.

    Args:
        username: Username for password auth.
        password: Password for password auth.
        api_key: API key for token auth.

    Returns:
        User info dict if authenticated, None otherwise.
    """
    # API key auth
    if api_key:
        for user in _users.values():
            if user.get("api_key") == api_key:
                return {
                    "id": user["id"],
                    "username": user["username"],
                    "role": user["role"],
                }
        return None

    # Password auth
    if username and password:
        user = _users.get(username)
        if user is None:
            return None

        password_hash = hashlib.sha256(password.encode()).hexdigest()
        if user["password_hash"] == password_hash:
            return {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
            }

    return None


def check_permission(user_role: str, permission: str) -> bool:
    """
    Check if a role has a specific permission.

    Args:
        user_role: The user's role.
        permission: Required permission string (e.g., 'playbook.create').

    Returns:
        True if permitted, False otherwise.
    """
    perms = _ROLE_PERMISSIONS.get(user_role, [])
    if "*" in perms:
        return True
    return permission in perms


async def list_users() -> List[Dict[str, Any]]:
    """
    List all users (without sensitive fields).

    Returns:
        List of user info dicts.
    """
    return [
        {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "created_at": user["created_at"],
        }
        for user in _users.values()
    ]
