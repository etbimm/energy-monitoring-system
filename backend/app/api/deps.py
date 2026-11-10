"""Dependency autentikasi dan otorisasi untuk router API.

- `get_current_user`: wajib login (cookie sesi valid, akun aktif).
- `require_admin`: wajib login sebagai admin.

Pengecekan di frontend (menyembunyikan tombol/menu) hanya kenyamanan;
pengamanan sebenarnya ada di sini.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db import get_session
from app.models import User
from app.services.auth import decode_token

NOT_AUTHENTICATED = "Sesi tidak valid atau sudah berakhir. Silakan login kembali."


async def user_from_token(session: AsyncSession, token: str | None) -> User | None:
    """User aktif pemilik token, atau None bila token/akun tidak valid."""
    claims = decode_token(token)
    if claims is None:
        return None
    user = (await session.execute(select(User).where(User.id == claims.user_id))).scalar_one_or_none()
    if user is None or not user.is_active or user.token_version != claims.version:
        return None
    return user


async def get_current_user(request: Request, session: AsyncSession = Depends(get_session)) -> User:
    token = request.cookies.get(get_settings().session_cookie_name)
    if not token:
        raise HTTPException(status_code=401, detail=NOT_AUTHENTICATED)
    user = await user_from_token(session, token)
    if user is None:
        raise HTTPException(status_code=401, detail=NOT_AUTHENTICATED)
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Fitur ini hanya untuk admin.")
    return user
