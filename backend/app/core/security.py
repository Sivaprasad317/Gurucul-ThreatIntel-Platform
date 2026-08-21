from datetime import UTC, datetime, timedelta
import hashlib
import hmac
import secrets
from typing import Any

import jwt

from backend.app.core.config import get_settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    """Hash a password using PBKDF2-HMAC-SHA256."""
    if len(password) < 8:
        raise ValueError("Password must contain at least 8 characters.")
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, 210_000)
    return f"pbkdf2_sha256$210000${salt.hex()}${digest.hex()}"


def verify_password(password: str, encoded: str) -> bool:
    """Verify a PBKDF2 password hash."""
    try:
        algorithm, rounds, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt_hex), int(rounds))
        return hmac.compare_digest(digest.hex(), digest_hex)
    except (ValueError, TypeError):
        return False


def create_access_token(user_id: str, email: str) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": user_id, "email": email, "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decode and validate a JWT."""
    return jwt.decode(token, get_settings().jwt_secret, algorithms=[ALGORITHM])
