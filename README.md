# EMS - Energy Monitoring System

Dashboard monitoring energi untuk beberapa power meter.

## Alur Data

```
Power Meter (Modbus RTU)
  -> RS485 to Ethernet Converter
  -> Switch / Network
  -> Server
  -> Node-RED (parsing & filtering raw -> data matang)
  -> MQTT Broker (Mosquitto)
  -> Backend API (Node.js) + Database (PostgreSQL + TimescaleDB)
  -> Frontend Dashboard (Next.js)
```

## Struktur Folder

```
ems/
|- frontend/     Dashboard Next.js (sedang dikerjakan)
|- backend/      REST API Node.js (placeholder)
|- database/     SQL schema + seed untuk PostgreSQL/TimescaleDB
|- node-red/     Flow parsing Modbus (placeholder)
|- docs/         Dokumentasi arsitektur & data model
`- scripts/      Utilitas
```

## Menjalankan Frontend

```bash
cd frontend
npm install
npm run dev
```

Buka http://localhost:3000

> Saat ini seluruh data masih dummy (lihat `src/lib/mock-data.ts`).
> Nanti diganti dengan fetch ke backend API.

## Status

- [x] Struktur monorepo
- [x] Frontend scaffold dengan mock data
- [ ] Backend API
- [ ] PostgreSQL + TimescaleDB
- [ ] MQTT broker + Node-RED flow
- [ ] Integrasi data real-time (WebSocket)

## Dokumentasi

- [Arsitektur](docs/architecture.md)
- [Data Model](docs/data-model.md)
- [Node-RED Flow](docs/node-red-flow.md)