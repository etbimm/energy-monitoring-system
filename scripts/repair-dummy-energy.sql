-- Perbaikan counter energi pada DATABASE DUMMY (pengembangan saja).
-- JANGAN jalankan pada database dengan meter fisik: skrip ini menimpa nilai
-- kWh/kVARh/kVAh yang tersimpan.
--
-- Masalah yang diperbaiki:
--   * simulator lama menghitung kWh dengan rumus tetap per hari (tidak
--     mengikuti kW, selisih ~38x), turun setiap 00:00 UTC, dan melonjak saat
--     versi baru mulai berjalan;
--   * kVAh lama = kWh / PF sesaat (tidak monoton).
--
-- Cara kerja (sama dengan simulator & seed saat ini): counter dihitung ulang
-- dengan mengintegrasikan daya yang TERSIMPAN di setiap baris:
--   kWh   = energi_awal + Σ (P_sebelumnya + P_sekarang) / 2 x Δt_jam
--   kVARh = energi_awal x 0.4 + Σ (Q_sebelumnya + Q_sekarang) / 2 x Δt_jam
-- lalu kVAh diintegrasikan per interval (sama dengan backend):
--   kVAh  = kWh_awal / PF_awal + Σ ΔkWh / PF_rata2
--
-- Hentikan acquisition selama skrip berjalan, lalu jalankan:
--   docker compose stop acquisition
--   docker exec -i ems-db-1 psql -U ems -d ems -v ON_ERROR_STOP=1 < scripts/repair-dummy-energy.sql
--   docker compose start acquisition

BEGIN;

-- Chunk lama sudah dikompresi; izinkan UPDATE mendekompresi semua baris
-- (hanya untuk transaksi ini). Policy kompresi akan mengompres ulang.
SET LOCAL timescaledb.max_tuples_decompressed_per_dml_transaction = 0;

CREATE TEMP TABLE meter_specs (device_code TEXT PRIMARY KEY, nominal_power DOUBLE PRECISION, base_energy DOUBLE PRECISION)
ON COMMIT DROP;
INSERT INTO meter_specs VALUES
  ('PM-LVMDP-IN-01', 118.6, 1421.3),
  ('PM-LVMDP-IN-02', 74.2, 889.4),
  ('PM-LVMDP-IN-03', 52.8, 633.6),
  ('PM-LVMDP-IN-04', 33.1, 397.2),
  ('PM-LVMDP-IN-05', 21.3, 255.6),
  ('PM-LVMDP-OUT-01', 96.4, 1156.8),
  ('PM-LVMDP-OUT-02', 71.8, 861.6),
  ('PM-LVMDP-OUT-03', 55.2, 662.4),
  ('PM-MVMDP-01', 64.5, 774.0),
  ('PM-MCC1-01', 42.6, 511.2),
  ('PM-MCC1-02', 38.2, 458.4),
  ('PM-MCC2-01', 29.4, 352.8),
  ('PM-MCC3-01', 31.7, 380.4),
  ('PM-MCC3-02', 27.3, 327.6),
  ('PM-MCC4-01', 18.0, 210.0),
  ('PM-PEL1-01', 26.5, 318.0),
  ('PM-PEL2-01', 24.1, 289.2),
  ('PM-PEL3-01', 28.9, 346.8);

-- 1. kWh dan kVARh dari integrasi daya tersimpan (monoton, sesuai kW).
WITH steps AS (
  SELECT
    r.time,
    r.device_id,
    s.base_energy,
    COALESCE(
      (COALESCE(r.power, 0) + COALESCE(LAG(r.power) OVER w, 0)) / 2
        * EXTRACT(EPOCH FROM (r.time - LAG(r.time) OVER w)) / 3600.0,
      0
    ) AS step_kwh,
    COALESCE(
      (COALESCE(r.reactive_power, 0) + COALESCE(LAG(r.reactive_power) OVER w, 0)) / 2
        * EXTRACT(EPOCH FROM (r.time - LAG(r.time) OVER w)) / 3600.0,
      0
    ) AS step_kvarh
  FROM readings r
  JOIN devices d ON d.id = r.device_id
  JOIN meter_specs s ON s.device_code = d.device_code
  WINDOW w AS (PARTITION BY r.device_id ORDER BY r.time)
),
counters AS (
  SELECT
    time,
    device_id,
    base_energy + SUM(step_kwh) OVER w AS kwh,
    base_energy * 0.4 + SUM(step_kvarh) OVER w AS kvarh
  FROM steps
  WINDOW w AS (PARTITION BY device_id ORDER BY time)
)
UPDATE readings r
SET
  energy_active = round(c.kwh::numeric, 3),
  energy_reactive = round(c.kvarh::numeric, 3)
FROM counters c
WHERE r.device_id = c.device_id AND r.time = c.time;

-- 2. kVAh diintegrasikan per interval.
WITH steps AS (
  SELECT
    time,
    device_id,
    energy_active - LAG(energy_active) OVER w AS delta_kwh,
    COALESCE(
      (NULLIF(power_factor, 0) + COALESCE(NULLIF(LAG(power_factor) OVER w, 0), NULLIF(power_factor, 0))) / 2,
      NULLIF(LAG(power_factor) OVER w, 0),
      1
    ) AS pf_avg,
    FIRST_VALUE(energy_active / COALESCE(NULLIF(power_factor, 0), 1)) OVER w AS start_kvah
  FROM readings
  WINDOW w AS (PARTITION BY device_id ORDER BY time)
),
integrated AS (
  SELECT
    time,
    device_id,
    start_kvah + COALESCE(SUM(delta_kwh / pf_avg) OVER (PARTITION BY device_id ORDER BY time), 0) AS kvah
  FROM steps
)
UPDATE readings r
SET energy_apparent = round(i.kvah::numeric, 3)
FROM integrated i
WHERE r.device_id = i.device_id AND r.time = i.time;

-- 3. Verifikasi: tidak boleh ada counter yang turun.
DO $$
DECLARE
  bad BIGINT;
BEGIN
  SELECT count(*) INTO bad FROM (
    SELECT
      energy_active < LAG(energy_active) OVER w
        OR energy_apparent < LAG(energy_apparent) OVER w
        OR energy_reactive < LAG(energy_reactive) OVER w AS turun
    FROM readings
    WINDOW w AS (PARTITION BY device_id ORDER BY time)
  ) t WHERE turun;
  IF bad > 0 THEN
    RAISE EXCEPTION 'Masih ada % counter yang turun; perbaikan dibatalkan', bad;
  END IF;
END $$;

COMMIT;

-- 4. Hitung ulang agregat dari data yang sudah diperbaiki.
CALL refresh_continuous_aggregate('readings_1min', NULL, now() - INTERVAL '1 minute');
CALL refresh_continuous_aggregate('readings_15min', NULL, now() - INTERVAL '15 minutes');
CALL refresh_continuous_aggregate('daily_energy', NULL, now() - INTERVAL '1 hour');
