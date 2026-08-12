import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

from ..config import settings

JWT_ALGORITHM = settings.jwt_algorithm


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
    except ValueError:
        return False


def generate_token_jti() -> str:
    return secrets.token_urlsafe(24)


def create_access_token(subject: str, token_type: str = "access") -> tuple[str, str]:
    jti = generate_token_jti()
    expires = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {"sub": subject, "type": token_type, "jti": jti, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM), jti


def create_refresh_token(subject: str) -> tuple[str, str]:
    jti = generate_token_jti()
    expires = datetime.now(timezone.utc) + timedelta(
        days=settings.refresh_token_expire_days
    )
    payload = {"sub": subject, "type": "refresh", "jti": jti, "exp": expires}
    return jwt.encode(payload, settings.jwt_secret, algorithm=JWT_ALGORITHM), jti


def decode_token(token: str) -> dict[str, Any]:
    return jwt.decode(token, settings.jwt_secret, algorithms=[JWT_ALGORITHM])


def hash_refresh_token(raw: str) -> str:
    from hashlib import sha256

    return sha256(raw.encode()).hexdigest()


def utcnow() -> datetime:
    # Naive UTC: SQLite stores DateTime without tz info; keeping naive avoids
    # aware-vs-naive comparison errors.
    return datetime.now(timezone.utc).replace(tzinfo=None)
