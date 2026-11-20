"""Ambang alarm yang dikonfigurasi admin dan disimpan di database.

`apply_alarms` memakai cache di memori agar evaluasi alarm tidak query database
setiap kali telemetry masuk. Cache dimuat saat startup dan diperbarui saat
admin menyimpan perubahan lewat endpoint.
"""
from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AlarmSettings
from app.schemas import AlarmThresholds

DEFAULT_ALARM_THRESHOLDS = AlarmThresholds()

_cached: AlarmThresholds = DEFAULT_ALARM_THRESHOLDS


def current_thresholds() -> AlarmThresholds:
    """Ambang yang dipakai evaluasi alarm (cache memori)."""
    return _cached


def set_cached_thresholds(thresholds: AlarmThresholds) -> None:
    global _cached
    _cached = thresholds


async def load_thresholds(session: AsyncSession) -> AlarmThresholds:
    """Ambang dari database; fallback ke bawaan bila tabel/baris belum ada."""
    row = (await session.execute(select(AlarmSettings))).scalar_one_or_none()
    if row is None or not row.thresholds:
        return DEFAULT_ALARM_THRESHOLDS
    return AlarmThresholds.model_validate(row.thresholds)


async def save_thresholds(session: AsyncSession, thresholds: AlarmThresholds) -> None:
    """Simpan ambang ke database (commit dilakukan caller)."""
    data = thresholds.model_dump(by_alias=False)
    row = (await session.execute(select(AlarmSettings))).scalar_one_or_none()
    if row is None:
        session.add(AlarmSettings(id=1, thresholds=data))
    else:
        row.thresholds = data


async def refresh_cached_thresholds(session: AsyncSession) -> AlarmThresholds:
    """Muat ulang cache dari database (dipanggil saat startup)."""
    thresholds = await load_thresholds(session)
    set_cached_thresholds(thresholds)
    return thresholds
