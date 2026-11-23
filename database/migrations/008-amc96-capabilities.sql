-- Tandai kapabilitas unbalance dan demand pada device ACREL AMC96.
--
-- Jalankan:
--   docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/008-amc96-capabilities.sql

UPDATE devices
SET capabilities = jsonb_set(
  jsonb_set(
    COALESCE(capabilities, '{}'::jsonb),
    '{unbalance}',
    'true'::jsonb,
    true
  ),
  '{demand}',
  'true'::jsonb,
  true
)
WHERE model = 'ACREL AMC96';
