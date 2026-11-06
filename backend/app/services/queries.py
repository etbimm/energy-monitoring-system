from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import case, func, literal_column, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import Alarm, Device, PhaseReading, Reading
from app.config import get_settings
from app.schemas import (
    AlarmOut,
    DeviceOut,
    EnergyTotalsOut,
    MeterCapabilities,
    PhaseReadingOut,
    SummaryOut,
    TimeSeriesPoint,
)
from app.services.realtime import device_status


def _caps(raw: dict | None, model: str) -> MeterCapabilities:
    data = raw or {}
    return MeterCapabilities(
        per_phase=data.get("perPhase", True),
        apparent_energy_register=data.get("apparentEnergyRegister", False),
        thd_current=True,
        thd_voltage=model != "WEIDMULLER EM220",
        max_harmonic_order=data.get("maxHarmonicOrder", 0),
        unbalance=data.get("unbalance", False),
        reactive_energy=data.get("reactiveEnergy", True),
        demand=data.get("demand", False),
    )


def _severity_rank():
    return func.max(
        case(
            (Alarm.severity == "critical", 2),
            (Alarm.severity == "warning", 1),
            else_=0,
        )
    )


async def list_devices(session: AsyncSession) -> list[DeviceOut]:
    latest = (
        select(Reading)
        .distinct(Reading.device_id)
        .order_by(Reading.device_id, Reading.time.desc())
        .subquery()
    )
    latest_reading = aliased(Reading, latest)
    open_alarm = (
        select(Alarm.device_id, _severity_rank().label("rank"))
        .where(Alarm.cleared_at.is_(None))
        .group_by(Alarm.device_id)
        .subquery()
    )

    rows = (
        await session.execute(
            select(Device, latest_reading, open_alarm.c.rank)
            .outerjoin(latest_reading, Device.id == latest_reading.device_id)
            .outerjoin(open_alarm, Device.id == open_alarm.c.device_id)
            .order_by(Device.id)
        )
    ).all()

    device_ids = [device.id for device, *_ in rows]
    phases_by_device: dict[int, list] = {device_id: [] for device_id in device_ids}
    if device_ids:
        latest_phase = (
            select(PhaseReading)
            .distinct(PhaseReading.device_id, PhaseReading.phase)
            .order_by(PhaseReading.device_id, PhaseReading.phase, PhaseReading.time.desc())
            .subquery()
        )
        phase_rows = (
            await session.execute(
                select(latest_phase).where(latest_phase.c.device_id.in_(device_ids))
            )
        ).all()
        for phase in phase_rows:
            phases_by_device.setdefault(phase.device_id, []).append(phase)

    result: list[DeviceOut] = []
    for device, reading, alarm_rank in rows:
        has_warning = (alarm_rank or 0) > 0
        status = device_status(device.last_seen_at, has_warning)
        phases = sorted(phases_by_device.get(device.id, []), key=lambda item: item.phase)
        has_reading = reading is not None and getattr(reading, "time", None) is not None
        result.append(
            DeviceOut(
                id=device.device_code,
                name=device.name,
                location=device.location,
                brand=device.brand,
                model=device.model,
                role=device.role,
                status=status,
                capabilities=_caps(device.capabilities, device.model),
                voltage=reading.voltage if has_reading else None,
                current=reading.current if has_reading else None,
                power=reading.power if has_reading else None,
                apparent_power=reading.apparent_power if has_reading else None,
                reactive_power=reading.reactive_power if has_reading else None,
                energy_active=reading.energy_active if has_reading else None,
                energy_reactive=reading.energy_reactive if has_reading else None,
                power_factor=reading.power_factor if has_reading else None,
                energy_apparent=reading.energy_apparent if has_reading else None,
                thd_current=reading.thd_current if has_reading else None,
                thd_voltage=reading.thd_voltage if has_reading else None,
                unbalance_voltage=reading.unbalance_voltage if has_reading else None,
                unbalance_current=reading.unbalance_current if has_reading else None,
                frequency=reading.frequency if has_reading else None,
                last_seen=device.last_seen_at,
                phases=[
                    PhaseReadingOut(
                        phase=item.phase,  # type: ignore[arg-type]
                        voltage=item.voltage,
                        current=item.current,
                        power=item.power,
                        apparent_power=item.apparent_power,
                        reactive_power=item.reactive_power,
                        power_factor=item.power_factor,
                        thd_current=item.thd_current,
                        thd_voltage=item.thd_voltage,
                    )
                    for item in phases
                ],
            )
        )
    return result


def local_day_start(now: datetime | None = None) -> datetime:
    """Awal hari (00:00) di zona waktu lokal pabrik, dikembalikan dalam UTC."""
    tz = get_settings().tz
    local_now = (now or datetime.now(timezone.utc)).astimezone(tz)
    return local_now.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def _device_filter(device_code: str | None, role: str | None):
    if device_code:
        return Device.device_code == device_code
    return Device.role == (role or "incoming")


async def get_energy_totals(
    session: AsyncSession,
    *,
    start: datetime,
    end: datetime,
    device_code: str | None = None,
    role: str | None = "incoming",
) -> EnergyTotalsOut:
    """Total energi rentang waktu = jumlah delta per meter.

    Delta dihitung per meter (`last - first`) baru dijumlahkan, sehingga meter
    yang offline di awal/akhir rentang tidak merusak total. Delta negatif
    (counter reset / meter diganti) diabaikan.
    """
    per_device = (
        select(
            Reading.device_id,
            (
                func.last(Reading.energy_active, Reading.time)
                - func.first(Reading.energy_active, Reading.time)
            ).label("active"),
            (
                func.last(Reading.energy_reactive, Reading.time)
                - func.first(Reading.energy_reactive, Reading.time)
            ).label("reactive"),
            (
                func.last(Reading.energy_apparent, Reading.time)
                - func.first(Reading.energy_apparent, Reading.time)
            ).label("apparent"),
        )
        .join(Device, Device.id == Reading.device_id)
        .where(Reading.time >= start, Reading.time <= end, _device_filter(device_code, role))
        .group_by(Reading.device_id)
    )
    rows = (await session.execute(per_device)).all()

    def positive_sum(attr: str) -> float:
        total = 0.0
        for row in rows:
            value = getattr(row, attr)
            if value is not None and value > 0:
                total += float(value)
        return total

    return EnergyTotalsOut(
        energy_active=positive_sum("active"),
        energy_reactive=positive_sum("reactive"),
        energy_apparent=positive_sum("apparent"),
        devices=len(rows),
    )


async def get_summary(session: AsyncSession) -> SummaryOut:
    devices = await list_devices(session)
    incoming = [item for item in devices if item.role == "incoming"]
    now = datetime.now(timezone.utc)
    totals = await get_energy_totals(
        session, start=local_day_start(now), end=now, role="incoming"
    )

    return SummaryOut(
        total_power=sum(item.power or 0 for item in incoming),
        total_apparent_power=sum(item.apparent_power or 0 for item in incoming),
        total_reactive_power=sum(item.reactive_power or 0 for item in incoming),
        energy_today=totals.energy_active,
        online=sum(1 for item in devices if item.status == "online"),
        warning=sum(1 for item in devices if item.status == "warning"),
        offline=sum(1 for item in devices if item.status == "offline"),
        total=len(devices),
    )


def _bucket_interval(bucket: str) -> str | None:
    mapping = {
        "raw": None,
        "1m": "1 minute",
        "5m": "5 minutes",
        "15m": "15 minutes",
        "1h": "1 hour",
        "1d": "1 day",
    }
    if bucket not in mapping:
        raise ValueError("bucket harus salah satu dari: raw, 1m, 5m, 15m, 1h, 1d")
    return mapping[bucket]


def _bucket_expr(interval: str):
    """time_bucket; bucket harian mengikuti zona waktu lokal (00:00 WIB)."""
    width = literal_column(f"INTERVAL '{interval}'")
    if interval == "1 day":
        # Nama zona sudah divalidasi di Settings, aman dijadikan literal SQL.
        tz = literal_column(f"'{get_settings().timezone}'")
        return func.time_bucket(width, Reading.time, tz)
    return func.time_bucket(width, Reading.time)


def _point(ts: datetime, row) -> TimeSeriesPoint:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    local = ts.astimezone(get_settings().tz)
    return TimeSeriesPoint(
        timestamp=ts,
        label=local.strftime("%H:%M"),
        power=row.power,
        apparent_power=row.apparent_power,
        reactive_power=row.reactive_power,
        energy=row.energy_active,
        energy_reactive=row.energy_reactive,
        energy_apparent=row.energy_apparent,
        voltage=row.voltage,
        current=row.current,
        frequency=row.frequency,
        power_factor=row.power_factor,
        thd_current=row.thd_current,
    )


# Mode raw untuk gabungan beberapa meter tidak bisa dikelompokkan per
# timestamp persis (tiap meter dibaca pada detik berbeda), jadi dibulatkan
# ke bucket minimum ini.
AGGREGATE_RAW_INTERVAL = "1 minute"


async def get_readings(
    session: AsyncSession,
    *,
    device_code: str | None,
    start: datetime,
    end: datetime,
    bucket: str = "5m",
    role: str | None = "incoming",
) -> list[TimeSeriesPoint]:
    interval = _bucket_interval(bucket)
    filters = [Reading.time >= start, Reading.time <= end]
    device_filter = _device_filter(device_code, role)

    if interval is None:
        if device_code:
            stmt = (
                select(Reading)
                .join(Device, Device.id == Reading.device_id)
                .where(*filters, device_filter)
                .order_by(Reading.time)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_point(row.time, row) for row in rows]
        interval = AGGREGATE_RAW_INTERVAL

    bucket_col = _bucket_expr(interval).label("bucket")
    per_device = (
        select(
            Reading.device_id,
            bucket_col,
            func.avg(Reading.power).label("power"),
            func.avg(Reading.apparent_power).label("apparent_power"),
            func.avg(Reading.reactive_power).label("reactive_power"),
            func.last(Reading.energy_active, Reading.time).label("energy_active"),
            func.last(Reading.energy_reactive, Reading.time).label("energy_reactive"),
            func.last(Reading.energy_apparent, Reading.time).label("energy_apparent"),
            func.avg(Reading.voltage).label("voltage"),
            func.avg(Reading.current).label("current"),
            func.avg(Reading.frequency).label("frequency"),
            (
                func.avg(Reading.power)
                / func.nullif(func.avg(Reading.apparent_power), 0)
            ).label("power_factor"),
            func.avg(Reading.thd_current).label("thd_current"),
        )
        .join(Device, Device.id == Reading.device_id)
        .where(*filters, device_filter)
        .group_by(Reading.device_id, bucket_col)
        .subquery()
    )
    stmt = (
        select(
            per_device.c.bucket,
            func.sum(per_device.c.power).label("power"),
            func.sum(per_device.c.apparent_power).label("apparent_power"),
            func.sum(per_device.c.reactive_power).label("reactive_power"),
            func.sum(per_device.c.energy_active).label("energy_active"),
            func.sum(per_device.c.energy_reactive).label("energy_reactive"),
            func.sum(per_device.c.energy_apparent).label("energy_apparent"),
            func.avg(per_device.c.voltage).label("voltage"),
            func.avg(per_device.c.current).label("current"),
            func.avg(per_device.c.frequency).label("frequency"),
            (
                func.sum(per_device.c.power)
                / func.nullif(func.sum(per_device.c.apparent_power), 0)
            ).label("power_factor"),
            func.avg(per_device.c.thd_current).label("thd_current"),
        )
        .group_by(per_device.c.bucket)
        .order_by(per_device.c.bucket)
    )
    rows = (await session.execute(stmt)).all()
    return [_point(row.bucket, row) for row in rows]


async def list_alarms(session: AsyncSession, include_cleared: bool = False) -> list[AlarmOut]:
    stmt = select(Alarm, Device).join(Device, Device.id == Alarm.device_id)
    if not include_cleared:
        stmt = stmt.where(Alarm.cleared_at.is_(None))
    stmt = stmt.order_by(Alarm.triggered_at.desc()).limit(200)
    rows = (await session.execute(stmt)).all()
    return [
        AlarmOut(
            id=str(alarm.id),
            timestamp=alarm.triggered_at,
            device_id=device.device_code,
            device_name=device.name,
            severity=alarm.severity,  # type: ignore[arg-type]
            message=alarm.message,
            acknowledged=alarm.acknowledged,
        )
        for alarm, device in rows
    ]
