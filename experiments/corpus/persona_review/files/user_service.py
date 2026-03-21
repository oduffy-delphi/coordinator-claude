"""User management service with validation, soft-delete, and search.

Provides CRUD operations against an in-memory store with email
uniqueness enforcement and role-based access patterns.
"""

from __future__ import annotations

import hashlib
import re
import secrets
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

EMAIL_PATTERN = re.compile(
    r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(\.[a-zA-Z0-9-]+)*\.[a-zA-Z]{2,}$"
)

MIN_PASSWORD_LENGTH = 8
MAX_DISPLAY_NAME_LENGTH = 64
SALT_LENGTH = 32


class Role(str, Enum):
    USER = "user"
    ADMIN = "admin"
    MODERATOR = "moderator"


@dataclass
class User:
    """Represents a user account."""

    user_id: str
    email: str
    display_name: str
    password_hash: str
    salt: str
    role: Role = Role.USER
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    is_deleted: bool = False
    login_attempts: int = 0
    last_login: float | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def _hash_password(password: str, salt: str) -> str:
    """Hash a password with the given salt using SHA-256."""
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()


def _generate_salt() -> str:
    """Generate a cryptographically random salt."""
    return secrets.token_hex(SALT_LENGTH)


class UserService:
    """In-memory user management service."""

    def __init__(self) -> None:
        self._users: dict[str, User] = {}
        self._email_index: dict[str, str] = {}  # email → user_id

    def create_user(
        self,
        user_id: str,
        email: str,
        display_name: str,
        password: str,
        role: Role = Role.USER,
    ) -> User:
        """Create a new user account with validation."""
        email = email.strip().lower()

        # Validate email format
        if not EMAIL_PATTERN.match(email):
            raise ValueError(f"Invalid email format: {email}")

        # Check uniqueness
        if email in self._email_index:
            raise ValueError(f"Email already registered: {email}")

        # Validate password strength
        if len(password) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
            )

        # Validate display name
        if not display_name.strip():
            raise ValueError("Display name cannot be empty")
        if len(display_name) > MAX_DISPLAY_NAME_LENGTH:
            raise ValueError(
                f"Display name exceeds {MAX_DISPLAY_NAME_LENGTH} characters"
            )

        salt = _generate_salt()
        user = User(
            user_id=user_id,
            email=email,
            display_name=display_name.strip(),
            password_hash=_hash_password(password, salt),
            salt=salt,
            role=role,
        )

        self._users[user_id] = user
        self._email_index[email] = user_id
        return user

    def get_user(self, user_id: str) -> User | None:
        """Retrieve a user by ID. Returns None for deleted users."""
        user = self._users.get(user_id)
        if user is None or user.is_deleted:
            return None
        return user

    def get_by_email(self, email: str) -> User | None:
        """Look up a user by email address."""
        email = email.strip().lower()
        user_id = self._email_index.get(email)
        if user_id is None:
            return None
        return self._users.get(user_id)

    def authenticate(self, email: str, password: str) -> User | None:
        """Authenticate a user by email and password.

        Returns the user on success, None on failure.
        Tracks failed login attempts.
        """
        user = self.get_by_email(email)
        if user is None:
            return None

        if user.is_deleted:
            return None

        expected_hash = _hash_password(password, user.salt)
        if user.password_hash != expected_hash:
            user.login_attempts += 1
            return None

        user.login_attempts = 0
        user.last_login = time.time()
        return user

    def update_user(
        self,
        user_id: str,
        display_name: str | None = None,
        email: str | None = None,
        role: Role | None = None,
    ) -> User:
        """Update user fields. Only provided fields are changed."""
        user = self.get_user(user_id)
        if user is None:
            raise KeyError(f"User not found: {user_id}")

        if display_name is not None:
            if not display_name.strip():
                raise ValueError("Display name cannot be empty")
            user.display_name = display_name.strip()

        if email is not None:
            email = email.strip().lower()
            if not EMAIL_PATTERN.match(email):
                raise ValueError(f"Invalid email format: {email}")
            if email != user.email and email in self._email_index:
                raise ValueError(f"Email already registered: {email}")
            # Update email index
            del self._email_index[user.email]
            self._email_index[email] = user_id
            user.email = email

        if role is not None:
            user.role = role

        user.updated_at = time.time()
        return user

    def delete_user(self, user_id: str) -> bool:
        """Soft-delete a user. Returns True if the user existed."""
        user = self._users.get(user_id)
        if user is None or user.is_deleted:
            return False

        user.is_deleted = True
        user.updated_at = time.time()
        return True

    def search_users(
        self,
        query: str,
        include_deleted: bool = False,
        role: Role | None = None,
        limit: int = 50,
    ) -> list[User]:
        """Search users by display name or email prefix."""
        query_lower = query.strip().lower()
        results: list[User] = []

        for user in self._users.values():
            if not include_deleted and user.is_deleted:
                continue
            if role is not None and user.role != role:
                continue

            if (
                query_lower in user.display_name.lower()
                or user.email.startswith(query_lower)
            ):
                results.append(user)

            if len(results) >= limit:
                break

        return results

    def change_password(
        self, user_id: str, old_password: str, new_password: str
    ) -> bool:
        """Change a user's password after verifying the old password."""
        user = self.get_user(user_id)
        if user is None:
            return False

        # Verify old password
        if _hash_password(old_password, user.salt) != user.password_hash:
            return False

        # Validate new password
        if len(new_password) < MIN_PASSWORD_LENGTH:
            raise ValueError(
                f"Password must be at least {MIN_PASSWORD_LENGTH} characters"
            )

        # Reuse existing salt for the new password
        user.password_hash = _hash_password(new_password, user.salt)
        user.updated_at = time.time()
        return True

    def count_active_users(self) -> int:
        """Count non-deleted users."""
        return sum(1 for u in self._users.values() if not u.is_deleted)
