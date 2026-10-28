from datetime import datetime

from sqlalchemy import Boolean, DateTime, Double, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Device(Base):
    __tablename__ = "devices"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_code: Mapped[str] = mapped_column(Text, unique=True)
    name: Mapped[str] = mapped_column(Text)
    location: Mapped[str | None] = mapped_column(Text)
    brand: Mapped[str | None] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text)
    modbus_host: Mapped[str | None] = mapped_column(Text)
    modbus_port: Mapped[int] = mapped_column(Integer, default=502)
    modbus_address: Mapped[int | None] = mapped_column(Integer)
    transport: Mapped[str | None] = mapped_column(Text)
    capabilities: Mapped[dict] = mapped_column(JSONB, default=dict)
    rated_power_kw: Mapped[float | None] = mapped_column(Double)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    readings = relationship("Reading", back_populates="device")
    alarms = relationship("Alarm", back_populates="device")


class Reading(Base):
    __tablename__ = "readings"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), primary_key=True)
    voltage: Mapped[float | None] = mapped_column(Double)
    current: Mapped[float | None] = mapped_column(Double)
    power: Mapped[float | None] = mapped_column(Double)
    apparent_power: Mapped[float | None] = mapped_column(Double)
    reactive_power: Mapped[float | None] = mapped_column(Double)
    energy_active: Mapped[float | None] = mapped_column(Double)
    energy_reactive: Mapped[float | None] = mapped_column(Double)
    frequency: Mapped[float | None] = mapped_column(Double)
    power_factor: Mapped[float | None] = mapped_column(Double)
    energy_apparent: Mapped[float | None] = mapped_column(Double)
    thd_current: Mapped[float | None] = mapped_column(Double)
    thd_voltage: Mapped[float | None] = mapped_column(Double)
    unbalance_voltage: Mapped[float | None] = mapped_column(Double)
    unbalance_current: Mapped[float | None] = mapped_column(Double)

    device = relationship("Device", back_populates="readings")


class PhaseReading(Base):
    __tablename__ = "phase_readings"

    time: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    device_id: Mapped[int] = mapped_column(ForeignKey("devices.id"), primary_key=True)
    phase: Mapped[str] = mapped_column(Text, primary_key=True)
    voltage: Mapped[float | None] = mapped_column(Double)
    current: Mapped[float | None] = mapped_column(Double)
    power: Mapped[float | None] = mapped_column(Double)
    apparent_power: Mapped[float | None] = mapped_column(Double)
    reactive_power: Mapped[float | None] = mapped_column(Double)
    power_factor: Mapped[float | None] = mapped_column(Double)
    thd_current: Mapped[float | None] = mapped_column(Double)
    thd_voltage: Mapped[float | None] = mapped_column(Double)


class Alarm(Base):
    __tablename__ = "alarms"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    device_id: Mapped[int | None] = mapped_column(ForeignKey("devices.id"))
    alarm_type: Mapped[str] = mapped_column(Text)
    severity: Mapped[str] = mapped_column(Text)
    message: Mapped[str] = mapped_column(Text)
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    triggered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    device = relationship("Device", back_populates="alarms")
