-- Data historis 24 jam (interval 5 menit) untuk pengembangan chart.
-- HAPUS file ini sebelum production / volume DB lapangan.

INSERT INTO readings (
  time, device_id, voltage, current, power, apparent_power, reactive_power,
  energy_active, energy_reactive, frequency, power_factor, energy_apparent,
  thd_current, thd_voltage, unbalance_voltage, unbalance_current
)
SELECT
  ts,
  d.id,
  398 + random() * 5,
  20 + random() * 160,
  power_val,
  CASE WHEN pf > 0 THEN power_val / pf ELSE NULL END,
  CASE
    WHEN pf > 0 AND pf < 1 THEN power_val * tan(acos(pf))
    ELSE 0
  END,
  GREATEST(
    0,
    base_energy + power_val * EXTRACT(EPOCH FROM (ts - date_trunc('day', NOW()))) / 3600.0
  ),
  GREATEST(
    0,
    (base_energy * 0.4) + power_val * 0.4 * EXTRACT(EPOCH FROM (ts - date_trunc('day', NOW()))) / 3600.0
  ),
  49.9 + random() * 0.2,
  pf,
  CASE
    WHEN pf > 0 THEN
      GREATEST(
        0,
        (base_energy + power_val * EXTRACT(EPOCH FROM (ts - date_trunc('day', NOW()))) / 3600.0) / pf
      )
    ELSE NULL
  END,
  CASE WHEN (d.capabilities->>'thdCurrent')::boolean THEN 1.5 + random() * 4 ELSE NULL END,
  CASE WHEN (d.capabilities->>'thdVoltage')::boolean THEN 0.8 + random() * 2 ELSE NULL END,
  CASE WHEN (d.capabilities->>'unbalance')::boolean THEN 0.3 + random() * 1.5 ELSE NULL END,
  CASE WHEN (d.capabilities->>'unbalance')::boolean THEN 1.0 + random() * 3 ELSE NULL END
FROM devices d
CROSS JOIN LATERAL generate_series(
  date_trunc('day', NOW()),
  NOW(),
  INTERVAL '5 minutes'
) AS ts
CROSS JOIN LATERAL (
  SELECT
    CASE d.device_code
      WHEN 'PM-LVMDP-IN-01' THEN 118.6
      WHEN 'PM-LVMDP-IN-02' THEN 74.2
      WHEN 'PM-LVMDP-IN-03' THEN 52.8
      WHEN 'PM-LVMDP-IN-04' THEN 33.1
      WHEN 'PM-LVMDP-IN-05' THEN 21.3
      WHEN 'PM-LVMDP-OUT-01' THEN 96.4
      WHEN 'PM-LVMDP-OUT-02' THEN 71.8
      WHEN 'PM-LVMDP-OUT-03' THEN 55.2
      WHEN 'PM-MVMDP-01' THEN 64.5
      WHEN 'PM-MCC1-01' THEN 42.6
      WHEN 'PM-MCC1-02' THEN 38.2
      WHEN 'PM-MCC2-01' THEN 29.4
      WHEN 'PM-MCC3-01' THEN 31.7
      WHEN 'PM-MCC3-02' THEN 27.3
      WHEN 'PM-MCC4-01' THEN 18.0
      WHEN 'PM-PEL1-01' THEN 26.5
      WHEN 'PM-PEL2-01' THEN 24.1
      WHEN 'PM-PEL3-01' THEN 28.9
      ELSE 20
    END AS nominal_power,
    CASE d.device_code
      WHEN 'PM-LVMDP-IN-01' THEN 1421.3
      WHEN 'PM-LVMDP-IN-02' THEN 889.4
      WHEN 'PM-LVMDP-IN-03' THEN 633.6
      WHEN 'PM-LVMDP-IN-04' THEN 397.2
      WHEN 'PM-LVMDP-IN-05' THEN 255.6
      WHEN 'PM-LVMDP-OUT-01' THEN 1156.8
      WHEN 'PM-LVMDP-OUT-02' THEN 861.6
      WHEN 'PM-LVMDP-OUT-03' THEN 662.4
      WHEN 'PM-MVMDP-01' THEN 774.0
      WHEN 'PM-MCC1-01' THEN 511.2
      WHEN 'PM-MCC1-02' THEN 458.4
      WHEN 'PM-MCC2-01' THEN 352.8
      WHEN 'PM-MCC3-01' THEN 380.4
      WHEN 'PM-MCC3-02' THEN 327.6
      WHEN 'PM-MCC4-01' THEN 210.0
      WHEN 'PM-PEL1-01' THEN 318.0
      WHEN 'PM-PEL2-01' THEN 289.2
      WHEN 'PM-PEL3-01' THEN 346.8
      ELSE 100
    END AS base_energy
) meta
CROSS JOIN LATERAL (
  SELECT
    GREATEST(0, meta.nominal_power * (
      CASE
        WHEN EXTRACT(HOUR FROM ts) < 6 THEN 0.25
        WHEN EXTRACT(HOUR FROM ts) < 8 THEN 0.55
        WHEN EXTRACT(HOUR FROM ts) < 11 THEN 0.95
        WHEN EXTRACT(HOUR FROM ts) < 14 THEN 1.15
        WHEN EXTRACT(HOUR FROM ts) < 17 THEN 1.00
        WHEN EXTRACT(HOUR FROM ts) < 20 THEN 0.70
        ELSE 0.35
      END
    ) * (0.92 + random() * 0.16)) AS power_val,
    CASE
      WHEN d.device_code = 'PM-LVMDP-IN-03' THEN 0.88
      WHEN d.device_code = 'PM-MCC1-02' THEN 0.89
      ELSE 0.90 + random() * 0.05
    END AS pf
) p
WHERE d.device_code <> 'PM-MCC4-01'
ON CONFLICT DO NOTHING;

UPDATE devices
SET last_seen_at = NOW() - INTERVAL '2 minutes'
WHERE device_code <> 'PM-MCC4-01';

UPDATE devices
SET last_seen_at = NOW() - INTERVAL '42 minutes'
WHERE device_code = 'PM-MCC4-01';
