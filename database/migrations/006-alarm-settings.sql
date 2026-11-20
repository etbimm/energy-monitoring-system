-- Migrasi untuk database yang SUDAH berjalan.
-- Menyimpan ambang alarm (tegangan, power factor, frekuensi, THD, unbalance,
-- beban) di tabel agar bisa diubah lewat halaman admin tanpa deploy kode.
--
-- Jalankan:
--   docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/006-alarm-settings.sql

CREATE TABLE IF NOT EXISTS alarm_settings (
  id          INTEGER PRIMARY KEY,
  thresholds  JSONB NOT NULL,
  updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO alarm_settings (id, thresholds)
VALUES (
  1,
  '{"voltage_ll_warning_low":385.0,"voltage_ll_warning_high":415.0,"voltage_ll_critical_low":350.0,"voltage_ll_critical_high":440.0,"power_factor_warning":0.90,"power_factor_critical":0.85,"frequency_warning":0.5,"frequency_critical":1.0,"thd_current_warning":5.0,"thd_current_critical":8.0,"unbalance_voltage_warning":2.0,"unbalance_voltage_critical":5.0,"load_warning":0.80,"load_critical":0.95}'::jsonb
)
ON CONFLICT (id) DO NOTHING;
