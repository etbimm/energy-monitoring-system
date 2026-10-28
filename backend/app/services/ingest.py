from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Device, PhaseReading, Reading
from app.services.alarms import apply_alarms, clear_offline_alarm
from app.services.derive import apply_derived
from app.services.realtime import device_status, hub


def _parse_time(value: str | datetime | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc)
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    text = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


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
    reading = Reading(
        time=ts,
        device_id=device.id,
        voltage=payload.get("voltage"),
        current=payload.get("current"),
        power=payload.get("power"),
        apparent_power=payload.get("apparent_power"),
        reactive_power=payload.get("reactive_power"),
        energy_active=payload.get("energy_active"),
        energy_reactive=payload.get("energy_reactive"),
        frequency=payload.get("frequency"),
        power_factor=payload.get("power_factor"),
        energy_apparent=payload.get("energy_apparent"),
        thd_current=payload.get("thd_current"),
        thd_voltage=payload.get("thd_voltage"),
        unbalance_voltage=payload.get("unbalance_voltage"),
        unbalance_current=payload.get("unbalance_current"),
    )
    await session.merge(reading)

    phases = payload.get("phases") or {}
    for name, phase in phases.items():
        if name not in {"L1", "L2", "L3"}:
            continue
        await session.merge(
            PhaseReading(
                time=ts,
                device_id=device.id,
                phase=name,
                voltage=phase.get("voltage"),
                current=phase.get("current"),
                power=phase.get("power"),
                apparent_power=phase.get("apparent_power"),
                reactive_power=phase.get("reactive_power"),
                power_factor=phase.get("power_factor"),
                thd_current=phase.get("thd_current"),
                thd_voltage=phase.get("thd_voltage"),
            )
        )

    device.last_seen_at = ts
    await clear_offline_alarm(session, device.id)
    await apply_alarms(session, device, payload)
    await session.commit()

    snapshot = {**payload, "status": device_status(ts)}
    hub.remember(code, snapshot)
    await hub.broadcast({"type": "telemetry", "payload": snapshot})
    return snapshot
