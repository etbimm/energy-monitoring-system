"""Login, sesi JWT, dan pembatasan akses (tanpa database sungguhan)."""
import math
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException, Response
from fastapi.testclient import TestClient
from redis.exceptions import ConnectionError as RedisConnectionError
from starlette.requests import Request

from app import main
from app.api import auth as auth_api
from app.api import deps
from app.schemas import LoginIn
from app.services import auth


@pytest.fixture
def client():
    # Tanpa `with`: lifespan (MQTT, offline watcher) tidak dijalankan.
    return TestClient(main.app)


class _FakeRedis:
    def __init__(self):
        self.zsets: dict[str, dict[str, int]] = {}
        self.expires: dict[str, int] = {}

    def _expire_and_prune(self, now_ms: int, window_ms: int, key: str) -> dict[str, int]:
        for expired_key, expiry in list(self.expires.items()):
            if now_ms >= expiry:
                self.zsets.pop(expired_key, None)
                self.expires.pop(expired_key, None)

        entries = self.zsets.get(key, {})
        cutoff = now_ms - window_ms
        entries = {member: score for member, score in entries.items() if score > cutoff}
        if entries:
            self.zsets[key] = entries
        else:
            self.zsets.pop(key, None)
        return entries

    async def eval(self, script, numkeys, *args):
        keys = list(args[:numkeys])
        now_arg = args[numkeys]
        now_ms = int(now_arg) if now_arg else 0
        window_ms = int(args[numkeys + 1])

        if script == auth._CHECK_FAILURES_SCRIPT:
            limits = [int(value) for value in args[numkeys + 2 : numkeys + 2 + numkeys]]
            wait_ms = 0
            for key, limit in zip(keys, limits):
                entries = self._expire_and_prune(now_ms, window_ms, key)
                if len(entries) >= limit:
                    oldest = min(entries.values())
                    wait_ms = max(wait_ms, oldest + window_ms - now_ms)
            return math.ceil(wait_ms / 1000)

        if script == auth._RECORD_FAILURE_SCRIPT:
            member = args[numkeys + 2]
            limits = [int(value) for value in args[numkeys + 3 : numkeys + 3 + numkeys]]
            wait_ms = 0
            for key, limit in zip(keys, limits):
                entries = self._expire_and_prune(now_ms, window_ms, key)
                if len(entries) >= limit:
                    oldest = min(entries.values())
                    wait_ms = max(wait_ms, oldest + window_ms - now_ms)
            if wait_ms > 0:
                return math.ceil(wait_ms / 1000)
            for key in keys:
                self.zsets.setdefault(key, {})[member] = now_ms
                self.expires[key] = now_ms + window_ms
            return 0

        raise AssertionError("Unexpected Redis script")

    async def delete(self, key):
        self.zsets.pop(key, None)
        self.expires.pop(key, None)

    async def ping(self):
        return True

    async def aclose(self):
        return None


def test_password_hash_roundtrip():
    hashed = auth.hash_password("rahasia123")
    assert hashed != "rahasia123"
    assert auth.verify_password("rahasia123", hashed)
    assert not auth.verify_password("salah12345", hashed)
    assert not auth.verify_password("rahasia123", None)
    assert not auth.verify_password("rahasia123", "bukan-hash")


@pytest.mark.parametrize(
    ("password", "ok"),
    [("pendek1", False), ("12345678", False), ("abcdefgh", False), ("abcd1234", True), ("x" * 129, False)],
)
def test_password_policy(password, ok):
    assert (auth.password_problem(password) is None) is ok


def test_token_roundtrip_and_version():
    token, max_age = auth.create_token(7, 3)
    assert max_age == main.settings.jwt_expire_minutes * 60
    claims = auth.decode_token(token)
    assert claims == auth.TokenClaims(user_id=7, version=3)


def test_token_rejects_expired_tampered_and_garbage():
    past = datetime.now(timezone.utc) - timedelta(days=2)
    expired, _ = auth.create_token(1, 0, now=past)
    assert auth.decode_token(expired) is None

    forged = jwt.encode({"sub": "1", "ver": 0, "iat": 0, "exp": 9_999_999_999}, "x" * 40, algorithm="HS256")
    assert auth.decode_token(forged) is None

    unsigned = jwt.encode({"sub": "1", "iat": 0, "exp": 9_999_999_999}, None, algorithm="none")
    assert auth.decode_token(unsigned) is None

    for value in (None, "", "abc.def.ghi"):
        assert auth.decode_token(value) is None


async def test_login_throttle_blocks_after_limit_and_expires():
    throttle = auth.LoginThrottle(_FakeRedis(), limit=3, window=60)
    for t in range(3):
        assert await throttle.retry_after("1.1.1.1", "budi", now=t) == 0
        assert await throttle.fail("1.1.1.1", "budi", now=t) == 0
    assert await throttle.retry_after("1.1.1.1", "budi", now=10) > 0
    # IP atau username lain tidak ikut terblokir.
    assert await throttle.retry_after("2.2.2.2", "budi", now=10) == 0
    assert await throttle.retry_after("1.1.1.1", "ani", now=10) == 0
    # Setelah jendela waktu lewat, boleh mencoba lagi.
    assert await throttle.retry_after("1.1.1.1", "budi", now=200) == 0
    await throttle.fail("1.1.1.1", "budi", now=200)
    await throttle.reset("1.1.1.1", "budi")
    assert await throttle.retry_after("1.1.1.1", "budi", now=201) == 0


async def test_login_throttle_enforces_ip_and_account_limits():
    throttle = auth.LoginThrottle(
        _FakeRedis(),
        limit=10,
        ip_limit=2,
        account_limit=2,
        global_limit=100,
        window=60,
    )
    await throttle.fail("10.0.0.1", "budi", now=0)
    await throttle.fail("10.0.0.2", "budi", now=1)
    assert await throttle.retry_after("10.0.0.3", "budi", now=2) > 0

    await throttle.fail("10.0.0.1", "siti", now=2)
    assert await throttle.retry_after("10.0.0.1", "andi", now=3) > 0
    assert await throttle.retry_after("10.0.0.3", "andi", now=3) == 0


async def test_login_throttle_global_limit_bounds_unique_key_churn():
    redis = _FakeRedis()
    throttle = auth.LoginThrottle(
        redis,
        limit=100,
        ip_limit=100,
        account_limit=100,
        global_limit=5,
        window=60,
    )
    for index in range(100):
        wait = await throttle.fail(f"10.0.0.{index}", f"user-{index}", now=1)
        assert (wait == 0) is (index < 5)

    global_key = f"{throttle.key_prefix}:global"
    assert len(redis.zsets[global_key]) == 5
    assert len(redis.zsets) <= 16
    assert all("user-" not in key and "10.0.0." not in key for key in redis.zsets)
    assert await throttle.retry_after("new-ip", "new-user", now=2) > 0
    assert await throttle.retry_after("new-ip", "new-user", now=61) == 0
    assert global_key not in redis.zsets


async def test_login_throttle_success_reset_clears_only_pair_bucket():
    throttle = auth.LoginThrottle(
        _FakeRedis(),
        limit=2,
        ip_limit=10,
        account_limit=10,
        global_limit=100,
        window=60,
    )
    await throttle.fail("10.0.0.1", "budi", now=0)
    await throttle.fail("10.0.0.1", "budi", now=1)
    assert await throttle.retry_after("10.0.0.1", "budi", now=2) > 0

    await throttle.reset("10.0.0.1", "budi")
    assert await throttle.retry_after("10.0.0.1", "budi", now=2) == 0


async def test_login_fails_closed_when_redis_is_unavailable(monkeypatch):
    async def redis_unavailable(*_args, **_kwargs):
        raise RedisConnectionError("redis down")

    monkeypatch.setattr(auth_api.login_throttle, "retry_after", redis_unavailable)
    request = Request({
        "type": "http",
        "headers": [],
        "client": ("127.0.0.1", 12345),
    })
    with pytest.raises(HTTPException) as exc:
        await auth_api.login(LoginIn(username="budi", password="rahasia123"), request, Response(), None)
    assert exc.value.status_code == 503


async def test_require_admin_rejects_viewer():
    viewer = SimpleNamespace(role="viewer")
    with pytest.raises(HTTPException) as exc:
        await deps.require_admin(viewer)
    assert exc.value.status_code == 403
    admin = SimpleNamespace(role="admin")
    assert await deps.require_admin(admin) is admin


async def test_user_from_token_checks_active_and_version(monkeypatch):
    user = SimpleNamespace(id=5, is_active=True, token_version=2)

    class FakeResult:
        def scalar_one_or_none(self):
            return user

    class FakeSession:
        async def execute(self, _stmt):
            return FakeResult()

    token, _ = auth.create_token(5, 2)
    assert await deps.user_from_token(FakeSession(), token) is user

    stale, _ = auth.create_token(5, 1)  # password direset -> versi naik
    assert await deps.user_from_token(FakeSession(), stale) is None

    user.is_active = False
    assert await deps.user_from_token(FakeSession(), token) is None


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/devices"),
        ("get", "/api/summary/today"),
        ("get", "/api/alarms"),
        ("get", "/api/readings?from=2026-01-01T00:00:00Z&to=2026-01-01T01:00:00Z"),
        ("post", "/api/alarms/1/acknowledge"),
        ("get", "/api/auth/me"),
        ("get", "/api/admin/users"),
        ("delete", "/api/admin/users/1"),
        ("get", "/api/admin/devices"),
        ("post", "/api/admin/devices"),
        ("patch", "/api/admin/devices/PM-MCC1-01"),
        ("get", "/api/admin/audit-log"),
    ],
)
def test_protected_endpoints_require_login(client, method, path):
    response = getattr(client, method)(path)
    assert response.status_code == 401


def test_invalid_cookie_is_rejected_before_database(client):
    client.cookies.set(main.settings.session_cookie_name, "token-palsu")
    assert client.get("/api/devices").status_code == 401


def test_logout_clears_cookie(client):
    response = client.post("/api/auth/logout")
    assert response.status_code == 200
    cookie = response.headers["set-cookie"]
    assert main.settings.session_cookie_name in cookie
    assert "Max-Age=0" in cookie or "expires=" in cookie.lower()


@pytest.mark.parametrize("role", ["admin", "viewer"])
async def test_logout_records_authenticated_user(monkeypatch, role):
    user = SimpleNamespace(id=5, username="budi", role=role)

    class FakeSession:
        def __init__(self):
            self.added = []
            self.committed = False

        def add(self, item):
            self.added.append(item)

        async def commit(self):
            self.committed = True

    async def current_user(_session, _token):
        return user

    monkeypatch.setattr(auth_api, "user_from_token", current_user)
    cookie = f"{main.settings.session_cookie_name}=valid"
    request = Request({
        "type": "http",
        "headers": [(b"cookie", cookie.encode())],
        "client": ("127.0.0.1", 12345),
    })
    session = FakeSession()

    result = await auth_api.logout(request, Response(), session)

    assert result == {"ok": True}
    assert session.committed
    assert len(session.added) == 1
    assert session.added[0].action == "auth.logout"
    assert session.added[0].username == "budi"
    assert session.added[0].detail == {"ip": "127.0.0.1"}


def test_websocket_origin_check(monkeypatch):
    monkeypatch.setattr(main.settings, "cors_origins", "http://localhost:3000")
    assert main.websocket_origin_allowed("http://localhost:3000")
    assert main.websocket_origin_allowed(None)
    assert not main.websocket_origin_allowed("http://evil.example")
