from __future__ import annotations

from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditLog, User


def record(
    session: AsyncSession,
    actor: User | None,
    action: str,
    target: str | None = None,
    detail: dict[str, Any] | None = None,
    username: str | None = None,
) -> None:
    """Tambahkan baris audit ke sesi; ikut tersimpan saat caller commit."""
    session.add(
        AuditLog(
            user_id=actor.id if actor else None,
            username=actor.username if actor else username,
            action=action,
            target=target,
            detail=detail or {},
        )
    )
