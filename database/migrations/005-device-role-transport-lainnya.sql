-- Migrasi untuk database yang SUDAH berjalan.
-- Peran (role) dan jalur (transport) device boleh berisi nilai selain pilihan
-- bawaan (opsi "Lainnya" di halaman Kelola Device).
--
-- Jalankan:
--   docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/005-device-role-transport-lainnya.sql

ALTER TABLE devices DROP CONSTRAINT IF EXISTS devices_role_check;
ALTER TABLE devices ADD CONSTRAINT devices_role_check
  CHECK (length(btrim(role)) BETWEEN 1 AND 40);

ALTER TABLE devices DROP CONSTRAINT IF EXISTS devices_transport_check;
ALTER TABLE devices ADD CONSTRAINT devices_transport_check
  CHECK (transport IS NULL OR length(btrim(transport)) BETWEEN 1 AND 40);
