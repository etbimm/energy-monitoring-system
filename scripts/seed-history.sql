-- Data simulasi 30 hari, interval 15 menit, untuk dashboard pengembangan.
-- Jangan jalankan pada database produksi atau database dengan meter fisik.

BEGIN;

CREATE TEMP TABLE ems_demo_history ON COMMIT DROP AS
WITH parameters AS (
  SELECT
    date_trunc('day', CURRENT_TIMESTAMP AT TIME ZONE 'UTC') AT TIME ZONE 'UTC'
      - INTERVAL '29 days' AS start_time,
    date_bin(
      INTERVAL '15 minutes',
      CURRENT_TIMESTAMP,
      TIMESTAMPTZ '2000-01-01 00:07:00+00'
    ) AS end_time
),
meter_specs (device_code, nominal_power, base_energy, base_pf) AS (
  VALUES
    ('PM-LVMDP-IN-01', 118.6, 1421.3, 0.94),
    ('PM-LVMDP-IN-02', 74.2, 889.4, 0.92),
    ('PM-LVMDP-IN-03', 52.8, 633.6, 0.88),
    ('PM-LVMDP-IN-04', 33.1, 397.2, 0.93),
    ('PM-LVMDP-IN-05', 21.3, 255.6, 0.90),
    ('PM-LVMDP-OUT-01', 96.4, 1156.8, 0.91),
    ('PM-LVMDP-OUT-02', 71.8, 861.6, 0.90),
    ('PM-LVMDP-OUT-03', 55.2, 662.4, 0.92),
    ('PM-MVMDP-01', 64.5, 774.0, 0.95),
    ('PM-MCC1-01', 42.6, 511.2, 0.90),
    ('PM-MCC1-02', 38.2, 458.4, 0.89),
    ('PM-MCC2-01', 29.4, 352.8, 0.88),
    ('PM-MCC3-01', 31.7, 380.4, 0.91),
    ('PM-MCC3-02', 27.3, 327.6, 0.90),
    ('PM-MCC4-01', 18.0, 210.0, 0.90),
    ('PM-PEL1-01', 26.5, 318.0, 0.93),
    ('PM-PEL2-01', 24.1, 289.2, 0.92),
    ('PM-PEL3-01', 28.9, 346.8, 0.94)
),
samples AS (
  SELECT
    d.id AS device_id,
    d.device_code,
    d.capabilities,
    s.nominal_power,
    s.base_energy,
    s.base_pf,
    ticks.sample_time
  FROM devices d
  JOIN meter_specs s ON s.device_code = d.device_code
  CROSS JOIN parameters p
  CROSS JOIN LATERAL generate_series(
    p.start_time + INTERVAL '7 minutes',
    p.end_time,
    INTERVAL '15 minutes'
  ) AS ticks(sample_time)
  WHERE d.is_active AND d.device_code <> 'PM-MCC4-01'
),
profile AS (
  SELECT
    samples.*,
    400 + 2.5 * sin(EXTRACT(EPOCH FROM sample_time) / 3000 + device_id)
      AS voltage,
    -- Profil beban harian/mingguan mengikuti jam lokal pabrik (WIB).
    CASE
      WHEN EXTRACT(HOUR FROM sample_time AT TIME ZONE 'Asia/Jakarta') < 6 THEN 0.25
      WHEN EXTRACT(HOUR FROM sample_time AT TIME ZONE 'Asia/Jakarta') < 8 THEN 0.55
      WHEN EXTRACT(HOUR FROM sample_time AT TIME ZONE 'Asia/Jakarta') < 11 THEN 0.95
      WHEN EXTRACT(HOUR FROM sample_time AT TIME ZONE 'Asia/Jakarta') < 14 THEN 1.15
      WHEN EXTRACT(HOUR FROM sample_time AT TIME ZONE 'Asia/Jakarta') < 17 THEN 1.00
      WHEN EXTRACT(HOUR FROM sample_time AT TIME ZONE 'Asia/Jakarta') < 20 THEN 0.70
      ELSE 0.35
    END
      * CASE
          WHEN EXTRACT(ISODOW FROM sample_time AT TIME ZONE 'Asia/Jakarta') = 6 THEN 0.78
          WHEN EXTRACT(ISODOW FROM sample_time AT TIME ZONE 'Asia/Jakarta') = 7 THEN 0.62
          ELSE 1.0
        END
      * (1 + 0.08 * sin(EXTRACT(EPOCH FROM sample_time) / 7200 + device_id))
      AS load_factor,
    GREATEST(
      0.85,
      LEAST(
        0.99,
        base_pf + 0.015 * sin(EXTRACT(EPOCH FROM sample_time) / 3600 + device_id)
      )
    ) AS power_factor
  FROM samples
),
powered AS (
  SELECT
    profile.*,
    nominal_power * load_factor AS power,
    (nominal_power * load_factor) * tan(acos(power_factor)) AS reactive_power
  FROM profile
),
steps AS (
  -- Energi per interval = rata-rata daya awal & akhir interval x durasi (jam),
  -- sama dengan simulator: kWh += (P_sebelumnya + P_sekarang) / 2 x Δt.
  SELECT
    powered.*,
    COALESCE(
      (power + LAG(power) OVER w) / 2
        * EXTRACT(EPOCH FROM (sample_time - LAG(sample_time) OVER w)) / 3600.0,
      0
    ) AS step_kwh,
    COALESCE(
      (reactive_power + LAG(reactive_power) OVER w) / 2
        * EXTRACT(EPOCH FROM (sample_time - LAG(sample_time) OVER w)) / 3600.0,
      0
    ) AS step_kvarh,
    (power_factor + COALESCE(LAG(power_factor) OVER w, power_factor)) / 2
      AS pf_avg,
    FIRST_VALUE(power_factor) OVER w AS first_pf
  FROM powered
  WINDOW w AS (PARTITION BY device_id ORDER BY sample_time)
)
SELECT
  steps.*,
  -- Counter kumulatif: energi awal + jumlah energi tiap interval.
  base_energy + SUM(step_kwh) OVER w AS energy_active,
  base_energy * 0.4 + SUM(step_kvarh) OVER w AS energy_reactive,
  -- kVAh diintegrasikan seperti backend: awal = kWh/PF, lalu + ΔkWh/PF_rata2.
  base_energy / first_pf + SUM(step_kwh / pf_avg) OVER w AS energy_apparent,
  power / power_factor AS apparent_power,
  power * 1000 / (sqrt(3.0) * voltage * power_factor) AS current
FROM steps
WINDOW w AS (PARTITION BY device_id ORDER BY sample_time);

INSERT INTO readings (
  time, device_id, voltage, current, power, apparent_power, reactive_power,
  energy_active, energy_reactive, frequency, power_factor, energy_apparent,
  thd_current, thd_voltage, unbalance_voltage, unbalance_current
)
SELECT
  sample_time,
  device_id,
  voltage,
  current,
  power,
  apparent_power,
  reactive_power,
  energy_active,
  energy_reactive,
  50 + 0.03 * sin(EXTRACT(EPOCH FROM sample_time) / 1800 + device_id),
  power_factor,
  energy_apparent,
  CASE WHEN (capabilities->>'thdCurrent')::boolean
    THEN 1.5 + 4 * (0.5 + 0.5 * sin(EXTRACT(EPOCH FROM sample_time) / 2400 + device_id))
    ELSE NULL
  END,
  CASE WHEN (capabilities->>'thdVoltage')::boolean
    THEN 0.8 + 2 * (0.5 + 0.5 * sin(EXTRACT(EPOCH FROM sample_time) / 3600 + device_id))
    ELSE NULL
  END,
  CASE WHEN (capabilities->>'unbalance')::boolean
    THEN 0.3 + 1.5 * (0.5 + 0.5 * sin(EXTRACT(EPOCH FROM sample_time) / 4200 + device_id))
    ELSE NULL
  END,
  CASE WHEN (capabilities->>'unbalance')::boolean
    THEN 1 + 3 * (0.5 + 0.5 * sin(EXTRACT(EPOCH FROM sample_time) / 3000 + device_id))
    ELSE NULL
  END
FROM ems_demo_history
ON CONFLICT (time, device_id) DO UPDATE SET
  voltage = EXCLUDED.voltage,
  current = EXCLUDED.current,
  power = EXCLUDED.power,
  apparent_power = EXCLUDED.apparent_power,
  reactive_power = EXCLUDED.reactive_power,
  energy_active = EXCLUDED.energy_active,
  energy_reactive = EXCLUDED.energy_reactive,
  frequency = EXCLUDED.frequency,
  power_factor = EXCLUDED.power_factor,
  energy_apparent = EXCLUDED.energy_apparent,
  thd_current = EXCLUDED.thd_current,
  thd_voltage = EXCLUDED.thd_voltage,
  unbalance_voltage = EXCLUDED.unbalance_voltage,
  unbalance_current = EXCLUDED.unbalance_current;

INSERT INTO phase_readings (
  time, device_id, phase, voltage, current, power, apparent_power,
  reactive_power, power_factor, thd_current, thd_voltage
)
SELECT
  sample.sample_time,
  sample.device_id,
  phase.phase,
  sample.voltage / sqrt(3.0)
    + phase.voltage_offset,
  sample.current * phase.current_factor,
  sample.power * phase.power_share,
  sample.apparent_power * phase.power_share,
  sample.reactive_power * phase.power_share,
  sample.power_factor,
  CASE WHEN (sample.capabilities->>'thdCurrent')::boolean
    THEN 1.5 + 4 * (
      0.5 + 0.5 * sin(EXTRACT(EPOCH FROM sample.sample_time) / 2400 + sample.device_id + phase.phase_offset)
    )
    ELSE NULL
  END,
  CASE WHEN (sample.capabilities->>'thdVoltage')::boolean
    THEN 0.8 + 2 * (
      0.5 + 0.5 * sin(EXTRACT(EPOCH FROM sample.sample_time) / 3600 + sample.device_id + phase.phase_offset)
    )
    ELSE NULL
  END
FROM ems_demo_history sample
CROSS JOIN (
  VALUES
    ('L1', 0.34, 1.02, 0.5, 0.0),
    ('L2', 0.33, 0.99, -0.2, 1.0),
    ('L3', 0.33, 0.99, -0.3, 2.0)
) AS phase(phase, power_share, current_factor, voltage_offset, phase_offset)
ON CONFLICT (time, device_id, phase) DO UPDATE SET
  voltage = EXCLUDED.voltage,
  current = EXCLUDED.current,
  power = EXCLUDED.power,
  apparent_power = EXCLUDED.apparent_power,
  reactive_power = EXCLUDED.reactive_power,
  power_factor = EXCLUDED.power_factor,
  thd_current = EXCLUDED.thd_current,
  thd_voltage = EXCLUDED.thd_voltage;

UPDATE devices
SET last_seen_at = CURRENT_TIMESTAMP - INTERVAL '2 minutes'
WHERE device_code <> 'PM-MCC4-01';

UPDATE devices
SET last_seen_at = CURRENT_TIMESTAMP - INTERVAL '42 minutes'
WHERE device_code = 'PM-MCC4-01';

COMMIT;
