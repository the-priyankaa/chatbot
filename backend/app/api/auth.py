from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from ..config import settings
from ..core.ratelimit import limiter
from ..core.security import (
    create_access_token,
    create_refresh_token,
    hash_refresh_token,
    utcnow,
)
from ..models import RefreshToken, User
from ..schemas.auth import RefreshRequest, TokenPair, UserCreate, UserLogin, UserOut
from ..services.auth import (
    CurrentUser,
    DbDep,
    authenticate_user,
    consume_refresh_token,
    create_user,
    store_refresh_token,
)

router = APIRouter(prefix="/auth", tags=["auth"])

_RATE = f"{settings.rate_limit_per_minute}/minute"


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
@limiter.limit(_RATE)
async def register(request: Request, payload: UserCreate, db: DbDep) -> TokenPair:
    existing = (
        await db.execute(
            select(User).where(
                (User.username == payload.username) | (User.email == payload.email)
            )
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username or email taken"
        )

    user = create_user(db, payload.username, payload.email, payload.password)
    try:
        await db.flush()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username or email taken"
        ) from None

    access, _ = create_access_token(user.id)
    refresh, _ = create_refresh_token(user.id)
    await store_refresh_token(
        db,
        user,
        hash_refresh_token(refresh),
        utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username or email taken"
        ) from None
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/login", response_model=TokenPair)
@limiter.limit(_RATE)
async def login(request: Request, payload: UserLogin, db: DbDep) -> TokenPair:
    user = await authenticate_user(db, payload.identifier, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username/email or password",
        )

    access, _ = create_access_token(user.id)
    refresh, _ = create_refresh_token(user.id)
    await store_refresh_token(
        db,
        user,
        hash_refresh_token(refresh),
        utcnow() + timedelta(days=settings.refresh_token_expire_days),
        rotate=True,
    )
    await db.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenPair)
@limiter.limit(_RATE)
async def refresh(request: Request, payload: RefreshRequest, db: DbDep) -> TokenPair:
    user = await consume_refresh_token(db, payload.refresh_token)
    access, _ = create_access_token(user.id)
    refresh, _ = create_refresh_token(user.id)
    await store_refresh_token(
        db,
        user,
        hash_refresh_token(refresh),
        utcnow() + timedelta(days=settings.refresh_token_expire_days),
    )
    await db.commit()
    return TokenPair(access_token=access, refresh_token=refresh)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(payload: RefreshRequest, db: DbDep) -> None:
    hashed = hash_refresh_token(payload.refresh_token)
    record = (
        await db.execute(select(RefreshToken).where(RefreshToken.token_hash == hashed))
    ).scalar_one_or_none()
    if record:
        record.revoked_at = utcnow()
        await db.commit()


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser) -> User:
    return user
