"""Endpoint khusus admin: kelola akun, kelola device, dan audit log."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.acquisition.profiles import (
    CUSTOM_MODEL_CAPABILITIES,
    MODEL_CATALOG,
    PROFILES,
    default_capabilities,
    is_supported_model,
)
from app.api.deps import require_admin
from app.db import get_session
from app.models import Alarm, AuditLog, Device, User
from app.schemas import (
    AuditLogOut,
    DeviceConfigOut,
    DeviceCreate,
    DeviceModelOut,
    DeviceOptionsOut,
    DeviceUpdate,
    KNOWN_ROLES,
    KNOWN_TRANSPORTS,
    MeterCapabilities,
    PasswordReset,
    UserCreate,
    UserOut,
    UserUpdate,
)
from app.services import audit
from app.services.auth import hash_password, password_problem
from app.services.error_reporting import resolve_error
from app.services.realtime import hub

router = APIRouter(prefix="/api/admin", tags=["admin"], dependencies=[Depends(require_admin)])


# ---------------------------------------------------------------------------
# Akun pengguna
# ---------------------------------------------------------------------------


async def _get_user(session: AsyncSession, user_id: int) -> User:
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=404, detail="Akun tidak ditemukan.")
    return user


async def _active_admin_count(session: AsyncSession) -> int:
    return (
        await session.execute(
            select(func.count()).select_from(User).where(User.role == "admin", User.is_active.is_(True))
        )
    ).scalar_one()


@router.get("/users", response_model=list[UserOut])
async def list_users(session: AsyncSession = Depends(get_session)) -> list[User]:
    return list((await session.execute(select(User).order_by(User.id))).scalars().all())


@router.post("/users", response_model=UserOut, status_code=201)
async def create_user(
    payload: UserCreate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> User:
    problem = password_problem(payload.password)
    if problem:
        raise HTTPException(status_code=422, detail=problem)
    exists = (await session.execute(select(User.id).where(User.username == payload.username))).first()
    if exists:
        raise HTTPException(status_code=409, detail=f"Username '{payload.username}' sudah dipakai.")

    user = User(
        username=payload.username,
        full_name=payload.full_name,
        role=payload.role,
        password_hash=hash_password(payload.password),
        is_active=True,
        token_version=0,
    )
    session.add(user)
    audit.record(session, admin, "user.create", payload.username, {"role": payload.role})
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail=f"Username '{payload.username}' sudah dipakai.")
    await session.refresh(user)
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
async def update_user(
    user_id: int,
    payload: UserUpdate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> User:
    user = await _get_user(session, user_id)
    changes = payload.model_dump(exclude_unset=True)
    if any(value is None for value in changes.values()):
        raise HTTPException(status_code=422, detail="Field tidak boleh dikosongkan.")

    role_changed = changes.get("role", user.role) != user.role
    deactivating = changes.get("is_active", user.is_active) is False and user.is_active
    # Admin aktif yang kehilangan hak admin (diturunkan ke viewer / dinonaktifkan).
    losing_admin = user.role == "admin" and user.is_active and (role_changed or deactivating)
    if user.id == admin.id and losing_admin:
        raise HTTPException(
            status_code=400,
            detail="Anda tidak bisa menurunkan role atau menonaktifkan akun sendiri.",
        )
    if losing_admin and await _active_admin_count(session) <= 1:
        raise HTTPException(status_code=400, detail="Harus ada minimal satu admin aktif.")

    before = {key: getattr(user, key) for key in changes}
    for key, value in changes.items():
        setattr(user, key, value)
    if role_changed or deactivating:
        # Sesi lama berakhir agar hak akses baru langsung berlaku.
        user.token_version += 1
    diff = {key: {"from": before[key], "to": value} for key, value in changes.items() if before[key] != value}
    if diff:
        audit.record(session, admin, "user.update", user.username, diff)
    await session.commit()
    await session.refresh(user)
    return user


@router.post("/users/{user_id}/reset-password")
async def reset_password(
    user_id: int,
    payload: PasswordReset,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    problem = password_problem(payload.password)
    if problem:
        raise HTTPException(status_code=422, detail=problem)
    user = await _get_user(session, user_id)
    user.password_hash = hash_password(payload.password)
    user.token_version += 1
    audit.record(session, admin, "user.reset_password", user.username)
    await session.commit()
    return {"ok": True}


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> dict[str, bool]:
    """Hapus akun permanen.

    Riwayat audit log tetap ada: kolom username menyimpan salinan nama, dan
    user_id otomatis menjadi NULL (FK ON DELETE SET NULL). Sesi akun yang
    dihapus langsung tidak berlaku karena user tidak ditemukan lagi.
    """
    user = await _get_user(session, user_id)
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Anda tidak bisa menghapus akun sendiri.")
    if user.role == "admin" and user.is_active and await _active_admin_count(session) <= 1:
        raise HTTPException(status_code=400, detail="Harus ada minimal satu admin aktif.")

    audit.record(
        session,
        admin,
        "user.delete",
        user.username,
        {"full_name": user.full_name, "role": user.role, "was_active": user.is_active},
    )
    await session.delete(user)
    await session.commit()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Device
# ---------------------------------------------------------------------------


def _device_out(device: Device) -> DeviceConfigOut:
    return DeviceConfigOut(
        id=device.device_code,
        name=device.name,
        location=device.location,
        brand=device.brand,
        model=device.model,
        role=device.role,
        transport=device.transport,
        modbus_host=device.modbus_host,
        modbus_port=device.modbus_port,
        modbus_address=device.modbus_address,
        rated_power_kw=device.rated_power_kw,
        is_active=device.is_active,
        profile_supported=is_supported_model(device.model),
        last_seen=device.last_seen_at,
        created_at=device.created_at,
        updated_at=device.updated_at,
    )


async def _get_device(session: AsyncSession, code: str) -> Device:
    device = (
        await session.execute(select(Device).where(Device.device_code == code.strip().upper()))
    ).scalar_one_or_none()
    if device is None:
        raise HTTPException(status_code=404, detail="Device tidak ditemukan.")
    return device


async def _ensure_address_free(
    session: AsyncSession, host: str | None, port: int, address: int | None, exclude_id: int | None = None
) -> None:
    """Satu alamat Modbus hanya untuk satu meter aktif (bentrok = data tertukar)."""
    if host is None or address is None:
        return
    stmt = select(Device.device_code).where(
        Device.is_active.is_(True),
        Device.modbus_host == host,
        Device.modbus_port == port,
        Device.modbus_address == address,
    )
    if exclude_id is not None:
        stmt = stmt.where(Device.id != exclude_id)
    other = (await session.execute(stmt)).scalar_one_or_none()
    if other:
        raise HTTPException(
            status_code=409,
            detail=f"Alamat Modbus {host}:{port} slave {address} sudah dipakai {other}.",
        )


def _brand_for(model: str) -> str:
    entry = MODEL_CATALOG.get(model)
    return entry["label"] if entry else model


def _resolve_brand(model: str, brand: str | None) -> str:
    """Merek yang disimpan: label katalog untuk model dikenal, isian admin
    untuk model "Lainnya" (wajib diisi)."""
    if is_supported_model(model):
        return _brand_for(model)
    if not brand:
        raise HTTPException(status_code=422, detail="Merek wajib diisi untuk model di luar daftar (Lainnya).")
    return brand


async def _on_deactivated(session: AsyncSession, device: Device) -> None:
    """Meter dinonaktifkan: tutup alarmnya dan berhenti tampil di realtime."""
    await session.execute(
        update(Alarm)
        .where(Alarm.device_id == device.id, Alarm.cleared_at.is_(None))
        .values(cleared_at=datetime.now(timezone.utc))
    )
    hub.latest.pop(device.device_code, None)


@router.get("/device-models", response_model=list[DeviceModelOut])
async def device_models(session: AsyncSession = Depends(get_session)) -> list[DeviceModelOut]:
    """Model yang punya profil register, lalu model "Lainnya" yang sudah
    pernah dipakai device (agar bisa dipilih ulang tanpa diketik)."""
    options = [
        DeviceModelOut(
            model=model,
            brand=profile.brand,
            label=_brand_for(model),
            capabilities=MeterCapabilities.model_validate(default_capabilities(model)),
        )
        for model, profile in PROFILES.items()
    ]
    rows = (
        await session.execute(
            select(Device.model, func.min(Device.brand))
            .where(Device.model.not_in(list(PROFILES)))
            .group_by(Device.model)
            .order_by(Device.model)
        )
    ).all()
    for model, brand in rows:
        options.append(
            DeviceModelOut(
                model=model,
                brand=brand or model,
                label=f"{brand} {model}" if brand and brand.casefold() not in model.casefold() else model,
                capabilities=MeterCapabilities.model_validate(CUSTOM_MODEL_CAPABILITIES),
                supported=False,
            )
        )
    return options


@router.get("/device-options", response_model=DeviceOptionsOut)
async def device_options(session: AsyncSession = Depends(get_session)) -> DeviceOptionsOut:
    roles = (
        await session.execute(
            select(Device.role).where(Device.role.not_in(KNOWN_ROLES)).distinct().order_by(Device.role)
        )
    ).scalars().all()
    transports = (
        await session.execute(
            select(Device.transport)
            .where(Device.transport.is_not(None), Device.transport.not_in(KNOWN_TRANSPORTS))
            .distinct()
            .order_by(Device.transport)
        )
    ).scalars().all()
    return DeviceOptionsOut(custom_roles=list(roles), custom_transports=list(transports))


@router.get("/devices", response_model=list[DeviceConfigOut])
async def list_device_configs(session: AsyncSession = Depends(get_session)) -> list[DeviceConfigOut]:
    devices = (await session.execute(select(Device).order_by(Device.id))).scalars().all()
    return [_device_out(device) for device in devices]


@router.post("/devices", response_model=DeviceConfigOut, status_code=201)
async def create_device(
    payload: DeviceCreate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> DeviceConfigOut:
    exists = (
        await session.execute(select(Device.id).where(Device.device_code == payload.device_code))
    ).first()
    if exists:
        raise HTTPException(status_code=409, detail=f"Kode device {payload.device_code} sudah terdaftar.")
    await _ensure_address_free(session, payload.modbus_host, payload.modbus_port, payload.modbus_address)

    device = Device(
        device_code=payload.device_code,
        name=payload.name,
        location=payload.location,
        brand=_resolve_brand(payload.model, payload.brand),
        model=payload.model,
        role=payload.role,
        transport=payload.transport,
        modbus_host=payload.modbus_host,
        modbus_port=payload.modbus_port,
        modbus_address=payload.modbus_address,
        rated_power_kw=payload.rated_power_kw,
        capabilities=default_capabilities(payload.model),
        is_active=True,
    )
    session.add(device)
    audit.record(
        session, admin, "device.create", payload.device_code,
        {**payload.model_dump(exclude={"device_code", "brand"}), "brand": device.brand},
    )
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Kode device atau alamat Modbus sudah dipakai.")
    await session.refresh(device)
    return _device_out(device)


@router.patch("/devices/{device_code}", response_model=DeviceConfigOut)
async def update_device(
    device_code: str,
    payload: DeviceUpdate,
    admin: User = Depends(require_admin),
    session: AsyncSession = Depends(get_session),
) -> DeviceConfigOut:
    device = await _get_device(session, device_code)
    changes = payload.model_dump(exclude_unset=True)
    nullable = {"location", "rated_power_kw", "brand"}
    if any(value is None and key not in nullable for key, value in changes.items()):
        raise HTTPException(status_code=422, detail="Field wajib tidak boleh dikosongkan.")

    will_be_active = changes.get("is_active", device.is_active)
    if will_be_active:
        await _ensure_address_free(
            session,
            changes.get("modbus_host", device.modbus_host),
            changes.get("modbus_port", device.modbus_port),
            changes.get("modbus_address", device.modbus_address),
            exclude_id=device.id,
        )

    new_model = changes.get("model", device.model)
    if "brand" in changes or "model" in changes:
        # Merek mengikuti katalog untuk model dikenal; untuk model "Lainnya"
        # pakai isian baru, atau merek lama bila model tidak berganti.
        fallback = device.brand if new_model == device.model else None
        changes["brand"] = _resolve_brand(new_model, changes.get("brand") or fallback)

    before = {key: getattr(device, key) for key in changes}
    for key, value in changes.items():
        setattr(device, key, value)
    if "model" in changes and changes["model"] != before["model"]:
        device.capabilities = default_capabilities(device.model)
    if before.get("is_active") is True and device.is_active is False:
        await _on_deactivated(session, device)

    diff = {key: {"from": before[key], "to": value} for key, value in changes.items() if before[key] != value}
    if diff:
        action = "device.update"
        if set(diff) == {"is_active"}:
            action = "device.activate" if device.is_active else "device.deactivate"
        audit.record(session, admin, action, device.device_code, diff)
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        raise HTTPException(status_code=409, detail="Alamat Modbus sudah dipakai meter aktif lain.")
    await session.refresh(device)
    if before.get("is_active") is True and not device.is_active:
        await resolve_error(f"meter:{device.device_code}", f"Power meter {device.device_code} dinonaktifkan.")
    return _device_out(device)


# ---------------------------------------------------------------------------
# Audit log
# ---------------------------------------------------------------------------


@router.get("/audit-log", response_model=list[AuditLogOut])
async def audit_log(
    limit: int = Query(default=100, ge=1, le=500),
    session: AsyncSession = Depends(get_session),
) -> list[AuditLog]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc()).limit(limit)
    return list((await session.execute(stmt)).scalars().all())
