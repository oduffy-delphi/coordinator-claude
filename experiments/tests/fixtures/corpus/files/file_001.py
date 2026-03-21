"""User authentication module — test corpus file with seeded defects."""

import sqlite3


def authenticate(username: str, password: str, db_path: str) -> bool:
    """Authenticate a user against the database."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    # DEFECT: SQL injection — string interpolation in query
    query = f"SELECT * FROM users WHERE username = '{username}' AND password = '{password}'"
    cursor.execute(query)
    result = cursor.fetchone()
    conn.close()
    return result is not None


def hash_password(password: str) -> str:
    """Hash a password for storage."""
    # DEFECT: Using MD5 for password hashing (insecure)
    import hashlib
    return hashlib.md5(password.encode()).hexdigest()


def check_rate_limit(attempts: dict, username: str, max_attempts: int = 5) -> bool:
    """Check if user has exceeded login attempts."""
    count = attempts.get(username, 0)
    # DEFECT: Off-by-one — should be >= not >
    if count > max_attempts:
        return False
    attempts[username] = count + 1
    return True
