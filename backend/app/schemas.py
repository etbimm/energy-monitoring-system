import ipaddress
import re
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class MeterCapabilities(CamelModel):
    per_phase: bool = True
    apparent_energy_register: bool = False
    thd_current: bool = False
    thd_voltage: bool = False
    max_harmonic_order: int = 0
    unbalance: bool = False
    reactive_energy: bool = True
    demand: bool = False


class PhaseReadingOut(CamelModel):
    phase: Literal["L1", "L2", "L3"]
    voltage: float | None = None
    current: float | None = None
    power: float | None = None
    apparent_power: float | None = None
    reactive_power: float | None = None
    power_factor: float | None = None
    thd_current: float | None = None
    thd_voltage: float | None = None


class DeviceOut(CamelModel):
    id: str
    name: str
    location: str | None = None
    brand: str | None = None
    model: str
    role: str
    status: Literal["online", "warning", "offline"]
    capabilities: MeterCapabilities
    voltage: float | None = None
    current: float | None = None
    power: float | None = None
    apparent_power: float | None = None
    reactive_power: float | None = None
    energy_active: float | None = None
    energy_reactive: float | None = None
    power_factor: float | None = None
    energy_apparent: float | None = None
    thd_current: float | None = None
    thd_voltage: float | None = None
    unbalance_voltage: float | None = None
    unbalance_current: float | None = None
    phases: list[PhaseReadingOut] = Field(default_factory=list)
    frequency: float | None = None
    last_seen: datetime | None = None


class TimeSeriesPoint(CamelModel):
    timestamp: datetime
    label: str
    power: float | None = None
    apparent_power: float | None = None
    reactive_power: float | None = None
    energy: float | None = None
    energy_reactive: float | None = None
    energy_apparent: float | None = None
    voltage: float | None = None
    current: float | None = None
    frequency: float | None = None
    power_factor: float | None = None
    thd_current: float | None = None


class SummaryOut(CamelModel):
    total_power: float
    total_apparent_power: float
    total_reactive_power: float
    energy_today: float
    online: int
    warning: int
    offline: int
    total: int


class EnergyTotalsOut(CamelModel):
    energy_active: float
    energy_reactive: float
    energy_apparent: float
    devices: int


class AlarmOut(CamelModel):
    id: str
    timestamp: datetime
    device_id: str
    device_name: str
    severity: Literal["critical", "warning", "info"]
    message: str
    acknowledged: bool


class TelemetryIn(BaseModel):
    device_code: str
    timestamp: datetime | None = None
    voltage: float | None = None
    voltage_ln: float | None = None
    voltage_ll: float | None = None
    current: float | None = None
    power: float | None = None
    apparent_power: float | None = None
    reactive_power: float | None = None
    energy_active: float | None = None
    energy_reactive: float | None = None
    frequency: float | None = None
    thd_current: float | None = None
    thd_voltage: float | None = None
    unbalance_voltage: float | None = None
    unbalance_current: float | None = None
    phases: dict | None = None


class ClientErrorIn(BaseModel):
    key: str = Field(min_length=1, max_length=120, pattern=r"^[a-zA-Z0-9._-]+$")
    summary: str = Field(min_length=1, max_length=300)


# ---------------------------------------------------------------------------
# Login & akun pengguna
# ---------------------------------------------------------------------------

UserRole = Literal["admin", "viewer"]
USERNAME_PATTERN = r"^[a-z0-9._-]{3,32}$"


def _normalize_username(value: str) -> str:
    return value.strip().lower() if isinstance(value, str) else value


def _required_text(value: str, label: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{label} wajib diisi")
    return value


class LoginIn(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize(cls, value: str) -> str:
        return _normalize_username(value)


class UserOut(CamelModel):
    id: int
    username: str
    full_name: str
    role: UserRole
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime | None = None


class UserCreate(CamelModel):
    username: str = Field(pattern=USERNAME_PATTERN)
    full_name: str = Field(min_length=1, max_length=80)
    role: UserRole = "viewer"
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username", mode="before")
    @classmethod
    def normalize(cls, value: str) -> str:
        return _normalize_username(value)

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return _required_text(value, "Nama lengkap")


class UserUpdate(CamelModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=80)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("full_name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return None if value is None else _required_text(value, "Nama lengkap")


class PasswordReset(CamelModel):
    password: str = Field(min_length=1, max_length=128)


class PasswordChange(CamelModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=1, max_length=128)


class AuditLogOut(CamelModel):
    id: int
    username: str | None = None
    action: str
    target: str | None = None
    detail: dict = Field(default_factory=dict)
    created_at: datetime


# ---------------------------------------------------------------------------
# Manajemen device (admin)
# ---------------------------------------------------------------------------

DEVICE_CODE_PATTERN = r"^PM-[A-Z0-9]+(-[A-Z0-9]+)*$"
# Pilihan bawaan. Nilai lain ("Lainnya") diperbolehkan, maks. 40 karakter.
KNOWN_ROLES = ("incoming", "outcoming", "distribution")
KNOWN_TRANSPORTS = ("rs485", "ethernet")


def _clean_choice(value: str | None, known: tuple[str, ...], label: str) -> str | None:
    """Rapikan nilai pilihan bebas.

    Nilai yang sama dengan pilihan bawaan (abaikan huruf besar/kecil, spasi,
    dan tanda hubung, mis. "RS-485" atau "Incoming") disimpan sebagai kode
    bawaannya, agar logika seperti total daya 'incoming' tetap berlaku.
    """
    if value is None:
        return None
    value = " ".join(value.split())
    if not value:
        raise ValueError(f"{label} wajib diisi")
    if len(value) > 40:
        raise ValueError(f"{label} maksimal 40 karakter")
    key = "".join(ch for ch in value.casefold() if ch.isalnum())
    for item in known:
        if key == item:
            return item
    return value


def clean_role(value: str | None) -> str | None:
    return _clean_choice(value, KNOWN_ROLES, "Peran")


def clean_transport(value: str | None) -> str | None:
    return _clean_choice(value, KNOWN_TRANSPORTS, "Jalur")
_HOSTNAME = re.compile(
    r"^(?=.{1,253}$)[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?"
    r"(\.[A-Za-z0-9]([A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*$"
)


def _validate_host(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        pass
    # Angka bertitik yang bukan IP valid (mis. 192.168.1.300) adalah salah ketik.
    if not _HOSTNAME.match(value) or value.replace(".", "").isdigit():
        raise ValueError("Host Modbus harus berupa alamat IP atau hostname yang valid")
    return value


def _validate_model(value: str | None) -> str | None:
    """Rapikan nama model.

    Model di luar daftar profil ("Lainnya") diperbolehkan. Penulisan yang
    hanya beda huruf besar/kecil/spasi dari model yang dikenal disamakan ke
    nama profilnya, agar meter tersebut tetap terbaca akuisisi.
    """
    from app.acquisition.profiles import PROFILES

    if value is None:
        return None
    value = " ".join(value.split())
    if not value:
        raise ValueError("Model meter wajib diisi")
    if len(value) > 60:
        raise ValueError("Model meter maksimal 60 karakter")
    for known in PROFILES:
        if value.casefold() == known.casefold():
            return known
    return value


def _validate_brand(value: str | None) -> str | None:
    if value is None:
        return None
    value = " ".join(value.split())
    if len(value) > 60:
        raise ValueError("Merek maksimal 60 karakter")
    return value or None


def _strip_optional(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


class DeviceModelOut(CamelModel):
    model: str
    brand: str
    label: str
    capabilities: MeterCapabilities
    # False = model "Lainnya": belum ada profil register, belum bisa dibaca
    # akuisisi mode modbus.
    supported: bool = True


class DeviceOptionsOut(CamelModel):
    """Pilihan Peran & Jalur untuk form: bawaan + nilai "Lainnya" yang
    sudah pernah dipakai device (agar bisa dipilih ulang)."""

    custom_roles: list[str] = Field(default_factory=list)
    custom_transports: list[str] = Field(default_factory=list)


class DeviceConfigOut(CamelModel):
    """Konfigurasi lengkap device untuk halaman admin (termasuk Modbus)."""

    id: str
    name: str
    location: str | None = None
    brand: str | None = None
    model: str
    role: str
    transport: str | None = None
    modbus_host: str | None = None
    modbus_port: int
    modbus_address: int | None = None
    rated_power_kw: float | None = None
    is_active: bool
    profile_supported: bool = True
    last_seen: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class DeviceCreate(CamelModel):
    device_code: str = Field(min_length=4, max_length=40, pattern=DEVICE_CODE_PATTERN)
    name: str = Field(min_length=1, max_length=80)
    location: str | None = Field(default=None, max_length=80)
    model: str
    # Wajib untuk model "Lainnya"; untuk model yang dikenal diisi otomatis.
    brand: str | None = None
    role: str
    transport: str
    modbus_host: str = Field(min_length=1, max_length=253)
    modbus_port: int = Field(default=502, ge=1, le=65535)
    modbus_address: int = Field(ge=1, le=247)
    rated_power_kw: float | None = Field(default=None, gt=0, le=100_000)

    @field_validator("device_code", mode="before")
    @classmethod
    def normalize_code(cls, value: str) -> str:
        return value.strip().upper() if isinstance(value, str) else value

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str) -> str:
        return _required_text(value, "Nama device")

    @field_validator("location")
    @classmethod
    def strip_location(cls, value: str | None) -> str | None:
        return _strip_optional(value)

    @field_validator("model")
    @classmethod
    def known_model(cls, value: str) -> str:
        return _validate_model(value)  # type: ignore[return-value]

    @field_validator("brand")
    @classmethod
    def clean_brand(cls, value: str | None) -> str | None:
        return _validate_brand(value)

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str) -> str:
        return clean_role(value)  # type: ignore[return-value]

    @field_validator("transport")
    @classmethod
    def valid_transport(cls, value: str) -> str:
        return clean_transport(value)  # type: ignore[return-value]

    @field_validator("modbus_host")
    @classmethod
    def valid_host(cls, value: str) -> str:
        return _validate_host(value)  # type: ignore[return-value]


class DeviceUpdate(CamelModel):
    """Hanya field yang dikirim yang diubah. Kode device tidak bisa diubah."""

    name: str | None = Field(default=None, min_length=1, max_length=80)
    location: str | None = Field(default=None, max_length=80)
    model: str | None = None
    brand: str | None = None
    role: str | None = None
    transport: str | None = None
    modbus_host: str | None = Field(default=None, min_length=1, max_length=253)
    modbus_port: int | None = Field(default=None, ge=1, le=65535)
    modbus_address: int | None = Field(default=None, ge=1, le=247)
    rated_power_kw: float | None = Field(default=None, gt=0, le=100_000)
    is_active: bool | None = None

    @field_validator("name")
    @classmethod
    def strip_name(cls, value: str | None) -> str | None:
        return None if value is None else _required_text(value, "Nama device")

    @field_validator("location")
    @classmethod
    def strip_location(cls, value: str | None) -> str | None:
        return _strip_optional(value)

    @field_validator("model")
    @classmethod
    def known_model(cls, value: str | None) -> str | None:
        return _validate_model(value)

    @field_validator("brand")
    @classmethod
    def clean_brand(cls, value: str | None) -> str | None:
        return _validate_brand(value)

    @field_validator("role")
    @classmethod
    def valid_role(cls, value: str | None) -> str | None:
        return clean_role(value)

    @field_validator("transport")
    @classmethod
    def valid_transport(cls, value: str | None) -> str | None:
        return clean_transport(value)

    @field_validator("modbus_host")
    @classmethod
    def valid_host(cls, value: str | None) -> str | None:
        return _validate_host(value)
