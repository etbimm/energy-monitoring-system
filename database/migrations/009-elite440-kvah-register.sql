-- Aktifkan counter kVAh native untuk meter CEWE Elite440.
-- Unbalance pada mapping ELITE440 hanya tersedia sebagai bit status/alarm,
-- sehingga capability unbalance (%) tetap false.
--
-- Jalankan:
--   docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/009-elite440-kvah-register.sql

UPDATE devices
SET capabilities = jsonb_set(
  COALESCE(capabilities, '{}'::jsonb),
  '{apparentEnergyRegister}',
  'true'::jsonb,
  true
)
WHERE model = 'CEWE Elite440';
