"""Login: hash password (Argon2) dan sesi JWT di cookie httpOnly.

Isi token hanya `sub` (id user), `ver` (token_version), `iat`, dan `exp`.
Role dan status aktif selalu dibaca ulang dari database setiap request,
sehingga perubahan role/penonaktifan akun langsung berlaku.
"""
from __future__ import annotations

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from redis.asyncio import Redis

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
    settings = get_settings()
    if settings.jwt_secret:
        return settings.jwt_secret
    if settings.is_production:
        # Settings sudah menolak start di production tanpa JWT_SECRET; ini
        # pengaman tambahan bila objek Settings dibuat dengan cara lain.
        raise RuntimeError("JWT_SECRET wajib diisi saat ENVIRONMENT=production")
    if _generated_secret is None:
        _generated_secret = secrets.token_urlsafe(48)
        log.warning(
            "JWT_SECRET belum diisi: memakai secret acak sementara (mode development). "
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


_CHECK_FAILURES_SCRIPT = """
local now_ms
if ARGV[1] == "" then
    local redis_time = redis.call("TIME")
    now_ms = tonumber(redis_time[1]) * 1000 + math.floor(tonumber(redis_time[2]) / 1000)
else
    now_ms = tonumber(ARGV[1])
end
local window_ms = tonumber(ARGV[2])
local wait_ms = 0
for i, key in ipairs(KEYS) do
    redis.call("ZREMRANGEBYSCORE", key, "-inf", now_ms - window_ms)
    local count = redis.call("ZCARD", key)
    local limit = tonumber(ARGV[i + 2])
    if count >= limit then
        local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
        local remaining = tonumber(oldest[2]) + window_ms - now_ms
        if remaining > wait_ms then
            wait_ms = remaining
        end
    end
end
return math.ceil(wait_ms / 1000)
"""

_RECORD_FAILURE_SCRIPT = """
local now_ms
if ARGV[1] == "" then
    local redis_time = redis.call("TIME")
    now_ms = tonumber(redis_time[1]) * 1000 + math.floor(tonumber(redis_time[2]) / 1000)
else
    now_ms = tonumber(ARGV[1])
end
local window_ms = tonumber(ARGV[2])
local member = ARGV[3]
local wait_ms = 0
for i, key in ipairs(KEYS) do
    redis.call("ZREMRANGEBYSCORE", key, "-inf", now_ms - window_ms)
    local count = redis.call("ZCARD", key)
    local limit = tonumber(ARGV[i + 3])
    if count >= limit then
        local oldest = redis.call("ZRANGE", key, 0, 0, "WITHSCORES")
        local remaining = tonumber(oldest[2]) + window_ms - now_ms
        if remaining > wait_ms then
            wait_ms = remaining
        end
    end
end
if wait_ms > 0 then
    return math.ceil(wait_ms / 1000)
end
for _, key in ipairs(KEYS) do
    redis.call("ZADD", key, now_ms, member)
    redis.call("PEXPIRE", key, window_ms)
end
return 0
"""


class LoginThrottle:
    """Track failed login attempts in a shared Redis sliding window."""

    def __init__(
        self,
        redis_client: Redis | None = None,
        *,
        limit: int = 5,
        ip_limit: int = 20,
        account_limit: int = 10,
        global_limit: int = 10_000,
        window: float = 15 * 60,
        key_prefix: str = "ems:login:fail",
    ) -> None:
        if min(limit, ip_limit, account_limit, global_limit) < 1 or window <= 0:
            raise ValueError("Batas dan jendela login throttle harus positif")
        self.limit = limit
        self.ip_limit = ip_limit
        self.account_limit = account_limit
        self.global_limit = global_limit
        self.window_ms = int(window * 1000)
        self.key_prefix = key_prefix
        self._redis = (
            redis_client
            if redis_client is not None
            else Redis.from_url(get_settings().redis_url, decode_responses=True)
        )

    @staticmethod
    def _digest(value: str) -> str:
        return hashlib.sha256(value.encode("utf-8")).hexdigest()

    def _keys(self, ip: str, username: str) -> list[str]:
        normalized_username = username.strip().lower()
        return [
            f"{self.key_prefix}:pair:{self._digest(ip + chr(0) + normalized_username)}",
            f"{self.key_prefix}:ip:{self._digest(ip)}",
            f"{self.key_prefix}:account:{self._digest(normalized_username)}",
            f"{self.key_prefix}:global",
        ]

    @staticmethod
    def _now_argument(now: float | None) -> str:
        return "" if now is None else str(int(now * 1000))

    async def retry_after(self, ip: str, username: str, now: float | None = None) -> int:
        """Return the wait in seconds if any limit is reached."""
        keys = self._keys(ip, username)
        result = await self._redis.eval(
            _CHECK_FAILURES_SCRIPT,
            len(keys),
            *keys,
            self._now_argument(now),
            self.window_ms,
            self.limit,
            self.ip_limit,
            self.account_limit,
            self.global_limit,
        )
        return int(result)

    async def fail(self, ip: str, username: str, now: float | None = None) -> int:
        """Atomically record a failure, returning wait seconds if a limit filled concurrently."""
        keys = self._keys(ip, username)
        result = await self._redis.eval(
            _RECORD_FAILURE_SCRIPT,
            len(keys),
            *keys,
            self._now_argument(now),
            self.window_ms,
            secrets.token_urlsafe(18),
            self.limit,
            self.ip_limit,
            self.account_limit,
            self.global_limit,
        )
        return int(result)

    async def reset(self, ip: str, username: str) -> None:
        """Clear the pair bucket after successful authentication."""
        await self._redis.delete(self._keys(ip, username)[0])

    async def ping(self) -> bool:
        return bool(await self._redis.ping())

    async def aclose(self) -> None:
        await self._redis.aclose()


login_throttle = LoginThrottle()
