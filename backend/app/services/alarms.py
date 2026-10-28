from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Alarm, Device
from app.services.realtime import hub

NOMINAL_HZ = 50.0


def _now() -> datetime:
    return datetime.now(timezone.utc)


def evaluate_conditions(payload: dict, device: Device) -> list[tuple[str, str, str]]:
    """Kembalikan list (alarm_type, severity, message) yang sedang aktif."""
    found: list[tuple[str, str, str]] = []
    pf = payload.get("power_factor")
    voltage = payload.get("voltage")
    freq = payload.get("frequency")
    thd_i = payload.get("thd_current")
    unbalance_v = payload.get("unbalance_voltage")
    power = payload.get("power")

    if pf is not None:
        if pf < 0.85:
            found.append(("power_factor", "critical", f"Power factor kritis ({pf:.3f})"))
        elif pf < 0.90:
            found.append(("power_factor", "warning", f"Power factor rendah ({pf:.3f})"))

    if voltage is not None and voltage > 0:
        if voltage < 350 or voltage > 440:
            found.append(("voltage", "critical", f"Tegangan di luar batas kritis ({voltage:.1f} V)"))
        elif voltage < 385 or voltage > 415:
            found.append(("voltage", "warning", f"Tegangan di luar rentang normal ({voltage:.1f} V)"))

    if freq is not None and freq > 0:
        deviation = abs(freq - NOMINAL_HZ)
        if deviation > 1.0:
            found.append(("frequency", "critical", f"Deviasi frekuensi kritis ({freq:.2f} Hz)"))
        elif deviation > 0.5:
            found.append(("frequency", "warning", f"Deviasi frekuensi ({freq:.2f} Hz)"))

    if thd_i is not None:
        if thd_i >= 8:
            found.append(("thd_current", "critical", f"THD arus kritis ({thd_i:.1f} %)"))
        elif thd_i >= 5:
            found.append(("thd_current", "warning", f"THD arus tinggi ({thd_i:.1f} %)"))

    if unbalance_v is not None:
        if unbalance_v > 5:
            found.append(("unbalance_voltage", "critical", f"Unbalance tegangan kritis ({unbalance_v:.1f} %)"))
        elif unbalance_v > 2:
            found.append(("unbalance_voltage", "warning", f"Unbalance tegangan ({unbalance_v:.1f} %)"))

    if device.rated_power_kw and power:
        load = power / device.rated_power_kw
        if load > 0.95:
            found.append(("load", "critical", f"Beban > 95% kapasitas ({load:.0%})"))
        elif load > 0.80:
            found.append(("load", "warning", f"Beban > 80% kapasitas ({load:.0%})"))

    return found


async def apply_alarms(session: AsyncSession, device: Device, payload: dict) -> list[Alarm]:
    active = evaluate_conditions(payload, device)
    active_types = {item[0] for item in active}
    created: list[Alarm] = []

    open_alarms = (
        await session.execute(
            select(Alarm).where(Alarm.device_id == device.id, Alarm.cleared_at.is_(None))
        )
    ).scalars().all()
    open_by_type = {alarm.alarm_type: alarm for alarm in open_alarms}

    for alarm_type, severity, message in active:
        existing = open_by_type.get(alarm_type)
        if existing:
            existing.severity = severity
            existing.message = message
            continue
        alarm = Alarm(
            device_id=device.id,
            alarm_type=alarm_type,
            severity=severity,
            message=message,
            triggered_at=_now(),
        )
        session.add(alarm)
        created.append(alarm)

    for alarm in open_alarms:
        if alarm.alarm_type not in active_types and alarm.alarm_type not in {"offline"}:
            alarm.cleared_at = _now()

    if created:
        await session.flush()
        for alarm in created:
            await hub.broadcast(
                {
                    "type": "alarm",
                    "payload": {
                        "id": str(alarm.id),
                        "deviceId": device.device_code,
                        "deviceName": device.name,
                        "severity": alarm.severity,
                        "message": alarm.message,
                        "timestamp": alarm.triggered_at.isoformat(),
                    },
                }
            )
    return created


async def set_offline_alarm(session: AsyncSession, device: Device, critical: bool) -> None:
    severity = "critical" if critical else "warning"
    message = "Meter offline > 3 menit" if critical else "Heartbeat meter terputus > 30 detik"
    existing = (
        await session.execute(
            select(Alarm).where(
                Alarm.device_id == device.id,
                Alarm.alarm_type == "offline",
                Alarm.cleared_at.is_(None),
            )
        )
    ).scalar_one_or_none()
    if existing:
        existing.severity = severity
        existing.message = message
        return
    session.add(
        Alarm(
            device_id=device.id,
            alarm_type="offline",
            severity=severity,
            message=message,
            triggered_at=_now(),
        )
    )


async def clear_offline_alarm(session: AsyncSession, device_id: int) -> None:
    await session.execute(
        update(Alarm)
        .where(
            Alarm.device_id == device_id,
            Alarm.alarm_type == "offline",
            Alarm.cleared_at.is_(None),
        )
        .values(cleared_at=_now())
    )
