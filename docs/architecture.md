# Arsitektur Sistem EMS

## Diagram Alur Data

```
[Lapisan Field]
Power Meter (Modbus RTU / Modbus TCP)
    |
    | RS485 (sebagian meter) / Ethernet (PAC3220)
    v
RS485 to Ethernet Converter  (meter RS485)
    |
    v
Switch / Jaringan LAN
    |
    v
[Lapisan Server]
Server (Linux / Docker)
    |
    |-- Acquisition (Python + pymodbus)
    |     poll register, decode per model (skala, word order, satuan)
    |     publish JSON engineering ke MQTT
    |
    |-- Mosquitto     : MQTT broker
    |
    |-- Backend API   : FastAPI
    |     subscribe MQTT, hitung PF & kVAh, simpan DB, REST + WebSocket
    |
    |-- PostgreSQL    : + TimescaleDB untuk data time-series
    |
    v
[Lapisan Presentation]
Frontend Dashboard (Next.js) : fetch REST + listen WebSocket
```

Node-RED **tidak dipakai**. Akuisisi dan decode register ada di proses Python
`backend/app/acquisition`.

## Kenapa tetap ada MQTT?

Poller dan API dipisah:

- FastAPI tidak perlu memegang socket Modbus
- Kalau API restart, broker menahan publish (QoS 1)
- Consumer lain (nanti: billing, historian) cukup subscribe
- Mode `simulator` dan mode `modbus` memakai kontrak topic yang sama

## Kontrak Topic MQTT

```
ems/meter/{device_code}/telemetry     -> payload JSON reading (satuan engineering)
ems/meter/{device_code}/status        -> online / offline
ems/alarm                             -> payload JSON alarm (opsional, REST tetap sumber)
```

Contoh payload telemetry:

```json
{
  "device_code": "PM-LVMDP-IN-01",
  "timestamp": "2026-10-28T08:30:00Z",
  "voltage": 400.2,
  "current": 182.4,
  "power": 118.6,
  "apparent_power": 126.2,
  "reactive_power": 43.1,
  "energy_active": 1421.3,
  "energy_reactive": 568.5,
  "frequency": 50.01,
  "thd_current": 2.4,
  "thd_voltage": 1.3,
  "unbalance_voltage": 0.6,
  "unbalance_current": 1.8,
  "phases": {
    "L1": { "voltage": 400.6, "current": 62.0, "power": null, "thd_current": 2.4 }
  }
}
```

Kaidah:

- Nilai sudah satuan engineering, bukan register mentah
- Field opsional yang tidak didukung = `null`, bukan `0`
- `power_factor` dan `energy_apparent` **tidak** dikirim poller — dihitung API

## Endpoint API

```
GET  /health
GET  /api/devices
GET  /api/devices/{device_code}
GET  /api/devices/{device_code}/latest
GET  /api/readings?device=&from=&to=&bucket=&role=
GET  /api/summary/today
GET  /api/alarms
POST /api/alarms/{id}/acknowledge
WS   /ws
```

Dokumentasi interaktif: http://localhost:4000/docs

## Decode per model

Sumber kebenaran profil register: `backend/app/acquisition/profiles.py`

| Model | Format | Skala khas | Function code |
|---|---|---|---|
| SIEMENS PAC3220 | float32 + uint | 1 / 10 / 100 | FC04 |
| LOVATO DMG510 | int32 / uint16 | 100 / 10 / 1000 | FC03 |
| CEWE Elite440 | float32 | 1 | FC03 |
| ACREL AMC96 | uint16 | 10 / 100 | FC03 |
| WEIDMULLER EM220 | uint32 / uint16 | 1000 / 100 | FC03 |

Word order default: little-endian (low word dulu). PF dan kVAh native tidak dipoll.

## Konsep Penting

**Time-series, bukan relasional murni.**
TimescaleDB hypertable untuk `readings` dan `phase_readings`.

**Pisahkan real-time dan historis.**
- Real-time: MQTT + memori + WebSocket
- Historis: query DB dengan `time_bucket`

**Downsampling.**
Continuous aggregate 1 menit, 15 menit, dan harian. Energi harian = delta
register kumulatif (`last - first`), bukan `SUM(power)`.
