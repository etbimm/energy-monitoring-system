"""Login: hash password (Argon2) dan sesi JWT di cookie httpOnly.

Isi token hanya `sub` (id user), `ver` (token_version), `iat`, dan `exp`.
Role dan status aktif selalu dibaca ulang dari database setiap request,
sehingga perubahan role/penonaktifan akun langsung berlaku.
"""
from __future__ import annotations

import logging
import secrets
import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.config import get_settings

log = logging.getLogger("ems.auth")

ROLES = ("admin", "viewer")
JWT_ALGORITHM = "HS256"
MIN_PASSWORD_LENGTH = 8

_hasher = PasswordHasher()
# Hash pembanding saat username tidak ada, agar waktu respons login sama
# (penyerang tidak bisa menebak username yang terdaftar dari lamanya respons).
_DUMMY_HASH = _hasher.hash(secrets.token_urlsafe(16))
_generated_secret: str | None = None


def jwt_secret() -> str:
    global _generated_secret
    configured = get_settings().jwt_secret
    if configured:
        return configured
    if _generated_secret is None:
        _generated_secret = secrets.token_urlsafe(48)
        log.warning(
            "JWT_SECRET belum diisi: memakai secret acak sementara. "
            "Semua sesi login hilang setiap backend restart."
        )
    return _generated_secret


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    try:
        return _hasher.verify(password_hash or _DUMMY_HASH, password) and password_hash is not None
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def password_problem(password: str) -> str | None:
    """Alasan password ditolak, atau None bila memenuhi syarat."""
    if len(password) < MIN_PASSWORD_LENGTH:
        return f"Password minimal {MIN_PASSWORD_LENGTH} karakter."
    if len(password) > 128:
        return "Password maksimal 128 karakter."
    if password.isdigit() or password.isalpha():
        return "Password harus berisi kombinasi huruf dan angka/simbol."
    return None


@dataclass(frozen=True)
class TokenClaims:
    user_id: int
    version: int


def create_token(user_id: int, version: int, now: datetime | None = None) -> tuple[str, int]:
    """Buat JWT sesi. Mengembalikan (token, umur detik)."""
    now = now or datetime.now(timezone.utc)
    max_age = get_settings().jwt_expire_minutes * 60
    payload = {
        "sub": str(user_id),
        "ver": version,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=max_age)).timestamp()),
    }
    return jwt.encode(payload, jwt_secret(), algorithm=JWT_ALGORITHM), max_age


def decode_token(token: str | None) -> TokenClaims | None:
    """Klaim token yang valid, atau None bila kosong/rusak/kedaluwarsa."""
    if not token:
        return None
    try:
        payload = jwt.decode(
            token,
            jwt_secret(),
            algorithms=[JWT_ALGORITHM],
            options={"require": ["sub", "exp", "iat"]},
        )
        return TokenClaims(user_id=int(payload["sub"]), version=int(payload.get("ver", 0)))
    except (jwt.PyJWTError, ValueError, TypeError):
        return None


class LoginThrottle:
    """Batasi percobaan login gagal per (IP, username) di memori proses.

    Setelah `limit` kegagalan dalam `window` detik, login ditolak sampai
    kegagalan tertua keluar dari jendela waktu.
    """

    def __init__(self, limit: int = 5, window: float = 15 * 60) -> None:
        self.limit = limit
        self.window = window
        self._failures: dict[tuple[str, str], deque[float]] = {}

    def _prune(self, key: tuple[str, str], now: float) -> deque[float]:
        bucket = self._failures.setdefault(key, deque())
        while bucket and now - bucket[0] > self.window:
            bucket.popleft()
        return bucket

    def retry_after(self, ip: str, username: str, now: float | None = None) -> int:
        """Detik sampai boleh mencoba lagi (0 = boleh sekarang)."""
        now = time.monotonic() if now is None else now
        bucket = self._prune((ip, username), now)
        if len(bucket) < self.limit:
            return 0
        return max(1, int(self.window - (now - bucket[0])) + 1)

    def fail(self, ip: str, username: str, now: float | None = None) -> None:
        now = time.monotonic() if now is None else now
        self._prune((ip, username), now).append(now)
        if len(self._failures) > 10_000:
            # Cegah memori tumbuh tanpa batas saat diserang banyak username.
            for key in [k for k, v in self._failures.items() if not v]:
                del self._failures[key]

    def reset(self, ip: str, username: str) -> None:
        self._failures.pop((ip, username), None)


login_throttle = LoginThrottle()
