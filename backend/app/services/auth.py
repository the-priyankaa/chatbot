from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..core.security import hash_refresh_token, hash_password, verify_password, decode_token, utcnow
from ..database import get_db
from ..models import RefreshToken, User
from ..config import settings

bearer_scheme = HTTPBearer(auto_error=False)

DbDep = Annotated[AsyncSession, Depends(get_db)]


async def authenticate_user(
    db: AsyncSession, identifier: str, password: str
) -> User | None:
    stmt = select(User).where(
        (User.username == identifier) | (User.email == identifier)
    )
    user = (await db.execute(stmt)).scalar_one_or_none()
    if user and verify_password(password, user.password_hash):
        return user
    return None


def create_user(db: AsyncSession, username: str, email: str, password: str) -> User:
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
    )
    db.add(user)
    return user


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: DbDep,
) -> User:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    try:
        payload = decode_token(credentials.credentials)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        ) from exc

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not an access token"
        )

    user = await db.get(User, payload.get("sub"))
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def store_refresh_token(
    db: AsyncSession, user: User, token_hash: str, expires_at, rotate: bool = False
) -> None:
    if rotate:
        # Revoke any existing live refresh tokens for this user (single active session)
        stmt = select(RefreshToken).where(
            RefreshToken.user_id == user.id,
            RefreshToken.revoked_at.is_(None),
        )
        for tok in (await db.execute(stmt)).scalars().all():
            tok.revoked_at = utcnow()
    db.add(
        RefreshToken(
            user_id=user.id, token_hash=token_hash, expires_at=expires_at
        )
    )


async def consume_refresh_token(db: AsyncSession, refresh_token: str) -> User:
    hashed = hash_refresh_token(refresh_token)
    stmt = select(RefreshToken).where(RefreshToken.token_hash == hashed)
    record = (await db.execute(stmt)).scalar_one_or_none()

    if record is None or record.revoked_at is not None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    if record.expires_at < utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired"
        )

    # Rotation: mark as used
    record.revoked_at = utcnow()
    user = await db.get(User, record.user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found"
        )
    return user
