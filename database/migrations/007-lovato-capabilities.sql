-- Tandai kapabilitas kVAh native dan unbalance pada device LOVATO DMG510.
--
-- Jalankan:
--   docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/007-lovato-capabilities.sql

UPDATE devices
SET capabilities = jsonb_set(
  jsonb_set(
    COALESCE(capabilities, '{}'::jsonb),
    '{apparentEnergyRegister}',
    'true'::jsonb,
    true
  ),
  '{unbalance}',
  'true'::jsonb,
  true
)
WHERE model = 'LOVATO DMG510';
