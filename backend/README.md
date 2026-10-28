# Backend EMS

FastAPI + PostgreSQL/TimescaleDB + MQTT (Mosquitto) + akuisisi Modbus (`pymodbus`).

## Tanggung jawab

- Worker akuisisi membaca meter (Modbus TCP) atau mode simulator
- Decode register per model (skala, word order, float vs integer)
- Publish JSON engineering ke MQTT
- API subscribe MQTT, hitung PF & kVAh, simpan ke TimescaleDB, evaluasi alarm
- REST + WebSocket untuk frontend

## Struktur

```
backend/
|- app/
|  |- main.py              FastAPI (REST + WebSocket)
|  |- api/                 endpoint
|  |- services/            ingest, MQTT, alarm, query
|  |- acquisition/         pymodbus + profil + decoder
|  |- models.py            SQLAlchemy
|  `- schemas.py           kontrak JSON (camelCase)
|- tests/
|- Dockerfile
`- requirements.txt
```

## Endpoint

```
GET  /health
GET  /api/devices
GET  /api/devices/{device_code}
GET  /api/devices/{device_code}/latest
GET  /api/readings?device=&from=&to=&bucket=5m&role=incoming
GET  /api/summary/today
GET  /api/alarms
POST /api/alarms/{id}/acknowledge
WS   /ws
POST /internal/ingest          # debug tanpa MQTT
```

`bucket`: `raw` | `1m` | `5m` | `15m` | `1h`

Total daya/energi hanya menjumlahkan meter `role=incoming`.

## Menjalankan (Docker, disarankan)

Dari root repo:

```bash
docker compose up --build
```

- API: http://localhost:4000/docs
- Postgres: localhost:5432
- MQTT: localhost:1883

Mode default akuisisi: `simulator` (tidak butuh meter fisik).
Untuk poll meter sungguhan:

```bash
ACQUISITION_MODE=modbus docker compose up --build
```

Sesuaikan `modbus_host` / `modbus_address` di tabel `devices`.

## Menjalankan lokal tanpa Docker API

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 4000
python -m app.acquisition
```

Database dan Mosquitto tetap lewat `docker compose up db mqtt`.

## Tes decoder

```bash
cd backend
pytest
```
