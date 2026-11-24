from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Device, PhaseReading, Reading
from app.services.alarms import apply_alarms, clear_offline_alarm, send_alarm_notices
from app.services.derive import PreviousReading, apply_derived
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


TELEMETRY_FIELDS = {
    "device_code", "timestamp", "voltage", "voltage_ln", "voltage_ll", "current",
    "power", "apparent_power", "reactive_power", "energy_active", "energy_reactive",
    "energy_apparent", "frequency", "thd_current", "thd_voltage", "unbalance_voltage",
    "unbalance_current", "unbalance_voltage_flag", "unbalance_current_flag", "phases",
}


def validate_telemetry(payload: object, expected_device_code: str | None = None) -> dict:
    """Validate the MQTT telemetry contract before it can reach persistence."""
    if not isinstance(payload, dict):
        raise ValueError("Payload telemetry harus berupa object")
    if set(payload) - TELEMETRY_FIELDS:
        raise ValueError("Payload telemetry memiliki field yang tidak dikenal")
    code = payload.get("device_code")
    if not isinstance(code, str) or not code.strip():
        raise ValueError("device_code wajib berupa string")
    if expected_device_code is not None and code != expected_device_code:
        raise ValueError("device_code tidak cocok dengan topic MQTT")
    for key, value in payload.items():
        if key in {"device_code", "timestamp", "phases"}:
            continue
        if key.endswith("_flag"):
            if value is not None and not isinstance(value, bool):
                raise ValueError(f"{key} harus berupa boolean")
        elif value is not None and (
            isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
        ):
            raise ValueError(f"{key} harus berupa angka finite atau null")
    phases = payload.get("phases")
    if phases is not None:
        if not isinstance(phases, dict) or set(phases) - {"L1", "L2", "L3"}:
            raise ValueError("phases harus object dengan kunci L1, L2, atau L3")
        for phase_name, phase in phases.items():
            if not isinstance(phase, dict) or set(phase) - set(PHASE_FIELDS):
                raise ValueError(f"Data fasa {phase_name} tidak valid")
            for key, value in phase.items():
                if value is not None and (
                    isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value)
                ):
                    raise ValueError(f"Nilai {key} pada {phase_name} harus angka finite atau null")
    timestamp = payload.get("timestamp")
    if timestamp is not None:
        try:
            ts = _parse_time(timestamp)
        except (AttributeError, TypeError, ValueError, OverflowError) as exc:
            raise ValueError("timestamp telemetry tidak valid") from exc
        now = datetime.now(timezone.utc)
        if ts < now - timedelta(minutes=5) or ts > now + timedelta(minutes=1):
            raise ValueError("timestamp telemetry di luar jendela waktu yang diizinkan")
    return payload


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


async def _previous_reading(session: AsyncSession, device_id: int, before: datetime) -> PreviousReading | None:
    row = (
        await session.execute(
            select(Reading.energy_active, Reading.energy_apparent, Reading.power_factor)
            .where(Reading.device_id == device_id, Reading.time < before)
            .order_by(Reading.time.desc())
            .limit(1)
        )
    ).first()
    if row is None:
        return None
    return PreviousReading(row.energy_active, row.energy_apparent, row.power_factor)


async def ingest_telemetry(
    session: AsyncSession, payload: dict, expected_device_code: str | None = None
) -> dict | None:
    payload = validate_telemetry(payload, expected_device_code)
    code = payload.get("device_code")
    if not code:
        return None

    device = (
        await session.execute(select(Device).where(Device.device_code == code))
    ).scalar_one_or_none()
    # Meter yang dinonaktifkan admin: data yang masih masuk diabaikan.
    if device is None or not device.is_active:
        return None

    ts = _parse_time(payload.get("timestamp"))
    # kVAh diintegrasikan dari pembacaan sebelumnya (lihat derive.py).
    payload = apply_derived(payload, await _previous_reading(session, device.id, ts))
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
