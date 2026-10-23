-- ============================================
-- EMS - Skema Database
-- PostgreSQL + TimescaleDB
-- Dijalankan otomatis saat container pertama kali start
-- ============================================

-- 1. Tabel device (power meter)
CREATE TABLE IF NOT EXISTS devices (
  id            SERIAL PRIMARY KEY,
  device_code   TEXT UNIQUE NOT NULL,          -- mis. PM-001
  name          TEXT NOT NULL,
  location      TEXT,
  modbus_address INT,
  is_active     BOOLEAN DEFAULT TRUE,
  created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Tabel reading utama (time-series / hypertable)
CREATE TABLE IF NOT EXISTS readings (
  time          TIMESTAMPTZ NOT NULL,          -- waktu pembacaan
  device_id     INTEGER NOT NULL REFERENCES devices(id),
  voltage       DOUBLE PRECISION,              -- Volt
  current       DOUBLE PRECISION,              -- Ampere
  power         DOUBLE PRECISION,              -- kW (active power)
  power_factor  DOUBLE PRECISION,              -- 0..1
  frequency     DOUBLE PRECISION,              -- Hz
  energy_total  DOUBLE PRECISION,              -- kWh kumulatif dari meter
  PRIMARY KEY (time, device_id)
);

-- Jadikan readings sebagai hypertable TimescaleDB
SELECT create_hypertable('readings', 'time', chunk_time_interval => INTERVAL '1 day');

-- Index untuk query per device pada rentang waktu tertentu
CREATE INDEX IF NOT EXISTS idx_readings_device_time
  ON readings (device_id, time DESC);

-- 3. Tabel alarm
CREATE TABLE IF NOT EXISTS alarms (
  id            SERIAL PRIMARY KEY,
  device_id     INTEGER REFERENCES devices(id),
  severity      TEXT NOT NULL CHECK (severity IN ('critical','warning','info')),
  message       TEXT NOT NULL,
  acknowledged  BOOLEAN DEFAULT FALSE,
  triggered_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_alarms_triggered
  ON alarms (triggered_at DESC);

-- ============================================
-- Continuous aggregate untuk laporan harian
-- (dapat dipercepat dengan materialized view)
-- ============================================
CREATE MATERIALIZED VIEW IF NOT EXISTS daily_energy
WITH (timescaledb.continuous) AS
SELECT
  device_id,
  time_bucket(INTERVAL '1 day', time) AS day,
  SUM(power) AS energy_kwh,
  MAX(power) AS peak_power,
  AVG(power_factor) AS avg_pf
FROM readings
GROUP BY device_id, day
WITH NO DATA;

SELECT add_continuous_aggregate_policy(
  'daily_energy',
  start_offset => INTERVAL '30 days',
  end_offset   => INTERVAL '1 hour',
  schedule_interval => INTERVAL '1 hour'
);