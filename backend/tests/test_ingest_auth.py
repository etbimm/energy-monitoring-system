import pytest
from fastapi import HTTPException

from app import main


def test_ingest_disabled_without_configured_key(monkeypatch):
    monkeypatch.setattr(main.settings, "ingest_api_key", None)
    with pytest.raises(HTTPException) as exc:
        main.require_ingest_key("anything")
    assert exc.value.status_code == 404


def test_ingest_rejects_wrong_key(monkeypatch):
    monkeypatch.setattr(main.settings, "ingest_api_key", "rahasia")
    for key in (None, "", "salah"):
        with pytest.raises(HTTPException) as exc:
            main.require_ingest_key(key)
        assert exc.value.status_code == 401


def test_ingest_accepts_correct_key(monkeypatch):
    monkeypatch.setattr(main.settings, "ingest_api_key", "rahasia")
    assert main.require_ingest_key("rahasia") is None
