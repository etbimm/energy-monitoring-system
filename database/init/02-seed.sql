-- ============================================
-- Seed data dummy untuk pengembangan awal.
-- HAPUS file ini / baris ini sebelum production.
-- ============================================

INSERT INTO devices (device_code, name, location, modbus_address) VALUES
  ('PM-001', 'Main Incoming 1',   'Panel Utama Lantai 1', 1),
  ('PM-002', 'Gedung Produksi A', 'Lantai 2 - Line A',     2),
  ('PM-003', 'Gedung Produksi B', 'Lantai 2 - Line B',     3),
  ('PM-004', 'Ruang Chiller',     'Basement',              4),
  ('PM-005', 'Kantor Lt. 3',      'Lantai 3',              5),
  ('PM-006', 'Parkir & Outdoor',  'Area Parkir',           6)
ON CONFLICT (device_code) DO NOTHING;

-- Generate 24 jam reading per device dengan interval 5 menit
INSERT INTO readings (time, device_id, voltage, current, power, power_factor, frequency, energy_total)
SELECT
  ts,
  d.id,
  398 + random() * 5,
  20 + random() * 160,
  power_val,
  0.85 + random() * 0.12,
  49.9 + random() * 0.2,
  0
FROM devices d
CROSS JOIN LATERAL generate_series(
  date_trunc('day', NOW()),
  date_trunc('day', NOW()) + INTERVAL '24 hours',
  INTERVAL '5 minutes'
) AS ts
CROSS JOIN LATERAL (
  SELECT CASE
    WHEN EXTRACT(HOUR FROM ts) < 6   THEN 15 + random() * 20
    WHEN EXTRACT(HOUR FROM ts) < 8   THEN 40 + random() * 30
    WHEN EXTRACT(HOUR FROM ts) < 11  THEN 90 + random() * 60
    WHEN EXTRACT(HOUR FROM ts) < 14  THEN 150 + random() * 90
    WHEN EXTRACT(HOUR FROM ts) < 17  THEN 120 + random() * 60
    WHEN EXTRACT(HOUR FROM ts) < 20  THEN 70  + random() * 40
    ELSE 30 + random() * 25
  END AS power_val
) p
ON CONFLICT DO NOTHING;