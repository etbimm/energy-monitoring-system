-- ============================================
-- EMS - Skema Database
-- PostgreSQL + TimescaleDB
-- Dijalankan otomatis saat volume DB pertama kali dibuat
-- ============================================

CREATE TABLE IF NOT EXISTS devices (
  id              SERIAL PRIMARY KEY,
  device_code     TEXT UNIQUE NOT NULL,
  name            TEXT NOT NULL,
  location        TEXT,
  brand           TEXT,
  model           TEXT NOT NULL,
  role            TEXT NOT NULL CHECK (role IN ('incoming', 'outcoming', 'distribution')),
  modbus_host     TEXT,
  modbus_port     INTEGER NOT NULL DEFAULT 502,
  modbus_address  INTEGER,
  transport       TEXT CHECK (transport IN ('rs485', 'ethernet')),
  capabilities    JSONB NOT NULL DEFAULT '{}'::jsonb,
  rated_power_kw  DOUBLE PRECISION,
  is_active       BOOLEAN NOT NULL DEFAULT TRUE,
  last_seen_at    TIMESTAMPTZ,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Satu alamat Modbus (gateway + port + slave ID) hanya boleh dipakai satu
-- meter aktif. Meter nonaktif tidak dihitung agar alamatnya bisa dipakai ulang.
CREATE UNIQUE INDEX IF NOT EXISTS uq_devices_modbus_active
  ON devices (modbus_host, modbus_port, modbus_address)
  WHERE is_active AND modbus_host IS NOT NULL AND modbus_address IS NOT NULL;

CREATE TABLE IF NOT EXISTS readings (
  time               TIMESTAMPTZ NOT NULL,
  device_id          INTEGER NOT NULL REFERENCES devices(id),
  voltage            DOUBLE PRECISION,
  current            DOUBLE PRECISION,
  power              DOUBLE PRECISION,
  apparent_power     DOUBLE PRECISION,
  reactive_power     DOUBLE PRECISION,
  energy_active      DOUBLE PRECISION,
  energy_reactive    DOUBLE PRECISION,
  frequency          DOUBLE PRECISION,
  power_factor       DOUBLE PRECISION,
  energy_apparent    DOUBLE PRECISION,
  thd_current        DOUBLE PRECISION,
  thd_voltage        DOUBLE PRECISION,
  unbalance_voltage  DOUBLE PRECISION,
  unbalance_current  DOUBLE PRECISION,
  PRIMARY KEY (time, device_id)
);

SELECT create_hypertable(
  'readings',
  'time',
  chunk_time_interval => INTERVAL '1 day',
  if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_readings_device_time
  ON readings (device_id, time DESC);

CREATE TABLE IF NOT EXISTS phase_readings (
  time            TIMESTAMPTZ NOT NULL,
  device_id       INTEGER NOT NULL REFERENCES devices(id),
  phase           TEXT NOT NULL CHECK (phase IN ('L1', 'L2', 'L3')),
  voltage         DOUBLE PRECISION,
  current         DOUBLE PRECISION,
  power           DOUBLE PRECISION,
  apparent_power  DOUBLE PRECISION,
  reactive_power  DOUBLE PRECISION,
  power_factor    DOUBLE PRECISION,
  thd_current     DOUBLE PRECISION,
  thd_voltage     DOUBLE PRECISION,
  PRIMARY KEY (time, device_id, phase)
);

SELECT create_hypertable(
  'phase_readings',
  'time',
  chunk_time_interval => INTERVAL '1 day',
  if_not_exists => TRUE
);

CREATE INDEX IF NOT EXISTS idx_phase_readings_device_time
  ON phase_readings (device_id, time DESC);

CREATE TABLE IF NOT EXISTS alarms (
  id               SERIAL PRIMARY KEY,
  device_id        INTEGER REFERENCES devices(id),
  alarm_type       TEXT NOT NULL,
  severity         TEXT NOT NULL CHECK (severity IN ('critical', 'warning', 'info')),
  message          TEXT NOT NULL,
  acknowledged     BOOLEAN NOT NULL DEFAULT FALSE,
  acknowledged_at  TIMESTAMPTZ,
  triggered_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  cleared_at       TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_alarms_triggered
  ON alarms (triggered_at DESC);

CREATE INDEX IF NOT EXISTS idx_alarms_open
  ON alarms (device_id, alarm_type)
  WHERE cleared_at IS NULL;

-- Status notifikasi Telegram yang masih aktif (anti-duplikat antar proses
-- backend/acquisition dan antar restart).
CREATE TABLE IF NOT EXISTS notification_state (
  key           TEXT PRIMARY KEY,
  summary       TEXT NOT NULL,
  active_since  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Akun pengguna dashboard (dibuat oleh admin, tidak ada registrasi publik).
-- token_version dinaikkan saat password direset, role diubah, atau akun
-- dinonaktifkan, sehingga sesi (JWT) lama langsung tidak berlaku.
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

-- Jejak perubahan oleh pengguna (login, kelola akun, kelola device).
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

-- Agregat 1 menit (grafik shift / laporan harian)
-- materialized_only = false: data terbaru yang belum dimaterialisasi ikut
-- dihitung real-time, sehingga grafik dan total energi tidak tertinggal.
CREATE MATERIALIZED VIEW IF NOT EXISTS readings_1min
WITH (timescaledb.continuous, timescaledb.materialized_only = false) AS
SELECT
  device_id,
  time_bucket(INTERVAL '1 minute', time) AS bucket,
  AVG(voltage) AS voltage,
  AVG(current) AS current,
  AVG(power) AS power,
  AVG(apparent_power) AS apparent_power,
  AVG(reactive_power) AS reactive_power,
  AVG(frequency) AS frequency,
  AVG(power_factor) AS power_factor,
  AVG(thd_current) AS thd_current,
  AVG(thd_voltage) AS thd_voltage,
  last(energy_active, time) AS energy_active,
  last(energy_reactive, time) AS energy_reactive,
  last(energy_apparent, time) AS energy_apparent
FROM readings
GROUP BY device_id, bucket
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
  'readings_1min',
  start_offset => INTERVAL '2 hours',
  end_offset => INTERVAL '1 minute',
  schedule_interval => INTERVAL '1 minute',
  if_not_exists => TRUE
);

-- Agregat 15 menit. Belum dibaca API saat ini (grafik memakai readings_1min);
-- dicadangkan sebagai sumber delta energi permanen untuk fitur deteksi losses
-- (docs/loss-detection-design.md). Jangan dihapus.
CREATE MATERIALIZED VIEW IF NOT EXISTS readings_15min
WITH (timescaledb.continuous) AS
SELECT
  device_id,
  time_bucket(INTERVAL '15 minutes', time) AS bucket,
  AVG(voltage) AS voltage,
  AVG(current) AS current,
  AVG(power) AS power,
  AVG(apparent_power) AS apparent_power,
  AVG(reactive_power) AS reactive_power,
  AVG(frequency) AS frequency,
  AVG(power_factor) AS power_factor,
  last(energy_active, time) AS energy_active,
  last(energy_reactive, time) AS energy_reactive,
  last(energy_apparent, time) AS energy_apparent
FROM readings
GROUP BY device_id, bucket
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
  'readings_15min',
  start_offset => INTERVAL '1 day',
  end_offset => INTERVAL '15 minutes',
  schedule_interval => INTERVAL '15 minutes',
  if_not_exists => TRUE
);

-- Rollup harian: energi = delta kumulatif (bukan SUM(power))
-- Batas hari mengikuti WIB (00:00 Asia/Jakarta), bukan 00:00 UTC.
-- Belum dibaca API saat ini; dicadangkan untuk laporan harian/penalti PF dan
-- acuan batas hari fitur deteksi losses. Jangan dihapus.
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_energy
WITH (timescaledb.continuous) AS
SELECT
  device_id,
  time_bucket(INTERVAL '1 day', time, 'Asia/Jakarta') AS day,
  last(energy_active, time) - first(energy_active, time) AS energy_kwh,
  last(energy_reactive, time) - first(energy_reactive, time) AS energy_kvarh,
  MAX(power) AS peak_power,
  AVG(power_factor) AS avg_pf
FROM readings
GROUP BY device_id, day
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
  'daily_energy',
  start_offset => INTERVAL '30 days',
  end_offset => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour',
  if_not_exists => TRUE
);

-- ============================================
-- Kompresi dan retensi (lihat docs/data-model.md)
-- Data mentah dikompresi setelah 7 hari dan dihapus setelah 90 hari.
-- Agregat (readings_1min, readings_15min, daily_energy) disimpan permanen.
-- ============================================
ALTER TABLE readings SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'device_id',
  timescaledb.compress_orderby = 'time DESC'
);
SELECT add_compression_policy('readings', INTERVAL '7 days', if_not_exists => TRUE);

ALTER TABLE phase_readings SET (
  timescaledb.compress,
  timescaledb.compress_segmentby = 'device_id, phase',
  timescaledb.compress_orderby = 'time DESC'
);
SELECT add_compression_policy('phase_readings', INTERVAL '7 days', if_not_exists => TRUE);

SELECT add_retention_policy('readings', INTERVAL '90 days', if_not_exists => TRUE);
SELECT add_retention_policy('phase_readings', INTERVAL '90 days', if_not_exists => TRUE);
