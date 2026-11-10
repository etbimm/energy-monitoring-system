from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.config import get_settings
from app.db import get_session
from app.models import User
from app.schemas import LoginIn, PasswordChange, UserOut
from app.services import audit
from app.services.auth import (
    create_token,
    hash_password,
    login_throttle,
    password_problem,
    verify_password,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])

INVALID_LOGIN = "Username atau password salah."


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def set_session_cookie(response: Response, user: User) -> None:
    settings = get_settings()
    token, max_age = create_token(user.id, user.token_version)
    response.set_cookie(
        settings.session_cookie_name,
        token,
        max_age=max_age,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session_cookie(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        settings.session_cookie_name,
        path="/",
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
    )


@router.post("/login", response_model=UserOut)
async def login(
    payload: LoginIn,
    request: Request,
    response: Response,
    session: AsyncSession = Depends(get_session),
) -> User:
    ip = client_ip(request)
    wait = login_throttle.retry_after(ip, payload.username)
    if wait:
        raise HTTPException(
            status_code=429,
            detail=f"Terlalu banyak percobaan login. Coba lagi dalam {max(1, wait // 60)} menit.",
            headers={"Retry-After": str(wait)},
        )

    user = (
        await session.execute(select(User).where(User.username == payload.username))
    ).scalar_one_or_none()
    # verify_password tetap dijalankan walau user tidak ada (waktu respons sama).
    valid = verify_password(payload.password, user.password_hash if user else None)
    if user is None or not valid or not user.is_active:
        login_throttle.fail(ip, payload.username)
        audit.record(session, None, "auth.login_failed", payload.username, {"ip": ip}, username=payload.username)
        await session.commit()
        raise HTTPException(status_code=401, detail=INVALID_LOGIN)

    login_throttle.reset(ip, payload.username)
    user.last_login_at = datetime.now(timezone.utc)
    audit.record(session, user, "auth.login", user.username, {"ip": ip})
    await session.commit()
    set_session_cookie(response, user)
    return user


@router.post("/logout")
async def logout(response: Response) -> dict[str, bool]:
    # Tidak wajib login: cookie kedaluwarsa pun tetap bisa dihapus.
    clear_session_cookie(response)
    return {"ok": True}


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)) -> User:
    return user


@router.post("/change-password")
async def change_password(
    payload: PasswordChange,
    response: Response,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    if not verify_password(payload.current_password, user.password_hash):
        raise HTTPException(status_code=400, detail="Password lama salah.")
    problem = password_problem(payload.new_password)
    if problem:
        raise HTTPException(status_code=422, detail=problem)
    if payload.new_password == payload.current_password:
        raise HTTPException(status_code=422, detail="Password baru harus berbeda dari password lama.")

    user.password_hash = hash_password(payload.new_password)
    # Sesi di perangkat lain berakhir; sesi ini diperbarui dengan token baru.
    user.token_version += 1
    audit.record(session, user, "auth.change_password", user.username)
    await session.commit()
    set_session_cookie(response, user)
    return {"ok": True}
