-- Inventaris 18 power meter (Java Wood Pellet).
-- IP/host Modbus adalah placeholder — sesuaikan saat commissioning.

INSERT INTO devices (
  device_code, name, location, brand, model, role,
  modbus_host, modbus_port, modbus_address, transport, capabilities
) VALUES
  (
    'PM-LVMDP-IN-01', 'LVMDP Incoming 1', 'LVMDP', 'SIEMENS PAC3220', 'SIEMENS PAC3220', 'incoming',
    '192.168.10.11', 502, 1, 'ethernet',
    '{"perPhase":true,"apparentEnergyRegister":true,"thdCurrent":true,"thdVoltage":true,"maxHarmonicOrder":40,"unbalance":true,"reactiveEnergy":true,"demand":true}'::jsonb
  ),
  (
    'PM-LVMDP-IN-02', 'LVMDP Incoming 2', 'LVMDP', 'SIEMENS PAC3220', 'SIEMENS PAC3220', 'incoming',
    '192.168.10.12', 502, 1, 'ethernet',
    '{"perPhase":true,"apparentEnergyRegister":true,"thdCurrent":true,"thdVoltage":true,"maxHarmonicOrder":40,"unbalance":true,"reactiveEnergy":true,"demand":true}'::jsonb
  ),
  (
    'PM-LVMDP-IN-03', 'LVMDP Incoming 3', 'LVMDP', 'SIEMENS PAC3220', 'SIEMENS PAC3220', 'incoming',
    '192.168.10.13', 502, 1, 'ethernet',
    '{"perPhase":true,"apparentEnergyRegister":true,"thdCurrent":true,"thdVoltage":true,"maxHarmonicOrder":40,"unbalance":true,"reactiveEnergy":true,"demand":true}'::jsonb
  ),
  (
    'PM-LVMDP-IN-04', 'LVMDP Incoming 4', 'LVMDP', 'SIEMENS PAC3220', 'SIEMENS PAC3220', 'incoming',
    '192.168.10.14', 502, 1, 'ethernet',
    '{"perPhase":true,"apparentEnergyRegister":true,"thdCurrent":true,"thdVoltage":true,"maxHarmonicOrder":40,"unbalance":true,"reactiveEnergy":true,"demand":true}'::jsonb
  ),
  (
    'PM-LVMDP-IN-05', 'LVMDP Incoming 5', 'LVMDP', 'SIEMENS PAC3220', 'SIEMENS PAC3220', 'incoming',
    '192.168.10.15', 502, 1, 'ethernet',
    '{"perPhase":true,"apparentEnergyRegister":true,"thdCurrent":true,"thdVoltage":true,"maxHarmonicOrder":40,"unbalance":true,"reactiveEnergy":true,"demand":true}'::jsonb
  ),
  (
    'PM-LVMDP-OUT-01', 'LVMDP Outcoming 1', 'LVMDP', 'LOVATO DMG510', 'LOVATO DMG510', 'outcoming',
    '192.168.10.20', 502, 1, 'rs485',
    '{"perPhase":true,"apparentEnergyRegister":false,"thdCurrent":true,"thdVoltage":true,"maxHarmonicOrder":15,"unbalance":false,"reactiveEnergy":true,"demand":true}'::jsonb
  ),
  (
    'PM-LVMDP-OUT-02', 'LVMDP Outcoming 2', 'LVMDP', 'LOVATO DMG510', 'LOVATO DMG510', 'outcoming',
    '192.168.10.20', 502, 2, 'rs485',
    '{"perPhase":true,"apparentEnergyRegister":false,"thdCurrent":true,"thdVoltage":true,"maxHarmonicOrder":15,"unbalance":false,"reactiveEnergy":true,"demand":true}'::jsonb
  ),
  (
    'PM-LVMDP-OUT-03', 'LVMDP Outcoming 3', 'LVMDP', 'LOVATO DMG510', 'LOVATO DMG510', 'outcoming',
    '192.168.10.20', 502, 3, 'rs485',
    '{"perPhase":true,"apparentEnergyRegister":false,"thdCurrent":true,"thdVoltage":true,"maxHarmonicOrder":15,"unbalance":false,"reactiveEnergy":true,"demand":true}'::jsonb
  ),
  (
    'PM-MVMDP-01', 'MVMDP', 'MVMDP', 'CEWE Elite440', 'CEWE Elite440', 'incoming',
    '192.168.10.21', 502, 1, 'rs485',
    '{"perPhase":true,"apparentEnergyRegister":false,"thdCurrent":true,"thdVoltage":true,"maxHarmonicOrder":31,"unbalance":false,"reactiveEnergy":true,"demand":true}'::jsonb
  ),
  (
    'PM-MCC1-01', 'MCC 1 Meter 1', 'MCC 1', 'Acrel AMC96', 'ACREL AMC96', 'distribution',
    '192.168.10.22', 502, 1, 'rs485',
    '{"perPhase":true,"apparentEnergyRegister":false,"thdCurrent":false,"thdVoltage":false,"maxHarmonicOrder":31,"unbalance":false,"reactiveEnergy":true,"demand":false}'::jsonb
  ),
  (
    'PM-MCC1-02', 'MCC 1 Meter 2', 'MCC 1', 'Acrel AMC96', 'ACREL AMC96', 'distribution',
    '192.168.10.22', 502, 2, 'rs485',
    '{"perPhase":true,"apparentEnergyRegister":false,"thdCurrent":false,"thdVoltage":false,"maxHarmonicOrder":31,"unbalance":false,"reactiveEnergy":true,"demand":false}'::jsonb
  ),
  (
    'PM-MCC2-01', 'MCC 2 Meter 1', 'MCC 2', 'Acrel AMC96', 'ACREL AMC96', 'distribution',
    '192.168.10.23', 502, 1, 'rs485',
    '{"perPhase":true,"apparentEnergyRegister":false,"thdCurrent":true,"thdVoltage":true,"maxHarmonicOrder":31,"unbalance":false,"reactiveEnergy":true,"demand":false}'::jsonb
  ),
  (
    'PM-MCC3-01', 'MCC 3 Meter 1', 'MCC 3', 'Acrel AMC96', 'ACREL AMC96', 'distribution',
    '192.168.10.24', 502, 1, 'rs485',
    '{"perPhase":true,"apparentEnergyRegister":false,"thdCurrent":false,"thdVoltage":false,"maxHarmonicOrder":31,"unbalance":false,"reactiveEnergy":true,"demand":false}'::jsonb
  ),
  (
    'PM-MCC3-02', 'MCC 3 Meter 2', 'MCC 3', 'Acrel AMC96', 'ACREL AMC96', 'distribution',
    '192.168.10.24', 502, 2, 'rs485',
    '{"perPhase":true,"apparentEnergyRegister":false,"thdCurrent":false,"thdVoltage":false,"maxHarmonicOrder":31,"unbalance":false,"reactiveEnergy":true,"demand":false}'::jsonb
  ),
  (
    'PM-MCC4-01', 'MCC 4 Meter 1', 'MCC 4', 'Acrel AMC96', 'ACREL AMC96', 'distribution',
    '192.168.10.25', 502, 1, 'rs485',
    '{"perPhase":true,"apparentEnergyRegister":false,"thdCurrent":false,"thdVoltage":false,"maxHarmonicOrder":31,"unbalance":false,"reactiveEnergy":true,"demand":false}'::jsonb
  ),
  (
    'PM-PEL1-01', 'MCC Pellet 1', 'MCC Pellet 1', 'Weidmuller EM220', 'WEIDMULLER EM220', 'distribution',
    '192.168.10.26', 502, 1, 'rs485',
    '{"perPhase":true,"apparentEnergyRegister":false,"thdCurrent":false,"thdVoltage":false,"maxHarmonicOrder":0,"unbalance":false,"reactiveEnergy":true,"demand":true}'::jsonb
  ),
  (
    'PM-PEL2-01', 'MCC Pellet 2', 'MCC Pellet 2', 'Weidmuller EM220', 'WEIDMULLER EM220', 'distribution',
    '192.168.10.26', 502, 2, 'rs485',
    '{"perPhase":true,"apparentEnergyRegister":false,"thdCurrent":false,"thdVoltage":false,"maxHarmonicOrder":0,"unbalance":false,"reactiveEnergy":true,"demand":true}'::jsonb
  ),
  (
    'PM-PEL3-01', 'MCC Pellet 3', 'MCC Pellet 3', 'Weidmuller EM220', 'WEIDMULLER EM220', 'distribution',
    '192.168.10.26', 502, 3, 'rs485',
    '{"perPhase":true,"apparentEnergyRegister":false,"thdCurrent":false,"thdVoltage":false,"maxHarmonicOrder":0,"unbalance":false,"reactiveEnergy":true,"demand":true}'::jsonb
  )
ON CONFLICT (device_code) DO NOTHING;

UPDATE devices
SET capabilities = jsonb_set(
  jsonb_set(capabilities, '{thdCurrent}', 'true'::jsonb, true),
  '{thdVoltage}',
  CASE WHEN model = 'WEIDMULLER EM220' THEN 'false'::jsonb ELSE 'true'::jsonb END,
  true
)
WHERE model IN (
  'SIEMENS PAC3220',
  'LOVATO DMG510',
  'CEWE Elite440',
  'ACREL AMC96',
  'WEIDMULLER EM220'
);
