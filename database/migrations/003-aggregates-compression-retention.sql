-- Migrasi untuk database yang SUDAH berjalan.
-- 1. readings_1min memakai agregasi real-time (data terbaru ikut terhitung)
--    dan diisi ulang untuk seluruh histori (dipakai grafik dan total energi).
-- 2. Kompresi data mentah setelah 7 hari, retensi data mentah 90 hari.
--
-- Jalankan (CALL tidak boleh di dalam transaksi, jadi jangan pakai -1):
--   docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/003-aggregates-compression-retention.sql

ALTER MATERIALIZED VIEW readings_1min SET (timescaledb.materialized_only = false);
CALL refresh_continuous_aggregate('readings_1min', NULL, now() - INTERVAL '1 minute');

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
