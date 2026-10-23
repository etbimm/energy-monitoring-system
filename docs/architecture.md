# Arsitektur Sistem EMS

## Diagram Alur Data

```
[Lapisan Field]
Power Meter (Modbus RTU master)
    |
    | RS485
    v
RS485 to Ethernet Converter
    |
    v
Switch / Jaringan LAN
    |
    v
[Lapisan Server]
Server (Linux)
    |
    |-- Node-RED      : baca register Modbus, parse, filter -> JSON matang
    |                     publish ke topic MQTT
    |
    |-- Mosquitto     : MQTT broker sebagai bridge
    |
    |-- Backend API   : subscribe MQTT, simpan ke DB, serve REST + WebSocket
    |
    |-- PostgreSQL    : + TimescaleDB untuk data time-series
    |
    v
[Lapisan Presentation]
Frontend Dashboard (Next.js) : fetch REST + listen WebSocket
```

## Kenapa Ada MQTT?

Node-RED sudah menjadi jembatan antara hardware dan software. Dengan MQTT:

- Backend **tidak perlu tahu** soal RS485 / Modbus sama sekali
- Kalau Node-RED restart/down, data tetap aman di broker (QoS 1)
- Kalau nanti ada consumer lain (mis. sistem billing), tinggal subscribe
- Kalau nanti pindah dari Modbus ke BACnet/M-Bus, hanya flow Node-RED yang berubah

## Kontrak Topic MQTT

```
ems/meter/{device_code}/telemetry     -> payload JSON reading
ems/meter/{device_code}/status        -> online / offline
ems/alarm                            -> payload JSON alarm
```

Contoh payload telemetry:

```json
{
  "device_code": "PM-001",
  "timestamp": "2026-10-10T08:30:00Z",
  "voltage": 400.2,
  "current": 182.4,
  "power": 118.6,
  "power_factor": 0.94,
  "frequency": 50.01,
  "energy_total": 14213.7
}
```

## Endpoint API (rencana)

```
GET  /api/devices                 -> daftar device
GET  /api/devices/:id/latest      -> reading terakhir
GET  /api/readings?device=&from=&to=&bucket=  -> data historis
GET  /api/summary/today           -> total daya, energy, biaya
GET  /api/alarms                  -> daftar alarm
WS   /ws                          -> push data real-time
```

## Konsep Penting

**Time-series, bukan relasional murni.**
Data monitoring = millions of rows per bulan, selalu ditulis, jarang di-update,
selalu di-query per rentang waktu. TimescaleDB membuat query ini cepat.

**Pisahkan real-time dan historis.**
- Real-time: tidak perlu query DB, cukup dari memory / broker
- Historis: query DB dengan agregasi (downsampling per jam/hari)

**Downsampling.**
Tidak perlu simpan & render data per detik untuk chart historis. Untuk chart
mingguan, cukup data per 5 menit; bulanan, per jam. Ini juga lebih hemat storage.