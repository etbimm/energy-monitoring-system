-- Migrasi untuk database yang SUDAH berjalan.
-- Menambahkan login (tabel users), jejak perubahan (audit_log), dan
-- pendukung manajemen device (updated_at + alamat Modbus unik).
--
-- Jalankan:
--   docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/004-auth-device-management.sql
--
-- Setelah itu buat akun admin pertama:
--   docker compose exec backend python -m app.cli create-admin

ALTER TABLE devices
  ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW();

-- Gagal bila sudah ada dua meter aktif dengan alamat Modbus sama:
-- perbaiki datanya dulu, lalu jalankan ulang migrasi ini.
CREATE UNIQUE INDEX IF NOT EXISTS uq_devices_modbus_active
  ON devices (modbus_host, modbus_port, modbus_address)
  WHERE is_active AND modbus_host IS NOT NULL AND modbus_address IS NOT NULL;

CREATE TABLE IF NOT EXISTS users (
  id             SERIAL PRIMARY KEY,
  username       TEXT UNIQUE NOT NULL CHECK (username ~ '^[a-z0-9._-]{3,32}$'),
  password_hash  TEXT NOT NULL,
  full_name      TEXT NOT NULL,
  role           TEXT NOT NULL CHECK (role IN ('admin', 'viewer')),
  is_active      BOOLEAN NOT NULL DEFAULT TRUE,
  token_version  INTEGER NOT NULL DEFAULT 0,
  last_login_at  TIMESTAMPTZ,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS audit_log (
  id          BIGSERIAL PRIMARY KEY,
  user_id     INTEGER REFERENCES users(id) ON DELETE SET NULL,
  username    TEXT,
  action      TEXT NOT NULL,
  target      TEXT,
  detail      JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_audit_log_created
  ON audit_log (created_at DESC);
