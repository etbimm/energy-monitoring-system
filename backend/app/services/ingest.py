from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Device, PhaseReading, Reading
from app.services.alarms import apply_alarms, clear_offline_alarm, send_alarm_notices
from app.services.derive import apply_derived
from app.services.error_reporting import resolve_error
from app.services.realtime import device_status, hub


def _parse_time(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


READING_FIELDS = (
    "voltage", "current", "power", "apparent_power", "reactive_power",
    "energy_active", "energy_reactive", "frequency", "power_factor",
    "energy_apparent", "thd_current", "thd_voltage", "unbalance_voltage",
    "unbalance_current",
)
PHASE_FIELDS = (
    "voltage", "current", "power", "apparent_power", "reactive_power",
    "power_factor", "thd_current", "thd_voltage",
)


def reading_values(device_id: int, ts: datetime, payload: dict) -> dict:
    return {"time": ts, "device_id": device_id, **{f: payload.get(f) for f in READING_FIELDS}}


def phase_values(device_id: int, ts: datetime, payload: dict) -> list[dict]:
    rows = []
    for name, phase in (payload.get("phases") or {}).items():
        if name not in {"L1", "L2", "L3"} or not isinstance(phase, dict):
            continue
        rows.append(
            {"time": ts, "device_id": device_id, "phase": name, **{f: phase.get(f) for f in PHASE_FIELDS}}
        )
    return rows


async def ingest_telemetry(session: AsyncSession, payload: dict) -> dict | None:
    payload = apply_derived(payload)
    code = payload.get("device_code")
    if not code:
        return None

    device = (
        await session.execute(select(Device).where(Device.device_code == code))
    ).scalar_one_or_none()
    if device is None:
        return None

    ts = _parse_time(payload.get("timestamp"))
    # INSERT ... ON CONFLICT DO NOTHING: satu statement per tabel, tanpa
    # SELECT lebih dulu seperti session.merge(). Pesan duplikat (mis. MQTT
    # QoS 1 terkirim ulang) diabaikan.
    await session.execute(
        pg_insert(Reading).values(reading_values(device.id, ts, payload)).on_conflict_do_nothing()
    )
    phases = phase_values(device.id, ts, payload)
    if phases:
        await session.execute(pg_insert(PhaseReading).values(phases).on_conflict_do_nothing())

    device.last_seen_at = ts
    await clear_offline_alarm(session, device.id)
    _, notices = await apply_alarms(session, device, payload, now=ts)
    await session.commit()
    await send_alarm_notices(notices)

    await resolve_error(f"meter:{code}", f"Power meter {code} kembali mengirim data.")
    snapshot = {**payload, "status": device_status(ts)}
    hub.remember(code, snapshot)
    await hub.broadcast({"type": "telemetry", "payload": snapshot})
    return snapshot
