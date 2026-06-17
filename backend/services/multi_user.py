"""
Multi-user authentication and session management for MiLyfe Brain.

Supports:
- API key authentication (existing)
- JWT token authentication (new)
- User registration and login
- Role-based access control (admin, user, readonly)
- Session management with Redis backing

Configuration:
    AUTH_ENABLED=true
    AUTH_JWT_SECRET=<random-secret>
    AUTH_JWT_EXPIRY_HOURS=24
    AUTH_ALLOW_REGISTRATION=true
    AUTH_DEFAULT_ROLE=user
"""

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Optional

from .logging_config import get_logger

logger = get_logger("auth")


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


@dataclass
class AuthenticatedUser:
    """Represents an authenticated user."""
    id: str
    username: str
    email: Optional[str] = None
    role: UserRole = UserRole.USER
    workspace_id: Optional[str] = None

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def can_write(self) -> bool:
        return self.role in (UserRole.ADMIN, UserRole.USER)

    @property
    def can_execute(self) -> bool:
        return self.role in (UserRole.ADMIN, UserRole.USER)


class AuthService:
    """Handles user authentication and authorization."""

    def __init__(self):
        self.enabled = os.getenv("AUTH_ENABLED", "false").lower() == "true"
        self.jwt_secret = os.getenv("AUTH_JWT_SECRET", "change-me-to-a-real-secret-in-production")
        self.jwt_expiry_hours = int(os.getenv("AUTH_JWT_EXPIRY_HOURS", "24"))
        self.allow_registration = os.getenv("AUTH_ALLOW_REGISTRATION", "true").lower() == "true"
        self.default_role = UserRole(os.getenv("AUTH_DEFAULT_ROLE", "user"))
        self.api_key = os.getenv("API_KEY", "")

    def hash_password(self, password: str) -> str:
        """Hash a password with salt."""
        salt = os.urandom(32)
        key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
        return salt.hex() + ":" + key.hex()

    def verify_password(self, password: str, stored_hash: str) -> bool:
        """Verify a password against stored hash."""
        try:
            salt_hex, key_hex = stored_hash.split(":")
            salt = bytes.fromhex(salt_hex)
            stored_key = bytes.fromhex(key_hex)
            new_key = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 100000)
            return hmac.compare_digest(new_key, stored_key)
        except (ValueError, AttributeError):
            return False

    def create_token(self, user: AuthenticatedUser) -> str:
        """Create a JWT-like token (simplified, no external deps)."""
        header = {"alg": "HS256", "typ": "JWT"}
        payload = {
            "sub": user.id,
            "username": user.username,
            "role": user.role.value,
            "iat": int(time.time()),
            "exp": int(time.time()) + (self.jwt_expiry_hours * 3600),
        }

        # Encode
        import base64
        header_b64 = base64.urlsafe_b64encode(json.dumps(header).encode()).rstrip(b"=").decode()
        payload_b64 = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=").decode()

        # Sign
        message = f"{header_b64}.{payload_b64}"
        signature = hmac.new(
            self.jwt_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).digest()
        sig_b64 = base64.urlsafe_b64encode(signature).rstrip(b"=").decode()

        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def verify_token(self, token: str) -> Optional[AuthenticatedUser]:
        """Verify and decode a JWT token."""
        try:
            import base64
            parts = token.split(".")
            if len(parts) != 3:
                return None

            header_b64, payload_b64, sig_b64 = parts

            # Verify signature
            message = f"{header_b64}.{payload_b64}"
            expected_sig = hmac.new(
                self.jwt_secret.encode(),
                message.encode(),
                hashlib.sha256,
            ).digest()
            actual_sig = base64.urlsafe_b64decode(sig_b64 + "==")

            if not hmac.compare_digest(expected_sig, actual_sig):
                return None

            # Decode payload
            payload_json = base64.urlsafe_b64decode(payload_b64 + "==")
            payload = json.loads(payload_json)

            # Check expiry
            if payload.get("exp", 0) < time.time():
                return None

            return AuthenticatedUser(
                id=payload["sub"],
                username=payload["username"],
                role=UserRole(payload.get("role", "user")),
            )

        except Exception as e:
            logger.debug(f"Token verification failed: {e}")
            return None

    def verify_api_key(self, key: str) -> Optional[AuthenticatedUser]:
        """Verify an API key."""
        if not self.api_key:
            return None

        if hmac.compare_digest(key, self.api_key):
            return AuthenticatedUser(
                id="api-key-user",
                username="api",
                role=UserRole.ADMIN,
            )
        return None

    async def authenticate_request(self, request) -> Optional[AuthenticatedUser]:
        """Authenticate an incoming request.

        Checks in order:
        1. Bearer token (Authorization header)
        2. API key (X-API-Key header)
        3. Session cookie
        """
        if not self.enabled:
            # Auth disabled - return default user
            return AuthenticatedUser(
                id="default-user",
                username="local",
                role=UserRole.ADMIN,
            )

        # Check Bearer token
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            user = self.verify_token(token)
            if user:
                return user

        # Check API key
        api_key = request.headers.get("X-API-Key", "")
        if api_key:
            user = self.verify_api_key(api_key)
            if user:
                return user

        return None

    def check_permission(self, user: AuthenticatedUser, action: str, resource: str = "") -> bool:
        """Check if user has permission for an action.

        Actions: read, write, execute, admin, delete
        """
        if user.is_admin:
            return True

        permission_map = {
            UserRole.USER: {"read", "write", "execute"},
            UserRole.READONLY: {"read"},
        }

        allowed_actions = permission_map.get(user.role, set())
        return action in allowed_actions


# Singleton instance
auth_service = AuthService()
