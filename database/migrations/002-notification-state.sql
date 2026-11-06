-- Migrasi untuk database yang SUDAH berjalan.
-- Tabel status notifikasi Telegram yang masih aktif, agar notifikasi tidak
-- terkirim ganda (backend + acquisition) atau terkirim ulang setelah restart.
--
-- Jalankan:
--   docker exec -i ems-db-1 psql -U ems -d ems < database/migrations/002-notification-state.sql

-- Status notifikasi Telegram yang masih aktif (anti-duplikat antar proses
-- backend/acquisition dan antar restart).
CREATE TABLE IF NOT EXISTS notification_state (
  key           TEXT PRIMARY KEY,
  summary       TEXT NOT NULL,
  active_since  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

