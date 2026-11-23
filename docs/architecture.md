# Arsitektur Sistem EMS

## Diagram Alur Data

```
Power Meter --RS485 / Ethernet--> Gateway (bila digunakan)
                                      |
                   mode modbus: Modbus TCP
                                      v
Simulator --------------------> Acquisition worker (Python)
                                 |  baca konfigurasi meter aktif dari DB
                                 |  poll setiap 5 detik; gateway paralel,
                                 |  meter pada gateway yang sama berurutan
                                 |  publish telemetry dan status
                                 v
                         Mosquitto (MQTT QoS 1)
                                 |
                                 | subscriber hanya topic telemetry
                                 v
Frontend (Next.js) <--> Backend API (FastAPI) : REST request/response + WebSocket
  login diperlukan;                |  hitung PF dan integrasi kVAh
  REST sinkron berkala             |  ingest, alarm, REST, WebSocket
                                   v
                         PostgreSQL + TimescaleDB
                         devices, readings, phase_readings,
                         alarms, users, audit_log, alarm_settings,
                         notification_state, continuous aggregates
```

Backend API dan acquisition adalah proses/container terpisah. Acquisition
memakai konfigurasi meter aktif dari database dan mengirim telemetry serta
status ke broker; subscriber backend memproses telemetry. Status online/offline
dashboard dihitung backend dari `last_seen_at`, bukan dari konsumsi topic status.
Pada mode `simulator`, telemetry dibuat lokal tanpa komunikasi Modbus. Frontend
dijalankan terpisah dan mengakses API melalui REST serta WebSocket `/ws`.

## Kenapa tetap ada MQTT?

Poller dan API dipisah:

- FastAPI tidak perlu memegang socket Modbus
- Acquisition dan API berjalan sebagai service terpisah; MQTT memakai QoS 1
- Consumer lain (nanti: billing, historian) cukup subscribe
- Mode `simulator` dan mode `modbus` memakai kontrak topic yang sama

## Kontrak Topic MQTT

```
ems/meter/{device_code}/telemetry     -> payload JSON reading (satuan engineering)
ems/meter/{device_code}/status        -> online / offline
```

Acquisition menerbitkan topic telemetry dan status. Backend subscribe hanya ke
topic telemetry; alarm diproses backend lalu disampaikan lewat REST/WebSocket.

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
GET  /api/energy?device=&from=&to=&role=
GET  /api/summary/today
GET  /api/alarms
POST /api/alarms/{id}/acknowledge
GET/PUT /api/admin/alarm-thresholds  (khusus Admin)
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
| WEIDMULLER EM220 | uint32 / uint16 / float32 THD-I | 1000 / 100 / 1 | FC04 |

Word order default: little-endian (low word dulu); register Float32 Elite440
dan EM220 memakai high-word first. ELITE440 mempoll kVAh import/export di
offset `215`/`217` (register `40216`/`40218`) dan status flags di offset `749`
(register `40750`). Bit 4 dan 14 menandai voltage/current imbalance.

## Konsep Penting

**Time-series, bukan relasional murni.**
TimescaleDB hypertable untuk `readings` dan `phase_readings`.

**Pisahkan real-time dan historis.**
- Real-time: MQTT telemetry -> ingest -> database dan WebSocket
- Historis: query DB/continuous aggregate dengan `time_bucket`

**Downsampling.**
Continuous aggregate 1 menit, 15 menit, dan harian. Pembacaan mentah
dikompresi setelah 7 hari dan dihapus setelah 90 hari; aggregate disimpan
permanen. Energi harian = delta register kumulatif (`last - first`), bukan
`SUM(power)`.
