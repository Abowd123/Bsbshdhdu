import hmac
import uuid
from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import decode_token
from app.core.config import settings
from app.db.session import get_db
from app.models.user import User, UserRole

# auto_error=False حتى نستطيع السقوط إلى مسار X-API-Key عند غياب Bearer token
bearer_scheme = HTTPBearer(auto_error=False)


async def _get_api_key_user(db: AsyncSession) -> User:
    """يُستخدم من تكاملات خارجية (بوت التحكم في تيليجرام مثلاً) عبر مفتاح ثابت من .env
    بدلاً من تسجيل دخول JWT. يُعيد صاحب الحساب المحدد في ADMIN_EMAIL فقط."""
    if not settings.ADMIN_EMAIL:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_api_key")
    result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active or user.is_suspended:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_inactive")
    return user


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    api_key = request.headers.get("x-api-key")
    if api_key is not None:
        if not settings.BOT_CONTROL_API_KEY or not hmac.compare_digest(api_key, settings.BOT_CONTROL_API_KEY):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_api_key")
        return await _get_api_key_user(db)

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="not_authenticated")

    try:
        payload = decode_token(credentials.credentials)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")

    if payload.get("type") != "access":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token_type")

    user_id = payload.get("sub")
    try:
        user_uuid = uuid.UUID(user_id)
    except (ValueError, TypeError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_token")

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if user is None or not user.is_active or user.is_suspended:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="user_inactive")

    return user


async def get_current_admin(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.ADMIN, UserRole.SUPER_ADMIN):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="admin_required")
    return user


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
