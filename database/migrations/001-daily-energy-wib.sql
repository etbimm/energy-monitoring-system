-- Migrasi untuk database yang SUDAH berjalan (file di database/init hanya
-- dieksekusi saat volume database pertama kali dibuat).
-- Mengubah batas hari view daily_energy dari 00:00 UTC menjadi 00:00 WIB.
--
-- Jalankan:
--   docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/001-daily-energy-wib.sql

DROP MATERIALIZED VIEW IF EXISTS daily_energy;

CREATE MATERIALIZED VIEW daily_energy
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

CALL refresh_continuous_aggregate('daily_energy', NULL, NULL);
