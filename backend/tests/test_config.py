"""Aturan konfigurasi environment (hard-fail JWT di production)."""
import pytest
from pydantic import ValidationError

from app.config import Settings


def test_production_requires_jwt_secret():
    with pytest.raises(ValidationError, match="JWT_SECRET wajib diisi"):
        Settings(environment="production", jwt_secret=None, _env_file=None)


def test_development_allows_generated_secret():
    settings = Settings(environment="development", jwt_secret=None, _env_file=None)
    assert settings.jwt_secret is None
    assert not settings.is_production


def test_production_accepts_valid_jwt_secret():
    settings = Settings(environment="production", jwt_secret="x" * 32, _env_file=None)
    assert settings.is_production
    assert settings.jwt_secret == "x" * 32


def test_short_jwt_secret_is_rejected():
    with pytest.raises(ValidationError, match="minimal 32 karakter"):
        Settings(environment="production", jwt_secret="pendek", _env_file=None)


def test_unknown_environment_is_rejected():
    with pytest.raises(ValidationError, match="ENVIRONMENT harus"):
        Settings(environment="prodution", _env_file=None)
