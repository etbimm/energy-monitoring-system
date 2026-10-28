from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field
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


class SummaryOut(CamelModel):
    total_power: float
    total_apparent_power: float
    total_reactive_power: float
    energy_today: float
    online: int
    warning: int
    offline: int
    total: int


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
