"""Perintah administrasi dari terminal.

Membuat admin pertama (password diketik, tidak tersimpan di repo/riwayat):
    docker compose exec backend python -m app.cli create-admin

Reset password admin yang lupa:
    docker compose exec backend python -m app.cli reset-password --username admin
"""
from __future__ import annotations

import argparse
import asyncio
import getpass
import re
import sys

from sqlalchemy import select

from app.db import SessionLocal, engine
from app.models import User
from app.schemas import USERNAME_PATTERN
from app.services import audit
from app.services.auth import hash_password, password_problem


def _ask_password() -> str:
    while True:
        password = getpass.getpass("Password: ")
        problem = password_problem(password)
        if problem:
            print(problem)
            continue
        if getpass.getpass("Ulangi password: ") != password:
            print("Password tidak sama, ulangi.")
            continue
        return password


async def create_admin(username: str, full_name: str) -> int:
    async with SessionLocal() as session:
        exists = (await session.execute(select(User.id).where(User.username == username))).first()
        if exists:
            print(f"Username '{username}' sudah ada. Pakai reset-password bila lupa password.")
            return 1
        password = _ask_password()
        user = User(
            username=username,
            full_name=full_name,
            role="admin",
            password_hash=hash_password(password),
            is_active=True,
            token_version=0,
        )
        session.add(user)
        audit.record(session, None, "user.create", username, {"role": "admin", "via": "cli"}, username="cli")
        await session.commit()
    print(f"Admin '{username}' berhasil dibuat. Silakan login di dashboard.")
    return 0


async def reset_password(username: str) -> int:
    async with SessionLocal() as session:
        user = (await session.execute(select(User).where(User.username == username))).scalar_one_or_none()
        if user is None:
            print(f"Username '{username}' tidak ditemukan.")
            return 1
        user.password_hash = hash_password(_ask_password())
        user.token_version += 1
        user.is_active = True
        audit.record(session, None, "user.reset_password", username, {"via": "cli"}, username="cli")
        await session.commit()
    print(f"Password '{username}' berhasil direset dan akun diaktifkan.")
    return 0


def _username(value: str) -> str:
    value = value.strip().lower()
    if not re.fullmatch(USERNAME_PATTERN, value):
        raise argparse.ArgumentTypeError("username 3-32 karakter: huruf kecil, angka, titik, _ atau -")
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.cli")
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create-admin", help="buat akun admin")
    create.add_argument("--username", type=_username)
    create.add_argument("--full-name")

    reset = sub.add_parser("reset-password", help="reset password akun")
    reset.add_argument("--username", type=_username, required=True)

    args = parser.parse_args(argv)

    async def run() -> int:
        try:
            if args.command == "create-admin":
                username = args.username or _username(input("Username admin: "))
                full_name = (args.full_name or input("Nama lengkap: ")).strip() or username
                return await create_admin(username, full_name)
            return await reset_password(args.username)
        finally:
            await engine.dispose()

    return asyncio.run(run())


if __name__ == "__main__":
    sys.exit(main())
