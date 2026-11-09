from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import Double, Integer, case, column, func, literal_column, select, table, true
from sqlalchemy.types import DateTime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.models import Alarm, Device, PhaseReading, Reading
from app.acquisition.profiles import register_capabilities
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

# Continuous aggregate TimescaleDB (lihat database/init/01-schema.sql).
READINGS_1MIN = table(
    "readings_1min",
    column("device_id", Integer),
    column("bucket", DateTime(timezone=True)),
    *(
        column(name, Double)
        for name in (
            "voltage", "current", "power", "apparent_power", "reactive_power",
            "frequency", "power_factor", "thd_current", "thd_voltage",
            "energy_active", "energy_reactive", "energy_apparent",
        )
    ),
)


def _caps(raw: dict | None, model: str) -> MeterCapabilities:
    # Kapabilitas THD diturunkan dari profil register meter (profiles.py).
    data = {**(raw or {}), **register_capabilities(model)}
    return MeterCapabilities(
        per_phase=data.get("perPhase", True),
        apparent_energy_register=data.get("apparentEnergyRegister", False),
        thd_current=data.get("thdCurrent", False),
        thd_voltage=data.get("thdVoltage", False),
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
    # Pembacaan terakhir per meter: LATERAL ... ORDER BY time DESC LIMIT 1
    # memakai index (device_id, time DESC), bukan memindai seluruh hypertable
    # seperti DISTINCT ON.
    latest = (
        select(Reading)
        .where(Reading.device_id == Device.id)
        .order_by(Reading.time.desc())
        .limit(1)
        .correlate(Device)
        .lateral("latest_reading")
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
            .select_from(Device)
            .outerjoin(latest_reading, true())
            .outerjoin(open_alarm, Device.id == open_alarm.c.device_id)
            .order_by(Device.id)
        )
    ).all()

    device_ids = [device.id for device, *_ in rows]
    phases_by_device: dict[int, list] = {device_id: [] for device_id in device_ids}
    if device_ids:
        # Tiga baris terbaru per meter = L1/L2/L3 dari pembacaan terakhir.
        latest_phase = (
            select(PhaseReading)
            .where(PhaseReading.device_id == Device.id)
            .order_by(PhaseReading.time.desc())
            .limit(3)
            .correlate(Device)
            .lateral("latest_phase")
        )
        phase_rows = (
            await session.execute(
                select(latest_phase).select_from(Device).join(latest_phase, true()).where(Device.id.in_(device_ids))
            )
        ).all()
        for phase in phase_rows:
            bucket = phases_by_device.setdefault(phase.device_id, [])
            if all(item.phase != phase.phase for item in bucket):
                bucket.append(phase)

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
    (counter reset / meter diganti) diabaikan. Sumber data: continuous
    aggregate `readings_1min` (nilai counter terakhir tiap menit), sehingga
    tetap tersedia setelah data mentah dihapus retention policy.
    """
    m = READINGS_1MIN
    per_device = (
        select(
            m.c.device_id,
            (func.last(m.c.energy_active, m.c.bucket) - func.first(m.c.energy_active, m.c.bucket)).label("active"),
            (func.last(m.c.energy_reactive, m.c.bucket) - func.first(m.c.energy_reactive, m.c.bucket)).label("reactive"),
            (func.last(m.c.energy_apparent, m.c.bucket) - func.first(m.c.energy_apparent, m.c.bucket)).label("apparent"),
        )
        .join(Device, Device.id == m.c.device_id)
        .where(m.c.bucket >= _minute_floor(start), m.c.bucket <= end, _device_filter(device_code, role))
        .group_by(m.c.device_id)
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


_BUCKETS: dict[str, tuple[str | None, int]] = {
    # nama: (interval SQL, detik per titik)
    "raw": (None, 5),
    "1m": ("1 minute", 60),
    "5m": ("5 minutes", 300),
    "15m": ("15 minutes", 900),
    "1h": ("1 hour", 3600),
    "1d": ("1 day", 86400),
}

# Batas ukuran respons agar query tidak mengembalikan jutaan baris (B6).
MAX_RAW_RANGE = timedelta(days=7)
MAX_POINTS = 20_000


def _bucket_interval(bucket: str) -> str | None:
    if bucket not in _BUCKETS:
        raise ValueError("bucket harus salah satu dari: raw, 1m, 5m, 15m, 1h, 1d")
    return _BUCKETS[bucket][0]


def validate_range(start: datetime, end: datetime, bucket: str) -> None:
    """Tolak rentang yang terlalu besar untuk resolusi yang diminta."""
    _bucket_interval(bucket)
    if start > end:
        raise ValueError("'from' harus sebelum 'to'")
    span = end - start
    if bucket == "raw":
        if span > MAX_RAW_RANGE:
            raise ValueError("bucket raw maksimal 7 hari; gunakan bucket 1m/5m/15m/1h/1d")
        return
    points = span.total_seconds() / _BUCKETS[bucket][1]
    if points > MAX_POINTS:
        raise ValueError(
            f"rentang terlalu besar untuk bucket {bucket} (~{int(points)} titik, maks {MAX_POINTS}); "
            "pilih bucket yang lebih besar"
        )


def _minute_floor(ts: datetime) -> datetime:
    return ts.replace(second=0, microsecond=0)


def _bucket_expr(interval: str, column=None):
    """time_bucket; bucket harian mengikuti zona waktu lokal (00:00 WIB)."""
    column = READINGS_1MIN.c.bucket if column is None else column
    width = literal_column(f"INTERVAL '{interval}'")
    if interval == "1 day":
        # Nama zona sudah divalidasi di Settings, aman dijadikan literal SQL.
        tz = literal_column(f"'{get_settings().timezone}'")
        return func.time_bucket(width, column, tz)
    return func.time_bucket(width, column)


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
    validate_range(start, end, bucket)
    interval = _bucket_interval(bucket)
    device_filter = _device_filter(device_code, role)

    if interval is None:
        if device_code:
            stmt = (
                select(Reading)
                .join(Device, Device.id == Reading.device_id)
                .where(Reading.time >= start, Reading.time <= end, device_filter)
                .order_by(Reading.time)
            )
            rows = (await session.execute(stmt)).scalars().all()
            return [_point(row.time, row) for row in rows]
        interval = AGGREGATE_RAW_INTERVAL

    # Semua bucket >= 1 menit dibaca dari continuous aggregate readings_1min
    # (sudah dirata-ratakan per menit oleh TimescaleDB), bukan dari tabel
    # mentah. Rata-rata dari rata-rata per menit setara karena jumlah sampel
    # per menit sama.
    m = READINGS_1MIN
    bucket_col = _bucket_expr(interval, m.c.bucket).label("bucket")
    per_device = (
        select(
            m.c.device_id,
            bucket_col,
            func.avg(m.c.power).label("power"),
            func.avg(m.c.apparent_power).label("apparent_power"),
            func.avg(m.c.reactive_power).label("reactive_power"),
            func.last(m.c.energy_active, m.c.bucket).label("energy_active"),
            func.last(m.c.energy_reactive, m.c.bucket).label("energy_reactive"),
            func.last(m.c.energy_apparent, m.c.bucket).label("energy_apparent"),
            func.avg(m.c.voltage).label("voltage"),
            func.avg(m.c.current).label("current"),
            func.avg(m.c.frequency).label("frequency"),
            (func.avg(m.c.power) / func.nullif(func.avg(m.c.apparent_power), 0)).label("power_factor"),
            func.avg(m.c.thd_current).label("thd_current"),
        )
        .join(Device, Device.id == m.c.device_id)
        .where(m.c.bucket >= _minute_floor(start), m.c.bucket <= end, device_filter)
        .group_by(m.c.device_id, bucket_col)
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
