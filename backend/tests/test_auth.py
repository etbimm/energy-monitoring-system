"""Login, sesi JWT, dan pembatasan akses (tanpa database sungguhan)."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import jwt
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app import main
from app.api import deps
from app.services import auth


@pytest.fixture
def client():
    # Tanpa `with`: lifespan (MQTT, offline watcher) tidak dijalankan.
    return TestClient(main.app)


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


def test_login_throttle_blocks_after_limit_and_expires():
    throttle = auth.LoginThrottle(limit=3, window=60)
    for t in range(3):
        assert throttle.retry_after("1.1.1.1", "budi", now=t) == 0
        throttle.fail("1.1.1.1", "budi", now=t)
    assert throttle.retry_after("1.1.1.1", "budi", now=10) > 0
    # IP atau username lain tidak ikut terblokir.
    assert throttle.retry_after("2.2.2.2", "budi", now=10) == 0
    assert throttle.retry_after("1.1.1.1", "ani", now=10) == 0
    # Setelah jendela waktu lewat, boleh mencoba lagi.
    assert throttle.retry_after("1.1.1.1", "budi", now=200) == 0
    throttle.fail("1.1.1.1", "budi", now=200)
    throttle.reset("1.1.1.1", "budi")
    assert throttle.retry_after("1.1.1.1", "budi", now=201) == 0


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


def test_websocket_origin_check(monkeypatch):
    monkeypatch.setattr(main.settings, "cors_origins", "http://localhost:3000")
    assert main.websocket_origin_allowed("http://localhost:3000")
    assert main.websocket_origin_allowed(None)
    assert not main.websocket_origin_allowed("http://evil.example")
