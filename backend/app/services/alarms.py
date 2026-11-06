from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models import Alarm, Device
from app.services.realtime import hub

NOMINAL_HZ = 50.0
SQRT3 = 3 ** 0.5

# Batas tegangan antar-fasa (L-L, nominal 400 V).
VOLTAGE_LL_WARNING = (385.0, 415.0)
VOLTAGE_LL_CRITICAL = (350.0, 440.0)
# Batas fasa-netral (L-N, nominal 230 V) = batas L-L dibagi sqrt(3).
VOLTAGE_LN_WARNING = tuple(round(v / SQRT3, 1) for v in VOLTAGE_LL_WARNING)
VOLTAGE_LN_CRITICAL = tuple(round(v / SQRT3, 1) for v in VOLTAGE_LL_CRITICAL)

# Deadband (hysteresis): alarm yang sudah aktif baru dianggap normal bila nilai
# kembali melewati ambang ditambah margin ini, agar tidak "flapping".
DEADBAND = {
    "power_factor": 0.01,  # PF
    "voltage_ll": 4.0,  # V (1% dari 400 V)
    "voltage_ln": 2.3,  # V (1% dari 230 V)
    "frequency": 0.1,  # Hz
    "thd_current": 0.5,  # % (poin)
    "unbalance_voltage": 0.3,  # % (poin)
    "load": 0.03,  # fraksi kapasitas (3%)
}

# Tipe alarm yang dikelola terpisah (offline watcher), bukan dari telemetry.
_EXTERNAL_TYPES = {"offline"}


def _voltage_basis(payload: dict) -> tuple[float, str, tuple[float, float], tuple[float, float]] | None:
    """Pilih tegangan yang benar-benar diukur meter beserta batasnya.

    Prioritas: L-N terukur, lalu L-L terukur, lalu `voltage` (selalu L-L).
    """
    ln = payload.get("voltage_ln")
    if ln is not None and ln > 0:
        return ln, "L-N", VOLTAGE_LN_WARNING, VOLTAGE_LN_CRITICAL
    ll = payload.get("voltage_ll")
    if ll is None:
        ll = payload.get("voltage")
    if ll is not None and ll > 0:
        return ll, "L-L", VOLTAGE_LL_WARNING, VOLTAGE_LL_CRITICAL
    return None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def evaluate_conditions(
    payload: dict,
    device: Device,
    hysteresis: bool = False,
) -> list[tuple[str, str, str]]:
    """Kembalikan list (alarm_type, severity, message) yang sedang aktif.

    `hysteresis=True` menggeser setiap ambang ke arah normal sebesar DEADBAND.
    Mode ini dipakai untuk alarm yang sudah aktif: alarm tetap dianggap abnormal
    sampai nilai benar-benar kembali normal (melewati ambang + margin).
    """
    m = 1.0 if hysteresis else 0.0
    found: list[tuple[str, str, str]] = []
    pf = payload.get("power_factor")
    voltage_basis = _voltage_basis(payload)
    freq = payload.get("frequency")
    thd_i = payload.get("thd_current")
    unbalance_v = payload.get("unbalance_voltage")
    power = payload.get("power")

    if pf is not None:
        d = DEADBAND["power_factor"] * m
        if pf < 0.85 + d:
            found.append(("power_factor", "critical", f"Power factor kritis ({pf:.3f})"))
        elif pf < 0.90 + d:
            found.append(("power_factor", "warning", f"Power factor rendah ({pf:.3f})"))

    if voltage_basis is not None:
        value, kind, (warn_lo, warn_hi), (crit_lo, crit_hi) = voltage_basis
        d = DEADBAND["voltage_ln" if kind == "L-N" else "voltage_ll"] * m
        if value < crit_lo + d or value > crit_hi - d:
            found.append(("voltage", "critical", f"Tegangan {kind} di luar batas kritis ({value:.1f} V)"))
        elif value < warn_lo + d or value > warn_hi - d:
            found.append(("voltage", "warning", f"Tegangan {kind} di luar rentang normal ({value:.1f} V)"))

    if freq is not None and freq > 0:
        d = DEADBAND["frequency"] * m
        deviation = abs(freq - NOMINAL_HZ)
        if deviation > 1.0 - d:
            found.append(("frequency", "critical", f"Deviasi frekuensi kritis ({freq:.2f} Hz)"))
        elif deviation > 0.5 - d:
            found.append(("frequency", "warning", f"Deviasi frekuensi ({freq:.2f} Hz)"))

    if thd_i is not None:
        d = DEADBAND["thd_current"] * m
        if thd_i >= 8 - d:
            found.append(("thd_current", "critical", f"THD arus kritis ({thd_i:.1f} %)"))
        elif thd_i >= 5 - d:
            found.append(("thd_current", "warning", f"THD arus tinggi ({thd_i:.1f} %)"))

    if unbalance_v is not None:
        d = DEADBAND["unbalance_voltage"] * m
        if unbalance_v > 5 - d:
            found.append(("unbalance_voltage", "critical", f"Unbalance tegangan kritis ({unbalance_v:.1f} %)"))
        elif unbalance_v > 2 - d:
            found.append(("unbalance_voltage", "warning", f"Unbalance tegangan ({unbalance_v:.1f} %)"))

    if device.rated_power_kw and power:
        d = DEADBAND["load"] * m
        load = power / device.rated_power_kw
        if load > 0.95 - d:
            found.append(("load", "critical", f"Beban > 95% kapasitas ({load:.0%})"))
        elif load > 0.80 - d:
            found.append(("load", "warning", f"Beban > 80% kapasitas ({load:.0%})"))

    return found


@dataclass
class AlarmTracker:
    """Status sementara (di memori) untuk delay aktif/normal alarm."""

    pending_since: dict[tuple[int, str], datetime] = field(default_factory=dict)
    clearing_since: dict[tuple[int, str], datetime] = field(default_factory=dict)


tracker = AlarmTracker()


@dataclass(frozen=True)
class AlarmNotice:
    """Notifikasi Telegram yang dikirim SETELAH transaksi ingest di-commit."""

    action: str  # "report" | "resolve"
    key: str
    text: str


def _notice_key(device: Device, alarm_type: str) -> str:
    return f"alarm:{device.device_code}:{alarm_type}"


async def apply_alarms(
    session: AsyncSession,
    device: Device,
    payload: dict,
    now: datetime | None = None,
    state: AlarmTracker | None = None,
) -> tuple[list[Alarm], list[AlarmNotice]]:
    """Evaluasi alarm telemetry dengan delay dan hysteresis.

    - Alarm baru dibuat hanya jika kondisi abnormal bertahan >= ALARM_ON_DELAY.
    - Alarm aktif baru dinyatakan normal jika nilai kembali melewati ambang +
      DEADBAND dan bertahan normal >= ALARM_OFF_DELAY.
    - Alarm berseverity critical menghasilkan notifikasi Telegram; notifikasi
      pulih dikirim saat alarm critical dinormalkan atau turun ke warning.
    """
    settings = get_settings()
    now = now or _now()
    state = state or tracker
    strict = {t: (sev, msg) for t, sev, msg in evaluate_conditions(payload, device)}
    relaxed = {t: (sev, msg) for t, sev, msg in evaluate_conditions(payload, device, hysteresis=True)}
    created: list[Alarm] = []
    notices: list[AlarmNotice] = []

    open_alarms = (
        await session.execute(
            select(Alarm).where(Alarm.device_id == device.id, Alarm.cleared_at.is_(None))
        )
    ).scalars().all()
    open_by_type = {
        alarm.alarm_type: alarm for alarm in open_alarms if alarm.alarm_type not in _EXTERNAL_TYPES
    }

    for alarm_type in set(open_by_type) | set(strict):
        key = (device.id, alarm_type)
        existing = open_by_type.get(alarm_type)

        if existing is not None:
            if alarm_type in relaxed:
                # Masih abnormal (termasuk zona deadband): alarm tetap aktif.
                state.clearing_since.pop(key, None)
                severity, message = strict.get(alarm_type) or relaxed[alarm_type]
                existing.severity = severity
                existing.message = message
            else:
                started = state.clearing_since.setdefault(key, now)
                if (now - started).total_seconds() >= settings.alarm_off_delay_seconds:
                    existing.cleared_at = now
                    state.clearing_since.pop(key, None)
            continue

        started = state.pending_since.setdefault(key, now)
        if (now - started).total_seconds() < settings.alarm_on_delay_seconds:
            continue
        state.pending_since.pop(key, None)
        severity, message = strict[alarm_type]
        alarm = Alarm(
            device_id=device.id,
            alarm_type=alarm_type,
            severity=severity,
            message=message,
            triggered_at=now,
        )
        session.add(alarm)
        created.append(alarm)

    # Kondisi yang hilang sebelum delay terpenuhi tidak jadi alarm.
    for key in [k for k in state.pending_since if k[0] == device.id and k[1] not in strict]:
        state.pending_since.pop(key, None)

    for alarm in [*open_by_type.values(), *created]:
        notice_key = _notice_key(device, alarm.alarm_type)
        label = f"{device.name} ({device.device_code})"
        if alarm.cleared_at is None and alarm.severity == "critical":
            notices.append(AlarmNotice("report", notice_key, f"{label}: {alarm.message}"))
        else:
            notices.append(
                AlarmNotice("resolve", notice_key, f"{label}: alarm {alarm.alarm_type} tidak lagi kritis.")
            )

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
    return created, notices


async def send_alarm_notices(notices: list[AlarmNotice]) -> None:
    from app.services.error_reporting import error_reporter

    for notice in notices:
        if notice.action == "report":
            await error_reporter.report(notice.key, notice.text, title="EMS ALARM KRITIS")
        else:
            await error_reporter.resolve(notice.key, notice.text, title="EMS ALARM PULIH")


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
