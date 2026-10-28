# EMS - Energy Monitoring System

Dashboard monitoring energi untuk 18 power meter di Java Wood Pellet.

## Alur Data

```
Power Meter (Modbus RTU / TCP)
  -> RS485 to Ethernet Converter (meter RS485)
  -> Switch / Network
  -> Acquisition (Python + pymodbus, decode per model)
  -> MQTT Broker (Mosquitto)
  -> Backend API (FastAPI) + PostgreSQL/TimescaleDB
  -> Frontend Dashboard (Next.js)
```

## Struktur Folder

```
ems/
|- frontend/     Dashboard Next.js (REST API + WebSocket)
|- backend/      FastAPI + worker akuisisi Modbus
|- database/     SQL init PostgreSQL/TimescaleDB
|- mqtt/         Konfigurasi Mosquitto
|- docs/         Dokumentasi arsitektur & data model
`- scripts/      Utilitas
```

## Menjalankan Backend + Database + MQTT

```bash
docker compose up --build
```

| Service | URL |
|---|---|
| API + Swagger | http://localhost:4000/docs |
| PostgreSQL | localhost:5432 (user/db `ems`) |
| MQTT | localhost:1883 |

Mode akuisisi default: `simulator` (tanpa hardware). Set `ACQUISITION_MODE=modbus` di `.env` untuk poll meter sungguhan.

## Menjalankan Frontend

```bash
cd frontend
npm install
npm run dev
```

Buka http://localhost:3000

Frontend mengambil data dari API backend. Secara default API URL adalah
`http://localhost:4000`; atur `NEXT_PUBLIC_API_URL` sebelum menjalankan
frontend jika backend berada di host/port lain. WebSocket menggunakan URL yang
sama dengan skema `ws://`; atur `NEXT_PUBLIC_WS_URL` hanya jika endpoint WS
berbeda. Jika backend belum tersedia atau belum memiliki data meter, dashboard
menampilkan fixture simulasi realistis dan menandainya sebagai **Mode demo**.

## Status

- [x] Struktur monorepo
- [x] Frontend scaffold dengan mock data
- [x] Backend API FastAPI
- [x] PostgreSQL + TimescaleDB
- [x] MQTT broker (Mosquitto)
- [x] Akuisisi pymodbus + profil decode per model
- [x] Integrasi dashboard ke API (REST + WebSocket)
- [x] Histori API, tabel pembacaan, dan export CSV
- [x] Acknowledge alarm dari dashboard

## Dokumentasi

- [Arsitektur](docs/architecture.md)
- [Data Model](docs/data-model.md)
- [Spesifikasi Parameter](docs/parameter-specification.md)
- [Backend](backend/README.md)
